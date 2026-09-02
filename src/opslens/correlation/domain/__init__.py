"""Domain types for deterministic vulnerability correlation."""

from opslens.correlation.domain.aliases import (
    CveAliasLinkState,
    CveAliasReconciliationEvidence,
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
    "PyPIClauseEvidence",
    "PyPICorrelationEvidence",
    "PyPIEcosystem",
    "PyPIRangeClause",
    "PyPIRangeOperator",
    "PyPIVulnerableRange",
    "canonicalize_pypi_ecosystem",
    "canonicalize_pypi_package",
    "canonicalize_pypi_purl",
    "canonicalize_pypi_version",
    "evaluate_pypi_correlation",
    "parse_pypi_vulnerable_range",
]
