"""Deterministic authority for the Phase 19 asynchronous public-analysis job lifecycle."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import StrEnum
from hashlib import sha256

from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.public_analysis.domain.request import (
    PublicAnalysisRequest,
    PublicRepositoryTarget,
    create_public_analysis_request,
)

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


def _positive_epoch_seconds(value: int, *, field: str) -> int:
    """Require one positive non-boolean epoch-seconds value."""
    if type(value) is not int or value <= 0:
        raise PublicAnalysisValidationError(f"{field} must be a positive integer")
    return value


def _lease_deadline(*, now_epoch_seconds: int, lease_seconds: int) -> int:
    """Derive one explicit bounded lease deadline without consulting a hidden clock."""
    now = _positive_epoch_seconds(now_epoch_seconds, field="now_epoch_seconds")
    lease = _positive_epoch_seconds(lease_seconds, field="lease_seconds")
    return now + lease


@dataclass(frozen=True, slots=True)
class AsyncJobIdentity:
    """Content-addressed async job identity plus reconstructable admitted request semantics."""

    job_id: str
    idempotency_key_sha256: str
    request_id: str
    request_sha256: str
    repository_owner: str
    repository_name: str
    requested_ref: str | None

    def __post_init__(self) -> None:
        """Reject forged identity values or request coordinates that do not match the digest."""
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

        reconstructed = create_public_analysis_request(
            PublicRepositoryTarget(
                owner=self.repository_owner,
                name=self.repository_name,
                requested_ref=self.requested_ref,
            )
        )
        if reconstructed.request_id != self.request_id:
            raise PublicAnalysisValidationError(
                "request_id must match the persisted normalized request semantics"
            )
        if reconstructed.request_sha256 != self.request_sha256:
            raise PublicAnalysisValidationError(
                "request_sha256 must match the persisted normalized request semantics"
            )

        expected_job_digest = sha256(
            f"{self.idempotency_key_sha256}:{self.request_sha256}".encode("ascii")
        ).hexdigest()
        expected_job_id = f"{ASYNC_JOB_CONTRACT_VERSION}:{expected_job_digest}"
        if self.job_id != expected_job_id:
            raise PublicAnalysisValidationError(
                "job_id must match the idempotency-key/request content identity"
            )

    @property
    def request(self) -> PublicAnalysisRequest:
        """Reconstruct the exact admitted request required by a later worker attempt."""
        return create_public_analysis_request(
            PublicRepositoryTarget(
                owner=self.repository_owner,
                name=self.repository_name,
                requested_ref=self.requested_ref,
            )
        )


@dataclass(frozen=True, slots=True)
class AsyncJobRecord:
    """Deterministic job state, optimistic version, lease, and terminal evidence."""

    identity: AsyncJobIdentity
    state: AsyncJobState
    attempt_count: int = 0
    version: int = 0
    lease_expires_at_epoch_seconds: int | None = None
    result_sha256: str | None = None
    result_bytes: int | None = None
    result_json: str | None = None
    failure_code: str | None = None

    def __post_init__(self) -> None:
        """Enforce state-specific result, failure, version, attempt, and lease invariants."""
        if type(self.identity) is not AsyncJobIdentity:
            raise PublicAnalysisValidationError("identity must be AsyncJobIdentity")
        if type(self.state) is not AsyncJobState:
            raise PublicAnalysisValidationError("state must be AsyncJobState")
        if type(self.attempt_count) is not int or self.attempt_count < 0:
            raise PublicAnalysisValidationError("attempt_count must be a non-negative integer")
        if type(self.version) is not int or self.version < 0:
            raise PublicAnalysisValidationError("version must be a non-negative integer")

        lease = self.lease_expires_at_epoch_seconds
        if self.state in {AsyncJobState.SUBMITTING, AsyncJobState.RUNNING}:
            if type(lease) is not int or lease <= 0:
                raise PublicAnalysisValidationError(
                    "SUBMITTING and RUNNING jobs require one positive lease deadline"
                )
        elif lease is not None:
            raise PublicAnalysisValidationError(
                "only SUBMITTING and RUNNING jobs may carry a lease deadline"
            )

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


def validate_async_job_id(value: str) -> str:
    """Validate one public asynchronous job identifier."""
    if type(value) is not str or _JOB_ID_PATTERN.fullmatch(value) is None:
        raise PublicAnalysisValidationError("job_id violates the async job identity contract")
    return value


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
        repository_owner=request.target.owner,
        repository_name=request.target.name,
        requested_ref=request.target.requested_ref,
    )


def create_submitting_job(
    identity: AsyncJobIdentity,
    *,
    lease_expires_at_epoch_seconds: int,
) -> AsyncJobRecord:
    """Create the only valid initial state with an explicit bounded submission lease."""
    if type(identity) is not AsyncJobIdentity:
        raise PublicAnalysisValidationError("identity must be AsyncJobIdentity")
    deadline = _positive_epoch_seconds(
        lease_expires_at_epoch_seconds,
        field="lease_expires_at_epoch_seconds",
    )
    return AsyncJobRecord(
        identity=identity,
        state=AsyncJobState.SUBMITTING,
        lease_expires_at_epoch_seconds=deadline,
    )


def refresh_submitting_lease(
    job: AsyncJobRecord,
    *,
    now_epoch_seconds: int,
    lease_seconds: int,
) -> AsyncJobRecord:
    """Renew only an expired SUBMITTING lease for safe idempotent queue resubmission."""
    if type(job) is not AsyncJobRecord or job.state is not AsyncJobState.SUBMITTING:
        raise PublicAnalysisValidationError("only SUBMITTING jobs may refresh submission lease")
    now = _positive_epoch_seconds(now_epoch_seconds, field="now_epoch_seconds")
    if job.lease_expires_at_epoch_seconds is None:
        raise PublicAnalysisValidationError("SUBMITTING job is missing lease authority")
    if job.lease_expires_at_epoch_seconds > now:
        raise PublicAnalysisValidationError("SUBMITTING lease is still active")
    return replace(
        job,
        version=job.version + 1,
        lease_expires_at_epoch_seconds=_lease_deadline(
            now_epoch_seconds=now,
            lease_seconds=lease_seconds,
        ),
    )


def accept_async_job(job: AsyncJobRecord) -> AsyncJobRecord:
    """Admit successful queue publication without pretending DynamoDB and SQS are atomic."""
    if type(job) is not AsyncJobRecord or job.state is not AsyncJobState.SUBMITTING:
        raise PublicAnalysisValidationError("only SUBMITTING jobs may become ACCEPTED")
    return replace(
        job,
        state=AsyncJobState.ACCEPTED,
        version=job.version + 1,
        lease_expires_at_epoch_seconds=None,
    )


def claim_async_job_attempt(
    job: AsyncJobRecord,
    *,
    now_epoch_seconds: int,
    lease_seconds: int,
) -> AsyncJobRecord:
    """Claim one worker attempt, blocking duplicate work while a RUNNING lease is active."""
    if type(job) is not AsyncJobRecord:
        raise PublicAnalysisValidationError("job must be AsyncJobRecord")
    if job.state not in {
        AsyncJobState.SUBMITTING,
        AsyncJobState.ACCEPTED,
        AsyncJobState.RUNNING,
    }:
        raise PublicAnalysisValidationError("only admitted non-terminal jobs may be claimed")
    now = _positive_epoch_seconds(now_epoch_seconds, field="now_epoch_seconds")
    if (
        job.state is AsyncJobState.RUNNING
        and job.lease_expires_at_epoch_seconds is not None
        and job.lease_expires_at_epoch_seconds > now
    ):
        raise PublicAnalysisValidationError("RUNNING worker lease is still active")
    return replace(
        job,
        state=AsyncJobState.RUNNING,
        attempt_count=job.attempt_count + 1,
        version=job.version + 1,
        lease_expires_at_epoch_seconds=_lease_deadline(
            now_epoch_seconds=now,
            lease_seconds=lease_seconds,
        ),
    )


def transition_async_job(
    job: AsyncJobRecord,
    *,
    target_state: AsyncJobState,
) -> AsyncJobRecord:
    """Apply lifecycle transitions that do not require submission/worker lease authority."""
    if type(job) is not AsyncJobRecord:
        raise PublicAnalysisValidationError("job must be AsyncJobRecord")
    if type(target_state) is not AsyncJobState:
        raise PublicAnalysisValidationError("target_state must be AsyncJobState")
    if target_state is AsyncJobState.ACCEPTED:
        return accept_async_job(job)
    if target_state is AsyncJobState.RUNNING:
        raise PublicAnalysisValidationError(
            "RUNNING requires claim_async_job_attempt with an explicit worker lease"
        )
    if target_state is AsyncJobState.SUCCEEDED:
        raise PublicAnalysisValidationError(
            "SUCCEEDED requires complete_async_job_success with admitted result evidence"
        )
    if target_state is AsyncJobState.FAILED:
        raise PublicAnalysisValidationError(
            "FAILED requires complete_async_job_failure with an explicit failure code"
        )
    if target_state is not AsyncJobState.EXPIRED or job.state is AsyncJobState.EXPIRED:
        raise PublicAnalysisValidationError(
            f"async job transition {job.state.value}->{target_state.value} is not allowed"
        )
    return replace(
        job,
        state=AsyncJobState.EXPIRED,
        version=job.version + 1,
        lease_expires_at_epoch_seconds=None,
        result_sha256=None,
        result_bytes=None,
        result_json=None,
    )


def complete_async_job_success(
    job: AsyncJobRecord,
    *,
    serialized_result: bytes,
) -> AsyncJobRecord:
    """Admit one non-empty serialized result and terminalize a claimed RUNNING job."""
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
    "accept_async_job",
    "claim_async_job_attempt",
    "complete_async_job_failure",
    "complete_async_job_success",
    "create_async_job_identity",
    "create_submitting_job",
    "refresh_submitting_lease",
    "transition_async_job",
    "validate_async_job_id",
    "validate_idempotency_key",
]
