"""Run the frozen Gate 12.2 multi-agent comparison fixture without model calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from opslens.multi_agent.application.comparison import (
    evaluate_multi_agent_comparison_dataset,
    load_multi_agent_comparison_dataset,
)
from opslens.multi_agent.domain.comparison import MultiAgentComparisonCaseScore

_DEFAULT_DATASET = Path("tests/fixtures/multi_agent/golden_multi_agent_comparison_v1.json")


def _parser() -> argparse.ArgumentParser:
    """Build the bounded offline comparison CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the frozen Gate 12.2 synthetic handoff fixture deterministically. "
            "No model or capability execution is performed."
        )
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=_DEFAULT_DATASET,
        help="Frozen comparison dataset path.",
    )
    return parser


def _score_projection(score: MultiAgentComparisonCaseScore) -> dict[str, object]:
    """Project one content-minimized deterministic case score for CLI output."""
    return {
        "admission_match": score.admission_match,
        "bounds_compliant": score.bounds_compliant,
        "case_id": score.case_id,
        "case_key": score.case_key,
        "decision_match": score.decision_match,
        "non_broadening": score.non_broadening,
        "observed_admission_outcome": score.observed_admission_outcome.value,
        "observed_decision": score.observed_decision.value,
        "observed_specialization": (
            score.observed_specialization.value
            if score.observed_specialization is not None
            else None
        ),
        "observed_target_capabilities": [
            capability.value for capability in score.observed_target_capabilities
        ],
        "passed": score.passed,
        "score_id": score.score_id,
        "score_sha256": score.score_sha256,
        "source_capability_slots": score.source_capability_slots,
        "specialist_capability_slots": score.specialist_capability_slots,
        "specialization_match": score.specialization_match,
        "target_scope_match": score.target_scope_match,
    }


def main() -> int:
    """Load and evaluate the frozen fixture, returning nonzero on conformance failure."""
    args = _parser().parse_args()
    dataset_path = cast(Path, args.dataset)
    dataset = load_multi_agent_comparison_dataset(dataset_path)
    report = evaluate_multi_agent_comparison_dataset(dataset)
    output: dict[str, object] = {
        "contract_version": "multi-agent-comparison:v1",
        "dataset_id": dataset.dataset_id,
        "dataset_sha256": dataset.dataset_sha256,
        "phase11_reference": {
            "corpus_sha256": dataset.phase11_reference_corpus_sha256,
            "report_sha256": dataset.phase11_reference_report_sha256,
        },
        "report_id": report.report_id,
        "report_sha256": report.report_sha256,
        "metrics": {
            "abstention_cases": report.abstention_cases,
            "admission_matches": report.admission_matches,
            "bounds_compliant_cases": report.bounds_compliant_cases,
            "capability_slots_removed": report.capability_slots_removed,
            "decision_matches": report.decision_matches,
            "handoff_cases": report.handoff_cases,
            "non_broadening_cases": report.non_broadening_cases,
            "offline_capability_executions": report.offline_capability_executions,
            "passed_cases": report.passed_cases,
            "source_capability_slots_for_handoffs": (
                report.source_capability_slots_for_handoffs
            ),
            "specialist_capability_slots": report.specialist_capability_slots,
            "specialization_matches": report.specialization_matches,
            "target_scope_matches": report.target_scope_matches,
            "total_cases": report.total_cases,
        },
        "runtime_measurements": {
            "client_elapsed_ms": report.client_elapsed_ms,
            "inference_cost_usd": report.inference_cost_usd,
            "input_tokens": report.input_tokens,
            "model_invocation_count": report.model_invocation_count,
            "output_tokens": report.output_tokens,
            "provider_latency_ms": report.provider_latency_ms,
            "sdk_retries": report.sdk_retries,
            "total_tokens": report.total_tokens,
        },
        "scores": [_score_projection(score) for score in report.case_scores],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if report.passed_cases == report.total_cases else 2


if __name__ == "__main__":
    raise SystemExit(main())
