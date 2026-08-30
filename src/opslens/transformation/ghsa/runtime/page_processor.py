"""Verify exact GHSA Bronze page evidence and derive advisory occurrences."""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import cast

from opslens.transformation.ghsa.runtime.provenance import (
    GhsaBronzeAdvisoryOccurrenceV1,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class GhsaBronzePageEvidenceV1:
    """Describe the exact persisted Bronze page expected by Silver."""

    sync_id: str
    attempt_id: str

    manifest_key: str
    manifest_version_id: str

    page_ordinal: int
    page_key: str
    page_version_id: str

    expected_size_bytes: int
    expected_sha256: str

    def __post_init__(self) -> None:
        """Validate immutable physical page evidence."""
        self._require_sha256(self.sync_id, "sync_id")
        self._require_sha256(self.attempt_id, "attempt_id")
        self._require_sha256(self.expected_sha256, "expected_sha256")

        for field_name, value in (
            ("manifest_key", self.manifest_key),
            ("manifest_version_id", self.manifest_version_id),
            ("page_key", self.page_key),
            ("page_version_id", self.page_version_id),
        ):
            if not value.strip():
                raise ValueError(
                    f"GHSA Bronze page evidence {field_name} cannot be empty."
                )

        if type(self.page_ordinal) is not int or self.page_ordinal < 1:
            raise ValueError(
                "GHSA Bronze page evidence page_ordinal must be positive."
            )

        if (
            type(self.expected_size_bytes) is not int
            or self.expected_size_bytes <= 0
        ):
            raise ValueError(
                "GHSA Bronze page evidence expected_size_bytes must be positive."
            )

    @staticmethod
    def _require_sha256(value: str, field_name: str) -> None:
        """Require a lowercase hexadecimal SHA-256 digest."""
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError(
                f"GHSA Bronze page evidence {field_name} must be "
                "a lowercase SHA-256 digest."
            )


@dataclass(frozen=True, slots=True)
class GhsaVerifiedBronzePageV1:
    """Represent one exact verified Bronze page and its derived occurrences."""

    evidence: GhsaBronzePageEvidenceV1
    occurrences: tuple[GhsaBronzeAdvisoryOccurrenceV1, ...]

    @property
    def item_count(self) -> int:
        """Return the number of advisory occurrences in this exact page."""
        return len(self.occurrences)


class GhsaBronzePageProcessorV1:
    """Verify exact Bronze bytes before deriving Silver provenance."""

    def process(
        self,
        *,
        evidence: GhsaBronzePageEvidenceV1,
        page_bytes: bytes,
    ) -> GhsaVerifiedBronzePageV1:
        """Verify one exact persisted page and derive advisory occurrences."""
        if len(page_bytes) != evidence.expected_size_bytes:
            raise ValueError(
                "GHSA Bronze page bytes do not match expected_size_bytes."
            )

        actual_sha256 = hashlib.sha256(page_bytes).hexdigest()

        if actual_sha256 != evidence.expected_sha256:
            raise ValueError(
                "GHSA Bronze page bytes do not match expected_sha256."
            )

        advisories = self._parse_advisories(page_bytes)

        occurrences = tuple(
            GhsaBronzeAdvisoryOccurrenceV1.from_source(
                sync_id=evidence.sync_id,
                attempt_id=evidence.attempt_id,
                manifest_key=evidence.manifest_key,
                manifest_version_id=evidence.manifest_version_id,
                page_ordinal=evidence.page_ordinal,
                page_key=evidence.page_key,
                page_version_id=evidence.page_version_id,
                source_index=source_index,
                source_advisory=source_advisory,
            )
            for source_index, source_advisory in enumerate(advisories)
        )

        return GhsaVerifiedBronzePageV1(
            evidence=evidence,
            occurrences=occurrences,
        )

    @staticmethod
    def _parse_advisories(page_bytes: bytes) -> tuple[dict[str, object], ...]:
        """Parse exact Bronze bytes as one top-level advisory JSON array."""
        try:
            text = page_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "GHSA Bronze page must contain valid UTF-8."
            ) from exc

        try:
            parsed = cast(object, json.loads(text))
        except json.JSONDecodeError as exc:
            raise ValueError(
                "GHSA Bronze page must contain valid JSON."
            ) from exc

        if not isinstance(parsed, list):
            raise ValueError(
                "GHSA Bronze page top-level JSON value must be an array."
            )

        advisories: list[dict[str, object]] = []

        for source_index, value in enumerate(cast(list[object], parsed)):
            if not isinstance(value, dict):
                raise ValueError(
                    "GHSA Bronze page advisory "
                    f"at source_index={source_index} must be an object."
                )

            advisories.append(cast(dict[str, object], value))

        return tuple(advisories)
