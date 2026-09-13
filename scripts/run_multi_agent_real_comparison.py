#!/usr/bin/env python3
"""Run the frozen Gate 12.3 two-model corpus through Amazon Bedrock."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import cast

from botocore.config import Config
from botocore.session import Session

from opslens.agent_baseline.adapters import (
    BedrockAgentReasoningConverseClient,
    BedrockSingleAgentReasoningModel,
)
from opslens.agent_baseline.domain.reasoning import AgentReasoningResult
from opslens.multi_agent.adapters import (
    BEDROCK_TRIAGE_REASONING_REGION,
    BedrockMultiAgentTriageModel,
    BedrockTriageConverseClient,
)
from opslens.multi_agent.application import (
    load_multi_agent_real_comparison_dataset,
    run_two_model_reasoning,
)
from opslens.multi_agent.domain.real_comparison import (
    MultiAgentRealComparisonCaseScore,
    MultiAgentRealComparisonReport,
)

_DEFAULT_DATASET = (
    Path(__file__).parents[1]
    / "tests"
    / "fixtures"
    / "multi_agent"
    / "golden_multi_agent_real_comparison_v1.json"
)


def _parse_args() -> argparse.Namespace:
    """Parse local credential and dataset options without model-selection authority."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen OpsLens Gate 12.3 corpus through fixed Bedrock triage and "
            "specialist reasoning adapters. No capability execution is performed."
        )
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Optional local AWS profile; omitted uses the standard SDK credential chain.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=_DEFAULT_DATASET,
        help="Frozen Gate 12.3 real-comparison dataset path.",
    )
    return parser.parse_args()


def _bedrock_client(session: Session) -> object:
    """Create one fixed-region Bedrock runtime client with retries disabled by policy."""
    return session.create_client(
        "bedrock-runtime",
        region_name=BEDROCK_TRIAGE_REASONING_REGION,
        config=Config(
            connect_timeout=10,
            read_timeout=300,
            retries={"total_max_attempts": 1, "mode": "standard"},
        ),
    )


def _specialist_observation(result: object) -> object:
    """Project optional specialist evidence without raw model output."""
    if result is None:
        return None
    if type(result) is not AgentReasoningResult:
        raise TypeError("specialist result must be AgentReasoningResult or null")
    return {
        "authorization_outcome": result.authorization_outcome.value,
        "capability": (
            result.proposal.capability.value
            if result.proposal.capability is not None
            else None
        ),
        "decision": result.proposal.decision.value,
        "invocation_evidence": asdict(result.invocation_evidence),
        "reasoning_result_id": result.result_id,
        "task_id": result.task.task_id,
    }


def main() -> int:
    """Execute one measured two-model corpus replay and emit minimized JSON evidence."""
    args = _parse_args()
    dataset_path = cast(Path, args.dataset)
    profile = cast(str | None, args.profile)
    dataset = load_multi_agent_real_comparison_dataset(dataset_path)

    session = Session(profile=profile)
    client = _bedrock_client(session)
    triage_model = BedrockMultiAgentTriageModel(
        cast(BedrockTriageConverseClient, client)
    )
    specialist_model = BedrockSingleAgentReasoningModel(
        cast(BedrockAgentReasoningConverseClient, client)
    )

    scores: list[MultiAgentRealComparisonCaseScore] = []
    observations: list[dict[str, object]] = []
    for case in dataset.cases:
        result = run_two_model_reasoning(
            task=case.task,
            triage_model=triage_model,
            specialist_model=specialist_model,
        )
        score = MultiAgentRealComparisonCaseScore.create(case=case, result=result)
        scores.append(score)
        observations.append(
            {
                "case_key": case.case_key,
                "handoff_evidence_id": result.handoff_evidence_id,
                "model_invocation_count": result.model_invocation_count,
                "outcome": result.outcome.value,
                "result_id": result.result_id,
                "score": asdict(score),
                "specialist": _specialist_observation(result.specialist_result),
                "triage": {
                    "decision": result.triage_result.proposal.decision.value,
                    "invocation_evidence": asdict(
                        result.triage_result.invocation_evidence
                    ),
                    "reasoning_result_id": result.triage_result.result_id,
                    "target_specialization": (
                        result.triage_result.proposal.target_specialization.value
                        if result.triage_result.proposal.target_specialization is not None
                        else None
                    ),
                },
            }
        )

    report = MultiAgentRealComparisonReport.create(
        dataset=dataset,
        scores=tuple(scores),
    )
    payload: dict[str, object] = {
        "capability_executions": report.metrics.capability_executions,
        "dataset_id": dataset.dataset_id,
        "dataset_sha256": dataset.dataset_sha256,
        "gate12_reference_dataset_sha256": dataset.gate12_reference_dataset_sha256,
        "gate12_reference_report_sha256": dataset.gate12_reference_report_sha256,
        "inference_cost_usd": None,
        "metrics": asdict(report.metrics),
        "observations": observations,
        "phase11_reference_corpus_sha256": dataset.phase11_reference_corpus_sha256,
        "phase11_reference_report_sha256": dataset.phase11_reference_report_sha256,
        "report_id": report.report_id,
        "report_sha256": report.report_sha256,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if report.metrics.passed_cases == report.metrics.total_cases else 2


if __name__ == "__main__":
    raise SystemExit(main())
