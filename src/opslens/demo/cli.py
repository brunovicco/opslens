"""CLI surface for the deterministic OpsLens V1 offline demo."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import cast

from opslens.demo.material_vulnerability import (
    MATERIAL_VULNERABILITY_SCENARIO_ID,
    DemoContractError,
    DemoRunResult,
    build_material_vulnerability_demo,
)

_SUPPORTED_SCENARIOS = (MATERIAL_VULNERABILITY_SCENARIO_ID,)
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


def run_demo(scenario: str) -> DemoRunResult:
    """Dispatch only explicitly admitted offline scenarios."""
    if scenario != MATERIAL_VULNERABILITY_SCENARIO_ID:
        raise DemoContractError(f"unsupported demo scenario: {scenario}")
    return build_material_vulnerability_demo()


def render_demo(result: DemoRunResult, output_format: str) -> str:
    """Render one admitted result as text or stable canonical JSON."""
    if type(result) is not DemoRunResult:
        raise DemoContractError("render_demo requires one DemoRunResult")
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


__all__ = ["main", "render_demo", "run_demo"]
