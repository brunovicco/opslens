"""Run the frozen Gate 7.7 grounded citation evaluation against Bedrock once."""

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

from opslens.knowledge_retrieval.adapters.bedrock_grounded_synthesis import (
    BedrockGroundedKnowledgeSynthesizer,
)
from opslens.knowledge_retrieval.adapters.bedrock_retrieval import (
    BedrockAgentRuntimeClient,
    BedrockKnowledgeBaseRetrieveAdapter,
)
from opslens.knowledge_retrieval.adapters.bedrock_synthesis import (
    BedrockConverseClient,
)
from opslens.knowledge_retrieval.application.bedrock_retrieval import (
    BedrockRetrieveResult,
    run_bounded_retrieve,
)
from opslens.knowledge_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MODEL_ID,
    BEDROCK_SYNTHESIS_REGION,
)
from opslens.knowledge_retrieval.application.corpus_config import (
    CorpusConfigError,
    load_corpus_manifest,
)
from opslens.knowledge_retrieval.application.grounding_evaluation import (
    GroundingEvaluationError,
    load_golden_grounding_dataset,
)
from opslens.knowledge_retrieval.application.grounding_runtime_runner import (
    GroundingRuntimeCaseExecution,
    GroundingRuntimeExecution,
    run_grounding_runtime_evaluation,
)
from opslens.knowledge_retrieval.application.retrieval_catalog import (
    RetrievalCatalogError,
    build_retrieval_catalog,
)
from opslens.knowledge_retrieval.domain import (
    DEFAULT_RETRIEVAL_TOP_K,
    KnowledgeRetrievalValidationError,
    RetrievalRequest,
)

_REQUIRED_REGION = BEDROCK_SYNTHESIS_REGION
_DEFAULT_MANIFEST = Path("knowledge/corpus/v1/manifest.json")
_DEFAULT_FIXTURE = Path(
    "tests/fixtures/knowledge_retrieval/golden_grounding_v1.json"
)


class GroundingRuntimeCliError(ValueError):
    """Raised when CLI input violates the frozen Gate 7.7 runtime contract."""


def _parser() -> argparse.ArgumentParser:
    """Build the explicit full-fixture one-attempt Gate 7.7 runtime CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Run each frozen Gate 7.7 grounding case at most once using one direct "
            "Retrieve followed by one grounded non-streaming Converse invocation. "
            "Stop after the first failed application attempt and preserve partial evidence."
        )
    )
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--data-source-id", required=True)
    parser.add_argument("--source-bucket", required=True)
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument("--fixture", type=Path, default=_DEFAULT_FIXTURE)
    parser.add_argument("--region", default=_REQUIRED_REGION)
    return parser


def require_grounding_region(value: object) -> str:
    """Require the single frozen Phase 7 source Region."""
    if not isinstance(value, str) or value != _REQUIRED_REGION:
        raise GroundingRuntimeCliError(
            f"region must equal the frozen Phase 7 region {_REQUIRED_REGION!r}"
        )
    return value


def _retrieval_payload(attempt: GroundingRuntimeCaseExecution) -> dict[str, object] | None:
    """Serialize admitted retrieval metadata without source bodies."""
    retrieval = attempt.retrieval
    if retrieval is None:
        return None
    return {
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
        "provider_request_id": retrieval.invocation.provider_request_id,
        "requested_top_k": retrieval.evidence.request.top_k,
        "retrieval_id": retrieval.evidence.retrieval_id,
        "retry_attempts": retrieval.invocation.retry_attempts,
        "returned_result_count": retrieval.invocation.returned_result_count,
    }


def _context_payload(attempt: GroundingRuntimeCaseExecution) -> dict[str, object] | None:
    """Serialize bounded context and deterministic citation projection metadata."""
    context = attempt.context
    catalog = attempt.citation_catalog
    if context is None or catalog is None:
        return None
    return {
        "catalog_sha256": catalog.catalog_sha256,
        "citations": [
            {
                "canonical_uri": item.citation.canonical_uri,
                "chunk_content_sha256": item.chunk_content_sha256,
                "chunk_id": item.citation.chunk_id,
                "citation_id": item.citation.citation_id,
                "citation_sha256": item.citation_sha256,
                "document_id": item.citation.document_id,
                "rank": item.retrieval_rank,
                "source_id": item.citation.source_id,
            }
            for item in catalog.citations
        ],
        "context_sha256": context.context_sha256,
        "selected_chunk_count": len(context.blocks),
        "selected_utf8_bytes": context.total_utf8_bytes,
        "stop_reason": context.stop_reason.value,
    }


def _synthesis_payload(attempt: GroundingRuntimeCaseExecution) -> dict[str, object] | None:
    """Serialize claim text plus content-free grounded provider evidence."""
    synthesis = attempt.synthesis
    if synthesis is None:
        return None
    return {
        "bedrock_latency_ms": synthesis.evidence.bedrock_latency_ms,
        "cache_read_input_tokens": synthesis.evidence.cache_read_input_tokens,
        "cache_write_input_tokens": synthesis.evidence.cache_write_input_tokens,
        "citation_catalog_sha256": synthesis.evidence.citation_catalog_sha256,
        "claims": [
            {
                "citation_ids": list(claim.citation_ids),
                "claim_index": claim.claim_index,
                "claim_sha256": claim.claim_sha256,
                "text": claim.text,
            }
            for claim in synthesis.result.claims
        ],
        "client_elapsed_ms": synthesis.evidence.client_elapsed_ms,
        "decision": synthesis.result.decision.value,
        "grounded_request_sha256": synthesis.evidence.grounded_request_sha256,
        "input_tokens": synthesis.evidence.input_tokens,
        "model_id": synthesis.evidence.model_id,
        "output_tokens": synthesis.evidence.output_tokens,
        "prompt_sha256": synthesis.evidence.prompt_sha256,
        "provider_request_id": synthesis.evidence.request_id,
        "rendered_answer": synthesis.result.rendered_answer,
        "result_sha256": synthesis.result.result_sha256,
        "retry_attempts": synthesis.evidence.retry_attempts,
        "stop_reason": synthesis.evidence.stop_reason,
        "total_tokens": synthesis.evidence.total_tokens,
    }


def _attempt_payload(attempt: GroundingRuntimeCaseExecution) -> dict[str, object]:
    """Serialize one attempted case without raw retrieval source text."""
    case = attempt.case
    return {
        "application_complete": attempt.complete,
        "case_id": case.case_id,
        "context": _context_payload(attempt),
        "expected_citation_chunk_ids": list(case.expected_citation_chunk_ids),
        "expected_decision": case.expected_decision.value,
        "failure_category": attempt.failure_category,
        "question_sha256": sha256(case.question.encode("utf-8")).hexdigest(),
        "retrieval": _retrieval_payload(attempt),
        "synthesis": _synthesis_payload(attempt),
    }


def serialize_grounding_runtime_execution(
    execution: GroundingRuntimeExecution,
    *,
    knowledge_base_id: str,
    region: str,
) -> str:
    """Serialize first-run evidence before any semantic support judgment is added."""
    return json.dumps(
        {
            "application_case_attempt_count": len(execution.attempts),
            "complete": execution.complete,
            "dataset_id": execution.dataset_id,
            "knowledge_base_id": knowledge_base_id,
            "model_id": BEDROCK_SYNTHESIS_MODEL_ID,
            "planned_case_count": execution.planned_case_count,
            "planned_top_k": DEFAULT_RETRIEVAL_TOP_K,
            "region": region,
            "semantic_judgments_collected": False,
            "cases": [_attempt_payload(attempt) for attempt in execution.attempts],
        },
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"


def _retrieval_config() -> Config:
    """Return bounded transport settings for each direct Retrieve attempt."""
    return Config(
        connect_timeout=5,
        read_timeout=30,
        retries={"max_attempts": 3, "mode": "standard"},
    )


def _synthesis_config() -> Config:
    """Allow bounded structured-output compilation latency without model iteration."""
    return Config(
        connect_timeout=5,
        read_timeout=90,
        retries={"max_attempts": 3, "mode": "standard"},
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the frozen four-case Gate 7.7 real path once and preserve first evidence."""
    args = _parser().parse_args(argv)
    knowledge_base_id = cast(str, args.knowledge_base_id)
    data_source_id = cast(str, args.data_source_id)
    source_bucket = cast(str, args.source_bucket)
    manifest_path = cast(Path, args.manifest)
    fixture_path = cast(Path, args.fixture)

    try:
        region = require_grounding_region(args.region)
        dataset = load_golden_grounding_dataset(fixture_path)
        catalog = build_retrieval_catalog(load_corpus_manifest(manifest_path))

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
        retrieval_client = cast(
            BedrockAgentRuntimeClient,
            dynamic_retrieval_client,
        )
        synthesis_client = cast(BedrockConverseClient, dynamic_synthesis_client)
        retrieval_adapter = BedrockKnowledgeBaseRetrieveAdapter(retrieval_client)
        synthesis_adapter = BedrockGroundedKnowledgeSynthesizer(synthesis_client)

        def retrieve(request: RetrievalRequest) -> BedrockRetrieveResult:
            """Run one already-bounded direct Retrieve request for one frozen case."""
            return run_bounded_retrieve(
                retrieval_adapter,
                request=request,
                catalog=catalog,
                knowledge_base_id=knowledge_base_id,
                expected_source_bucket=source_bucket,
                expected_data_source_id=data_source_id,
            )

        execution = run_grounding_runtime_evaluation(
            retrieve,
            synthesis_adapter.synthesize,
            dataset=dataset,
            catalog=catalog,
        )
        serialized = serialize_grounding_runtime_execution(
            execution,
            knowledge_base_id=knowledge_base_id,
            region=region,
        )
    except (
        BotoCoreError,
        ClientError,
        CorpusConfigError,
        GroundingEvaluationError,
        GroundingRuntimeCliError,
        KnowledgeRetrievalValidationError,
        OSError,
        RetrievalCatalogError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(serialized, end="")
    return 0 if execution.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
