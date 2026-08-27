"""Compose fully normalized GHSA Silver logical records."""

from opslens.transformation.ghsa.domain.collections_transformer import (
    GhsaAdvisoryCollectionsTransformer,
)
from opslens.transformation.ghsa.domain.transformer import (
    GhsaAdvisoryCoreTransformer,
)
from opslens.transformation.ghsa.domain.vulnerabilities_transformer import (
    GhsaVulnerabilitiesTransformer,
)
from opslens.transformation.ghsa.serialization.models import (
    GhsaSilverRecordV1,
)


class GhsaSilverRecordComposerV1:
    """Compose one deterministic Silver logical record from one source advisory."""

    def __init__(
        self,
        *,
        core_transformer: GhsaAdvisoryCoreTransformer,
        collections_transformer: GhsaAdvisoryCollectionsTransformer,
        vulnerabilities_transformer: GhsaVulnerabilitiesTransformer,
    ) -> None:
        """Initialize explicit deterministic normalization dependencies."""
        self._core_transformer = core_transformer
        self._collections_transformer = collections_transformer
        self._vulnerabilities_transformer = vulnerabilities_transformer

    def compose(self, source_advisory: dict[str, object]) -> GhsaSilverRecordV1:
        """Normalize one complete reviewed GHSA into Silver schema-v1 domain form."""
        return GhsaSilverRecordV1(
            core=self._core_transformer.transform(source_advisory),
            collections=self._collections_transformer.transform(source_advisory),
            vulnerabilities=self._vulnerabilities_transformer.transform(source_advisory),
        )
