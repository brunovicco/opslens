"""Provider-neutral bounded execution service for one asynchronous public-analysis attempt."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from opslens.public_analysis.application.async_job_service import (
    AsyncClaimDisposition,
    AsyncJobStore,
    claim_async_worker_attempt,
    complete_claimed_async_worker_failure,
    complete_claimed_async_worker_success,
)
from opslens.public_analysis.domain.async_job import AsyncJobRecord
from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.public_analysis.domain.request import PublicAnalysisRequest


class AsyncAnalysisExecutor(Protocol):
    """Provider-heavy execution boundary entered only after a deterministic worker claim."""

    def execute(self, request: PublicAnalysisRequest) -> bytes:
        """Return one admitted serialized result or raise an execution failure."""
        ...


class AsyncWorkerExecutionDisposition(StrEnum):
    """Deterministic message-level outcomes for one SQS worker delivery."""

    ACK_SUCCEEDED = "ACK_SUCCEEDED"
    ACK_ALREADY_TERMINAL = "ACK_ALREADY_TERMINAL"
    ACK_EXPIRED = "ACK_EXPIRED"
    ACK_ATTEMPT_LIMIT_FAILED = "ACK_ATTEMPT_LIMIT_FAILED"
    RETAIN_ACTIVE_LEASE = "RETAIN_ACTIVE_LEASE"
    RETAIN_CONCURRENT_CLAIM = "RETAIN_CONCURRENT_CLAIM"


@dataclass(frozen=True, slots=True)
class AsyncWorkerExecutionResult:
    """One bounded worker result used by the SQS event adapter."""

    disposition: AsyncWorkerExecutionDisposition
    job: AsyncJobRecord


def execute_async_worker_delivery(
    *,
    job_id: str,
    store: AsyncJobStore,
    executor: AsyncAnalysisExecutor,
    now_epoch_seconds: int,
    worker_lease_seconds: int,
    max_attempts: int,
) -> AsyncWorkerExecutionResult:
    """Claim, execute, and conditionally terminalize one asynchronous job delivery."""
    if type(max_attempts) is not int or max_attempts <= 0:
        raise PublicAnalysisValidationError("max_attempts must be a positive integer")

    claim = claim_async_worker_attempt(
        job_id=job_id,
        store=store,
        now_epoch_seconds=now_epoch_seconds,
        worker_lease_seconds=worker_lease_seconds,
    )
    if claim.disposition is AsyncClaimDisposition.NOOP_ALREADY_TERMINAL:
        return AsyncWorkerExecutionResult(
            disposition=AsyncWorkerExecutionDisposition.ACK_ALREADY_TERMINAL,
            job=claim.job,
        )
    if claim.disposition is AsyncClaimDisposition.NOOP_EXPIRED:
        return AsyncWorkerExecutionResult(
            disposition=AsyncWorkerExecutionDisposition.ACK_EXPIRED,
            job=claim.job,
        )
    if claim.disposition is AsyncClaimDisposition.NOOP_ACTIVE_LEASE:
        return AsyncWorkerExecutionResult(
            disposition=AsyncWorkerExecutionDisposition.RETAIN_ACTIVE_LEASE,
            job=claim.job,
        )
    if claim.disposition is AsyncClaimDisposition.NOOP_CONCURRENT_CLAIM:
        return AsyncWorkerExecutionResult(
            disposition=AsyncWorkerExecutionDisposition.RETAIN_CONCURRENT_CLAIM,
            job=claim.job,
        )

    try:
        serialized_result = executor.execute(claim.job.identity.request)
    except Exception:
        if claim.job.attempt_count >= max_attempts:
            failed = complete_claimed_async_worker_failure(
                claimed_job=claim.job,
                failure_code="EXECUTION_ATTEMPT_LIMIT",
                store=store,
            )
            return AsyncWorkerExecutionResult(
                disposition=AsyncWorkerExecutionDisposition.ACK_ATTEMPT_LIMIT_FAILED,
                job=failed,
            )
        raise

    succeeded = complete_claimed_async_worker_success(
        claimed_job=claim.job,
        serialized_result=serialized_result,
        store=store,
    )
    return AsyncWorkerExecutionResult(
        disposition=AsyncWorkerExecutionDisposition.ACK_SUCCEEDED,
        job=succeeded,
    )


__all__ = [
    "AsyncAnalysisExecutor",
    "AsyncWorkerExecutionDisposition",
    "AsyncWorkerExecutionResult",
    "execute_async_worker_delivery",
]
