"""Strict PyPI vulnerable-range parsing and deterministic applicability evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from opslens.correlation.domain.errors import (
    CorrelationContractError,
    InvalidFirstPatchedVersionError,
    InvalidPackageVersionError,
    InvalidVulnerableRangeError,
    UnsupportedRangeOperatorError,
)
from opslens.correlation.domain.pypi import (
    CanonicalPyPIVersion,
    build_pypi_purl,
    canonicalize_pypi_package,
    canonicalize_pypi_version,
)

_OPERATOR_PREFIX_PATTERN = re.compile(r"^(?P<operator>[<>=!~^]+)", re.ASCII)
_SUPPORTED_CLAUSE_PATTERN = re.compile(
    r"^(?P<operator><=|>=|=|<|>)\s*(?P<version>\S+)$",
    re.ASCII,
)


class PyPIRangeOperator(StrEnum):
    """Operators explicitly supported by the frozen GHSA PyPI v1 grammar."""

    EQUAL = "="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="


class CorrelationResult(StrEnum):
    """Deterministic applicability outcomes for one package/version/range tuple."""

    AFFECTED = "affected"
    NOT_AFFECTED = "not_affected"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class PyPIRangeClause:
    """One normalized ordered comparison from a GHSA vulnerable range."""

    original: str
    operator: PyPIRangeOperator
    bound: CanonicalPyPIVersion

    def matches(self, installed: CanonicalPyPIVersion) -> bool:
        """Evaluate this clause with PEP 440 version ordering."""
        if self.operator is PyPIRangeOperator.EQUAL:
            return installed.parsed == self.bound.parsed
        if self.operator is PyPIRangeOperator.LESS_THAN:
            return installed.parsed < self.bound.parsed
        if self.operator is PyPIRangeOperator.LESS_THAN_OR_EQUAL:
            return installed.parsed <= self.bound.parsed
        if self.operator is PyPIRangeOperator.GREATER_THAN:
            return installed.parsed > self.bound.parsed
        if self.operator is PyPIRangeOperator.GREATER_THAN_OR_EQUAL:
            return installed.parsed >= self.bound.parsed
        raise AssertionError(f"Unhandled PyPI range operator: {self.operator!r}.")


@dataclass(frozen=True, slots=True)
class PyPIVulnerableRange:
    """One strict conjunction of ordered PyPI vulnerable-range clauses."""

    original: str
    clauses: tuple[PyPIRangeClause, ...]

    def matches(self, installed: CanonicalPyPIVersion) -> bool:
        """Return whether every clause in the conjunction matches the installed version."""
        return all(clause.matches(installed) for clause in self.clauses)


@dataclass(frozen=True, slots=True)
class PyPIClauseEvidence:
    """Reconstructable evidence for one evaluated vulnerable-range clause."""

    operator: str
    bound_original: str
    bound_canonical: str
    matched: bool


@dataclass(frozen=True, slots=True)
class PyPICorrelationEvidence:
    """Deterministic result and evidence for one PyPI package applicability decision."""

    package_name_original: str
    package_name_canonical: str | None
    version_original: str
    version_canonical: str | None
    purl_canonical: str | None
    vulnerable_range_original: str
    parsed_clauses: tuple[PyPIClauseEvidence, ...]
    first_patched_version_original: str | None
    first_patched_version_canonical: str | None
    result: CorrelationResult
    reason_code: str


def parse_pypi_vulnerable_range(value: str) -> PyPIVulnerableRange:
    """Parse the frozen Phase 3 v1 GHSA range grammar into typed PEP 440 clauses.

    Only `=`, `<`, `<=`, `>`, and `>=` are accepted. Commas represent logical AND.
    Operators from broader dependency-specifier grammars are intentionally rejected.
    """
    if not value or value != value.strip():
        raise InvalidVulnerableRangeError("Vulnerable range must be a non-empty clean token.")

    raw_clauses = value.split(",")
    if not raw_clauses or any(not raw_clause.strip() for raw_clause in raw_clauses):
        raise InvalidVulnerableRangeError("Vulnerable range contains an empty clause.")

    clauses: list[PyPIRangeClause] = []
    for raw_clause in raw_clauses:
        clause = raw_clause.strip()
        operator_match = _OPERATOR_PREFIX_PATTERN.match(clause)
        if operator_match is None:
            raise InvalidVulnerableRangeError(
                f"Vulnerable range clause is missing an operator: {clause!r}."
            )

        raw_operator = operator_match.group("operator")
        if raw_operator not in {operator.value for operator in PyPIRangeOperator}:
            raise UnsupportedRangeOperatorError(
                f"Unsupported vulnerable-range operator: {raw_operator!r}."
            )

        clause_match = _SUPPORTED_CLAUSE_PATTERN.fullmatch(clause)
        if clause_match is None:
            raise InvalidVulnerableRangeError(f"Malformed vulnerable-range clause: {clause!r}.")

        bound_original = clause_match.group("version")
        try:
            bound = canonicalize_pypi_version(bound_original)
        except InvalidPackageVersionError as exc:
            raise InvalidVulnerableRangeError(
                f"Invalid PEP 440 bound in vulnerable range: {bound_original!r}."
            ) from exc

        clauses.append(
            PyPIRangeClause(
                original=clause,
                operator=PyPIRangeOperator(raw_operator),
                bound=bound,
            )
        )

    return PyPIVulnerableRange(original=value, clauses=tuple(clauses))


def evaluate_pypi_correlation(
    *,
    package: str,
    version: str,
    vulnerable_range: str,
    first_patched_version: str | None = None,
) -> PyPICorrelationEvidence:
    """Evaluate package applicability and emit deterministic fail-closed evidence.

    `first_patched_version` is normalized only as remediation evidence. Applicability is
    determined exclusively by package identity, installed version, and vulnerable range.
    """
    package_canonical: str | None = None
    version_canonical: str | None = None
    purl_canonical: str | None = None
    first_patched_canonical: str | None = None
    parsed_clauses: tuple[PyPIClauseEvidence, ...] = ()

    try:
        canonical_package = canonicalize_pypi_package(package)
        package_canonical = canonical_package.canonical

        canonical_version = canonicalize_pypi_version(version)
        version_canonical = canonical_version.canonical
        purl_canonical = build_pypi_purl(
            package=canonical_package,
            version=canonical_version,
        )

        parsed_range = parse_pypi_vulnerable_range(vulnerable_range)
        parsed_clauses = tuple(
            PyPIClauseEvidence(
                operator=clause.operator.value,
                bound_original=clause.bound.original,
                bound_canonical=clause.bound.canonical,
                matched=clause.matches(canonical_version),
            )
            for clause in parsed_range.clauses
        )

        if first_patched_version is not None:
            try:
                canonical_first_patched = canonicalize_pypi_version(first_patched_version)
            except InvalidPackageVersionError as exc:
                raise InvalidFirstPatchedVersionError(
                    f"Invalid first patched PyPI version: {first_patched_version!r}."
                ) from exc
            first_patched_canonical = canonical_first_patched.canonical

        if all(clause.matched for clause in parsed_clauses):
            result = CorrelationResult.AFFECTED
            reason_code = "version_matches_vulnerable_range"
        else:
            result = CorrelationResult.NOT_AFFECTED
            reason_code = "version_outside_vulnerable_range"
    except CorrelationContractError as exc:
        result = CorrelationResult.UNSUPPORTED
        reason_code = exc.reason_code

    return PyPICorrelationEvidence(
        package_name_original=package,
        package_name_canonical=package_canonical,
        version_original=version,
        version_canonical=version_canonical,
        purl_canonical=purl_canonical,
        vulnerable_range_original=vulnerable_range,
        parsed_clauses=parsed_clauses,
        first_patched_version_original=first_patched_version,
        first_patched_version_canonical=first_patched_canonical,
        result=result,
        reason_code=reason_code,
    )
