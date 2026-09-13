"""Run the single versioned Gate 8.5 hybrid synthesis optimization experiment."""

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
    BEDROCK_SYNTHESIS_REGION,
)
from opslens.hybrid_retrieval.application.evaluation import (
    load_hybrid_evaluation_dataset,
)
from opslens.hybrid_retrieval.application.optimization import (
    GATE_8_4_BASELINE_ABSTENTION,
    GATE_8_4_BASELINE_CITATION_CORRECTNESS,
    GATE_8_4_BASELINE_INPUT_TOKENS,
    GATE_8_4_BASELINE_LATENCY_MS,
    GATE_8_4_BASELINE_OUTPUT_TOKENS,
    GATE_8_4_BASELINE_ROUTE_ACCURACY,
    GATE_8_4_BASELINE_SEMANTIC_GROUNDEDNESS,
    GATE_8_4_BASELINE_STRUCTURED_FACT_CORRECTNESS,
    GATE_8_4_BASELINE_TOTAL_TOKENS,
    GATE_8_5_EXPERIMENT_ID,
    GATE_8_5_HYPOTHESIS_ID,
    HybridOptimizationComparison,
    evaluate_gate_8_5_hypothesis,
)
from opslens.hybrid_retrieval.application.synthesis_evaluation import (
    evaluate_hybrid_synthesis_runtime,
    run_hybrid_synthesis_runtime_evaluation,
)
from opslens.hybrid_retrieval.application.synthesis_prompt import (
    HybridSynthesisPromptPolicy,
)
from opslens.hybrid_retrieval.cli.run_bedrock_hybrid_synthesis_evaluation import (
    serialize_hybrid_runtime_execution,
)
from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError

_FROZEN_FIXTURE = Path("tests/fixtures/hybrid_retrieval/golden_hybrid_v1.json")
_REQUIRED_REGION = BEDROCK_SYNTHESIS_REGION
_CANDIDATE_POLICY = HybridSynthesisPromptPolicy.GATE_8_5_H85_01


class HybridOptimizationRuntimeCliError(ValueError):
    """Raised when Gate 8.5 runtime input drifts from H8.5-01."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the single H8.5-01 prompt-only experiment over the exact frozen "
            "six-case fixture. The model, retrieval evidence, output schema, and "
            "one-call execution budget are unchanged from Gate 8.4."
        )
    )
    parser.add_argument("--region", default=_REQUIRED_REGION)
    return parser


def _require_region(value: object) -> str:
    if not isinstance(value, str) or value != _REQUIRED_REGION:
        raise HybridOptimizationRuntimeCliError(
            f"region must equal the frozen synthesis region {_REQUIRED_REGION!r}"
        )
    return value


def _synthesis_config() -> Config:
    return Config(
        connect_timeout=5,
        read_timeout=90,
        retries={"max_attempts": 3, "mode": "standard"},
    )


def _baseline_reference_payload() -> dict[str, object]:
    return {
        "abstention": GATE_8_4_BASELINE_ABSTENTION,
        "citation_correctness": GATE_8_4_BASELINE_CITATION_CORRECTNESS,
        "input_tokens": GATE_8_4_BASELINE_INPUT_TOKENS,
        "latency_ms": GATE_8_4_BASELINE_LATENCY_MS,
        "output_tokens": GATE_8_4_BASELINE_OUTPUT_TOKENS,
        "route_accuracy": GATE_8_4_BASELINE_ROUTE_ACCURACY,
        "semantic_groundedness": GATE_8_4_BASELINE_SEMANTIC_GROUNDEDNESS,
        "structured_fact_correctness": (
            GATE_8_4_BASELINE_STRUCTURED_FACT_CORRECTNESS
        ),
        "total_tokens": GATE_8_4_BASELINE_TOTAL_TOKENS,
        "evidence_path": (
            "labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json"
        ),
    }


def _comparison_payload(
    comparison: HybridOptimizationComparison,
) -> dict[str, object]:
    return {
        "abstention": comparison.abstention,
        "citation_correctness": comparison.citation_correctness,
        "decision": comparison.decision.value,
        "input_token_delta": comparison.input_token_delta,
        "input_tokens": comparison.input_tokens,
        "latency_delta_ms": comparison.latency_delta_ms,
        "latency_ms": comparison.latency_ms,
        "output_token_delta": comparison.output_token_delta,
        "output_tokens": comparison.output_tokens,
        "rejection_reasons": list(comparison.rejection_reasons),
        "route_accuracy": comparison.route_accuracy,
        "semantic_groundedness": comparison.semantic_groundedness,
        "structured_fact_correctness": comparison.structured_fact_correctness,
        "total_token_delta": comparison.total_token_delta,
        "total_tokens": comparison.total_tokens,
    }


def _serialize_experiment(
    runtime_json: str,
    *,
    comparison: HybridOptimizationComparison | None,
) -> str:
    decoded: object = json.loads(runtime_json)
    if not isinstance(decoded, dict):
        raise HybridOptimizationRuntimeCliError(
            "Gate 8.4 runtime serializer must return one JSON object."
        )
    payload = cast(dict[str, object], decoded)
    payload["baseline_reference"] = _baseline_reference_payload()
    payload["experiment_id"] = GATE_8_5_EXPERIMENT_ID
    payload["hypothesis_id"] = GATE_8_5_HYPOTHESIS_ID
    payload["optimization_decision"] = (
        comparison.decision.value if comparison is not None else "incomplete"
    )
    payload["optimization_comparison"] = (
        _comparison_payload(comparison) if comparison is not None else None
    )
    payload["prompt_policy"] = _CANDIDATE_POLICY.value
    payload["single_run_hypothesis"] = True
    return json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Measure H8.5-01 once; quality rejection is a valid completed experiment."""
    args = _parser().parse_args(argv)
    try:
        region = _require_region(args.region)
        dataset = load_hybrid_evaluation_dataset(_FROZEN_FIXTURE)
        session = get_session()
        dynamic_client = session.create_client(
            "bedrock-runtime",
            region_name=region,
            config=_synthesis_config(),
        )
        client = cast(BedrockHybridConverseClient, dynamic_client)
        synthesizer = BedrockHybridSynthesizer(
            client,
            prompt_policy=_CANDIDATE_POLICY,
        )
        execution = run_hybrid_synthesis_runtime_evaluation(
            synthesizer.synthesize,
            dataset=dataset,
        )
        baseline = (
            evaluate_hybrid_synthesis_runtime(execution, dataset=dataset)
            if execution.complete
            else None
        )
        comparison = (
            evaluate_gate_8_5_hypothesis(execution, baseline=baseline)
            if baseline is not None
            else None
        )
        runtime_json = serialize_hybrid_runtime_execution(
            execution,
            baseline=baseline,
            region=region,
        )
        serialized = _serialize_experiment(
            runtime_json,
            comparison=comparison,
        )
    except (
        BotoCoreError,
        ClientError,
        HybridOptimizationRuntimeCliError,
        HybridRetrievalValidationError,
        OSError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(serialized, end="")
    return 0 if execution.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
