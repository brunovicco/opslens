"""Bind the S3 analytics repository to the application replay contract."""

from opslens.transformation.nvd.adapters.outbound.s3_analytics_projection import (
    NvdAnalyticsProjectionAlreadyExistsError,
    S3NvdAnalyticsProjectionRepositoryV1,
)
from opslens.transformation.nvd.application.analytics_projection_key_factory import (
    NvdAnalyticsProjectionKeyV1,
    NvdAnalyticsProjectionRequestV1,
)
from opslens.transformation.nvd.application.analytics_projection_models import (
    NvdAnalyticsExactObjectRefV1,
)
from opslens.transformation.nvd.application.analytics_projection_service import (
    NvdAnalyticsProjectionReplayRequiredError,
)


class NvdAnalyticsProjectionRepositoryBindingV1:
    """Translate provider-specific replay collisions into the application port."""

    def __init__(
        self,
        *,
        repository: S3NvdAnalyticsProjectionRepositoryV1,
    ) -> None:
        """Initialize the binding around one exact S3 projection repository."""
        self._repository = repository

    def copy_if_absent(
        self,
        *,
        request: NvdAnalyticsProjectionRequestV1,
        destination: NvdAnalyticsProjectionKeyV1,
    ) -> NvdAnalyticsExactObjectRefV1:
        """Create one projection or signal application-level replay verification."""
        try:
            return self._repository.copy_if_absent(
                request=request,
                destination=destination,
            )
        except NvdAnalyticsProjectionAlreadyExistsError as exc:
            raise NvdAnalyticsProjectionReplayRequiredError(
                "NVD analytics destination exists and requires exact replay verification."
            ) from exc

    def verify_current(
        self,
        *,
        request: NvdAnalyticsProjectionRequestV1,
        destination: NvdAnalyticsProjectionKeyV1,
    ) -> NvdAnalyticsExactObjectRefV1:
        """Delegate exact current-destination replay verification."""
        return self._repository.verify_current(
            request=request,
            destination=destination,
        )
