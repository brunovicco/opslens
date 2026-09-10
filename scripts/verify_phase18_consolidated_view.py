#!/usr/bin/env python3
"""Verify the frozen Phase 18 Gate 18.2 consolidated evaluation view."""

from __future__ import annotations

import argparse
from pathlib import Path

from opslens.evaluation_readiness import (
    ConsolidatedViewValidationError,
    validate_consolidated_view,
)

_DEFAULT_INVENTORY = Path("labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json")
_DEFAULT_SIGNALS = Path("labs/evidence/phase-18-gate-18-2-decision-signals-v1.json")
_DEFAULT_VIEW = Path("labs/evidence/phase-18-gate-18-2-consolidated-view-v1.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--inventory", type=Path, default=_DEFAULT_INVENTORY)
    parser.add_argument("--signals", type=Path, default=_DEFAULT_SIGNALS)
    parser.add_argument("--view", type=Path, default=_DEFAULT_VIEW)
    return parser


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def main() -> int:
    """Run the deterministic consolidated-view verifier and return a process exit code."""
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    try:
        summary = validate_consolidated_view(
            inventory_path=_resolve(repo_root, args.inventory),
            signal_path=_resolve(repo_root, args.signals),
            view_path=_resolve(repo_root, args.view),
            repo_root=repo_root,
        )
    except ConsolidatedViewValidationError as exc:
        print(f"phase18_consolidated_view=FAIL reason={exc}")
        return 1

    print(
        "phase18_consolidated_view=PASS "
        f"sections={summary.section_count} "
        f"metrics={summary.metric_count} "
        f"decision_signals={summary.decision_signal_count} "
        f"unmeasured={summary.unmeasured_count} "
        f"not_applicable={summary.not_applicable_count} "
        f"non_comparable_pairs={summary.non_comparability_assertion_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
