#!/usr/bin/env python3
"""Measure what a GHSA-by-package and NVD-by-CVE projection would actually cost.

Gate 20.1 builds the only projection the request path needs. Two things decide its
physical shape, and neither should be guessed:

    how many index rows, and how wide
    how hot the worst key is

This probes both against the real Silver tables, read only, and writes the answer as
retained evidence so the Gate 20.1 store decision is evidence-backed rather than a
preference.

Two constraints found while writing this, both worth knowing before running:

**The Athena workgroup enforces a 10 MiB scan cutoff per query**
(`bytes_scanned_cutoff_per_query = 10485760`, with
`enforce_workgroup_configuration = true`), so a query cannot raise it and this script
does not try. A query killed by the cutoff is recorded as `CUTOFF_EXCEEDED` and the run
continues: "this table is larger than the demonstration-scale cutoff" is a real
measurement, not a failure to handle.

**`ghsa_advisory_versions` is not partitioned**, so any query touching it reads the whole
table. `nvd_cve_versions` is partitioned by `source_kind_partition` and
`projection_date`. That asymmetry is most of the cost difference between the two halves.

So the sizing runs in two phases. Phase A lists the S3 objects behind each Glue table:
free, immune to the cutoff, and enough on its own to answer "how big is this". Phase B
asks Athena the shape questions that object sizes cannot answer — distinct packages, rows
per package, the hottest key — and reports the bytes each one scanned.

```text
READ, NEVER WRITE. This probe creates no table, no workgroup and no object.
projected index != source of truth
```
"""

import argparse
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Protocol, cast

from _bootstrap import ensure_repository_src_on_path
from boto3.session import Session

ensure_repository_src_on_path()

from opslens.semantic_query.config import SemanticQueryCatalog  # noqa: E402
from opslens.shared.evidence import canonical_json, canonical_sha256  # noqa: E402

CORRELATION_INDEX_PROBE_CONTRACT_VERSION: Final = "opslens-correlation-index-probe:v1"

_DEFAULT_REGION: Final = "us-east-1"
_DEFAULT_GHSA_TABLE: Final = "ghsa_advisory_versions"
_DEFAULT_NVD_TABLE: Final = "nvd_cve_versions"
# The cutoff is read from the workgroup rather than written down here. A probe that
# asserts a number the workgroup no longer carries reports a bound that is not the one
# in force, which is the same failure as measuring nothing and calling it zero.
#
#     declared constant != configuration in force

_TERMINAL_STATES: Final = frozenset({"SUCCEEDED", "FAILED", "CANCELLED"})
_POLL_SECONDS: Final = 2.0
_MAX_POLLS: Final = 90
_EMPTY_MAPPING: Final[Mapping[str, object]] = {}
_MAX_RESULT_ROWS: Final = 25
# Below this many PyPI index rows the GHSA corpus is fixture or partial-ingestion
# scale, not a real advisory corpus. A heuristic, reported as one.
_PLAUSIBLE_GHSA_INDEX_ROWS: Final = 100


class ProbeError(RuntimeError):
    """Raised when the probe cannot complete a measurement it was asked for."""


class _StsClient(Protocol):
    """Only the STS operation this probe needs."""

    def get_caller_identity(self) -> Mapping[str, object]:
        """Return the calling identity."""
        ...


class _GlueClient(Protocol):
    """Only the Glue operation this probe needs."""

    def get_table(self, *, DatabaseName: str, Name: str) -> Mapping[str, object]:
        """Return one table definition."""
        ...


class _S3Paginator(Protocol):
    """Only the S3 pagination surface this probe needs."""

    def paginate(self, *, Bucket: str, Prefix: str) -> Iterable[Mapping[str, object]]:
        """Yield object listing pages."""
        ...


class _S3Client(Protocol):
    """Only the S3 operation this probe needs."""

    def get_paginator(self, operation_name: str) -> _S3Paginator:
        """Return a paginator for one listing operation."""
        ...


class _AthenaClient(Protocol):
    """Only the read-only Athena operations this probe needs."""

    def start_query_execution(
        self,
        *,
        QueryString: str,
        QueryExecutionContext: Mapping[str, str],
        WorkGroup: str,
    ) -> Mapping[str, object]:
        """Start one measurement query."""
        ...

    def get_query_execution(self, *, QueryExecutionId: str) -> Mapping[str, object]:
        """Return status and statistics for one execution."""
        ...

    def get_work_group(self, *, WorkGroup: str) -> Mapping[str, object]:
        """Return the workgroup's own configuration."""
        ...

    def get_query_results(
        self,
        *,
        QueryExecutionId: str,
        MaxResults: int,
    ) -> Mapping[str, object]:
        """Return one bounded page of results."""
        ...


@dataclass(frozen=True, slots=True)
class StorageMeasurement:
    """Compressed footprint of one Glue table's S3 prefix.

    Attributes:
        table: Glue table name.
        location: The `s3://` prefix the table reads from.
        object_count: Objects under that prefix.
        compressed_bytes: Total size of those objects.
        largest_object_bytes: Size of the largest single object.
        distinct_partition_prefixes: Distinct `key=value/` prefixes observed.
    """

    table: str
    location: str
    object_count: int
    compressed_bytes: int
    largest_object_bytes: int
    distinct_partition_prefixes: int


@dataclass(frozen=True, slots=True)
class QueryMeasurement:
    """One Athena measurement and what it cost to take.

    Attributes:
        label: Stable identifier for the question asked.
        state: `SUCCEEDED`, `CUTOFF_EXCEEDED`, or another terminal Athena state.
        scanned_bytes: Bytes Athena reported scanning.
        elapsed_ms: Engine execution time, when Athena reported it.
        columns: Result column names, empty when the query did not succeed.
        rows: Result rows, empty when the query did not succeed.
        detail: Athena's state-change reason, when it supplied one.
    """

    label: str
    state: str
    scanned_bytes: int
    elapsed_ms: int | None
    columns: tuple[str, ...] = ()
    rows: tuple[tuple[str | None, ...], ...] = ()
    detail: str | None = None

    @property
    def succeeded(self) -> bool:
        """Report whether this measurement produced a result."""
        return self.state == "SUCCEEDED"

    def value(self, column: str) -> str | None:
        """Return one named value from the first result row, or None when unavailable.

        Args:
            column: Result column name.

        Returns:
            The value, or None when the query did not succeed or lacks the column.
        """
        if not self.succeeded or column not in self.columns or not self.rows:
            return None
        return self.rows[0][self.columns.index(column)]

    def integer(self, column: str) -> int | None:
        """Return one named value parsed as an integer, or None when unusable."""
        raw = self.value(column)
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError:
            return None


@dataclass(frozen=True, slots=True)
class CallerIdentity:
    """Who took the measurement, without carrying a personal session name.

    Attributes:
        account_id: The AWS account the measurement was taken in.
        role: The assumed role name, with any session name deliberately dropped.
    """

    account_id: str
    role: str


def _caller_identity(session: Session, region: str, profile: str | None) -> CallerIdentity:
    """Confirm credentials before any measurement, and record who is measuring.

    Failing here rather than inside the first Glue call turns "Unable to locate
    credentials" into an instruction.

    Args:
        session: boto3 session to check.
        region: AWS Region for the STS client.
        profile: The profile the operator asked for, for the error message.

    Returns:
        The account and role taking the measurement.

    Raises:
        ProbeError: If no usable credentials are available.
    """
    client = cast(
        _StsClient,
        session.client("sts", region_name=region),  # pyright: ignore[reportUnknownMemberType]
    )
    try:
        identity = client.get_caller_identity()
    except Exception as exc:
        named = profile or "<none supplied>"
        raise ProbeError(
            f"no usable AWS credentials (profile: {named}): {exc}\n"
            "This repository authenticates through IAM Identity Center. Try:\n"
            "  aws sso login --profile opslens-bootstrap\n"
            "  aws sts get-caller-identity --profile opslens-bootstrap\n"
            "then re-run with --profile opslens-bootstrap "
            "(or export AWS_PROFILE=opslens-bootstrap)."
        ) from exc

    account = identity.get("Account")
    arn = identity.get("Arn")
    if not isinstance(account, str) or not isinstance(arn, str):
        raise ProbeError("STS returned no usable caller identity")
    # arn:aws:sts::<account>:assumed-role/<role>/<session name>. The session name is
    # frequently the operator's email address, and this evidence may be committed, so
    # only the role is kept.
    parts = arn.split("/")
    role = parts[1] if len(parts) >= 2 else arn.rsplit(":", 1)[-1]
    return CallerIdentity(account_id=account, role=role)


@dataclass(slots=True)
class ProbeRun:
    """Accumulated measurements for one probe execution."""

    storage: list[StorageMeasurement] = field(default_factory=list[StorageMeasurement])
    queries: list[QueryMeasurement] = field(default_factory=list[QueryMeasurement])


def _glue_table_location(session: Session, region: str, database: str, table: str) -> str:
    """Read one Glue table's S3 location instead of hardcoding a bucket.

    Args:
        session: Authenticated boto3 session.
        region: AWS Region holding the Glue catalog.
        database: Glue database name.
        table: Glue table name.

    Returns:
        The `s3://bucket/prefix` location the table reads from.

    Raises:
        ProbeError: If the table is missing or declares no location.
    """
    client = cast(
        _GlueClient,
        session.client("glue", region_name=region),  # pyright: ignore[reportUnknownMemberType]
    )
    try:
        response = client.get_table(DatabaseName=database, Name=table)
    except Exception as exc:
        raise ProbeError(f"could not read Glue table {database}.{table}: {exc}") from exc

    table_value = response.get("Table")
    if not isinstance(table_value, Mapping):
        raise ProbeError(f"Glue returned no table object for {database}.{table}")
    descriptor = cast(Mapping[str, object], table_value).get("StorageDescriptor")
    if not isinstance(descriptor, Mapping):
        raise ProbeError(f"{database}.{table} declares no storage descriptor")
    location = cast(Mapping[str, object], descriptor).get("Location")
    if not isinstance(location, str) or not location.startswith("s3://"):
        raise ProbeError(f"{database}.{table} declares no usable S3 location")
    return location


def _measure_storage(
    session: Session,
    region: str,
    table: str,
    location: str,
) -> StorageMeasurement:
    """List every object under a table's prefix and total its compressed size.

    This is the only measurement immune to the workgroup scan cutoff, so it runs first
    and always.

    Args:
        session: Authenticated boto3 session.
        region: AWS Region holding the bucket.
        table: Glue table name, for the report.
        location: The table's `s3://bucket/prefix` location.

    Returns:
        The table's compressed footprint.

    Raises:
        ProbeError: If the objects cannot be listed.
    """
    remainder = location.removeprefix("s3://")
    bucket, _, prefix = remainder.partition("/")
    client = cast(
        _S3Client,
        session.client("s3", region_name=region),  # pyright: ignore[reportUnknownMemberType]
    )

    object_count = 0
    compressed_bytes = 0
    largest = 0
    partition_prefixes: set[str] = set()

    try:
        pages = client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix)
        for page in pages:
            contents = page.get("Contents")
            if not isinstance(contents, list):
                continue
            for item in cast(list[Mapping[str, object]], contents):
                size = item.get("Size")
                key = item.get("Key")
                if not isinstance(size, int) or not isinstance(key, str):
                    continue
                object_count += 1
                compressed_bytes += size
                largest = max(largest, size)
                directory = key.rsplit("/", 1)[0]
                if "=" in directory:
                    partition_prefixes.add(directory)
    except Exception as exc:
        raise ProbeError(f"could not list s3://{bucket}/{prefix}: {exc}") from exc

    return StorageMeasurement(
        table=table,
        location=location,
        object_count=object_count,
        compressed_bytes=compressed_bytes,
        largest_object_bytes=largest,
        distinct_partition_prefixes=len(partition_prefixes),
    )


@dataclass(frozen=True, slots=True)
class WorkgroupBound:
    """What the workgroup actually enforces, read rather than assumed.

    Attributes:
        name: The workgroup addressed.
        scan_cutoff_bytes: Its per-query scan ceiling, or None when it sets none.
        configuration_enforced: Whether a client may override that ceiling.
    """

    name: str
    scan_cutoff_bytes: int | None
    configuration_enforced: bool


def read_workgroup_bound(client: _AthenaClient, workgroup: str) -> WorkgroupBound:
    """Read the scan ceiling the workgroup enforces.

    Args:
        client: The Athena client.
        workgroup: The workgroup to describe.

    Returns:
        What that workgroup enforces.

    Raises:
        ProbeError: If the workgroup cannot be described.
    """
    try:
        described = client.get_work_group(WorkGroup=workgroup)
    except Exception as exc:
        raise ProbeError(f"could not describe workgroup {workgroup}: {exc}") from exc

    group = described.get("WorkGroup")
    configuration: Mapping[str, object] = {}
    if isinstance(group, dict):
        candidate = cast(Mapping[str, object], group).get("Configuration")
        if isinstance(candidate, dict):
            configuration = cast(Mapping[str, object], candidate)

    cutoff = configuration.get("BytesScannedCutoffPerQuery")
    enforced = configuration.get("EnforceWorkGroupConfiguration")
    return WorkgroupBound(
        name=workgroup,
        scan_cutoff_bytes=cutoff if type(cutoff) is int else None,
        configuration_enforced=enforced is True,
    )


def _run_query(
    session: Session,
    region: str,
    catalog: SemanticQueryCatalog,
    *,
    label: str,
    sql: str,
) -> QueryMeasurement:
    """Execute one bounded read-only measurement query and record what it cost.

    A query killed by the workgroup scan cutoff is recorded rather than raised: the
    cutoff firing is itself a measurement.

    Args:
        session: Authenticated boto3 session.
        region: AWS Region holding the workgroup.
        catalog: Database and workgroup to address.
        label: Stable identifier for the question.
        sql: The SELECT statement to run.

    Returns:
        The measurement, successful or not.

    Raises:
        ProbeError: If Athena cannot be reached or the query never reaches a terminal
            state within the polling bound.
    """
    client = cast(
        _AthenaClient,
        session.client("athena", region_name=region),  # pyright: ignore[reportUnknownMemberType]
    )

    started = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": catalog.database},
        WorkGroup=catalog.workgroup,
    )
    execution_id = started.get("QueryExecutionId")
    if not isinstance(execution_id, str):
        raise ProbeError(f"Athena returned no execution id for {label}")

    for _ in range(_MAX_POLLS):
        response = client.get_query_execution(QueryExecutionId=execution_id)
        execution = response.get("QueryExecution")
        if not isinstance(execution, Mapping):
            raise ProbeError(f"Athena returned no execution object for {label}")
        execution_map = cast(Mapping[str, object], execution)
        status = execution_map.get("Status")
        status_map: Mapping[str, object] = (
            cast(Mapping[str, object], status) if isinstance(status, Mapping) else _EMPTY_MAPPING
        )
        state = status_map.get("State")
        if not isinstance(state, str):
            raise ProbeError(f"Athena returned no state for {label}")
        if state not in _TERMINAL_STATES:
            time.sleep(_POLL_SECONDS)
            continue

        statistics = execution_map.get("Statistics")
        statistics_map: Mapping[str, object] = (
            cast(Mapping[str, object], statistics)
            if isinstance(statistics, Mapping)
            else _EMPTY_MAPPING
        )
        scanned = statistics_map.get("DataScannedInBytes")
        elapsed = statistics_map.get("EngineExecutionTimeInMillis")
        reason = status_map.get("StateChangeReason")
        detail = reason if isinstance(reason, str) else None

        if state != "SUCCEEDED":
            cutoff = detail is not None and "cutoff" in detail.lower()
            return QueryMeasurement(
                label=label,
                state="CUTOFF_EXCEEDED" if cutoff else state,
                scanned_bytes=scanned if isinstance(scanned, int) else 0,
                elapsed_ms=elapsed if isinstance(elapsed, int) else None,
                detail=detail,
            )

        page = client.get_query_results(
            QueryExecutionId=execution_id,
            MaxResults=_MAX_RESULT_ROWS + 1,
        )
        columns, rows = _parse_rows(page)
        return QueryMeasurement(
            label=label,
            state="SUCCEEDED",
            scanned_bytes=scanned if isinstance(scanned, int) else 0,
            elapsed_ms=elapsed if isinstance(elapsed, int) else None,
            columns=columns,
            rows=rows,
            detail=None,
        )

    raise ProbeError(f"{label} did not reach a terminal state within the polling bound")


def _parse_rows(
    page: Mapping[str, object],
) -> tuple[tuple[str, ...], tuple[tuple[str | None, ...], ...]]:
    """Read the bounded result rows and their column names.

    Args:
        page: One `GetQueryResults` response.

    Returns:
        The column names and every data row after the header row.
    """
    result_set = page.get("ResultSet")
    if not isinstance(result_set, Mapping):
        return (), ()
    result_map = cast(Mapping[str, object], result_set)
    metadata = result_map.get("ResultSetMetadata")
    columns: tuple[str, ...] = ()
    if isinstance(metadata, Mapping):
        column_info = cast(Mapping[str, object], metadata).get("ColumnInfo")
        if isinstance(column_info, list):
            columns = tuple(
                str(cast(Mapping[str, object], item).get("Name", ""))
                for item in cast(list[object], column_info)
                if isinstance(item, Mapping)
            )
    raw_rows = result_map.get("Rows")
    if not isinstance(raw_rows, list) or len(cast(list[object], raw_rows)) < 2:
        return columns, ()
    parsed: list[tuple[str | None, ...]] = []
    for data_row in cast(list[Mapping[str, object]], raw_rows)[1:]:
        data = data_row.get("Data")
        if not isinstance(data, list):
            continue
        values: list[str | None] = []
        for datum in cast(list[object], data):
            if not isinstance(datum, Mapping):
                values.append(None)
                continue
            raw = cast(Mapping[str, object], datum).get("VarCharValue")
            values.append(raw if isinstance(raw, str) else None)
        parsed.append(tuple(values))
    return columns, tuple(parsed)


def _ghsa_shape_sql(database: str, table: str) -> str:
    """Build the GHSA index-shape query.

    Counts only what the projection would actually store: the fields
    `GhsaPyPIVulnerabilityEvidence` needs, for the latest observed version of each
    non-withdrawn advisory, unnested to one row per (package, advisory) pair.
    """
    return f'''
WITH ranked AS (
  SELECT ghsa_id, cve_id, is_withdrawn, vulnerabilities,
         ROW_NUMBER() OVER (PARTITION BY ghsa_id ORDER BY updated_at DESC) AS rn
  FROM "{database}"."{table}"
),
pairs AS (
  SELECT
    lower(regexp_replace(v.package_name, '[-_.]+', '-')) AS package,
    r.ghsa_id,
    r.cve_id,
    length(coalesce(v.package_name, ''))
      + length(coalesce(v.vulnerable_version_range, ''))
      + length(coalesce(v.first_patched_version, ''))
      + length(coalesce(v.vulnerability_entry_id, ''))
      + length(coalesce(v.source_entry_sha256, ''))
      + length(r.ghsa_id) + 96 AS projected_bytes
  FROM ranked r
  CROSS JOIN UNNEST(r.vulnerabilities) AS t (v)
  WHERE r.rn = 1 AND NOT r.is_withdrawn AND v.ecosystem = 'pip'
)
SELECT
  count(*) AS index_rows,
  count(DISTINCT package) AS distinct_packages,
  count(DISTINCT ghsa_id) AS distinct_advisories,
  count(DISTINCT cve_id) AS distinct_cves,
  sum(projected_bytes) AS projected_bytes_total,
  max(projected_bytes) AS projected_bytes_max_row
FROM pairs
'''.strip()


def _ghsa_hot_key_sql(database: str, table: str) -> str:
    """Build the per-package distribution query, which decides hot-key risk."""
    return f'''
WITH ranked AS (
  SELECT ghsa_id, is_withdrawn, vulnerabilities,
         ROW_NUMBER() OVER (PARTITION BY ghsa_id ORDER BY updated_at DESC) AS rn
  FROM "{database}"."{table}"
),
pairs AS (
  SELECT lower(regexp_replace(v.package_name, '[-_.]+', '-')) AS package
  FROM ranked r
  CROSS JOIN UNNEST(r.vulnerabilities) AS t (v)
  WHERE r.rn = 1 AND NOT r.is_withdrawn AND v.ecosystem = 'pip'
),
per_package AS (
  SELECT package, count(*) AS advisories FROM pairs GROUP BY package
)
SELECT
  cast(approx_percentile(advisories, 0.5) AS varchar) AS p50_advisories_per_package,
  cast(approx_percentile(advisories, 0.95) AS varchar) AS p95_advisories_per_package,
  cast(max(advisories) AS varchar) AS max_advisories_per_package
FROM per_package
'''.strip()


def _ghsa_hot_key_identity_sql(database: str, table: str) -> str:
    """Name the packages behind the per-package distribution.

    `ghsa_hot_key` reports a maximum without saying which package carries it, and a
    skew that extreme has two very different explanations. A package with a genuinely
    long advisory history is a schema constraint: one DynamoDB item per package would
    exceed the 400 KB item limit, forcing an item per (package, advisory) pair. An
    empty or absent `package_name` collapsing every such entry onto one normalized key
    is a measurement artifact, and designing a limit around it would bound the request
    path against a package that does not exist.

    ```text
    a maximum != the thing carrying it
    ```

    The same filters as `ghsa_hot_key` and `ghsa_shape`, so the counts are comparable
    rather than merely similar. Empty names are deliberately not filtered out: whether
    they exist is the question.
    """
    return f'''
WITH ranked AS (
  SELECT ghsa_id, is_withdrawn, vulnerabilities,
         ROW_NUMBER() OVER (PARTITION BY ghsa_id ORDER BY updated_at DESC) AS rn
  FROM "{database}"."{table}"
),
pairs AS (
  SELECT
    lower(regexp_replace(coalesce(v.package_name, ''), '[-_.]+', '-')) AS package,
    length(coalesce(v.package_name, '')) AS name_length
  FROM ranked r
  CROSS JOIN UNNEST(r.vulnerabilities) AS t (v)
  WHERE r.rn = 1 AND NOT r.is_withdrawn AND v.ecosystem = 'pip'
)
SELECT
  CASE WHEN package = '' THEN '(empty package name)' ELSE package END AS package,
  cast(count(*) AS varchar) AS advisories,
  cast(min(name_length) AS varchar) AS shortest_source_name
FROM pairs
GROUP BY package
ORDER BY count(*) DESC
LIMIT 6
'''.strip()


def _ghsa_census_sql(database: str, table: str) -> str:
    """Build the GHSA corpus census.

    Sizing is meaningless if the source is empty, so this asks what is actually in the
    table before anything asks how to store a projection of it.
    """
    return f'''
SELECT
  count(*) AS row_count,
  count(DISTINCT ghsa_id) AS distinct_advisories,
  sum(CASE WHEN is_withdrawn THEN 1 ELSE 0 END) AS withdrawn_rows,
  sum(vulnerability_entry_count) AS vulnerability_entries
FROM "{database}"."{table}"
'''.strip()


def _ghsa_ecosystem_sql(database: str, table: str) -> str:
    """Break the GHSA corpus down by ecosystem.

    Distinguishes "no PyPI advisories ingested" from "the pip filter is wrong", which
    look identical in the shape query.
    """
    return f'''
SELECT v.ecosystem AS ecosystem, count(*) AS entries
FROM "{database}"."{table}" r
CROSS JOIN UNNEST(r.vulnerabilities) AS t (v)
GROUP BY v.ecosystem
ORDER BY entries DESC
'''.strip()


def _nvd_partition_sql(database: str, table: str) -> str:
    """Count distinct CVEs per NVD source partition.

    Shows whether the NVD corpus is a complete load or a bootstrap subset.
    """
    return f'''
SELECT source_kind_partition AS source_kind, count(DISTINCT cve_id) AS distinct_cves
FROM "{database}"."{table}"
GROUP BY source_kind_partition
ORDER BY distinct_cves DESC
'''.strip()


def _nvd_shape_sql(database: str, table: str) -> str:
    """Build the NVD index-shape query.

    The port needs five scalar fields per CVE, so this reads only those columns. On a
    columnar table that is a far narrower read than the GHSA query.
    """
    return f'''
WITH ranked AS (
  SELECT cve_id, source_identifier, vuln_status,
         ROW_NUMBER() OVER (PARTITION BY cve_id ORDER BY last_modified_at DESC) AS rn
  FROM "{database}"."{table}"
)
SELECT
  count(*) AS distinct_cves,
  sum(length(cve_id)
      + length(coalesce(source_identifier, ''))
      + length(coalesce(vuln_status, '')) + 64) AS projected_bytes_total
FROM ranked
WHERE rn = 1
'''.strip()


def _measurements(
    database: str,
    ghsa_table: str,
    nvd_table: str,
) -> tuple[tuple[str, str], ...]:
    """Return every measurement, census first.

    Census before shape is deliberate: a store decision taken from a shape query over
    an empty table is a decision taken from nothing.
    """
    return (
        ("ghsa_census", _ghsa_census_sql(database, ghsa_table)),
        ("ghsa_ecosystems", _ghsa_ecosystem_sql(database, ghsa_table)),
        ("ghsa_shape", _ghsa_shape_sql(database, ghsa_table)),
        ("ghsa_hot_key", _ghsa_hot_key_sql(database, ghsa_table)),
        ("ghsa_hot_key_identity", _ghsa_hot_key_identity_sql(database, ghsa_table)),
        ("nvd_partitions", _nvd_partition_sql(database, nvd_table)),
        ("nvd_shape", _nvd_shape_sql(database, nvd_table)),
    )


def _assess(run: ProbeRun) -> dict[str, object]:
    """Say plainly whether these measurements can support a store decision.

    A sizing probe that reports two rows without flagging that two is implausible for
    a real GHSA PyPI corpus is a probe that lets someone build on sand.
    """
    by_label = {item.label: item for item in run.queries}
    shape = by_label.get("ghsa_shape")
    index_rows = shape.integer("index_rows") if shape is not None else None

    if index_rows is None:
        return {
            "ghsa_corpus_sufficient_for_sizing": False,
            "reason": "the GHSA shape measurement did not complete",
            "ghsa_index_rows": None,
        }
    if index_rows < _PLAUSIBLE_GHSA_INDEX_ROWS:
        return {
            "ghsa_corpus_sufficient_for_sizing": False,
            "reason": (
                f"{index_rows} PyPI index rows is fixture or partial-ingestion scale, "
                "not a real GHSA advisory corpus; a store decision taken from this "
                "number would be a decision taken from nothing, and an endpoint "
                "correlating against it would report no known vulnerabilities for "
                "almost every real repository"
            ),
            "ghsa_index_rows": index_rows,
            "heuristic_threshold": _PLAUSIBLE_GHSA_INDEX_ROWS,
        }
    return {
        "ghsa_corpus_sufficient_for_sizing": True,
        "reason": "the GHSA PyPI corpus is large enough for the numbers to mean something",
        "ghsa_index_rows": index_rows,
    }


def _parser() -> argparse.ArgumentParser:
    """Build the probe's command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Measure the GHSA-by-package and NVD-by-CVE projection before Gate 20.1 "
            "picks a store. Read-only; creates nothing."
        ),
    )
    parser.add_argument("--region", default=_DEFAULT_REGION, help="AWS Region (default: us-east-1)")
    parser.add_argument("--profile", default=None, help="Optional local AWS profile")
    parser.add_argument("--ghsa-table", default=_DEFAULT_GHSA_TABLE, help="GHSA Silver table")
    parser.add_argument("--nvd-table", default=_DEFAULT_NVD_TABLE, help="NVD Silver table")
    parser.add_argument(
        "--storage-only",
        action="store_true",
        help="run only the free S3 sizing and skip every Athena query",
    )
    parser.add_argument(
        "--print-sql",
        action="store_true",
        help="print the measurement SQL and exit without touching AWS",
    )
    parser.add_argument(
        "--format", dest="output_format", choices=("text", "json"), default="text",
        help="reviewer output projection",
    )
    parser.add_argument(
        "--workgroup", default=None,
        help=(
            "Athena workgroup to measure in; defaults to the configured one. The "
            "projection workgroup is bounded well above the request path, because a "
            "projection is built from a full corpus scan by design."
        ),
    )
    parser.add_argument("--output", default=None, help="also write canonical JSON evidence here")
    return parser


def _payload(
    run: ProbeRun,
    *,
    catalog: SemanticQueryCatalog,
    region: str,
    ghsa_table: str,
    nvd_table: str,
    identity: CallerIdentity,
    bound: WorkgroupBound,
) -> dict[str, object]:
    """Project the run as a content-addressable payload."""
    payload: dict[str, object] = {
        "contract_version": CORRELATION_INDEX_PROBE_CONTRACT_VERSION,
        "authority": {
            "read_only": True,
            "creates_infrastructure": False,
            "workgroup_scan_cutoff_bytes": bound.scan_cutoff_bytes,
            "workgroup_configuration_enforced": bound.configuration_enforced,
        },
        "measured_by": {
            "account_id": identity.account_id,
            "role": identity.role,
        },
        "target": {
            "region": region,
            "database": catalog.database,
            "workgroup": catalog.workgroup,
            "ghsa_table": ghsa_table,
            "nvd_table": nvd_table,
        },
        "storage": [
            {
                "table": item.table,
                "location": item.location,
                "object_count": item.object_count,
                "compressed_bytes": item.compressed_bytes,
                "largest_object_bytes": item.largest_object_bytes,
                "distinct_partition_prefixes": item.distinct_partition_prefixes,
            }
            for item in run.storage
        ],
        "queries": [
            {
                "label": item.label,
                "state": item.state,
                "scanned_bytes": item.scanned_bytes,
                "elapsed_ms": item.elapsed_ms,
                "rows": [
                    dict(zip(item.columns, row, strict=False)) for row in item.rows
                ],
                "detail": item.detail,
            }
            for item in run.queries
        ],
    }
    payload["assessment"] = _assess(run)
    payload["probe_id"] = (
        f"{CORRELATION_INDEX_PROBE_CONTRACT_VERSION}@sha256:{canonical_sha256(payload)}"
    )
    return payload


def _render_cutoff(authority: Mapping[str, object]) -> str:
    """Render the scan ceiling the workgroup reported, without inventing one."""
    cutoff = authority.get("workgroup_scan_cutoff_bytes")
    enforced = "enforced" if authority.get("workgroup_configuration_enforced") else "overridable"
    if type(cutoff) is not int:
        return f"none declared ({enforced})"
    return f"{cutoff / (1024 * 1024):.0f} MiB ({enforced})"


def _render_text(payload: dict[str, object]) -> str:
    """Render one reviewer-facing summary."""
    target = cast(Mapping[str, object], payload["target"])
    measured = cast(Mapping[str, object], payload["measured_by"])
    authority = cast(Mapping[str, object], payload["authority"])
    lines = [
        "OpsLens correlation index sizing probe",
        f"region: {target['region']}  database: {target['database']}  "
        f"workgroup: {target['workgroup']}",
        f"measured by: account {measured['account_id']} as {measured['role']}",
        f"measured at: {datetime.now(UTC).isoformat(timespec='seconds')}",
        f"scan cutoff in force: {_render_cutoff(authority)}",
        "",
        "storage (free, immune to the workgroup scan cutoff)",
    ]
    for item in cast(list[Mapping[str, object]], payload["storage"]):
        compressed = cast(int, item["compressed_bytes"])
        lines.append(
            f"  {item['table']:<24} {item['object_count']:>7} objects  "
            f"{compressed / 1_048_576:>10.1f} MiB  "
            f"{item['distinct_partition_prefixes']:>5} partition prefixes"
        )

    queries = cast(list[Mapping[str, object]], payload["queries"])
    if queries:
        lines.extend(("", "measurements"))
        for item in queries:
            scanned = cast(int, item["scanned_bytes"])
            lines.append(
                f"  {item['label']:<28} {item['state']:<16} "
                f"scanned {scanned / 1_048_576:>8.2f} MiB"
            )
            for row in cast(list[Mapping[str, object]], item["rows"]):
                rendered = "  ".join(f"{key}={value}" for key, value in sorted(row.items()))
                lines.append(f"      {rendered}")
            detail = item.get("detail")
            if detail:
                lines.append(f"      detail: {detail}")

    assessment = cast(Mapping[str, object], payload["assessment"])
    sufficient = bool(assessment["ghsa_corpus_sufficient_for_sizing"])
    lines.extend((
        "",
        "assessment",
        f"  GHSA corpus sufficient for a store decision: {'yes' if sufficient else 'NO'}",
        f"  {assessment['reason']}",
        "",
        f"probe: {payload['probe_id']}",
        "authority: read-only measurement; creates no table, workgroup or object",
        "scope: sizing evidence for Gate 20.1, not a projection",
    ))
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the probe and emit one reviewer projection.

    Args:
        argv: Command-line arguments, or None to read `sys.argv`.

    Returns:
        0 when every requested measurement was taken or explicitly recorded as
        cut off, 2 when the probe could not run at all.
    """
    namespace = _parser().parse_args(list(argv) if argv is not None else None)
    catalog = SemanticQueryCatalog.from_environment()
    workgroup_override = cast(str | None, namespace.workgroup)
    if workgroup_override is not None:
        catalog = replace(catalog, workgroup=workgroup_override)
    ghsa_table = cast(str, namespace.ghsa_table)
    nvd_table = cast(str, namespace.nvd_table)
    region = cast(str, namespace.region)

    if cast(bool, namespace.print_sql):
        for label, sql in _measurements(catalog.database, ghsa_table, nvd_table):
            sys.stdout.write(f"-- {label}\n{sql}\n\n")
        return 0

    profile = cast(str | None, namespace.profile)
    session = Session(profile_name=profile)
    run = ProbeRun()

    try:
        identity = _caller_identity(session, region, profile)
        bound = read_workgroup_bound(
            cast(
                _AthenaClient,
                session.client("athena", region_name=region),  # pyright: ignore[reportUnknownMemberType]
            ),
            catalog.workgroup,
        )
        for table in (ghsa_table, nvd_table):
            location = _glue_table_location(session, region, catalog.database, table)
            run.storage.append(_measure_storage(session, region, table, location))

        if not cast(bool, namespace.storage_only):
            for label, sql in _measurements(catalog.database, ghsa_table, nvd_table):
                run.queries.append(
                    _run_query(session, region, catalog, label=label, sql=sql)
                )
    except ProbeError as exc:
        print(f"correlation index probe rejected: {exc}", file=sys.stderr)
        return 2

    payload = _payload(
        run,
        catalog=catalog,
        region=region,
        ghsa_table=ghsa_table,
        nvd_table=nvd_table,
        identity=identity,
        bound=bound,
    )

    output = cast(str | None, namespace.output)
    if output is not None:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json(payload) + b"\n")

    if cast(str, namespace.output_format) == "json":
        sys.stdout.write(canonical_json(payload).decode("utf-8") + "\n")
    else:
        sys.stdout.write(_render_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
