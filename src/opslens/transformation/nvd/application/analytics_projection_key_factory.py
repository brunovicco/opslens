"""Deterministic key construction for permanent NVD analytics projection."""

from dataclasses import dataclass

from opslens.transformation.nvd.application.analytics_projection_models import (
    NvdBootstrapAnalyticsProjectionRequestV1,
    NvdIncrementalAnalyticsProjectionRequestV1,
)
from opslens.transformation.nvd.serialization.schema import (
    NVD_CVE_VERSIONS_SCHEMA_VERSION,
)

NvdAnalyticsProjectionRequestV1 = (
    NvdIncrementalAnalyticsProjectionRequestV1
    | NvdBootstrapAnalyticsProjectionRequestV1
)


@dataclass(frozen=True, slots=True)
class NvdAnalyticsProjectionKeyV1:
    """Describe one deterministic permanent analytics destination."""

    object_key: str
    source_kind_partition: str
    projection_date: str

    def __post_init__(self) -> None:
        """Validate the bounded Glue/Athena partition coordinates."""
        if not self.object_key.strip() or self.object_key != self.object_key.strip():
            raise ValueError(
                "NVD analytics destination object_key must be non-empty and trimmed."
            )

        if self.source_kind_partition not in {"bootstrap", "incremental"}:
            raise ValueError(
                "NVD analytics source_kind_partition must be bootstrap or incremental."
            )

        if len(self.projection_date) != 10:
            raise ValueError(
                "NVD analytics projection_date must use YYYY-MM-DD format."
            )


class NvdAnalyticsProjectionKeyFactoryV1:
    """Build permanent clean-Parquet destinations without runtime discovery."""

    DEFAULT_PREFIX = "analytics/nvd/cve"

    def __init__(self, prefix: str = DEFAULT_PREFIX) -> None:
        """Initialize the analytics key factory with one explicit root."""
        normalized = prefix.strip("/")

        if not normalized:
            raise ValueError("NVD analytics prefix cannot be empty.")

        self._prefix = normalized

    def build(
        self,
        request: NvdAnalyticsProjectionRequestV1,
    ) -> NvdAnalyticsProjectionKeyV1:
        """Build one deterministic destination for an authorized source batch."""
        projection_date = request.projection_date.isoformat()
        source_kind = request.source_kind.value
        base = (
            f"{self._prefix}/"
            f"schema_version={NVD_CVE_VERSIONS_SCHEMA_VERSION}/"
            f"source_kind={source_kind}/"
            f"projection_date={projection_date}"
        )

        if isinstance(
            request,
            NvdIncrementalAnalyticsProjectionRequestV1,
        ):
            filename = f"update_id={request.update_id}.parquet"
        elif isinstance(
            request,
            NvdBootstrapAnalyticsProjectionRequestV1,
        ):
            filename = f"feed_revision={request.feed_revision}.parquet"
        else:
            raise TypeError("Unsupported NVD analytics projection request type.")

        return NvdAnalyticsProjectionKeyV1(
            object_key=f"{base}/{filename}",
            source_kind_partition=source_kind,
            projection_date=projection_date,
        )
