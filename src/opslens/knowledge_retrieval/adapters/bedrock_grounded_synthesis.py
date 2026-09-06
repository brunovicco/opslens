"""Bounded Bedrock Converse adapter for citation-aware knowledge synthesis."""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from opslens.knowledge_retrieval.adapters.bedrock_synthesis import (
    BedrockConverseClient,
    BedrockSynthesisFailureCategory,
    BedrockSynthesisRuntimeError,
)
from opslens.knowledge_retrieval.application.bedrock_grounded_synthesis import (
    build_bedrock_grounded_synthesis_converse_request,
)
from opslens.knowledge_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MODEL_ID,
    BEDROCK_SYNTHESIS_REGION,
)
from opslens.knowledge_retrieval.application.grounded_synthesis_prompt import (
    build_grounded_synthesis_prompt,
)
from opslens.knowledge_retrieval.application.grounding_contract import (
    GroundedSynthesisOutputError,
    parse_grounded_synthesis_output,
)
from opslens.knowledge_retrieval.domain import (
    GroundedSynthesisRequest,
    GroundedSynthesisResult,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ACCEPTED_STOP_REASON = "end_turn"


def _normalized_text(value: object, *, field: str) -> str:
    """Require one normalized non-empty provider metadata string."""
    if type(value) is not str or not value.strip() or value.strip() != value:
        raise BedrockSynthesisRuntimeError(
            f"{field} must be a normalized non-empty string.",
            category=BedrockSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    return value


def _sha256(value: object, *, field: str) -> str:
    """Require one lowercase SHA-256 digest in metadata-only evidence."""
    normalized = _normalized_text(value, field=field)
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest.")
    return normalized


def _non_negative_int(value: object, *, field: str) -> int:
    """Require one non-negative integer without accepting bool."""
    if type(value) is not int or value < 0:
        raise BedrockSynthesisRuntimeError(
            f"{field} must be a non-negative integer.",
            category=BedrockSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
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


def _required_mapping(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> Mapping[str, object]:
    """Read one required mapping from a Converse response."""
    value = mapping.get(key)
    if not isinstance(value, Mapping):
        raise BedrockSynthesisRuntimeError(
            f"{context}.{key} must be an object.",
            category=BedrockSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    raw = cast(Mapping[object, object], value)
    if any(not isinstance(item, str) for item in raw):
        raise BedrockSynthesisRuntimeError(
            f"{context}.{key} keys must be strings.",
            category=BedrockSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    return cast(Mapping[str, object], raw)


def _required_sequence(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> Sequence[object]:
    """Read one required non-string sequence from a Converse response."""
    value = mapping.get(key)
    if not isinstance(value, Sequence) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        raise BedrockSynthesisRuntimeError(
            f"{context}.{key} must be an array.",
            category=BedrockSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    return cast(Sequence[object], value)


def _provider_identity(response: Mapping[str, object]) -> tuple[str, int]:
    """Extract request ID and SDK retry evidence."""
    metadata = _required_mapping(
        response,
        "ResponseMetadata",
        context="Converse response",
    )
    request_id = _normalized_text(
        metadata.get("RequestId"),
        field="Converse response.ResponseMetadata.RequestId",
    )
    retries = _non_negative_int(
        metadata.get("RetryAttempts", 0),
        field="Converse response.ResponseMetadata.RetryAttempts",
    )
    return request_id, retries


def _stop_reason(response: Mapping[str, object], *, request_id: str) -> str:
    """Accept only natural end-of-turn completion."""
    reason = _normalized_text(
        response.get("stopReason"),
        field="Converse response.stopReason",
    )
    if reason != _ACCEPTED_STOP_REASON:
        raise BedrockSynthesisRuntimeError(
            "Bedrock grounded synthesis stopped before end_turn completion.",
            category=BedrockSynthesisFailureCategory.STOP_REASON,
            request_id=request_id,
            stop_reason=reason,
        )
    return reason


def _extract_single_text_output(response: Mapping[str, object]) -> str:
    """Require exactly one assistant text block and no tool/citation union."""
    output = _required_mapping(response, "output", context="Converse response")
    message = _required_mapping(
        output,
        "message",
        context="Converse response.output",
    )
    role = _normalized_text(
        message.get("role"),
        field="Converse response.output.message.role",
    )
    if role != "assistant":
        raise BedrockSynthesisRuntimeError(
            "Converse grounded synthesis response role must be assistant.",
            category=BedrockSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    content = _required_sequence(
        message,
        "content",
        context="Converse response.output.message",
    )
    if len(content) != 1:
        raise BedrockSynthesisRuntimeError(
            "Converse grounded synthesis must contain exactly one content block.",
            category=BedrockSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    block = content[0]
    if not isinstance(block, Mapping):
        raise BedrockSynthesisRuntimeError(
            "Converse grounded synthesis content block must be an object.",
            category=BedrockSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    typed_block = cast(Mapping[object, object], block)
    if set(typed_block) != {"text"}:
        raise BedrockSynthesisRuntimeError(
            "Converse grounded synthesis content block must contain only text.",
            category=BedrockSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    text = typed_block.get("text")
    if type(text) is not str or not text.strip():
        raise BedrockSynthesisRuntimeError(
            "Converse grounded synthesis content must contain non-empty text.",
            category=BedrockSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    return text


@dataclass(frozen=True, slots=True)
class BedrockGroundedSynthesisInvocationEvidence:
    """Content-free evidence for one successful citation-aware model invocation."""

    model_id: str
    region: str
    request_id: str
    stop_reason: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_read_input_tokens: int
    cache_write_input_tokens: int
    bedrock_latency_ms: int
    client_elapsed_ms: int
    retry_attempts: int
    grounded_request_sha256: str
    prompt_sha256: str
    context_sha256: str
    citation_catalog_sha256: str

    def __post_init__(self) -> None:
        """Reject partial or forged grounded runtime evidence."""
        if self.model_id != BEDROCK_SYNTHESIS_MODEL_ID:
            raise ValueError("model_id must match the frozen synthesis model profile.")
        if self.region != BEDROCK_SYNTHESIS_REGION:
            raise ValueError("region must match the frozen synthesis Region.")
        if self.stop_reason != _ACCEPTED_STOP_REASON:
            raise ValueError("successful grounded synthesis requires end_turn.")
        if not self.request_id or self.request_id.strip() != self.request_id:
            raise ValueError("request_id must be a normalized non-empty string.")

        for field_name, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
            ("total_tokens", self.total_tokens),
            ("cache_read_input_tokens", self.cache_read_input_tokens),
            ("cache_write_input_tokens", self.cache_write_input_tokens),
            ("bedrock_latency_ms", self.bedrock_latency_ms),
            ("client_elapsed_ms", self.client_elapsed_ms),
            ("retry_attempts", self.retry_attempts),
        ):
            if type(value) is not int or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens must equal input_tokens plus output_tokens.")

        for field_name, value in (
            ("grounded_request_sha256", self.grounded_request_sha256),
            ("prompt_sha256", self.prompt_sha256),
            ("context_sha256", self.context_sha256),
            ("citation_catalog_sha256", self.citation_catalog_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{field_name} must be a lowercase SHA-256 digest.")


@dataclass(frozen=True, slots=True)
class BedrockGroundedSynthesisExecution:
    """Bind one grounded result to metadata-only invocation evidence."""

    result: GroundedSynthesisResult
    evidence: BedrockGroundedSynthesisInvocationEvidence

    def __post_init__(self) -> None:
        """Keep result and provider evidence bound to the same grounded request."""
        if type(self.result) is not GroundedSynthesisResult:
            raise TypeError("result must be GroundedSynthesisResult.")
        if type(self.evidence) is not BedrockGroundedSynthesisInvocationEvidence:
            raise TypeError(
                "evidence must be BedrockGroundedSynthesisInvocationEvidence."
            )
        if (
            self.result.grounded_request_sha256
            != self.evidence.grounded_request_sha256
        ):
            raise ValueError(
                "result and invocation evidence must reference the same grounded request."
            )
        if (
            self.result.citation_catalog_sha256
            != self.evidence.citation_catalog_sha256
        ):
            raise ValueError(
                "result and invocation evidence must reference the same citation catalog."
            )


def _parse_invocation_evidence(
    response: Mapping[str, object],
    *,
    request: GroundedSynthesisRequest,
    prompt_sha256: str,
    request_id: str,
    stop_reason: str,
    retry_attempts: int,
    client_elapsed_ms: int,
) -> BedrockGroundedSynthesisInvocationEvidence:
    """Translate bounded Converse metadata into content-free grounded evidence."""
    usage = _required_mapping(response, "usage", context="Converse response")
    metrics = _required_mapping(response, "metrics", context="Converse response")
    return BedrockGroundedSynthesisInvocationEvidence(
        model_id=BEDROCK_SYNTHESIS_MODEL_ID,
        region=BEDROCK_SYNTHESIS_REGION,
        request_id=request_id,
        stop_reason=stop_reason,
        input_tokens=_non_negative_int(
            usage.get("inputTokens"),
            field="Converse response.usage.inputTokens",
        ),
        output_tokens=_non_negative_int(
            usage.get("outputTokens"),
            field="Converse response.usage.outputTokens",
        ),
        total_tokens=_non_negative_int(
            usage.get("totalTokens"),
            field="Converse response.usage.totalTokens",
        ),
        cache_read_input_tokens=_non_negative_int(
            usage.get("cacheReadInputTokens", 0),
            field="Converse response.usage.cacheReadInputTokens",
        ),
        cache_write_input_tokens=_non_negative_int(
            usage.get("cacheWriteInputTokens", 0),
            field="Converse response.usage.cacheWriteInputTokens",
        ),
        bedrock_latency_ms=_non_negative_int(
            metrics.get("latencyMs"),
            field="Converse response.metrics.latencyMs",
        ),
        client_elapsed_ms=client_elapsed_ms,
        retry_attempts=retry_attempts,
        grounded_request_sha256=_sha256(
            request.grounded_request_sha256,
            field="grounded_request_sha256",
        ),
        prompt_sha256=_sha256(prompt_sha256, field="prompt_sha256"),
        context_sha256=_sha256(
            request.synthesis_request.context.context_sha256,
            field="context_sha256",
        ),
        citation_catalog_sha256=_sha256(
            request.citation_catalog.catalog_sha256,
            field="citation_catalog_sha256",
        ),
    )


class BedrockGroundedKnowledgeSynthesizer:
    """Execute exactly one citation-aware bounded Bedrock Converse call."""

    def __init__(
        self,
        client: BedrockConverseClient,
        *,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        """Create the adapter with injected runtime client and monotonic clock."""
        self._client = client
        self._clock = clock

    def synthesize(
        self,
        request: GroundedSynthesisRequest,
    ) -> BedrockGroundedSynthesisExecution:
        """Invoke Bedrock once and admit only valid citation-aware output."""
        if type(request) is not GroundedSynthesisRequest:
            raise TypeError("request must be GroundedSynthesisRequest.")

        prompt = build_grounded_synthesis_prompt(request)
        payload = build_bedrock_grounded_synthesis_converse_request(prompt)
        started = self._clock()
        try:
            response = self._client.converse(**payload)
        except Exception as exc:
            diagnostic = _provider_diagnostic(exc)
            raise BedrockSynthesisRuntimeError(
                f"Bedrock grounded Converse synthesis failed {diagnostic}",
                category=BedrockSynthesisFailureCategory.PROVIDER_INVOCATION,
            ) from exc

        finished = self._clock()
        elapsed = finished - started
        if elapsed < 0:
            raise BedrockSynthesisRuntimeError(
                "Grounded synthesis client clock moved backwards.",
                category=BedrockSynthesisFailureCategory.CLOCK,
            )
        client_elapsed_ms = round(elapsed * 1000)

        request_id, retry_attempts = _provider_identity(response)
        stop_reason = _stop_reason(response, request_id=request_id)
        evidence = _parse_invocation_evidence(
            response,
            request=request,
            prompt_sha256=prompt.prompt_sha256,
            request_id=request_id,
            stop_reason=stop_reason,
            retry_attempts=retry_attempts,
            client_elapsed_ms=client_elapsed_ms,
        )
        output = _extract_single_text_output(response)
        try:
            result = parse_grounded_synthesis_output(output, request=request)
        except GroundedSynthesisOutputError as exc:
            raise BedrockSynthesisRuntimeError(
                "Bedrock grounded output violated deterministic output admission.",
                category=BedrockSynthesisFailureCategory.OUTPUT_CONTRACT,
                request_id=request_id,
                stop_reason=stop_reason,
            ) from exc
        return BedrockGroundedSynthesisExecution(result=result, evidence=evidence)
