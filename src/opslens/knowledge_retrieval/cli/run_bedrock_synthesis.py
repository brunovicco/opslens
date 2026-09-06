"""Run one bounded real retrieval-to-Bedrock knowledge synthesis operation."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from typing import cast

from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from botocore.session import get_session

from opslens.knowledge_retrieval.adapters.bedrock_retrieval import (
    BedrockAgentRuntimeClient,
    BedrockKnowledgeBaseRetrieveAdapter,
)
from opslens.knowledge_retrieval.adapters.bedrock_synthesis import (
    BedrockConverseClient,
    BedrockKnowledgeSynthesizer,
    BedrockSynthesisExecution,
    BedrockSynthesisRuntimeError,
)
from opslens.knowledge_retrieval.application.bedrock_retrieval import (
    BedrockRetrievalProviderError,
    BedrockRetrievalValidationError,
    BedrockRetrieveResult,
    run_bounded_retrieve,
)
from opslens.knowledge_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MODEL_ID,
    BEDROCK_SYNTHESIS_REGION,
)
from opslens.knowledge_retrieval.application.context_assembly import (
    ContextAssemblyError,
    assemble_retrieval_context,
)
from opslens.knowledge_retrieval.application.corpus_config import (
    CorpusConfigError,
    load_corpus_manifest,
)
from opslens.knowledge_retrieval.application.retrieval_catalog import (
    RetrievalCatalogError,
    build_retrieval_catalog,
)
from opslens.knowledge_retrieval.application.synthesis_contract import (
    SynthesisAdmissionError,
    SynthesisOutputError,
    build_synthesis_request,
)
from opslens.knowledge_retrieval.domain import (
    DEFAULT_RETRIEVAL_TOP_K,
    AssembledContext,
    KnowledgeRetrievalValidationError,
    RetrievalRequest,
    SynthesisAuthorityDecision,
)

_REQUIRED_REGION = BEDROCK_SYNTHESIS_REGION
_DEFAULT_MANIFEST = Path("knowledge/corpus/v1/manifest.json")


class SynthesisCliError(ValueError):
    """Raised when CLI inputs violate the frozen Gate 7.6 runtime contract."""


def _parser() -> argparse.ArgumentParser:
    """Build the explicit one-retrieval/one-synthesis lab runtime contract."""
    parser = argparse.ArgumentParser(
        description=(
            "Run at most one bounded Bedrock Knowledge Base Retrieve call followed by "
            "at most one non-streaming Bedrock Converse synthesis call. The authority "
            "decision is explicit operator/test-harness input for this lab entrypoint."
        )
    )
    parser.add_argument("--query", required=True)
    parser.add_argument(
        "--authority-decision",
        required=True,
        choices=tuple(item.value for item in SynthesisAuthorityDecision),
    )
    parser.add_argument("--top-k", type=int, default=DEFAULT_RETRIEVAL_TOP_K)
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--data-source-id", required=True)
    parser.add_argument("--source-bucket", required=True)
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument("--region", default=_REQUIRED_REGION)
    return parser


def require_synthesis_region(value: object) -> str:
    """Require the single frozen Gate 7.6 source Region."""
    if not isinstance(value, str) or value != _REQUIRED_REGION:
        raise SynthesisCliError(
            f"region must equal the frozen Gate 7.6 region {_REQUIRED_REGION!r}"
        )
    return value


def serialize_unsupported_authority(request: RetrievalRequest, *, region: str) -> str:
    """Serialize a valid pre-model refusal without creating an AWS client."""
    return json.dumps(
        {
            "authority_decision": SynthesisAuthorityDecision.UNSUPPORTED.value,
            "execution_complete": True,
            "model_invoked": False,
            "query_sha256": sha256(request.query.encode("utf-8")).hexdigest(),
            "region": region,
            "retrieval_invoked": False,
            "status": "unsupported_authority",
        },
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"


def serialize_synthesis_evidence(
    retrieval: BedrockRetrieveResult,
    *,
    context: AssembledContext,
    execution: BedrockSynthesisExecution,
    region: str,
) -> str:
    """Serialize first-run quality plus content-addressed runtime/provenance evidence."""
    answer = execution.result.answer
    return json.dumps(
        {
            "authority_decision": SynthesisAuthorityDecision.SUPPORTED.value,
            "context": {
                "blocks": [
                    {
                        "canonical_uri": block.canonical_uri,
                        "chunk_content_sha256": block.chunk_content_sha256,
                        "chunk_id": block.chunk_id,
                        "document_id": block.document_id,
                        "rank": block.retrieval_rank,
                        "source_id": block.source_id,
                        "source_type": block.source_type.value,
                    }
                    for block in context.blocks
                ],
                "context_sha256": context.context_sha256,
                "retrieved_chunk_count": context.retrieved_chunk_count,
                "selected_chunk_count": len(context.blocks),
                "selected_utf8_bytes": context.total_utf8_bytes,
                "stop_reason": context.stop_reason.value,
            },
            "execution_complete": True,
            "model_invoked": True,
            "region": region,
            "retrieval": {
                "backend": retrieval.evidence.backend.value,
                "chunks": [
                    {
                        "canonical_uri": chunk.canonical_uri,
                        "chunk_content_sha256": chunk.chunk_content_sha256,
                        "chunk_id": chunk.chunk_id,
                        "document_id": chunk.document_id,
                        "rank": chunk.rank,
                        "relevance_score": chunk.relevance_score,
                        "source_id": chunk.source_id,
                        "source_type": chunk.source_type.value,
                    }
                    for chunk in retrieval.evidence.chunks
                ],
                "client_elapsed_ms": retrieval.invocation.client_elapsed_ms,
                "knowledge_base_id": retrieval.invocation.knowledge_base_id,
                "provider_request_id": retrieval.invocation.provider_request_id,
                "requested_top_k": retrieval.evidence.request.top_k,
                "retrieval_id": retrieval.evidence.retrieval_id,
                "retry_attempts": retrieval.invocation.retry_attempts,
                "returned_result_count": retrieval.invocation.returned_result_count,
            },
            "retrieval_invoked": True,
            "synthesis": {
                "answer": answer,
                "answer_char_count": 0 if answer is None else len(answer),
                "answer_sha256": execution.result.answer_sha256,
                "bedrock_latency_ms": execution.evidence.bedrock_latency_ms,
                "cache_read_input_tokens": execution.evidence.cache_read_input_tokens,
                "cache_write_input_tokens": execution.evidence.cache_write_input_tokens,
                "client_elapsed_ms": execution.evidence.client_elapsed_ms,
                "context_sha256": execution.evidence.context_sha256,
                "decision": execution.result.decision.value,
                "input_tokens": execution.evidence.input_tokens,
                "model_id": execution.evidence.model_id,
                "output_tokens": execution.evidence.output_tokens,
                "prompt_sha256": execution.evidence.prompt_sha256,
                "provider_request_id": execution.evidence.request_id,
                "request_sha256": execution.evidence.request_sha256,
                "result_sha256": execution.result.result_sha256,
                "retry_attempts": execution.evidence.retry_attempts,
                "stop_reason": execution.evidence.stop_reason,
                "total_tokens": execution.evidence.total_tokens,
            },
        },
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"


def _retrieval_config() -> Config:
    """Return bounded transport settings for the single real Retrieve call."""
    return Config(
        connect_timeout=5,
        read_timeout=30,
        retries={"max_attempts": 3, "mode": "standard"},
    )


def _synthesis_config() -> Config:
    """Allow bounded first-schema compilation latency without enabling iteration."""
    return Config(
        connect_timeout=5,
        read_timeout=90,
        retries={"max_attempts": 3, "mode": "standard"},
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Gate 7.6e lab path while preserving deterministic authority boundaries."""
    args = _parser().parse_args(argv)
    query = cast(str, args.query)
    top_k = cast(int, args.top_k)
    knowledge_base_id = cast(str, args.knowledge_base_id)
    data_source_id = cast(str, args.data_source_id)
    source_bucket = cast(str, args.source_bucket)
    manifest_path = cast(Path, args.manifest)

    try:
        region = require_synthesis_region(args.region)
        authority = SynthesisAuthorityDecision(cast(str, args.authority_decision))
        retrieval_request = RetrievalRequest(query=query, top_k=top_k)

        if authority is SynthesisAuthorityDecision.UNSUPPORTED:
            print(
                serialize_unsupported_authority(retrieval_request, region=region),
                end="",
            )
            return 0

        manifest = load_corpus_manifest(manifest_path)
        catalog = build_retrieval_catalog(manifest)
        session = get_session()
        dynamic_retrieval_client = session.create_client(
            "bedrock-agent-runtime",
            region_name=region,
            config=_retrieval_config(),
        )
        dynamic_synthesis_client = session.create_client(
            "bedrock-runtime",
            region_name=region,
            config=_synthesis_config(),
        )
        retrieval_client = cast(BedrockAgentRuntimeClient, dynamic_retrieval_client)
        synthesis_client = cast(BedrockConverseClient, dynamic_synthesis_client)

        retrieval = run_bounded_retrieve(
            BedrockKnowledgeBaseRetrieveAdapter(retrieval_client),
            request=retrieval_request,
            catalog=catalog,
            knowledge_base_id=knowledge_base_id,
            expected_source_bucket=source_bucket,
            expected_data_source_id=data_source_id,
        )
        context = assemble_retrieval_context(retrieval.evidence)
        synthesis_request = build_synthesis_request(
            question=retrieval_request.query,
            context=context,
            authority_decision=authority,
        )
        execution = BedrockKnowledgeSynthesizer(synthesis_client).synthesize(
            synthesis_request
        )
    except (
        BedrockRetrievalProviderError,
        BedrockRetrievalValidationError,
        BedrockSynthesisRuntimeError,
        BotoCoreError,
        ClientError,
        ContextAssemblyError,
        CorpusConfigError,
        KnowledgeRetrievalValidationError,
        OSError,
        RetrievalCatalogError,
        SynthesisAdmissionError,
        SynthesisCliError,
        SynthesisOutputError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if execution.evidence.model_id != BEDROCK_SYNTHESIS_MODEL_ID:
        print("ERROR: synthesis model identity drifted", file=sys.stderr)
        return 1

    print(
        serialize_synthesis_evidence(
            retrieval,
            context=context,
            execution=execution,
            region=region,
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
