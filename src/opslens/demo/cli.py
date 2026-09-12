"""CLI surface for the deterministic OpsLens V1 offline demo."""

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Final, cast

from opslens.demo.controlled_benign import (
    CONTROLLED_BENIGN_RESULT_CONTRACT_VERSION,
    CONTROLLED_BENIGN_SCENARIO_ID,
    ControlledBenignDemoResult,
    build_controlled_benign_demo,
)
from opslens.demo.fail_closed import (
    FAIL_CLOSED_RESULT_CONTRACT_VERSION,
    FAIL_CLOSED_SCENARIO_ID,
    FailClosedDemoResult,
    build_fail_closed_incomplete_evidence_demo,
)
from opslens.demo.material_vulnerability import (
    DEMO_RESULT_CONTRACT_VERSION,
    MATERIAL_VULNERABILITY_SCENARIO_ID,
    DemoContractError,
    DemoRunResult,
    build_material_vulnerability_demo,
)

type DemoScenarioResult = DemoRunResult | ControlledBenignDemoResult | FailClosedDemoResult

_SUPPORTED_SCENARIOS = (
    MATERIAL_VULNERABILITY_SCENARIO_ID,
    CONTROLLED_BENIGN_SCENARIO_ID,
    FAIL_CLOSED_SCENARIO_ID,
)
_SUPPORTED_FORMATS = ("text", "json")
_SUPPORTED_EXIT_CODE_MODES = ("run", "outcome")

EXIT_OK: Final = 0
"""The demo ran, or — under ``--exit-code outcome`` — produced no material finding."""

EXIT_MATERIAL_FINDING: Final = 1
"""``--exit-code outcome`` only: the scenario produced a material finding."""

EXIT_REJECTED: Final = 2
"""Admission, rendering or (under ``--exit-code outcome``) evidence was rejected."""

_OUTCOME_EXIT_CODES: Final = {
    DemoRunResult: EXIT_MATERIAL_FINDING,
    ControlledBenignDemoResult: EXIT_OK,
    FailClosedDemoResult: EXIT_REJECTED,
}


def _parser() -> argparse.ArgumentParser:
    """Build the fail-closed command-line parser for the canonical demo."""
    parser = argparse.ArgumentParser(
        description="Run the deterministic offline OpsLens V1 demonstration.",
        epilog=(
            "Exit codes under --exit-code outcome: "
            "0 no material finding, 1 material finding, 2 rejected incomplete evidence. "
            "The default, --exit-code run, reports whether the demo itself ran."
        ),
    )
    parser.add_argument(
        "--scenario",
        choices=_SUPPORTED_SCENARIOS,
        default=MATERIAL_VULNERABILITY_SCENARIO_ID,
        help="admitted offline scenario identity",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=_SUPPORTED_FORMATS,
        default="text",
        help="reviewer output projection",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help=(
            "indent the JSON projection for reading; identity stays the canonical "
            "bytes, which --pretty never recomputes"
        ),
    )
    parser.add_argument(
        "--exit-code",
        dest="exit_code_mode",
        choices=_SUPPORTED_EXIT_CODE_MODES,
        default="run",
        help="whether the exit status reports the run or the deterministic outcome",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print the admitted demo contract versions and exit",
    )
    return parser


def run_demo(scenario: str) -> DemoScenarioResult:
    """Dispatch only explicitly admitted offline scenarios."""
    if scenario == MATERIAL_VULNERABILITY_SCENARIO_ID:
        return build_material_vulnerability_demo()
    if scenario == CONTROLLED_BENIGN_SCENARIO_ID:
        return build_controlled_benign_demo()
    if scenario == FAIL_CLOSED_SCENARIO_ID:
        return build_fail_closed_incomplete_evidence_demo()
    raise DemoContractError(f"unsupported demo scenario: {scenario}")


def render_demo(result: DemoScenarioResult, output_format: str, *, pretty: bool = False) -> str:
    """Render one admitted result as text or stable canonical JSON.

    Args:
        result: One admitted deterministic scenario result.
        output_format: Either ``"text"`` or ``"json"``.
        pretty: Indent the JSON projection. Rejected for text output, because
            there is nothing to reindent.

    Returns:
        The rendered projection, newline-terminated for JSON.

    Raises:
        DemoContractError: If the result, format or flag combination is not
            admitted.
    """
    if type(result) not in {DemoRunResult, ControlledBenignDemoResult, FailClosedDemoResult}:
        raise DemoContractError("render_demo requires one admitted demo scenario result")
    if output_format == "text":
        if pretty:
            raise DemoContractError("--pretty applies only to the json projection")
        return result.to_text()
    if output_format == "json":
        canonical = result.canonical_json.decode("utf-8")
        if not pretty:
            return canonical + "\n"
        # Reindent the canonical bytes rather than re-serializing the payload:
        # the projection changes, the identity does not.
        return json.dumps(json.loads(canonical), indent=2, sort_keys=True) + "\n"
    raise DemoContractError(f"unsupported demo output format: {output_format}")


def outcome_exit_code(result: DemoScenarioResult) -> int:
    """Map one deterministic outcome onto a pipeline-compatible exit status.

    Args:
        result: One admitted deterministic scenario result.

    Returns:
        ``0`` for no material finding, ``1`` for a material finding, ``2`` for a
        rejection on incomplete evidence.

    Raises:
        DemoContractError: If the result is not one admitted scenario result.
    """
    code = _OUTCOME_EXIT_CODES.get(type(result))
    if code is None:
        raise DemoContractError("outcome_exit_code requires one admitted demo scenario result")
    return code


def render_versions() -> str:
    """Render the admitted demo contract versions, one per line."""
    return "\n".join(
        (
            f"material-vulnerability: {DEMO_RESULT_CONTRACT_VERSION}",
            f"controlled-benign: {CONTROLLED_BENIGN_RESULT_CONTRACT_VERSION}",
            f"fail-closed-incomplete-evidence: {FAIL_CLOSED_RESULT_CONTRACT_VERSION}",
        )
    ) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the canonical offline demo and return a process-compatible exit status."""
    namespace = _parser().parse_args(list(argv) if argv is not None else None)
    if cast(bool, namespace.version):
        sys.stdout.write(render_versions())
        return EXIT_OK

    scenario = cast(str, namespace.scenario)
    output_format = cast(str, namespace.output_format)
    pretty = cast(bool, namespace.pretty)
    exit_code_mode = cast(str, namespace.exit_code_mode)
    try:
        result = run_demo(scenario)
        rendered = render_demo(result, output_format, pretty=pretty)
        status = outcome_exit_code(result) if exit_code_mode == "outcome" else EXIT_OK
    except DemoContractError as exc:
        print(f"opslens demo rejected: {exc}", file=sys.stderr)
        return EXIT_REJECTED
    sys.stdout.write(rendered)
    return status


__all__ = [
    "EXIT_MATERIAL_FINDING",
    "EXIT_OK",
    "EXIT_REJECTED",
    "DemoScenarioResult",
    "main",
    "outcome_exit_code",
    "render_demo",
    "render_versions",
    "run_demo",
]
