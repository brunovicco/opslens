"""Tests for strict PyPI vulnerable-range parsing and applicability evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from opslens.correlation.domain.errors import (
    InvalidVulnerableRangeError,
    UnsupportedRangeOperatorError,
)
from opslens.correlation.domain.pypi import canonicalize_pypi_version
from opslens.correlation.domain.pypi_ranges import (
    CorrelationResult,
    PyPIRangeOperator,
    evaluate_pypi_correlation,
    parse_pypi_vulnerable_range,
)

_FIXTURE_PATH = Path("tests/fixtures/correlation/pypi_v1_cases.json")


def _load_cases() -> list[dict[str, Any]]:
    """Load the frozen Phase 3 PyPI contract cases."""
    payload = cast(dict[str, Any], json.loads(_FIXTURE_PATH.read_text(encoding="utf-8")))
    return cast(list[dict[str, Any]], payload["cases"])


def test_frozen_pypi_corpus_applicability_expectations() -> None:
    """Evaluate all frozen corpus cases against the deterministic range contract."""
    cases = _load_cases()
    assert len(cases) == 15

    for case in cases:
        first_patched = cast(str | None, case.get("first_patched_version"))
        evidence = evaluate_pypi_correlation(
            package=cast(str, case["package"]),
            version=cast(str, case["version"]),
            vulnerable_range=cast(str, case["vulnerable_range"]),
            first_patched_version=first_patched,
        )

        assert evidence.result.value == case["expected_result"], case["id"]
        assert evidence.package_name_canonical == case["expected_package_canonical"], case["id"]

        expected_version = cast(str | None, case.get("expected_version_canonical"))
        assert evidence.version_canonical == expected_version, case["id"]

        expected_reason = cast(str | None, case.get("expected_reason_code"))
        if expected_reason is not None:
            assert evidence.reason_code == expected_reason, case["id"]
        elif evidence.result is CorrelationResult.AFFECTED:
            assert evidence.reason_code == "version_matches_vulnerable_range", case["id"]
        else:
            assert evidence.reason_code == "version_outside_vulnerable_range", case["id"]

        if first_patched is None:
            assert evidence.first_patched_version_canonical is None, case["id"]
        else:
            expected_patched = canonicalize_pypi_version(first_patched).canonical
            assert evidence.first_patched_version_canonical == expected_patched, case["id"]


def test_parser_preserves_typed_conjunction_evidence() -> None:
    """Parse ordered clauses without losing original or normalized bound evidence."""
    parsed = parse_pypi_vulnerable_range(">= 1.0RC1, < 2.0")

    assert parsed.original == ">= 1.0RC1, < 2.0"
    assert len(parsed.clauses) == 2
    assert parsed.clauses[0].original == ">= 1.0RC1"
    assert parsed.clauses[0].operator is PyPIRangeOperator.GREATER_THAN_OR_EQUAL
    assert parsed.clauses[0].bound.original == "1.0RC1"
    assert parsed.clauses[0].bound.canonical == "1.0rc1"
    assert parsed.clauses[1].operator is PyPIRangeOperator.LESS_THAN
    assert parsed.clauses[1].bound.canonical == "2.0"


def test_inclusive_and_exclusive_boundaries_are_distinct() -> None:
    """Respect inclusive lower and exclusive upper boundaries exactly."""
    lower = evaluate_pypi_correlation(
        package="demo-package",
        version="4.3.0",
        vulnerable_range=">= 4.3.0, < 4.3.5",
    )
    upper = evaluate_pypi_correlation(
        package="demo-package",
        version="4.3.5",
        vulnerable_range=">= 4.3.0, < 4.3.5",
    )

    assert lower.result is CorrelationResult.AFFECTED
    assert tuple(clause.matched for clause in lower.parsed_clauses) == (True, True)
    assert upper.result is CorrelationResult.NOT_AFFECTED
    assert tuple(clause.matched for clause in upper.parsed_clauses) == (True, False)


def test_first_patched_version_never_overrides_published_range() -> None:
    """Treat first patched version as remediation evidence, not applicability authority."""
    evidence = evaluate_pypi_correlation(
        package="demo-package",
        version="1.5.0",
        vulnerable_range=">= 1.0.0, < 2.0.0",
        first_patched_version="1.0.0",
    )

    assert evidence.result is CorrelationResult.AFFECTED
    assert evidence.reason_code == "version_matches_vulnerable_range"
    assert evidence.first_patched_version_canonical == "1.0.0"


def test_invalid_first_patched_version_fails_closed() -> None:
    """Reject malformed remediation evidence instead of silently dropping it."""
    evidence = evaluate_pypi_correlation(
        package="demo-package",
        version="1.5.0",
        vulnerable_range=">= 1.0.0, < 2.0.0",
        first_patched_version="not-a-pep440-version",
    )

    assert evidence.result is CorrelationResult.UNSUPPORTED
    assert evidence.reason_code == "invalid_first_patched_version"
    assert len(evidence.parsed_clauses) == 2
    assert evidence.first_patched_version_canonical is None


def test_unsupported_dependency_operator_is_rejected_explicitly() -> None:
    """Reject operators outside the frozen GHSA grammar with a stable reason class."""
    with pytest.raises(UnsupportedRangeOperatorError) as exc_info:
        parse_pypi_vulnerable_range("~= 1.4")

    assert exc_info.value.reason_code == "unsupported_range_operator"


def test_missing_operator_is_invalid_range_not_dependency_inference() -> None:
    """Do not infer an equality or compatible-release operator from bare versions."""
    with pytest.raises(InvalidVulnerableRangeError) as exc_info:
        parse_pypi_vulnerable_range("1.4")

    assert exc_info.value.reason_code == "invalid_range"


@pytest.mark.parametrize(
    "value",
    [
        "",
        " >= 1.0",
        ">= 1.0 ",
        ">=",
        ">= 1.0,",
        ">= 1.0,, < 2.0",
        ">= definitely-not-a-version",
        ">= 1.0 extra",
    ],
)
def test_malformed_ranges_fail_closed(value: str) -> None:
    """Reject malformed range evidence instead of converting it to not affected."""
    with pytest.raises(InvalidVulnerableRangeError) as exc_info:
        parse_pypi_vulnerable_range(value)

    assert exc_info.value.reason_code == "invalid_range"


def test_syntactically_valid_contradictory_range_is_not_affected() -> None:
    """Evaluate valid contradictory evidence literally instead of declaring it malformed."""
    evidence = evaluate_pypi_correlation(
        package="demo-package",
        version="1.5.0",
        vulnerable_range=">= 2.0, < 1.0",
    )

    assert evidence.result is CorrelationResult.NOT_AFFECTED
    assert tuple(clause.matched for clause in evidence.parsed_clauses) == (False, False)


def test_pep440_semantic_equality_is_used_for_equal_operator() -> None:
    """Use PEP 440 identity rather than textual equality for the exact operator."""
    evidence = evaluate_pypi_correlation(
        package="demo-package",
        version="1.0.0",
        vulnerable_range="= 1.0",
    )

    assert evidence.result is CorrelationResult.AFFECTED
    assert evidence.parsed_clauses[0].matched is True
