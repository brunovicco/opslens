"""Turn Silver query results into index rows, keyed exactly as the request path asks.

The index answers "what applies to these packages", so its key has to be the key a
request arrives with. That sounds obvious and is the easiest thing in this system to get
silently wrong.

`canonicalize_pypi_package` is what the request path uses, and what
`PublicRepositoryThreatEvidence` re-runs on every item it receives. It collapses `[-_.]`
runs and lowercases — but only after validating the name against the PyPA grammar, and
it raises on anything that fails. SQL normalization looks identical and is not: Athena
would happily normalize a name Python refuses, producing an index key no request can
ever match.

A key that no request matches is not a crash. It is an advisory that silently stops
applying, and the endpoint answering "no known vulnerabilities" for a package that has
them. So the key is computed here, in Python, by the same function the request path
calls — never by the query.

```text
normalized in SQL != canonical in Python
unmatched key != absent vulnerability
```

Names that fail the grammar are rejected and counted rather than dropped, the accounting
ADR 0085 established: `admitted + rejected == total`. A projection that quietly discards
what it cannot key would under-report by exactly the amount nobody measured.

This module maps and rejects. It runs no query and writes no row.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from opslens.correlation.domain.pypi import (
    InvalidPackageNameError,
    canonicalize_pypi_package,
)
from opslens.correlation_index.domain.index_contract import (
    CorrelationIndexContractError,
    ProjectedGhsaIndexRow,
    ProjectedNvdIndexRow,
    ProjectedSourceIdentifier,
    source_instant,
)

GHSA_PROJECTION_COLUMNS: Final = (
    "ghsa_id",
    "observed_advisory_version_id",
    "source_advisory_sha256",
    "cve_id",
    "identifiers_json",
    "source_index",
    "vulnerability_entry_id",
    "source_entry_sha256",
    "ecosystem",
    "package_name",
    "vulnerable_version_range",
    "first_patched_version",
)

NVD_PROJECTION_COLUMNS: Final = (
    "cve_id",
    "observed_cve_version_id",
    "source_cve_sha256",
    "source_identifier",
    "published_at",
    "last_modified_at",
    "vuln_status",
)


class ProjectionMappingError(ValueError):
    """Raised when a result row cannot be read at all, as opposed to being unkeyable."""


@dataclass(frozen=True, slots=True)
class ProjectionRejection:
    """One source occurrence the index cannot key, and why.

    Attributes:
        package_name_original: The name exactly as the source wrote it.
        ghsa_id: The advisory the occurrence belongs to, when the row carried one.
        reason: Why the occurrence could not become a row.
    """

    package_name_original: str
    ghsa_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class GhsaProjectionOutcome:
    """Everything one GHSA projection pass produced, admitted and refused.

    Attributes:
        rows: The rows that can be stored and later rebuilt.
        rejected: The occurrences that cannot be keyed.
    """

    rows: tuple[ProjectedGhsaIndexRow, ...]
    rejected: tuple[ProjectionRejection, ...]

    @property
    def accounted_count(self) -> int:
        """Return how many source occurrences this pass accounted for."""
        return len(self.rows) + len(self.rejected)


def ghsa_projection_sql(database: str, table: str) -> str:
    """Build the query that feeds the GHSA-by-package index.

    Selects the latest observed version of each non-withdrawn advisory and unnests its
    vulnerability entries, emitting exactly the fields the index row carries. The
    package name is emitted raw: canonicalization is Python's job, deliberately.

    Args:
        database: The Glue database holding Silver.
        table: The GHSA Silver table.

    Returns:
        The SELECT statement.
    """
    return f'''
WITH ranked AS (
  SELECT ghsa_id, observed_advisory_version_id, source_advisory_sha256, cve_id,
         identifiers, is_withdrawn, vulnerabilities,
         ROW_NUMBER() OVER (PARTITION BY ghsa_id ORDER BY updated_at DESC) AS rn
  FROM "{database}"."{table}"
)
SELECT
  r.ghsa_id AS ghsa_id,
  r.observed_advisory_version_id AS observed_advisory_version_id,
  r.source_advisory_sha256 AS source_advisory_sha256,
  r.cve_id AS cve_id,
  json_format(cast(r.identifiers AS json)) AS identifiers_json,
  cast(v.source_index AS varchar) AS source_index,
  v.vulnerability_entry_id AS vulnerability_entry_id,
  v.source_entry_sha256 AS source_entry_sha256,
  v.ecosystem AS ecosystem,
  v.package_name AS package_name,
  v.vulnerable_version_range AS vulnerable_version_range,
  v.first_patched_version AS first_patched_version
FROM ranked r
CROSS JOIN UNNEST(r.vulnerabilities) AS t (v)
WHERE r.rn = 1 AND NOT r.is_withdrawn AND v.ecosystem = 'pip'
'''.strip()


def nvd_projection_sql(database: str, table: str, cve_ids: Sequence[str]) -> str:
    """Build the query that feeds the NVD-by-CVE index.

    Scoped to the CVEs the admitted GHSA rows actually name, because
    `PublicRepositoryThreatEvidence` refuses NVD records unrelated to scoped GHSA
    evidence. Projecting every CVE would store records the request path may not use.

    Args:
        database: The Glue database holding Silver.
        table: The NVD Silver table.
        cve_ids: The CVEs to project.

    Returns:
        The SELECT statement.

    Raises:
        ProjectionMappingError: If any identifier is not a plain CVE identifier, which
            would otherwise be interpolated into SQL.
    """
    for value in cve_ids:
        if not value or any(
            character not in "CVE-0123456789" for character in value
        ) or not value.startswith("CVE-"):
            raise ProjectionMappingError(f"{value!r} is not a CVE identifier")

    # An empty scope must select nothing rather than everything, so the IN list holds a
    # value no CVE identifier can equal.
    wanted = (
        ", ".join(f"'{value}'" for value in sorted(set(cve_ids))) if cve_ids else "''"
    )

    return f'''
WITH ranked AS (
  SELECT cve_id, observed_cve_version_id, source_cve_sha256, source_identifier,
         published_at, last_modified_at, vuln_status,
         ROW_NUMBER() OVER (PARTITION BY cve_id ORDER BY last_modified_at DESC) AS rn
  FROM "{database}"."{table}"
  WHERE cve_id IN ({wanted})
)
SELECT
  cve_id AS cve_id,
  observed_cve_version_id AS observed_cve_version_id,
  source_cve_sha256 AS source_cve_sha256,
  source_identifier AS source_identifier,
  published_at AS published_at,
  last_modified_at AS last_modified_at,
  vuln_status AS vuln_status
FROM ranked
WHERE rn = 1
'''.strip()


def _text(row: Mapping[str, str], column: str) -> str:
    """Read one required column.

    Args:
        row: The result row.
        column: The column name.

    Returns:
        The value.

    Raises:
        ProjectionMappingError: If the column is absent.
    """
    try:
        return row[column]
    except KeyError as exc:
        raise ProjectionMappingError(f"result row carries no {column}") from exc


def _optional(row: Mapping[str, str], column: str) -> str | None:
    """Read one column where the source writes emptiness to mean absence.

    ADR 0085 established this reading for GHSA passthrough fields: an empty value is a
    sparse source record, not a malformed one.

    Args:
        row: The result row.
        column: The column name.

    Returns:
        The value, or None when the source left it empty.
    """
    value = row.get(column)
    return value if value else None


def _identifiers(raw: str) -> tuple[ProjectedSourceIdentifier, ...]:
    """Read the advisory identifiers the query serialized as JSON.

    Args:
        raw: The `identifiers_json` column.

    Returns:
        The identifiers, in source order.

    Raises:
        ProjectionMappingError: If the column is not a JSON array of typed objects.
    """
    if not raw:
        return ()
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProjectionMappingError("identifiers_json is not JSON") from exc
    if not isinstance(decoded, list):
        raise ProjectionMappingError("identifiers_json must be a JSON array")

    identifiers: list[ProjectedSourceIdentifier] = []
    for item in decoded:  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(item, dict):
            raise ProjectionMappingError("each identifier must be a JSON object")
        entry: dict[str, object] = item  # pyright: ignore[reportUnknownVariableType]
        kind = entry.get("type")
        value = entry.get("value")
        if not isinstance(kind, str) or not isinstance(value, str):
            raise ProjectionMappingError("each identifier needs a string type and value")
        identifiers.append(ProjectedSourceIdentifier(identifier_type=kind, value=value))
    return tuple(identifiers)


def project_ghsa_rows(results: Sequence[Mapping[str, str]]) -> GhsaProjectionOutcome:
    """Map GHSA query results onto index rows, accounting for what cannot be keyed.

    Args:
        results: Result rows carrying `GHSA_PROJECTION_COLUMNS`.

    Returns:
        The admitted rows and the refused occurrences, together covering every input.

    Raises:
        ProjectionMappingError: If a row is missing a column or carries a non-integer
            source index — a query defect rather than a source one.
    """
    rows: list[ProjectedGhsaIndexRow] = []
    rejected: list[ProjectionRejection] = []

    for result in results:
        package_original = _text(result, "package_name")
        ghsa_id = _text(result, "ghsa_id")

        try:
            package = canonicalize_pypi_package(package_original)
        except InvalidPackageNameError as exc:
            rejected.append(
                ProjectionRejection(
                    package_name_original=package_original,
                    ghsa_id=ghsa_id,
                    reason=f"UNCANONICALIZABLE_PYPI_NAME: {exc}",
                )
            )
            continue

        raw_index = _text(result, "source_index")
        try:
            source_index = int(raw_index)
        except ValueError as exc:
            raise ProjectionMappingError(
                f"source_index {raw_index!r} is not an integer"
            ) from exc

        try:
            rows.append(
                ProjectedGhsaIndexRow(
                    package_name_canonical=package.canonical,
                    observed_advisory_version_id=_text(
                        result, "observed_advisory_version_id"
                    ),
                    source_advisory_sha256=_text(result, "source_advisory_sha256"),
                    source_entry_sha256=_text(result, "source_entry_sha256"),
                    ghsa_id=ghsa_id,
                    github_cve_id=_optional(result, "cve_id"),
                    github_identifiers=_identifiers(result.get("identifiers_json", "")),
                    vulnerability_entry_id=_text(result, "vulnerability_entry_id"),
                    source_index=source_index,
                    ecosystem_original=_text(result, "ecosystem"),
                    package_name_original=package_original,
                    vulnerable_range_original=_text(result, "vulnerable_version_range"),
                    first_patched_version_original=_optional(
                        result, "first_patched_version"
                    ),
                )
            )
        except CorrelationIndexContractError as exc:
            rejected.append(
                ProjectionRejection(
                    package_name_original=package_original,
                    ghsa_id=ghsa_id,
                    reason=f"UNSTORABLE_INDEX_ROW: {exc}",
                )
            )

    return GhsaProjectionOutcome(rows=tuple(rows), rejected=tuple(rejected))


def project_nvd_rows(
    results: Sequence[Mapping[str, str]],
) -> tuple[ProjectedNvdIndexRow, ...]:
    """Map NVD query results onto index rows.

    NVD carries no name normalization and therefore no unkeyable case: a row that fails
    the contract is a defect in the query or the source, not a package the index cannot
    address, so it raises rather than being counted as rejected.

    Args:
        results: Result rows carrying `NVD_PROJECTION_COLUMNS`.

    Returns:
        The projected rows.

    Raises:
        ProjectionMappingError: If a row is missing a column or fails the contract.
    """
    rows: list[ProjectedNvdIndexRow] = []
    for result in results:
        try:
            rows.append(
                ProjectedNvdIndexRow(
                    cve_id=_text(result, "cve_id"),
                    observed_cve_version_id=_text(result, "observed_cve_version_id"),
                    source_cve_sha256=_text(result, "source_cve_sha256"),
                    source_identifier=_text(result, "source_identifier"),
                    published_at=source_instant(
                        _text(result, "published_at"), field="published_at"
                    ),
                    last_modified_at=source_instant(
                        _text(result, "last_modified_at"), field="last_modified_at"
                    ),
                    vuln_status=_text(result, "vuln_status"),
                )
            )
        except CorrelationIndexContractError as exc:
            raise ProjectionMappingError(f"NVD result row is not storable: {exc}") from exc
    return tuple(rows)
