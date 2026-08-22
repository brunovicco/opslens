"""Deterministic NVD Silver object-key construction."""

from dataclasses import dataclass

from opslens.transformation.nvd.provenance.models import (
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)
from opslens.transformation.nvd.serialization.schema import (
    NVD_CVE_VERSIONS_SCHEMA_VERSION,
)


@dataclass(frozen=True, slots=True)
class NvdSilverObjectKeysV1:
    """Represent deterministic Silver object keys for one source batch."""

    parquet_key: str
    manifest_key: str


class NvdSilverKeyFactoryV1:
    """Build deterministic Silver keys without runtime timestamps."""

    DEFAULT_PREFIX = "silver/nvd/cve"

    def __init__(
        self,
        prefix: str = DEFAULT_PREFIX,
    ) -> None:
        """Initialize the Silver key factory."""
        normalized = prefix.strip("/")

        if not normalized:
            raise ValueError("NVD Silver prefix cannot be empty.")

        self._prefix = normalized

    def build(
        self,
        evidence: VerifiedNvdBronzeEvidenceV1,
    ) -> NvdSilverObjectKeysV1:
        """Build Parquet and COMPLETE manifest keys."""
        base = (
            f"{self._prefix}/"
            f"schema_version={NVD_CVE_VERSIONS_SCHEMA_VERSION}/"
            f"source_kind={evidence.source_kind.value}"
        )

        if evidence.source_kind is NvdSilverSourceKind.BOOTSTRAP:
            year = evidence.bootstrap_feed_year
            revision = evidence.bootstrap_feed_revision

            if type(year) is not int:
                raise ValueError("Bootstrap Silver key requires feed year.")

            if revision is None or not revision:
                raise ValueError("Bootstrap Silver key requires feed revision.")

            if "/" in revision:
                raise ValueError("Bootstrap feed revision cannot contain '/'.")

            base = f"{base}/feed_year={year}/feed_revision={revision}"

        elif evidence.source_kind is NvdSilverSourceKind.INCREMENTAL:
            update_id = evidence.incremental_update_id

            if (
                update_id is None
                or len(update_id) != 64
                or any(character not in "0123456789abcdef" for character in update_id)
            ):
                raise ValueError("Incremental Silver key requires SHA-256 update_id.")

            base = f"{base}/update_id={update_id}"

        else:
            raise ValueError("Unsupported NVD Silver source kind.")

        return NvdSilverObjectKeysV1(
            parquet_key=f"{base}/part-00000.parquet",
            manifest_key=f"{base}/manifest.json",
        )
