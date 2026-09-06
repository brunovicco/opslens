"""Tests for the bounded Gate 7.4 real Retrieve CLI evidence boundary."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import cast

import pytest

from opslens.knowledge_retrieval.application.bedrock_retrieval import (
    BedrockRetrieveInvocationEvidence,
    BedrockRetrieveResult,
)
from opslens.knowledge_retrieval.cli.run_bedrock_retrieve import (
    RetrieveCliError,
    main,
    require_retrieve_region,
    serialize_retrieve_evidence,
)
from opslens.knowledge_retrieval.domain import (
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
)

_TEXT = "Canonical remediation evidence that must not be serialized by the CLI."


def _result() -> BedrockRetrieveResult:
    """Build one admitted retrieval result for content-free serialization tests."""
    request = RetrievalRequest(query="How should I remediate this dependency?", top_k=1)
    chunk = RetrievedChunk.from_text(
        chunk_id="knowledge-chunk:test:remediation:v1",
        document_id="knowledge-doc:test:v1",
        source_id="example:test",
        source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
        canonical_uri="https://example.com/security/remediation/",
        document_content_sha256="a" * 64,
        text=_TEXT,
        rank=1,
        relevance_score=0.89,
        title="Example remediation",
        section_path=("Remediation",),
    )
    evidence = RetrievalEvidence(
        retrieval_id="bedrock-retrieve:req-123",
        request=request,
        chunks=(chunk,),
        backend=RetrievalBackend.BEDROCK_KNOWLEDGE_BASE,
        backend_reference="BTVJ2PBR2A",
    )
    invocation = BedrockRetrieveInvocationEvidence(
        knowledge_base_id="BTVJ2PBR2A",
        provider_request_id="req-123",
        retry_attempts=0,
        client_elapsed_ms=321,
        returned_result_count=1,
    )
    return BedrockRetrieveResult(evidence=evidence, invocation=invocation)


def test_serializer_emits_ranked_provenance_and_telemetry_without_chunk_text() -> None:
    """Operational evidence remains useful without copying retrieved source content to logs."""
    serialized = serialize_retrieve_evidence(_result(), region="us-east-1")
    payload = cast(dict[str, object], json.loads(serialized))
    chunks = cast(list[dict[str, object]], payload["chunks"])

    assert _TEXT not in serialized
    assert payload["knowledge_base_id"] == "BTVJ2PBR2A"
    assert payload["provider_request_id"] == "req-123"
    assert payload["requested_top_k"] == 1
    assert payload["returned_result_count"] == 1
    assert payload["query_sha256"] == sha256(
        b"How should I remediate this dependency?"
    ).hexdigest()
    assert chunks[0]["chunk_id"] == "knowledge-chunk:test:remediation:v1"
    assert chunks[0]["rank"] == 1
    assert chunks[0]["relevance_score"] == 0.89


def test_retrieve_region_is_frozen_to_us_east_1() -> None:
    """CLI callers cannot silently redirect the frozen dev Knowledge Base runtime."""
    assert require_retrieve_region("us-east-1") == "us-east-1"

    with pytest.raises(RetrieveCliError, match="us-east-1"):
        require_retrieve_region("us-west-2")


def test_invalid_top_k_fails_before_runtime_client_creation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The Gate 7.1 product bound rejects provider breadth before any AWS client is needed."""
    exit_code = main(
        [
            "--query",
            "How should I remediate this?",
            "--top-k",
            "11",
            "--knowledge-base-id",
            "BTVJ2PBR2A",
            "--data-source-id",
            "IEL1LBE026",
            "--source-bucket",
            "opslens-dev-data-487757851499-us-east-1",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "top_k" in captured.err
    assert captured.out == ""
