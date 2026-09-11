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


class AsyncWorkerDisposition(StrEnum):
    """Deterministic outcomes for one at-least-once queue delivery."""

    CLAIM_ATTEMPT = "CLAIM_ATTEMPT"
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
) -> AsyncSubmissionDecision:
    """Decide whether a submit creates a job, reuses it, or fails on key conflict."""
    identity = create_async_job_identity(request, idempotency_key=idempotency_key)
    if existing_job is None:
        return AsyncSubmissionDecision(
            disposition=AsyncSubmissionDisposition.CREATE_NEW_JOB,
            job=create_submitting_job(identity),
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
    if existing_job.identity.job_id != identity.job_id:
        raise PublicAnalysisValidationError(
            "existing job identity does not match deterministic request/key identity"
        )
    return AsyncSubmissionDecision(
        disposition=AsyncSubmissionDisposition.RETURN_EXISTING_JOB,
        job=existing_job,
    )


def decide_worker_delivery(job: AsyncJobRecord) -> AsyncWorkerDecision:
    """Admit or no-op one SQS delivery without treating delivery as execution authority."""
    if type(job) is not AsyncJobRecord:
        raise PublicAnalysisValidationError("job must be AsyncJobRecord")
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
