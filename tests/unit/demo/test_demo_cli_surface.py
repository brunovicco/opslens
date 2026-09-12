"""Tests for the reviewer-facing CLI surface: exit codes, --pretty and --version."""

import json
from typing import cast

import pytest

from opslens.demo import (
    CONTROLLED_BENIGN_RESULT_CONTRACT_VERSION,
    CONTROLLED_BENIGN_SCENARIO_ID,
    DEMO_RESULT_CONTRACT_VERSION,
    FAIL_CLOSED_RESULT_CONTRACT_VERSION,
    FAIL_CLOSED_SCENARIO_ID,
    MATERIAL_VULNERABILITY_SCENARIO_ID,
    DemoContractError,
    build_controlled_benign_demo,
    build_fail_closed_incomplete_evidence_demo,
    build_material_vulnerability_demo,
)
from opslens.demo.cli import (
    EXIT_MATERIAL_FINDING,
    EXIT_OK,
    EXIT_REJECTED,
    main,
    outcome_exit_code,
    render_demo,
    render_versions,
)


def _object(value: object) -> dict[str, object]:
    """Require one JSON object in test projections."""
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_default_exit_code_reports_the_run_not_the_outcome() -> None:
    """The documented reviewer command stays exit 0 for every admitted scenario."""
    for scenario in (
        MATERIAL_VULNERABILITY_SCENARIO_ID,
        CONTROLLED_BENIGN_SCENARIO_ID,
        FAIL_CLOSED_SCENARIO_ID,
    ):
        assert main(["--scenario", scenario, "--format", "json"]) == EXIT_OK


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        (MATERIAL_VULNERABILITY_SCENARIO_ID, EXIT_MATERIAL_FINDING),
        (CONTROLLED_BENIGN_SCENARIO_ID, EXIT_OK),
        (FAIL_CLOSED_SCENARIO_ID, EXIT_REJECTED),
    ],
)
def test_outcome_exit_code_mode_maps_each_deterministic_outcome(
    scenario: str, expected: int
) -> None:
    """Opting into outcome semantics makes the demo usable in a pipeline."""
    assert main(["--scenario", scenario, "--format", "json", "--exit-code", "outcome"]) == expected


def test_outcome_exit_codes_are_distinct() -> None:
    """A rejection must never be indistinguishable from a clean or a material run."""
    codes = {
        outcome_exit_code(build_material_vulnerability_demo()),
        outcome_exit_code(build_controlled_benign_demo()),
        outcome_exit_code(build_fail_closed_incomplete_evidence_demo()),
    }

    assert codes == {EXIT_OK, EXIT_MATERIAL_FINDING, EXIT_REJECTED}


def test_outcome_exit_code_rejects_unadmitted_results() -> None:
    """Only an admitted scenario result can carry an outcome exit status."""
    with pytest.raises(DemoContractError, match="admitted demo scenario result"):
        outcome_exit_code(cast(object, "not-a-result"))  # pyright: ignore[reportArgumentType]


def test_pretty_reindents_without_moving_identity() -> None:
    """--pretty is a projection of the canonical bytes, never a re-serialization."""
    result = build_material_vulnerability_demo()
    canonical = render_demo(result, "json")
    pretty = render_demo(result, "json", pretty=True)

    assert pretty != canonical
    assert "\n  " in pretty
    assert json.loads(pretty) == json.loads(canonical)
    identities = _object(_object(json.loads(pretty))["identities"])
    analysis_sha256 = result.repository_analysis.analysis.evidence_sha256
    assert identities["repository_analysis_sha256"] == analysis_sha256


def test_pretty_output_is_stable_across_runs() -> None:
    """The readable projection stays deterministic like the canonical one."""
    assert render_demo(build_material_vulnerability_demo(), "json", pretty=True) == render_demo(
        build_material_vulnerability_demo(), "json", pretty=True
    )


def test_pretty_is_rejected_for_text_output() -> None:
    """There is nothing to reindent in the text projection, so the flag fails closed."""
    with pytest.raises(DemoContractError, match="only to the json projection"):
        render_demo(build_material_vulnerability_demo(), "text", pretty=True)


def test_cli_rejects_pretty_text_combination() -> None:
    """The CLI surfaces the same rejection as a non-zero exit."""
    assert main(["--format", "text", "--pretty"]) == EXIT_REJECTED


def test_version_lists_every_admitted_result_contract() -> None:
    """--version names the contract behind each scenario, not a package version."""
    rendered = render_versions()

    assert DEMO_RESULT_CONTRACT_VERSION in rendered
    assert CONTROLLED_BENIGN_RESULT_CONTRACT_VERSION in rendered
    assert FAIL_CLOSED_RESULT_CONTRACT_VERSION in rendered
    assert rendered.endswith("\n")


def test_version_exits_before_running_any_scenario(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--version is a metadata query, not a demo execution."""
    assert main(["--version"]) == EXIT_OK
    captured = capsys.readouterr().out

    assert captured == render_versions()
    assert "sha256" not in captured
