"""Deterministic checked-corpus lookup for Bedrock retrieval admission."""

from __future__ import annotations

import re
from dataclasses import dataclass

from opslens.knowledge_retrieval.application.bedrock_publication import (
    BEDROCK_PUBLICATION_PREFIX,
)
from opslens.knowledge_retrieval.domain import (
    KnowledgeCorpusManifest,
    KnowledgeSourceType,
)

_CHUNK_KEY_PREFIX = f"{BEDROCK_PUBLICATION_PREFIX}/chunks/"
_CHUNK_KEY_PATTERN = re.compile(
    rf"^{re.escape(_CHUNK_KEY_PREFIX)}(?P<digest>[0-9a-f]{{64}})\.txt$",
    re.ASCII,
)


class RetrievalCatalogError(ValueError):
    """Raised when checked corpus evidence cannot resolve one retrieval result safely."""


def _require_nonblank(value: object, *, field: str) -> str:
    """Require one trimmed non-empty string at a runtime boundary."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise RetrievalCatalogError(f"{field} must be one trimmed non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class CanonicalRetrievalChunk:
    """Provider-neutral canonical identity behind one published Bedrock content key."""

    content_key: str
    chunk_id: str
    document_id: str
    source_id: str
    source_type: KnowledgeSourceType
    canonical_uri: str
    document_content_sha256: str
    chunk_content_sha256: str
    title: str
    section_path: tuple[str, ...]
    content_utf8_byte_count: int

    def __post_init__(self) -> None:
        """Require the key digest and canonical chunk digest to be identical."""
        match = _CHUNK_KEY_PATTERN.fullmatch(self.content_key)
        if match is None:
            raise RetrievalCatalogError(
                "content_key must use the frozen content-addressed Bedrock chunk shape"
            )
        if match.group("digest") != self.chunk_content_sha256:
            raise RetrievalCatalogError(
                "content_key digest must equal chunk_content_sha256"
            )
        if type(self.content_utf8_byte_count) is not int or self.content_utf8_byte_count <= 0:
            raise RetrievalCatalogError("content_utf8_byte_count must be a positive integer")


@dataclass(frozen=True, slots=True)
class CanonicalRetrievalCatalog:
    """Exact one-to-one lookup from published S3 content keys to checked corpus chunks."""

    chunks: tuple[CanonicalRetrievalChunk, ...]

    def __post_init__(self) -> None:
        """Reject empty or ambiguous content-addressed lookup authority."""
        if not isinstance(self.chunks, tuple) or not self.chunks:
            raise RetrievalCatalogError("chunks must be one non-empty tuple")
        if any(not isinstance(chunk, CanonicalRetrievalChunk) for chunk in self.chunks):
            raise RetrievalCatalogError(
                "chunks must contain only CanonicalRetrievalChunk values"
            )
        keys = tuple(chunk.content_key for chunk in self.chunks)
        digests = tuple(chunk.chunk_content_sha256 for chunk in self.chunks)
        chunk_ids = tuple(chunk.chunk_id for chunk in self.chunks)
        for label, values in (
            ("content_key", keys),
            ("chunk_content_sha256", digests),
            ("chunk_id", chunk_ids),
        ):
            if len(set(values)) != len(values):
                raise RetrievalCatalogError(
                    f"canonical retrieval {label} values must be globally unique"
                )

    def resolve_content_key(self, key: object) -> CanonicalRetrievalChunk:
        """Resolve one exact published content key or fail closed."""
        normalized = _require_nonblank(key, field="content_key")
        if _CHUNK_KEY_PATTERN.fullmatch(normalized) is None:
            raise RetrievalCatalogError(
                "content_key is outside the frozen Bedrock publication key shape"
            )
        matches = tuple(chunk for chunk in self.chunks if chunk.content_key == normalized)
        if len(matches) != 1:
            raise RetrievalCatalogError(
                "content_key does not resolve to exactly one checked canonical chunk"
            )
        return matches[0]


def build_retrieval_catalog(manifest: KnowledgeCorpusManifest) -> CanonicalRetrievalCatalog:
    """Build the content-key lookup authority directly from one checked typed manifest."""
    if not isinstance(manifest, KnowledgeCorpusManifest):
        raise RetrievalCatalogError("manifest must be one KnowledgeCorpusManifest")

    chunks: list[CanonicalRetrievalChunk] = []
    for document in manifest.documents:
        for chunk in document.chunks:
            chunks.append(
                CanonicalRetrievalChunk(
                    content_key=(
                        f"{_CHUNK_KEY_PREFIX}{chunk.chunk_content_sha256}.txt"
                    ),
                    chunk_id=chunk.chunk_id,
                    document_id=document.document_id,
                    source_id=document.source_id,
                    source_type=document.source_type,
                    canonical_uri=document.canonical_uri,
                    document_content_sha256=document.content_sha256,
                    chunk_content_sha256=chunk.chunk_content_sha256,
                    title=document.title,
                    section_path=chunk.section_path,
                    content_utf8_byte_count=chunk.content_utf8_byte_count,
                )
            )
    return CanonicalRetrievalCatalog(chunks=tuple(chunks))
