"""Regression tests for the preserved Gate 7.7 human-reviewed first run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from opslens.knowledge_retrieval.application.corpus_config import load_corpus_manifest
from opslens.knowledge_retrieval.application.grounding_evaluation import (
    ClaimCitationSupportJudgment,
    GroundingEvaluationError,
    GroundingSupportJudgmentSource,
    load_golden_grounding_dataset,
)
from opslens.knowledge_retrieval.application.grounding_review import (
    ReviewedCitationSelection,
    ReviewedGroundingCase,
    evaluate_reviewed_grounding_run,
)
from opslens.knowledge_retrieval.application.retrieval_catalog import (
    build_retrieval_catalog,
)
from opslens.knowledge_retrieval.domain import SynthesisDecision

_REVIEW_PATH = Path("labs/evidence/phase-7-gate-7-7-first-run-review-v1.json")
_DATASET_PATH = Path("tests/fixtures/knowledge_retrieval/golden_grounding_v1.json")
_MANIFEST_PATH = Path("knowledge/corpus/v1/manifest.json")
_RUN_HEAD_SHA = "507fe04f963c7eeb49748eb950101ea2fc55e14f"


def _object(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    raw = cast(dict[object, object], value)
    assert all(isinstance(key, str) for key in raw)
    return cast(dict[str, object], raw)


def _array(value: object) -> list[object]:
    assert isinstance(value, list)
    return cast(list[object], value)


def _text(value: object) -> str:
    assert isinstance(value, str)
    return value


def _integer(value: object) -> int:
    assert type(value) is int
    return value


def _boolean(value: object) -> bool:
    assert type(value) is bool
    return value


def _load_reviews() -> tuple[ReviewedGroundingCase, ...]:
    root = _object(cast(object, json.loads(_REVIEW_PATH.read_text(encoding="utf-8"))))
    assert root["artifact_id"] == "knowledge-grounding-first-run-review:v1"
    assert root["dataset_id"] == "knowledge-grounding-golden:v1"
    assert root["run_head_sha"] == _RUN_HEAD_SHA
    assert root["judgment_authority"] == "human_reviewed_claim_citation_pairs_v1"

    reviews: list[ReviewedGroundingCase] = []
    for raw_case in _array(root["cases"]):
        case = _object(raw_case)
        selections = tuple(
            ReviewedCitationSelection(
                citation_id=_text(item["citation_id"]),
                chunk_id=_text(item["chunk_id"]),
            )
            for item in (
                _object(raw_selection)
                for raw_selection in _array(case["selected_citations"])
            )
        )
        judgments = tuple(
            ClaimCitationSupportJudgment(
                claim_sha256=_text(item["claim_sha256"]),
                citation_id=_text(item["citation_id"]),
                supports_claim=_boolean(item["supports_claim"]),
                source=GroundingSupportJudgmentSource.HUMAN_REVIEWED,
                judgment_sha256=_text(item["judgment_sha256"]),
            )
            for item in (
                _object(raw_judgment)
                for raw_judgment in _array(case["support_judgments"])
            )
        )
        reviews.append(
            ReviewedGroundingCase(
                case_id=_text(case["case_id"]),
                question_sha256=_text(case["question_sha256"]),
                actual_decision=SynthesisDecision(_text(case["actual_decision"])),
                runtime_claim_count=_integer(case["runtime_claim_count"]),
                runtime_claim_citation_pair_count=_integer(
                    case["runtime_claim_citation_pair_count"]
                ),
                selected_citations=selections,
                support_judgments=judgments,
            )
        )
    return tuple(reviews)


def test_first_run_review_metrics_are_deterministic_and_content_free() -> None:
    """Compute frozen Gate 7.7 metrics from hashes, citations, and human labels only."""
    dataset = load_golden_grounding_dataset(_DATASET_PATH)
    catalog = build_retrieval_catalog(load_corpus_manifest(_MANIFEST_PATH))

    report = evaluate_reviewed_grounding_run(
        dataset,
        catalog,
        _load_reviews(),
    )

    assert [item.case_id for item in report.cases] == [
        "grounding-hash-verification-01",
        "grounding-transitive-review-01",
        "grounding-isolation-01",
        "grounding-insufficient-pip-tls-cipher-01",
    ]

    hash_case, transitive_case, isolation_case, abstention_case = report.cases

    assert hash_case.citation_target_precision == pytest.approx(0.5)
    assert hash_case.citation_target_recall == pytest.approx(1.0)
    assert hash_case.claim_supportedness_rate == pytest.approx(1.0)

    assert transitive_case.citation_target_precision == pytest.approx(0.25)
    assert transitive_case.citation_target_recall == pytest.approx(0.5)
    assert transitive_case.claim_supportedness_rate == pytest.approx(1.0)

    assert isolation_case.citation_target_precision == pytest.approx(0.0)
    assert isolation_case.citation_target_recall == pytest.approx(0.0)
    assert isolation_case.claim_supportedness_rate == pytest.approx(0.0)
    assert isolation_case.unsupported_claim_count == 2

    assert abstention_case.decision_correct is True
    assert abstention_case.claim_count == 0
    assert abstention_case.citation_target_precision is None
    assert abstention_case.citation_target_recall is None

    summary = report.summary
    assert summary.case_count == 4
    assert summary.decision_accuracy == pytest.approx(1.0)
    assert summary.citation_target_selected_count == 7
    assert summary.citation_target_expected_count == 4
    assert summary.citation_target_correct_count == 2
    assert summary.citation_target_precision == pytest.approx(2 / 7)
    assert summary.citation_target_recall == pytest.approx(0.5)
    assert summary.claim_count == 13
    assert summary.supported_claim_count == 11
    assert summary.unsupported_claim_count == 2
    assert summary.claim_supportedness_rate == pytest.approx(11 / 13)
    assert summary.unsupported_claim_rate == pytest.approx(2 / 13)
    assert summary.claim_citation_pair_count == 13
    assert summary.supporting_claim_citation_pair_count == 11
    assert summary.citation_correctness_rate == pytest.approx(11 / 13)
    assert summary.abstention_precision == pytest.approx(1.0)
    assert summary.abstention_recall == pytest.approx(1.0)


def test_first_run_review_rejects_unknown_selected_chunk() -> None:
    """A reviewed citation cannot point outside the checked canonical corpus."""
    dataset = load_golden_grounding_dataset(_DATASET_PATH)
    catalog = build_retrieval_catalog(load_corpus_manifest(_MANIFEST_PATH))
    reviews = list(_load_reviews())
    first = reviews[0]
    reviews[0] = ReviewedGroundingCase(
        case_id=first.case_id,
        question_sha256=first.question_sha256,
        actual_decision=first.actual_decision,
        runtime_claim_count=first.runtime_claim_count,
        runtime_claim_citation_pair_count=first.runtime_claim_citation_pair_count,
        selected_citations=(
            ReviewedCitationSelection(
                citation_id="C1",
                chunk_id="knowledge-chunk:unknown:v1",
            ),
            *first.selected_citations[1:],
        ),
        support_judgments=first.support_judgments,
    )

    with pytest.raises(GroundingEvaluationError, match="unknown canonical chunks"):
        evaluate_reviewed_grounding_run(dataset, catalog, tuple(reviews))


def test_first_run_review_judgment_hashes_fail_closed() -> None:
    """Human labels remain content-addressed evidence rather than mutable booleans."""
    with pytest.raises(GroundingEvaluationError, match="judgment_sha256"):
        ClaimCitationSupportJudgment(
            claim_sha256=(
                "99f583f44d2082c1a12adbfd00f340406c1ab9d864152e6d3bae5f5c1d8aee32"
            ),
            citation_id="C1",
            supports_claim=False,
            source=GroundingSupportJudgmentSource.HUMAN_REVIEWED,
            judgment_sha256=(
                "8feaac70eaee4f6c6d8b731aed6d3f9d2bb2c0463ca503f3b9da7b8d1cf0589e"
            ),
        )
