"""HTTP transport adapter for the bounded AgentCore Runtime experiment."""

from __future__ import annotations

import json
from dataclasses import dataclass

from opslens.agent_baseline.domain.errors import AgentReasoningValidationError
from opslens.agent_baseline.ports.reasoning import AgentReasoningModel
from opslens.agentcore_runtime.application import handle_agentcore_runtime_invocation
from opslens.agentcore_runtime.domain import AgentCoreRuntimeValidationError

_AGENTCORE_INVOCATIONS_PATH = "/invocations"
_AGENTCORE_PING_PATH = "/ping"
_APPLICATION_JSON = "application/json"
_MAX_HTTP_RESPONSE_UTF8_BYTES = 16_384


@dataclass(frozen=True, slots=True)
class AgentCoreHttpResponse:
    """Represent one content-minimized HTTP response produced by OpsLens."""

    status_code: int
    content_type: str
    body: bytes

    def __post_init__(self) -> None:
        """Reject malformed transport responses before they reach the server."""
        if type(self.status_code) is not int or not 100 <= self.status_code <= 599:
            raise ValueError("status_code must be one valid HTTP status code")
        if self.content_type != _APPLICATION_JSON:
            raise ValueError("AgentCore HTTP responses must use application/json")
        if type(self.body) is not bytes or not self.body:
            raise ValueError("AgentCore HTTP response body must be non-empty bytes")
        if len(self.body) > _MAX_HTTP_RESPONSE_UTF8_BYTES:
            raise ValueError("AgentCore HTTP response exceeds the response byte limit")


def handle_agentcore_http_request(
    *,
    method: str,
    path: str,
    content_type: str | None,
    body: bytes,
    model: AgentReasoningModel,
) -> AgentCoreHttpResponse:
    """Handle one bounded AgentCore HTTP request without granting transport authority."""
    if type(method) is not str or type(path) is not str:
        return _error_response(status_code=400, code="invalid_http_request")
    if type(body) is not bytes:
        return _error_response(status_code=400, code="invalid_http_request")

    if path == _AGENTCORE_PING_PATH:
        if method != "GET":
            return _error_response(status_code=405, code="method_not_allowed")
        if body:
            return _error_response(status_code=400, code="invalid_ping_request")
        return _json_response(status_code=200, payload={"status": "Healthy"})

    if path != _AGENTCORE_INVOCATIONS_PATH:
        return _error_response(status_code=404, code="not_found")
    if method != "POST":
        return _error_response(status_code=405, code="method_not_allowed")
    if content_type != _APPLICATION_JSON:
        return _error_response(status_code=415, code="unsupported_media_type")

    try:
        projection = handle_agentcore_runtime_invocation(raw_body=body, model=model)
    except AgentCoreRuntimeValidationError:
        return _error_response(status_code=400, code="invalid_runtime_request")
    except AgentReasoningValidationError:
        return _error_response(status_code=502, code="invalid_model_response")
    except Exception:
        # Provider/framework exception content is intentionally excluded from protocol output.
        return _error_response(status_code=502, code="reasoning_unavailable")

    return _json_response(status_code=200, payload=projection.to_payload())


def _error_response(*, status_code: int, code: str) -> AgentCoreHttpResponse:
    """Return one stable error envelope without downstream exception content."""
    return _json_response(status_code=status_code, payload={"error": {"code": code}})


def _json_response(*, status_code: int, payload: object) -> AgentCoreHttpResponse:
    """Serialize one bounded canonical JSON response."""
    body = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if len(body) > _MAX_HTTP_RESPONSE_UTF8_BYTES:
        return AgentCoreHttpResponse(
            status_code=500,
            content_type=_APPLICATION_JSON,
            body=b'{"error":{"code":"response_too_large"}}',
        )
    return AgentCoreHttpResponse(
        status_code=status_code,
        content_type=_APPLICATION_JSON,
        body=body,
    )


__all__ = ["AgentCoreHttpResponse", "handle_agentcore_http_request"]
