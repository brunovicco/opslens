"""Application orchestration for deterministic NVD Bronze-to-Silver preparation."""

from opslens.transformation.nvd.application.models import (
    NvdSilverPreparedBatchV1,
    NvdSilverTransformRequestV1,
)
from opslens.transformation.nvd.application.record_composer import (
    NvdSilverRecordComposerV1,
)
from opslens.transformation.nvd.application.source_reader import (
    NvdSilverSourceBatchReaderV1,
)
from opslens.transformation.nvd.completion.key_factory import (
    NvdSilverKeyFactoryV1,
)
from opslens.transformation.nvd.provenance.models import (
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.provenance.verifier import (
    NvdBronzeEvidenceVerifierV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)
from opslens.transformation.nvd.serialization.parquet import (
    NvdSilverParquetSerializerV1,
)


class NvdSilverPrepareServiceV1:
    """Prepare one verified NVD Bronze batch for immutable Silver persistence."""

    def __init__(
        self,
        *,
        evidence_verifier: NvdBronzeEvidenceVerifierV1,
        source_reader: NvdSilverSourceBatchReaderV1,
        record_composer: NvdSilverRecordComposerV1,
        parquet_serializer: NvdSilverParquetSerializerV1,
        key_factory: NvdSilverKeyFactoryV1,
    ) -> None:
        """Initialize deterministic application dependencies."""
        self._evidence_verifier = evidence_verifier
        self._source_reader = source_reader
        self._record_composer = record_composer
        self._parquet_serializer = parquet_serializer
        self._key_factory = key_factory

    def prepare(
        self,
        request: NvdSilverTransformRequestV1,
    ) -> NvdSilverPreparedBatchV1:
        """Verify, normalize, and serialize one Bronze source batch."""
        evidence = self._verify_request(request)

        source_records = self._source_reader.read(
            evidence=evidence,
            object_payloads=request.object_payloads,
        )

        records = tuple(
            self._record_composer.compose(
                evidence=evidence,
                source_record=source_record,
            )
            for source_record in source_records
        )

        if records:
            parquet_artifact = self._parquet_serializer.serialize(records)
        else:
            parquet_artifact = self._parquet_serializer.serialize_empty(
                source_kind=evidence.source_kind,
                source_batch_id=evidence.source_batch_id,
            )

        keys = self._key_factory.build(evidence)

        return NvdSilverPreparedBatchV1(
            evidence=evidence,
            records=records,
            parquet_artifact=parquet_artifact,
            keys=keys,
        )

    def _verify_request(
        self,
        request: NvdSilverTransformRequestV1,
    ) -> VerifiedNvdBronzeEvidenceV1:
        """Verify the exact Bronze contract selected by source kind."""
        if request.source_kind is NvdSilverSourceKind.BOOTSTRAP:
            return self._evidence_verifier.verify_bootstrap(
                manifest_key=request.manifest_key,
                manifest_version_id=request.manifest_version_id,
                manifest_bytes=request.manifest_bytes,
                object_payloads=request.object_payloads,
            )

        if request.source_kind is NvdSilverSourceKind.INCREMENTAL:
            return self._evidence_verifier.verify_incremental(
                manifest_key=request.manifest_key,
                manifest_version_id=request.manifest_version_id,
                manifest_bytes=request.manifest_bytes,
                object_payloads=request.object_payloads,
            )

        raise ValueError(f"Unsupported NVD Silver source kind {request.source_kind!r}.")
