"""Domain models for versioned NVD CVE Silver identity."""

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self, cast

from opslens.transformation.nvd.domain.canonicalization import (
    canonicalize_json_object,
    canonicalize_json_value,
    canonicalize_nvd_cve,
    sha256_hex,
)
from opslens.transformation.nvd.domain.errors import (
    InvalidNvdObservedCveVersionError,
)

_CVE_PATTERN = re.compile(r"^CVE-[0-9]{4}-[0-9]{4,}$")
_CWE_PATTERN = re.compile(r"^CWE-[0-9]+$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class NvdVulnerabilityStatus(StrEnum):
    """Represent the bounded NVD vulnerability-status vocabulary."""

    UNDERGOING_ANALYSIS = "UndergoingAnalysis"
    MODIFIED = "Modified"
    AWAITING_ANALYSIS = "AwaitingAnalysis"
    REJECTED = "Rejected"
    RECEIVED = "Received"
    ANALYZED = "Analyzed"
    DEFERRED = "Deferred"


@dataclass(frozen=True, slots=True)
class ObservedCveVersion:
    """Identify one exact NVD CVE content version observed by OpsLens.

    CVE identity and CVE content-version identity are intentionally different:

    - ``cve_id`` identifies the vulnerability;
    - ``source_cve_sha256`` identifies the complete observed NVD CVE content;
    - ``observed_cve_version_id`` combines both for a human-readable stable ID.

    The NVD ``lastModified`` value is evidence contained inside the source
    object, but it is deliberately not the version identity.

    Attributes:
        cve_id: Canonical CVE identifier.
        canonical_json: Canonical JSON v1 representation of the complete
            source CVE object.
        source_cve_sha256: SHA-256 of ``canonical_json``.
    """

    cve_id: str
    canonical_json: bytes
    source_cve_sha256: str

    @classmethod
    def from_source(cls, source_cve: dict[str, object]) -> Self:
        """Build one observed version from a parsed NVD CVE object."""
        cve_id = source_cve.get("id")

        if not isinstance(cve_id, str) or _CVE_PATTERN.fullmatch(cve_id) is None:
            raise InvalidNvdObservedCveVersionError("NVD CVE id must use the canonical CVE format.")

        canonical_json = canonicalize_nvd_cve(source_cve)

        return cls(
            cve_id=cve_id,
            canonical_json=canonical_json,
            source_cve_sha256=sha256_hex(canonical_json),
        )

    def __post_init__(self) -> None:
        """Validate invariants required by every observed CVE version."""
        if _CVE_PATTERN.fullmatch(self.cve_id) is None:
            raise InvalidNvdObservedCveVersionError("NVD CVE id must use the canonical CVE format.")

        if not self.canonical_json:
            raise InvalidNvdObservedCveVersionError("NVD CVE canonical JSON cannot be empty.")

        if _SHA256_PATTERN.fullmatch(self.source_cve_sha256) is None:
            raise InvalidNvdObservedCveVersionError(
                "NVD CVE source SHA-256 must contain 64 lowercase hexadecimal characters."
            )

        calculated_sha256 = sha256_hex(self.canonical_json)

        if calculated_sha256 != self.source_cve_sha256:
            raise InvalidNvdObservedCveVersionError(
                "NVD CVE source SHA-256 does not match the canonical JSON."
            )

        source_cve = self._parse_canonical_json()

        if source_cve.get("id") != self.cve_id:
            raise InvalidNvdObservedCveVersionError(
                "NVD CVE canonical JSON id does not match the observed CVE id."
            )

        expected_canonical_json = canonicalize_nvd_cve(source_cve)

        if expected_canonical_json != self.canonical_json:
            raise InvalidNvdObservedCveVersionError(
                "NVD CVE content does not use the Canonical JSON v1 encoding."
            )

    @property
    def observed_cve_version_id(self) -> str:
        """Return the deterministic identity of this observed CVE version."""
        return f"{self.cve_id}@sha256:{self.source_cve_sha256}"

    def _parse_canonical_json(self) -> dict[str, object]:
        """Parse stored canonical bytes for invariant verification."""
        try:
            text = self.canonical_json.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidNvdObservedCveVersionError(
                "NVD CVE canonical JSON must be valid UTF-8."
            ) from exc

        try:
            parsed = cast(object, json.loads(text))
        except json.JSONDecodeError as exc:
            raise InvalidNvdObservedCveVersionError(
                "NVD CVE canonical JSON must contain valid JSON."
            ) from exc

        if not isinstance(parsed, dict):
            raise InvalidNvdObservedCveVersionError(
                "NVD CVE canonical JSON must contain an object."
            )

        return cast(dict[str, object], parsed)


@dataclass(frozen=True, slots=True)
class NvdCveCoreRecord:
    """Represent normalized scalar fields for one observed NVD CVE version."""

    observed_version: ObservedCveVersion
    source_identifier: str
    published_at: datetime
    last_modified_at: datetime
    vuln_status: NvdVulnerabilityStatus

    def __post_init__(self) -> None:
        """Validate invariants required by every normalized NVD CVE core record."""
        if not self.source_identifier or not self.source_identifier.strip():
            raise ValueError("NVD sourceIdentifier must be non-empty.")

        if self.published_at.tzinfo is None:
            raise ValueError("NVD published timestamp must be timezone-aware.")

        if self.last_modified_at.tzinfo is None:
            raise ValueError("NVD lastModified timestamp must be timezone-aware.")

        if self.published_at.utcoffset() != UTC.utcoffset(self.published_at):
            raise ValueError("NVD published timestamp must be normalized to UTC.")

        if self.last_modified_at.utcoffset() != UTC.utcoffset(self.last_modified_at):
            raise ValueError("NVD lastModified timestamp must be normalized to UTC.")

    @property
    def is_rejected(self) -> bool:
        """Return whether this observed CVE version is explicitly rejected."""
        return self.vuln_status is NvdVulnerabilityStatus.REJECTED


@dataclass(frozen=True, slots=True)
class NvdLocalizedText:
    """Preserve one localized textual value from NVD."""

    lang: str
    value: str

    def __post_init__(self) -> None:
        """Validate localized-text invariants without rewriting source text."""
        if not self.lang or not self.lang.strip():
            raise ValueError("NVD localized-text language cannot be empty.")

        if not self.value or not self.value.strip():
            raise ValueError("NVD localized-text value cannot be empty.")


@dataclass(frozen=True, slots=True)
class NvdCveTag:
    """Preserve one source-qualified NVD CVE tag group."""

    source_identifier: str | None
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate CVE-tag values when supplied."""
        if self.source_identifier is not None and not self.source_identifier.strip():
            raise ValueError("NVD CVE tag sourceIdentifier cannot be empty when present.")

        for tag in self.tags:
            if not tag or not tag.strip():
                raise ValueError("NVD CVE tags cannot contain empty values.")


@dataclass(frozen=True, slots=True)
class NvdWeakness:
    """Preserve one source-qualified NVD weakness observation."""

    source: str
    type: str
    descriptions: tuple[NvdLocalizedText, ...]

    def __post_init__(self) -> None:
        """Validate NVD weakness scalar invariants."""
        if not self.source or not self.source.strip():
            raise ValueError("NVD weakness source cannot be empty.")

        if not self.type or not self.type.strip():
            raise ValueError("NVD weakness type cannot be empty.")


@dataclass(frozen=True, slots=True)
class NvdReference:
    """Preserve one NVD vulnerability reference."""

    url: str
    source: str | None
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate reference invariants without dereferencing the URL."""
        if not self.url or not self.url.strip():
            raise ValueError("NVD reference URL cannot be empty.")

        if self.source is not None and not self.source.strip():
            raise ValueError("NVD reference source cannot be empty when present.")

        for tag in self.tags:
            if not tag or not tag.strip():
                raise ValueError("NVD reference tags cannot contain empty values.")


@dataclass(frozen=True, slots=True)
class NvdCveCollections:
    """Represent normalized non-CVSS collection fields for one NVD CVE."""

    descriptions: tuple[NvdLocalizedText, ...]
    cve_tags: tuple[NvdCveTag, ...]
    weaknesses: tuple[NvdWeakness, ...]
    references: tuple[NvdReference, ...]

    def __post_init__(self) -> None:
        """Validate collection-level NVD invariants."""
        if not self.descriptions:
            raise ValueError("NVD CVE must contain at least one description.")

    @property
    def cwe_ids(self) -> tuple[str, ...]:
        """Return stable unique canonical CWE identifiers in source order."""
        result: list[str] = []
        seen: set[str] = set()

        for weakness in self.weaknesses:
            for description in weakness.descriptions:
                value = description.value

                if _CWE_PATTERN.fullmatch(value) is not None and value not in seen:
                    seen.add(value)
                    result.append(value)

        return tuple(result)


class NvdCvssFamily(StrEnum):
    """Represent CVSS families understood by Silver schema v1."""

    V2 = "V2"
    V30 = "V30"
    V31 = "V31"
    V40 = "V40"


class NvdCvssMetricType(StrEnum):
    """Represent the NVD metric-source classification."""

    PRIMARY = "Primary"
    SECONDARY = "Secondary"


@dataclass(frozen=True, slots=True)
class NvdCvssMetric:
    """Preserve one complete CVSS assessment observed by NVD."""

    family: NvdCvssFamily
    version: str
    source: str
    metric_type: NvdCvssMetricType
    vector_string: str
    base_score: float
    base_severity: str | None
    exploitability_score: float | None
    impact_score: float | None
    metric_json: str

    def __post_init__(self) -> None:
        """Validate normalized CVSS metric invariants."""
        expected_versions = {
            NvdCvssFamily.V2: "2.0",
            NvdCvssFamily.V30: "3.0",
            NvdCvssFamily.V31: "3.1",
            NvdCvssFamily.V40: "4.0",
        }

        if self.version != expected_versions[self.family]:
            raise ValueError(
                f"CVSS family {self.family.value} requires version "
                f"{expected_versions[self.family]!r}."
            )

        if not self.source or not self.source.strip():
            raise ValueError("NVD CVSS source cannot be empty.")

        if not self.vector_string or not self.vector_string.strip():
            raise ValueError("NVD CVSS vectorString cannot be empty.")

        if self.base_severity is not None and not self.base_severity.strip():
            raise ValueError("NVD CVSS baseSeverity cannot be empty.")

        self._validate_score(
            self.base_score,
            "baseScore",
        )

        if self.exploitability_score is not None:
            self._validate_score(
                self.exploitability_score,
                "exploitabilityScore",
            )

        if self.impact_score is not None:
            self._validate_score(
                self.impact_score,
                "impactScore",
            )

        try:
            parsed = cast(
                object,
                json.loads(self.metric_json),
            )
        except json.JSONDecodeError as exc:
            raise ValueError("NVD CVSS metric_json must contain valid JSON.") from exc

        if not isinstance(parsed, dict):
            raise ValueError("NVD CVSS metric_json must contain a JSON object.")

        metric_object = cast(
            dict[str, object],
            parsed,
        )

        if canonicalize_json_object(metric_object).decode("utf-8") != self.metric_json:
            raise ValueError("NVD CVSS metric_json must use Canonical JSON v1.")

    @staticmethod
    def _validate_score(
        value: float,
        field_name: str,
    ) -> None:
        """Require one finite bounded CVSS score."""
        if not math.isfinite(value):
            raise ValueError(f"NVD CVSS {field_name} must be finite.")

        if value < 0.0 or value > 10.0:
            raise ValueError(f"NVD CVSS {field_name} must be between 0.0 and 10.0.")


@dataclass(frozen=True, slots=True)
class NvdCvssMetrics:
    """Represent all CVSS assessments from one observed NVD CVE."""

    metrics: tuple[NvdCvssMetric, ...]
    unsupported_cvss_families: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NvdCpeConfigurations:
    """Preserve validated NVD applicability configurations as canonical JSON."""

    configurations_json: str
    configuration_count: int

    def __post_init__(self) -> None:
        """Validate stored configuration evidence and its canonical encoding."""
        if type(self.configuration_count) is not int:
            raise ValueError("NVD configuration_count must be an integer.")

        if self.configuration_count < 0:
            raise ValueError("NVD configuration_count cannot be negative.")

        try:
            parsed = cast(
                object,
                json.loads(self.configurations_json),
            )
        except json.JSONDecodeError as exc:
            raise ValueError("NVD configurations_json must contain valid JSON.") from exc

        if not isinstance(parsed, list):
            raise ValueError("NVD configurations_json must contain a JSON array.")

        configurations = cast(
            list[object],
            parsed,
        )

        if len(configurations) != self.configuration_count:
            raise ValueError("NVD configuration_count does not match configurations_json.")

        expected = canonicalize_json_value(configurations).decode("utf-8")

        if expected != self.configurations_json:
            raise ValueError("NVD configurations_json must use Canonical JSON v1.")
