"""Tests for the bounded AgentCore Runtime HTTP transport adapter."""

from __future__ import annotations

import json

from opslens.agent_baseline.domain.models import AgentCapability, SingleAgentTask
from opslens.agent_baseline.domain.reasoning import AgentReasoningInvocationEvidence
from opslens.agent_baseline.ports.reasoning import AgentReasoningModelResponse
from opslens.agentcore_runtime.http_adapter import handle_agentcore_http_request


class _FakeReasoningModel:
    """Return one fixed reasoning response while recording invocation count."""

    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.invocation_count = 0

    def generate(self, task: SingleAgentTask) -> AgentReasoningModelResponse:
        """Create deterministic metadata-only evidence bound to the received task."""
        self.invocation_count += 1
        return AgentReasoningModelResponse(
            output_text=self.output_text,
            evidence=AgentReasoningInvocationEvidence.create(
                task_id=task.task_id,
                provider="amazon_bedrock",
                model_id="fixed-model",
                region="us-east-1",
                request_id="request-1",
                stop_reason="end_turn",
                input_tokens=10,
                output_tokens=2,
                total_tokens=12,
                cache_read_input_tokens=0,
                cache_write_input_tokens=0,
                provider_latency_ms=20,
                client_elapsed_ms=25,
                retry_attempts=0,
            ),
        )


class _FailingReasoningModel:
    """Raise one provider-like exception that must never enter protocol output."""

    def __init__(self) -> None:
        self.invocation_count = 0

    def generate(self, task: SingleAgentTask) -> AgentReasoningModelResponse:
        """Raise after recording the admitted task invocation."""
        self.invocation_count += 1
        raise RuntimeError(f"provider secret for {task.task_id}: do-not-leak")


def _body() -> bytes:
    return json.dumps(
        {
            "task_text": "Show structured vulnerability facts.",
            "allowed_capabilities": [AgentCapability.STRUCTURED_SECURITY_QUERY.value],
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _payload(response_body: bytes) -> dict[str, object]:
    value = json.loads(response_body.decode("utf-8"))
    assert isinstance(value, dict)
    return value


def test_ping_is_health_only_and_does_not_invoke_model() -> None:
    """Keep the health endpoint free of reasoning and authority-bearing data."""
    model = _FakeReasoningModel('{"decision":"abstain","capability":null}')

    response = handle_agentcore_http_request(
        method="GET",
        path="/ping",
        content_type=None,
        body=b"",
        model=model,
    )

    assert response.status_code == 200
    assert _payload(response.body) == {"status": "Healthy"}
    assert model.invocation_count == 0


def test_invocations_returns_content_minimized_projection() -> None:
    """Expose the admitted reasoning projection and never the raw model output."""
    model = _FakeReasoningModel(
        '{"decision":"act","capability":"structured_security_query"}'
    )

    response = handle_agentcore_http_request(
        method="POST",
        path="/invocations",
        content_type="application/json",
        body=_body(),
        model=model,
    )
    payload = _payload(response.body)

    assert response.status_code == 200
    assert model.invocation_count == 1
    assert payload["authorization_outcome"] == "authorized"
    assert payload["capability"] == "structured_security_query"
    assert "output_text" not in payload
    assert "result" not in payload
    assert "sql" not in payload


def test_invalid_body_fails_before_model_invocation() -> None:
    """Reject runtime input deterministically before model work begins."""
    model = _FakeReasoningModel('{"decision":"abstain","capability":null}')

    response = handle_agentcore_http_request(
        method="POST",
        path="/invocations",
        content_type="application/json",
        body=b'{"task_text":"missing allowlist"}',
        model=model,
    )

    assert response.status_code == 400
    assert _payload(response.body) == {"error": {"code": "invalid_runtime_request"}}
    assert model.invocation_count == 0


def test_provider_exception_content_is_not_returned() -> None:
    """Map provider failures to a stable transport error without exception leakage."""
    model = _FailingReasoningModel()

    response = handle_agentcore_http_request(
        method="POST",
        path="/invocations",
        content_type="application/json",
        body=_body(),
        model=model,
    )

    assert response.status_code == 502
    assert _payload(response.body) == {"error": {"code": "reasoning_unavailable"}}
    assert b"do-not-leak" not in response.body
    assert model.invocation_count == 1


def test_malformed_model_output_maps_to_stable_upstream_error() -> None:
    """Keep untrusted malformed model output outside the HTTP response body."""
    model = _FakeReasoningModel("not-json")

    response = handle_agentcore_http_request(
        method="POST",
        path="/invocations",
        content_type="application/json",
        body=_body(),
        model=model,
    )

    assert response.status_code == 502
    assert _payload(response.body) == {"error": {"code": "invalid_model_response"}}
    assert b"not-json" not in response.body
    assert model.invocation_count == 1


def test_transport_rejects_unknown_path_method_media_type_and_ping_body() -> None:
    """Keep the first AgentCore HTTP surface exactly /ping and /invocations."""
    model = _FakeReasoningModel('{"decision":"abstain","capability":null}')

    cases = (
        ("POST", "/unknown", "application/json", _body(), 404, "not_found"),
        ("GET", "/invocations", None, b"", 405, "method_not_allowed"),
        ("POST", "/invocations", "text/plain", _body(), 415, "unsupported_media_type"),
        ("POST", "/ping", "application/json", b"", 405, "method_not_allowed"),
        ("GET", "/ping", None, b"unexpected", 400, "invalid_ping_request"),
    )

    for method, path, content_type, body, status_code, error_code in cases:
        response = handle_agentcore_http_request(
            method=method,
            path=path,
            content_type=content_type,
            body=body,
            model=model,
        )
        assert response.status_code == status_code
        assert _payload(response.body) == {"error": {"code": error_code}}

    assert model.invocation_count == 0
