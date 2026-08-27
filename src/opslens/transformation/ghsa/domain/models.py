"""Domain models for versioned GitHub Security Advisory Silver evidence."""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self, cast

from opslens.transformation.ghsa.domain.canonicalization import (
    canonicalize_ghsa_advisory,
    sha256_hex,
)
from opslens.transformation.ghsa.domain.errors import (
    InvalidGhsaObservedAdvisoryVersionError,
)

_GHSA_PATTERN = re.compile(r"^GHSA(?:-[23456789cfghjmpqrvwx]{4}){3}$")
_CVE_PATTERN = re.compile(r"^CVE-[0-9]{4}-[0-9]{4,}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class GhsaAdvisoryType(StrEnum):
    """Represent the documented GitHub global-advisory classes."""

    REVIEWED = "reviewed"
    UNREVIEWED = "unreviewed"
    MALWARE = "malware"


class GhsaAdvisorySeverity(StrEnum):
    """Represent the documented GitHub advisory severity vocabulary."""

    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class ObservedGhsaAdvisoryVersion:
    """Identify one exact GitHub advisory content version observed by OpsLens.

    GHSA identity and observed content-version identity are intentionally
    different:

    - ``ghsa_id`` identifies the advisory;
    - ``source_advisory_sha256`` identifies the complete observed REST object;
    - ``observed_advisory_version_id`` combines both into a stable identifier.

    GitHub ``updated_at`` is preserved source metadata but is deliberately not
    trusted as the sole version identity.
    """

    ghsa_id: str
    canonical_json: bytes
    source_advisory_sha256: str

    @classmethod
    def from_source(cls, source_advisory: dict[str, object]) -> Self:
        """Build one observed advisory version from a parsed GitHub REST object."""
        ghsa_id = source_advisory.get("ghsa_id")

        if not isinstance(ghsa_id, str) or _GHSA_PATTERN.fullmatch(ghsa_id) is None:
            raise InvalidGhsaObservedAdvisoryVersionError(
                "GitHub advisory ghsa_id must use the canonical GHSA format."
            )

        canonical_json = canonicalize_ghsa_advisory(source_advisory)

        return cls(
            ghsa_id=ghsa_id,
            canonical_json=canonical_json,
            source_advisory_sha256=sha256_hex(canonical_json),
        )

    def __post_init__(self) -> None:
        """Validate invariants required by every observed advisory version."""
        if _GHSA_PATTERN.fullmatch(self.ghsa_id) is None:
            raise InvalidGhsaObservedAdvisoryVersionError(
                "GitHub advisory ghsa_id must use the canonical GHSA format."
            )

        if not self.canonical_json:
            raise InvalidGhsaObservedAdvisoryVersionError(
                "GitHub advisory canonical JSON cannot be empty."
            )

        if _SHA256_PATTERN.fullmatch(self.source_advisory_sha256) is None:
            raise InvalidGhsaObservedAdvisoryVersionError(
                "GitHub advisory source SHA-256 must contain 64 lowercase "
                "hexadecimal characters."
            )

        calculated_sha256 = sha256_hex(self.canonical_json)

        if calculated_sha256 != self.source_advisory_sha256:
            raise InvalidGhsaObservedAdvisoryVersionError(
                "GitHub advisory source SHA-256 does not match the canonical JSON."
            )

        source_advisory = self._parse_canonical_json()

        if source_advisory.get("ghsa_id") != self.ghsa_id:
            raise InvalidGhsaObservedAdvisoryVersionError(
                "GitHub advisory canonical JSON ghsa_id does not match the observed advisory id."
            )

        expected_canonical_json = canonicalize_ghsa_advisory(source_advisory)

        if expected_canonical_json != self.canonical_json:
            raise InvalidGhsaObservedAdvisoryVersionError(
                "GitHub advisory content does not use the Canonical JSON v1 encoding."
            )

    @property
    def observed_advisory_version_id(self) -> str:
        """Return the deterministic identity of this observed advisory version."""
        return f"{self.ghsa_id}@sha256:{self.source_advisory_sha256}"

    def _parse_canonical_json(self) -> dict[str, object]:
        """Parse stored canonical bytes for invariant verification."""
        try:
            text = self.canonical_json.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidGhsaObservedAdvisoryVersionError(
                "GitHub advisory canonical JSON must be valid UTF-8."
            ) from exc

        try:
            parsed = cast(object, json.loads(text))
        except json.JSONDecodeError as exc:
            raise InvalidGhsaObservedAdvisoryVersionError(
                "GitHub advisory canonical JSON must contain valid JSON."
            ) from exc

        if not isinstance(parsed, dict):
            raise InvalidGhsaObservedAdvisoryVersionError(
                "GitHub advisory canonical JSON must contain an object."
            )

        return cast(dict[str, object], parsed)


@dataclass(frozen=True, slots=True)
class GhsaAdvisoryCoreRecord:
    """Represent normalized scalar fields for one observed reviewed GHSA."""

    observed_version: ObservedGhsaAdvisoryVersion
    cve_id: str | None
    advisory_type: GhsaAdvisoryType
    severity: GhsaAdvisorySeverity
    url: str
    html_url: str
    repository_advisory_url: str | None
    source_code_location: str | None
    summary: str
    description: str
    published_at: datetime
    updated_at: datetime
    github_reviewed_at: datetime | None
    nvd_published_at: datetime | None
    withdrawn_at: datetime | None

    def __post_init__(self) -> None:
        """Validate normalized core-record invariants."""
        if self.advisory_type is not GhsaAdvisoryType.REVIEWED:
            raise ValueError("GHSA Silver v1 accepts reviewed advisories only.")

        if self.cve_id is not None and _CVE_PATTERN.fullmatch(self.cve_id) is None:
            raise ValueError("GHSA cve_id must use canonical CVE format when present.")

        for field_name, value in (
            ("url", self.url),
            ("html_url", self.html_url),
            ("summary", self.summary),
            ("description", self.description),
        ):
            if not value.strip():
                raise ValueError(f"GHSA {field_name} cannot be empty.")

        for field_name, value in (
            ("repository_advisory_url", self.repository_advisory_url),
            ("source_code_location", self.source_code_location),
        ):
            if value is not None and not value.strip():
                raise ValueError(f"GHSA {field_name} cannot be empty when present.")

        self._require_utc("published_at", self.published_at)
        self._require_utc("updated_at", self.updated_at)

        for field_name, value in (
            ("github_reviewed_at", self.github_reviewed_at),
            ("nvd_published_at", self.nvd_published_at),
            ("withdrawn_at", self.withdrawn_at),
        ):
            if value is not None:
                self._require_utc(field_name, value)

    @property
    def is_withdrawn(self) -> bool:
        """Return whether this observed advisory version is withdrawn."""
        return self.withdrawn_at is not None

    @staticmethod
    def _require_utc(field_name: str, value: datetime) -> None:
        """Require timezone-aware UTC timestamps in normalized Silver records."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"GHSA {field_name} must be timezone-aware.")

        if value.utcoffset() != UTC.utcoffset(value):
            raise ValueError(f"GHSA {field_name} must be normalized to UTC.")
