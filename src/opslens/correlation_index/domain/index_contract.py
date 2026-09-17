"""Shape and identity of the derived correlation index, before anything builds one.

The public request path cannot answer "what applies to these packages" from Silver.
Silver is 35,584 Parquet objects averaging 21 KiB, partitioned by advisory id, so the
question costs a corpus scan (ADR 0086). The answer is a projection keyed by what the
request actually asks about: GHSA by normalized package name, NVD by CVE.

Two properties make this contract worth its own module rather than living inside the
projector that writes it.

**A row that the authority would reject must not be storable.** `GhsaPyPIVulnerabilityEvidence`
is what `PublicThreatEvidenceAuthority` returns, and `PublicRepositoryThreatEvidence`
validates every item it receives: exact lowercase source hashes, and an observed version
identity that agrees with the advisory hash. If the index could hold a row failing those
checks, the failure would surface at request time, on the public path, as a rejected
analysis for a repository that did nothing wrong. So the same rules are enforced here,
at write time, where the operator sees them.

```text
rejected at write != rejected at request
```

**A projection is dated, and says so.** It is built from sources at a moment, and
"no known vulnerabilities" is only true as of that moment. The manifest therefore carries
its own content-addressed identity, the instant it was built, and a watermark per source,
so every response can name the index that answered it and how old that index was.

```text
projected index != source of truth
stale index != current answer
```

This module describes and validates. It reads nothing and writes nothing.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from opslens.shared.evidence import canonical_json, evidence_id, sha256_hex

# v1 took the index identity over counts, watermarks and `built_at`. Counts do not
# distinguish content — two indexes holding entirely different rows in the same quantity
# derived the same identity, and therefore the same key space — while `built_at` made
# every re-run of identical content a new generation. v2 digests the rows and drops
# `built_at` from the identity, which makes both halves of ADR 0088 true. A v1 digest
# must never silently match a v2 manifest, so the version moves.
CORRELATION_INDEX_CONTRACT_VERSION: Final = "opslens-correlation-index:v2"

_SHA256_RE: Final = re.compile(r"[0-9a-f]{64}")
_CVE_RE: Final = re.compile(r"CVE-[0-9]{4}-[0-9]{4,}")
_GHSA_RE: Final = re.compile(r"GHSA(?:-[23456789cfghjmpqrvwx]{4}){3}")
_TIMESTAMP_FORMAT: Final = "%Y-%m-%dT%H:%M:%SZ"
_INSTANT_RE: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
# One occurrence is identified by (observed advisory version, source index), the same
# pair `PublicRepositoryThreatEvidence` refuses to see twice. Zero-padding keeps the
# sort key ordered as text, which is the only ordering a key-value store gives.
_SOURCE_INDEX_WIDTH: Final = 6
# ADR 0088: the build generation prefixes every partition key, so a build writes into a
# key space nothing is reading. 16 hex characters of the manifest digest: long enough
# that two live generations cannot collide, short enough to stay cheap on every key.
_GENERATION_WIDTH: Final = 16
# `#` cannot appear in a canonical PyPI name or a CVE identifier, so it cannot be
# smuggled in to address another generation's key space.
_KEY_SEPARATOR: Final = "#"
_MAX_SOURCE_INDEX: Final = 10**_SOURCE_INDEX_WIDTH - 1


class CorrelationIndexContractError(ValueError):
    """Raised when a projected row or manifest would not survive the request path."""


def index_generation(index_id: str) -> str:
    """Derive the key-space generation one build writes into.

    ADR 0088 puts the generation in the partition key so a build writes where nothing
    is reading. It is the manifest digest truncated, not a counter: two builds of
    identical content land in the same key space, so a re-run is idempotent instead of
    producing a second generation of the same thing.

    Args:
        index_id: The manifest identity, `<contract>@sha256:<digest>`.

    Returns:
        The generation prefix.

    Raises:
        CorrelationIndexContractError: If the identity carries no sha-256 digest.
    """
    _, separator, digest = index_id.partition("@sha256:")
    if not separator or _SHA256_RE.fullmatch(digest) is None:
        raise CorrelationIndexContractError(
            f"{index_id!r} is not a content-addressed index identity"
        )
    return digest[:_GENERATION_WIDTH]


def ghsa_partition_key(generation: str, package_name_canonical: str) -> str:
    """Build the GHSA partition key for one generation and package.

    Args:
        generation: The build generation.
        package_name_canonical: The canonical package name the request asks about.

    Returns:
        The partition key.

    Raises:
        CorrelationIndexContractError: If either part is malformed.
    """
    _require_generation(generation)
    _require_text(package_name_canonical, field="package_name_canonical")
    return f"{generation}{_KEY_SEPARATOR}{package_name_canonical}"


def nvd_partition_key(generation: str, cve_id: str) -> str:
    """Build the NVD partition key for one generation and CVE.

    Args:
        generation: The build generation.
        cve_id: The CVE the scoped advisories name.

    Returns:
        The partition key.

    Raises:
        CorrelationIndexContractError: If either part is malformed.
    """
    _require_generation(generation)
    if _CVE_RE.fullmatch(cve_id) is None:
        raise CorrelationIndexContractError(f"{cve_id} is not a CVE identifier")
    return f"{generation}{_KEY_SEPARATOR}{cve_id}"


def _require_generation(value: str) -> None:
    """Reject a generation that could address another build's key space.

    Args:
        value: The generation to check.

    Raises:
        CorrelationIndexContractError: If it is not a digest prefix of the right width.
    """
    if (
        type(value) is not str
        or len(value) != _GENERATION_WIDTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CorrelationIndexContractError(
            f"a generation is {_GENERATION_WIDTH} lowercase hex characters"
        )


def index_timestamp(value: datetime) -> str:
    """Render one instant in the index's single timestamp form.

    Args:
        value: Any timezone-aware instant.

    Returns:
        The instant in UTC, as `YYYY-MM-DDTHH:MM:SSZ`.

    Raises:
        CorrelationIndexContractError: If the instant carries no timezone.
    """
    if value.tzinfo is None:
        raise CorrelationIndexContractError("an index timestamp must be timezone-aware")
    return value.astimezone(UTC).strftime(_TIMESTAMP_FORMAT)


def source_instant(value: str, *, field: str) -> str:
    """Read a source's own rendering of an instant into the index's single form.

    Athena renders a Glue `timestamp` column as `2026-07-22 15:17:17.527` — a space
    instead of `T`, milliseconds, no zone. Stored unchanged, that string becomes part of
    the response envelope, and the index then emits two renderings of the same kind of
    thing: `index_timestamp` for its own instants and the source's for everything else.

    ```text
    a source rendering != the index's rendering
    ```

    This is the only place a foreign rendering is accepted, so there is one form to
    depend on downstream. Sub-second precision is dropped rather than rounded: the index
    states freshness to the second and must not imply more.

    Args:
        value: The instant as the source wrote it.
        field: The field being read, for the message.

    Returns:
        The instant as `YYYY-MM-DDTHH:MM:SSZ`.

    Raises:
        CorrelationIndexContractError: If the value is not an instant.
    """
    text = value.strip().replace(" ", "T")
    for suffix in ("Z", "+00:00"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    text = text.split(".", 1)[0]
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)
    except ValueError as exc:
        raise CorrelationIndexContractError(
            f"{field} {value!r} is not an instant this index can render"
        ) from exc
    return index_timestamp(parsed)


def _require_instant(value: str, *, field: str) -> None:
    """Reject an instant that is not already in the index's single form.

    Args:
        value: The candidate instant.
        field: The field being checked, for the message.

    Raises:
        CorrelationIndexContractError: If the value is not `YYYY-MM-DDTHH:MM:SSZ`.
    """
    if _INSTANT_RE.fullmatch(value) is None:
        raise CorrelationIndexContractError(
            f"{field} {value!r} is not rendered as YYYY-MM-DDTHH:MM:SSZ; "
            "read it through source_instant before building a row"
        )


def _require_text(value: str, *, field: str) -> None:
    """Reject an empty or padded string field.

    Args:
        value: The value to check.
        field: The field name, for the message.

    Raises:
        CorrelationIndexContractError: If the value is empty or padded.
    """
    if type(value) is not str or not value or value.strip() != value:
        raise CorrelationIndexContractError(f"{field} must be a non-empty unpadded string")


def _require_sha256(value: str, *, field: str) -> None:
    """Reject anything that is not a lowercase sha-256 hex digest.

    Args:
        value: The value to check.
        field: The field name, for the message.

    Raises:
        CorrelationIndexContractError: If the value is not such a digest.
    """
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise CorrelationIndexContractError(f"{field} must be a lowercase sha-256 hex digest")


@dataclass(frozen=True, slots=True)
class ProjectedSourceIdentifier:
    """One advisory identifier exactly as GitHub emitted it.

    Attributes:
        identifier_type: The kind GitHub assigned, such as `GHSA` or `CVE`.
        value: The identifier itself.
    """

    identifier_type: str
    value: str

    def __post_init__(self) -> None:
        """Reject an identifier that carries no authority.

        Raises:
            CorrelationIndexContractError: If either field is empty or padded.
        """
        _require_text(self.identifier_type, field="identifier_type")
        _require_text(self.value, field="value")


@dataclass(frozen=True, slots=True)
class ProjectedGhsaIndexRow:
    """One GHSA occurrence, keyed by the package a request asks about.

    One item per (package, advisory occurrence) rather than one per package: ADR 0087
    measured `tensorflow` carrying 1,323 advisories, which as a single item exceeds the
    store's per-item limit. The median package carries one.

    Attributes:
        package_name_canonical: Normalized package name; the partition key.
        observed_advisory_version_id: `<ghsa id>@sha256:<advisory digest>`.
        source_advisory_sha256: Digest of the whole source advisory.
        source_entry_sha256: Digest of this vulnerability entry within it.
        ghsa_id: The advisory identifier.
        github_cve_id: The CVE the advisory names, when it names one.
        github_identifiers: Every identifier the advisory carries, in source order.
        vulnerability_entry_id: Source-local identity of the entry.
        source_index: Position of the entry within the advisory.
        ecosystem_original: Ecosystem exactly as the source wrote it.
        package_name_original: Package name exactly as the source wrote it.
        vulnerable_range_original: Affected range exactly as the source wrote it.
        first_patched_version_original: First fixed version, when the source gives one.
    """

    package_name_canonical: str
    observed_advisory_version_id: str
    source_advisory_sha256: str
    source_entry_sha256: str
    ghsa_id: str
    github_cve_id: str | None
    github_identifiers: tuple[ProjectedSourceIdentifier, ...]
    vulnerability_entry_id: str
    source_index: int
    ecosystem_original: str
    package_name_original: str
    vulnerable_range_original: str
    first_patched_version_original: str | None

    def __post_init__(self) -> None:
        """Enforce, at write time, every rule the request path enforces at read time.

        Raises:
            CorrelationIndexContractError: If the row would be refused downstream.
        """
        for field, value in (
            ("package_name_canonical", self.package_name_canonical),
            ("vulnerability_entry_id", self.vulnerability_entry_id),
            ("ecosystem_original", self.ecosystem_original),
            ("package_name_original", self.package_name_original),
            ("vulnerable_range_original", self.vulnerable_range_original),
        ):
            _require_text(value, field=field)

        _require_sha256(self.source_advisory_sha256, field="source_advisory_sha256")
        _require_sha256(self.source_entry_sha256, field="source_entry_sha256")

        if _GHSA_RE.fullmatch(self.ghsa_id) is None:
            raise CorrelationIndexContractError(f"{self.ghsa_id} is not a GHSA identifier")

        expected = f"{self.ghsa_id}@sha256:{self.source_advisory_sha256}"
        if self.observed_advisory_version_id != expected:
            raise CorrelationIndexContractError(
                "observed advisory version identity contradicts the advisory digest"
            )

        if type(self.source_index) is not int or not 0 <= self.source_index <= _MAX_SOURCE_INDEX:
            raise CorrelationIndexContractError(
                f"source_index must be between 0 and {_MAX_SOURCE_INDEX}"
            )

        if type(self.github_identifiers) is not tuple or any(
            type(item) is not ProjectedSourceIdentifier for item in self.github_identifiers
        ):
            raise CorrelationIndexContractError("github_identifiers must be a typed tuple")

        if self.github_cve_id is not None and _CVE_RE.fullmatch(self.github_cve_id) is None:
            raise CorrelationIndexContractError(
                f"{self.github_cve_id} is not a CVE identifier"
            )

        if self.first_patched_version_original is not None:
            _require_text(
                self.first_patched_version_original, field="first_patched_version_original"
            )

    @property
    def occurrence_key(self) -> str:
        """Return the sort key identifying this occurrence within its package."""
        return (
            f"{self.observed_advisory_version_id}"
            f"{_KEY_SEPARATOR}{self.source_index:0{_SOURCE_INDEX_WIDTH}d}"
        )

    @property
    def canonical_payload(self) -> Mapping[str, object]:
        """Project every field this row carries, for the index content digest.

        Every field, not the keys: an index whose digest covered only the keys would be
        unchanged by an advisory whose range or patched version moved, which is the
        change most worth noticing. A test drives this from `dataclasses.fields`, so a
        new field fails until it is digested.
        """
        return {
            "ecosystem_original": self.ecosystem_original,
            "first_patched_version_original": self.first_patched_version_original,
            "ghsa_id": self.ghsa_id,
            "github_cve_id": self.github_cve_id,
            "github_identifiers": [
                {"identifier_type": item.identifier_type, "value": item.value}
                for item in self.github_identifiers
            ],
            "observed_advisory_version_id": self.observed_advisory_version_id,
            "package_name_canonical": self.package_name_canonical,
            "package_name_original": self.package_name_original,
            "source_advisory_sha256": self.source_advisory_sha256,
            "source_entry_sha256": self.source_entry_sha256,
            "source_index": self.source_index,
            "vulnerability_entry_id": self.vulnerability_entry_id,
            "vulnerable_range_original": self.vulnerable_range_original,
        }


@dataclass(frozen=True, slots=True)
class ProjectedNvdIndexRow:
    """One observed NVD CVE version, keyed by the CVE a scoped advisory names.

    Attributes:
        cve_id: The CVE identifier; the partition key.
        observed_cve_version_id: `<cve id>@sha256:<content digest>`.
        source_cve_sha256: Digest of the observed CVE content.
        source_identifier: The NVD source identifier.
        published_at: When NVD published the CVE.
        last_modified_at: When NVD last modified it.
        vuln_status: The NVD vulnerability status, as the source wrote it.
    """

    cve_id: str
    observed_cve_version_id: str
    source_cve_sha256: str
    source_identifier: str
    published_at: str
    last_modified_at: str
    vuln_status: str

    def __post_init__(self) -> None:
        """Reject a row whose identity does not agree with its own digest.

        Raises:
            CorrelationIndexContractError: If the row is malformed.
        """
        if _CVE_RE.fullmatch(self.cve_id) is None:
            raise CorrelationIndexContractError(f"{self.cve_id} is not a CVE identifier")

        _require_sha256(self.source_cve_sha256, field="source_cve_sha256")
        for field, value in (
            ("source_identifier", self.source_identifier),
            ("published_at", self.published_at),
            ("last_modified_at", self.last_modified_at),
            ("vuln_status", self.vuln_status),
        ):
            _require_text(value, field=field)

        for field, value in (
            ("published_at", self.published_at),
            ("last_modified_at", self.last_modified_at),
        ):
            _require_instant(value, field=field)

        expected = f"{self.cve_id}@sha256:{self.source_cve_sha256}"
        if self.observed_cve_version_id != expected:
            raise CorrelationIndexContractError(
                "observed CVE version identity contradicts the content digest"
            )

    @property
    def canonical_payload(self) -> Mapping[str, object]:
        """Project every field this row carries, for the index content digest."""
        return {
            "cve_id": self.cve_id,
            "last_modified_at": self.last_modified_at,
            "observed_cve_version_id": self.observed_cve_version_id,
            "published_at": self.published_at,
            "source_cve_sha256": self.source_cve_sha256,
            "source_identifier": self.source_identifier,
            "vuln_status": self.vuln_status,
        }


def index_content_digest(
    ghsa_rows: Sequence[ProjectedGhsaIndexRow],
    nvd_rows: Sequence[ProjectedNvdIndexRow],
) -> str:
    """Digest exactly what one build holds, independent of the order it was produced in.

    This is what makes an index identity an identity. Before it existed, the manifest was
    digested over counts and watermarks, so two indexes holding entirely different rows
    in the same quantity derived the same identity, and therefore the same key space.

    ```text
    identity of the description != identity of the content
    ```

    Rows are sorted by their store keys rather than trusted in query order, so a build
    that reads the same corpus through a differently ordered query produces the same
    digest. That is what makes a re-run idempotent, which is what ADR 0088 said the
    generation was for.

    Args:
        ghsa_rows: Every GHSA row the build holds.
        nvd_rows: Every NVD row the build holds.

    Returns:
        A lowercase sha-256 hex digest over the whole content.
    """
    return sha256_hex(
        canonical_json(
            {
                "ghsa": [
                    row.canonical_payload
                    for row in sorted(
                        ghsa_rows,
                        key=lambda item: (item.package_name_canonical, item.occurrence_key),
                    )
                ],
                "nvd": [
                    row.canonical_payload
                    for row in sorted(nvd_rows, key=lambda item: item.cve_id)
                ],
            }
        )
    )


@dataclass(frozen=True, slots=True)
class SourceWatermark:
    """How current one source was when the index was built.

    Attributes:
        source: The source name, such as `ghsa` or `nvd`.
        observed_through: The latest source instant the build saw.
        record_count: How many source records it read.
    """

    source: str
    observed_through: str
    record_count: int

    def __post_init__(self) -> None:
        """Reject a watermark that would let a response overstate freshness.

        Raises:
            CorrelationIndexContractError: If the watermark is malformed.
        """
        _require_text(self.source, field="source")
        _require_text(self.observed_through, field="observed_through")
        try:
            datetime.strptime(self.observed_through, _TIMESTAMP_FORMAT).replace(tzinfo=UTC)
        except ValueError as exc:
            raise CorrelationIndexContractError(
                f"observed_through must use {_TIMESTAMP_FORMAT}"
            ) from exc
        if type(self.record_count) is not int or self.record_count < 0:
            raise CorrelationIndexContractError("record_count must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class CorrelationIndexManifest:
    """What one build of the index is, so a response can name what answered it.

    The identity is taken over the content and the freshness, and deliberately not over
    `built_at`. Two builds of identical content from identically fresh sources are the
    same index, whenever they ran, and reusing their generation is what ADR 0088 meant by
    an idempotent re-run. `built_at` is still carried, still stored, and still reported —
    it is provenance, not identity.

    ```text
    what is stored != what is digested
    when it was built != what was built
    ```

    Attributes:
        built_at: When the build ran, as `YYYY-MM-DDTHH:MM:SSZ`. Not part of the identity.
        content_digest: sha-256 over every row the build holds.
        ghsa_row_count: Rows written to the GHSA-by-package index.
        nvd_row_count: Rows written to the NVD-by-CVE index.
        distinct_package_count: Distinct normalized packages covered.
        watermarks: One watermark per contributing source.
    """

    built_at: str
    content_digest: str
    ghsa_row_count: int
    nvd_row_count: int
    distinct_package_count: int
    watermarks: tuple[SourceWatermark, ...]

    def __post_init__(self) -> None:
        """Reject a manifest that could not describe a real build.

        Raises:
            CorrelationIndexContractError: If the manifest is malformed, carries no
                source, or names a source twice.
        """
        _require_text(self.built_at, field="built_at")
        try:
            datetime.strptime(self.built_at, _TIMESTAMP_FORMAT).replace(tzinfo=UTC)
        except ValueError as exc:
            raise CorrelationIndexContractError(
                f"built_at must use {_TIMESTAMP_FORMAT}"
            ) from exc

        _require_sha256(self.content_digest, field="content_digest")

        for field, value in (
            ("ghsa_row_count", self.ghsa_row_count),
            ("nvd_row_count", self.nvd_row_count),
            ("distinct_package_count", self.distinct_package_count),
        ):
            if type(value) is not int or value < 0:
                raise CorrelationIndexContractError(f"{field} must be a non-negative integer")

        if self.distinct_package_count > self.ghsa_row_count:
            raise CorrelationIndexContractError(
                "an index cannot cover more packages than it holds rows"
            )

        if type(self.watermarks) is not tuple or not self.watermarks:
            raise CorrelationIndexContractError(
                "an index built from no source cannot state its freshness"
            )
        if any(type(item) is not SourceWatermark for item in self.watermarks):
            raise CorrelationIndexContractError("watermarks must be typed")

        names = [item.source for item in self.watermarks]
        if len(set(names)) != len(names):
            raise CorrelationIndexContractError("each source carries exactly one watermark")
        if names != sorted(names):
            raise CorrelationIndexContractError(
                "watermarks must be in canonical order, so identity does not depend on it"
            )

    @property
    def canonical_payload(self) -> Mapping[str, object]:
        """Project the payload the index identity is taken over.

        `built_at` is absent on purpose. Counts are present and prove nothing on their
        own — `content_digest` is what makes two indexes with the same shape and
        different rows different indexes.
        """
        return {
            "content_digest": self.content_digest,
            "contract_version": CORRELATION_INDEX_CONTRACT_VERSION,
            "counts": {
                "distinct_packages": self.distinct_package_count,
                "ghsa_rows": self.ghsa_row_count,
                "nvd_rows": self.nvd_row_count,
            },
            "watermarks": [
                {
                    "observed_through": item.observed_through,
                    "record_count": item.record_count,
                    "source": item.source,
                }
                for item in self.watermarks
            ],
        }

    @property
    def stored_document(self) -> Mapping[str, object]:
        """Project everything the retained manifest object holds.

        The identity payload plus the provenance that is not part of it. A reader
        rebuilds the typed manifest from this and re-derives the identity, which is how a
        manifest certifies that it describes the generation the pointer names.

        ```text
        what is stored != what is digested
        ```
        """
        return {**self.canonical_payload, "built_at": self.built_at}

    @property
    def canonical_json(self) -> bytes:
        """Return the exact bytes the index identity is taken over."""
        return canonical_json(self.canonical_payload)

    @property
    def stored_json(self) -> bytes:
        """Return the exact bytes the retained manifest object holds."""
        return canonical_json(self.stored_document)

    @property
    def index_id(self) -> str:
        """Return `<contract version>@sha256:<digest>` for this build."""
        return evidence_id(CORRELATION_INDEX_CONTRACT_VERSION, self.canonical_payload)


def build_manifest(
    *,
    built_at: datetime,
    ghsa_rows: Sequence[ProjectedGhsaIndexRow],
    nvd_rows: Sequence[ProjectedNvdIndexRow],
    watermarks: Sequence[SourceWatermark],
) -> CorrelationIndexManifest:
    """Describe one build from the rows it actually produced.

    Counting the rows rather than accepting counts is deliberate: a manifest whose
    numbers are passed in can disagree with the index it describes, and a response that
    cites a disagreeing manifest is worse than one that cites none.

    Args:
        built_at: When the build ran.
        ghsa_rows: The GHSA rows written.
        nvd_rows: The NVD rows written.
        watermarks: One watermark per contributing source, in any order.

    Returns:
        The manifest describing that build.

    Raises:
        CorrelationIndexContractError: If the manifest would be malformed.
    """
    return CorrelationIndexManifest(
        built_at=index_timestamp(built_at),
        content_digest=index_content_digest(ghsa_rows, nvd_rows),
        ghsa_row_count=len(ghsa_rows),
        nvd_row_count=len(nvd_rows),
        distinct_package_count=len({row.package_name_canonical for row in ghsa_rows}),
        watermarks=tuple(sorted(watermarks, key=lambda item: item.source)),
    )
