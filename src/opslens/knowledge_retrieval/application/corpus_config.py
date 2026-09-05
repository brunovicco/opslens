"""Fail-closed loading for versioned Gate 7.2 corpus inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from opslens.knowledge_retrieval.domain import (
    ChunkSelectionSpec,
    CorpusChunkManifestEntry,
    CorpusDocumentManifestEntry,
    DocumentMaterializationSpec,
    KnowledgeCorpusManifest,
    KnowledgeCorpusSpec,
    KnowledgeSourceDescriptor,
    KnowledgeSourceRegistry,
    KnowledgeSourceType,
)

_EXPECTED_NORMALIZATION_POLICY: dict[str, str] = {
    "encoding": "utf-8-strict",
    "newline": "lf",
    "unicode": "preserve",
    "bom": "reject",
    "nul": "reject",
    "selection": "exact-line-aligned-start-inclusive-end-exclusive",
    "document_join": "two-lf",
}


class CorpusConfigError(ValueError):
    """Raised when checked-in corpus configuration violates the exact v1 schema."""


def _load_object(path: Path) -> dict[str, object]:
    """Load one UTF-8 JSON object while rejecting invalid or non-object content."""
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CorpusConfigError(f"could not read corpus config {path}") from exc
    try:
        parsed = cast(object, json.loads(raw_text))
    except json.JSONDecodeError as exc:
        raise CorpusConfigError(f"corpus config {path} must contain valid JSON") from exc
    if not isinstance(parsed, dict):
        raise CorpusConfigError(f"corpus config {path} must contain one JSON object")
    return cast(dict[str, object], parsed)


def _require_exact_keys(
    value: dict[str, object],
    *,
    expected: set[str],
    label: str,
) -> None:
    """Reject both missing and unknown schema keys."""
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise CorpusConfigError(
            f"{label} keys must match the v1 schema; missing={missing}, unknown={unknown}"
        )


def _require_string(value: object, *, label: str) -> str:
    """Require one non-empty string without normalizing configuration silently."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise CorpusConfigError(f"{label} must be one trimmed non-empty string")
    return value


def _require_positive_int(value: object, *, label: str) -> int:
    """Require one positive non-boolean integer from checked JSON evidence."""
    if type(value) is not int or value <= 0:
        raise CorpusConfigError(f"{label} must be a positive integer")
    return value


def _require_list(value: object, *, label: str) -> list[object]:
    """Require one JSON array through an explicit typing boundary."""
    if not isinstance(value, list):
        raise CorpusConfigError(f"{label} must be a JSON array")
    return cast(list[object], value)


def _require_object(value: object, *, label: str) -> dict[str, object]:
    """Require one JSON object through an explicit typing boundary."""
    if not isinstance(value, dict):
        raise CorpusConfigError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _require_string_tuple(value: object, *, label: str) -> tuple[str, ...]:
    """Convert one JSON array of strings to a typed immutable tuple."""
    items = _require_list(value, label=label)
    return tuple(_require_string(item, label=label) for item in items)


def _require_source_type(value: object, *, label: str) -> KnowledgeSourceType:
    """Convert one exact checked source-type string to its frozen enum."""
    try:
        return KnowledgeSourceType(_require_string(value, label=label))
    except ValueError as exc:
        raise CorpusConfigError(f"{label} contains an unsupported source_type") from exc


def load_source_registry(path: Path) -> KnowledgeSourceRegistry:
    """Load the exact v1 pinned-source registry from one checked-in JSON file."""
    raw = _load_object(path)
    _require_exact_keys(
        raw,
        expected={
            "registry_id",
            "purpose",
            "authority_boundary",
            "acquisition_status",
            "entries",
        },
        label="source registry",
    )
    _require_string(raw["purpose"], label="source registry purpose")
    _require_string(raw["authority_boundary"], label="source registry authority_boundary")
    if raw["acquisition_status"] != "not_started":
        raise CorpusConfigError(
            "source registry acquisition_status must remain 'not_started'; "
            "materialization evidence belongs in the manifest"
        )

    entries: list[KnowledgeSourceDescriptor] = []
    for index, raw_entry in enumerate(_require_list(raw["entries"], label="source entries")):
        entry = _require_object(raw_entry, label=f"source entry {index}")
        _require_exact_keys(
            entry,
            expected={
                "document_id",
                "source_id",
                "source_type",
                "canonical_uri",
                "upstream_repository",
                "upstream_commit_sha",
                "upstream_path",
                "expected_chunk_ids",
            },
            label=f"source entry {index}",
        )
        source_type = _require_source_type(
            entry["source_type"],
            label=f"source entry {index} source_type",
        )
        entries.append(
            KnowledgeSourceDescriptor(
                document_id=_require_string(
                    entry["document_id"], label=f"source entry {index} document_id"
                ),
                source_id=_require_string(
                    entry["source_id"], label=f"source entry {index} source_id"
                ),
                source_type=source_type,
                canonical_uri=_require_string(
                    entry["canonical_uri"], label=f"source entry {index} canonical_uri"
                ),
                upstream_repository=_require_string(
                    entry["upstream_repository"],
                    label=f"source entry {index} upstream_repository",
                ),
                upstream_commit_sha=_require_string(
                    entry["upstream_commit_sha"],
                    label=f"source entry {index} upstream_commit_sha",
                ),
                upstream_path=_require_string(
                    entry["upstream_path"], label=f"source entry {index} upstream_path"
                ),
                expected_chunk_ids=_require_string_tuple(
                    entry["expected_chunk_ids"],
                    label=f"source entry {index} expected_chunk_ids",
                ),
            )
        )

    return KnowledgeSourceRegistry(
        registry_id=_require_string(raw["registry_id"], label="registry_id"),
        entries=tuple(entries),
    )


def load_corpus_spec(path: Path) -> KnowledgeCorpusSpec:
    """Load the exact v1 normalization and section-selection contract."""
    raw = _load_object(path)
    _require_exact_keys(
        raw,
        expected={"spec_id", "source_registry_id", "normalization", "documents"},
        label="corpus spec",
    )
    normalization = _require_object(raw["normalization"], label="normalization")
    if normalization != _EXPECTED_NORMALIZATION_POLICY:
        raise CorpusConfigError(
            "normalization must exactly match the frozen v1 corpus policy"
        )

    documents: list[DocumentMaterializationSpec] = []
    for doc_index, raw_document in enumerate(
        _require_list(raw["documents"], label="corpus documents")
    ):
        document = _require_object(raw_document, label=f"corpus document {doc_index}")
        _require_exact_keys(
            document,
            expected={"document_id", "title", "selections"},
            label=f"corpus document {doc_index}",
        )
        selections: list[ChunkSelectionSpec] = []
        for selection_index, raw_selection in enumerate(
            _require_list(
                document["selections"],
                label=f"corpus document {doc_index} selections",
            )
        ):
            selection = _require_object(
                raw_selection,
                label=f"corpus document {doc_index} selection {selection_index}",
            )
            _require_exact_keys(
                selection,
                expected={"chunk_id", "section_path", "start_marker", "end_marker"},
                label=f"corpus document {doc_index} selection {selection_index}",
            )
            selections.append(
                ChunkSelectionSpec(
                    chunk_id=_require_string(
                        selection["chunk_id"],
                        label=f"selection {selection_index} chunk_id",
                    ),
                    section_path=_require_string_tuple(
                        selection["section_path"],
                        label=f"selection {selection_index} section_path",
                    ),
                    start_marker=_require_string(
                        selection["start_marker"],
                        label=f"selection {selection_index} start_marker",
                    ),
                    end_marker=_require_string(
                        selection["end_marker"],
                        label=f"selection {selection_index} end_marker",
                    ),
                )
            )
        documents.append(
            DocumentMaterializationSpec(
                document_id=_require_string(
                    document["document_id"],
                    label=f"corpus document {doc_index} document_id",
                ),
                title=_require_string(
                    document["title"],
                    label=f"corpus document {doc_index} title",
                ),
                selections=tuple(selections),
            )
        )

    return KnowledgeCorpusSpec(
        spec_id=_require_string(raw["spec_id"], label="spec_id"),
        source_registry_id=_require_string(
            raw["source_registry_id"],
            label="source_registry_id",
        ),
        documents=tuple(documents),
    )


def load_corpus_manifest(path: Path) -> KnowledgeCorpusManifest:
    """Load the exact checked hash-only v1 manifest without replaying external sources."""
    raw = _load_object(path)
    _require_exact_keys(
        raw,
        expected={
            "manifest_id",
            "source_registry_id",
            "corpus_spec_id",
            "documents",
        },
        label="corpus manifest",
    )

    documents: list[CorpusDocumentManifestEntry] = []
    for doc_index, raw_document in enumerate(
        _require_list(raw["documents"], label="manifest documents")
    ):
        document = _require_object(
            raw_document,
            label=f"manifest document {doc_index}",
        )
        _require_exact_keys(
            document,
            expected={
                "document_id",
                "source_id",
                "source_type",
                "canonical_uri",
                "acquisition_uri",
                "upstream_repository",
                "upstream_commit_sha",
                "upstream_path",
                "source_byte_count",
                "source_bytes_sha256",
                "title",
                "content_utf8_byte_count",
                "content_sha256",
                "chunks",
            },
            label=f"manifest document {doc_index}",
        )

        chunks: list[CorpusChunkManifestEntry] = []
        for chunk_index, raw_chunk in enumerate(
            _require_list(
                document["chunks"],
                label=f"manifest document {doc_index} chunks",
            )
        ):
            chunk = _require_object(
                raw_chunk,
                label=f"manifest document {doc_index} chunk {chunk_index}",
            )
            _require_exact_keys(
                chunk,
                expected={
                    "chunk_id",
                    "section_path",
                    "content_utf8_byte_count",
                    "chunk_content_sha256",
                },
                label=f"manifest document {doc_index} chunk {chunk_index}",
            )
            chunks.append(
                CorpusChunkManifestEntry(
                    chunk_id=_require_string(
                        chunk["chunk_id"],
                        label=f"manifest chunk {chunk_index} chunk_id",
                    ),
                    section_path=_require_string_tuple(
                        chunk["section_path"],
                        label=f"manifest chunk {chunk_index} section_path",
                    ),
                    content_utf8_byte_count=_require_positive_int(
                        chunk["content_utf8_byte_count"],
                        label=f"manifest chunk {chunk_index} content_utf8_byte_count",
                    ),
                    chunk_content_sha256=_require_string(
                        chunk["chunk_content_sha256"],
                        label=f"manifest chunk {chunk_index} chunk_content_sha256",
                    ),
                )
            )

        documents.append(
            CorpusDocumentManifestEntry(
                document_id=_require_string(
                    document["document_id"],
                    label=f"manifest document {doc_index} document_id",
                ),
                source_id=_require_string(
                    document["source_id"],
                    label=f"manifest document {doc_index} source_id",
                ),
                source_type=_require_source_type(
                    document["source_type"],
                    label=f"manifest document {doc_index} source_type",
                ),
                canonical_uri=_require_string(
                    document["canonical_uri"],
                    label=f"manifest document {doc_index} canonical_uri",
                ),
                acquisition_uri=_require_string(
                    document["acquisition_uri"],
                    label=f"manifest document {doc_index} acquisition_uri",
                ),
                upstream_repository=_require_string(
                    document["upstream_repository"],
                    label=f"manifest document {doc_index} upstream_repository",
                ),
                upstream_commit_sha=_require_string(
                    document["upstream_commit_sha"],
                    label=f"manifest document {doc_index} upstream_commit_sha",
                ),
                upstream_path=_require_string(
                    document["upstream_path"],
                    label=f"manifest document {doc_index} upstream_path",
                ),
                source_byte_count=_require_positive_int(
                    document["source_byte_count"],
                    label=f"manifest document {doc_index} source_byte_count",
                ),
                source_bytes_sha256=_require_string(
                    document["source_bytes_sha256"],
                    label=f"manifest document {doc_index} source_bytes_sha256",
                ),
                title=_require_string(
                    document["title"],
                    label=f"manifest document {doc_index} title",
                ),
                content_utf8_byte_count=_require_positive_int(
                    document["content_utf8_byte_count"],
                    label=f"manifest document {doc_index} content_utf8_byte_count",
                ),
                content_sha256=_require_string(
                    document["content_sha256"],
                    label=f"manifest document {doc_index} content_sha256",
                ),
                chunks=tuple(chunks),
            )
        )

    return KnowledgeCorpusManifest(
        manifest_id=_require_string(raw["manifest_id"], label="manifest_id"),
        source_registry_id=_require_string(
            raw["source_registry_id"],
            label="manifest source_registry_id",
        ),
        corpus_spec_id=_require_string(
            raw["corpus_spec_id"],
            label="manifest corpus_spec_id",
        ),
        documents=tuple(documents),
    )
