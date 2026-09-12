"""Provider-neutral use cases for the Gate 19.4 asynchronous job lifecycle."""

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
    accept_async_job,
    claim_async_job_attempt,
    complete_async_job_failure,
    complete_async_job_success,
    create_async_job_identity,
    refresh_submitting_lease,
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


class AsyncWorkerStateConflictError(RuntimeError):
    """Raised when a stale worker attempt can no longer terminalize the admitted job."""


class AsyncClaimDisposition(StrEnum):
    """Deterministic outcomes for one worker attempt claim."""

    CLAIMED = "CLAIMED"
    NOOP_ACTIVE_LEASE = "NOOP_ACTIVE_LEASE"
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
        """Atomically replace exactly the expected current job state and version."""
        ...


class AsyncJobPublisher(Protocol):
    """Outbound queue publication boundary for one admitted job id."""

    def publish(self, job_id: str) -> None:
        """Publish one admitted job id or raise AsyncQueuePublishError."""
        ...


def _positive_int(value: int, *, field: str) -> int:
    """Require one positive non-boolean integer configuration value."""
    if type(value) is not int or value <= 0:
        raise PublicAnalysisValidationError(f"{field} must be a positive integer")
    return value


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


def _publish_and_accept(
    *,
    job: AsyncJobRecord,
    disposition: AsyncSubmissionDisposition,
    store: AsyncJobStore,
    publisher: AsyncJobPublisher,
) -> AsyncSubmitResult:
    """Cross the explicit DynamoDB/SQS dual-write boundary without claiming atomicity."""
    try:
        publisher.publish(job.identity.job_id)
    except AsyncQueuePublishError as exc:
        failed = complete_async_job_failure(job, failure_code="QUEUE_PUBLISH_FAILED")
        if not store.replace_if_current(current=job, replacement=failed):
            latest = _load_required_job(store, job.identity.job_id)
            return AsyncSubmitResult(
                disposition=AsyncSubmissionDisposition.RETURN_EXISTING_JOB,
                job=latest,
            )
        raise AsyncSubmissionUnavailableError("async job queue publication failed") from exc

    accepted = accept_async_job(job)
    if store.replace_if_current(current=job, replacement=accepted):
        return AsyncSubmitResult(disposition=disposition, job=accepted)

    latest = _load_required_job(store, job.identity.job_id)
    return AsyncSubmitResult(disposition=disposition, job=latest)


def submit_async_analysis(
    request: PublicAnalysisRequest,
    *,
    idempotency_key: str,
    store: AsyncJobStore,
    publisher: AsyncJobPublisher,
    now_epoch_seconds: int,
    submission_lease_seconds: int,
) -> AsyncSubmitResult:
    """Create, replay, or safely resume one expired SUBMITTING job."""
    now = _positive_int(now_epoch_seconds, field="now_epoch_seconds")
    lease_seconds = _positive_int(
        submission_lease_seconds,
        field="submission_lease_seconds",
    )
    lease_deadline = now + lease_seconds
    identity = create_async_job_identity(request, idempotency_key=idempotency_key)
    existing = store.get_by_idempotency_key_sha256(identity.idempotency_key_sha256)
    decision = decide_async_submission(
        request,
        idempotency_key=idempotency_key,
        existing_job=existing,
        submission_lease_expires_at_epoch_seconds=lease_deadline,
        now_epoch_seconds=now,
    )

    if decision.disposition is AsyncSubmissionDisposition.RETURN_EXISTING_JOB:
        return AsyncSubmitResult(disposition=decision.disposition, job=decision.job)

    if decision.disposition is AsyncSubmissionDisposition.CREATE_NEW_JOB:
        put = store.put_if_absent(decision.job)
        if type(put) is not AsyncJobPutOutcome:
            raise PublicAnalysisValidationError("job store returned an invalid put outcome")
        if put.created:
            return _publish_and_accept(
                job=put.job,
                disposition=decision.disposition,
                store=store,
                publisher=publisher,
            )
        decision = decide_async_submission(
            request,
            idempotency_key=idempotency_key,
            existing_job=put.job,
            submission_lease_expires_at_epoch_seconds=lease_deadline,
            now_epoch_seconds=now,
        )
        if decision.disposition is AsyncSubmissionDisposition.RETURN_EXISTING_JOB:
            return AsyncSubmitResult(disposition=decision.disposition, job=decision.job)

    if decision.disposition is not AsyncSubmissionDisposition.RESUME_EXPIRED_SUBMISSION:
        raise PublicAnalysisValidationError("async submission decision is not supported")

    refreshed = refresh_submitting_lease(
        decision.job,
        now_epoch_seconds=now,
        lease_seconds=lease_seconds,
    )
    if not store.replace_if_current(current=decision.job, replacement=refreshed):
        latest = _load_required_job(store, decision.job.identity.job_id)
        return AsyncSubmitResult(
            disposition=AsyncSubmissionDisposition.RETURN_EXISTING_JOB,
            job=latest,
        )
    return _publish_and_accept(
        job=refreshed,
        disposition=AsyncSubmissionDisposition.RESUME_EXPIRED_SUBMISSION,
        store=store,
        publisher=publisher,
    )


def claim_async_worker_attempt(
    *,
    job_id: str,
    store: AsyncJobStore,
    now_epoch_seconds: int,
    worker_lease_seconds: int,
) -> AsyncClaimResult:
    """Conditionally claim one delivery without overlapping an active RUNNING lease."""
    now = _positive_int(now_epoch_seconds, field="now_epoch_seconds")
    lease_seconds = _positive_int(worker_lease_seconds, field="worker_lease_seconds")
    current = _load_required_job(store, job_id)
    admission = decide_worker_delivery(current, now_epoch_seconds=now)
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
    if admission.disposition is AsyncWorkerDisposition.NOOP_ACTIVE_LEASE:
        return AsyncClaimResult(
            disposition=AsyncClaimDisposition.NOOP_ACTIVE_LEASE,
            job=current,
        )

    running = claim_async_job_attempt(
        current,
        now_epoch_seconds=now,
        lease_seconds=lease_seconds,
    )
    if store.replace_if_current(current=current, replacement=running):
        return AsyncClaimResult(disposition=AsyncClaimDisposition.CLAIMED, job=running)

    latest = _load_required_job(store, job_id)
    return AsyncClaimResult(
        disposition=AsyncClaimDisposition.NOOP_CONCURRENT_CLAIM,
        job=latest,
    )


def complete_claimed_async_worker_success(
    *,
    claimed_job: AsyncJobRecord,
    serialized_result: bytes,
    store: AsyncJobStore,
) -> AsyncJobRecord:
    """Conditionally persist one result only for the exact worker claim version."""
    succeeded = complete_async_job_success(
        claimed_job,
        serialized_result=serialized_result,
    )
    if store.replace_if_current(current=claimed_job, replacement=succeeded):
        return succeeded
    latest = _load_required_job(store, claimed_job.identity.job_id)
    if (
        latest.state is AsyncJobState.SUCCEEDED
        and latest.result_sha256 == succeeded.result_sha256
        and latest.result_bytes == succeeded.result_bytes
        and latest.result_json == succeeded.result_json
    ):
        return latest
    raise AsyncWorkerStateConflictError(
        "stale worker attempt cannot overwrite the current async job state"
    )


def complete_claimed_async_worker_failure(
    *,
    claimed_job: AsyncJobRecord,
    failure_code: str,
    store: AsyncJobStore,
) -> AsyncJobRecord:
    """Conditionally terminalize one claimed attempt with an explicit bounded failure code."""
    failed = complete_async_job_failure(claimed_job, failure_code=failure_code)
    if store.replace_if_current(current=claimed_job, replacement=failed):
        return failed
    latest = _load_required_job(store, claimed_job.identity.job_id)
    if latest.state in {AsyncJobState.FAILED, AsyncJobState.EXPIRED}:
        return latest
    raise AsyncWorkerStateConflictError(
        "stale worker attempt cannot overwrite the current async job state"
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
    "AsyncWorkerStateConflictError",
    "claim_async_worker_attempt",
    "complete_claimed_async_worker_failure",
    "complete_claimed_async_worker_success",
    "get_async_job_result",
    "get_async_job_status",
    "submit_async_analysis",
]
