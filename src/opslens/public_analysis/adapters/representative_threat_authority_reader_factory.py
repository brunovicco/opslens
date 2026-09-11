"""Compose concrete read-only threat-authority readers for human preparation."""

from __future__ import annotations

from dataclasses import dataclass

from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.ingestion.kev.domain.parser import KevCatalogParser
from opslens.public_analysis.adapters.exact_epss_authority import ExactEpssAuthorityReader
from opslens.public_analysis.adapters.exact_kev_authority import ExactKevAuthorityReader
from opslens.public_analysis.adapters.exact_s3_authority_object import (
    ExactS3AuthorityObjectClient,
    ExactS3AuthorityObjectReader,
)
from opslens.public_analysis.adapters.ghsa_authority import ExactGhsaSilverAuthorityReader
from opslens.public_analysis.adapters.nvd_authority import ExactNvdBronzeAuthorityReader
from opslens.public_analysis.application.representative_pre_measurement_authority import (
    RepresentativeThreatAuthorityReaders,
)


@dataclass(frozen=True, slots=True)
class RepresentativeThreatAuthorityByteLimits:
    """Bound every physical authority object read independently by source role."""

    ghsa_silver: int
    nvd_silver: int
    nvd_bronze: int
    kev_bronze: int
    epss_bronze: int

    def __post_init__(self) -> None:
        """Reject missing, boolean, zero, or negative byte ceilings fail-closed."""
        for name, value in (
            ("ghsa_silver", self.ghsa_silver),
            ("nvd_silver", self.nvd_silver),
            ("nvd_bronze", self.nvd_bronze),
            ("kev_bronze", self.kev_bronze),
            ("epss_bronze", self.epss_bronze),
        ):
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


def build_representative_threat_authority_readers(
    *,
    client: ExactS3AuthorityObjectClient,
    bucket_name: str,
    byte_limits: RepresentativeThreatAuthorityByteLimits,
) -> RepresentativeThreatAuthorityReaders:
    """Build concrete exact readers without performing provider I/O.

    The returned readers remain inert until the existing pre-measurement
    materialization boundary asks them to resolve already-admitted immutable
    object coordinates. Construction owns no discovery, retry, fallback, or
    write behavior.
    """
    ghsa_object_reader = ExactS3AuthorityObjectReader(
        client=client,
        bucket_name=bucket_name,
        max_bytes=byte_limits.ghsa_silver,
    )
    nvd_silver_object_reader = ExactS3AuthorityObjectReader(
        client=client,
        bucket_name=bucket_name,
        max_bytes=byte_limits.nvd_silver,
    )
    nvd_bronze_object_reader = ExactS3AuthorityObjectReader(
        client=client,
        bucket_name=bucket_name,
        max_bytes=byte_limits.nvd_bronze,
    )
    kev_object_reader = ExactS3AuthorityObjectReader(
        client=client,
        bucket_name=bucket_name,
        max_bytes=byte_limits.kev_bronze,
    )
    epss_object_reader = ExactS3AuthorityObjectReader(
        client=client,
        bucket_name=bucket_name,
        max_bytes=byte_limits.epss_bronze,
    )

    return RepresentativeThreatAuthorityReaders(
        ghsa=ExactGhsaSilverAuthorityReader(ghsa_object_reader),
        nvd=ExactNvdBronzeAuthorityReader(
            silver_object_reader=nvd_silver_object_reader,
            bronze_object_reader=nvd_bronze_object_reader,
        ),
        kev=ExactKevAuthorityReader(
            object_reader=kev_object_reader,
            parser=KevCatalogParser(),
        ),
        epss=ExactEpssAuthorityReader(
            object_reader=epss_object_reader,
            parser=EpssSnapshotParser(),
        ),
    )


__all__ = [
    "RepresentativeThreatAuthorityByteLimits",
    "build_representative_threat_authority_readers",
]
