"""Deterministic COMPLETE evidence for GHSA Silver attempt persistence."""

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import ClassVar

from opslens.transformation.ghsa.completion.key_factory import (
    GhsaSilverKeyFactoryV1,
)
from opslens.transformation.ghsa.completion.models import (
    GhsaSilverStoredContentObjectV1,
)
from opslens.transformation.ghsa.runtime.materializer import (
    GhsaSilverAttemptContextV1,
    GhsaSilverMaterializationV1,
)
from opslens.transformation.ghsa.serialization.parquet import (
    GHSA_PARQUET_WRITER_CONTRACT_VERSION,
)
from opslens.transformation.ghsa.serialization.schema import (
    GHSA_ADVISORY_VERSIONS_SCHEMA_NAME,
    GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class GhsaSilverCompletionOccurrenceV1:
    """Bind one Bronze occurrence to one exact persisted Silver content object."""

    page_ordinal: int
    source_index: int
    page_key: str
    page_version_id: str
    ghsa_id: str
    observed_advisory_version_id: str
    source_advisory_sha256: str
    silver_object: GhsaSilverStoredContentObjectV1

    def __post_init__(self) -> None:
        """Validate exact occurrence-to-content identity binding."""
        if type(self.page_ordinal) is not int or self.page_ordinal < 1:
            raise ValueError(
                "GHSA Silver completion page_ordinal must be positive."
            )

        if type(self.source_index) is not int or self.source_index < 0:
            raise ValueError(
                "GHSA Silver completion source_index must be non-negative."
            )

        for field_name, value in (
            ("page_key", self.page_key),
            ("page_version_id", self.page_version_id),
            ("ghsa_id", self.ghsa_id),
            (
                "observed_advisory_version_id",
                self.observed_advisory_version_id,
            ),
        ):
            if not value.strip():
                raise ValueError(
                    f"GHSA Silver completion {field_name} cannot be empty."
                )

        if _SHA256_PATTERN.fullmatch(self.source_advisory_sha256) is None:
            raise ValueError(
                "GHSA Silver completion source_advisory_sha256 is invalid."
            )

        if self.silver_object.ghsa_id != self.ghsa_id:
            raise ValueError(
                "GHSA Silver completion stored object ghsa_id does not match."
            )

        if (
            self.silver_object.observed_advisory_version_id
            != self.observed_advisory_version_id
        ):
            raise ValueError(
                "GHSA Silver completion stored object content identity "
                "does not match."
            )

        if (
            self.silver_object.source_advisory_sha256
            != self.source_advisory_sha256
        ):
            raise ValueError(
                "GHSA Silver completion stored object source SHA-256 "
                "does not match."
            )


@dataclass(frozen=True, slots=True)
class GhsaSilverCompletionManifestV1:
    """Represent COMPLETE evidence for one exact GHSA Bronze attempt."""

    MANIFEST_VERSION: ClassVar[str] = "1"
    COMPLETION_STATUS: ClassVar[str] = "complete"

    context: GhsaSilverAttemptContextV1
    logical_record_set_sha256: str
    occurrences: tuple[GhsaSilverCompletionOccurrenceV1, ...]

    def __post_init__(self) -> None:
        """Validate deterministic attempt-level completion evidence."""
        if _SHA256_PATTERN.fullmatch(self.logical_record_set_sha256) is None:
            raise ValueError(
                "GHSA Silver completion logical record-set SHA-256 is invalid."
            )

        ordered = tuple(
            sorted(
                self.occurrences,
                key=lambda item: (
                    item.page_ordinal,
                    item.source_index,
                ),
            )
        )

        if self.occurrences != ordered:
            raise ValueError(
                "GHSA Silver completion occurrences must use source order."
            )

        positions = tuple(
            (item.page_ordinal, item.source_index)
            for item in self.occurrences
        )

        if len(positions) != len(set(positions)):
            raise ValueError(
                "GHSA Silver completion contains duplicate occurrence positions."
            )

        observed_ids = tuple(
            item.observed_advisory_version_id
            for item in self.occurrences
        )

        if len(observed_ids) != len(set(observed_ids)):
            raise ValueError(
                "GHSA Silver completion contains duplicate content identities."
            )

    @property
    def record_count(self) -> int:
        """Return the number of exact advisory content versions completed."""
        return len(self.occurrences)


@dataclass(frozen=True, slots=True)
class GhsaSilverCompletionArtifactV1:
    """Represent canonical COMPLETE manifest bytes and destination identity."""

    manifest: GhsaSilverCompletionManifestV1
    key: str
    manifest_bytes: bytes
    manifest_sha256: str

    def __post_init__(self) -> None:
        """Validate deterministic completion artifact integrity."""
        if not self.key.strip():
            raise ValueError("GHSA Silver completion artifact key cannot be empty.")

        if not self.manifest_bytes:
            raise ValueError(
                "GHSA Silver completion artifact bytes cannot be empty."
            )

        if self.manifest_sha256 != sha256(self.manifest_bytes).hexdigest():
            raise ValueError(
                "GHSA Silver completion manifest SHA-256 does not match bytes."
            )


class GhsaSilverCompletionManifestFactoryV1:
    """Bind logical attempt evidence to exact persisted content objects."""

    def __init__(
        self,
        *,
        key_factory: GhsaSilverKeyFactoryV1,
    ) -> None:
        """Initialize deterministic completion dependencies."""
        self._key_factory = key_factory

    def build(
        self,
        *,
        materialization: GhsaSilverMaterializationV1,
        stored_objects: tuple[GhsaSilverStoredContentObjectV1, ...],
    ) -> GhsaSilverCompletionManifestV1:
        """Build COMPLETE evidence only when every binding has exact storage."""
        by_observed_id = self._stored_objects_by_observed_id(stored_objects)
        occurrences: list[GhsaSilverCompletionOccurrenceV1] = []

        for binding in materialization.bindings:
            occurrence = binding.occurrence
            observed_id = occurrence.observed_advisory_version_id
            stored = by_observed_id.pop(observed_id, None)

            if stored is None:
                raise ValueError(
                    "GHSA Silver completion lacks persisted content for "
                    f"{observed_id}."
                )

            expected_key = self._key_factory.build_content_object_key(
                occurrence.observed_version
            )

            if stored.key != expected_key:
                raise ValueError(
                    "GHSA Silver completion stored content key does not match "
                    "the deterministic content identity."
                )

            occurrences.append(
                GhsaSilverCompletionOccurrenceV1(
                    page_ordinal=occurrence.page_ordinal,
                    source_index=occurrence.source_index,
                    page_key=occurrence.page_key,
                    page_version_id=occurrence.page_version_id,
                    ghsa_id=occurrence.ghsa_id,
                    observed_advisory_version_id=observed_id,
                    source_advisory_sha256=(
                        occurrence.source_advisory_sha256
                    ),
                    silver_object=stored,
                )
            )

        if by_observed_id:
            raise ValueError(
                "GHSA Silver completion contains persisted content not present "
                "in the logical materialization."
            )

        return GhsaSilverCompletionManifestV1(
            context=materialization.context,
            logical_record_set_sha256=(
                materialization.logical_record_set_sha256
            ),
            occurrences=tuple(occurrences),
        )

    @staticmethod
    def _stored_objects_by_observed_id(
        stored_objects: tuple[GhsaSilverStoredContentObjectV1, ...],
    ) -> dict[str, GhsaSilverStoredContentObjectV1]:
        """Index stored content objects and reject duplicate evidence."""
        result: dict[str, GhsaSilverStoredContentObjectV1] = {}

        for stored in stored_objects:
            observed_id = stored.observed_advisory_version_id

            if observed_id in result:
                raise ValueError(
                    "GHSA Silver completion contains duplicate stored content "
                    "identity."
                )

            result[observed_id] = stored

        return result


class GhsaSilverCompletionManifestSerializerV1:
    """Serialize GHSA Silver COMPLETE evidence deterministically."""

    def __init__(
        self,
        *,
        key_factory: GhsaSilverKeyFactoryV1,
    ) -> None:
        """Initialize deterministic completion-key dependency."""
        self._key_factory = key_factory

    def serialize(
        self,
        manifest: GhsaSilverCompletionManifestV1,
    ) -> GhsaSilverCompletionArtifactV1:
        """Return canonical COMPLETE manifest bytes."""
        context = manifest.context
        occurrences: list[dict[str, object]] = []

        for item in manifest.occurrences:
            stored = item.silver_object
            occurrences.append(
                {
                    "attempt_occurrence_id": self._attempt_occurrence_id(
                        attempt_id=context.attempt_id,
                        page_ordinal=item.page_ordinal,
                        source_index=item.source_index,
                    ),
                    "bronze_page": {
                        "key": item.page_key,
                        "version_id": item.page_version_id,
                    },
                    "ghsa_id": item.ghsa_id,
                    "observed_advisory_version_id": (
                        item.observed_advisory_version_id
                    ),
                    "page_ordinal": item.page_ordinal,
                    "silver_content_object": {
                        "key": stored.key,
                        "parquet_sha256": stored.parquet_sha256,
                        "row_count": stored.row_count,
                        "size_bytes": stored.size_bytes,
                        "version_id": stored.version_id,
                    },
                    "source_advisory_sha256": (
                        item.source_advisory_sha256
                    ),
                    "source_index": item.source_index,
                }
            )

        document: dict[str, object] = {
            "attempt_id": context.attempt_id,
            "bronze_manifest": {
                "key": context.manifest_key,
                "version_id": context.manifest_version_id,
            },
            "completion_status": manifest.COMPLETION_STATUS,
            "dataset": GHSA_ADVISORY_VERSIONS_SCHEMA_NAME,
            "logical_record_set_sha256": (
                manifest.logical_record_set_sha256
            ),
            "manifest_version": manifest.MANIFEST_VERSION,
            "occurrences": occurrences,
            "record_count": manifest.record_count,
            "schema_version": GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION,
            "sync_id": context.sync_id,
            "writer_contract_version": GHSA_PARQUET_WRITER_CONTRACT_VERSION,
        }
        text = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        raw_bytes = f"{text}\n".encode()
        key = self._key_factory.build_completion_manifest_key(context)

        return GhsaSilverCompletionArtifactV1(
            manifest=manifest,
            key=key,
            manifest_bytes=raw_bytes,
            manifest_sha256=sha256(raw_bytes).hexdigest(),
        )

    @staticmethod
    def _attempt_occurrence_id(
        *,
        attempt_id: str,
        page_ordinal: int,
        source_index: int,
    ) -> str:
        """Build the exact occurrence identifier already frozen by runtime."""
        return (
            f"{attempt_id}/"
            f"page:{page_ordinal:06d}/"
            f"item:{source_index:03d}"
        )
