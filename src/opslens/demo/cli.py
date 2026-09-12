"""CLI surface for the deterministic OpsLens V1 offline demo."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import cast

from opslens.demo.controlled_benign import (
    CONTROLLED_BENIGN_SCENARIO_ID,
    ControlledBenignDemoResult,
    build_controlled_benign_demo,
)
from opslens.demo.fail_closed import (
    FAIL_CLOSED_SCENARIO_ID,
    FailClosedDemoResult,
    build_fail_closed_incomplete_evidence_demo,
)
from opslens.demo.material_vulnerability import (
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


def _parser() -> argparse.ArgumentParser:
    """Build the fail-closed command-line parser for the canonical demo."""
    parser = argparse.ArgumentParser(
        description="Run the deterministic offline OpsLens V1 demonstration.",
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


def render_demo(result: DemoScenarioResult, output_format: str) -> str:
    """Render one admitted result as text or stable canonical JSON."""
    if type(result) not in {DemoRunResult, ControlledBenignDemoResult, FailClosedDemoResult}:
        raise DemoContractError("render_demo requires one admitted demo scenario result")
    if output_format == "text":
        return result.to_text()
    if output_format == "json":
        return result.canonical_json.decode("utf-8") + "\n"
    raise DemoContractError(f"unsupported demo output format: {output_format}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the canonical offline demo and return a process-compatible exit status."""
    namespace = _parser().parse_args(list(argv) if argv is not None else None)
    scenario = cast(str, namespace.scenario)
    output_format = cast(str, namespace.output_format)
    try:
        result = run_demo(scenario)
        rendered = render_demo(result, output_format)
    except DemoContractError as exc:
        print(f"opslens demo rejected: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(rendered)
    return 0


__all__ = ["DemoScenarioResult", "main", "render_demo", "run_demo"]
