"""Deterministic API Gateway HTTP API v2 admission for the async public surface."""

import base64
import binascii
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from opslens.public_analysis.application.async_job_admission import (
    AsyncIdempotencyConflictError,
)
from opslens.public_analysis.application.async_job_service import (
    AsyncJobNotFoundError,
    AsyncJobPublisher,
    AsyncJobStore,
    AsyncResultExpiredError,
    AsyncResultNotReadyError,
    AsyncSubmissionUnavailableError,
    get_async_job_result,
    get_async_job_status,
    submit_async_analysis,
)
from opslens.public_analysis.application.request_admission import (
    MAX_PUBLIC_ANALYSIS_REQUEST_BYTES,
    PublicAnalysisRequestAdmissionError,
    admit_public_analysis_request,
)
from opslens.public_analysis.domain.async_job import (
    AsyncJobRecord,
    validate_async_job_id,
    validate_idempotency_key,
)
from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.shared.evidence import canonical_json_text

MAX_HTTP_API_BODY_TEXT_CHARS = 8_192

_SUBMIT_ROUTE_KEY = "POST /v1/analyses"
_STATUS_ROUTE_KEY = "GET /v1/analyses/{job_id}"
_RESULT_ROUTE_KEY = "GET /v1/analyses/{job_id}/result"


class AsyncHttpRoute(StrEnum):
    """Exact routes admitted by the Gate 19.3 public contract."""

    SUBMIT = "SUBMIT"
    STATUS = "STATUS"
    RESULT = "RESULT"


class AsyncHttpAdmissionError(ValueError):
    """Raised when an untrusted HTTP API event violates the frozen transport contract."""


@dataclass(frozen=True, slots=True)
class AsyncHttpRequest:
    """Small admitted projection of one API Gateway HTTP API v2 event."""

    route: AsyncHttpRoute
    request_id: str
    job_id: str | None = None
    idempotency_key: str | None = None
    body: bytes | None = None


@dataclass(frozen=True, slots=True)
class AsyncHttpResponse:
    """Exact Lambda proxy response for the HTTP API boundary."""

    status_code: int
    body: str

    def to_dict(self) -> dict[str, object]:
        """Render the API Gateway v2 Lambda proxy result."""
        return {
            "statusCode": self.status_code,
            "headers": {
                "content-type": "application/json",
                "cache-control": "no-store",
            },
            "body": self.body,
            "isBase64Encoded": False,
        }


def _canonical_json(value: object) -> str:
    """Serialize one small deterministic public HTTP response."""
    return canonical_json_text(value)


def _mapping(value: object, *, field: str) -> dict[str, object]:
    """Project one untyped JSON object into a string-keyed mapping."""
    if not isinstance(value, dict):
        raise AsyncHttpAdmissionError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise AsyncHttpAdmissionError(f"{field} keys must be strings")
    return cast(dict[str, object], raw)


def _normalized_headers(value: object) -> dict[str, str]:
    """Normalize HTTP header names while rejecting case-colliding duplicates."""
    raw = _mapping(value, field="headers")
    normalized: dict[str, str] = {}
    for name, candidate in raw.items():
        if type(candidate) is not str:
            raise AsyncHttpAdmissionError("header values must be strings")
        key = name.lower()
        if key in normalized:
            raise AsyncHttpAdmissionError("headers contain a case-insensitive duplicate")
        normalized[key] = candidate
    return normalized


def _request_context(event: Mapping[str, object]) -> tuple[str, str, str]:
    """Return request id, method, and path from one HTTP API v2 request context."""
    context = _mapping(event.get("requestContext"), field="requestContext")
    request_id = context.get("requestId")
    if type(request_id) is not str or not request_id:
        raise AsyncHttpAdmissionError("requestContext.requestId must be non-empty")
    http = _mapping(context.get("http"), field="requestContext.http")
    method = http.get("method")
    path = http.get("path")
    if type(method) is not str or type(path) is not str:
        raise AsyncHttpAdmissionError("requestContext.http method/path are required")
    return request_id, method, path


def _decode_submit_body(event: Mapping[str, object]) -> bytes:
    """Decode one bounded API Gateway body before domain request admission."""
    body = event.get("body")
    if type(body) is not str or not body:
        raise AsyncHttpAdmissionError("submit body must be a non-empty string")
    if len(body) > MAX_HTTP_API_BODY_TEXT_CHARS:
        raise AsyncHttpAdmissionError("submit body exceeds the transport text bound")
    encoded = event.get("isBase64Encoded", False)
    if type(encoded) is not bool:
        raise AsyncHttpAdmissionError("isBase64Encoded must be boolean")
    if encoded:
        try:
            decoded = base64.b64decode(body, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise AsyncHttpAdmissionError("submit body contains invalid base64") from exc
    else:
        try:
            decoded = body.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise AsyncHttpAdmissionError("submit body must encode as UTF-8") from exc
    if len(decoded) > MAX_PUBLIC_ANALYSIS_REQUEST_BYTES:
        raise AsyncHttpAdmissionError("submit body exceeds the public request byte bound")
    return decoded


def _job_path_parameter(event: Mapping[str, object]) -> str:
    """Read and validate the exact asynchronous job path parameter."""
    parameters = _mapping(event.get("pathParameters"), field="pathParameters")
    if set(parameters) != {"job_id"}:
        raise AsyncHttpAdmissionError("pathParameters must contain exactly job_id")
    raw_job_id = parameters["job_id"]
    if type(raw_job_id) is not str:
        raise AsyncHttpAdmissionError("job_id path parameter must be a string")
    try:
        return validate_async_job_id(raw_job_id)
    except PublicAnalysisValidationError as exc:
        raise AsyncHttpAdmissionError("job_id path parameter is invalid") from exc


def admit_async_http_request(event: Mapping[str, object]) -> AsyncHttpRequest:
    """Admit exactly one frozen HTTP API v2 submit/status/result event."""
    if event.get("version") != "2.0":
        raise AsyncHttpAdmissionError("only API Gateway HTTP API payload v2.0 is admitted")
    route_key = event.get("routeKey")
    if type(route_key) is not str:
        raise AsyncHttpAdmissionError("routeKey must be a string")
    request_id, method, path = _request_context(event)

    if route_key == _SUBMIT_ROUTE_KEY:
        if method != "POST" or path != "/v1/analyses":
            raise AsyncHttpAdmissionError("submit route context does not match routeKey")
        headers = _normalized_headers(event.get("headers"))
        content_type = headers.get("content-type")
        if content_type is None or content_type.split(";", 1)[0].strip().lower() != (
            "application/json"
        ):
            raise AsyncHttpAdmissionError("submit requires application/json content-type")
        raw_key = headers.get("idempotency-key")
        if raw_key is None or "," in raw_key:
            raise AsyncHttpAdmissionError("submit requires one Idempotency-Key header")
        try:
            idempotency_key = validate_idempotency_key(raw_key)
        except PublicAnalysisValidationError as exc:
            raise AsyncHttpAdmissionError("Idempotency-Key is invalid") from exc
        return AsyncHttpRequest(
            route=AsyncHttpRoute.SUBMIT,
            request_id=request_id,
            idempotency_key=idempotency_key,
            body=_decode_submit_body(event),
        )

    if route_key not in {_STATUS_ROUTE_KEY, _RESULT_ROUTE_KEY}:
        raise AsyncHttpAdmissionError("routeKey is outside the frozen async public contract")
    if method != "GET":
        raise AsyncHttpAdmissionError("status/result route must use GET")
    raw_body = event.get("body")
    if raw_body is not None and raw_body != "":
        raise AsyncHttpAdmissionError("status/result routes do not accept a request body")
    job_id = _job_path_parameter(event)
    expected_path = f"/v1/analyses/{job_id}"
    route = AsyncHttpRoute.STATUS
    if route_key == _RESULT_ROUTE_KEY:
        expected_path += "/result"
        route = AsyncHttpRoute.RESULT
    if path != expected_path:
        raise AsyncHttpAdmissionError("request path does not match admitted job coordinates")
    return AsyncHttpRequest(route=route, request_id=request_id, job_id=job_id)


def _status_payload(job: AsyncJobRecord) -> dict[str, object]:
    """Project one admitted job into the bounded public status response."""
    payload: dict[str, object] = {
        "attempt_count": job.attempt_count,
        "job_id": job.identity.job_id,
        "state": job.state.value,
    }
    if job.failure_code is not None:
        payload["failure_code"] = job.failure_code
    return payload


def _error_response(status_code: int, code: str) -> AsyncHttpResponse:
    """Return one content-minimized deterministic error response."""
    return AsyncHttpResponse(
        status_code=status_code,
        body=_canonical_json({"error": {"code": code}}),
    )


def handle_async_http_event(
    event: Mapping[str, object],
    *,
    store: AsyncJobStore,
    publisher: AsyncJobPublisher,
    now_epoch_seconds: int,
    submission_lease_seconds: int,
    submit_enabled: bool,
) -> dict[str, object]:
    """Execute the deterministic HTTP control path without provider-heavy analysis work."""
    try:
        request = admit_async_http_request(event)
    except AsyncHttpAdmissionError:
        return _error_response(400, "INVALID_HTTP_REQUEST").to_dict()

    if request.route is AsyncHttpRoute.SUBMIT:
        if not submit_enabled:
            return _error_response(503, "SUBMIT_DISABLED").to_dict()
        if request.body is None or request.idempotency_key is None:
            return _error_response(400, "INVALID_HTTP_REQUEST").to_dict()
        try:
            admitted = admit_public_analysis_request(request.body)
            result = submit_async_analysis(
                admitted.request,
                idempotency_key=request.idempotency_key,
                store=store,
                publisher=publisher,
                now_epoch_seconds=now_epoch_seconds,
                submission_lease_seconds=submission_lease_seconds,
            )
        except PublicAnalysisRequestAdmissionError:
            return _error_response(400, "INVALID_ANALYSIS_REQUEST").to_dict()
        except AsyncIdempotencyConflictError:
            return _error_response(409, "IDEMPOTENCY_CONFLICT").to_dict()
        except AsyncSubmissionUnavailableError:
            return _error_response(503, "SUBMISSION_UNAVAILABLE").to_dict()
        job_id = result.job.identity.job_id
        return AsyncHttpResponse(
            status_code=202,
            body=_canonical_json(
                {
                    "job_id": job_id,
                    "result_url": f"/v1/analyses/{job_id}/result",
                    "state": result.job.state.value,
                    "status_url": f"/v1/analyses/{job_id}",
                }
            ),
        ).to_dict()

    if request.job_id is None:
        return _error_response(400, "INVALID_HTTP_REQUEST").to_dict()
    if request.route is AsyncHttpRoute.STATUS:
        try:
            job = get_async_job_status(job_id=request.job_id, store=store)
        except AsyncJobNotFoundError:
            return _error_response(404, "JOB_NOT_FOUND").to_dict()
        return AsyncHttpResponse(
            status_code=200,
            body=_canonical_json(_status_payload(job)),
        ).to_dict()

    try:
        result_json = get_async_job_result(job_id=request.job_id, store=store)
    except AsyncJobNotFoundError:
        return _error_response(404, "JOB_NOT_FOUND").to_dict()
    except AsyncResultExpiredError:
        return _error_response(410, "RESULT_EXPIRED").to_dict()
    except AsyncResultNotReadyError:
        return _error_response(409, "RESULT_NOT_READY").to_dict()
    return AsyncHttpResponse(status_code=200, body=result_json).to_dict()


__all__ = [
    "MAX_HTTP_API_BODY_TEXT_CHARS",
    "AsyncHttpAdmissionError",
    "AsyncHttpRequest",
    "AsyncHttpResponse",
    "AsyncHttpRoute",
    "admit_async_http_request",
    "handle_async_http_event",
]
