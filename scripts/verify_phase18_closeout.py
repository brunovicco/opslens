#!/usr/bin/env python3
"""Verify the historical Phase 18 closeout artifact and current post-merge docs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from opslens.evaluation_readiness import validate_portfolio_pack

_CLOSEOUT = Path("labs/evidence/phase-18-closeout-v1.json")
_PORTFOLIO = Path("labs/evidence/phase-18-gate-18-4-portfolio-evidence-pack-v1.json")
_AIP_MAP = Path("labs/evidence/phase-18-gate-18-4-aip-c01-evidence-map-v1.json")

_EXPECTED_COUNTS = {
    "evidence_inventory_metrics": 27,
    "evidence_source_artifacts": 8,
    "comparability_groups": 20,
    "explicit_non_comparability_assertions": 11,
    "evaluation_dimensions": 5,
    "retained_decision_signals": 4,
    "cost_accounting_entries": 16,
    "configured_limit_claims": 7,
    "portfolio_headline_claims": 11,
    "aip_c01_tasks": 20,
    "aip_c01_evidenced_tasks": 14,
    "aip_c01_partial_tasks": 6,
    "aip_c01_study_only_tasks": 0,
}

_EXPECTED_AUTHORITY = {
    "aws_mutations": 0,
    "iam_mutations": 0,
    "new_aws_services": 0,
    "runtime_mutations": 0,
    "model_invocations": 0,
    "capability_executions": 0,
    "benchmark_replays": 0,
    "pricing_refresh": False,
    "production_tco_created": False,
    "business_authority_changed": False,
    "pr_89_touched": False,
}

_EXPECTED_GATE_18_4 = {
    "pull_request": 288,
    "implementation_head_sha": "c1eef255e6a98fb9a556fea191db8a41d13c2437",
    "protected_squash_merge_sha": "4a8e5d3d98504451cef26df4e9f274f2f9fd8dd0",
}

_EXPECTED_RUNS = {
    "security_hardening_ci": 34508507768,
    "dependency_review": 34508507778,
    "evaluation_readiness_ci": 34508507792,
    "agentcore_ci": 34508507802,
    "codeql": 34508507840,
}

_EXPECTED_ARTIFACTS = {
    "labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json",
    "labs/evidence/phase-18-gate-18-2-consolidated-view-v1.json",
    "labs/evidence/phase-18-gate-18-2-decision-signals-v1.json",
    "labs/evidence/phase-18-gate-18-3-cost-accounting-v1.json",
    "labs/evidence/phase-18-gate-18-4-portfolio-evidence-pack-v1.json",
    "labs/evidence/phase-18-gate-18-4-aip-c01-evidence-map-v1.json",
}

_REQUIRED_BOUNDARIES = {
    "MEASURED != DERIVED",
    "UNMEASURED != zero",
    "NOT_APPLICABLE != zero",
    "configured limit != measured utilization",
    "portfolio claim != new evidence authority",
    "AIP-C01 topic != product requirement",
    "AIP-C01 coverage != certification guarantee",
    "lab metric != production SLO",
    "cost evidence != production TCO",
    "historical experiment != standing authority",
    "Repository Risk != Runtime Exposure.",
}

# Gate 18.5's own evidence is intentionally historical. Current-facing documentation,
# however, must represent the fact that protected PR #290 has already merged.
_REQUIRED_DOC_MARKERS = {
    "docs/current-state.md": (
        "feca774535b7d83f57c26f4e9fe7da71ce268f0f",
        "Phase 18 — Evaluation, Cost & Portfolio Readiness",
        "status: COMPLETE",
        "Phase 19 — Bounded Public Runtime & Productization",
    ),
    "docs/roadmap.md": (
        "Phase 18  Evaluation, Cost & Portfolio Readiness              COMPLETE",
        "Phase 19  Bounded Public Runtime & Productization             IN PROGRESS",
        "Gate 19.1",
    ),
    "README.md": (
        "Phases 0–18 are complete.",
        "Phase 19 — Bounded Public Runtime & Productization",
    ),
    "README.pt-br.md": (
        "Phases 0–18 estão completas.",
        "Phase 19 — Bounded Public Runtime & Productization",
    ),
    "docs/architecture.md": (
        "Phases 0–18 are complete.",
        "Phase 19 — Bounded Public Runtime & Productization",
    ),
    "docs/architecture.pt-br.md": (
        "As Phases 0–18 estão completas.",
        "Phase 19 — Bounded Public Runtime & Productization",
    ),
}

_FORBIDDEN_LIVE_DOC_MARKERS = (
    "Gate 18.5 — Phase 18 closeout                               IN PROGRESS",
    "Gate 18.5 — Phase 18 closeout — IN PROGRESS",
    "18.5  Phase 18 evidence-backed closeout          IN PROGRESS",
    "COMPLETE PENDING GATE 18.5",
    "COMPLETE PENDING GATE 18.5 MERGE",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser


def _load_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"closeout artifact must be a JSON object: {path}")
    return cast(dict[str, object], value)


def _dict(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _string_set(value: object, *, label: str) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit(f"{label} must be a string array")
    return set(cast(list[str], value))


def _verify_closeout_artifact(repo_root: Path) -> None:
    """Keep validating the exact pre-merge Gate 18.5 evidence rather than rewriting history."""
    root = _load_object(repo_root / _CLOSEOUT)
    expected_scalar = {
        "artifact_version": "phase-18-closeout:v1",
        "evidence_date": "2026-09-10",
        "phase": "Phase 18 — Evaluation, Cost & Portfolio Readiness",
        "gate": "18.5 — Phase closeout",
        "issue": 289,
        "source_main_sha": "4a8e5d3d98504451cef26df4e9f274f2f9fd8dd0",
        "status": "PHASE_18_COMPLETE_PENDING_GATE_18_5_PROTECTED_MERGE",
        "decision": "CLOSE_PHASE_18_AT_EVIDENCE_BACKED_EVALUATION_COST_PORTFOLIO_BOUNDARY",
    }
    for key, expected in expected_scalar.items():
        if root.get(key) != expected:
            raise SystemExit(f"Phase 18 closeout scalar drifted: {key}")

    progression = _dict(root.get("gate_progression"), label="gate_progression")
    if progression != {
        "18.1": "COMPLETE_CROSS_PHASE_EVIDENCE_INVENTORY_AND_COMPARABILITY",
        "18.2": "COMPLETE_CONSOLIDATED_EVALUATION_AND_RELIABILITY_VIEW",
        "18.3": "COMPLETE_COST_ACCOUNTING_AND_CONFIGURED_BUDGET_ENVELOPES",
        "18.4": "COMPLETE_EVIDENCE_BOUND_PORTFOLIO_AND_AIP_C01_MAPPING",
        "18.5": "CLOSEOUT_PENDING_EXACT_HEAD_CI_AND_PROTECTED_MERGE",
    }:
        raise SystemExit("Phase 18 gate progression drifted")

    retained = _dict(root.get("retained_phase_18_contract"), label="retained_phase_18_contract")
    if retained != _EXPECTED_COUNTS:
        raise SystemExit("Phase 18 retained contract counts drifted")

    authority = _dict(root.get("gate_18_5_authority_impact"), label="gate_18_5_authority_impact")
    if authority != _EXPECTED_AUTHORITY:
        raise SystemExit("Gate 18.5 authority impact drifted")

    artifacts = _string_set(root.get("canonical_artifacts"), label="canonical_artifacts")
    if artifacts != _EXPECTED_ARTIFACTS:
        raise SystemExit("Phase 18 canonical artifact set drifted")
    for path_text in artifacts:
        if not (repo_root / path_text).is_file():
            raise SystemExit(f"canonical Phase 18 artifact missing: {path_text}")

    boundaries = _string_set(root.get("retained_boundaries"), label="retained_boundaries")
    if not _REQUIRED_BOUNDARIES.issubset(boundaries):
        raise SystemExit("Phase 18 closeout boundaries are incomplete")

    gate_18_4 = _dict(root.get("gate_18_4_final_validation"), label="gate_18_4_final_validation")
    for key, expected in _EXPECTED_GATE_18_4.items():
        if gate_18_4.get(key) != expected:
            raise SystemExit(f"Gate 18.4 merge evidence drifted: {key}")
    for key, run_id in _EXPECTED_RUNS.items():
        run = _dict(gate_18_4.get(key), label=f"gate_18_4_final_validation.{key}")
        if run != {"run_id": run_id, "conclusion": "SUCCESS"}:
            raise SystemExit(f"Gate 18.4 CI evidence drifted: {key}")

    # This is the historical decision that existed at Gate 18.5 creation time.
    # A later Phase 19 selection must not rewrite this source evidence.
    next_direction = _dict(root.get("next_direction"), label="next_direction")
    if next_direction != {
        "status": "NOT_AUTHORIZED_PENDING_EVIDENCE_BACKED_SELECTION",
        "phase_number_reserved": False,
        "governed_gateway_pr_89": "DEFERRED_SEPARATE_WORK",
    }:
        raise SystemExit("Historical post-Phase-18 direction was rewritten")


def _verify_docs(repo_root: Path) -> None:
    for path_text, markers in _REQUIRED_DOC_MARKERS.items():
        text = (repo_root / path_text).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                raise SystemExit(f"{path_text} is missing post-merge Phase 18 marker {marker!r}")
        for marker in _FORBIDDEN_LIVE_DOC_MARKERS:
            if marker in text:
                raise SystemExit(f"{path_text} still contains stale post-merge marker {marker!r}")


def main() -> int:
    """Revalidate Gate 18.4/18.5 history and the current post-merge documentation projection."""
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()

    summary = validate_portfolio_pack(
        portfolio_path=repo_root / _PORTFOLIO,
        aip_map_path=repo_root / _AIP_MAP,
        repo_root=repo_root,
    )
    observed = {
        "portfolio_headline_claims": summary.headline_metric_claim_count,
        "configured_limit_claims": summary.configured_budget_claim_count,
        "retained_decision_signals": summary.decision_signal_count,
        "aip_c01_tasks": summary.aip_task_count,
        "aip_c01_evidenced_tasks": summary.aip_evidenced_count,
        "aip_c01_partial_tasks": summary.aip_partial_count,
        "aip_c01_study_only_tasks": summary.aip_study_only_count,
    }
    for key, value in observed.items():
        if value != _EXPECTED_COUNTS[key]:
            raise SystemExit(f"Gate 18.4 retained count drifted at closeout: {key}")

    _verify_closeout_artifact(repo_root)
    _verify_docs(repo_root)

    print(
        "phase18_closeout=PASS "
        "historical_gate18_5_preserved=true "
        "protected_closeout_merge=feca774535b7d83f57c26f4e9fe7da71ce268f0f "
        "current_phase19_selected=true "
        "phase18_aws_mutations=0 phase18_iam_mutations=0 "
        "phase18_model_invocations=0 phase18_capability_executions=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
