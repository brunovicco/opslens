"""Deterministic pre-ingestion projection for the Gate 7.3 Bedrock S3 data source."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import cast

from opslens.knowledge_retrieval.application.corpus_manifest import (
    build_corpus_manifest,
    serialize_corpus_manifest,
)
from opslens.knowledge_retrieval.domain import (
    CANONICAL_METADATA_FIELDS,
    KnowledgeCorpusSpec,
    KnowledgeSourceRegistry,
    MaterializedKnowledgeDocument,
)

BEDROCK_PUBLICATION_PREFIX = "knowledge/corpus/v1/bedrock"
MAX_BEDROCK_CUSTOM_METADATA_BYTES = 1_024
MAX_BEDROCK_CUSTOM_METADATA_KEYS = 35
MAX_S3_METADATA_SIDECAR_BYTES = 10 * 1_024

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_REQUIRED_METADATA_FIELDS = frozenset(
    {
        "source_id",
        "source_type",
        "canonical_uri",
        "document_id",
        "content_sha256",
        "title",
        "section_path",
    }
)


class BedrockPublicationError(ValueError):
    """Raised when canonical corpus evidence cannot form an admitted publication plan."""


def _sha256_text(value: str) -> str:
    """Return the SHA-256 digest of one exact UTF-8 string."""
    return sha256(value.encode("utf-8")).hexdigest()


def _require_sha256(value: object, *, field: str) -> str:
    """Require one lowercase SHA-256 digest."""
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise BedrockPublicationError(f"{field} must be a lowercase 64-hex SHA-256 digest")
    return value


def _require_s3_key(value: object, *, field: str, suffix: str) -> str:
    """Require one clean deterministic relative S3 object key."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise BedrockPublicationError(f"{field} must be one trimmed non-empty S3 key")
    if value.startswith("/") or "//" in value or ".." in value.split("/"):
        raise BedrockPublicationError(f"{field} must be a clean relative S3 key")
    if not value.endswith(suffix):
        raise BedrockPublicationError(f"{field} must end with {suffix!r}")
    return value


def _require_positive_int(value: object, *, field: str) -> int:
    """Require one positive non-boolean integer."""
    if type(value) is not int or value <= 0:
        raise BedrockPublicationError(f"{field} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class BedrockPublicationObject:
    """One canonical chunk and its S3 metadata sidecar before any remote write."""

    chunk_id: str
    document_id: str
    content_key: str
    metadata_key: str
    content_text: str
    content_sha256: str
    metadata_json: str
    metadata_sha256: str
    custom_metadata_byte_count: int
    custom_metadata_key_count: int

    def __post_init__(self) -> None:
        """Reject mismatched content, sidecar identity, or Bedrock metadata budgets."""
        if not isinstance(self.chunk_id, str) or not self.chunk_id.strip():
            raise BedrockPublicationError("chunk_id must be one non-empty string")
        if not isinstance(self.document_id, str) or not self.document_id.strip():
            raise BedrockPublicationError("document_id must be one non-empty string")
        content_key = _require_s3_key(self.content_key, field="content_key", suffix=".txt")
        metadata_key = _require_s3_key(
            self.metadata_key,
            field="metadata_key",
            suffix=".txt.metadata.json",
        )
        if metadata_key != f"{content_key}.metadata.json":
            raise BedrockPublicationError(
                "metadata_key must equal content_key plus '.metadata.json'"
            )
        if not isinstance(self.content_text, str) or not self.content_text.strip():
            raise BedrockPublicationError("content_text must contain canonical chunk text")
        content_sha256 = _require_sha256(self.content_sha256, field="content_sha256")
        if _sha256_text(self.content_text) != content_sha256:
            raise BedrockPublicationError(
                "content_sha256 must match the exact publication UTF-8 content"
            )
        if not isinstance(self.metadata_json, str) or not self.metadata_json.endswith("\n"):
            raise BedrockPublicationError("metadata_json must be stable JSON ending with LF")
        metadata_sha256 = _require_sha256(self.metadata_sha256, field="metadata_sha256")
        if _sha256_text(self.metadata_json) != metadata_sha256:
            raise BedrockPublicationError(
                "metadata_sha256 must match the exact metadata sidecar UTF-8 content"
            )
        try:
            parsed = cast(object, json.loads(self.metadata_json))
        except json.JSONDecodeError as exc:
            raise BedrockPublicationError("metadata_json must contain valid JSON") from exc
        if not isinstance(parsed, dict):
            raise BedrockPublicationError("metadata_json must contain one JSON object")

        custom_metadata_byte_count = _require_positive_int(
            self.custom_metadata_byte_count,
            field="custom_metadata_byte_count",
        )
        if custom_metadata_byte_count > MAX_BEDROCK_CUSTOM_METADATA_BYTES:
            raise BedrockPublicationError(
                "custom metadata exceeds the Bedrock + S3 Vectors 1 KB limit"
            )
        custom_metadata_key_count = _require_positive_int(
            self.custom_metadata_key_count,
            field="custom_metadata_key_count",
        )
        if custom_metadata_key_count > MAX_BEDROCK_CUSTOM_METADATA_KEYS:
            raise BedrockPublicationError(
                "custom metadata exceeds the Bedrock + S3 Vectors 35-key limit"
            )
        if len(self.metadata_json.encode("utf-8")) > MAX_S3_METADATA_SIDECAR_BYTES:
            raise BedrockPublicationError("metadata sidecar exceeds the S3 10 KB file limit")

        object.__setattr__(self, "content_key", content_key)
        object.__setattr__(self, "metadata_key", metadata_key)
        object.__setattr__(self, "content_sha256", content_sha256)
        object.__setattr__(self, "metadata_sha256", metadata_sha256)
        object.__setattr__(
            self,
            "custom_metadata_byte_count",
            custom_metadata_byte_count,
        )
        object.__setattr__(
            self,
            "custom_metadata_key_count",
            custom_metadata_key_count,
        )


@dataclass(frozen=True, slots=True)
class BedrockPublicationPlan:
    """Complete deterministic publication evidence before S3 or Bedrock is called."""

    prefix: str
    source_manifest_sha256: str
    objects: tuple[BedrockPublicationObject, ...]

    def __post_init__(self) -> None:
        """Require one bounded complete plan with unique object and chunk identities."""
        if self.prefix != BEDROCK_PUBLICATION_PREFIX:
            raise BedrockPublicationError(
                f"prefix must equal {BEDROCK_PUBLICATION_PREFIX!r}"
            )
        source_manifest_sha256 = _require_sha256(
            self.source_manifest_sha256,
            field="source_manifest_sha256",
        )
        if not isinstance(self.objects, tuple) or not self.objects:
            raise BedrockPublicationError("objects must be one non-empty tuple")
        if any(not isinstance(item, BedrockPublicationObject) for item in self.objects):
            raise BedrockPublicationError(
                "objects must contain only BedrockPublicationObject values"
            )
        content_keys = [item.content_key for item in self.objects]
        metadata_keys = [item.metadata_key for item in self.objects]
        chunk_ids = [item.chunk_id for item in self.objects]
        for label, values in (
            ("content_key", content_keys),
            ("metadata_key", metadata_keys),
            ("chunk_id", chunk_ids),
        ):
            if len(set(values)) != len(values):
                raise BedrockPublicationError(f"publication {label} values must be unique")
        expected_prefix = f"{self.prefix}/chunks/"
        if any(not key.startswith(expected_prefix) for key in content_keys):
            raise BedrockPublicationError(
                "every publication content key must remain inside the frozen chunks prefix"
            )
        object.__setattr__(self, "source_manifest_sha256", source_manifest_sha256)


def _metadata_attribute_string(value: str) -> dict[str, object]:
    """Encode one string attribute explicitly without embedding influence."""
    return {
        "value": {"type": "STRING", "stringValue": value},
        "includeForEmbedding": False,
    }


def _metadata_attribute_string_list(values: tuple[str, ...]) -> dict[str, object]:
    """Encode one string-list attribute explicitly without embedding influence."""
    return {
        "value": {"type": "STRING_LIST", "stringListValue": list(values)},
        "includeForEmbedding": False,
    }


def _build_metadata_values(
    materialized: MaterializedKnowledgeDocument,
    *,
    section_path: tuple[str, ...],
) -> dict[str, str | list[str]]:
    """Project only the Gate 7.1 canonical metadata vocabulary."""
    document = materialized.document
    values: dict[str, str | list[str]] = {
        "source_id": document.source_id,
        "source_type": document.source_type.value,
        "canonical_uri": document.canonical_uri,
        "document_id": document.document_id,
        "content_sha256": document.content_sha256,
        "title": document.title,
        "section_path": list(section_path),
    }
    if document.published_at is not None:
        values["published_at"] = document.published_at.isoformat()
    if document.updated_at is not None:
        values["updated_at"] = document.updated_at.isoformat()
    if document.vulnerability_ids:
        values["vulnerability_ids"] = list(document.vulnerability_ids)
    if document.ecosystem is not None:
        values["ecosystem"] = document.ecosystem
    if document.package_name is not None:
        values["package_name"] = document.package_name

    keys = set(values)
    if not _REQUIRED_METADATA_FIELDS.issubset(keys):
        raise BedrockPublicationError("publication metadata is missing required provenance fields")
    if not keys.issubset(CANONICAL_METADATA_FIELDS):
        raise BedrockPublicationError("publication metadata contains a non-canonical field")
    return values


def _serialize_metadata(values: dict[str, str | list[str]]) -> tuple[str, int]:
    """Serialize one Bedrock S3 metadata sidecar and return logical metadata bytes."""
    logical_json = json.dumps(
        values,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    logical_byte_count = len(logical_json.encode("utf-8"))
    if logical_byte_count > MAX_BEDROCK_CUSTOM_METADATA_BYTES:
        raise BedrockPublicationError(
            "custom metadata exceeds the Bedrock + S3 Vectors 1 KB limit"
        )
    if len(values) > MAX_BEDROCK_CUSTOM_METADATA_KEYS:
        raise BedrockPublicationError(
            "custom metadata exceeds the Bedrock + S3 Vectors 35-key limit"
        )

    attributes: dict[str, object] = {}
    for key in sorted(values):
        value = values[key]
        if isinstance(value, str):
            attributes[key] = _metadata_attribute_string(value)
        else:
            attributes[key] = _metadata_attribute_string_list(tuple(value))

    serialized = json.dumps(
        {"metadataAttributes": attributes},
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"
    if len(serialized.encode("utf-8")) > MAX_S3_METADATA_SIDECAR_BYTES:
        raise BedrockPublicationError("metadata sidecar exceeds the S3 10 KB file limit")
    return serialized, logical_byte_count


def build_bedrock_publication_plan(
    registry: KnowledgeSourceRegistry,
    spec: KnowledgeCorpusSpec,
    materialized_documents: tuple[MaterializedKnowledgeDocument, ...],
    *,
    expected_manifest_text: str,
) -> BedrockPublicationPlan:
    """Build nine-object-ready publication evidence only after exact manifest verification."""
    actual_manifest = build_corpus_manifest(registry, spec, materialized_documents)
    actual_manifest_text = serialize_corpus_manifest(actual_manifest)
    if actual_manifest_text != expected_manifest_text:
        raise BedrockPublicationError(
            "fresh corpus replay does not exactly match the checked publication manifest"
        )

    objects: list[BedrockPublicationObject] = []
    for materialized in materialized_documents:
        for chunk in materialized.chunks:
            content_key = (
                f"{BEDROCK_PUBLICATION_PREFIX}/chunks/{chunk.chunk_content_sha256}.txt"
            )
            metadata_key = f"{content_key}.metadata.json"
            metadata_values = _build_metadata_values(
                materialized,
                section_path=chunk.section_path,
            )
            metadata_json, custom_metadata_byte_count = _serialize_metadata(metadata_values)
            objects.append(
                BedrockPublicationObject(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    content_key=content_key,
                    metadata_key=metadata_key,
                    content_text=chunk.text,
                    content_sha256=chunk.chunk_content_sha256,
                    metadata_json=metadata_json,
                    metadata_sha256=_sha256_text(metadata_json),
                    custom_metadata_byte_count=custom_metadata_byte_count,
                    custom_metadata_key_count=len(metadata_values),
                )
            )

    return BedrockPublicationPlan(
        prefix=BEDROCK_PUBLICATION_PREFIX,
        source_manifest_sha256=_sha256_text(expected_manifest_text),
        objects=tuple(objects),
    )


def publication_plan_to_dict(plan: BedrockPublicationPlan) -> dict[str, object]:
    """Project one plan to hash-only evidence without persisting third-party text."""
    return {
        "prefix": plan.prefix,
        "source_manifest_sha256": plan.source_manifest_sha256,
        "objects": [
            {
                "chunk_id": item.chunk_id,
                "document_id": item.document_id,
                "content_key": item.content_key,
                "metadata_key": item.metadata_key,
                "content_utf8_byte_count": len(item.content_text.encode("utf-8")),
                "content_sha256": item.content_sha256,
                "metadata_utf8_byte_count": len(item.metadata_json.encode("utf-8")),
                "metadata_sha256": item.metadata_sha256,
                "custom_metadata_byte_count": item.custom_metadata_byte_count,
                "custom_metadata_key_count": item.custom_metadata_key_count,
            }
            for item in plan.objects
        ],
    }


def serialize_bedrock_publication_plan(plan: BedrockPublicationPlan) -> str:
    """Serialize hash-only publication evidence byte-for-byte deterministically."""
    return json.dumps(
        publication_plan_to_dict(plan),
        indent=2,
        ensure_ascii=False,
    ) + "\n"
