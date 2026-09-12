#!/usr/bin/env python3
"""Verify the frozen Phase 18 Gate 18.3 cost-accounting envelope."""

import argparse
from pathlib import Path

from _bootstrap import ensure_repository_src_on_path

ensure_repository_src_on_path()

from opslens.evaluation_readiness import (  # noqa: E402
    CostAccountingValidationError,
    validate_cost_accounting,
)

_DEFAULT_ARTIFACT = Path("labs/evidence/phase-18-gate-18-3-cost-accounting-v1.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--artifact", type=Path, default=_DEFAULT_ARTIFACT)
    return parser


def main() -> int:
    """Run the deterministic Gate 18.3 verifier and return a process exit code."""
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    artifact_path = args.artifact
    if not artifact_path.is_absolute():
        artifact_path = repo_root / artifact_path

    try:
        summary = validate_cost_accounting(
            artifact_path=artifact_path,
            repo_root=repo_root,
        )
    except CostAccountingValidationError as exc:
        print(f"phase18_cost_accounting=FAIL reason={exc}")
        return 1

    print(
        "phase18_cost_accounting=PASS "
        f"entries={summary.entry_count} "
        f"cost_observations={summary.cost_observation_count} "
        f"resource_observations={summary.resource_observation_count} "
        f"configured_limits={summary.configured_limit_count} "
        f"unmeasured={summary.unmeasured_count} "
        f"not_applicable={summary.not_applicable_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
