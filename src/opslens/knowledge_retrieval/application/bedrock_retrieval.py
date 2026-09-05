"""Application-owned bounded admission for Bedrock Knowledge Base Retrieve evidence."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol, cast
from urllib.parse import urlparse

from opslens.knowledge_retrieval.application.retrieval_catalog import (
    CanonicalRetrievalCatalog,
    CanonicalRetrievalChunk,
    RetrievalCatalogError,
)
from opslens.knowledge_retrieval.domain import (
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
)

_PROVIDER_METADATA_PREFIX = "x-amz-bedrock-kb-"
_REQUIRED_CANONICAL_METADATA_FIELDS = frozenset(
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


class BedrockRetrievalValidationError(ValueError):
    """Raised when bounded retrieval input or provider evidence is not admissible."""


class BedrockRetrievalProviderError(RuntimeError):
    """Raised when the Bedrock runtime transport/provider call fails."""


def _require_trimmed(value: object, *, field: str, max_length: int = 2048) -> str:
    """Require one trimmed bounded non-empty string."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise BedrockRetrievalValidationError(
            f"{field} must be one trimmed non-empty string"
        )
    if len(value) > max_length:
        raise BedrockRetrievalValidationError(
            f"{field} must be at most {max_length} characters"
        )
    return value


def _require_nonnegative_int(value: object, *, field: str) -> int:
    """Require one non-negative non-boolean integer."""
    if type(value) is not int or value < 0:
        raise BedrockRetrievalValidationError(f"{field} must be a non-negative integer")
    return value


def _require_optional_score(value: object) -> float | None:
    """Preserve one finite provider relevance score without confidence semantics."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BedrockRetrievalValidationError("relevance_score must be numeric")
    score = float(value)
    if not math.isfinite(score):
        raise BedrockRetrievalValidationError("relevance_score must be finite")
    return score


def _require_metadata(value: object) -> Mapping[str, object]:
    """Require one provider metadata object with string keys."""
    if not isinstance(value, Mapping):
        raise BedrockRetrievalValidationError("metadata must be an object")
    raw = cast(Mapping[object, object], value)
    if any(not isinstance(key, str) for key in raw):
        raise BedrockRetrievalValidationError("metadata keys must be strings")
    return cast(Mapping[str, object], raw)


def _require_candidates(value: object) -> tuple[BedrockRetrievalCandidate, ...]:
    """Validate one runtime tuple of provider-neutral retrieval candidates."""
    if not isinstance(value, tuple):
        raise BedrockRetrievalValidationError("candidates must be a tuple")
    items = cast(tuple[object, ...], value)
    if any(not isinstance(item, BedrockRetrievalCandidate) for item in items):
        raise BedrockRetrievalValidationError(
            "candidates must contain only BedrockRetrievalCandidate values"
        )
    return cast(tuple[BedrockRetrievalCandidate, ...], items)


def _require_request(value: object) -> RetrievalRequest:
    """Validate one runtime retrieval request."""
    if not isinstance(value, RetrievalRequest):
        raise BedrockRetrievalValidationError("request must be one RetrievalRequest")
    return value


def _require_catalog(value: object) -> CanonicalRetrievalCatalog:
    """Validate one runtime checked-corpus retrieval catalog."""
    if not isinstance(value, CanonicalRetrievalCatalog):
        raise BedrockRetrievalValidationError(
            "catalog must be one CanonicalRetrievalCatalog"
        )
    return value


def _sha256_text(value: str) -> str:
    """Return exact UTF-8 SHA-256 for provider-returned text."""
    return sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class BedrockRetrievalCandidate:
    """Provider-neutral candidate extracted from one Bedrock Retrieve result."""

    text: str
    s3_uri: str
    metadata: Mapping[str, object]
    relevance_score: float | None = None

    def __post_init__(self) -> None:
        """Validate only transport-neutral primitive evidence."""
        text = _require_trimmed(self.text, field="text", max_length=100_000)
        s3_uri = _require_trimmed(self.s3_uri, field="s3_uri", max_length=4096)
        metadata = _require_metadata(self.metadata)
        relevance_score = _require_optional_score(self.relevance_score)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "s3_uri", s3_uri)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "relevance_score", relevance_score)


@dataclass(frozen=True, slots=True)
class BedrockRetrievalPage:
    """One bounded Bedrock Retrieve response page before canonical admission."""

    candidates: tuple[BedrockRetrievalCandidate, ...]
    request_id: str
    retry_attempts: int
    client_elapsed_ms: int
    next_token: str | None = None
    guardrail_action: str | None = None

    def __post_init__(self) -> None:
        """Validate bounded provider runtime evidence without admitting corpus truth."""
        object.__setattr__(self, "candidates", _require_candidates(self.candidates))
        object.__setattr__(
            self,
            "request_id",
            _require_trimmed(self.request_id, field="request_id", max_length=512),
        )
        object.__setattr__(
            self,
            "retry_attempts",
            _require_nonnegative_int(self.retry_attempts, field="retry_attempts"),
        )
        object.__setattr__(
            self,
            "client_elapsed_ms",
            _require_nonnegative_int(self.client_elapsed_ms, field="client_elapsed_ms"),
        )
        if self.next_token is not None:
            object.__setattr__(
                self,
                "next_token",
                _require_trimmed(self.next_token, field="next_token", max_length=2048),
            )
        if self.guardrail_action is not None:
            action = _require_trimmed(
                self.guardrail_action,
                field="guardrail_action",
                max_length=32,
            )
            if action not in {"NONE", "INTERVENED"}:
                raise BedrockRetrievalValidationError(
                    "guardrail_action contains an unsupported value"
                )
            object.__setattr__(self, "guardrail_action", action)


def _require_page(value: object) -> BedrockRetrievalPage:
    """Validate one runtime provider page after crossing the injected port boundary."""
    if not isinstance(value, BedrockRetrievalPage):
        raise BedrockRetrievalValidationError(
            "retrieval port must return one BedrockRetrievalPage"
        )
    return value


@dataclass(frozen=True, slots=True)
class BedrockRetrieveInvocationEvidence:
    """Content-free runtime evidence for one exact Bedrock Retrieve invocation."""

    knowledge_base_id: str
    provider_request_id: str
    retry_attempts: int
    client_elapsed_ms: int
    returned_result_count: int

    def __post_init__(self) -> None:
        """Validate bounded runtime identity and counters."""
        object.__setattr__(
            self,
            "knowledge_base_id",
            _require_trimmed(
                self.knowledge_base_id,
                field="knowledge_base_id",
                max_length=128,
            ),
        )
        object.__setattr__(
            self,
            "provider_request_id",
            _require_trimmed(
                self.provider_request_id,
                field="provider_request_id",
                max_length=512,
            ),
        )
        object.__setattr__(
            self,
            "retry_attempts",
            _require_nonnegative_int(self.retry_attempts, field="retry_attempts"),
        )
        object.__setattr__(
            self,
            "client_elapsed_ms",
            _require_nonnegative_int(self.client_elapsed_ms, field="client_elapsed_ms"),
        )
        object.__setattr__(
            self,
            "returned_result_count",
            _require_nonnegative_int(
                self.returned_result_count,
                field="returned_result_count",
            ),
        )


def _require_retrieval_evidence(value: object) -> RetrievalEvidence:
    """Validate one runtime typed retrieval evidence value."""
    if not isinstance(value, RetrievalEvidence):
        raise BedrockRetrievalValidationError(
            "evidence must be one RetrievalEvidence"
        )
    return value


def _require_invocation(value: object) -> BedrockRetrieveInvocationEvidence:
    """Validate one runtime Bedrock Retrieve invocation evidence value."""
    if not isinstance(value, BedrockRetrieveInvocationEvidence):
        raise BedrockRetrievalValidationError(
            "invocation must be one BedrockRetrieveInvocationEvidence"
        )
    return value


@dataclass(frozen=True, slots=True)
class BedrockRetrieveResult:
    """Admitted typed retrieval evidence plus provider invocation telemetry."""

    evidence: RetrievalEvidence
    invocation: BedrockRetrieveInvocationEvidence

    def __post_init__(self) -> None:
        """Require exact provider/backend consistency."""
        evidence = _require_retrieval_evidence(self.evidence)
        invocation = _require_invocation(self.invocation)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "invocation", invocation)
        if evidence.backend is not RetrievalBackend.BEDROCK_KNOWLEDGE_BASE:
            raise BedrockRetrievalValidationError(
                "evidence backend must be bedrock_knowledge_base"
            )
        if evidence.backend_reference != invocation.knowledge_base_id:
            raise BedrockRetrievalValidationError(
                "evidence backend reference must match invocation knowledge base"
            )
        if len(evidence.chunks) != invocation.returned_result_count:
            raise BedrockRetrievalValidationError(
                "invocation result count must match admitted chunk count"
            )


class BedrockRetrievalPort(Protocol):
    """Minimum provider authority required by the Gate 7.4 retrieval runtime."""

    def retrieve(
        self,
        *,
        knowledge_base_id: str,
        query: str,
        top_k: int,
    ) -> BedrockRetrievalPage:
        """Return one bounded semantic-only retrieval page."""
        ...


def _reject_unimplemented_filters(request: RetrievalRequest) -> None:
    """Fail closed rather than silently dropping Gate 7.1 typed scope."""
    if (
        request.source_types
        or request.vulnerability_ids
        or request.ecosystem is not None
        or request.package_name is not None
    ):
        raise BedrockRetrievalValidationError(
            "typed retrieval filters are not implemented in the first Gate 7.4 slice"
        )


def _s3_content_key(*, s3_uri: str, expected_bucket: str) -> str:
    """Resolve one exact expected S3 source URI to a relative content key."""
    parsed = urlparse(s3_uri)
    if (
        parsed.scheme != "s3"
        or parsed.netloc != expected_bucket
        or parsed.params
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/")
    ):
        raise BedrockRetrievalValidationError(
            "retrieval location must be one exact expected S3 source URI"
        )
    key = parsed.path[1:]
    if not key or key != key.strip() or "//" in key:
        raise BedrockRetrievalValidationError(
            "retrieval S3 location contains an invalid object key"
        )
    return key


def _expected_metadata(canonical: CanonicalRetrievalChunk) -> dict[str, object]:
    """Project canonical metadata values from checked corpus authority only."""
    return {
        "source_id": canonical.source_id,
        "source_type": canonical.source_type.value,
        "canonical_uri": canonical.canonical_uri,
        "document_id": canonical.document_id,
        "content_sha256": canonical.document_content_sha256,
        "title": canonical.title,
        "section_path": list(canonical.section_path),
    }


def _validate_metadata(
    *,
    metadata: Mapping[str, object],
    canonical: CanonicalRetrievalChunk,
    s3_uri: str,
    expected_data_source_id: str,
) -> None:
    """Require canonical equality while provider-reserved keys stay non-authoritative."""
    expected = _expected_metadata(canonical)
    for field in _REQUIRED_CANONICAL_METADATA_FIELDS:
        if field not in metadata:
            raise BedrockRetrievalValidationError(
                f"retrieval metadata is missing required canonical field {field!r}"
            )
        if metadata[field] != expected[field]:
            raise BedrockRetrievalValidationError(
                f"retrieval metadata field {field!r} disagrees with checked corpus evidence"
            )

    unknown = {
        field
        for field in metadata
        if field not in expected and not field.startswith(_PROVIDER_METADATA_PREFIX)
    }
    if unknown:
        raise BedrockRetrievalValidationError(
            "retrieval metadata contains unsupported non-provider fields"
        )

    source_uri = metadata.get("x-amz-bedrock-kb-source-uri")
    if source_uri is not None and source_uri != s3_uri:
        raise BedrockRetrievalValidationError(
            "provider source URI metadata disagrees with retrieval location"
        )
    data_source_id = metadata.get("x-amz-bedrock-kb-data-source-id")
    if data_source_id is not None and data_source_id != expected_data_source_id:
        raise BedrockRetrievalValidationError(
            "provider data source metadata disagrees with configured data source"
        )


def _admit_candidate(
    candidate: BedrockRetrievalCandidate,
    *,
    rank: int,
    catalog: CanonicalRetrievalCatalog,
    expected_bucket: str,
    expected_data_source_id: str,
) -> RetrievedChunk:
    """Admit one result only after S3, hash, manifest, and metadata cross-checks."""
    key = _s3_content_key(s3_uri=candidate.s3_uri, expected_bucket=expected_bucket)
    try:
        canonical = catalog.resolve_content_key(key)
    except RetrievalCatalogError as exc:
        raise BedrockRetrievalValidationError(
            "retrieval location does not resolve to checked canonical corpus evidence"
        ) from exc

    text_digest = _sha256_text(candidate.text)
    if text_digest != canonical.chunk_content_sha256:
        raise BedrockRetrievalValidationError(
            "retrieved text SHA-256 disagrees with content-addressed canonical chunk"
        )
    if len(candidate.text.encode("utf-8")) != canonical.content_utf8_byte_count:
        raise BedrockRetrievalValidationError(
            "retrieved text byte count disagrees with checked canonical chunk"
        )

    _validate_metadata(
        metadata=candidate.metadata,
        canonical=canonical,
        s3_uri=candidate.s3_uri,
        expected_data_source_id=expected_data_source_id,
    )

    return RetrievedChunk.from_text(
        chunk_id=canonical.chunk_id,
        document_id=canonical.document_id,
        source_id=canonical.source_id,
        source_type=canonical.source_type,
        canonical_uri=canonical.canonical_uri,
        document_content_sha256=canonical.document_content_sha256,
        text=candidate.text,
        rank=rank,
        relevance_score=candidate.relevance_score,
        title=canonical.title,
        section_path=canonical.section_path,
    )


def run_bounded_retrieve(
    port: BedrockRetrievalPort,
    *,
    request: RetrievalRequest,
    catalog: CanonicalRetrievalCatalog,
    knowledge_base_id: str,
    expected_source_bucket: str,
    expected_data_source_id: str,
) -> BedrockRetrieveResult:
    """Run one semantic-only Retrieve call and admit only checked canonical evidence."""
    typed_request = _require_request(request)
    typed_catalog = _require_catalog(catalog)
    _reject_unimplemented_filters(typed_request)
    kb_id = _require_trimmed(
        knowledge_base_id,
        field="knowledge_base_id",
        max_length=128,
    )
    bucket = _require_trimmed(
        expected_source_bucket,
        field="expected_source_bucket",
        max_length=255,
    )
    data_source_id = _require_trimmed(
        expected_data_source_id,
        field="expected_data_source_id",
        max_length=128,
    )

    page = _require_page(
        port.retrieve(
            knowledge_base_id=kb_id,
            query=typed_request.query,
            top_k=typed_request.top_k,
        )
    )
    if page.next_token is not None:
        raise BedrockRetrievalValidationError(
            "paginated Retrieve responses are not admitted by Gate 7.4 v1"
        )
    if page.guardrail_action == "INTERVENED":
        raise BedrockRetrievalValidationError(
            "guardrail-intervened retrieval responses are not admitted"
        )
    if len(page.candidates) > typed_request.top_k:
        raise BedrockRetrievalValidationError(
            "provider returned more results than request.top_k"
        )

    admitted = tuple(
        _admit_candidate(
            candidate,
            rank=rank,
            catalog=typed_catalog,
            expected_bucket=bucket,
            expected_data_source_id=data_source_id,
        )
        for rank, candidate in enumerate(page.candidates, start=1)
    )

    evidence = RetrievalEvidence(
        retrieval_id=f"bedrock-retrieve:{page.request_id}",
        request=typed_request,
        chunks=admitted,
        backend=RetrievalBackend.BEDROCK_KNOWLEDGE_BASE,
        backend_reference=kb_id,
    )
    invocation = BedrockRetrieveInvocationEvidence(
        knowledge_base_id=kb_id,
        provider_request_id=page.request_id,
        retry_attempts=page.retry_attempts,
        client_elapsed_ms=page.client_elapsed_ms,
        returned_result_count=len(admitted),
    )
    return BedrockRetrieveResult(evidence=evidence, invocation=invocation)
