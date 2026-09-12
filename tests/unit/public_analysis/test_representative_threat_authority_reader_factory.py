"""Tests for concrete Gate 19.2 threat-authority reader composition."""

from dataclasses import dataclass

import pytest

from opslens.public_analysis.adapters.exact_epss_authority import ExactEpssAuthorityReader
from opslens.public_analysis.adapters.exact_kev_authority import ExactKevAuthorityReader
from opslens.public_analysis.adapters.exact_s3_authority_object import ExactS3GetObjectResponse
from opslens.public_analysis.adapters.ghsa_authority import ExactGhsaSilverAuthorityReader
from opslens.public_analysis.adapters.nvd_authority import ExactNvdBronzeAuthorityReader
from opslens.public_analysis.adapters.representative_threat_authority_reader_factory import (
    RepresentativeThreatAuthorityByteLimits,
    build_representative_threat_authority_readers,
)


@dataclass(slots=True)
class NoCallS3Client:
    """Record provider calls so construction can prove structural zero I/O."""

    calls: int = 0

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> ExactS3GetObjectResponse:
        """Fail if reader construction unexpectedly touches S3."""
        del Bucket, Key, VersionId
        self.calls += 1
        raise AssertionError("unexpected S3 call during reader construction")


def _limits() -> RepresentativeThreatAuthorityByteLimits:
    """Return distinct limits so accidental role swaps are visible in review."""
    return RepresentativeThreatAuthorityByteLimits(
        ghsa_silver=11,
        nvd_silver=22,
        nvd_bronze=33,
        kev_bronze=44,
        epss_bronze=55,
    )


def test_builds_all_concrete_readers_without_provider_io() -> None:
    """Compose all concrete typed readers while keeping the provider untouched."""
    client = NoCallS3Client()

    readers = build_representative_threat_authority_readers(
        client=client,
        bucket_name="opslens-authority",
        byte_limits=_limits(),
    )

    assert isinstance(readers.ghsa, ExactGhsaSilverAuthorityReader)
    assert isinstance(readers.nvd, ExactNvdBronzeAuthorityReader)
    assert isinstance(readers.kev, ExactKevAuthorityReader)
    assert isinstance(readers.epss, ExactEpssAuthorityReader)
    assert client.calls == 0


def test_preserves_explicit_distinct_byte_limits() -> None:
    """Keep every source-role ceiling explicit and independently addressable."""
    limits = _limits()

    assert limits.ghsa_silver == 11
    assert limits.nvd_silver == 22
    assert limits.nvd_bronze == 33
    assert limits.kev_bronze == 44
    assert limits.epss_bronze == 55


@pytest.mark.parametrize("invalid", [0, -1, True])
def test_rejects_invalid_byte_limit(invalid: int) -> None:
    """Reject non-positive and boolean limits before any provider capability exists."""
    with pytest.raises(ValueError, match="ghsa_silver must be a positive integer"):
        RepresentativeThreatAuthorityByteLimits(
            ghsa_silver=invalid,
            nvd_silver=22,
            nvd_bronze=33,
            kev_bronze=44,
            epss_bronze=55,
        )


def test_rejects_empty_bucket_without_provider_io() -> None:
    """Delegate bucket validation to the exact object boundary before any S3 call."""
    client = NoCallS3Client()

    with pytest.raises(ValueError, match="bucket name cannot be empty"):
        build_representative_threat_authority_readers(
            client=client,
            bucket_name=" ",
            byte_limits=_limits(),
        )

    assert client.calls == 0
