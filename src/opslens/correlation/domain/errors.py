"""Fail-closed errors for deterministic vulnerability correlation."""


class CorrelationContractError(ValueError):
    """Base error for evidence that cannot satisfy the correlation contract."""

    reason_code = "invalid_correlation_evidence"


class UnsupportedEcosystemError(CorrelationContractError):
    """Raised when an ecosystem is outside the evaluator's explicit authority."""

    reason_code = "unsupported_ecosystem"


class InvalidPackageNameError(CorrelationContractError):
    """Raised when a package name is invalid for its ecosystem."""

    reason_code = "invalid_package_name"


class InvalidPackageVersionError(CorrelationContractError):
    """Raised when a concrete package version cannot be parsed deterministically."""

    reason_code = "invalid_version"


class InvalidPackagePurlError(CorrelationContractError):
    """Raised when a package URL is malformed or inconsistent with package evidence."""

    reason_code = "invalid_purl"


class UnsupportedPackagePurlFeatureError(CorrelationContractError):
    """Raised when a valid-looking purl uses a feature outside the frozen v1 contract."""

    reason_code = "unsupported_purl_feature"
