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


class InvalidVulnerableRangeError(CorrelationContractError):
    """Raised when vulnerable-range evidence cannot be parsed by the frozen grammar."""

    reason_code = "invalid_range"


class UnsupportedRangeOperatorError(InvalidVulnerableRangeError):
    """Raised when a range uses an operator outside the explicit Phase 3 v1 allowlist."""

    reason_code = "unsupported_range_operator"


class InvalidFirstPatchedVersionError(CorrelationContractError):
    """Raised when supplied fixed-version evidence is not a valid ecosystem version."""

    reason_code = "invalid_first_patched_version"


class InvalidGhsaEvidenceBridgeError(CorrelationContractError):
    """Raised when normalized GHSA evidence cannot be linked without losing authority."""

    reason_code = "invalid_ghsa_evidence_bridge"


class InvalidCveAliasReconciliationError(CorrelationContractError):
    """Raised when CVE alias evidence cannot be reconciled without inventing a link."""

    reason_code = "invalid_cve_alias_reconciliation"


class InvalidCorrelationEvidenceRecordError(CorrelationContractError):
    """Raised when Phase 3 evidence components cannot form one canonical record."""

    reason_code = "invalid_correlation_evidence_record"
