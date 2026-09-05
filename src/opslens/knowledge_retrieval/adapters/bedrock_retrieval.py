"""Bounded Amazon Bedrock Knowledge Base Retrieve adapter."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Protocol, cast

from opslens.knowledge_retrieval.application.bedrock_retrieval import (
    BedrockRetrievalCandidate,
    BedrockRetrievalPage,
    BedrockRetrievalProviderError,
    BedrockRetrievalValidationError,
)

_ALLOWED_RESPONSE_FIELDS = frozenset(
    {"retrievalResults", "nextToken", "guardrailAction", "ResponseMetadata"}
)
_ALLOWED_RESULT_FIELDS = frozenset(
    {"content", "location", "metadata", "score", "documentId"}
)
_ALLOWED_TEXT_CONTENT_FIELDS = frozenset({"type", "text"})
_ALLOWED_S3_LOCATION_FIELDS = frozenset({"type", "s3Location"})
_ALLOWED_S3_FIELDS = frozenset({"uri"})


class BedrockAgentRuntimeClient(Protocol):
    """Minimal boto-compatible runtime client surface required for Retrieve."""

    def retrieve(
        self,
        *,
        knowledgeBaseId: str,
        retrievalQuery: Mapping[str, object],
        retrievalConfiguration: Mapping[str, object],
    ) -> Mapping[str, object]:
        """Invoke one Bedrock Knowledge Base Retrieve request."""
        ...


def _require_mapping(value: object, *, field: str) -> Mapping[str, object]:
    """Require one mapping with only string keys."""
    if not isinstance(value, Mapping):
        raise BedrockRetrievalValidationError(f"{field} must be an object")
    raw = cast(Mapping[object, object], value)
    if any(not isinstance(key, str) for key in raw):
        raise BedrockRetrievalValidationError(f"{field} keys must be strings")
    return cast(Mapping[str, object], raw)


def _require_exact_or_allowed_keys(
    value: Mapping[str, object],
    *,
    allowed: frozenset[str],
    field: str,
) -> None:
    """Reject undocumented provider fields at this frozen adapter boundary."""
    unknown = set(value) - allowed
    if unknown:
        raise BedrockRetrievalValidationError(
            f"{field} contains unsupported fields"
        )


def _require_string(value: object, *, field: str, max_length: int = 4096) -> str:
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


def _require_optional_string(
    value: object,
    *,
    field: str,
    max_length: int = 4096,
) -> str | None:
    """Normalize one optional provider string."""
    if value is None:
        return None
    return _require_string(value, field=field, max_length=max_length)


def _require_nonnegative_int(value: object, *, field: str) -> int:
    """Require one non-negative non-boolean integer."""
    if type(value) is not int or value < 0:
        raise BedrockRetrievalValidationError(f"{field} must be a non-negative integer")
    return value


def _provider_diagnostic(exc: Exception) -> str:
    """Return one content-free provider code or exception type."""
    response = getattr(exc, "response", None)
    if isinstance(response, Mapping):
        typed_response = cast(Mapping[object, object], response)
        error = typed_response.get("Error")
        if isinstance(error, Mapping):
            typed_error = cast(Mapping[object, object], error)
            code = typed_error.get("Code")
            if isinstance(code, str) and code and code == code.strip():
                return f"provider_code={code}"
    return f"provider_type={type(exc).__name__}"


def _parse_candidate(value: object) -> BedrockRetrievalCandidate:
    """Extract one text/S3 candidate without granting provider provenance authority."""
    result = _require_mapping(value, field="retrieval_result")
    _require_exact_or_allowed_keys(
        result,
        allowed=_ALLOWED_RESULT_FIELDS,
        field="retrieval_result",
    )

    content = _require_mapping(result.get("content"), field="retrieval_result.content")
    _require_exact_or_allowed_keys(
        content,
        allowed=_ALLOWED_TEXT_CONTENT_FIELDS,
        field="retrieval_result.content",
    )
    if content.get("type") != "TEXT":
        raise BedrockRetrievalValidationError(
            "retrieval_result.content.type must equal 'TEXT'"
        )
    text = _require_string(
        content.get("text"),
        field="retrieval_result.content.text",
        max_length=100_000,
    )

    location = _require_mapping(
        result.get("location"),
        field="retrieval_result.location",
    )
    _require_exact_or_allowed_keys(
        location,
        allowed=_ALLOWED_S3_LOCATION_FIELDS,
        field="retrieval_result.location",
    )
    if location.get("type") != "S3":
        raise BedrockRetrievalValidationError(
            "retrieval_result.location.type must equal 'S3'"
        )
    s3_location = _require_mapping(
        location.get("s3Location"),
        field="retrieval_result.location.s3Location",
    )
    _require_exact_or_allowed_keys(
        s3_location,
        allowed=_ALLOWED_S3_FIELDS,
        field="retrieval_result.location.s3Location",
    )
    s3_uri = _require_string(
        s3_location.get("uri"),
        field="retrieval_result.location.s3Location.uri",
        max_length=4096,
    )

    metadata = _require_mapping(
        result.get("metadata"),
        field="retrieval_result.metadata",
    )
    score = result.get("score")
    return BedrockRetrievalCandidate(
        text=text,
        s3_uri=s3_uri,
        metadata=metadata,
        relevance_score=cast(float | int | None, score),
    )


def _parse_response(
    response: object,
    *,
    client_elapsed_ms: int,
) -> BedrockRetrievalPage:
    """Parse the current documented Retrieve response into bounded primitive evidence."""
    raw = _require_mapping(response, field="retrieve_response")
    _require_exact_or_allowed_keys(
        raw,
        allowed=_ALLOWED_RESPONSE_FIELDS,
        field="retrieve_response",
    )

    raw_results = raw.get("retrievalResults")
    if not isinstance(raw_results, list):
        raise BedrockRetrievalValidationError(
            "retrieve_response.retrievalResults must be a list"
        )
    candidates = tuple(_parse_candidate(item) for item in cast(list[object], raw_results))

    response_metadata = _require_mapping(
        raw.get("ResponseMetadata"),
        field="retrieve_response.ResponseMetadata",
    )
    request_id = _require_string(
        response_metadata.get("RequestId"),
        field="retrieve_response.ResponseMetadata.RequestId",
        max_length=512,
    )
    retry_attempts_raw = response_metadata.get("RetryAttempts", 0)
    retry_attempts = _require_nonnegative_int(
        retry_attempts_raw,
        field="retrieve_response.ResponseMetadata.RetryAttempts",
    )

    next_token = _require_optional_string(
        raw.get("nextToken"),
        field="retrieve_response.nextToken",
        max_length=2048,
    )
    guardrail_action = _require_optional_string(
        raw.get("guardrailAction"),
        field="retrieve_response.guardrailAction",
        max_length=32,
    )
    return BedrockRetrievalPage(
        candidates=candidates,
        request_id=request_id,
        retry_attempts=retry_attempts,
        client_elapsed_ms=client_elapsed_ms,
        next_token=next_token,
        guardrail_action=guardrail_action,
    )


class BedrockKnowledgeBaseRetrieveAdapter:
    """Execute exactly one semantic-only Bedrock Knowledge Base Retrieve call."""

    def __init__(
        self,
        client: BedrockAgentRuntimeClient,
        *,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._client = client
        self._clock = clock

    def retrieve(
        self,
        *,
        knowledge_base_id: str,
        query: str,
        top_k: int,
    ) -> BedrockRetrievalPage:
        """Send the frozen direct-Retrieve shape and parse one bounded response page."""
        started = self._clock()
        try:
            response = self._client.retrieve(
                knowledgeBaseId=knowledge_base_id,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": top_k,
                    }
                },
            )
        except Exception as exc:
            diagnostic = _provider_diagnostic(exc)
            raise BedrockRetrievalProviderError(
                f"Bedrock Retrieve failed {diagnostic}"
            ) from exc
        elapsed = self._clock() - started
        if elapsed < 0:
            raise BedrockRetrievalValidationError(
                "retrieval client clock produced a negative elapsed duration"
            )
        return _parse_response(
            response,
            client_elapsed_ms=int(round(elapsed * 1000)),
        )
