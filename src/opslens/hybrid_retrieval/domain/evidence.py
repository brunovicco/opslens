"""Provider-independent evidence contracts for deterministic hybrid composition."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import TypeAlias, cast
from urllib.parse import urlparse

from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.models import (
    CompletenessSemantics,
    EvidenceClass,
    EvidenceNeed,
    HybridRoute,
    HybridRouteDecision,
)

HYBRID_EVIDENCE_CONTRACT_VERSION = "hybrid-evidence:v1"

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

StructuredScalar: TypeAlias = str | int | float | bool | None


class StructuredEvidenceAuthority(StrEnum):
    """Deterministic authorities allowed to contribute structured evidence in v1."""

    REPOSITORY_ANALYSIS = "repository_analysis"
    RISK_POLICY = "risk_policy"
    SEMANTIC_QUERY = "semantic_query"


_ALLOWED_STRUCTURED_AUTHORITIES_BY_NEED: dict[
    EvidenceNeed, frozenset[StructuredEvidenceAuthority]
] = {
    EvidenceNeed.VULNERABILITY_FACTS: frozenset(
        {
            StructuredEvidenceAuthority.REPOSITORY_ANALYSIS,
            StructuredEvidenceAuthority.SEMANTIC_QUERY,
        }
    ),
    EvidenceNeed.RISK_PRIORITY: frozenset({StructuredEvidenceAuthority.RISK_POLICY}),
}

_EVIDENCE_CLASS_ORDER = {
    EvidenceClass.STRUCTURED: 0,
    EvidenceClass.SEMANTIC: 1,
}


def _require_runtime_instance(value: object, expected_type: type[object], label: str) -> None:
    """Validate untrusted runtime values without weakening public annotations."""
    if not isinstance(value, expected_type):
        raise HybridRetrievalValidationError(f"{label} has an unsupported value.")


def _normalize_required_text(value: object, label: str) -> str:
    """Return one trimmed non-empty string or fail closed."""
    if not isinstance(value, str):
        raise HybridRetrievalValidationError(f"{label} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise HybridRetrievalValidationError(f"{label} cannot be blank.")
    return normalized


def _normalize_optional_text(value: object, label: str) -> str | None:
    """Normalize an optional string while rejecting explicit blank values."""
    if value is None:
        return None
    return _normalize_required_text(value, label)


def _validate_sha256(value: object, label: str) -> str:
    """Require one lowercase hexadecimal SHA-256 digest."""
    normalized = _normalize_required_text(value, label)
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise HybridRetrievalValidationError(
            f"{label} must be a 64-character lowercase hexadecimal SHA-256 digest."
        )
    return normalized


def _sha256_text(text: str) -> str:
    """Return the canonical UTF-8 SHA-256 digest for one text payload."""
    return sha256(text.encode("utf-8")).hexdigest()


def _validate_https_uri(value: object, label: str) -> str:
    """Require one absolute HTTPS provenance URI."""
    normalized = _normalize_required_text(value, label)
    parsed = urlparse(normalized)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HybridRetrievalValidationError(f"{label} must be an absolute HTTPS URI.")
    return normalized


def _canonical_sha256(payload: object) -> str:
    """Hash one canonical JSON payload with stable ordering and separators."""
    canonical = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_structured_scalar(value: object) -> StructuredScalar:
    """Admit only JSON-stable scalar values into structured evidence rows."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise HybridRetrievalValidationError("structured field floats must be finite.")
        return value
    raise HybridRetrievalValidationError(
        "structured field values must be string, integer, finite float, boolean, or null."
    )


def _normalize_section_path(value: object) -> tuple[str, ...]:
    """Validate one ordered section path without silently inventing hierarchy."""
    if not isinstance(value, tuple):
        raise HybridRetrievalValidationError("section_path must be a tuple.")
    raw_values = cast(tuple[object, ...], value)
    normalized = tuple(
        _normalize_required_text(item, "section_path item") for item in raw_values
    )
    if len(set(normalized)) != len(normalized):
        raise HybridRetrievalValidationError("section_path cannot contain duplicates.")
    return normalized


@dataclass(frozen=True, slots=True)
class StructuredEvidenceField:
    """One canonical field/value pair inside already-validated structured evidence."""

    name: str
    value: StructuredScalar

    def __post_init__(self) -> None:
        """Validate the field name and preserve only JSON-stable scalar values."""
        object.__setattr__(self, "name", _normalize_required_text(self.name, "field name"))
        object.__setattr__(self, "value", _normalize_structured_scalar(self.value))

    def to_payload(self) -> dict[str, StructuredScalar]:
        """Return a canonical JSON-ready field payload."""
        return {"name": self.name, "value": self.value}


def _normalize_structured_fields(value: object) -> tuple[StructuredEvidenceField, ...]:
    """Validate, de-duplicate, and canonically order one structured row."""
    if not isinstance(value, tuple):
        raise HybridRetrievalValidationError("fields must be a tuple.")
    raw_values = cast(tuple[object, ...], value)
    if not raw_values:
        raise HybridRetrievalValidationError("structured evidence rows require at least one field.")
    if any(not isinstance(item, StructuredEvidenceField) for item in raw_values):
        raise HybridRetrievalValidationError(
            "fields must contain only StructuredEvidenceField values."
        )
    typed_values = cast(tuple[StructuredEvidenceField, ...], raw_values)
    names = tuple(item.name for item in typed_values)
    if len(set(names)) != len(names):
        raise HybridRetrievalValidationError("structured evidence field names must be unique.")
    return tuple(sorted(typed_values, key=lambda item: item.name))


@dataclass(frozen=True, slots=True)
class StructuredEvidenceRow:
    """One content-addressed structured row whose authority remains explicit."""

    evidence_need: EvidenceNeed
    authority: StructuredEvidenceAuthority
    source_artifact_id: str
    source_artifact_sha256: str
    row_key: str
    fields: tuple[StructuredEvidenceField, ...]

    def __post_init__(self) -> None:
        """Reject authority laundering and freeze canonical structured content."""
        _require_runtime_instance(self.evidence_need, EvidenceNeed, "evidence_need")
        _require_runtime_instance(self.authority, StructuredEvidenceAuthority, "authority")
        allowed_authorities = _ALLOWED_STRUCTURED_AUTHORITIES_BY_NEED.get(self.evidence_need)
        if allowed_authorities is None:
            raise HybridRetrievalValidationError(
                "structured evidence cannot satisfy this evidence need."
            )
        if self.authority not in allowed_authorities:
            raise HybridRetrievalValidationError(
                "structured evidence authority is not authorized for this evidence need."
            )
        object.__setattr__(
            self,
            "source_artifact_id",
            _normalize_required_text(self.source_artifact_id, "source_artifact_id"),
        )
        object.__setattr__(
            self,
            "source_artifact_sha256",
            _validate_sha256(self.source_artifact_sha256, "source_artifact_sha256"),
        )
        object.__setattr__(
            self,
            "row_key",
            _normalize_required_text(self.row_key, "row_key"),
        )
        object.__setattr__(self, "fields", _normalize_structured_fields(self.fields))

    @property
    def evidence_sha256(self) -> str:
        """Return exact content identity for this structured evidence row."""
        return _canonical_sha256(
            {
                "authority": self.authority.value,
                "contract_version": HYBRID_EVIDENCE_CONTRACT_VERSION,
                "evidence_need": self.evidence_need.value,
                "fields": [field.to_payload() for field in self.fields],
                "row_key": self.row_key,
                "source_artifact_id": self.source_artifact_id,
                "source_artifact_sha256": self.source_artifact_sha256,
            }
        )

    @property
    def evidence_id(self) -> str:
        """Return the versioned content-addressed structured evidence identifier."""
        return f"hybrid-structured:v1:{self.evidence_sha256}"


@dataclass(frozen=True, slots=True)
class SemanticEvidenceChunk:
    """One admitted semantic chunk projected with complete source provenance."""

    retrieval_id: str
    chunk_id: str
    document_id: str
    source_id: str
    source_type: str
    canonical_uri: str
    document_content_sha256: str
    chunk_content_sha256: str
    text: str
    rank: int
    relevance_score: float | None = None
    title: str | None = None
    section_path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Reject malformed semantic provenance, content identity, rank, or score."""
        for field_name in (
            "retrieval_id",
            "chunk_id",
            "document_id",
            "source_id",
            "source_type",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalize_required_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "canonical_uri",
            _validate_https_uri(self.canonical_uri, "canonical_uri"),
        )
        object.__setattr__(
            self,
            "document_content_sha256",
            _validate_sha256(self.document_content_sha256, "document_content_sha256"),
        )
        object.__setattr__(self, "text", _normalize_required_text(self.text, "text"))
        chunk_digest = _validate_sha256(self.chunk_content_sha256, "chunk_content_sha256")
        if chunk_digest != _sha256_text(self.text):
            raise HybridRetrievalValidationError(
                "chunk_content_sha256 must match the canonical UTF-8 semantic text."
            )
        object.__setattr__(self, "chunk_content_sha256", chunk_digest)
        if type(self.rank) is not int or self.rank < 1:
            raise HybridRetrievalValidationError("semantic chunk rank must be positive.")
        if self.relevance_score is not None:
            if isinstance(self.relevance_score, bool) or not isinstance(
                self.relevance_score, (int, float)
            ):
                raise HybridRetrievalValidationError("relevance_score must be numeric.")
            normalized_score = float(self.relevance_score)
            if not math.isfinite(normalized_score):
                raise HybridRetrievalValidationError("relevance_score must be finite.")
            object.__setattr__(self, "relevance_score", normalized_score)
        object.__setattr__(self, "title", _normalize_optional_text(self.title, "title"))
        object.__setattr__(self, "section_path", _normalize_section_path(self.section_path))

    @property
    def evidence_need(self) -> EvidenceNeed:
        """Return the only semantic evidence need authorized by the v1 contract."""
        return EvidenceNeed.REMEDIATION_GUIDANCE

    @property
    def evidence_sha256(self) -> str:
        """Return exact content identity for this semantic evidence projection."""
        return _canonical_sha256(
            {
                "canonical_uri": self.canonical_uri,
                "chunk_content_sha256": self.chunk_content_sha256,
                "chunk_id": self.chunk_id,
                "contract_version": HYBRID_EVIDENCE_CONTRACT_VERSION,
                "document_content_sha256": self.document_content_sha256,
                "document_id": self.document_id,
                "evidence_need": self.evidence_need.value,
                "rank": self.rank,
                "relevance_score": self.relevance_score,
                "retrieval_id": self.retrieval_id,
                "section_path": list(self.section_path),
                "source_id": self.source_id,
                "source_type": self.source_type,
                "text": self.text,
                "title": self.title,
            }
        )

    @property
    def evidence_id(self) -> str:
        """Return the versioned content-addressed semantic evidence identifier."""
        return f"hybrid-semantic:v1:{self.evidence_sha256}"


def _normalize_structured_rows(value: object) -> tuple[StructuredEvidenceRow, ...]:
    """Validate and canonically order structured evidence rows."""
    if not isinstance(value, tuple):
        raise HybridRetrievalValidationError("structured_evidence must be a tuple.")
    raw_values = cast(tuple[object, ...], value)
    if any(not isinstance(item, StructuredEvidenceRow) for item in raw_values):
        raise HybridRetrievalValidationError(
            "structured_evidence must contain only StructuredEvidenceRow values."
        )
    typed_values = cast(tuple[StructuredEvidenceRow, ...], raw_values)
    evidence_ids = tuple(item.evidence_id for item in typed_values)
    if len(set(evidence_ids)) != len(evidence_ids):
        raise HybridRetrievalValidationError("structured evidence IDs must be unique.")
    return tuple(
        sorted(
            typed_values,
            key=lambda item: (
                item.evidence_need.value,
                item.authority.value,
                item.source_artifact_id,
                item.row_key,
                item.evidence_id,
            ),
        )
    )


def _normalize_semantic_chunks(value: object) -> tuple[SemanticEvidenceChunk, ...]:
    """Validate and canonically order semantic evidence chunks."""
    if not isinstance(value, tuple):
        raise HybridRetrievalValidationError("semantic_evidence must be a tuple.")
    raw_values = cast(tuple[object, ...], value)
    if any(not isinstance(item, SemanticEvidenceChunk) for item in raw_values):
        raise HybridRetrievalValidationError(
            "semantic_evidence must contain only SemanticEvidenceChunk values."
        )
    typed_values = cast(tuple[SemanticEvidenceChunk, ...], raw_values)
    evidence_ids = tuple(item.evidence_id for item in typed_values)
    if len(set(evidence_ids)) != len(evidence_ids):
        raise HybridRetrievalValidationError("semantic evidence IDs must be unique.")
    return tuple(
        sorted(
            typed_values,
            key=lambda item: (item.retrieval_id, item.rank, item.chunk_id, item.evidence_id),
        )
    )


@dataclass(frozen=True, slots=True)
class EvidenceClassProvenance:
    """Canonical content-addressed evidence membership for one authority class."""

    evidence_class: EvidenceClass
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Require one recognized class and one non-empty unique evidence-ID tuple."""
        _require_runtime_instance(self.evidence_class, EvidenceClass, "evidence_class")
        if not isinstance(self.evidence_ids, tuple):
            raise HybridRetrievalValidationError("evidence_ids must be a tuple.")
        raw_ids = cast(tuple[object, ...], self.evidence_ids)
        normalized_ids = tuple(
            _normalize_required_text(item, "evidence_id") for item in raw_ids
        )
        if not normalized_ids:
            raise HybridRetrievalValidationError("evidence class provenance cannot be empty.")
        if len(set(normalized_ids)) != len(normalized_ids):
            raise HybridRetrievalValidationError("evidence class provenance IDs must be unique.")
        object.__setattr__(self, "evidence_ids", tuple(sorted(normalized_ids)))


@dataclass(frozen=True, slots=True)
class HybridEvidenceEnvelope:
    """Complete evidence envelope admitted under one deterministic route decision."""

    authority_decision: HybridRouteDecision
    structured_evidence: tuple[StructuredEvidenceRow, ...] = ()
    semantic_evidence: tuple[SemanticEvidenceChunk, ...] = ()

    def __post_init__(self) -> None:
        """Enforce route, class, need, provenance, and ALL_REQUIRED completeness."""
        _require_runtime_instance(
            self.authority_decision,
            HybridRouteDecision,
            "authority_decision",
        )
        if self.authority_decision.route is HybridRoute.UNSUPPORTED:
            raise HybridRetrievalValidationError(
                "unsupported route decisions cannot produce a hybrid evidence envelope."
            )
        if self.authority_decision.completeness is not CompletenessSemantics.ALL_REQUIRED:
            raise HybridRetrievalValidationError(
                "supported hybrid evidence envelopes require ALL_REQUIRED semantics."
            )

        structured = _normalize_structured_rows(self.structured_evidence)
        semantic = _normalize_semantic_chunks(self.semantic_evidence)
        object.__setattr__(self, "structured_evidence", structured)
        object.__setattr__(self, "semantic_evidence", semantic)

        required_classes = frozenset(self.authority_decision.required_evidence_classes)
        if EvidenceClass.STRUCTURED in required_classes and not structured:
            raise HybridRetrievalValidationError(
                "required structured evidence is missing from the envelope."
            )
        if EvidenceClass.STRUCTURED not in required_classes and structured:
            raise HybridRetrievalValidationError(
                "structured evidence is not authorized by the route decision."
            )
        if EvidenceClass.SEMANTIC in required_classes and not semantic:
            raise HybridRetrievalValidationError(
                "required semantic evidence is missing from the envelope."
            )
        if EvidenceClass.SEMANTIC not in required_classes and semantic:
            raise HybridRetrievalValidationError(
                "semantic evidence is not authorized by the route decision."
            )

        if semantic:
            retrieval_ids = {item.retrieval_id for item in semantic}
            if len(retrieval_ids) != 1:
                raise HybridRetrievalValidationError(
                    "v1 semantic evidence must come from exactly one retrieval operation."
                )
            actual_ranks = tuple(item.rank for item in semantic)
            expected_ranks = tuple(range(1, len(semantic) + 1))
            if actual_ranks != expected_ranks:
                raise HybridRetrievalValidationError(
                    "v1 semantic evidence ranks must be contiguous and ordered from 1."
                )

        requested_needs = frozenset(self.authority_decision.evidence_needs)
        satisfied_needs = {item.evidence_need for item in structured}
        if semantic:
            satisfied_needs.add(EvidenceNeed.REMEDIATION_GUIDANCE)
        if satisfied_needs != set(requested_needs):
            raise HybridRetrievalValidationError(
                "envelope evidence must satisfy exactly every authorized evidence need."
            )

    @property
    def satisfied_evidence_needs(self) -> tuple[EvidenceNeed, ...]:
        """Return the canonically ordered needs proven complete by admitted evidence."""
        return self.authority_decision.evidence_needs

    @property
    def completeness(self) -> CompletenessSemantics:
        """Return the frozen completeness semantics governing this complete envelope."""
        return self.authority_decision.completeness

    @property
    def provenance_by_class(self) -> tuple[EvidenceClassProvenance, ...]:
        """Return deterministic evidence membership separated by authority class."""
        provenance: list[EvidenceClassProvenance] = []
        if self.structured_evidence:
            provenance.append(
                EvidenceClassProvenance(
                    evidence_class=EvidenceClass.STRUCTURED,
                    evidence_ids=tuple(item.evidence_id for item in self.structured_evidence),
                )
            )
        if self.semantic_evidence:
            provenance.append(
                EvidenceClassProvenance(
                    evidence_class=EvidenceClass.SEMANTIC,
                    evidence_ids=tuple(item.evidence_id for item in self.semantic_evidence),
                )
            )
        return tuple(sorted(provenance, key=lambda item: _EVIDENCE_CLASS_ORDER[item.evidence_class]))

    @property
    def identity_sha256(self) -> str:
        """Return exact content identity for the admitted hybrid evidence envelope."""
        return _canonical_sha256(
            {
                "authority_decision_id": self.authority_decision.decision_id,
                "completeness": self.completeness.value,
                "contract_version": HYBRID_EVIDENCE_CONTRACT_VERSION,
                "satisfied_evidence_needs": [
                    need.value for need in self.satisfied_evidence_needs
                ],
                "semantic_evidence_ids": [
                    item.evidence_id for item in self.semantic_evidence
                ],
                "structured_evidence_ids": [
                    item.evidence_id for item in self.structured_evidence
                ],
            }
        )

    @property
    def envelope_id(self) -> str:
        """Return a versioned content-addressed identifier for audit/evaluation use."""
        return f"{HYBRID_EVIDENCE_CONTRACT_VERSION}:{self.identity_sha256}"
