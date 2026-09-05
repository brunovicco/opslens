"""Run one bounded real Bedrock Knowledge Base Retrieve operation."""

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
from opslens.knowledge_retrieval.application.bedrock_retrieval import (
    BedrockRetrievalProviderError,
    BedrockRetrievalValidationError,
    BedrockRetrieveResult,
    run_bounded_retrieve,
)
from opslens.knowledge_retrieval.application.corpus_config import (
    CorpusConfigError,
    load_corpus_manifest,
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

_REQUIRED_REGION = "us-east-1"
_DEFAULT_MANIFEST = Path("knowledge/corpus/v1/manifest.json")


class RetrieveCliError(ValueError):
    """Raised when CLI inputs do not authorize one bounded retrieval operation."""


def _parser() -> argparse.ArgumentParser:
    """Build the explicit retrieval-only runtime CLI contract."""
    parser = argparse.ArgumentParser(
        description=(
            "Run exactly one semantic-only Bedrock Knowledge Base Retrieve request, "
            "admit results against checked corpus evidence, and emit content-free "
            "runtime/provenance evidence."
        )
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=DEFAULT_RETRIEVAL_TOP_K)
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--data-source-id", required=True)
    parser.add_argument("--source-bucket", required=True)
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument("--region", default=_REQUIRED_REGION)
    return parser


def require_retrieve_region(value: object) -> str:
    """Require the single frozen Phase 7 dev retrieval region."""
    if not isinstance(value, str) or value != _REQUIRED_REGION:
        raise RetrieveCliError(
            f"region must equal the frozen Phase 7 region {_REQUIRED_REGION!r}"
        )
    return value


def serialize_retrieve_evidence(result: BedrockRetrieveResult, *, region: str) -> str:
    """Serialize retrieval telemetry/provenance deterministically without chunk text."""
    request = result.evidence.request
    return json.dumps(
        {
            "backend": result.evidence.backend.value,
            "chunks": [
                {
                    "canonical_uri": chunk.canonical_uri,
                    "chunk_content_sha256": chunk.chunk_content_sha256,
                    "chunk_id": chunk.chunk_id,
                    "document_content_sha256": chunk.document_content_sha256,
                    "document_id": chunk.document_id,
                    "rank": chunk.rank,
                    "relevance_score": chunk.relevance_score,
                    "section_path": list(chunk.section_path),
                    "source_id": chunk.source_id,
                    "source_type": chunk.source_type.value,
                    "title": chunk.title,
                }
                for chunk in result.evidence.chunks
            ],
            "client_elapsed_ms": result.invocation.client_elapsed_ms,
            "knowledge_base_id": result.invocation.knowledge_base_id,
            "provider_request_id": result.invocation.provider_request_id,
            "query_sha256": sha256(request.query.encode("utf-8")).hexdigest(),
            "region": region,
            "requested_top_k": request.top_k,
            "retrieval_id": result.evidence.retrieval_id,
            "retry_attempts": result.invocation.retry_attempts,
            "returned_result_count": result.invocation.returned_result_count,
        },
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Run one real direct Retrieve call with deterministic checked-corpus admission."""
    args = _parser().parse_args(argv)
    query = cast(str, args.query)
    top_k = cast(int, args.top_k)
    knowledge_base_id = cast(str, args.knowledge_base_id)
    data_source_id = cast(str, args.data_source_id)
    source_bucket = cast(str, args.source_bucket)
    manifest_path = cast(Path, args.manifest)

    try:
        region = require_retrieve_region(args.region)
        request = RetrievalRequest(query=query, top_k=top_k)
        manifest = load_corpus_manifest(manifest_path)
        catalog = build_retrieval_catalog(manifest)
        dynamic_client = get_session().create_client(
            "bedrock-agent-runtime",
            region_name=region,
            config=Config(
                connect_timeout=5,
                read_timeout=30,
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
        client = cast(BedrockAgentRuntimeClient, dynamic_client)
        result = run_bounded_retrieve(
            BedrockKnowledgeBaseRetrieveAdapter(client),
            request=request,
            catalog=catalog,
            knowledge_base_id=knowledge_base_id,
            expected_source_bucket=source_bucket,
            expected_data_source_id=data_source_id,
        )
    except (
        BedrockRetrievalProviderError,
        BedrockRetrievalValidationError,
        BotoCoreError,
        ClientError,
        CorpusConfigError,
        KnowledgeRetrievalValidationError,
        OSError,
        RetrievalCatalogError,
        RetrieveCliError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(serialize_retrieve_evidence(result, region=region), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
