"""Deterministic Bronze-to-Silver provenance models for GHSA."""

import re
from dataclasses import dataclass

from opslens.transformation.ghsa.domain.models import (
    ObservedGhsaAdvisoryVersion,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class GhsaBronzeAdvisoryOccurrenceV1:
    """Bind one exact Bronze advisory occurrence to one Silver content version."""

    sync_id: str
    attempt_id: str

    manifest_key: str
    manifest_version_id: str

    page_ordinal: int
    page_key: str
    page_version_id: str

    source_index: int
    observed_version: ObservedGhsaAdvisoryVersion

    def __post_init__(self) -> None:
        """Validate deterministic physical-to-logical provenance invariants."""
        self._require_sha256(self.sync_id, "sync_id")
        self._require_sha256(self.attempt_id, "attempt_id")

        for field_name, value in (
            ("manifest_key", self.manifest_key),
            ("manifest_version_id", self.manifest_version_id),
            ("page_key", self.page_key),
            ("page_version_id", self.page_version_id),
        ):
            if not value.strip():
                raise ValueError(
                    f"GHSA Bronze/Silver provenance {field_name} cannot be empty."
                )

        if type(self.page_ordinal) is not int or self.page_ordinal < 1:
            raise ValueError(
                "GHSA Bronze/Silver provenance page_ordinal must be positive."
            )

        if type(self.source_index) is not int or self.source_index < 0:
            raise ValueError(
                "GHSA Bronze/Silver provenance source_index must be non-negative."
            )

    @classmethod
    def from_source(
        cls,
        *,
        sync_id: str,
        attempt_id: str,
        manifest_key: str,
        manifest_version_id: str,
        page_ordinal: int,
        page_key: str,
        page_version_id: str,
        source_index: int,
        source_advisory: dict[str, object],
    ) -> "GhsaBronzeAdvisoryOccurrenceV1":
        """Derive logical Silver identity from one exact Bronze advisory object."""
        observed_version = ObservedGhsaAdvisoryVersion.from_source(
            source_advisory
        )

        return cls(
            sync_id=sync_id,
            attempt_id=attempt_id,
            manifest_key=manifest_key,
            manifest_version_id=manifest_version_id,
            page_ordinal=page_ordinal,
            page_key=page_key,
            page_version_id=page_version_id,
            source_index=source_index,
            observed_version=observed_version,
        )

    @staticmethod
    def _require_sha256(value: str, field_name: str) -> None:
        """Require one lowercase hexadecimal SHA-256 digest."""
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError(
                f"GHSA Bronze/Silver provenance {field_name} must be "
                "a lowercase SHA-256 digest."
            )

    @property
    def ghsa_id(self) -> str:
        """Return the advisory identity derived from source content."""
        return self.observed_version.ghsa_id

    @property
    def source_advisory_sha256(self) -> str:
        """Return the exact canonical source-content SHA-256."""
        return self.observed_version.source_advisory_sha256

    @property
    def observed_advisory_version_id(self) -> str:
        """Return the deterministic Silver advisory-content identity."""
        return self.observed_version.observed_advisory_version_id


    @property
    def attempt_occurrence_id(self) -> str:
        """Return the exact advisory position inside one Bronze attempt."""
        return (
            f"{self.attempt_id}/"
            f"page:{self.page_ordinal:06d}/"
            f"item:{self.source_index:03d}"
        )
