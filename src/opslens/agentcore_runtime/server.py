"""Minimal stdlib HTTP server for the bounded AgentCore Runtime experiment."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Final, cast

from botocore.config import Config
from botocore.session import Session

from opslens.agent_baseline.adapters.bedrock_reasoning import (
    BEDROCK_AGENT_REASONING_REGION,
    BedrockAgentReasoningConverseClient,
    BedrockSingleAgentReasoningModel,
)
from opslens.agent_baseline.ports.reasoning import AgentReasoningModel
from opslens.agentcore_runtime.domain import MAX_AGENTCORE_RUNTIME_REQUEST_UTF8_BYTES
from opslens.agentcore_runtime.http_adapter import (
    AgentCoreHttpResponse,
    handle_agentcore_http_request,
)

AGENTCORE_RUNTIME_HOST: Final = "0.0.0.0"
AGENTCORE_RUNTIME_PORT: Final = 8080


def create_bedrock_reasoning_model() -> BedrockSingleAgentReasoningModel:
    """Compose the fixed retained Bedrock reasoning adapter from execution-role credentials."""
    session = Session()
    client = session.create_client(
        "bedrock-runtime",
        region_name=BEDROCK_AGENT_REASONING_REGION,
        config=Config(
            connect_timeout=10,
            read_timeout=300,
            retries={"total_max_attempts": 1, "mode": "standard"},
        ),
    )
    return BedrockSingleAgentReasoningModel(
        cast(BedrockAgentReasoningConverseClient, client)
    )


def create_agentcore_request_handler(
    model: AgentReasoningModel,
) -> type[BaseHTTPRequestHandler]:
    """Create an HTTP handler bound to one fixed reasoning-model adapter."""

    class AgentCoreRequestHandler(BaseHTTPRequestHandler):
        """Serve only the AgentCore HTTP service contract required by Gate 14.2."""

        server_version = "OpsLensAgentCore/1"
        sys_version = ""

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            """Serve the bounded health route and reject all other GET surfaces."""
            body = self._read_bounded_body()
            if body is None:
                return
            response = handle_agentcore_http_request(
                method="GET",
                path=self.path,
                content_type=self.headers.get("Content-Type"),
                body=body,
                model=model,
            )
            self._write_response(response)

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            """Serve the bounded invocation route and reject all other POST surfaces."""
            body = self._read_bounded_body(require_content_length=True)
            if body is None:
                return
            response = handle_agentcore_http_request(
                method="POST",
                path=self.path,
                content_type=self.headers.get("Content-Type"),
                body=body,
                model=model,
            )
            self._write_response(response)

        def _read_bounded_body(
            self,
            *,
            require_content_length: bool = False,
        ) -> bytes | None:
            """Read one fixed-length request body without accepting chunked/unbounded input."""
            if self.headers.get("Transfer-Encoding") is not None:
                self._write_transport_error(400, "unsupported_transfer_encoding")
                return None

            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                if require_content_length:
                    self._write_transport_error(411, "content_length_required")
                    return None
                return b""
            try:
                content_length = int(raw_length, 10)
            except ValueError:
                self._write_transport_error(400, "invalid_content_length")
                return None
            if content_length < 0:
                self._write_transport_error(400, "invalid_content_length")
                return None
            if content_length > MAX_AGENTCORE_RUNTIME_REQUEST_UTF8_BYTES:
                self._write_transport_error(413, "request_too_large")
                return None

            body = self.rfile.read(content_length)
            if len(body) != content_length:
                self._write_transport_error(400, "incomplete_request_body")
                return None
            return body

        def _write_transport_error(self, status_code: int, code: str) -> None:
            """Emit one stable transport-layer error without application/provider content."""
            body = f'{{"error":{{"code":"{code}"}}}}'.encode()
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _write_response(self, response: AgentCoreHttpResponse) -> None:
            """Write one already-bounded application response."""
            self.send_response(response.status_code)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

        def log_message(self, format: str, *args: object) -> None:
            """Suppress default request logging so raw request-derived values are not echoed."""
            del format, args

    return AgentCoreRequestHandler


def serve_agentcore_runtime() -> None:
    """Serve the bounded runtime on the AgentCore-required host and port."""
    model = create_bedrock_reasoning_model()
    handler = create_agentcore_request_handler(model)
    server = ThreadingHTTPServer((AGENTCORE_RUNTIME_HOST, AGENTCORE_RUNTIME_PORT), handler)
    server.serve_forever()


def main() -> int:
    """Run the AgentCore HTTP server until the runtime terminates the process."""
    serve_agentcore_runtime()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AGENTCORE_RUNTIME_HOST",
    "AGENTCORE_RUNTIME_PORT",
    "create_agentcore_request_handler",
    "create_bedrock_reasoning_model",
    "serve_agentcore_runtime",
]
