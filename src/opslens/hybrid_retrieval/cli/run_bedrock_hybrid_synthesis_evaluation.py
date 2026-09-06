"""Run the frozen Gate 8.4 hybrid synthesis evaluation against Bedrock once."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from botocore.session import get_session

from opslens.hybrid_retrieval.adapters.bedrock_synthesis import (
    BedrockHybridConverseClient,
    BedrockHybridSynthesizer,
)
from opslens.hybrid_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MODEL_ID,
    BEDROCK_SYNTHESIS_REGION,
)
from opslens.hybrid_retrieval.application.evaluation import (
    load_hybrid_evaluation_dataset,
)
from opslens.hybrid_retrieval.application.synthesis_evaluation import (
    HybridRuntimeCaseExecution,
    HybridRuntimeExecution,
    evaluate_hybrid_synthesis_runtime,
    run_hybrid_synthesis_runtime_evaluation,
)
from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.evaluation import (
    HYBRID_EVALUATION_DATASET_ID,
    HYBRID_EVALUATION_DATASET_SHA256,
    HybridMetricDimension,
)
from opslens.hybrid_retrieval.domain.synthesis_evaluation import HybridSynthesisBaseline

_DEFAULT_FIXTURE = Path("tests/fixtures/hybrid_retrieval/golden_hybrid_v1.json")
_REQUIRED_REGION = BEDROCK_SYNTHESIS_REGION


class HybridSynthesisRuntimeCliError(ValueError):
    """Raised when CLI input violates the frozen Gate 8.4 runtime contract."""


def _parser() -> argparse.ArgumentParser:
    """Build the explicit first-run Gate 8.4 Bedrock CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen six-case Gate 8.4 fixture exactly once. Structured, "
            "unsupported, and incomplete cases make zero model calls; semantic and "
            "hybrid cases make at most one non-streaming Bedrock Converse call each."
        )
    )
    parser.add_argument("--fixture", type=Path, default=_DEFAULT_FIXTURE)
    parser.add_argument("--region", default=_REQUIRED_REGION)
    return parser


def require_hybrid_synthesis_region(value: object) -> str:
    """Require the single frozen synthesis Region used by the Phase 7 profile."""
    if not isinstance(value, str) or value != _REQUIRED_REGION:
        raise HybridSynthesisRuntimeCliError(
            f"region must equal the frozen synthesis region {_REQUIRED_REGION!r}"
        )
    return value


def _synthesis_config() -> Config:
    """Return bounded transport settings without application-level retries."""
    return Config(
        connect_timeout=5,
        read_timeout=90,
        retries={"max_attempts": 3, "mode": "standard"},
    )


def _synthesis_payload(attempt: HybridRuntimeCaseExecution) -> dict[str, object] | None:
    """Serialize admitted claims and content-free provider runtime evidence."""
    synthesis = attempt.synthesis
    request = attempt.request
    if synthesis is None or request is None:
        return None
    by_id = {
        item.citation_id: item.chunk_id for item in request.semantic_citations
    }
    return {
        "bedrock_latency_ms": synthesis.evidence.bedrock_latency_ms,
        "cache_read_input_tokens": synthesis.evidence.cache_read_input_tokens,
        "cache_write_input_tokens": synthesis.evidence.cache_write_input_tokens,
        "claims": [
            {
                "claim_index": claim.claim_index,
                "semantic_citation_ids": list(claim.semantic_citation_ids),
                "semantic_chunk_ids": [
                    by_id[item] for item in claim.semantic_citation_ids
                ],
                "structured_fact_ids": list(claim.structured_fact_ids),
                "text": claim.text,
            }
            for claim in synthesis.result.claims
        ],
        "client_elapsed_ms": synthesis.evidence.client_elapsed_ms,
        "decision": synthesis.result.decision.value,
        "envelope_sha256": synthesis.evidence.envelope_sha256,
        "input_tokens": synthesis.evidence.input_tokens,
        "model_id": synthesis.evidence.model_id,
        "output_tokens": synthesis.evidence.output_tokens,
        "prompt_sha256": synthesis.evidence.prompt_sha256,
        "provider_request_id": synthesis.evidence.request_id,
        "request_sha256": synthesis.evidence.request_sha256,
        "result_sha256": synthesis.result.result_sha256,
        "retry_attempts": synthesis.evidence.retry_attempts,
        "semantic_catalog_sha256": synthesis.evidence.semantic_catalog_sha256,
        "stop_reason": synthesis.evidence.stop_reason,
        "structured_catalog_sha256": synthesis.evidence.structured_catalog_sha256,
        "total_tokens": synthesis.evidence.total_tokens,
    }


def _attempt_payload(attempt: HybridRuntimeCaseExecution) -> dict[str, object]:
    """Serialize one bounded case without model-visible source bodies."""
    return {
        "application_complete": attempt.complete,
        "case_id": attempt.case.case_id,
        "expected_answer_behavior": attempt.case.expected_answer_behavior.value,
        "expected_citation_chunk_ids": list(attempt.case.expected_citation_chunk_ids),
        "expected_supported_chunk_ids": list(attempt.case.expected_supported_chunk_ids),
        "failure_category": attempt.failure_category,
        "model_required": attempt.request is not None,
        "observed_answer_behavior": (
            attempt.observed_behavior.value
            if attempt.observed_behavior is not None
            else None
        ),
        "route": attempt.route_decision.route.value,
        "structured_facts": [
            {
                "authority": item.authority,
                "evidence_id": item.evidence_id,
                "fact_id": item.fact_id,
                "field_name": item.field_name,
                "value": item.value,
            }
            for item in attempt.structured_facts
        ],
        "synthesis": _synthesis_payload(attempt),
    }


def _measurement_payload(baseline: HybridSynthesisBaseline) -> dict[str, object]:
    """Serialize every independent metric without a composite score."""
    return {
        metric.value: {
            "status": baseline.measurement(metric).status.value,
            "unit": baseline.measurement(metric).unit.value,
            "value": baseline.measurement(metric).value,
        }
        for metric in HybridMetricDimension
    }


def serialize_hybrid_runtime_execution(
    execution: HybridRuntimeExecution,
    *,
    baseline: HybridSynthesisBaseline | None,
    region: str,
) -> str:
    """Serialize immutable first-run runtime evidence and measured Gate 8.4 metrics."""
    return json.dumps(
        {
            "complete": execution.complete,
            "dataset_id": execution.dataset_id,
            "dataset_sha256": execution.dataset_sha256,
            "expected_dataset_id": HYBRID_EVALUATION_DATASET_ID,
            "expected_dataset_sha256": HYBRID_EVALUATION_DATASET_SHA256,
            "fixture_support_targets_frozen": True,
            "measurements": (
                _measurement_payload(baseline) if baseline is not None else None
            ),
            "model_call_count": sum(
                attempt.synthesis is not None for attempt in execution.attempts
            ),
            "model_id": BEDROCK_SYNTHESIS_MODEL_ID,
            "planned_case_count": execution.planned_case_count,
            "region": region,
            "cases": [_attempt_payload(attempt) for attempt in execution.attempts],
        },
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the frozen Gate 8.4 fixture once and emit reviewable JSON evidence."""
    args = _parser().parse_args(argv)
    fixture_path = cast(Path, args.fixture)

    try:
        region = require_hybrid_synthesis_region(args.region)
        dataset = load_hybrid_evaluation_dataset(fixture_path)
        session = get_session()
        dynamic_client = session.create_client(
            "bedrock-runtime",
            region_name=region,
            config=_synthesis_config(),
        )
        client = cast(BedrockHybridConverseClient, dynamic_client)
        synthesizer = BedrockHybridSynthesizer(client)
        execution = run_hybrid_synthesis_runtime_evaluation(
            synthesizer.synthesize,
            dataset=dataset,
        )
        baseline = (
            evaluate_hybrid_synthesis_runtime(execution, dataset=dataset)
            if execution.complete
            else None
        )
        serialized = serialize_hybrid_runtime_execution(
            execution,
            baseline=baseline,
            region=region,
        )
    except (
        BotoCoreError,
        ClientError,
        HybridRetrievalValidationError,
        HybridSynthesisRuntimeCliError,
        OSError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(serialized, end="")
    return 0 if execution.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
