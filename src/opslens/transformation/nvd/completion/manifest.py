"""Deterministic COMPLETE manifest for NVD Silver v1."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import ClassVar

from opslens.transformation.nvd.completion.key_factory import (
    NvdSilverKeyFactoryV1,
    NvdSilverObjectKeysV1,
)
from opslens.transformation.nvd.provenance.models import (
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.serialization.logical_hash import (
    NvdLogicalRecordSetHasherV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverParquetArtifactV1,
    NvdSilverRecordV1,
    NvdSilverSourceKind,
)
from opslens.transformation.nvd.serialization.parquet import (
    NVD_PARQUET_WRITER_CONTRACT_VERSION,
    NvdSilverParquetSerializerV1,
)
from opslens.transformation.nvd.serialization.schema import (
    NVD_CVE_VERSIONS_SCHEMA_NAME,
    NVD_CVE_VERSIONS_SCHEMA_VERSION,
)


@dataclass(frozen=True, slots=True)
class NvdSilverStoredObjectV1:
    """Describe the exact persisted Silver Parquet object."""

    key: str
    version_id: str
    sha256: str
    size_bytes: int
    row_count: int

    def __post_init__(self) -> None:
        """Validate exact persisted Silver object evidence."""
        if not self.key.strip():
            raise ValueError("NVD Silver object key cannot be empty.")

        if not self.version_id.strip():
            raise ValueError("NVD Silver object VersionId cannot be empty.")

        if len(self.sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.sha256
        ):
            raise ValueError("NVD Silver object SHA-256 is invalid.")

        if type(self.size_bytes) is not int or self.size_bytes <= 0:
            raise ValueError("NVD Silver object size must be positive.")

        if type(self.row_count) is not int or self.row_count < 0:
            raise ValueError("NVD Silver object row_count must be non-negative.")


@dataclass(frozen=True, slots=True)
class NvdSilverCompletionManifestV1:
    """Represent COMPLETE evidence for one NVD Silver source batch."""

    MANIFEST_VERSION: ClassVar[str] = "1"
    COMPLETION_STATUS: ClassVar[str] = "complete"

    bronze_evidence: VerifiedNvdBronzeEvidenceV1
    silver_object: NvdSilverStoredObjectV1
    logical_record_set_sha256: str
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate deterministic Silver completion evidence."""
        if len(self.logical_record_set_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.logical_record_set_sha256
        ):
            raise ValueError("NVD logical record-set SHA-256 is invalid.")

        if self.warnings != tuple(sorted(set(self.warnings))):
            raise ValueError("NVD Silver warnings must be sorted and unique.")

        if any(not warning.strip() for warning in self.warnings):
            raise ValueError("NVD Silver warnings cannot contain empty values.")


@dataclass(frozen=True, slots=True)
class NvdSilverCompletionArtifactV1:
    """Represent deterministic manifest bytes and their destination key."""

    manifest: NvdSilverCompletionManifestV1
    manifest_key: str
    manifest_bytes: bytes
    manifest_sha256: str

    def __post_init__(self) -> None:
        """Validate manifest artifact integrity."""
        if not self.manifest_key.strip():
            raise ValueError("NVD Silver manifest key cannot be empty.")

        if not self.manifest_bytes:
            raise ValueError("NVD Silver manifest bytes cannot be empty.")

        expected = sha256(self.manifest_bytes).hexdigest()

        if self.manifest_sha256 != expected:
            raise ValueError("NVD Silver manifest SHA-256 does not match bytes.")


class NvdSilverCompletionManifestFactoryV1:
    """Build COMPLETE evidence only from verified inputs and output."""

    def __init__(
        self,
        *,
        key_factory: NvdSilverKeyFactoryV1 | None = None,
        logical_hasher: NvdLogicalRecordSetHasherV1 | None = None,
    ) -> None:
        """Initialize deterministic completion dependencies."""
        self._key_factory = key_factory if key_factory is not None else NvdSilverKeyFactoryV1()
        self._logical_hasher = (
            logical_hasher if logical_hasher is not None else NvdLogicalRecordSetHasherV1()
        )

    def build(
        self,
        *,
        evidence: VerifiedNvdBronzeEvidenceV1,
        records: tuple[NvdSilverRecordV1, ...],
        parquet_artifact: NvdSilverParquetArtifactV1,
        silver_object_version_id: str,
        additional_warnings: tuple[str, ...] = (),
    ) -> tuple[
        NvdSilverCompletionManifestV1,
        NvdSilverObjectKeysV1,
    ]:
        """Bind exact Bronze evidence to exact persisted Silver output."""
        self._validate_record_count(
            evidence=evidence,
            records=records,
        )

        if parquet_artifact.source_kind is not evidence.source_kind:
            raise ValueError("NVD Silver artifact source_kind does not match Bronze.")

        if parquet_artifact.source_batch_id != evidence.source_batch_id:
            raise ValueError("NVD Silver artifact source_batch_id does not match Bronze.")

        if parquet_artifact.row_count != len(records):
            raise ValueError("NVD Silver artifact row_count does not match record set.")

        if not silver_object_version_id.strip():
            raise ValueError("NVD Silver completion requires exact S3 VersionId.")

        for record in records:
            self._validate_record_provenance(
                evidence=evidence,
                record=record,
            )

        parquet_serializer = NvdSilverParquetSerializerV1()

        if records:
            expected_parquet = parquet_serializer.serialize(records)
        else:
            expected_parquet = parquet_serializer.serialize_empty(
                source_kind=evidence.source_kind,
                source_batch_id=evidence.source_batch_id,
            )

        if parquet_artifact.parquet_bytes != expected_parquet.parquet_bytes:
            raise ValueError(
                "NVD Silver Parquet artifact does not match "
                "the deterministic serialization of the logical "
                "record set."
            )

        if parquet_artifact.parquet_sha256 != expected_parquet.parquet_sha256:
            raise ValueError(
                "NVD Silver Parquet SHA-256 does not match the deterministic logical record set."
            )
        keys = self._key_factory.build(evidence)

        stored_object = NvdSilverStoredObjectV1(
            key=keys.parquet_key,
            version_id=silver_object_version_id,
            sha256=parquet_artifact.parquet_sha256,
            size_bytes=parquet_artifact.size_bytes,
            row_count=parquet_artifact.row_count,
        )

        warnings = self._build_warnings(
            records=records,
            additional_warnings=additional_warnings,
        )

        manifest = NvdSilverCompletionManifestV1(
            bronze_evidence=evidence,
            silver_object=stored_object,
            logical_record_set_sha256=(self._logical_hasher.digest(records)),
            warnings=warnings,
        )

        return manifest, keys

    @staticmethod
    def _validate_record_count(
        *,
        evidence: VerifiedNvdBronzeEvidenceV1,
        records: tuple[NvdSilverRecordV1, ...],
    ) -> None:
        """Require Silver cardinality to match verified Bronze evidence."""
        if evidence.source_kind is NvdSilverSourceKind.INCREMENTAL:
            expected = evidence.incremental_total_results

            if type(expected) is not int or expected < 0:
                raise ValueError("Verified incremental Bronze evidence lacks valid total_results.")

            if len(records) != expected:
                raise ValueError(
                    "NVD Silver record count does not match verified Bronze total_results."
                )

            return

        if not records:
            raise ValueError("NVD bootstrap Silver completion requires records.")

    @staticmethod
    def _validate_record_provenance(
        *,
        evidence: VerifiedNvdBronzeEvidenceV1,
        record: NvdSilverRecordV1,
    ) -> None:
        """Require every row to bind to the same verified Bronze evidence."""
        provenance = record.provenance

        if provenance.source_kind is not evidence.source_kind:
            raise ValueError("NVD Silver row source_kind does not match Bronze.")

        if provenance.source_batch_id != evidence.source_batch_id:
            raise ValueError("NVD Silver row source_batch_id does not match Bronze.")

        if provenance.bronze_manifest_key != evidence.manifest_key:
            raise ValueError("NVD Silver row Bronze manifest key does not match.")

        if provenance.bronze_manifest_version_id != evidence.manifest_version_id:
            raise ValueError("NVD Silver row Bronze manifest VersionId does not match.")

        if provenance.bronze_manifest_sha256 != evidence.manifest_sha256:
            raise ValueError("NVD Silver row Bronze manifest SHA-256 does not match.")

        reference = evidence.object_by_key(provenance.bronze_object_key)

        if provenance.bronze_object_version_id != reference.version_id:
            raise ValueError("NVD Silver row Bronze object VersionId does not match.")

        if provenance.bronze_object_sha256 != reference.sha256:
            raise ValueError("NVD Silver row Bronze object SHA-256 does not match.")

        if evidence.source_kind is NvdSilverSourceKind.INCREMENTAL:
            if provenance.incremental_update_id != evidence.incremental_update_id:
                raise ValueError("NVD Silver row update_id does not match Bronze.")

            if provenance.incremental_page_start != reference.page_start:
                raise ValueError("NVD Silver row page_start does not match Bronze.")

        else:
            if provenance.bootstrap_feed_year != evidence.bootstrap_feed_year:
                raise ValueError("NVD Silver row feed year does not match Bronze.")

            if provenance.bootstrap_feed_revision != evidence.bootstrap_feed_revision:
                raise ValueError("NVD Silver row feed revision does not match Bronze.")

    @staticmethod
    def _build_warnings(
        *,
        records: tuple[NvdSilverRecordV1, ...],
        additional_warnings: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Collect deterministic non-fatal Silver warnings."""
        warning_values: set[str] = set()

        for warning in additional_warnings:
            normalized = warning.strip()

            if not normalized:
                raise ValueError("NVD Silver additional warning cannot be empty.")

            warning_values.add(normalized)

        for record in records:
            for family in record.cvss.unsupported_cvss_families:
                warning_values.add(f"unsupported_cvss_family:{family}")

        return tuple(sorted(warning_values))


class NvdSilverCompletionManifestSerializerV1:
    """Serialize Silver COMPLETE evidence deterministically."""

    def serialize(
        self,
        *,
        manifest: NvdSilverCompletionManifestV1,
        manifest_key: str,
    ) -> NvdSilverCompletionArtifactV1:
        """Return canonical COMPLETE manifest bytes."""
        evidence = manifest.bronze_evidence

        objects: list[dict[str, object]] = []

        for item in evidence.objects:
            document: dict[str, object] = {
                "key": item.key,
                "role": item.role.value,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
                "version_id": item.version_id,
            }

            if item.page_start is not None:
                document["page_start"] = item.page_start

            if item.source_timestamp is not None:
                document["source_timestamp"] = item.source_timestamp

            objects.append(document)

        source_coordinates: dict[str, object]

        if evidence.source_kind is NvdSilverSourceKind.BOOTSTRAP:
            source_time = evidence.bootstrap_source_observed_at

            if source_time is None:
                raise ValueError("Bootstrap completion evidence lacks source timestamp.")

            source_coordinates = {
                "feed_revision": evidence.bootstrap_feed_revision,
                "feed_year": evidence.bootstrap_feed_year,
                "source_observed_at": self._format_utc(source_time),
            }

        else:
            window_start = evidence.incremental_window_start_at
            window_end = evidence.incremental_window_end_at

            if window_start is None or window_end is None:
                raise ValueError("Incremental completion evidence lacks window.")

            source_coordinates = {
                "total_results": evidence.incremental_total_results,
                "update_id": evidence.incremental_update_id,
                "window_end_at": self._format_utc(window_end),
                "window_start_at": self._format_utc(window_start),
            }

        document: dict[str, object] = {
            "bronze_manifest": {
                "key": evidence.manifest_key,
                "sha256": evidence.manifest_sha256,
                "size_bytes": evidence.manifest_size_bytes,
                "version_id": evidence.manifest_version_id,
            },
            "bronze_objects": objects,
            "completion_status": manifest.COMPLETION_STATUS,
            "dataset": NVD_CVE_VERSIONS_SCHEMA_NAME,
            "logical_record_set_sha256": (manifest.logical_record_set_sha256),
            "manifest_version": manifest.MANIFEST_VERSION,
            "schema_version": NVD_CVE_VERSIONS_SCHEMA_VERSION,
            "silver_object": {
                "key": manifest.silver_object.key,
                "row_count": manifest.silver_object.row_count,
                "sha256": manifest.silver_object.sha256,
                "size_bytes": manifest.silver_object.size_bytes,
                "version_id": manifest.silver_object.version_id,
            },
            "source_batch_id": evidence.source_batch_id,
            "source_coordinates": source_coordinates,
            "source_kind": evidence.source_kind.value,
            "warnings": list(manifest.warnings),
            "writer_contract_version": (NVD_PARQUET_WRITER_CONTRACT_VERSION),
        }

        text = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )

        raw_bytes = f"{text}\n".encode()

        return NvdSilverCompletionArtifactV1(
            manifest=manifest,
            manifest_key=manifest_key,
            manifest_bytes=raw_bytes,
            manifest_sha256=sha256(raw_bytes).hexdigest(),
        )

    @staticmethod
    def _format_utc(
        value: datetime,
    ) -> str:
        """Serialize one timestamp deterministically as UTC."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("NVD Silver completion timestamp must be timezone-aware.")

        normalized = value.astimezone(UTC)
        timespec = "microseconds" if normalized.microsecond else "seconds"

        return normalized.isoformat(timespec=timespec).replace("+00:00", "Z")
