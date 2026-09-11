"""Provider-neutral async submission and duplicate-delivery admission decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from opslens.public_analysis.domain.async_job import (
    AsyncJobRecord,
    AsyncJobState,
    create_async_job_identity,
    create_submitting_job,
)
from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.public_analysis.domain.request import PublicAnalysisRequest


class AsyncSubmissionDisposition(StrEnum):
    """Deterministic outcomes for one idempotent submit request."""

    CREATE_NEW_JOB = "CREATE_NEW_JOB"
    RETURN_EXISTING_JOB = "RETURN_EXISTING_JOB"
    RESUME_EXPIRED_SUBMISSION = "RESUME_EXPIRED_SUBMISSION"


class AsyncWorkerDisposition(StrEnum):
    """Deterministic outcomes for one at-least-once queue delivery."""

    CLAIM_ATTEMPT = "CLAIM_ATTEMPT"
    NOOP_ACTIVE_LEASE = "NOOP_ACTIVE_LEASE"
    NOOP_ALREADY_TERMINAL = "NOOP_ALREADY_TERMINAL"
    NOOP_EXPIRED = "NOOP_EXPIRED"


class AsyncIdempotencyConflictError(PublicAnalysisValidationError):
    """Raised when one idempotency key is rebound to different request semantics."""


@dataclass(frozen=True, slots=True)
class AsyncSubmissionDecision:
    """One provider-neutral idempotent submission decision."""

    disposition: AsyncSubmissionDisposition
    job: AsyncJobRecord


@dataclass(frozen=True, slots=True)
class AsyncWorkerDecision:
    """One provider-neutral duplicate-delivery admission decision."""

    disposition: AsyncWorkerDisposition
    job: AsyncJobRecord


def decide_async_submission(
    request: PublicAnalysisRequest,
    *,
    idempotency_key: str,
    existing_job: AsyncJobRecord | None,
    submission_lease_expires_at_epoch_seconds: int,
    now_epoch_seconds: int,
) -> AsyncSubmissionDecision:
    """Decide whether submit creates, replays, or resumes an expired submission lease."""
    identity = create_async_job_identity(request, idempotency_key=idempotency_key)
    if type(now_epoch_seconds) is not int or now_epoch_seconds <= 0:
        raise PublicAnalysisValidationError("now_epoch_seconds must be a positive integer")
    if existing_job is None:
        return AsyncSubmissionDecision(
            disposition=AsyncSubmissionDisposition.CREATE_NEW_JOB,
            job=create_submitting_job(
                identity,
                lease_expires_at_epoch_seconds=submission_lease_expires_at_epoch_seconds,
            ),
        )
    if type(existing_job) is not AsyncJobRecord:
        raise PublicAnalysisValidationError("existing_job must be AsyncJobRecord or None")
    if existing_job.identity.idempotency_key_sha256 != identity.idempotency_key_sha256:
        raise PublicAnalysisValidationError(
            "existing idempotency lookup returned a job bound to a different key"
        )
    if existing_job.identity.request_sha256 != identity.request_sha256:
        raise AsyncIdempotencyConflictError(
            "Idempotency-Key is already bound to different request semantics"
        )
    if existing_job.identity != identity:
        raise PublicAnalysisValidationError(
            "existing job identity does not match deterministic request/key identity"
        )
    if (
        existing_job.state is AsyncJobState.SUBMITTING
        and existing_job.lease_expires_at_epoch_seconds is not None
        and existing_job.lease_expires_at_epoch_seconds <= now_epoch_seconds
    ):
        return AsyncSubmissionDecision(
            disposition=AsyncSubmissionDisposition.RESUME_EXPIRED_SUBMISSION,
            job=existing_job,
        )
    return AsyncSubmissionDecision(
        disposition=AsyncSubmissionDisposition.RETURN_EXISTING_JOB,
        job=existing_job,
    )


def decide_worker_delivery(
    job: AsyncJobRecord,
    *,
    now_epoch_seconds: int,
) -> AsyncWorkerDecision:
    """Admit or no-op one delivery using deterministic state plus explicit worker lease."""
    if type(job) is not AsyncJobRecord:
        raise PublicAnalysisValidationError("job must be AsyncJobRecord")
    if type(now_epoch_seconds) is not int or now_epoch_seconds <= 0:
        raise PublicAnalysisValidationError("now_epoch_seconds must be a positive integer")
    if job.state in {AsyncJobState.SUCCEEDED, AsyncJobState.FAILED}:
        return AsyncWorkerDecision(
            disposition=AsyncWorkerDisposition.NOOP_ALREADY_TERMINAL,
            job=job,
        )
    if job.state is AsyncJobState.EXPIRED:
        return AsyncWorkerDecision(
            disposition=AsyncWorkerDisposition.NOOP_EXPIRED,
            job=job,
        )
    if (
        job.state is AsyncJobState.RUNNING
        and job.lease_expires_at_epoch_seconds is not None
        and job.lease_expires_at_epoch_seconds > now_epoch_seconds
    ):
        return AsyncWorkerDecision(
            disposition=AsyncWorkerDisposition.NOOP_ACTIVE_LEASE,
            job=job,
        )
    return AsyncWorkerDecision(
        disposition=AsyncWorkerDisposition.CLAIM_ATTEMPT,
        job=job,
    )


__all__ = [
    "AsyncIdempotencyConflictError",
    "AsyncSubmissionDecision",
    "AsyncSubmissionDisposition",
    "AsyncWorkerDecision",
    "AsyncWorkerDisposition",
    "decide_async_submission",
    "decide_worker_delivery",
]
