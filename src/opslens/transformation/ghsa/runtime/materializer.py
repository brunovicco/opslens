"""Materialize verified GHSA Silver records deterministically in memory."""

import re
from dataclasses import dataclass

from opslens.transformation.ghsa.runtime.record_processor import (
    GhsaSilverOccurrenceRecordV1,
)
from opslens.transformation.ghsa.serialization.logical_hash import (
    GhsaLogicalRecordSetHasherV1,
)
from opslens.transformation.ghsa.serialization.models import (
    GhsaSilverParquetArtifactV1,
)
from opslens.transformation.ghsa.serialization.parquet import (
    GhsaSilverParquetSerializerV1,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class GhsaSilverAttemptContextV1:
    """Identify the exact Bronze attempt being materialized into Silver."""

    sync_id: str
    attempt_id: str
    manifest_key: str
    manifest_version_id: str

    def __post_init__(self) -> None:
        """Validate immutable Bronze attempt coordinates."""
        self._require_sha256(self.sync_id, "sync_id")
        self._require_sha256(self.attempt_id, "attempt_id")

        for field_name, value in (
            ("manifest_key", self.manifest_key),
            ("manifest_version_id", self.manifest_version_id),
        ):
            if not value.strip():
                raise ValueError(
                    f"GHSA Silver attempt context {field_name} cannot be empty."
                )

    @staticmethod
    def _require_sha256(value: str, field_name: str) -> None:
        """Require a lowercase hexadecimal SHA-256 digest."""
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError(
                f"GHSA Silver attempt context {field_name} must be "
                "a lowercase SHA-256 digest."
            )


@dataclass(frozen=True, slots=True)
class GhsaSilverMaterializationV1:
    """Represent deterministic in-memory Silver output for one Bronze attempt."""

    context: GhsaSilverAttemptContextV1
    bindings: tuple[GhsaSilverOccurrenceRecordV1, ...]
    logical_record_set_sha256: str
    parquet_artifact: GhsaSilverParquetArtifactV1 | None

    def __post_init__(self) -> None:
        """Validate materialized logical and physical Silver invariants."""
        if _SHA256_PATTERN.fullmatch(self.logical_record_set_sha256) is None:
            raise ValueError(
                "GHSA Silver logical_record_set_sha256 must be "
                "a lowercase SHA-256 digest."
            )

        if not self.bindings:
            if self.parquet_artifact is not None:
                raise ValueError(
                    "Empty GHSA Silver materialization cannot contain "
                    "a Parquet artifact."
                )
            return

        if self.parquet_artifact is None:
            raise ValueError(
                "Non-empty GHSA Silver materialization requires "
                "a Parquet artifact."
            )

        if self.parquet_artifact.row_count != len(self.bindings):
            raise ValueError(
                "GHSA Silver Parquet row_count does not match "
                "the bound record count."
            )

    @property
    def record_count(self) -> int:
        """Return the number of exact advisory content versions materialized."""
        return len(self.bindings)


class GhsaSilverMaterializerV1:
    """Build logical and physical Silver artifacts from verified bindings."""

    def __init__(
        self,
        *,
        logical_hasher: GhsaLogicalRecordSetHasherV1,
        parquet_serializer: GhsaSilverParquetSerializerV1,
    ) -> None:
        """Initialize frozen Silver serialization dependencies."""
        self._logical_hasher = logical_hasher
        self._parquet_serializer = parquet_serializer

    def materialize(
        self,
        *,
        context: GhsaSilverAttemptContextV1,
        bindings: tuple[GhsaSilverOccurrenceRecordV1, ...],
    ) -> GhsaSilverMaterializationV1:
        """Materialize one exact Bronze attempt into deterministic Silver."""
        ordered = tuple(
            sorted(
                bindings,
                key=lambda binding: (
                    binding.occurrence.page_ordinal,
                    binding.occurrence.source_index,
                ),
            )
        )

        self._validate_bindings(
            context=context,
            bindings=ordered,
        )

        records = tuple(binding.record for binding in ordered)

        logical_sha256 = self._logical_hasher.digest(records)

        parquet_artifact = (
            self._parquet_serializer.serialize(records)
            if records
            else None
        )

        return GhsaSilverMaterializationV1(
            context=context,
            bindings=ordered,
            logical_record_set_sha256=logical_sha256,
            parquet_artifact=parquet_artifact,
        )

    @staticmethod
    def _validate_bindings(
        *,
        context: GhsaSilverAttemptContextV1,
        bindings: tuple[GhsaSilverOccurrenceRecordV1, ...],
    ) -> None:
        """Require every record to belong to one exact Bronze attempt."""
        attempt_occurrence_ids: set[str] = set()
        observed_version_ids: set[str] = set()

        for binding in bindings:
            occurrence = binding.occurrence

            if occurrence.sync_id != context.sync_id:
                raise ValueError(
                    "GHSA Silver binding sync_id does not match attempt context."
                )

            if occurrence.attempt_id != context.attempt_id:
                raise ValueError(
                    "GHSA Silver binding attempt_id does not match attempt context."
                )

            if occurrence.manifest_key != context.manifest_key:
                raise ValueError(
                    "GHSA Silver binding manifest_key does not match attempt context."
                )

            if (
                occurrence.manifest_version_id
                != context.manifest_version_id
            ):
                raise ValueError(
                    "GHSA Silver binding manifest_version_id does not match "
                    "attempt context."
                )


            attempt_occurrence_id = occurrence.attempt_occurrence_id

            if attempt_occurrence_id in attempt_occurrence_ids:
                raise ValueError(
                    "GHSA Silver materialization contains duplicate "
                    "attempt occurrence identity."
                )

            attempt_occurrence_ids.add(attempt_occurrence_id)

            observed_version_id = (
                occurrence.observed_advisory_version_id
            )

            if observed_version_id in observed_version_ids:
                raise ValueError(
                    "GHSA Silver materialization contains duplicate "
                    "observed_advisory_version_id."
                )

            observed_version_ids.add(observed_version_id)
