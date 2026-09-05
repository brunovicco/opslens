"""Tests for fail-closed loading of versioned Gate 7.2 corpus inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from opslens.knowledge_retrieval.application.corpus_config import (
    CorpusConfigError,
    load_corpus_spec,
    load_source_registry,
)
from opslens.knowledge_retrieval.domain import CORPUS_SPEC_ID, SOURCE_REGISTRY_ID

_REPO_ROOT = Path(__file__).parents[3]
_CORPUS_DIR = _REPO_ROOT / "knowledge" / "corpus" / "v1"
_REGISTRY_FILE = _CORPUS_DIR / "source_registry.json"
_SPEC_FILE = _CORPUS_DIR / "corpus_spec.json"


def _load_json(path: Path) -> dict[str, object]:
    """Load a checked-in JSON object for controlled mutation in negative tests."""
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, value: dict[str, object]) -> None:
    """Write deterministic UTF-8 JSON for one negative fixture."""
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def test_product_registry_and_corpus_spec_load_into_typed_contracts() -> None:
    """Checked-in product inputs are consumable without test-only parsing logic."""
    registry = load_source_registry(_REGISTRY_FILE)
    spec = load_corpus_spec(_SPEC_FILE)

    assert registry.registry_id == SOURCE_REGISTRY_ID
    assert spec.spec_id == CORPUS_SPEC_ID
    assert spec.source_registry_id == registry.registry_id
    assert [document.document_id for document in spec.documents] == [
        entry.document_id for entry in registry.entries
    ]
    assert sum(len(document.selections) for document in spec.documents) == 9


def test_registry_loader_rejects_unknown_schema_keys(tmp_path: Path) -> None:
    """Adding unreviewed registry authority cannot be silently ignored."""
    raw = _load_json(_REGISTRY_FILE)
    raw["unexpected"] = "authority"
    mutated = tmp_path / "registry.json"
    _write_json(mutated, raw)

    with pytest.raises(CorpusConfigError, match="unknown=\['unexpected'\]"):
        load_source_registry(mutated)


def test_corpus_spec_loader_rejects_normalization_policy_drift(tmp_path: Path) -> None:
    """Normalization changes require an explicit versioned contract change."""
    raw = _load_json(_SPEC_FILE)
    normalization = cast(dict[str, object], raw["normalization"])
    normalization["unicode"] = "NFKC"
    mutated = tmp_path / "corpus_spec.json"
    _write_json(mutated, raw)

    with pytest.raises(CorpusConfigError, match="frozen v1 corpus policy"):
        load_corpus_spec(mutated)


def test_corpus_spec_loader_rejects_unknown_selector_fields(tmp_path: Path) -> None:
    """A selector cannot gain hidden behavior outside the reviewed v1 schema."""
    raw = _load_json(_SPEC_FILE)
    documents = cast(list[dict[str, object]], raw["documents"])
    selections = cast(list[dict[str, object]], documents[0]["selections"])
    selections[0]["occurrence"] = 2
    mutated = tmp_path / "corpus_spec.json"
    _write_json(mutated, raw)

    with pytest.raises(CorpusConfigError, match="unknown=\['occurrence'\]"):
        load_corpus_spec(mutated)
