"""Application-boundary models for NVD Silver orchestration."""

from dataclasses import dataclass

from opslens.transformation.nvd.completion.key_factory import (
    NvdSilverObjectKeysV1,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectPayloadV1,
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverParquetArtifactV1,
    NvdSilverRecordV1,
    NvdSilverSourceKind,
)


@dataclass(frozen=True, slots=True)
class NvdSilverTransformRequestV1:
    """Carry one exact Bronze batch into Silver application orchestration.

    This model validates only the application envelope.

    Trust in the manifest and supplied object bytes is established later by
    NvdBronzeEvidenceVerifierV1.
    """

    source_kind: NvdSilverSourceKind
    manifest_key: str
    manifest_version_id: str
    manifest_bytes: bytes
    object_payloads: tuple[NvdBronzeObjectPayloadV1, ...]

    def __post_init__(self) -> None:
        """Validate required application coordinates without verifying evidence."""
        if not self.manifest_key.strip():
            raise ValueError("NVD Silver request manifest_key cannot be empty.")

        if not self.manifest_version_id.strip():
            raise ValueError("NVD Silver request manifest_version_id cannot be empty.")

        if not self.manifest_bytes:
            raise ValueError("NVD Silver request manifest_bytes cannot be empty.")


@dataclass(frozen=True, slots=True)
class NvdSilverPreparedBatchV1:
    """Represent one verified and serialized Silver batch before persistence."""

    evidence: VerifiedNvdBronzeEvidenceV1
    records: tuple[NvdSilverRecordV1, ...]
    parquet_artifact: NvdSilverParquetArtifactV1
    keys: NvdSilverObjectKeysV1

    def __post_init__(self) -> None:
        """Require prepared output to remain bound to verified Bronze evidence."""
        if self.parquet_artifact.source_kind is not self.evidence.source_kind:
            raise ValueError("Prepared NVD Silver artifact source_kind does not match Bronze.")

        if self.parquet_artifact.source_batch_id != self.evidence.source_batch_id:
            raise ValueError("Prepared NVD Silver artifact source_batch_id does not match Bronze.")

        if self.parquet_artifact.row_count != len(self.records):
            raise ValueError("Prepared NVD Silver artifact row_count does not match records.")

        if self.evidence.source_kind is NvdSilverSourceKind.BOOTSTRAP:
            if not self.records:
                raise ValueError("Prepared bootstrap NVD Silver batch requires records.")

        elif self.evidence.source_kind is NvdSilverSourceKind.INCREMENTAL:
            expected = self.evidence.incremental_total_results

            if type(expected) is not int or expected != len(self.records):
                raise ValueError(
                    "Prepared incremental NVD Silver record count "
                    "does not match Bronze total_results."
                )

        if not self.keys.parquet_key.strip():
            raise ValueError("Prepared NVD Silver parquet_key cannot be empty.")

        if not self.keys.manifest_key.strip():
            raise ValueError("Prepared NVD Silver manifest_key cannot be empty.")

        if self.keys.parquet_key == self.keys.manifest_key:
            raise ValueError("Prepared NVD Silver Parquet and manifest keys must differ.")
