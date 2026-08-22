"""Compose fully normalized NVD Silver records from verified source observations."""

from opslens.transformation.nvd.application.source_reader import (
    NvdSilverSourceRecordV1,
)
from opslens.transformation.nvd.domain.collections_transformer import (
    NvdCveCollectionsTransformer,
)
from opslens.transformation.nvd.domain.configurations_transformer import (
    NvdCpeConfigurationsTransformer,
)
from opslens.transformation.nvd.domain.cvss_transformer import (
    NvdCvssMetricsTransformer,
)
from opslens.transformation.nvd.domain.transformer import (
    NvdCveCoreTransformer,
)
from opslens.transformation.nvd.provenance.models import (
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.provenance.verifier import (
    NvdSilverProvenanceFactoryV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverRecordV1,
)


class NvdSilverRecordComposerV1:
    """Compose one deterministic Silver record from one verified source CVE."""

    def __init__(
        self,
        *,
        core_transformer: NvdCveCoreTransformer,
        collections_transformer: NvdCveCollectionsTransformer,
        cvss_transformer: NvdCvssMetricsTransformer,
        configurations_transformer: NvdCpeConfigurationsTransformer,
        provenance_factory: NvdSilverProvenanceFactoryV1,
    ) -> None:
        """Initialize explicit deterministic record dependencies."""
        self._core_transformer = core_transformer
        self._collections_transformer = collections_transformer
        self._cvss_transformer = cvss_transformer
        self._configurations_transformer = configurations_transformer
        self._provenance_factory = provenance_factory

    def compose(
        self,
        *,
        evidence: VerifiedNvdBronzeEvidenceV1,
        source_record: NvdSilverSourceRecordV1,
    ) -> NvdSilverRecordV1:
        """Normalize one source observation into Silver schema-v1 domain form."""
        provenance = self._provenance_factory.build(
            evidence=evidence,
            bronze_object_key=source_record.bronze_object_key,
            record_index=source_record.record_index,
        )

        source_cve = source_record.source_cve

        return NvdSilverRecordV1(
            core=self._core_transformer.transform(source_cve),
            collections=self._collections_transformer.transform(source_cve),
            cvss=self._cvss_transformer.transform(source_cve),
            configurations=self._configurations_transformer.transform(source_cve),
            provenance=provenance,
        )
