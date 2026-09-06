"""Bounded Amazon Bedrock Converse adapter for hybrid synthesis."""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, cast

from opslens.hybrid_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MODEL_ID,
    BEDROCK_SYNTHESIS_REGION,
    build_bedrock_hybrid_synthesis_converse_request,
)
from opslens.hybrid_retrieval.application.synthesis import (
    HybridSynthesisOutputError,
    parse_hybrid_synthesis_output,
)
from opslens.hybrid_retrieval.application.synthesis_prompt import (
    build_hybrid_synthesis_prompt,
)
from opslens.hybrid_retrieval.domain.synthesis import (
    HybridSynthesisRequest,
    HybridSynthesisResult,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ACCEPTED_STOP_REASON = "end_turn"


class BedrockHybridSynthesisFailureCategory(StrEnum):
    """Content-free categories for provider/runtime hybrid synthesis failures."""

    PROVIDER_INVOCATION = "provider_invocation"
    RESPONSE_CONTRACT = "response_contract"
    STOP_REASON = "stop_reason"
    OUTPUT_CONTRACT = "output_contract"
    CLOCK = "clock"


class BedrockHybridSynthesisRuntimeError(RuntimeError):
    """Raised when Bedrock execution violates the bounded hybrid boundary."""

    def __init__(
        self,
        message: str,
        *,
        category: BedrockHybridSynthesisFailureCategory,
        request_id: str | None = None,
        stop_reason: str | None = None,
    ) -> None:
        """Preserve bounded diagnostics without retaining prompt/output content."""
        self.category = category
        self.request_id = request_id
        self.stop_reason = stop_reason
        super().__init__(message)


class BedrockHybridConverseClient(Protocol):
    """Define only the non-streaming Bedrock capability required by Gate 8.4."""

    def converse(self, **request: object) -> Mapping[str, object]:
        """Invoke one non-streaming Converse request."""
        ...


def _admit_synthesis_result(value: object) -> HybridSynthesisResult:
    """Admit one hybrid result at the runtime evidence binding boundary."""
    if not isinstance(value, HybridSynthesisResult):
        raise TypeError("result must be HybridSynthesisResult.")
    return value


def _admit_invocation_evidence(
    value: object,
) -> BedrockHybridSynthesisInvocationEvidence:
    """Admit one runtime metadata record at the execution binding boundary."""
    if not isinstance(value, BedrockHybridSynthesisInvocationEvidence):
        raise TypeError("evidence must be BedrockHybridSynthesisInvocationEvidence.")
    return value


def _admit_synthesis_request(value: object) -> HybridSynthesisRequest:
    """Admit one exact request before invoking the provider."""
    if not isinstance(value, HybridSynthesisRequest):
        raise TypeError("request must be HybridSynthesisRequest.")
    return value


def _normalized_text(value: object, *, field: str) -> str:
    """Require one normalized non-empty provider metadata string."""
    if not isinstance(value, str) or not value.strip() or value.strip() != value:
        raise BedrockHybridSynthesisRuntimeError(
            f"{field} must be a normalized non-empty string.",
            category=BedrockHybridSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    """Require one non-negative integer without accepting bool."""
    if type(value) is not int or value < 0:
        raise BedrockHybridSynthesisRuntimeError(
            f"{field} must be a non-negative integer.",
            category=BedrockHybridSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    return value


def _provider_diagnostic(exc: Exception) -> str:
    """Return one bounded provider code or exception type."""
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
        raise BedrockHybridSynthesisRuntimeError(
            f"{context}.{key} must be an object.",
            category=BedrockHybridSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    raw = cast(Mapping[object, object], value)
    if any(not isinstance(item, str) for item in raw):
        raise BedrockHybridSynthesisRuntimeError(
            f"{context}.{key} keys must be strings.",
            category=BedrockHybridSynthesisFailureCategory.RESPONSE_CONTRACT,
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
        raise BedrockHybridSynthesisRuntimeError(
            f"{context}.{key} must be an array.",
            category=BedrockHybridSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    return cast(Sequence[object], value)


def _provider_identity(response: Mapping[str, object]) -> tuple[str, int]:
    """Extract exact request ID and SDK retry evidence."""
    metadata = _required_mapping(
        response,
        "ResponseMetadata",
        context="Converse response",
    )
    request_id = _normalized_text(
        metadata.get("RequestId"),
        field="Converse response.ResponseMetadata.RequestId",
    )
    retry_attempts = _non_negative_int(
        metadata.get("RetryAttempts", 0),
        field="Converse response.ResponseMetadata.RetryAttempts",
    )
    return request_id, retry_attempts


def _stop_reason(response: Mapping[str, object], *, request_id: str) -> str:
    """Accept only natural end-of-turn completion."""
    reason = _normalized_text(
        response.get("stopReason"),
        field="Converse response.stopReason",
    )
    if reason != _ACCEPTED_STOP_REASON:
        raise BedrockHybridSynthesisRuntimeError(
            "Bedrock hybrid synthesis stopped before end_turn completion.",
            category=BedrockHybridSynthesisFailureCategory.STOP_REASON,
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
        raise BedrockHybridSynthesisRuntimeError(
            "Converse hybrid synthesis response role must be assistant.",
            category=BedrockHybridSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    content = _required_sequence(
        message,
        "content",
        context="Converse response.output.message",
    )
    if len(content) != 1:
        raise BedrockHybridSynthesisRuntimeError(
            "Converse hybrid synthesis must contain exactly one content block.",
            category=BedrockHybridSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    block = content[0]
    if not isinstance(block, Mapping):
        raise BedrockHybridSynthesisRuntimeError(
            "Converse hybrid synthesis content block must be an object.",
            category=BedrockHybridSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    typed_block = cast(Mapping[object, object], block)
    if set(typed_block) != {"text"}:
        raise BedrockHybridSynthesisRuntimeError(
            "Converse hybrid synthesis content block must contain only text.",
            category=BedrockHybridSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    text = typed_block.get("text")
    if not isinstance(text, str) or not text.strip():
        raise BedrockHybridSynthesisRuntimeError(
            "Converse hybrid synthesis content must contain non-empty text.",
            category=BedrockHybridSynthesisFailureCategory.RESPONSE_CONTRACT,
        )
    return text


@dataclass(frozen=True, slots=True)
class BedrockHybridSynthesisInvocationEvidence:
    """Content-free evidence for one successful bounded hybrid model invocation."""

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
    request_sha256: str
    prompt_sha256: str
    envelope_sha256: str
    structured_catalog_sha256: str
    semantic_catalog_sha256: str

    def __post_init__(self) -> None:
        """Reject partial or forged runtime evidence."""
        if self.model_id != BEDROCK_SYNTHESIS_MODEL_ID:
            raise ValueError("model_id must match the frozen Phase 7 synthesis profile.")
        if self.region != BEDROCK_SYNTHESIS_REGION:
            raise ValueError("region must match the frozen synthesis Region.")
        if self.stop_reason != _ACCEPTED_STOP_REASON:
            raise ValueError("successful hybrid synthesis requires end_turn.")
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
            ("request_sha256", self.request_sha256),
            ("prompt_sha256", self.prompt_sha256),
            ("envelope_sha256", self.envelope_sha256),
            ("structured_catalog_sha256", self.structured_catalog_sha256),
            ("semantic_catalog_sha256", self.semantic_catalog_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{field_name} must be a lowercase SHA-256 digest.")


@dataclass(frozen=True, slots=True)
class BedrockHybridSynthesisExecution:
    """Bind one admitted hybrid result to metadata-only invocation evidence."""

    result: HybridSynthesisResult
    evidence: BedrockHybridSynthesisInvocationEvidence

    def __post_init__(self) -> None:
        """Keep output and provider evidence bound to the same exact request."""
        result = _admit_synthesis_result(self.result)
        evidence = _admit_invocation_evidence(self.evidence)
        if result.request_sha256 != evidence.request_sha256:
            raise ValueError("result and invocation evidence must reference the same request.")


def _parse_invocation_evidence(
    response: Mapping[str, object],
    *,
    request: HybridSynthesisRequest,
    prompt_sha256: str,
    request_id: str,
    stop_reason: str,
    retry_attempts: int,
    client_elapsed_ms: int,
) -> BedrockHybridSynthesisInvocationEvidence:
    """Translate bounded Converse metadata into content-free runtime evidence."""
    usage = _required_mapping(response, "usage", context="Converse response")
    metrics = _required_mapping(response, "metrics", context="Converse response")
    return BedrockHybridSynthesisInvocationEvidence(
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
        request_sha256=request.request_sha256,
        prompt_sha256=prompt_sha256,
        envelope_sha256=request.envelope.identity_sha256,
        structured_catalog_sha256=request.structured_catalog_sha256,
        semantic_catalog_sha256=request.semantic_catalog_sha256,
    )


class BedrockHybridSynthesizer:
    """Execute exactly one bounded Bedrock Converse call for a semantic/hybrid request."""

    def __init__(
        self,
        client: BedrockHybridConverseClient,
        *,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        """Create the adapter with injected runtime client and monotonic clock."""
        self._client = client
        self._clock = clock

    def synthesize(
        self,
        request: HybridSynthesisRequest,
    ) -> BedrockHybridSynthesisExecution:
        """Invoke Bedrock once and admit only exact bounded hybrid output."""
        admitted_request = _admit_synthesis_request(request)
        prompt = build_hybrid_synthesis_prompt(admitted_request)
        payload = build_bedrock_hybrid_synthesis_converse_request(prompt)
        started = self._clock()
        try:
            response = self._client.converse(**payload)
        except Exception as exc:
            diagnostic = _provider_diagnostic(exc)
            raise BedrockHybridSynthesisRuntimeError(
                f"Bedrock hybrid Converse synthesis failed {diagnostic}",
                category=BedrockHybridSynthesisFailureCategory.PROVIDER_INVOCATION,
            ) from exc
        finished = self._clock()
        elapsed = finished - started
        if elapsed < 0:
            raise BedrockHybridSynthesisRuntimeError(
                "Hybrid synthesis client clock moved backwards.",
                category=BedrockHybridSynthesisFailureCategory.CLOCK,
            )
        client_elapsed_ms = round(elapsed * 1000)
        request_id, retry_attempts = _provider_identity(response)
        stop_reason = _stop_reason(response, request_id=request_id)
        evidence = _parse_invocation_evidence(
            response,
            request=admitted_request,
            prompt_sha256=prompt.prompt_sha256,
            request_id=request_id,
            stop_reason=stop_reason,
            retry_attempts=retry_attempts,
            client_elapsed_ms=client_elapsed_ms,
        )
        output = _extract_single_text_output(response)
        try:
            result = parse_hybrid_synthesis_output(
                output,
                request=admitted_request,
            )
        except HybridSynthesisOutputError as exc:
            raise BedrockHybridSynthesisRuntimeError(
                "Bedrock hybrid output violated deterministic output admission.",
                category=BedrockHybridSynthesisFailureCategory.OUTPUT_CONTRACT,
                request_id=request_id,
                stop_reason=stop_reason,
            ) from exc
        return BedrockHybridSynthesisExecution(result=result, evidence=evidence)