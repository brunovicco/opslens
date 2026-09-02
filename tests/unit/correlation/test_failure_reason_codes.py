"""Tests for stable fail-closed correlation reason codes."""

from opslens.correlation.domain.errors import (
    InvalidPackageNameError,
    InvalidPackagePurlError,
    InvalidPackageVersionError,
    UnsupportedEcosystemError,
    UnsupportedPackagePurlFeatureError,
)


def test_identity_failure_reason_codes_are_stable() -> None:
    """Machine-readable reason codes are part of the deterministic evidence contract."""
    assert UnsupportedEcosystemError.reason_code == "unsupported_ecosystem"
    assert InvalidPackageNameError.reason_code == "invalid_package_name"
    assert InvalidPackageVersionError.reason_code == "invalid_version"
    assert InvalidPackagePurlError.reason_code == "invalid_purl"
    assert UnsupportedPackagePurlFeatureError.reason_code == "unsupported_purl_feature"
