#!/usr/bin/env python3
"""Run every standing repository-invariant verifier and report one result table.

`scripts/` holds 28 files named `verify_*.py`, and they are not one kind of thing.
Twenty-three are **standing verifiers**: they take no required argument, assert a
repository invariant, and must pass on any change. Five are **evidence admission
tools**: they take a Terraform plan, a published artifact manifest or a live
measurement artifact and admit or reject it. An admission tool cannot pass on its
own and was never meant to.

Nothing in the directory said which was which, so running everything read as
"23 of 28 pass" — five apparently broken gates that are in fact a different kind
of tool being invoked wrongly. This runner names the distinction, and
`tests/unit/scripts/test_verifier_registry.py` keeps it honest: it derives each
script's kind from its own argparse definition and fails if the registry below
disagrees, so a new verifier cannot be added unclassified.

```text
standing invariant != admitted evidence
a tool that needs input is not a failing gate
```
"""

import argparse
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Final, cast

_REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[1]
_SCRIPTS_ROOT: Final = _REPOSITORY_ROOT / "scripts"

STANDING_VERIFIERS: Final = (
    "verify_module_imports.py",
    "verify_operational_recovery.py",
    "verify_phase18_closeout.py",
    "verify_phase18_consolidated_view.py",
    "verify_phase18_cost_accounting.py",
    "verify_phase18_evidence_inventory.py",
    "verify_phase18_portfolio_pack.py",
    "verify_phase19_gate19_1_public_runtime_contract.py",
    "verify_phase19_gate19_2_closeout.py",
    "verify_phase19_gate19_2_measurement_contract.py",
    "verify_phase19_gate19_3_async_topology_contract.py",
    "verify_phase19_gate19_4_disabled_async_runtime.py",
    "verify_phase19_gate19_5_async_artifact_build.py",
    "verify_phase19_gate19_7_materialization_contract.py",
    "verify_phase19_gate19_7_untaint_contract.py",
    "verify_phase19_gate19_8_threat_evidence_authority.py",
    "verify_phase19_gate19_9_v1_demonstration_contract.py",
    "verify_phase19_gate19_10_demo_runner.py",
    "verify_phase19_gate19_11_demo_scenarios.py",
    "verify_phase19_gate19_12_visual_demo.py",
    "verify_phase19_gate19_13_portfolio_polish.py",
    "verify_telemetry_safety.py",
    "verify_workflow_security.py",
)
"""Verifiers that take no required argument and must pass offline on any change."""

EVIDENCE_ADMISSION_TOOLS: Final = (
    "verify_phase19_gate19_2_live_measurement.py",
    "verify_phase19_gate19_5_artifact_publication.py",
    "verify_phase19_gate19_6_exact_plan.py",
    "verify_phase19_gate19_7_fresh_plan.py",
    "verify_phase19_gate19_7_recovery_plan.py",
)
"""Tools that admit or reject a supplied artifact. They require inputs by design."""


class InvariantRunError(RuntimeError):
    """Raised when the registry does not describe the scripts on disk."""


def _assert_registry_matches_disk() -> None:
    """Fail before running anything if the registry has drifted from the directory.

    Raises:
        InvariantRunError: If a verifier is unregistered or registered but absent.
    """
    on_disk = {path.name for path in _SCRIPTS_ROOT.glob("verify_*.py")}
    registered = set(STANDING_VERIFIERS) | set(EVIDENCE_ADMISSION_TOOLS)

    unregistered = sorted(on_disk - registered)
    missing = sorted(registered - on_disk)
    if unregistered or missing:
        raise InvariantRunError(
            "the verifier registry does not match scripts/\n"
            f"unregistered on disk: {unregistered}\n"
            f"registered but absent: {missing}"
        )


def _run_one(name: str) -> tuple[bool, float, str]:
    """Run one standing verifier and return its outcome, duration and tail output.

    Args:
        name: The verifier file name under `scripts/`.

    Returns:
        Whether it passed, how long it took in seconds, and the last output lines.
    """
    started = time.monotonic()
    process = subprocess.run(
        [sys.executable, str(_SCRIPTS_ROOT / name)],
        cwd=_REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    elapsed = time.monotonic() - started
    combined = (process.stdout + process.stderr).strip().splitlines()
    return process.returncode == 0, elapsed, "\n".join(combined[-12:])


def _parser() -> argparse.ArgumentParser:
    """Build the runner's command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the standing repository-invariant verifiers. Evidence admission "
            "tools are listed but never run: they require input artifacts."
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="print the classification and exit without running anything",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="stop at the first failing verifier",
    )
    return parser


def _render_listing() -> str:
    """Render the classification of every verifier on disk."""
    lines = [f"standing verifiers ({len(STANDING_VERIFIERS)}) — run with no arguments"]
    lines.extend(f"  {name}" for name in STANDING_VERIFIERS)
    lines.append("")
    lines.append(
        f"evidence admission tools ({len(EVIDENCE_ADMISSION_TOOLS)}) — require input artifacts"
    )
    lines.extend(f"  {name}" for name in EVIDENCE_ADMISSION_TOOLS)
    lines.append("")
    lines.append("standing invariant != admitted evidence")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the standing verifiers and return a process exit status.

    Args:
        argv: Command-line arguments, or None to read `sys.argv`.

    Returns:
        0 when every standing verifier passes, 1 when any fails, 2 when the
        registry does not describe the scripts on disk.
    """
    namespace = _parser().parse_args(list(argv) if argv is not None else None)

    try:
        _assert_registry_matches_disk()
    except InvariantRunError as exc:
        print(f"repository invariants rejected: {exc}", file=sys.stderr)
        return 2

    if cast(bool, namespace.list):
        sys.stdout.write(_render_listing())
        return 0

    fail_fast = cast(bool, namespace.fail_fast)
    failures: list[tuple[str, str]] = []
    total_elapsed = 0.0

    for name in STANDING_VERIFIERS:
        passed, elapsed, tail = _run_one(name)
        total_elapsed += elapsed
        status = "PASS" if passed else "FAIL"
        print(f"{status}  {elapsed:6.1f}s  {name}", flush=True)
        if not passed:
            failures.append((name, tail))
            if fail_fast:
                break

    print()
    print(
        f"standing verifiers: {len(STANDING_VERIFIERS) - len(failures)}"
        f"/{len(STANDING_VERIFIERS)} passed in {total_elapsed:.1f}s"
    )
    print(
        f"evidence admission tools not run: {len(EVIDENCE_ADMISSION_TOOLS)} "
        "(they require input artifacts)"
    )

    for name, tail in failures:
        print(f"\n---------- {name}\n{tail}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
