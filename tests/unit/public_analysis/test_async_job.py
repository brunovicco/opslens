"""Deterministic tests for the Gate 19.4 async job authority slice."""

from __future__ import annotations

import pytest

from opslens.public_analysis.application.async_job_admission import (
    AsyncIdempotencyConflictError,
    AsyncSubmissionDisposition,
    AsyncWorkerDisposition,
    decide_async_submission,
    decide_worker_delivery,
)
from opslens.public_analysis.domain.async_job import (
    AsyncJobState,
    complete_async_job_failure,
    complete_async_job_success,
    create_async_job_identity,
    create_submitting_job,
    transition_async_job,
    validate_idempotency_key,
)
from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.public_analysis.domain.request import (
    PublicAnalysisRequest,
    PublicRepositoryTarget,
    create_public_analysis_request,
)


def _request(*, repository_name: str = "mockprock") -> PublicAnalysisRequest:
    """Build one admitted deterministic public-analysis request."""
    return create_public_analysis_request(
        PublicRepositoryTarget(
            owner="openedx",
            name=repository_name,
            requested_ref="18c954d8604df4740c829ba17fa2f3640b92b900",
        )
    )


def test_async_identity_is_deterministic_and_key_is_not_exposed() -> None:
    """Bind job identity to request/key hashes without storing the raw key."""
    request = _request()
    first = create_async_job_identity(request, idempotency_key="client-key-0001")
    second = create_async_job_identity(request, idempotency_key="client-key-0001")

    assert first == second
    assert first.job_id.startswith("public-analysis-job:v1:")
    assert first.request_sha256 == request.request_sha256
    assert first.idempotency_key_sha256 != "client-key-0001"
    assert "client-key-0001" not in first.job_id


def test_same_key_and_same_request_returns_existing_job() -> None:
    """Make idempotent replay return the exact existing job."""
    request = _request()
    first = decide_async_submission(
        request,
        idempotency_key="client-key-0001",
        existing_job=None,
    )
    replay = decide_async_submission(
        request,
        idempotency_key="client-key-0001",
        existing_job=first.job,
    )

    assert first.disposition is AsyncSubmissionDisposition.CREATE_NEW_JOB
    assert replay.disposition is AsyncSubmissionDisposition.RETURN_EXISTING_JOB
    assert replay.job == first.job


def test_same_key_and_different_request_is_conflict() -> None:
    """Reject rebinding one idempotency key to different request semantics."""
    first_request = _request(repository_name="mockprock")
    second_request = _request(repository_name="edx-platform")
    existing = decide_async_submission(
        first_request,
        idempotency_key="client-key-0001",
        existing_job=None,
    ).job

    with pytest.raises(AsyncIdempotencyConflictError):
        decide_async_submission(
            second_request,
            idempotency_key="client-key-0001",
            existing_job=existing,
        )


def test_running_transition_claims_exactly_one_attempt() -> None:
    """Increment attempt ownership only when entering one RUNNING delivery attempt."""
    identity = create_async_job_identity(_request(), idempotency_key="client-key-0001")
    submitting = create_submitting_job(identity)
    accepted = transition_async_job(submitting, target_state=AsyncJobState.ACCEPTED)
    running = transition_async_job(accepted, target_state=AsyncJobState.RUNNING)
    retry = transition_async_job(running, target_state=AsyncJobState.RUNNING)

    assert submitting.attempt_count == 0
    assert accepted.attempt_count == 0
    assert running.attempt_count == 1
    assert retry.attempt_count == 2


def test_forbidden_transition_fails_closed() -> None:
    """Reject transitions outside the exact Gate 19.3 lifecycle."""
    identity = create_async_job_identity(_request(), idempotency_key="client-key-0001")
    submitting = create_submitting_job(identity)

    with pytest.raises(PublicAnalysisValidationError):
        transition_async_job(submitting, target_state=AsyncJobState.SUCCEEDED)


def test_success_requires_running_and_persists_result_integrity() -> None:
    """Persist hash and byte count only for one admitted RUNNING result."""
    identity = create_async_job_identity(_request(), idempotency_key="client-key-0001")
    running = transition_async_job(
        create_submitting_job(identity),
        target_state=AsyncJobState.RUNNING,
    )
    succeeded = complete_async_job_success(
        running,
        serialized_result=b'{"status":"ok"}',
    )

    assert succeeded.state is AsyncJobState.SUCCEEDED
    assert succeeded.result_bytes == 15
    assert succeeded.result_sha256 is not None
    assert succeeded.result_json == '{"status":"ok"}'
    assert succeeded.failure_code is None


def test_failure_requires_explicit_bounded_code() -> None:
    """Terminalize one non-terminal job with deterministic failure evidence."""
    identity = create_async_job_identity(_request(), idempotency_key="client-key-0001")
    accepted = transition_async_job(
        create_submitting_job(identity),
        target_state=AsyncJobState.ACCEPTED,
    )
    failed = complete_async_job_failure(accepted, failure_code="QUEUE_PUBLISH_FAILED")

    assert failed.state is AsyncJobState.FAILED
    assert failed.failure_code == "QUEUE_PUBLISH_FAILED"


def test_terminal_duplicate_delivery_is_noop() -> None:
    """Keep at-least-once queue delivery separate from execution authority."""
    identity = create_async_job_identity(_request(), idempotency_key="client-key-0001")
    running = transition_async_job(
        create_submitting_job(identity),
        target_state=AsyncJobState.RUNNING,
    )
    succeeded = complete_async_job_success(running, serialized_result=b'{"status":"ok"}')

    decision = decide_worker_delivery(succeeded)

    assert decision.disposition is AsyncWorkerDisposition.NOOP_ALREADY_TERMINAL
    assert decision.job == succeeded


def test_expiry_removes_inline_result_payload() -> None:
    """Remove result material when a successful job crosses the explicit expiry transition."""
    identity = create_async_job_identity(_request(), idempotency_key="client-key-0001")
    running = transition_async_job(
        create_submitting_job(identity),
        target_state=AsyncJobState.RUNNING,
    )
    succeeded = complete_async_job_success(running, serialized_result=b'{"status":"ok"}')
    expired = transition_async_job(succeeded, target_state=AsyncJobState.EXPIRED)

    assert expired.state is AsyncJobState.EXPIRED
    assert expired.result_sha256 is None
    assert expired.result_bytes is None
    assert expired.result_json is None
    assert decide_worker_delivery(expired).disposition is AsyncWorkerDisposition.NOOP_EXPIRED


@pytest.mark.parametrize(
    "value",
    ["short", "has space", "a" * 129, "ümlaut-key"],
)
def test_idempotency_key_validation_is_bounded(value: str) -> None:
    """Reject keys outside the frozen ASCII and length envelope."""
    with pytest.raises(PublicAnalysisValidationError):
        validate_idempotency_key(value)
