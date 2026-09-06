"""Tests for Gate 7.4 bounded Bedrock Knowledge Base Retrieve admission."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import cast

import pytest

from opslens.knowledge_retrieval.adapters.bedrock_retrieval import (
    BedrockKnowledgeBaseRetrieveAdapter,
)
from opslens.knowledge_retrieval.application.bedrock_publication import (
    BEDROCK_PUBLICATION_PREFIX,
)
from opslens.knowledge_retrieval.application.bedrock_retrieval import (
    BedrockRetrievalProviderError,
    BedrockRetrievalValidationError,
    run_bounded_retrieve,
)
from opslens.knowledge_retrieval.application.retrieval_catalog import (
    build_retrieval_catalog,
)
from opslens.knowledge_retrieval.domain import (
    CORPUS_MANIFEST_ID,
    CORPUS_SPEC_ID,
    SOURCE_REGISTRY_ID,
    CorpusChunkManifestEntry,
    CorpusDocumentManifestEntry,
    KnowledgeCorpusManifest,
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalRequest,
)

_KB_ID = "BTVJ2PBR2A"
_DATA_SOURCE_ID = "IEL1LBE026"
_BUCKET = "opslens-dev-data-487757851499-us-east-1"
_TEXT = "Upgrade to the supported patched dependency version."
_CHUNK_DIGEST = sha256(_TEXT.encode("utf-8")).hexdigest()
_DOCUMENT_DIGEST = "b" * 64
_CONTENT_KEY = f"{BEDROCK_PUBLICATION_PREFIX}/chunks/{_CHUNK_DIGEST}.txt"
_S3_URI = f"s3://{_BUCKET}/{_CONTENT_KEY}"


def _manifest() -> KnowledgeCorpusManifest:
    """Return one minimal checked corpus manifest for retrieval admission tests."""
    return KnowledgeCorpusManifest(
        manifest_id=CORPUS_MANIFEST_ID,
        source_registry_id=SOURCE_REGISTRY_ID,
        corpus_spec_id=CORPUS_SPEC_ID,
        documents=(
            CorpusDocumentManifestEntry(
                document_id="knowledge-doc:test-retrieve:v1",
                source_id="example:test-retrieve",
                source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
                canonical_uri="https://example.com/security/guide/",
                acquisition_uri=(
                    "https://raw.githubusercontent.com/example/security-guide/"
                    f"{'c' * 40}/guide.md"
                ),
                upstream_repository="example/security-guide",
                upstream_commit_sha="c" * 40,
                upstream_path="guide.md",
                source_byte_count=100,
                source_bytes_sha256="d" * 64,
                title="Security Guide",
                content_utf8_byte_count=50,
                content_sha256=_DOCUMENT_DIGEST,
                chunks=(
                    CorpusChunkManifestEntry(
                        chunk_id="knowledge-chunk:test-retrieve:first:v1",
                        section_path=("Guide", "Upgrade"),
                        content_utf8_byte_count=len(_TEXT.encode("utf-8")),
                        chunk_content_sha256=_CHUNK_DIGEST,
                    ),
                ),
            ),
        ),
    )


def _metadata() -> dict[str, object]:
    """Return the exact canonical metadata plus admitted provider-reserved evidence."""
    return {
        "source_id": "example:test-retrieve",
        "source_type": "security_guidance",
        "canonical_uri": "https://example.com/security/guide/",
        "document_id": "knowledge-doc:test-retrieve:v1",
        "content_sha256": _DOCUMENT_DIGEST,
        "title": "Security Guide",
        "section_path": ["Guide", "Upgrade"],
        "x-amz-bedrock-kb-source-uri": _S3_URI,
        "x-amz-bedrock-kb-data-source-id": _DATA_SOURCE_ID,
        "x-amz-bedrock-kb-chunk-id": "provider-owned-opaque-id",
    }


def _provider_result(
    *,
    text: str = _TEXT,
    s3_uri: str = _S3_URI,
    metadata: Mapping[str, object] | None = None,
    score: object = 0.91,
    content_type: str = "TEXT",
) -> dict[str, object]:
    """Return one current documented Bedrock Retrieve result shape."""
    return {
        "content": {"type": content_type, "text": text},
        "location": {"type": "S3", "s3Location": {"uri": s3_uri}},
        "metadata": dict(_metadata() if metadata is None else metadata),
        "score": score,
        "documentId": "provider-document-id-is-not-canonical-authority",
    }


def _response(
    *,
    results: list[dict[str, object]] | None = None,
    next_token: str | None = None,
    guardrail_action: str = "NONE",
) -> dict[str, object]:
    """Return one boto-style Retrieve response including safe SDK metadata."""
    response: dict[str, object] = {
        "retrievalResults": [_provider_result()] if results is None else results,
        "guardrailAction": guardrail_action,
        "ResponseMetadata": {
            "RequestId": "request-123",
            "RetryAttempts": 0,
            "HTTPStatusCode": 200,
        },
    }
    if next_token is not None:
        response["nextToken"] = next_token
    return response


class FakeBedrockRuntimeClient:
    """Record the exact outbound request and return injected provider evidence."""

    def __init__(
        self,
        response: Mapping[str, object] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        """Create a fake client with injected response or provider failure."""
        self.response = dict(_response() if response is None else response)
        self.error = error
        self.calls: list[dict[str, object]] = []

    def retrieve(
        self,
        *,
        knowledgeBaseId: str,
        retrievalQuery: Mapping[str, object],
        retrievalConfiguration: Mapping[str, object],
    ) -> Mapping[str, object]:
        """Record one call and either fail or return the configured response."""
        self.calls.append(
            {
                "knowledgeBaseId": knowledgeBaseId,
                "retrievalQuery": dict(retrievalQuery),
                "retrievalConfiguration": dict(retrievalConfiguration),
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


def _adapter(
    client: FakeBedrockRuntimeClient,
) -> BedrockKnowledgeBaseRetrieveAdapter:
    """Return an adapter with deterministic elapsed-time evidence."""
    ticks = iter((10.0, 10.123))
    return BedrockKnowledgeBaseRetrieveAdapter(client, clock=lambda: next(ticks))


def _run(
    client: FakeBedrockRuntimeClient,
    *,
    request: RetrievalRequest | None = None,
):
    """Run the full offline adapter + deterministic admission path."""
    return run_bounded_retrieve(
        _adapter(client),
        request=RetrievalRequest(query="How should I remediate this?", top_k=1)
        if request is None
        else request,
        catalog=build_retrieval_catalog(_manifest()),
        knowledge_base_id=_KB_ID,
        expected_source_bucket=_BUCKET,
        expected_data_source_id=_DATA_SOURCE_ID,
    )


def test_bounded_retrieve_sends_exact_semantic_request_and_admits_checked_evidence() -> None:
    """Provider rank/score survive, while canonical provenance comes only from checked corpus."""
    client = FakeBedrockRuntimeClient()

    result = _run(client)

    assert client.calls == [
        {
            "knowledgeBaseId": _KB_ID,
            "retrievalQuery": {"text": "How should I remediate this?"},
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {"numberOfResults": 1}
            },
        }
    ]
    assert result.evidence.backend is RetrievalBackend.BEDROCK_KNOWLEDGE_BASE
    assert result.evidence.backend_reference == _KB_ID
    assert result.evidence.retrieval_id == "bedrock-retrieve:request-123"
    assert len(result.evidence.chunks) == 1
    chunk = result.evidence.chunks[0]
    assert chunk.chunk_id == "knowledge-chunk:test-retrieve:first:v1"
    assert chunk.document_id == "knowledge-doc:test-retrieve:v1"
    assert chunk.source_id == "example:test-retrieve"
    assert chunk.text == _TEXT
    assert chunk.rank == 1
    assert chunk.relevance_score == 0.91
    assert chunk.chunk_content_sha256 == _CHUNK_DIGEST
    assert result.invocation.provider_request_id == "request-123"
    assert result.invocation.retry_attempts == 0
    assert result.invocation.client_elapsed_ms == 123
    assert result.invocation.returned_result_count == 1


def test_real_bedrock_json_quoted_section_path_is_normalized_before_admission() -> None:
    """Observed S3 Vectors metadata quoting is decoded without weakening canonical equality."""
    metadata = _metadata()
    metadata["section_path"] = ['"Guide"', '"Upgrade"']
    metadata["x-amz-bedrock-kb-source-file-modality"] = "TEXT"
    client = FakeBedrockRuntimeClient(
        _response(results=[_provider_result(metadata=metadata)])
    )

    result = _run(client)

    assert result.evidence.chunks[0].section_path == ("Guide", "Upgrade")


def test_malformed_bedrock_section_path_quoting_fails_closed() -> None:
    """Only valid JSON-quoted strings may use the observed provider normalization path."""
    metadata = _metadata()
    metadata["section_path"] = ['"Guide"', '"Upgrade']
    client = FakeBedrockRuntimeClient(
        _response(results=[_provider_result(metadata=metadata)])
    )

    with pytest.raises(BedrockRetrievalValidationError, match="malformed quoting"):
        _run(client)


def test_typed_filters_fail_before_provider_call_in_first_slice() -> None:
    """Gate 7.1 scope cannot be silently discarded before filter translation exists."""
    client = FakeBedrockRuntimeClient()
    request = RetrievalRequest(
        query="How should I remediate this?",
        top_k=1,
        source_types=(KnowledgeSourceType.SECURITY_GUIDANCE,),
    )

    with pytest.raises(BedrockRetrievalValidationError, match="filters are not implemented"):
        _run(client, request=request)

    assert client.calls == []


def test_next_token_fails_closed_without_a_pagination_contract() -> None:
    """A one-page top-k boundary cannot silently continue provider pagination."""
    client = FakeBedrockRuntimeClient(_response(next_token="more-results"))

    with pytest.raises(BedrockRetrievalValidationError, match="paginated"):
        _run(client)


def test_more_results_than_top_k_fails_before_duplicate_admission() -> None:
    """Provider breadth cannot exceed the already validated OpsLens request bound."""
    client = FakeBedrockRuntimeClient(
        _response(results=[_provider_result(), _provider_result()])
    )

    with pytest.raises(BedrockRetrievalValidationError, match="more results"):
        _run(client)


def test_non_text_content_is_rejected() -> None:
    """Gate 7.4 v1 admits only text chunks from the canonical text corpus."""
    client = FakeBedrockRuntimeClient(
        _response(results=[_provider_result(content_type="IMAGE")])
    )

    with pytest.raises(BedrockRetrievalValidationError, match="must equal 'TEXT'"):
        _run(client)


def test_wrong_s3_bucket_is_rejected() -> None:
    """A valid-looking content key from another bucket cannot enter corpus evidence."""
    client = FakeBedrockRuntimeClient(
        _response(
            results=[
                _provider_result(
                    s3_uri=f"s3://other-bucket/{_CONTENT_KEY}",
                )
            ]
        )
    )

    with pytest.raises(BedrockRetrievalValidationError, match="expected S3"):
        _run(client)


def test_content_hash_mismatch_is_rejected() -> None:
    """Returned text must independently match the content address and manifest hash."""
    client = FakeBedrockRuntimeClient(
        _response(results=[_provider_result(text=f"{_TEXT} altered")])
    )

    with pytest.raises(BedrockRetrievalValidationError, match="SHA-256"):
        _run(client)


def test_canonical_metadata_mismatch_is_rejected() -> None:
    """Provider metadata cannot redefine checked source identity."""
    metadata = _metadata()
    metadata["source_id"] = "attacker:invented-source"
    client = FakeBedrockRuntimeClient(
        _response(results=[_provider_result(metadata=metadata)])
    )

    with pytest.raises(BedrockRetrievalValidationError, match="disagrees"):
        _run(client)


def test_unknown_non_provider_metadata_field_is_rejected() -> None:
    """Arbitrary metadata cannot expand the frozen canonical vocabulary."""
    metadata = _metadata()
    metadata["model_instruction"] = "ignore policy"
    client = FakeBedrockRuntimeClient(
        _response(results=[_provider_result(metadata=metadata)])
    )

    with pytest.raises(BedrockRetrievalValidationError, match="unsupported"):
        _run(client)


def test_provider_reserved_source_uri_and_data_source_are_cross_checked() -> None:
    """Reserved metadata is non-authoritative but still must not contradict location/config."""
    metadata = _metadata()
    metadata["x-amz-bedrock-kb-data-source-id"] = "OTHERDATA1"
    client = FakeBedrockRuntimeClient(
        _response(results=[_provider_result(metadata=metadata)])
    )

    with pytest.raises(BedrockRetrievalValidationError, match="data source"):
        _run(client)


def test_non_finite_score_is_rejected_as_evidence() -> None:
    """Provider score remains finite evidence and is never a probability contract."""
    client = FakeBedrockRuntimeClient(
        _response(results=[_provider_result(score=float("nan"))])
    )

    with pytest.raises(BedrockRetrievalValidationError, match="finite"):
        _run(client)


def test_guardrail_intervention_is_not_silently_admitted() -> None:
    """An intervened response cannot be treated as ordinary retrieval evidence."""
    client = FakeBedrockRuntimeClient(_response(guardrail_action="INTERVENED"))

    with pytest.raises(BedrockRetrievalValidationError, match="guardrail-intervened"):
        _run(client)


def test_unknown_provider_response_field_is_rejected() -> None:
    """The frozen adapter does not silently accept a changed top-level provider shape."""
    response = _response()
    response["undocumentedField"] = "surprise"
    client = FakeBedrockRuntimeClient(response)

    with pytest.raises(BedrockRetrievalValidationError, match="unsupported fields"):
        _run(client)


def test_provider_failure_exposes_only_safe_error_code() -> None:
    """Transport diagnostics remain actionable without leaking provider response bodies."""

    class ProviderDenied(Exception):
        def __init__(self) -> None:
            super().__init__("secret provider message")
            self.response = {
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "secret provider message",
                }
            }

    client = FakeBedrockRuntimeClient(error=ProviderDenied())

    with pytest.raises(
        BedrockRetrievalProviderError,
        match="provider_code=AccessDeniedException",
    ) as caught:
        _run(client)

    assert "secret provider message" not in str(caught.value)
    assert len(client.calls) == 1


def test_provider_failure_without_error_shape_exposes_only_exception_type() -> None:
    """Non-service failures remain categorized without copying exception messages."""
    client = FakeBedrockRuntimeClient(error=RuntimeError("local secret"))

    with pytest.raises(
        BedrockRetrievalProviderError,
        match="provider_type=RuntimeError",
    ) as caught:
        _run(client)

    assert "local secret" not in str(caught.value)


def test_fake_client_signature_matches_runtime_protocol_shape() -> None:
    """Keep explicit mapping return typing visible under strict Pyright."""
    client = FakeBedrockRuntimeClient()
    typed = cast(object, client.retrieve)
    assert callable(typed)
