"""Domain types for deterministic vulnerability correlation."""

from opslens.correlation.domain.aliases import (
    CveAliasLinkState,
    CveAliasReconciliationEvidence,
)
from opslens.correlation.domain.evidence import (
    Phase3CorrelationEvidenceRecordV1,
    build_phase3_correlation_evidence_record,
)
from opslens.correlation.domain.pypi import (
    CanonicalPyPIPackage,
    CanonicalPyPIPurl,
    CanonicalPyPIVersion,
    PyPIEcosystem,
    canonicalize_pypi_ecosystem,
    canonicalize_pypi_package,
    canonicalize_pypi_purl,
    canonicalize_pypi_version,
)
from opslens.correlation.domain.pypi_ranges import (
    CorrelationResult,
    PyPIClauseEvidence,
    PyPICorrelationEvidence,
    PyPIRangeClause,
    PyPIRangeOperator,
    PyPIVulnerableRange,
    evaluate_pypi_correlation,
    parse_pypi_vulnerable_range,
)

__all__ = [
    "CanonicalPyPIPackage",
    "CanonicalPyPIPurl",
    "CanonicalPyPIVersion",
    "CorrelationResult",
    "CveAliasLinkState",
    "CveAliasReconciliationEvidence",
    "Phase3CorrelationEvidenceRecordV1",
    "PyPIClauseEvidence",
    "PyPICorrelationEvidence",
    "PyPIEcosystem",
    "PyPIRangeClause",
    "PyPIRangeOperator",
    "PyPIVulnerableRange",
    "build_phase3_correlation_evidence_record",
    "canonicalize_pypi_ecosystem",
    "canonicalize_pypi_package",
    "canonicalize_pypi_purl",
    "canonicalize_pypi_version",
    "evaluate_pypi_correlation",
    "parse_pypi_vulnerable_range",
]
