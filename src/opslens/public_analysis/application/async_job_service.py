"""Provider-neutral use cases for the Gate 19.4 asynchronous job lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from opslens.public_analysis.application.async_job_admission import (
    AsyncSubmissionDisposition,
    AsyncWorkerDisposition,
    decide_async_submission,
    decide_worker_delivery,
)
from opslens.public_analysis.domain.async_job import (
    AsyncJobRecord,
    AsyncJobState,
    complete_async_job_failure,
    create_async_job_identity,
    transition_async_job,
)
from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.public_analysis.domain.request import PublicAnalysisRequest


class AsyncQueuePublishError(RuntimeError):
    """Raised by the queue port when one job message was not admitted for delivery."""


class AsyncSubmissionUnavailableError(RuntimeError):
    """Raised after deterministic job state records a queue-publication failure."""


class AsyncJobNotFoundError(LookupError):
    """Raised when an async job id has no admitted state authority."""


class AsyncResultNotReadyError(RuntimeError):
    """Raised when result retrieval is attempted before successful terminalization."""


class AsyncResultExpiredError(RuntimeError):
    """Raised when result retrieval is attempted after explicit expiry."""


class AsyncClaimDisposition(StrEnum):
    """Deterministic outcomes for one worker attempt claim."""

    CLAIMED = "CLAIMED"
    NOOP_ALREADY_TERMINAL = "NOOP_ALREADY_TERMINAL"
    NOOP_EXPIRED = "NOOP_EXPIRED"
    NOOP_CONCURRENT_CLAIM = "NOOP_CONCURRENT_CLAIM"


@dataclass(frozen=True, slots=True)
class AsyncJobPutOutcome:
    """Result of one atomic create-if-absent job-store operation."""

    created: bool
    job: AsyncJobRecord


@dataclass(frozen=True, slots=True)
class AsyncSubmitResult:
    """Application result for one idempotent submit use case."""

    disposition: AsyncSubmissionDisposition
    job: AsyncJobRecord


@dataclass(frozen=True, slots=True)
class AsyncClaimResult:
    """Application result for one at-least-once worker delivery claim."""

    disposition: AsyncClaimDisposition
    job: AsyncJobRecord


class AsyncJobStore(Protocol):
    """Conditional persistence authority required by the async application layer."""

    def get_by_idempotency_key_sha256(self, digest: str) -> AsyncJobRecord | None:
        """Return the job bound to one hashed idempotency key, when present."""
        ...

    def put_if_absent(self, job: AsyncJobRecord) -> AsyncJobPutOutcome:
        """Atomically create one SUBMITTING job or return the already-bound job."""
        ...

    def get(self, job_id: str) -> AsyncJobRecord | None:
        """Return one admitted job by deterministic job id."""
        ...

    def replace_if_current(
        self,
        *,
        current: AsyncJobRecord,
        replacement: AsyncJobRecord,
    ) -> bool:
        """Atomically replace exactly the expected current job state."""
        ...


class AsyncJobPublisher(Protocol):
    """Outbound queue publication boundary for one admitted job id."""

    def publish(self, job_id: str) -> None:
        """Publish one admitted job id or raise AsyncQueuePublishError."""
        ...


def _load_required_job(store: AsyncJobStore, job_id: str) -> AsyncJobRecord:
    """Load one job or map persistence absence to the public application contract."""
    if type(job_id) is not str or not job_id:
        raise PublicAnalysisValidationError("job_id must be a non-empty string")
    job = store.get(job_id)
    if job is None:
        raise AsyncJobNotFoundError("async job was not found")
    if type(job) is not AsyncJobRecord:
        raise PublicAnalysisValidationError("job store returned a non-admitted job value")
    return job


def submit_async_analysis(
    request: PublicAnalysisRequest,
    *,
    idempotency_key: str,
    store: AsyncJobStore,
    publisher: AsyncJobPublisher,
) -> AsyncSubmitResult:
    """Create or replay one async job without coupling queue delivery to business truth."""
    identity = create_async_job_identity(request, idempotency_key=idempotency_key)
    existing = store.get_by_idempotency_key_sha256(identity.idempotency_key_sha256)
    decision = decide_async_submission(
        request,
        idempotency_key=idempotency_key,
        existing_job=existing,
    )
    if decision.disposition is AsyncSubmissionDisposition.RETURN_EXISTING_JOB:
        return AsyncSubmitResult(disposition=decision.disposition, job=decision.job)

    put = store.put_if_absent(decision.job)
    if type(put) is not AsyncJobPutOutcome:
        raise PublicAnalysisValidationError("job store returned an invalid put outcome")
    if not put.created:
        raced = decide_async_submission(
            request,
            idempotency_key=idempotency_key,
            existing_job=put.job,
        )
        return AsyncSubmitResult(disposition=raced.disposition, job=raced.job)

    try:
        publisher.publish(put.job.identity.job_id)
    except AsyncQueuePublishError as exc:
        failed = complete_async_job_failure(put.job, failure_code="QUEUE_PUBLISH_FAILED")
        store.replace_if_current(current=put.job, replacement=failed)
        raise AsyncSubmissionUnavailableError("async job queue publication failed") from exc

    accepted = transition_async_job(put.job, target_state=AsyncJobState.ACCEPTED)
    if store.replace_if_current(current=put.job, replacement=accepted):
        return AsyncSubmitResult(
            disposition=AsyncSubmissionDisposition.CREATE_NEW_JOB,
            job=accepted,
        )

    latest = _load_required_job(store, put.job.identity.job_id)
    return AsyncSubmitResult(
        disposition=AsyncSubmissionDisposition.CREATE_NEW_JOB,
        job=latest,
    )


def claim_async_worker_attempt(
    *,
    job_id: str,
    store: AsyncJobStore,
) -> AsyncClaimResult:
    """Conditionally claim one delivery attempt without retrying a lost claim in-process."""
    current = _load_required_job(store, job_id)
    admission = decide_worker_delivery(current)
    if admission.disposition is AsyncWorkerDisposition.NOOP_ALREADY_TERMINAL:
        return AsyncClaimResult(
            disposition=AsyncClaimDisposition.NOOP_ALREADY_TERMINAL,
            job=current,
        )
    if admission.disposition is AsyncWorkerDisposition.NOOP_EXPIRED:
        return AsyncClaimResult(
            disposition=AsyncClaimDisposition.NOOP_EXPIRED,
            job=current,
        )

    running = transition_async_job(current, target_state=AsyncJobState.RUNNING)
    if store.replace_if_current(current=current, replacement=running):
        return AsyncClaimResult(disposition=AsyncClaimDisposition.CLAIMED, job=running)

    latest = _load_required_job(store, job_id)
    return AsyncClaimResult(
        disposition=AsyncClaimDisposition.NOOP_CONCURRENT_CLAIM,
        job=latest,
    )


def get_async_job_status(*, job_id: str, store: AsyncJobStore) -> AsyncJobRecord:
    """Return one admitted job status projection without changing lifecycle state."""
    return _load_required_job(store, job_id)


def get_async_job_result(*, job_id: str, store: AsyncJobStore) -> str:
    """Return the admitted inline result only for SUCCEEDED non-expired jobs."""
    job = _load_required_job(store, job_id)
    if job.state is AsyncJobState.EXPIRED:
        raise AsyncResultExpiredError("async job result has expired")
    if job.state is not AsyncJobState.SUCCEEDED or job.result_json is None:
        raise AsyncResultNotReadyError("async job result is not available")
    return job.result_json


__all__ = [
    "AsyncClaimDisposition",
    "AsyncClaimResult",
    "AsyncJobNotFoundError",
    "AsyncJobPublisher",
    "AsyncJobPutOutcome",
    "AsyncJobStore",
    "AsyncQueuePublishError",
    "AsyncResultExpiredError",
    "AsyncResultNotReadyError",
    "AsyncSubmissionUnavailableError",
    "AsyncSubmitResult",
    "claim_async_worker_attempt",
    "get_async_job_result",
    "get_async_job_status",
    "submit_async_analysis",
]
