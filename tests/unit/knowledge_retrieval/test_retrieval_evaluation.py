"""Tests for the deterministic Gate 7.5 retrieval evaluation core."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from opslens.knowledge_retrieval.application.corpus_config import load_corpus_manifest
from opslens.knowledge_retrieval.application.retrieval_catalog import (
    CanonicalRetrievalCatalog,
    CanonicalRetrievalChunk,
    build_retrieval_catalog,
)
from opslens.knowledge_retrieval.application.retrieval_evaluation import (
    RankedEvaluationChunk,
    RetrievalCaseObservation,
    RetrievalEvaluationError,
    RetrievalEvaluationIncompleteError,
    aggregate_retrieval_evaluation,
    load_golden_retrieval_dataset,
    validate_dataset_catalog,
)

_REPO_ROOT = Path(__file__).parents[3]
_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "knowledge_retrieval" / "golden_retrieval_v1.json"
_MANIFEST = _REPO_ROOT / "knowledge" / "corpus" / "v1" / "manifest.json"


def _catalog() -> CanonicalRetrievalCatalog:
    """Build the checked production catalog without external source replay."""
    return build_retrieval_catalog(load_corpus_manifest(_MANIFEST))


def _ranked(chunk: CanonicalRetrievalChunk, *, score: float) -> RankedEvaluationChunk:
    """Project one content-free canonical result into evaluation evidence."""
    return RankedEvaluationChunk(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        source_type=chunk.source_type.value,
        relevance_score=score,
    )


def _ordered_results_for_case(
    catalog: CanonicalRetrievalCatalog,
    *,
    relevant_chunk_ids: tuple[str, ...],
    first_relevant_rank: int | None,
) -> tuple[RankedEvaluationChunk, ...]:
    """Build one unique synthetic ranking with an optional first relevant hit."""
    relevant = tuple(chunk for chunk in catalog.chunks if chunk.chunk_id in relevant_chunk_ids)
    nonrelevant = tuple(
        chunk for chunk in catalog.chunks if chunk.chunk_id not in relevant_chunk_ids
    )
    if first_relevant_rank is None:
        selected = nonrelevant
    else:
        before = nonrelevant[: first_relevant_rank - 1]
        after = tuple(
            chunk for chunk in catalog.chunks if chunk not in before and chunk != relevant[0]
        )
        selected = (*before, relevant[0], *after)
    return tuple(
        _ranked(chunk, score=1.0 - (index * 0.05))
        for index, chunk in enumerate(selected, start=1)
    )


def _complete_observations() -> tuple[RetrievalCaseObservation, ...]:
    """Return ten deterministic observations with known aggregate metrics."""
    dataset = load_golden_retrieval_dataset(_FIXTURE)
    catalog = _catalog()
    positive_ranks: list[int | None] = [1, 1, 2, 3, 4, 5, 9, None]
    positive_index = 0
    observations: list[RetrievalCaseObservation] = []
    for index, case in enumerate(dataset.cases, start=1):
        if case.should_have_relevant_evidence:
            returned = _ordered_results_for_case(
                catalog,
                relevant_chunk_ids=case.relevant_chunk_ids,
                first_relevant_rank=positive_ranks[positive_index],
            )
            positive_index += 1
        else:
            returned = tuple(
                _ranked(chunk, score=0.5 - (rank * 0.01))
                for rank, chunk in enumerate(catalog.chunks, start=1)
            )
        observations.append(
            RetrievalCaseObservation(
                case_id=case.case_id,
                returned_chunks=returned,
                client_elapsed_ms=index * 100,
                provider_request_id=f"request-{index}",
                retry_attempts=1 if index == 10 else 0,
            )
        )
    return tuple(observations)


def test_checked_golden_fixture_loads_and_matches_canonical_catalog() -> None:
    """The frozen product fixture is valid against the actual nine-chunk corpus."""
    dataset = load_golden_retrieval_dataset(_FIXTURE)
    catalog = _catalog()

    validate_dataset_catalog(dataset, catalog)

    assert dataset.dataset_id == "knowledge-retrieval-golden:v1"
    assert len(dataset.cases) == 10
    assert sum(case.should_have_relevant_evidence for case in dataset.cases) == 8
    assert len(catalog.chunks) == 9


def test_aggregate_metrics_follow_frozen_recall_mrr_and_latency_definitions() -> None:
    """One ranking per case deterministically yields every required cutoff metric."""
    dataset = load_golden_retrieval_dataset(_FIXTURE)
    catalog = _catalog()

    summary = aggregate_retrieval_evaluation(
        dataset,
        catalog,
        _complete_observations(),
    )

    assert summary.case_count == 10
    assert summary.positive_case_count == 8
    assert summary.negative_case_count == 2
    assert summary.recall_at_1 == pytest.approx(0.25)
    assert summary.recall_at_3 == pytest.approx(0.5)
    assert summary.recall_at_5 == pytest.approx(0.75)
    assert summary.recall_at_10 == pytest.approx(0.875)
    assert summary.mean_reciprocal_rank == pytest.approx(0.42430555555555555)
    assert summary.relevant_hit_provenance_correct_rate == pytest.approx(1.0)
    assert summary.negative_nonempty_retrieval_rate == pytest.approx(1.0)
    assert len(summary.negative_rank1_scores) == 2
    assert summary.latency_min_ms == 100
    assert summary.latency_max_ms == 1000
    assert summary.latency_mean_ms == pytest.approx(550.0)
    assert summary.latency_p50_ms == 500
    assert summary.latency_p95_ms == 1000
    assert summary.total_retry_attempts == 1


def test_fixture_loader_rejects_unreviewed_schema_fields(tmp_path: Path) -> None:
    """Golden labels cannot silently gain behavior outside the frozen v1 schema."""
    raw = cast(
        dict[str, object],
        json.loads(_FIXTURE.read_text(encoding="utf-8")),
    )
    raw["unexpected"] = "authority"
    mutated = tmp_path / "golden.json"
    mutated.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(RetrievalEvaluationError, match="unknown=\['unexpected'\]"):
        load_golden_retrieval_dataset(mutated)


def test_catalog_validation_rejects_unknown_positive_chunk_label() -> None:
    """A fixture cannot refer to evidence outside the checked canonical corpus."""
    dataset = load_golden_retrieval_dataset(_FIXTURE)
    first = dataset.cases[0]
    mutated_case = replace(
        first,
        relevant_chunk_ids=("knowledge-chunk:invented:v1",),
    )
    mutated = replace(dataset, cases=(mutated_case, *dataset.cases[1:]))

    with pytest.raises(RetrievalEvaluationError, match="unknown canonical chunk"):
        validate_dataset_catalog(mutated, _catalog())


def test_provider_failure_is_not_silently_converted_into_a_retrieval_miss() -> None:
    """Incomplete runtime evidence prevents publication of misleading aggregate quality."""
    dataset = load_golden_retrieval_dataset(_FIXTURE)
    observations = list(_complete_observations())
    observations[0] = RetrievalCaseObservation(
        case_id=dataset.cases[0].case_id,
        returned_chunks=(),
        client_elapsed_ms=125,
        provider_request_id="",
        retry_attempts=0,
        failure_category="provider_code=ThrottlingException",
    )

    with pytest.raises(RetrievalEvaluationIncompleteError, match="failures prevent"):
        aggregate_retrieval_evaluation(dataset, _catalog(), tuple(observations))


def test_observation_provenance_must_match_checked_catalog() -> None:
    """Evaluation cannot accept a chunk ID paired with provider-invented provenance."""
    dataset = load_golden_retrieval_dataset(_FIXTURE)
    observations = list(_complete_observations())
    first_result = observations[0].returned_chunks[0]
    forged = replace(first_result, document_id="knowledge-doc:forged:v1")
    observations[0] = replace(
        observations[0],
        returned_chunks=(forged, *observations[0].returned_chunks[1:]),
    )

    with pytest.raises(RetrievalEvaluationError, match="provenance disagrees"):
        aggregate_retrieval_evaluation(dataset, _catalog(), tuple(observations))
