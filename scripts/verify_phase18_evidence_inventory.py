#!/usr/bin/env python3
"""Verify the frozen Phase 18 Gate 18.1 evidence inventory."""

import argparse
from pathlib import Path

from opslens.evaluation_readiness import EvidenceInventoryValidationError, validate_inventory

_DEFAULT_INVENTORY = Path("labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--inventory", type=Path, default=_DEFAULT_INVENTORY)
    return parser


def main() -> int:
    """Run the deterministic inventory verifier and return a process exit code."""
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    inventory_path = args.inventory
    if not inventory_path.is_absolute():
        inventory_path = repo_root / inventory_path

    try:
        summary = validate_inventory(inventory_path=inventory_path, repo_root=repo_root)
    except EvidenceInventoryValidationError as exc:
        print(f"phase18_evidence_inventory=FAIL reason={exc}")
        return 1

    print(
        "phase18_evidence_inventory=PASS "
        f"records={summary.record_count} "
        f"artifacts={summary.evidence_artifact_count} "
        f"groups={summary.comparability_group_count} "
        f"non_comparable_pairs={summary.non_comparability_assertion_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
