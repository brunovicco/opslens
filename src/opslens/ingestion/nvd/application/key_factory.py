"""Deterministic S3 object-key generation for NVD Bootstrap Bronze."""

from dataclasses import dataclass

from opslens.ingestion.nvd.domain.source_identity import (
    NvdBootstrapSourceIdentity,
)


@dataclass(frozen=True, slots=True)
class NvdBootstrapObjectKeys:
    """Represent the complete Bronze key set for one NVD feed revision.

    Attributes:
        feed_key: Key for the exact NVD gzip source artifact.
        meta_key: Key for the exact NVD META source artifact.
        manifest_key: Reserved key for the bootstrap completion manifest.
    """

    feed_key: str
    meta_key: str
    manifest_key: str


class NvdBootstrapKeyFactory:
    """Build deterministic Bronze keys for one NVD yearly-feed revision."""

    DEFAULT_PREFIX = "bronze/nvd/cve/bootstrap"

    def __init__(self, prefix: str = DEFAULT_PREFIX) -> None:
        """Initialize the key factory with a configurable Bronze prefix."""
        normalized_prefix = prefix.strip("/")

        if not normalized_prefix:
            raise ValueError("NVD Bootstrap Bronze prefix cannot be empty.")

        self._prefix = normalized_prefix

    def build(
        self,
        identity: NvdBootstrapSourceIdentity,
    ) -> NvdBootstrapObjectKeys:
        """Build all Bronze object keys for one NVD source revision."""
        base_key = (
            f"{self._prefix}/feed_year={identity.feed_year}/feed_revision={identity.feed_revision}"
        )

        source_name = f"nvdcve-2.0-{identity.feed_year}"

        return NvdBootstrapObjectKeys(
            feed_key=f"{base_key}/{source_name}.json.gz",
            meta_key=f"{base_key}/{source_name}.meta",
            manifest_key=f"{base_key}/manifest.json",
        )
