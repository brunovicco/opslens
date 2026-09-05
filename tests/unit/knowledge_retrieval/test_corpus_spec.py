"""Tests for the frozen Gate 7.2 canonical corpus specification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from opslens.knowledge_retrieval.domain import CORPUS_SPEC_ID, SOURCE_REGISTRY_ID

_REPO_ROOT = Path(__file__).parents[3]
_CORPUS_DIR = _REPO_ROOT / "knowledge" / "corpus" / "v1"
_CORPUS_SPEC_FILE = _CORPUS_DIR / "corpus_spec.json"
_SOURCE_REGISTRY_FILE = _CORPUS_DIR / "source_registry.json"
_GOLDEN_FIXTURE = (
    Path(__file__).parents[2]
    / "fixtures"
    / "knowledge_retrieval"
    / "golden_retrieval_v1.json"
)


def _load(path: Path) -> dict[str, object]:
    """Load one checked-in JSON input through an explicit typing boundary."""
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_corpus_spec_freezes_minimal_deterministic_normalization() -> None:
    """The v1 normalizer changes representation only where the policy explicitly allows it."""
    raw = _load(_CORPUS_SPEC_FILE)

    assert raw["spec_id"] == CORPUS_SPEC_ID
    assert raw["source_registry_id"] == SOURCE_REGISTRY_ID
    assert raw["normalization"] == {
        "encoding": "utf-8-strict",
        "newline": "lf",
        "unicode": "preserve",
        "bom": "reject",
        "nul": "reject",
        "selection": "exact-line-aligned-start-inclusive-end-exclusive",
        "document_join": "two-lf",
    }


def test_corpus_spec_exactly_covers_registry_and_positive_golden_chunks() -> None:
    """No source-registry document or golden chunk is silently added, omitted, or reordered."""
    corpus = _load(_CORPUS_SPEC_FILE)
    registry = _load(_SOURCE_REGISTRY_FILE)
    golden = _load(_GOLDEN_FIXTURE)

    corpus_documents = cast(list[dict[str, object]], corpus["documents"])
    registry_entries = cast(list[dict[str, object]], registry["entries"])
    golden_cases = cast(list[dict[str, object]], golden["cases"])

    corpus_document_ids = [cast(str, document["document_id"]) for document in corpus_documents]
    registry_document_ids = [cast(str, entry["document_id"]) for entry in registry_entries]
    assert corpus_document_ids == registry_document_ids

    corpus_chunks_by_document = {
        cast(str, document["document_id"]): [
            cast(str, selection["chunk_id"])
            for selection in cast(list[dict[str, object]], document["selections"])
        ]
        for document in corpus_documents
    }
    registry_chunks_by_document = {
        cast(str, entry["document_id"]): cast(list[str], entry["expected_chunk_ids"])
        for entry in registry_entries
    }
    assert corpus_chunks_by_document == registry_chunks_by_document

    golden_chunk_ids = {
        chunk_id
        for case in golden_cases
        if cast(bool, case["should_have_relevant_evidence"])
        for chunk_id in cast(list[str], case["relevant_chunk_ids"])
    }
    corpus_chunk_ids = {
        chunk_id
        for chunk_ids in corpus_chunks_by_document.values()
        for chunk_id in chunk_ids
    }
    assert corpus_chunk_ids == golden_chunk_ids


def test_all_corpus_selectors_are_explicit_bounded_and_provenanced() -> None:
    """Each chunk has exact non-empty sentinels and a human-readable section path."""
    corpus = _load(_CORPUS_SPEC_FILE)
    documents = cast(list[dict[str, object]], corpus["documents"])

    selectors = [
        selection
        for document in documents
        for selection in cast(list[dict[str, object]], document["selections"])
    ]
    assert len(selectors) == 9
    assert len({cast(str, selector["chunk_id"]) for selector in selectors}) == 9

    for selector in selectors:
        start_marker = cast(str, selector["start_marker"])
        end_marker = cast(str, selector["end_marker"])
        section_path = cast(list[str], selector["section_path"])
        assert start_marker
        assert end_marker
        assert start_marker != end_marker
        assert "\r" not in start_marker
        assert "\r" not in end_marker
        assert section_path
        assert all(section.strip() == section and section for section in section_path)
