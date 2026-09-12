"""Localhost-only HTTP adapter for the OpsLens V1 deterministic visual demo."""

import json
from dataclasses import dataclass
from functools import cache
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from opslens.demo.cli import run_demo
from opslens.demo.controlled_benign import CONTROLLED_BENIGN_SCENARIO_ID
from opslens.demo.fail_closed import FAIL_CLOSED_SCENARIO_ID
from opslens.demo.material_vulnerability import (
    MATERIAL_VULNERABILITY_SCENARIO_ID,
    DemoContractError,
)
from opslens.demo.visual import (
    DemoVisualProjection,
    build_visual_projection,
    render_visual_index,
    render_visual_projection,
)

LOCAL_DEMO_HOST = "127.0.0.1"
LOCAL_DEMO_PORT = 8765
MAX_LOCAL_DEMO_PATH_CHARS = 512

_SUPPORTED_SCENARIOS = (
    MATERIAL_VULNERABILITY_SCENARIO_ID,
    CONTROLLED_BENIGN_SCENARIO_ID,
    FAIL_CLOSED_SCENARIO_ID,
)


@dataclass(frozen=True, slots=True)
class DemoHttpResponse:
    """Bounded HTTP response emitted by the presentation-only local adapter."""

    status: int
    content_type: str
    body: bytes


def _html_response(status: HTTPStatus, html: str) -> DemoHttpResponse:
    """Encode one local HTML response."""
    return DemoHttpResponse(
        status=int(status),
        content_type="text/html; charset=utf-8",
        body=html.encode("utf-8"),
    )


def _json_response(status: HTTPStatus, payload: dict[str, object]) -> DemoHttpResponse:
    """Encode one stable local JSON response."""
    body = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return DemoHttpResponse(
        status=int(status),
        content_type="application/json; charset=utf-8",
        body=body,
    )


def _error_page(title: str, message: str) -> str:
    """Render a small fixed-string rejection page without reflecting request content."""
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{title} · OpsLens</title></head><body>"
        f"<h1>{title}</h1><p>{message}</p><p><a href=\"/\">Back to demo</a></p>"
        "</body></html>"
    )


@cache
def build_visual_catalog() -> tuple[DemoVisualProjection, ...]:
    """Build the visual catalog only from the three admitted deterministic scenarios.

    Cached because the three scenarios are deterministic and immutable: rebuilding
    them on every request would recompute identical evidence, and memoizing states
    that plainly.
    """
    return tuple(
        build_visual_projection(run_demo(scenario)) for scenario in _SUPPORTED_SCENARIOS
    )


def route_visual_request(raw_path: str) -> DemoHttpResponse:
    """Route one GET/HEAD path through an exact allowlist with no arbitrary input authority."""
    if not raw_path or len(raw_path) > MAX_LOCAL_DEMO_PATH_CHARS:
        return _html_response(
            HTTPStatus.REQUEST_URI_TOO_LONG,
            _error_page(
                "Request rejected",
                "The local demo path is outside the admitted bound.",
            ),
        )

    parsed = urlsplit(raw_path)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        return _html_response(
            HTTPStatus.BAD_REQUEST,
            _error_page(
                "Request rejected",
                "The local demo accepts path-only navigation.",
            ),
        )

    path = parsed.path
    if path == "/":
        try:
            return _html_response(HTTPStatus.OK, render_visual_index(build_visual_catalog()))
        except DemoContractError:
            return _html_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                _error_page(
                    "Deterministic demo rejected",
                    "One admitted scenario failed its retained evidence contract.",
                ),
            )

    if path == "/health":
        return _json_response(
            HTTPStatus.OK,
            {
                "status": "ok",
                "mode": "LOCALHOST_OFFLINE_DEMO",
                "host": LOCAL_DEMO_HOST,
                "provider_execution": False,
                "model_execution": False,
            },
        )

    prefix = "/scenario/"
    if path.startswith(prefix):
        scenario_id = path[len(prefix) :]
        if scenario_id not in _SUPPORTED_SCENARIOS:
            return _html_response(
                HTTPStatus.NOT_FOUND,
                _error_page(
                    "Scenario not found",
                    "Only the three canonical V1 scenarios are admitted.",
                ),
            )
        try:
            projection = build_visual_projection(run_demo(scenario_id))
            return _html_response(HTTPStatus.OK, render_visual_projection(projection))
        except DemoContractError:
            return _html_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                _error_page(
                    "Deterministic demo rejected",
                    "The selected scenario failed its retained evidence contract.",
                ),
            )

    return _html_response(
        HTTPStatus.NOT_FOUND,
        _error_page(
            "Route not found",
            "This localhost demo exposes only bounded reviewer routes.",
        ),
    )


class VisualDemoRequestHandler(BaseHTTPRequestHandler):
    """Serve the bounded visual projection without accepting business-authority inputs."""

    server_version = "OpsLensLocalDemo/1.0"

    def _write(self, response: DemoHttpResponse, *, include_body: bool) -> None:
        """Write one response with browser hardening headers and no external asset authority."""
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        if include_body:
            self.wfile.write(response.body)

    def do_GET(self) -> None:
        """Serve one allowlisted local reviewer GET route."""
        self._write(route_visual_request(self.path), include_body=True)

    def do_HEAD(self) -> None:
        """Serve headers for one allowlisted local reviewer route."""
        self._write(route_visual_request(self.path), include_body=False)

    def do_POST(self) -> None:
        """Reject mutation/input submission because the V1 viewer is read-only."""
        self._write(
            _html_response(
                HTTPStatus.METHOD_NOT_ALLOWED,
                _error_page("Method not allowed", "The V1 local demo is read-only."),
            ),
            include_body=True,
        )

    def log_message(self, format: str, *args: object) -> None:
        """Suppress raw request logging so arbitrary path text is never echoed by the demo."""
        del format, args


def build_local_demo_server(*, port: int = LOCAL_DEMO_PORT) -> ThreadingHTTPServer:
    """Build a server that is structurally bound to IPv4 loopback only."""
    if isinstance(port, bool) or not 1 <= port <= 65_535:
        raise DemoContractError("local demo port must be an integer from 1 through 65535")
    return ThreadingHTTPServer((LOCAL_DEMO_HOST, port), VisualDemoRequestHandler)


def serve_local_demo(*, port: int = LOCAL_DEMO_PORT) -> None:
    """Run the local reviewer surface until interrupted by the human operator."""
    with build_local_demo_server(port=port) as server:
        print(f"OpsLens local visual demo: http://{LOCAL_DEMO_HOST}:{port}/")
        print("Localhost only. No provider or model execution. Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nOpsLens local visual demo stopped.")


__all__ = [
    "LOCAL_DEMO_HOST",
    "LOCAL_DEMO_PORT",
    "MAX_LOCAL_DEMO_PATH_CHARS",
    "DemoHttpResponse",
    "VisualDemoRequestHandler",
    "build_local_demo_server",
    "build_visual_catalog",
    "route_visual_request",
    "serve_local_demo",
]
