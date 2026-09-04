"""Structural tests for the Phase 7 offline retrieval golden dataset."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from opslens.knowledge_retrieval.domain import KnowledgeSourceType

_FIXTURE = (
    Path(__file__).parents[2]
    / "fixtures"
    / "knowledge_retrieval"
    / "golden_retrieval_v1.json"
)


def _load_dataset() -> dict[str, object]:
    """Load the checked-in golden fixture as a typed mapping boundary."""
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return cast(dict[str, object], raw)


def test_golden_dataset_is_versioned_offline_first_and_non_structured() -> None:
    """The first dataset freezes retrieval evaluation without creating AWS authority."""
    dataset = _load_dataset()

    assert dataset["dataset_id"] == "knowledge-retrieval-golden:v1"
    assert dataset["corpus_status"] == "planned_for_gate_7_2"
    authority_boundary = cast(str, dataset["authority_boundary"])
    assert "Structured NVD, KEV, EPSS, CVSS, GHSA applicability" in authority_boundary


def test_golden_dataset_has_unique_cases_with_expected_evidence_ids() -> None:
    """Every positive question identifies expected documents and chunks for Recall@K/MRR."""
    dataset = _load_dataset()
    cases = cast(list[object], dataset["cases"])

    assert 8 <= len(cases) <= 12

    case_ids: list[str] = []
    positive_cases = 0
    negative_cases = 0
    allowed_source_types = {source_type.value for source_type in KnowledgeSourceType}

    for raw_case in cases:
        case = cast(dict[str, object], raw_case)
        case_id = cast(str, case["case_id"])
        question = cast(str, case["question"])
        relevant_document_ids = cast(list[object], case["relevant_document_ids"])
        relevant_chunk_ids = cast(list[object], case["relevant_chunk_ids"])
        expected_source_types = cast(list[object], case["expected_source_types"])
        should_have_relevant_evidence = cast(bool, case["should_have_relevant_evidence"])

        assert case_id.strip()
        assert question.strip()
        assert case_id not in case_ids
        case_ids.append(case_id)
        assert all(isinstance(value, str) and value.strip() for value in relevant_document_ids)
        assert all(isinstance(value, str) and value.strip() for value in relevant_chunk_ids)
        assert all(
            isinstance(value, str) and value in allowed_source_types
            for value in expected_source_types
        )

        if should_have_relevant_evidence:
            positive_cases += 1
            assert relevant_document_ids
            assert relevant_chunk_ids
            assert expected_source_types
        else:
            negative_cases += 1
            assert relevant_document_ids == []
            assert relevant_chunk_ids == []
            assert expected_source_types == []

    assert positive_cases >= 6
    assert negative_cases >= 2
