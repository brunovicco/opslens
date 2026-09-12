#!/usr/bin/env python3
"""Verify the frozen Phase 18 Gate 18.4 portfolio and AIP-C01 evidence pack."""

import argparse
from pathlib import Path

from opslens.evaluation_readiness import validate_portfolio_pack

_DEFAULT_PORTFOLIO = Path(
    "labs/evidence/phase-18-gate-18-4-portfolio-evidence-pack-v1.json"
)
_DEFAULT_AIP_MAP = Path(
    "labs/evidence/phase-18-gate-18-4-aip-c01-evidence-map-v1.json"
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--portfolio", type=Path, default=_DEFAULT_PORTFOLIO)
    parser.add_argument("--aip-map", type=Path, default=_DEFAULT_AIP_MAP)
    return parser


def main() -> int:
    """Validate the canonical Gate 18.4 artifacts and emit one bounded marker."""
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    portfolio_path = args.portfolio
    aip_map_path = args.aip_map
    if not portfolio_path.is_absolute():
        portfolio_path = repo_root / portfolio_path
    if not aip_map_path.is_absolute():
        aip_map_path = repo_root / aip_map_path

    summary = validate_portfolio_pack(
        portfolio_path=portfolio_path,
        aip_map_path=aip_map_path,
        repo_root=repo_root,
    )
    print(
        "phase18_portfolio_pack=PASS "
        f"headline_metrics={summary.headline_metric_claim_count} "
        f"configured_limits={summary.configured_budget_claim_count} "
        f"decision_signals={summary.decision_signal_count} "
        f"aip_tasks={summary.aip_task_count} "
        f"aip_evidenced={summary.aip_evidenced_count} "
        f"aip_partial={summary.aip_partial_count} "
        f"aip_study_only={summary.aip_study_only_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
