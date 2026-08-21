"""Domain models for versioned NVD CVE Silver identity."""

import json
import re
from dataclasses import dataclass
from typing import Self, cast

from opslens.transformation.nvd.domain.canonicalization import (
    canonicalize_nvd_cve,
    sha256_hex,
)
from opslens.transformation.nvd.domain.errors import (
    InvalidNvdObservedCveVersionError,
)

_CVE_PATTERN = re.compile(r"^CVE-[0-9]{4}-[0-9]{4,}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


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
