"""Deterministic tests for the Gate 19.4 async job authority slice."""

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
    accept_async_job,
    claim_async_job_attempt,
    complete_async_job_failure,
    complete_async_job_success,
    create_async_job_identity,
    create_submitting_job,
    refresh_submitting_lease,
    transition_async_job,
    validate_idempotency_key,
)
from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.public_analysis.domain.request import (
    PublicAnalysisRequest,
    PublicRepositoryTarget,
    create_public_analysis_request,
)

_NOW = 2_000_000_000
_SUBMISSION_LEASE_SECONDS = 30
_WORKER_LEASE_SECONDS = 60


def _request(*, repository_name: str = "mockprock") -> PublicAnalysisRequest:
    """Build one admitted deterministic public-analysis request."""
    return create_public_analysis_request(
        PublicRepositoryTarget(
            owner="openedx",
            name=repository_name,
            requested_ref="18c954d8604df4740c829ba17fa2f3640b92b900",
        )
    )


def _submitting(*, repository_name: str = "mockprock"):
    """Build one leased SUBMITTING job."""
    identity = create_async_job_identity(
        _request(repository_name=repository_name),
        idempotency_key="client-key-0001",
    )
    return create_submitting_job(
        identity,
        lease_expires_at_epoch_seconds=_NOW + _SUBMISSION_LEASE_SECONDS,
    )


def test_async_identity_is_deterministic_reconstructable_and_key_is_not_exposed() -> None:
    """Bind identity to request/key hashes while retaining only normalized request semantics."""
    request = _request()
    first = create_async_job_identity(request, idempotency_key="client-key-0001")
    second = create_async_job_identity(request, idempotency_key="client-key-0001")

    assert first == second
    assert first.job_id.startswith("public-analysis-job:v1:")
    assert first.request_sha256 == request.request_sha256
    assert first.request == request
    assert first.repository_owner == "openedx"
    assert first.repository_name == "mockprock"
    assert first.idempotency_key_sha256 != "client-key-0001"
    assert "client-key-0001" not in first.job_id


def test_same_key_and_same_request_returns_existing_job() -> None:
    """Make idempotent replay return the exact existing leased job."""
    request = _request()
    first = decide_async_submission(
        request,
        idempotency_key="client-key-0001",
        existing_job=None,
        submission_lease_expires_at_epoch_seconds=_NOW + _SUBMISSION_LEASE_SECONDS,
        now_epoch_seconds=_NOW,
    )
    replay = decide_async_submission(
        request,
        idempotency_key="client-key-0001",
        existing_job=first.job,
        submission_lease_expires_at_epoch_seconds=_NOW + _SUBMISSION_LEASE_SECONDS,
        now_epoch_seconds=_NOW,
    )

    assert first.disposition is AsyncSubmissionDisposition.CREATE_NEW_JOB
    assert replay.disposition is AsyncSubmissionDisposition.RETURN_EXISTING_JOB
    assert replay.job == first.job


def test_expired_submitting_lease_is_resumable_without_rebinding_identity() -> None:
    """Permit queue resubmission only after the explicit SUBMITTING lease expires."""
    request = _request()
    submitting = create_submitting_job(
        create_async_job_identity(request, idempotency_key="client-key-0001"),
        lease_expires_at_epoch_seconds=_NOW,
    )

    decision = decide_async_submission(
        request,
        idempotency_key="client-key-0001",
        existing_job=submitting,
        submission_lease_expires_at_epoch_seconds=_NOW + _SUBMISSION_LEASE_SECONDS,
        now_epoch_seconds=_NOW,
    )
    refreshed = refresh_submitting_lease(
        decision.job,
        now_epoch_seconds=_NOW,
        lease_seconds=_SUBMISSION_LEASE_SECONDS,
    )

    assert decision.disposition is AsyncSubmissionDisposition.RESUME_EXPIRED_SUBMISSION
    assert refreshed.identity == submitting.identity
    assert refreshed.version == submitting.version + 1
    assert refreshed.lease_expires_at_epoch_seconds == _NOW + _SUBMISSION_LEASE_SECONDS


def test_same_key_and_different_request_is_conflict() -> None:
    """Reject rebinding one idempotency key to different request semantics."""
    first_request = _request(repository_name="mockprock")
    second_request = _request(repository_name="edx-platform")
    existing = decide_async_submission(
        first_request,
        idempotency_key="client-key-0001",
        existing_job=None,
        submission_lease_expires_at_epoch_seconds=_NOW + _SUBMISSION_LEASE_SECONDS,
        now_epoch_seconds=_NOW,
    ).job

    with pytest.raises(AsyncIdempotencyConflictError):
        decide_async_submission(
            second_request,
            idempotency_key="client-key-0001",
            existing_job=existing,
            submission_lease_expires_at_epoch_seconds=_NOW + _SUBMISSION_LEASE_SECONDS,
            now_epoch_seconds=_NOW,
        )


def test_running_worker_lease_blocks_duplicate_execution_until_expiry() -> None:
    """Keep at-least-once duplicate delivery from becoming concurrent provider execution."""
    accepted = accept_async_job(_submitting())
    running = claim_async_job_attempt(
        accepted,
        now_epoch_seconds=_NOW,
        lease_seconds=_WORKER_LEASE_SECONDS,
    )

    active = decide_worker_delivery(running, now_epoch_seconds=_NOW + 1)
    expired = decide_worker_delivery(
        running,
        now_epoch_seconds=_NOW + _WORKER_LEASE_SECONDS,
    )
    retry = claim_async_job_attempt(
        running,
        now_epoch_seconds=_NOW + _WORKER_LEASE_SECONDS,
        lease_seconds=_WORKER_LEASE_SECONDS,
    )

    assert running.attempt_count == 1
    assert active.disposition is AsyncWorkerDisposition.NOOP_ACTIVE_LEASE
    assert expired.disposition is AsyncWorkerDisposition.CLAIM_ATTEMPT
    assert retry.attempt_count == 2
    assert retry.version == running.version + 1


def test_running_transition_without_explicit_lease_fails_closed() -> None:
    """Prevent generic state mutation from bypassing worker lease authority."""
    accepted = accept_async_job(_submitting())

    with pytest.raises(PublicAnalysisValidationError):
        transition_async_job(accepted, target_state=AsyncJobState.RUNNING)


def test_success_requires_claimed_running_and_persists_result_integrity() -> None:
    """Persist hash and byte count only for one admitted leased RUNNING result."""
    running = claim_async_job_attempt(
        accept_async_job(_submitting()),
        now_epoch_seconds=_NOW,
        lease_seconds=_WORKER_LEASE_SECONDS,
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
    assert succeeded.lease_expires_at_epoch_seconds is None


def test_failure_requires_explicit_bounded_code_and_clears_lease() -> None:
    """Terminalize one non-terminal job with deterministic failure evidence."""
    accepted = accept_async_job(_submitting())
    failed = complete_async_job_failure(accepted, failure_code="QUEUE_PUBLISH_FAILED")

    assert failed.state is AsyncJobState.FAILED
    assert failed.failure_code == "QUEUE_PUBLISH_FAILED"
    assert failed.lease_expires_at_epoch_seconds is None


def test_terminal_duplicate_delivery_is_noop() -> None:
    """Keep terminal business truth separate from later queue redelivery."""
    running = claim_async_job_attempt(
        accept_async_job(_submitting()),
        now_epoch_seconds=_NOW,
        lease_seconds=_WORKER_LEASE_SECONDS,
    )
    succeeded = complete_async_job_success(running, serialized_result=b'{"status":"ok"}')

    decision = decide_worker_delivery(succeeded, now_epoch_seconds=_NOW + 1)

    assert decision.disposition is AsyncWorkerDisposition.NOOP_ALREADY_TERMINAL
    assert decision.job == succeeded


def test_expiry_removes_inline_result_payload() -> None:
    """Remove result material when a successful job crosses the explicit expiry transition."""
    running = claim_async_job_attempt(
        accept_async_job(_submitting()),
        now_epoch_seconds=_NOW,
        lease_seconds=_WORKER_LEASE_SECONDS,
    )
    succeeded = complete_async_job_success(running, serialized_result=b'{"status":"ok"}')
    expired = transition_async_job(succeeded, target_state=AsyncJobState.EXPIRED)

    assert expired.state is AsyncJobState.EXPIRED
    assert expired.result_sha256 is None
    assert expired.result_bytes is None
    assert expired.result_json is None
    assert expired.lease_expires_at_epoch_seconds is None
    assert (
        decide_worker_delivery(expired, now_epoch_seconds=_NOW + 1).disposition
        is AsyncWorkerDisposition.NOOP_EXPIRED
    )


@pytest.mark.parametrize(
    "value",
    ["short", "has space", "a" * 129, "ümlaut-key"],
)
def test_idempotency_key_validation_is_bounded(value: str) -> None:
    """Reject keys outside the frozen ASCII and length envelope."""
    with pytest.raises(PublicAnalysisValidationError):
        validate_idempotency_key(value)
