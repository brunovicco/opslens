"""Deterministic authority for the Phase 19 asynchronous public-analysis job lifecycle."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import StrEnum
from hashlib import sha256

from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.public_analysis.domain.request import PublicAnalysisRequest

ASYNC_JOB_CONTRACT_VERSION = "public-analysis-job:v1"

_IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$", re.ASCII)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_JOB_ID_PATTERN = re.compile(r"^public-analysis-job:v1:[0-9a-f]{64}$", re.ASCII)
_FAILURE_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$", re.ASCII)


class AsyncJobState(StrEnum):
    """Frozen Gate 19.3 asynchronous job states."""

    SUBMITTING = "SUBMITTING"
    ACCEPTED = "ACCEPTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


_ALLOWED_TRANSITIONS = frozenset(
    {
        (AsyncJobState.SUBMITTING, AsyncJobState.ACCEPTED),
        (AsyncJobState.SUBMITTING, AsyncJobState.RUNNING),
        (AsyncJobState.SUBMITTING, AsyncJobState.FAILED),
        (AsyncJobState.ACCEPTED, AsyncJobState.RUNNING),
        (AsyncJobState.ACCEPTED, AsyncJobState.FAILED),
        (AsyncJobState.RUNNING, AsyncJobState.RUNNING),
        (AsyncJobState.RUNNING, AsyncJobState.SUCCEEDED),
        (AsyncJobState.RUNNING, AsyncJobState.FAILED),
        (AsyncJobState.SUBMITTING, AsyncJobState.EXPIRED),
        (AsyncJobState.ACCEPTED, AsyncJobState.EXPIRED),
        (AsyncJobState.RUNNING, AsyncJobState.EXPIRED),
        (AsyncJobState.SUCCEEDED, AsyncJobState.EXPIRED),
        (AsyncJobState.FAILED, AsyncJobState.EXPIRED),
    }
)


@dataclass(frozen=True, slots=True)
class AsyncJobIdentity:
    """Content-addressed async job identity bound to request and idempotency key."""

    job_id: str
    idempotency_key_sha256: str
    request_id: str
    request_sha256: str

    def __post_init__(self) -> None:
        """Reject forged or malformed async identity values."""
        if type(self.job_id) is not str or _JOB_ID_PATTERN.fullmatch(self.job_id) is None:
            raise PublicAnalysisValidationError("job_id violates the async job identity contract")
        if (
            type(self.idempotency_key_sha256) is not str
            or _SHA256_PATTERN.fullmatch(self.idempotency_key_sha256) is None
        ):
            raise PublicAnalysisValidationError("idempotency_key_sha256 must be lowercase SHA-256")
        if type(self.request_id) is not str or not self.request_id:
            raise PublicAnalysisValidationError("request_id must be a non-empty string")
        if (
            type(self.request_sha256) is not str
            or _SHA256_PATTERN.fullmatch(self.request_sha256) is None
        ):
            raise PublicAnalysisValidationError("request_sha256 must be lowercase SHA-256")

        expected_job_digest = sha256(
            f"{self.idempotency_key_sha256}:{self.request_sha256}".encode("ascii")
        ).hexdigest()
        expected_job_id = f"{ASYNC_JOB_CONTRACT_VERSION}:{expected_job_digest}"
        if self.job_id != expected_job_id:
            raise PublicAnalysisValidationError(
                "job_id must match the idempotency-key/request content identity"
            )


@dataclass(frozen=True, slots=True)
class AsyncJobRecord:
    """Deterministic job state and admitted terminal evidence."""

    identity: AsyncJobIdentity
    state: AsyncJobState
    attempt_count: int = 0
    version: int = 0
    result_sha256: str | None = None
    result_bytes: int | None = None
    result_json: str | None = None
    failure_code: str | None = None

    def __post_init__(self) -> None:
        """Enforce state-specific result, failure, version, and attempt invariants."""
        if type(self.identity) is not AsyncJobIdentity:
            raise PublicAnalysisValidationError("identity must be AsyncJobIdentity")
        if type(self.state) is not AsyncJobState:
            raise PublicAnalysisValidationError("state must be AsyncJobState")
        if type(self.attempt_count) is not int or self.attempt_count < 0:
            raise PublicAnalysisValidationError("attempt_count must be a non-negative integer")
        if type(self.version) is not int or self.version < 0:
            raise PublicAnalysisValidationError("version must be a non-negative integer")

        has_any_result = any(
            value is not None
            for value in (self.result_sha256, self.result_bytes, self.result_json)
        )
        has_complete_result = (
            type(self.result_sha256) is str
            and _SHA256_PATTERN.fullmatch(self.result_sha256) is not None
            and type(self.result_bytes) is int
            and self.result_bytes > 0
            and type(self.result_json) is str
            and bool(self.result_json)
        )
        if self.state is AsyncJobState.SUCCEEDED:
            if not has_complete_result:
                raise PublicAnalysisValidationError(
                    "SUCCEEDED jobs require complete admitted result metadata and payload"
                )
            if self.failure_code is not None:
                raise PublicAnalysisValidationError("SUCCEEDED jobs cannot carry a failure_code")
        elif has_any_result:
            raise PublicAnalysisValidationError(
                "only SUCCEEDED jobs may carry admitted result metadata and payload"
            )

        if self.failure_code is not None:
            if (
                type(self.failure_code) is not str
                or _FAILURE_CODE_PATTERN.fullmatch(self.failure_code) is None
            ):
                raise PublicAnalysisValidationError(
                    "failure_code violates the frozen code contract"
                )
            if self.state not in {AsyncJobState.FAILED, AsyncJobState.EXPIRED}:
                raise PublicAnalysisValidationError(
                    "failure_code is allowed only for FAILED or expired-from-failure jobs"
                )
        elif self.state is AsyncJobState.FAILED:
            raise PublicAnalysisValidationError("FAILED jobs require a failure_code")


def validate_idempotency_key(value: str) -> str:
    """Validate and return one bounded public idempotency key without normalization."""
    if type(value) is not str or _IDEMPOTENCY_KEY_PATTERN.fullmatch(value) is None:
        raise PublicAnalysisValidationError(
            "Idempotency-Key must be 8-128 ASCII characters from [A-Za-z0-9._:-]"
        )
    return value


def create_async_job_identity(
    request: PublicAnalysisRequest,
    *,
    idempotency_key: str,
) -> AsyncJobIdentity:
    """Create deterministic async identity from an admitted request and idempotency key."""
    if type(request) is not PublicAnalysisRequest:
        raise PublicAnalysisValidationError("request must be PublicAnalysisRequest")
    key = validate_idempotency_key(idempotency_key)
    key_sha256 = sha256(key.encode("ascii")).hexdigest()
    job_digest = sha256(f"{key_sha256}:{request.request_sha256}".encode("ascii")).hexdigest()
    return AsyncJobIdentity(
        job_id=f"{ASYNC_JOB_CONTRACT_VERSION}:{job_digest}",
        idempotency_key_sha256=key_sha256,
        request_id=request.request_id,
        request_sha256=request.request_sha256,
    )


def create_submitting_job(identity: AsyncJobIdentity) -> AsyncJobRecord:
    """Create the only valid initial async job state."""
    if type(identity) is not AsyncJobIdentity:
        raise PublicAnalysisValidationError("identity must be AsyncJobIdentity")
    return AsyncJobRecord(identity=identity, state=AsyncJobState.SUBMITTING)


def transition_async_job(
    job: AsyncJobRecord,
    *,
    target_state: AsyncJobState,
) -> AsyncJobRecord:
    """Apply one exact Gate 19.3 state transition or fail closed."""
    if type(job) is not AsyncJobRecord:
        raise PublicAnalysisValidationError("job must be AsyncJobRecord")
    if type(target_state) is not AsyncJobState:
        raise PublicAnalysisValidationError("target_state must be AsyncJobState")
    if (job.state, target_state) not in _ALLOWED_TRANSITIONS:
        raise PublicAnalysisValidationError(
            f"async job transition {job.state.value}->{target_state.value} is not allowed"
        )
    if target_state is AsyncJobState.SUCCEEDED:
        raise PublicAnalysisValidationError(
            "SUCCEEDED requires complete_async_job_success with admitted result evidence"
        )
    if target_state is AsyncJobState.FAILED:
        raise PublicAnalysisValidationError(
            "FAILED requires complete_async_job_failure with an explicit failure code"
        )
    if target_state is AsyncJobState.RUNNING:
        return replace(
            job,
            state=target_state,
            attempt_count=job.attempt_count + 1,
            version=job.version + 1,
        )
    if target_state is AsyncJobState.EXPIRED:
        return replace(
            job,
            state=target_state,
            version=job.version + 1,
            result_sha256=None,
            result_bytes=None,
            result_json=None,
        )
    return replace(job, state=target_state, version=job.version + 1)


def complete_async_job_success(
    job: AsyncJobRecord,
    *,
    serialized_result: bytes,
) -> AsyncJobRecord:
    """Admit one non-empty serialized result and terminalize a RUNNING job."""
    if type(job) is not AsyncJobRecord or job.state is not AsyncJobState.RUNNING:
        raise PublicAnalysisValidationError("only RUNNING jobs may complete successfully")
    if type(serialized_result) is not bytes or not serialized_result:
        raise PublicAnalysisValidationError("serialized_result must be non-empty bytes")
    try:
        result_json = serialized_result.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PublicAnalysisValidationError("serialized_result must be UTF-8 JSON bytes") from exc
    return AsyncJobRecord(
        identity=job.identity,
        state=AsyncJobState.SUCCEEDED,
        attempt_count=job.attempt_count,
        version=job.version + 1,
        result_sha256=sha256(serialized_result).hexdigest(),
        result_bytes=len(serialized_result),
        result_json=result_json,
    )


def complete_async_job_failure(
    job: AsyncJobRecord,
    *,
    failure_code: str,
) -> AsyncJobRecord:
    """Terminalize an admitted non-terminal job with one bounded failure category."""
    if type(job) is not AsyncJobRecord:
        raise PublicAnalysisValidationError("job must be AsyncJobRecord")
    if job.state not in {
        AsyncJobState.SUBMITTING,
        AsyncJobState.ACCEPTED,
        AsyncJobState.RUNNING,
    }:
        raise PublicAnalysisValidationError("only non-terminal admitted jobs may fail")
    if type(failure_code) is not str or _FAILURE_CODE_PATTERN.fullmatch(failure_code) is None:
        raise PublicAnalysisValidationError("failure_code violates the frozen code contract")
    return AsyncJobRecord(
        identity=job.identity,
        state=AsyncJobState.FAILED,
        attempt_count=job.attempt_count,
        version=job.version + 1,
        failure_code=failure_code,
    )


__all__ = [
    "ASYNC_JOB_CONTRACT_VERSION",
    "AsyncJobIdentity",
    "AsyncJobRecord",
    "AsyncJobState",
    "complete_async_job_failure",
    "complete_async_job_success",
    "create_async_job_identity",
    "create_submitting_job",
    "transition_async_job",
    "validate_idempotency_key",
]
