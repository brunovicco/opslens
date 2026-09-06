"""Tests for loading checked Gate 7.2 manifest evidence in the retrieval runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from opslens.knowledge_retrieval.application.corpus_config import (
    CorpusConfigError,
    load_corpus_manifest,
)
from opslens.knowledge_retrieval.domain import CORPUS_MANIFEST_ID

_REPO_ROOT = Path(__file__).parents[3]
_MANIFEST_FILE = _REPO_ROOT / "knowledge" / "corpus" / "v1" / "manifest.json"
_EXPECTED_MANIFEST_SHA256 = (
    "98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418"
)


def _load_json(path: Path) -> dict[str, object]:
    """Load one checked JSON object for controlled negative mutation."""
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, value: dict[str, object]) -> None:
    """Write one deterministic negative JSON fixture."""
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def test_checked_manifest_loads_as_typed_runtime_catalog_input() -> None:
    """Runtime retrieval can use checked hash evidence without replaying external sources."""
    import hashlib

    manifest = load_corpus_manifest(_MANIFEST_FILE)
    raw = _MANIFEST_FILE.read_bytes()

    assert manifest.manifest_id == CORPUS_MANIFEST_ID
    assert len(manifest.documents) == 6
    assert sum(len(document.chunks) for document in manifest.documents) == 9
    assert hashlib.sha256(raw).hexdigest() == _EXPECTED_MANIFEST_SHA256


def test_manifest_loader_rejects_unknown_document_field(tmp_path: Path) -> None:
    """Runtime cannot silently gain unreviewed provenance authority from manifest JSON."""
    raw = _load_json(_MANIFEST_FILE)
    documents = cast(list[dict[str, object]], raw["documents"])
    documents[0]["runtime_hint"] = "trust-provider"
    mutated = tmp_path / "manifest.json"
    _write_json(mutated, raw)

    with pytest.raises(CorpusConfigError, match=r"unknown=\['runtime_hint'\]"):
        load_corpus_manifest(mutated)


def test_manifest_loader_rejects_non_positive_chunk_byte_count(tmp_path: Path) -> None:
    """A runtime catalog cannot admit impossible zero-length checked chunk evidence."""
    raw = _load_json(_MANIFEST_FILE)
    documents = cast(list[dict[str, object]], raw["documents"])
    chunks = cast(list[dict[str, object]], documents[0]["chunks"])
    chunks[0]["content_utf8_byte_count"] = 0
    mutated = tmp_path / "manifest.json"
    _write_json(mutated, raw)

    with pytest.raises(CorpusConfigError, match="positive integer"):
        load_corpus_manifest(mutated)
