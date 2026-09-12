"""Unit tests for the single Gate 8.5 measured optimization hypothesis."""

import json
from collections.abc import Mapping
from pathlib import Path

from opslens.hybrid_retrieval.adapters.bedrock_synthesis import (
    BedrockHybridConverseClient,
    BedrockHybridSynthesisExecution,
    BedrockHybridSynthesisInvocationEvidence,
    BedrockHybridSynthesizer,
)
from opslens.hybrid_retrieval.application.assembly import assemble_hybrid_evidence
from opslens.hybrid_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MODEL_ID,
    BEDROCK_SYNTHESIS_REGION,
)
from opslens.hybrid_retrieval.application.evaluation import (
    load_hybrid_evaluation_dataset,
)
from opslens.hybrid_retrieval.application.optimization import (
    GATE_8_5_EXPERIMENT_ID,
    GATE_8_5_HYPOTHESIS_ID,
    HybridOptimizationDecision,
    evaluate_gate_8_5_hypothesis,
)
from opslens.hybrid_retrieval.application.routing import route_evidence_request
from opslens.hybrid_retrieval.application.synthesis import (
    build_hybrid_synthesis_request,
    parse_hybrid_synthesis_output,
)
from opslens.hybrid_retrieval.application.synthesis_evaluation import (
    evaluate_hybrid_synthesis_runtime,
    run_hybrid_synthesis_runtime_evaluation,
)
from opslens.hybrid_retrieval.application.synthesis_prompt import (
    TRUSTED_HYBRID_SYNTHESIS_INSTRUCTIONS_H85_01,
    TRUSTED_HYBRID_SYNTHESIS_INSTRUCTIONS_V1,
    HybridSynthesisPromptPolicy,
    build_hybrid_synthesis_prompt,
)
from opslens.hybrid_retrieval.domain.evaluation import (
    HybridEvaluationCaseType,
    HybridEvaluationDataset,
)
from opslens.hybrid_retrieval.domain.models import HybridRoute, HybridRoutingRequest
from opslens.hybrid_retrieval.domain.synthesis import HybridSynthesisRequest

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "hybrid_retrieval"
    / "golden_hybrid_v1.json"
)

_GATE_8_4_PROMPT_SHA_BY_CASE = {
    HybridEvaluationCaseType.SEMANTIC_ONLY_REMEDIATION: (
        "7c240b766adeee0fa100b1658b6e1bf4a26c2cc0bf6ff820e87aaade2a5a24af"
    ),
    HybridEvaluationCaseType.TRUE_HYBRID: (
        "1319b042fc6c9006a8fc4eeb98abe8cec43d1cbaff51de912638deb05435c277"
    ),
    HybridEvaluationCaseType.SEMANTIC_RETRIEVAL_NOISE: (
        "50527cd3bbc05027848d2f94f8085540ac584add1deff78f071124c767260a1c"
    ),
}


def _dataset() -> HybridEvaluationDataset:
    return load_hybrid_evaluation_dataset(_FIXTURE)


def _request(case_type: HybridEvaluationCaseType) -> HybridSynthesisRequest:
    case = next(item for item in _dataset().cases if item.case_type is case_type)
    decision = route_evidence_request(
        HybridRoutingRequest(evidence_needs=case.evidence_needs)
    )
    envelope = assemble_hybrid_evidence(
        authority_decision=decision,
        structured_evidence=case.structured_evidence,
        semantic_evidence=case.semantic_evidence,
    )
    return build_hybrid_synthesis_request(
        question=case.question,
        envelope=envelope,
    )


class _NeverCalledClient(BedrockHybridConverseClient):
    def converse(self, **request: object) -> Mapping[str, object]:
        del request
        raise AssertionError("provider must not be invoked by policy inspection")


class _CandidateSynthesizer:
    def __init__(self, *, include_noise_claim: bool, retry_attempts: int = 0) -> None:
        self._include_noise_claim = include_noise_claim
        self._retry_attempts = retry_attempts
        self._call_count = 0

    def __call__(
        self,
        request: HybridSynthesisRequest,
    ) -> BedrockHybridSynthesisExecution:
        self._call_count += 1
        route = request.envelope.authority_decision.route
        claims: list[dict[str, object]]
        if route is HybridRoute.HYBRID:
            claims = [
                {
                    "text": "Validate the patched application before deployment.",
                    "semantic_citation_ids": ["S1"],
                    "structured_fact_ids": ["F1", "F2"],
                }
            ]
        elif len(request.semantic_citations) == 2:
            claims = [
                {
                    "text": "Review the lockfile diff for transitive dependency changes.",
                    "semantic_citation_ids": ["S2"],
                    "structured_fact_ids": [],
                }
            ]
            if self._include_noise_claim:
                claims.append(
                    {
                        "text": "Use a clean virtual environment when testing dependencies.",
                        "semantic_citation_ids": ["S1"],
                        "structured_fact_ids": [],
                    }
                )
        else:
            claims = [
                {
                    "text": "Regenerate and review the lockfile before deployment.",
                    "semantic_citation_ids": ["S1"],
                    "structured_fact_ids": [],
                }
            ]

        result = parse_hybrid_synthesis_output(
            json.dumps({"decision": "answer", "claims": claims}),
            request=request,
        )
        input_tokens = 1000 + self._call_count
        output_tokens = 100 + self._call_count
        evidence = BedrockHybridSynthesisInvocationEvidence(
            model_id=BEDROCK_SYNTHESIS_MODEL_ID,
            region=BEDROCK_SYNTHESIS_REGION,
            request_id=f"gate85-test-{self._call_count}",
            stop_reason="end_turn",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cache_read_input_tokens=0,
            cache_write_input_tokens=0,
            bedrock_latency_ms=900 + self._call_count,
            client_elapsed_ms=1000 + self._call_count,
            retry_attempts=self._retry_attempts,
            request_sha256=request.request_sha256,
            prompt_sha256=f"{self._call_count:064x}",
            envelope_sha256=request.envelope.identity_sha256,
            structured_catalog_sha256=request.structured_catalog_sha256,
            semantic_catalog_sha256=request.semantic_catalog_sha256,
        )
        return BedrockHybridSynthesisExecution(result=result, evidence=evidence)


def _comparison(
    *,
    include_noise_claim: bool,
    retry_attempts: int = 0,
):
    dataset = _dataset()
    execution = run_hybrid_synthesis_runtime_evaluation(
        _CandidateSynthesizer(
            include_noise_claim=include_noise_claim,
            retry_attempts=retry_attempts,
        ),
        dataset=dataset,
    )
    baseline = evaluate_hybrid_synthesis_runtime(execution, dataset=dataset)
    return evaluate_gate_8_5_hypothesis(execution, baseline=baseline)


def test_gate84_default_prompt_hashes_remain_exactly_frozen() -> None:
    """Adding a candidate policy must not alter the merged Gate 8.4 default prompt."""
    for case_type, expected_sha in _GATE_8_4_PROMPT_SHA_BY_CASE.items():
        prompt = build_hybrid_synthesis_prompt(_request(case_type))
        assert prompt.trusted_instructions == TRUSTED_HYBRID_SYNTHESIS_INSTRUCTIONS_V1
        assert prompt.prompt_sha256 == expected_sha


def test_gate85_candidate_is_explicit_and_changes_only_trusted_prompt_policy() -> None:
    """H8.5-01 must preserve request/evidence while changing the versioned prompt."""
    request = _request(HybridEvaluationCaseType.SEMANTIC_RETRIEVAL_NOISE)
    baseline = build_hybrid_synthesis_prompt(request)
    candidate = build_hybrid_synthesis_prompt(
        request,
        policy=HybridSynthesisPromptPolicy.GATE_8_5_H85_01,
    )

    assert candidate.request_sha256 == baseline.request_sha256
    assert candidate.evidence_json == baseline.evidence_json
    assert candidate.evidence_sha256 == baseline.evidence_sha256
    assert candidate.prompt_sha256 != baseline.prompt_sha256
    assert candidate.trusted_instructions == TRUSTED_HYBRID_SYNTHESIS_INSTRUCTIONS_H85_01
    assert "smallest sufficient set of claims and citations" in candidate.trusted_instructions
    assert "directly addresses the user's question" in candidate.trusted_instructions


def test_bedrock_synthesizer_keeps_gate84_default_and_requires_explicit_candidate() -> None:
    """The experiment cannot silently promote the candidate into the runtime default."""
    client = _NeverCalledClient()
    default = BedrockHybridSynthesizer(client)
    candidate = BedrockHybridSynthesizer(
        client,
        prompt_policy=HybridSynthesisPromptPolicy.GATE_8_5_H85_01,
    )

    assert default.prompt_policy is HybridSynthesisPromptPolicy.GATE_8_4_V1
    assert candidate.prompt_policy is HybridSynthesisPromptPolicy.GATE_8_5_H85_01


def test_gate85_accepts_only_when_quality_targets_and_guardrails_pass() -> None:
    """A candidate with exact support/citations and stable guardrails is ACCEPT."""
    comparison = _comparison(include_noise_claim=False)

    assert comparison.experiment_id == GATE_8_5_EXPERIMENT_ID
    assert comparison.hypothesis_id == GATE_8_5_HYPOTHESIS_ID
    assert comparison.decision is HybridOptimizationDecision.ACCEPT
    assert comparison.rejection_reasons == ()
    assert comparison.route_accuracy == 1.0
    assert comparison.structured_fact_correctness == 1.0
    assert comparison.semantic_groundedness == 1.0
    assert comparison.citation_correctness == 1.0
    assert comparison.abstention == 1.0


def test_gate85_rejects_candidate_when_noise_claim_remains() -> None:
    """H8.5-01 must be rejected if the measured Gate 8.4 weakness remains."""
    comparison = _comparison(include_noise_claim=True)

    assert comparison.decision is HybridOptimizationDecision.REJECT
    assert comparison.semantic_groundedness == 2.0 / 3.0
    assert comparison.citation_correctness == 2.0 / 3.0
    assert comparison.rejection_reasons == (
        "semantic_groundedness_target_not_met",
        "citation_correctness_target_not_met",
    )


def test_gate85_rejects_sdk_retry_even_if_quality_targets_pass() -> None:
    """A quality improvement cannot hide a runtime non-regression failure."""
    comparison = _comparison(
        include_noise_claim=False,
        retry_attempts=1,
    )

    assert comparison.decision is HybridOptimizationDecision.REJECT
    assert comparison.semantic_groundedness == 1.0
    assert comparison.citation_correctness == 1.0
    assert comparison.rejection_reasons == ("sdk_retry_regressed",)
