"""Run the bounded ten-case Gate 7.5 retrieval evaluation against Bedrock."""

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
from opslens.knowledge_retrieval.application.retrieval_evaluation import (
    GoldenRetrievalCase,
    RetrievalCaseObservation,
    RetrievalEvaluationError,
    load_golden_retrieval_dataset,
)
from opslens.knowledge_retrieval.application.retrieval_evaluation_runner import (
    RetrievalEvaluationExecution,
    run_retrieval_evaluation,
)
from opslens.knowledge_retrieval.domain import KnowledgeRetrievalValidationError

_REQUIRED_REGION = "us-east-1"
_DEFAULT_MANIFEST = Path("knowledge/corpus/v1/manifest.json")
_DEFAULT_FIXTURE = Path("tests/fixtures/knowledge_retrieval/golden_retrieval_v1.json")


class RetrievalEvaluationCliError(ValueError):
    """Raised when CLI inputs do not authorize the frozen Gate 7.5 evaluation."""


def _parser() -> argparse.ArgumentParser:
    """Build the explicit full-fixture evaluation CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Run exactly one top-k=10 direct Retrieve attempt for each frozen Gate 7.5 "
            "fixture case and emit content-free quality/latency evidence."
        )
    )
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--data-source-id", required=True)
    parser.add_argument("--source-bucket", required=True)
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument("--fixture", type=Path, default=_DEFAULT_FIXTURE)
    parser.add_argument("--region", default=_REQUIRED_REGION)
    return parser


def require_evaluation_region(value: object) -> str:
    """Require the frozen Phase 7 dev region."""
    if not isinstance(value, str) or value != _REQUIRED_REGION:
        raise RetrievalEvaluationCliError(
            f"region must equal the frozen Phase 7 region {_REQUIRED_REGION!r}"
        )
    return value


def _first_relevant_rank(
    case: GoldenRetrievalCase,
    observation: RetrievalCaseObservation,
) -> int | None:
    """Return the first frozen relevant chunk rank for content-free case reporting."""
    for rank, chunk in enumerate(observation.returned_chunks, start=1):
        if chunk.chunk_id in case.relevant_chunk_ids:
            return rank
    return None


def _case_payload(
    case: GoldenRetrievalCase,
    observation: RetrievalCaseObservation,
) -> dict[str, object]:
    """Serialize one case without raw question or retrieved source text."""
    payload: dict[str, object] = {
        "case_id": case.case_id,
        "client_elapsed_ms": observation.client_elapsed_ms,
        "failure_category": observation.failure_category,
        "provider_request_id": observation.provider_request_id or None,
        "question_sha256": sha256(case.question.encode("utf-8")).hexdigest(),
        "relevant_chunk_ids": list(case.relevant_chunk_ids),
        "retry_attempts": observation.retry_attempts,
        "returned_chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "rank": rank,
                "relevance_score": chunk.relevance_score,
                "source_type": chunk.source_type,
            }
            for rank, chunk in enumerate(observation.returned_chunks, start=1)
        ],
        "returned_result_count": len(observation.returned_chunks),
        "should_have_relevant_evidence": case.should_have_relevant_evidence,
    }
    if case.should_have_relevant_evidence:
        first_rank = _first_relevant_rank(case, observation)
        payload["first_relevant_rank"] = first_rank
        payload["reciprocal_rank"] = 0.0 if first_rank is None else 1.0 / first_rank
        payload["recall_hits"] = {
            "1": first_rank is not None and first_rank <= 1,
            "3": first_rank is not None and first_rank <= 3,
            "5": first_rank is not None and first_rank <= 5,
            "10": first_rank is not None and first_rank <= 10,
        }
    else:
        scores = tuple(
            chunk.relevance_score
            for chunk in observation.returned_chunks
            if chunk.relevance_score is not None
        )
        payload["negative_evidence"] = {
            "max_score": max(scores) if scores else None,
            "min_score": min(scores) if scores else None,
            "rank1_chunk_id": (
                observation.returned_chunks[0].chunk_id
                if observation.returned_chunks
                else None
            ),
            "rank1_score": (
                observation.returned_chunks[0].relevance_score
                if observation.returned_chunks
                else None
            ),
        }
    return payload


def serialize_evaluation_execution(
    execution: RetrievalEvaluationExecution,
    *,
    dataset_cases: tuple[GoldenRetrievalCase, ...],
    knowledge_base_id: str,
    region: str,
) -> str:
    """Serialize deterministic content-free Gate 7.5 execution evidence."""
    if len(execution.observations) != len(dataset_cases):
        raise RetrievalEvaluationCliError(
            "execution observation count must equal frozen dataset case count"
        )
    cases = [
        _case_payload(case, observation)
        for case, observation in zip(dataset_cases, execution.observations, strict=True)
    ]
    summary = execution.summary
    summary_payload: dict[str, object] | None = None
    if summary is not None:
        summary_payload = {
            "case_count": summary.case_count,
            "latency": {
                "max_ms": summary.latency_max_ms,
                "mean_ms": summary.latency_mean_ms,
                "min_ms": summary.latency_min_ms,
                "p50_ms": summary.latency_p50_ms,
                "p95_ms": summary.latency_p95_ms,
            },
            "mean_reciprocal_rank": summary.mean_reciprocal_rank,
            "negative_case_count": summary.negative_case_count,
            "negative_nonempty_retrieval_rate": summary.negative_nonempty_retrieval_rate,
            "negative_rank1_scores": list(summary.negative_rank1_scores),
            "positive_case_count": summary.positive_case_count,
            "provenance": {
                "correct_count": summary.relevant_hit_provenance_correct_count,
                "correct_rate": summary.relevant_hit_provenance_correct_rate,
                "relevant_hit_count": summary.relevant_hit_count,
            },
            "recall": {
                "1": summary.recall_at_1,
                "3": summary.recall_at_3,
                "5": summary.recall_at_5,
                "10": summary.recall_at_10,
            },
            "total_retry_attempts": summary.total_retry_attempts,
        }
    return json.dumps(
        {
            "cases": cases,
            "complete": execution.complete,
            "dataset_id": "knowledge-retrieval-golden:v1",
            "knowledge_base_id": knowledge_base_id,
            "planned_top_k": 10,
            "real_attempt_count": len(execution.observations),
            "region": region,
            "summary": summary_payload,
        },
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Run one bounded ten-case real retrieval evaluation and emit evidence once."""
    args = _parser().parse_args(argv)
    knowledge_base_id = cast(str, args.knowledge_base_id)
    data_source_id = cast(str, args.data_source_id)
    source_bucket = cast(str, args.source_bucket)
    manifest_path = cast(Path, args.manifest)
    fixture_path = cast(Path, args.fixture)

    try:
        region = require_evaluation_region(args.region)
        dataset = load_golden_retrieval_dataset(fixture_path)
        catalog = build_retrieval_catalog(load_corpus_manifest(manifest_path))
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
        adapter = BedrockKnowledgeBaseRetrieveAdapter(client)

        def retrieve(request):
            return run_bounded_retrieve(
                adapter,
                request=request,
                catalog=catalog,
                knowledge_base_id=knowledge_base_id,
                expected_source_bucket=source_bucket,
                expected_data_source_id=data_source_id,
            )

        execution = run_retrieval_evaluation(
            retrieve,
            dataset=dataset,
            catalog=catalog,
        )
        serialized = serialize_evaluation_execution(
            execution,
            dataset_cases=dataset.cases,
            knowledge_base_id=knowledge_base_id,
            region=region,
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
        RetrievalEvaluationCliError,
        RetrievalEvaluationError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(serialized, end="")
    return 0 if execution.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
