"""Tests for the Gate 7.2 trusted source registry."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from opslens.knowledge_retrieval.domain import (
    KnowledgeRetrievalValidationError,
    KnowledgeSourceType,
)
from opslens.knowledge_retrieval.domain.source_registry import (
    RAW_GITHUB_HOST,
    SOURCE_REGISTRY_ID,
    KnowledgeSourceDescriptor,
    KnowledgeSourceRegistry,
)

_FIXTURE_DIR = Path(__file__).parents[2] / "fixtures" / "knowledge_retrieval"
_REGISTRY_FIXTURE = _FIXTURE_DIR / "source_registry_v1.json"
_GOLDEN_FIXTURE = _FIXTURE_DIR / "golden_retrieval_v1.json"


def _load_mapping(path: Path) -> dict[str, object]:
    """Load a checked-in JSON fixture through one explicit typing boundary."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, object], raw)


def _descriptor(raw: object) -> KnowledgeSourceDescriptor:
    """Build the domain descriptor from one checked-in registry entry."""
    entry = cast(dict[str, object], raw)
    source_type = KnowledgeSourceType(cast(str, entry["source_type"]))
    chunk_ids = tuple(cast(list[str], entry["expected_chunk_ids"]))
    return KnowledgeSourceDescriptor(
        document_id=cast(str, entry["document_id"]),
        source_id=cast(str, entry["source_id"]),
        source_type=source_type,
        canonical_uri=cast(str, entry["canonical_uri"]),
        upstream_repository=cast(str, entry["upstream_repository"]),
        upstream_commit_sha=cast(str, entry["upstream_commit_sha"]),
        upstream_path=cast(str, entry["upstream_path"]),
        expected_chunk_ids=chunk_ids,
    )


def _registry() -> KnowledgeSourceRegistry:
    raw = _load_mapping(_REGISTRY_FIXTURE)
    entries = tuple(_descriptor(entry) for entry in cast(list[object], raw["entries"]))
    return KnowledgeSourceRegistry(
        registry_id=cast(str, raw["registry_id"]),
        entries=entries,
    )


def test_registry_is_versioned_pre_acquisition_and_non_structured() -> None:
    """The registry authorizes sources without pretending acquisition already happened."""
    raw = _load_mapping(_REGISTRY_FIXTURE)

    assert raw["registry_id"] == SOURCE_REGISTRY_ID
    assert raw["acquisition_status"] == "not_started"
    authority_boundary = cast(str, raw["authority_boundary"])
    assert "explanatory/remediation" in authority_boundary
    assert "NVD, KEV, EPSS, CVSS, GHSA applicability" in authority_boundary


def test_registry_exactly_covers_positive_golden_documents_and_chunks() -> None:
    """Every positive golden expectation has exactly one pre-authorized source."""
    registry = _registry()
    golden = _load_mapping(_GOLDEN_FIXTURE)
    cases = cast(list[object], golden["cases"])

    expected_documents: set[str] = set()
    expected_chunks: set[str] = set()
    expected_types_by_document: dict[str, set[str]] = {}

    for raw_case in cases:
        case = cast(dict[str, object], raw_case)
        if not cast(bool, case["should_have_relevant_evidence"]):
            continue
        document_ids = cast(list[str], case["relevant_document_ids"])
        chunk_ids = cast(list[str], case["relevant_chunk_ids"])
        source_types = cast(list[str], case["expected_source_types"])
        expected_documents.update(document_ids)
        expected_chunks.update(chunk_ids)
        for document_id in document_ids:
            expected_types_by_document.setdefault(document_id, set()).update(source_types)

    registry_documents = {entry.document_id for entry in registry.entries}
    registry_chunks = {
        chunk_id
        for entry in registry.entries
        for chunk_id in entry.expected_chunk_ids
    }

    assert registry_documents == expected_documents
    assert registry_chunks == expected_chunks
    for entry in registry.entries:
        assert expected_types_by_document[entry.document_id] == {entry.source_type.value}


def test_registry_pins_official_source_files_to_full_commits() -> None:
    """Every v1 acquisition URI is derived from repository, commit, and path evidence."""
    registry = _registry()

    assert len(registry.entries) == 6
    assert {entry.acquisition_host for entry in registry.entries} == {RAW_GITHUB_HOST}
    assert {entry.upstream_repository for entry in registry.entries} == {
        "OWASP/CheatSheetSeries",
        "astral-sh/uv",
        "django/django",
        "pypa/packaging.python.org",
        "pypa/pip",
    }
    for entry in registry.entries:
        assert len(entry.upstream_commit_sha) == 40
        assert entry.acquisition_uri.startswith(
            f"https://{RAW_GITHUB_HOST}/{entry.upstream_repository}/"
        )
        assert entry.upstream_commit_sha in entry.acquisition_uri


def test_source_descriptor_rejects_mutable_or_unsafe_upstream_coordinates() -> None:
    """The corpus cannot acquire mutable branches or path traversal through registry data."""
    descriptor = _registry().entries[0]

    with pytest.raises(
        KnowledgeRetrievalValidationError,
        match="full lowercase 40-hex Git SHA",
    ):
        replace(descriptor, upstream_commit_sha="main")

    with pytest.raises(
        KnowledgeRetrievalValidationError,
        match="traversal segments",
    ):
        replace(descriptor, upstream_path="docs/../secrets.txt")

    with pytest.raises(
        KnowledgeRetrievalValidationError,
        match="canonical_uri must be an absolute HTTPS URI",
    ):
        replace(descriptor, canonical_uri="http://pip.pypa.io/topics/dependency-resolution/")


def test_registry_rejects_duplicate_document_or_chunk_authority() -> None:
    """One v1 document/chunk identity cannot be authorized by competing registry entries."""
    registry = _registry()
    first = registry.entries[0]
    second = registry.entries[1]

    with pytest.raises(
        KnowledgeRetrievalValidationError,
        match="registry document_id values must be unique",
    ):
        KnowledgeSourceRegistry(
            registry_id=SOURCE_REGISTRY_ID,
            entries=(first, replace(second, document_id=first.document_id)),
        )

    with pytest.raises(
        KnowledgeRetrievalValidationError,
        match="registry expected_chunk_ids values must be unique",
    ):
        KnowledgeSourceRegistry(
            registry_id=SOURCE_REGISTRY_ID,
            entries=(
                first,
                replace(second, expected_chunk_ids=(first.expected_chunk_ids[0],)),
            ),
        )
