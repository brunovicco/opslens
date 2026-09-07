#!/usr/bin/env python3
"""Run the frozen Gate 11.4 single-agent reasoning corpus through Amazon Bedrock."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import cast

from boto3.session import Session
from botocore.config import Config

from opslens.agent_baseline.adapters import (
    BEDROCK_AGENT_REASONING_REGION,
    BedrockAgentReasoningConverseClient,
    BedrockSingleAgentReasoningModel,
)
from opslens.agent_baseline.application import (
    load_agent_reasoning_evaluation_dataset,
    reason_about_task,
)
from opslens.agent_baseline.domain import (
    AgentReasoningCaseScore,
    AgentReasoningEvaluationReport,
)

_DEFAULT_DATASET = (
    Path(__file__).parents[1]
    / "tests"
    / "fixtures"
    / "agent_baseline"
    / "golden_single_agent_reasoning_v1.json"
)


def _parse_args() -> argparse.Namespace:
    """Parse explicit local credential and dataset options without model selection authority."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen OpsLens Gate 11.4 reasoning corpus through one fixed Bedrock "
            "Converse adapter. No capability execution is performed."
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
        help="Frozen reasoning dataset path.",
    )
    return parser.parse_args()


def _bedrock_client(session: Session) -> BedrockAgentReasoningConverseClient:
    """Create the fixed-region Bedrock runtime client behind the narrow Protocol boundary."""
    client: object = session.client(
        "bedrock-runtime",
        region_name=BEDROCK_AGENT_REASONING_REGION,
        config=Config(
            connect_timeout=10,
            read_timeout=300,
            retries={"total_max_attempts": 1, "mode": "standard"},
        ),
    )
    return cast(BedrockAgentReasoningConverseClient, client)


def main() -> int:
    """Execute one measured corpus replay and emit content-minimized JSON evidence."""
    args = _parse_args()
    dataset_path = cast(Path, args.dataset)
    profile = cast(str | None, args.profile)
    dataset = load_agent_reasoning_evaluation_dataset(dataset_path)

    session = Session(profile_name=profile)
    model = BedrockSingleAgentReasoningModel(_bedrock_client(session))

    scores: list[AgentReasoningCaseScore] = []
    observations: list[dict[str, object]] = []
    for case in dataset.cases:
        result = reason_about_task(task=case.task, model=model)
        score = AgentReasoningCaseScore.create(case=case, result=result)
        scores.append(score)
        observations.append(
            {
                "authorization_outcome": result.authorization_outcome.value,
                "case_key": case.case_key,
                "decision": result.proposal.decision.value,
                "capability": (
                    result.proposal.capability.value
                    if result.proposal.capability is not None
                    else None
                ),
                "reasoning_result_id": result.result_id,
                "invocation_evidence": asdict(result.invocation_evidence),
                "score": asdict(score),
            }
        )

    report = AgentReasoningEvaluationReport.create(
        dataset=dataset,
        scores=tuple(scores),
    )
    payload: dict[str, object] = {
        "corpus_sha256": dataset.corpus_sha256,
        "report_id": report.report_id,
        "report_sha256": report.report_sha256,
        "metrics": asdict(report.metrics),
        "observations": observations,
        "capability_executions": 0,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if report.metrics.passed_cases == report.metrics.total_cases else 2


if __name__ == "__main__":
    raise SystemExit(main())
