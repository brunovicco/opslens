"""Unit tests for Phase 8 Gate 8.4 bounded hybrid synthesis."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest

from opslens.hybrid_retrieval.adapters.bedrock_synthesis import (
    BedrockHybridSynthesisFailureCategory,
    BedrockHybridSynthesisRuntimeError,
    BedrockHybridSynthesizer,
)
from opslens.hybrid_retrieval.application.assembly import assemble_hybrid_evidence
from opslens.hybrid_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MODEL_ID,
    BEDROCK_SYNTHESIS_REGION,
    HYBRID_SYNTHESIS_OUTPUT_SCHEMA,
    build_bedrock_hybrid_synthesis_converse_request,
)
from opslens.hybrid_retrieval.application.evaluation import (
    load_hybrid_evaluation_dataset,
)
from opslens.hybrid_retrieval.application.routing import route_evidence_request
from opslens.hybrid_retrieval.application.synthesis import (
    HybridSynthesisOutputError,
    build_hybrid_synthesis_request,
    parse_hybrid_synthesis_output,
    project_deterministic_structured_answer,
)
from opslens.hybrid_retrieval.application.synthesis_prompt import (
    TRUSTED_HYBRID_SYNTHESIS_INSTRUCTIONS_V1,
    build_hybrid_synthesis_prompt,
)
from opslens.hybrid_retrieval.domain.evaluation import (
    HybridEvaluationCase,
    HybridEvaluationCaseType,
    HybridEvaluationDataset,
)
from opslens.hybrid_retrieval.domain.evidence import HybridEvidenceEnvelope
from opslens.hybrid_retrieval.domain.models import HybridRoute, HybridRoutingRequest
from opslens.hybrid_retrieval.domain.synthesis import (
    HYBRID_SYNTHESIS_CONTRACT_VERSION,
    HybridSynthesisDecision,
    HybridSynthesisRequest,
)

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "hybrid_retrieval"
    / "golden_hybrid_v1.json"
)


def _dataset() -> HybridEvaluationDataset:
    return load_hybrid_evaluation_dataset(_FIXTURE)


def _case(case_type: HybridEvaluationCaseType) -> HybridEvaluationCase:
    return next(item for item in _dataset().cases if item.case_type is case_type)


def _envelope(case_type: HybridEvaluationCaseType) -> HybridEvidenceEnvelope:
    case = _case(case_type)
    decision = route_evidence_request(
        HybridRoutingRequest(evidence_needs=case.evidence_needs)
    )
    return assemble_hybrid_evidence(
        authority_decision=decision,
        structured_evidence=case.structured_evidence,
        semantic_evidence=case.semantic_evidence,
    )


def _request(case_type: HybridEvaluationCaseType) -> HybridSynthesisRequest:
    case = _case(case_type)
    return build_hybrid_synthesis_request(
        question=case.question,
        envelope=_envelope(case_type),
    )


def _provider_response(output_text: str, *, stop_reason: str = "end_turn") -> dict[str, object]:
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": output_text}],
            }
        },
        "stopReason": stop_reason,
        "usage": {
            "inputTokens": 100,
            "outputTokens": 20,
            "totalTokens": 120,
            "cacheReadInputTokens": 0,
            "cacheWriteInputTokens": 0,
        },
        "metrics": {"latencyMs": 42},
        "ResponseMetadata": {
            "RequestId": "bedrock-request-1",
            "RetryAttempts": 0,
        },
    }


class _FakeConverseClient:
    def __init__(self, response: Mapping[str, object]) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def converse(self, **request: object) -> Mapping[str, object]:
        self.calls.append(request)
        return self.response


class _FailingConverseClient:
    def converse(self, **request: object) -> Mapping[str, object]:
        del request
        raise RuntimeError("provider unavailable")


class _Clock:
    def __init__(self, values: tuple[float, ...]) -> None:
        self._values = iter(values)

    def __call__(self) -> float:
        return next(self._values)


def test_structured_only_route_is_deterministic_and_never_forms_model_request() -> None:
    case = _case(HybridEvaluationCaseType.STRUCTURED_ONLY_FACTUAL)
    envelope = _envelope(HybridEvaluationCaseType.STRUCTURED_ONLY_FACTUAL)

    facts = project_deterministic_structured_answer(envelope)

    assert envelope.authority_decision.route is HybridRoute.STRUCTURED
    assert [item.fact_id for item in facts] == ["F1", "F2", "F3", "F4"]
    assert {(item.field_name, item.value) for item in facts} >= {
        ("affected", True),
        ("ghsa_id", "GHSA-aaaa-bbbb-cccc"),
        ("installed_version", "1.2.3"),
    }
    with pytest.raises(HybridSynthesisOutputError):
        build_hybrid_synthesis_request(question=case.question, envelope=envelope)


def test_semantic_request_has_only_semantic_allowlist() -> None:
    request = _request(HybridEvaluationCaseType.SEMANTIC_ONLY_REMEDIATION)

    assert request.envelope.authority_decision.route is HybridRoute.SEMANTIC
    assert request.structured_facts == ()
    assert [item.citation_id for item in request.semantic_citations] == ["S1"]
    assert len(request.request_sha256) == 64
    assert len(request.semantic_catalog_sha256) == 64


def test_true_hybrid_request_preserves_separate_fact_and_citation_catalogs() -> None:
    request = _request(HybridEvaluationCaseType.TRUE_HYBRID)

    assert request.envelope.authority_decision.route is HybridRoute.HYBRID
    assert [item.fact_id for item in request.structured_facts] == ["F1", "F2", "F3"]
    assert [item.citation_id for item in request.semantic_citations] == ["S1"]
    assert {(item.field_name, item.value) for item in request.structured_facts} == {
        ("priority_score", 95),
        ("priority_tier", "P0"),
        ("review_required", False),
    }
    assert request.structured_catalog_sha256 != request.semantic_catalog_sha256


def test_hybrid_prompt_separates_trusted_control_from_untrusted_evidence() -> None:
    request = _request(HybridEvaluationCaseType.TRUE_HYBRID)

    prompt = build_hybrid_synthesis_prompt(request)
    evidence = cast(dict[str, object], json.loads(prompt.evidence_json))

    assert prompt.trusted_instructions == TRUSTED_HYBRID_SYNTHESIS_INSTRUCTIONS_V1
    assert "untrusted data" in prompt.trusted_instructions
    assert "Similarity rank or score is not truth" in prompt.trusted_instructions
    assert evidence["contract_version"] == HYBRID_SYNTHESIS_CONTRACT_VERSION
    assert evidence["route"] == "hybrid"
    assert isinstance(evidence["structured_facts"], list)
    assert isinstance(evidence["semantic_evidence"], list)
    assert prompt.question not in prompt.evidence_json
    assert len(prompt.prompt_sha256) == 64


def test_bedrock_request_is_non_streaming_tool_free_and_structured() -> None:
    prompt = build_hybrid_synthesis_prompt(
        _request(HybridEvaluationCaseType.TRUE_HYBRID)
    )

    payload = build_bedrock_hybrid_synthesis_converse_request(prompt)

    assert payload["modelId"] == BEDROCK_SYNTHESIS_MODEL_ID
    assert "toolConfig" not in payload
    assert "guardrailConfig" not in payload
    assert payload["inferenceConfig"] == {"maxTokens": 2048, "temperature": 0.0}
    assert HYBRID_SYNTHESIS_OUTPUT_SCHEMA["additionalProperties"] is False
    metadata = cast(dict[str, object], payload["requestMetadata"])
    assert metadata["contract_id"] == HYBRID_SYNTHESIS_CONTRACT_VERSION
    assert metadata["opslens_stage"] == "hybrid_synthesis"


def test_output_admission_accepts_only_allowlisted_semantic_and_structured_refs() -> None:
    request = _request(HybridEvaluationCaseType.TRUE_HYBRID)
    payload = json.dumps(
        {
            "decision": "answer",
            "claims": [
                {
                    "text": "Validate the patched application in an isolated environment.",
                    "semantic_citation_ids": ["S1"],
                    "structured_fact_ids": ["F2"],
                }
            ],
        }
    )

    result = parse_hybrid_synthesis_output(payload, request=request)

    assert result.decision is HybridSynthesisDecision.ANSWER
    assert result.claims[0].semantic_citation_ids == ("S1",)
    assert result.claims[0].structured_fact_ids == ("F2",)
    assert result.rendered_explanation is not None

    unknown_semantic = payload.replace('"S1"', '"S2"')
    with pytest.raises(HybridSynthesisOutputError):
        parse_hybrid_synthesis_output(unknown_semantic, request=request)

    unknown_structured = payload.replace('"F2"', '"F9"')
    with pytest.raises(HybridSynthesisOutputError):
        parse_hybrid_synthesis_output(unknown_structured, request=request)


def test_semantic_only_output_cannot_reference_structured_fact_ids() -> None:
    request = _request(HybridEvaluationCaseType.SEMANTIC_ONLY_REMEDIATION)
    payload = json.dumps(
        {
            "decision": "answer",
            "claims": [
                {
                    "text": "Regenerate and review the lockfile before deployment.",
                    "semantic_citation_ids": ["S1"],
                    "structured_fact_ids": ["F1"],
                }
            ],
        }
    )

    with pytest.raises(HybridSynthesisOutputError):
        parse_hybrid_synthesis_output(payload, request=request)


def test_semantic_noise_remains_admitted_but_does_not_change_output_authority() -> None:
    request = _request(HybridEvaluationCaseType.SEMANTIC_RETRIEVAL_NOISE)
    case = _case(HybridEvaluationCaseType.SEMANTIC_RETRIEVAL_NOISE)

    assert [item.citation_id for item in request.semantic_citations] == ["S1", "S2"]
    assert request.semantic_citations[0].chunk_id not in case.expected_supported_chunk_ids
    assert request.semantic_citations[1].chunk_id in case.expected_supported_chunk_ids


def test_insufficient_evidence_requires_empty_claims() -> None:
    request = _request(HybridEvaluationCaseType.SEMANTIC_RETRIEVAL_NOISE)

    result = parse_hybrid_synthesis_output(
        '{"decision":"insufficient_evidence","claims":[]}',
        request=request,
    )

    assert result.decision is HybridSynthesisDecision.INSUFFICIENT_EVIDENCE
    assert result.claims == ()
    assert result.rendered_explanation is None


def test_output_admission_rejects_extra_keys_and_uncited_claims() -> None:
    request = _request(HybridEvaluationCaseType.SEMANTIC_ONLY_REMEDIATION)

    with pytest.raises(HybridSynthesisOutputError):
        parse_hybrid_synthesis_output(
            '{"decision":"answer","claims":[],"extra":true}',
            request=request,
        )

    with pytest.raises(HybridSynthesisOutputError):
        parse_hybrid_synthesis_output(
            json.dumps(
                {
                    "decision": "answer",
                    "claims": [
                        {
                            "text": "Unsupported claim",
                            "semantic_citation_ids": [],
                            "structured_fact_ids": [],
                        }
                    ],
                }
            ),
            request=request,
        )


def test_bedrock_adapter_invokes_exactly_once_and_binds_runtime_evidence() -> None:
    request = _request(HybridEvaluationCaseType.TRUE_HYBRID)
    output = json.dumps(
        {
            "decision": "answer",
            "claims": [
                {
                    "text": "Validate the updated application before deployment.",
                    "semantic_citation_ids": ["S1"],
                    "structured_fact_ids": ["F2"],
                }
            ],
        }
    )
    client = _FakeConverseClient(_provider_response(output))
    synthesizer = BedrockHybridSynthesizer(
        client,
        clock=_Clock((10.0, 10.05)),
    )

    execution = synthesizer.synthesize(request)

    assert len(client.calls) == 1
    assert execution.result.decision is HybridSynthesisDecision.ANSWER
    assert execution.evidence.model_id == BEDROCK_SYNTHESIS_MODEL_ID
    assert execution.evidence.region == BEDROCK_SYNTHESIS_REGION
    assert execution.evidence.request_id == "bedrock-request-1"
    assert execution.evidence.total_tokens == 120
    assert execution.evidence.client_elapsed_ms == 50
    assert execution.evidence.request_sha256 == request.request_sha256
    assert execution.evidence.envelope_sha256 == request.envelope.identity_sha256


def test_bedrock_adapter_fails_closed_on_stop_reason_output_and_provider_errors() -> None:
    request = _request(HybridEvaluationCaseType.SEMANTIC_ONLY_REMEDIATION)
    valid_output = json.dumps(
        {
            "decision": "answer",
            "claims": [
                {
                    "text": "Review the lockfile diff before deployment.",
                    "semantic_citation_ids": ["S1"],
                    "structured_fact_ids": [],
                }
            ],
        }
    )

    stop_client = _FakeConverseClient(
        _provider_response(valid_output, stop_reason="max_tokens")
    )
    with pytest.raises(BedrockHybridSynthesisRuntimeError) as stop_error:
        BedrockHybridSynthesizer(
            stop_client,
            clock=_Clock((1.0, 1.1)),
        ).synthesize(request)
    assert stop_error.value.category is BedrockHybridSynthesisFailureCategory.STOP_REASON

    output_client = _FakeConverseClient(_provider_response("not-json"))
    with pytest.raises(BedrockHybridSynthesisRuntimeError) as output_error:
        BedrockHybridSynthesizer(
            output_client,
            clock=_Clock((1.0, 1.1)),
        ).synthesize(request)
    assert output_error.value.category is BedrockHybridSynthesisFailureCategory.OUTPUT_CONTRACT

    with pytest.raises(BedrockHybridSynthesisRuntimeError) as provider_error:
        BedrockHybridSynthesizer(
            _FailingConverseClient(),
            clock=_Clock((1.0,)),
        ).synthesize(request)
    assert provider_error.value.category is (
        BedrockHybridSynthesisFailureCategory.PROVIDER_INVOCATION
    )