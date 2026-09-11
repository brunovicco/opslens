"""Offline HTTP API tests for the Gate 19.4 asynchronous public control path."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from opslens.public_analysis.adapters.async_http_api import handle_async_http_event
from opslens.public_analysis.application.async_job_service import (
    AsyncJobPutOutcome,
    claim_async_worker_attempt,
    complete_claimed_async_worker_success,
)
from opslens.public_analysis.domain.async_job import AsyncJobRecord

_NOW = 2_000_000_000


def _new_job_map() -> dict[str, AsyncJobRecord]:
    """Return one typed job map."""
    return {}


def _new_key_map() -> dict[str, str]:
    """Return one typed idempotency map."""
    return {}


def _new_job_id_list() -> list[str]:
    """Return one typed publication list."""
    return []


@dataclass(slots=True)
class _MemoryStore:
    """Small conditional job store for inbound adapter tests."""

    by_job_id: dict[str, AsyncJobRecord] = field(default_factory=_new_job_map)
    by_key_hash: dict[str, str] = field(default_factory=_new_key_map)

    def get_by_idempotency_key_sha256(self, digest: str) -> AsyncJobRecord | None:
        """Resolve one hashed idempotency key."""
        job_id = self.by_key_hash.get(digest)
        return None if job_id is None else self.by_job_id[job_id]

    def put_if_absent(self, job: AsyncJobRecord) -> AsyncJobPutOutcome:
        """Create one job or return the existing binding."""
        digest = job.identity.idempotency_key_sha256
        existing_id = self.by_key_hash.get(digest)
        if existing_id is not None:
            return AsyncJobPutOutcome(created=False, job=self.by_job_id[existing_id])
        self.by_key_hash[digest] = job.identity.job_id
        self.by_job_id[job.identity.job_id] = job
        return AsyncJobPutOutcome(created=True, job=job)

    def get(self, job_id: str) -> AsyncJobRecord | None:
        """Return one job by id."""
        return self.by_job_id.get(job_id)

    def replace_if_current(
        self,
        *,
        current: AsyncJobRecord,
        replacement: AsyncJobRecord,
    ) -> bool:
        """Replace one exact current record."""
        if self.by_job_id.get(current.identity.job_id) != current:
            return False
        self.by_job_id[current.identity.job_id] = replacement
        return True


@dataclass(slots=True)
class _MemoryPublisher:
    """Record logical SQS publications without network access."""

    published: list[str] = field(default_factory=_new_job_id_list)

    def publish(self, job_id: str) -> None:
        """Record one job id."""
        self.published.append(job_id)


def _submit_event(
    *,
    repository_url: str = "https://github.com/openedx/mockprock",
    idempotency_key: str = "client-key-0001",
) -> dict[str, object]:
    """Build one exact HTTP API v2 submit event."""
    return {
        "version": "2.0",
        "routeKey": "POST /v1/analyses",
        "headers": {
            "content-type": "application/json",
            "idempotency-key": idempotency_key,
        },
        "requestContext": {
            "requestId": "request-1",
            "http": {"method": "POST", "path": "/v1/analyses"},
        },
        "body": json.dumps(
            {
                "repository_url": repository_url,
                "requested_ref": "18c954d8604df4740c829ba17fa2f3640b92b900",
            },
            separators=(",", ":"),
        ),
        "isBase64Encoded": False,
    }


def _get_event(job_id: str, *, result: bool = False) -> dict[str, object]:
    """Build one exact HTTP API v2 status or result event."""
    suffix = "/result" if result else ""
    route_key = (
        "GET /v1/analyses/{job_id}/result"
        if result
        else "GET /v1/analyses/{job_id}"
    )
    return {
        "version": "2.0",
        "routeKey": route_key,
        "requestContext": {
            "requestId": "request-2",
            "http": {
                "method": "GET",
                "path": f"/v1/analyses/{job_id}{suffix}",
            },
        },
        "pathParameters": {"job_id": job_id},
    }


def _handle(
    event: dict[str, object],
    *,
    store: _MemoryStore,
    publisher: _MemoryPublisher,
    submit_enabled: bool = True,
) -> dict[str, object]:
    """Invoke the inbound adapter with deterministic runtime configuration."""
    return handle_async_http_event(
        event,
        store=store,
        publisher=publisher,
        now_epoch_seconds=_NOW,
        submission_lease_seconds=30,
        submit_enabled=submit_enabled,
    )


def _response_json(response: dict[str, object]) -> dict[str, object]:
    """Decode one JSON proxy response body."""
    body = response["body"]
    assert isinstance(body, str)
    decoded = json.loads(body)
    assert isinstance(decoded, dict)
    return decoded


def test_submit_returns_202_with_relative_status_and_result_urls() -> None:
    """Keep provider-heavy execution out of the public submit request path."""
    store = _MemoryStore()
    publisher = _MemoryPublisher()

    response = _handle(_submit_event(), store=store, publisher=publisher)
    payload = _response_json(response)

    assert response["statusCode"] == 202
    assert payload["state"] == "ACCEPTED"
    job_id = payload["job_id"]
    assert isinstance(job_id, str)
    assert payload["status_url"] == f"/v1/analyses/{job_id}"
    assert payload["result_url"] == f"/v1/analyses/{job_id}/result"
    assert publisher.published == [job_id]


def test_submit_disabled_returns_503_without_persistence_or_queue_work() -> None:
    """Preserve an independent submit kill boundary before DynamoDB or SQS mutation."""
    store = _MemoryStore()
    publisher = _MemoryPublisher()

    response = _handle(
        _submit_event(),
        store=store,
        publisher=publisher,
        submit_enabled=False,
    )

    assert response["statusCode"] == 503
    assert _response_json(response) == {"error": {"code": "SUBMIT_DISABLED"}}
    assert store.by_job_id == {}
    assert publisher.published == []


def test_same_idempotency_key_with_different_request_returns_409() -> None:
    """Map semantic idempotency conflict to the frozen public transport contract."""
    store = _MemoryStore()
    publisher = _MemoryPublisher()
    first = _handle(_submit_event(), store=store, publisher=publisher)
    assert first["statusCode"] == 202

    conflict = _handle(
        _submit_event(repository_url="https://github.com/openedx/edx-platform"),
        store=store,
        publisher=publisher,
    )

    assert conflict["statusCode"] == 409
    assert _response_json(conflict) == {"error": {"code": "IDEMPOTENCY_CONFLICT"}}
    assert len(publisher.published) == 1


def test_invalid_public_body_returns_400_without_queue_publication() -> None:
    """Fail closed before the dual-write boundary when request admission rejects input."""
    store = _MemoryStore()
    publisher = _MemoryPublisher()
    event = _submit_event()
    event["body"] = '{"repository_url":"https://example.com/not-github"}'

    response = _handle(event, store=store, publisher=publisher)

    assert response["statusCode"] == 400
    assert _response_json(response) == {"error": {"code": "INVALID_ANALYSIS_REQUEST"}}
    assert publisher.published == []


def test_status_and_result_are_projected_from_admitted_job_state() -> None:
    """Serve status/result from DynamoDB authority rather than protocol success inference."""
    store = _MemoryStore()
    publisher = _MemoryPublisher()
    submitted = _handle(_submit_event(), store=store, publisher=publisher)
    submit_payload = _response_json(submitted)
    job_id = submit_payload["job_id"]
    assert isinstance(job_id, str)

    status = _handle(_get_event(job_id), store=store, publisher=publisher)
    not_ready = _handle(_get_event(job_id, result=True), store=store, publisher=publisher)

    assert status["statusCode"] == 200
    assert _response_json(status)["state"] == "ACCEPTED"
    assert not_ready["statusCode"] == 409
    assert _response_json(not_ready) == {"error": {"code": "RESULT_NOT_READY"}}

    claim = claim_async_worker_attempt(
        job_id=job_id,
        store=store,
        now_epoch_seconds=_NOW,
        worker_lease_seconds=60,
    )
    complete_claimed_async_worker_success(
        claimed_job=claim.job,
        serialized_result=b'{"risk":"bounded"}',
        store=store,
    )

    result = _handle(_get_event(job_id, result=True), store=store, publisher=publisher)
    assert result["statusCode"] == 200
    assert result["body"] == '{"risk":"bounded"}'


def test_mismatched_route_context_fails_closed() -> None:
    """Do not trust routeKey without matching HTTP method/path context."""
    store = _MemoryStore()
    publisher = _MemoryPublisher()
    event = _submit_event()
    context = event["requestContext"]
    assert isinstance(context, dict)
    http = context["http"]
    assert isinstance(http, dict)
    http["path"] = "/unexpected"

    response = _handle(event, store=store, publisher=publisher)

    assert response["statusCode"] == 400
    assert _response_json(response) == {"error": {"code": "INVALID_HTTP_REQUEST"}}
