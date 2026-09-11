"""Provider-neutral tests for Gate 19.4 async submit/status/result use cases."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from opslens.public_analysis.application.async_job_admission import (
    AsyncSubmissionDisposition,
)
from opslens.public_analysis.application.async_job_service import (
    AsyncClaimDisposition,
    AsyncJobPutOutcome,
    AsyncQueuePublishError,
    AsyncResultNotReadyError,
    AsyncSubmissionUnavailableError,
    claim_async_worker_attempt,
    get_async_job_result,
    submit_async_analysis,
)
from opslens.public_analysis.domain.async_job import (
    AsyncJobRecord,
    AsyncJobState,
    complete_async_job_success,
)
from opslens.public_analysis.domain.request import (
    PublicAnalysisRequest,
    PublicRepositoryTarget,
    create_public_analysis_request,
)


def _request() -> PublicAnalysisRequest:
    """Build one admitted public-analysis request."""
    return create_public_analysis_request(
        PublicRepositoryTarget(
            owner="openedx",
            name="mockprock",
            requested_ref="18c954d8604df4740c829ba17fa2f3640b92b900",
        )
    )


def _new_job_map() -> dict[str, AsyncJobRecord]:
    """Return one explicitly typed in-memory job map."""
    return {}


def _new_key_map() -> dict[str, str]:
    """Return one explicitly typed hashed-key lookup map."""
    return {}


def _new_job_id_list() -> list[str]:
    """Return one explicitly typed publication record."""
    return []


@dataclass(slots=True)
class _MemoryStore:
    """Deterministic in-memory implementation of the conditional job-store port."""

    by_job_id: dict[str, AsyncJobRecord] = field(default_factory=_new_job_map)
    by_key_hash: dict[str, str] = field(default_factory=_new_key_map)

    def get_by_idempotency_key_sha256(self, digest: str) -> AsyncJobRecord | None:
        """Return a job by hashed idempotency key."""
        job_id = self.by_key_hash.get(digest)
        return None if job_id is None else self.by_job_id[job_id]

    def put_if_absent(self, job: AsyncJobRecord) -> AsyncJobPutOutcome:
        """Create one job or return the already-bound record."""
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
        """Replace only when the exact expected state is still current."""
        observed = self.by_job_id.get(current.identity.job_id)
        if observed != current:
            return False
        self.by_job_id[current.identity.job_id] = replacement
        return True


@dataclass(slots=True)
class _MemoryPublisher:
    """Deterministic queue publisher test double."""

    fail: bool = False
    published_job_ids: list[str] = field(default_factory=_new_job_id_list)

    def publish(self, job_id: str) -> None:
        """Record publication or fail before recording it."""
        if self.fail:
            raise AsyncQueuePublishError("simulated queue failure")
        self.published_job_ids.append(job_id)


class _LostClaimStore(_MemoryStore):
    """Store that simulates another worker winning exactly one claim race."""

    lose_next_replace: bool = True

    def replace_if_current(
        self,
        *,
        current: AsyncJobRecord,
        replacement: AsyncJobRecord,
    ) -> bool:
        """Install the competing replacement while reporting this caller lost the CAS."""
        if self.lose_next_replace and replacement.state is AsyncJobState.RUNNING:
            self.lose_next_replace = False
            self.by_job_id[current.identity.job_id] = replacement
            return False
        return super().replace_if_current(current=current, replacement=replacement)


def test_submit_persists_then_publishes_then_accepts() -> None:
    """Model the explicit DynamoDB/SQS dual-write boundary deterministically."""
    store = _MemoryStore()
    publisher = _MemoryPublisher()

    result = submit_async_analysis(
        _request(),
        idempotency_key="client-key-0001",
        store=store,
        publisher=publisher,
    )

    assert result.disposition is AsyncSubmissionDisposition.CREATE_NEW_JOB
    assert result.job.state is AsyncJobState.ACCEPTED
    assert publisher.published_job_ids == [result.job.identity.job_id]
    assert store.get(result.job.identity.job_id) == result.job


def test_submit_replay_does_not_publish_again() -> None:
    """Return the existing job without amplifying queue or provider work."""
    store = _MemoryStore()
    publisher = _MemoryPublisher()
    request = _request()
    first = submit_async_analysis(
        request,
        idempotency_key="client-key-0001",
        store=store,
        publisher=publisher,
    )

    replay = submit_async_analysis(
        request,
        idempotency_key="client-key-0001",
        store=store,
        publisher=publisher,
    )

    assert replay.disposition is AsyncSubmissionDisposition.RETURN_EXISTING_JOB
    assert replay.job == first.job
    assert publisher.published_job_ids == [first.job.identity.job_id]


def test_queue_failure_terminalizes_submitting_job() -> None:
    """Record queue publication failure rather than treating the dual write as atomic."""
    store = _MemoryStore()
    publisher = _MemoryPublisher(fail=True)

    with pytest.raises(AsyncSubmissionUnavailableError):
        submit_async_analysis(
            _request(),
            idempotency_key="client-key-0001",
            store=store,
            publisher=publisher,
        )

    assert len(store.by_job_id) == 1
    failed = next(iter(store.by_job_id.values()))
    assert failed.state is AsyncJobState.FAILED
    assert failed.failure_code == "QUEUE_PUBLISH_FAILED"


def test_worker_claim_uses_conditional_state_authority() -> None:
    """Increment one attempt only after the conditional store claim succeeds."""
    store = _MemoryStore()
    submitted = submit_async_analysis(
        _request(),
        idempotency_key="client-key-0001",
        store=store,
        publisher=_MemoryPublisher(),
    )

    claim = claim_async_worker_attempt(job_id=submitted.job.identity.job_id, store=store)

    assert claim.disposition is AsyncClaimDisposition.CLAIMED
    assert claim.job.state is AsyncJobState.RUNNING
    assert claim.job.attempt_count == 1


def test_worker_does_not_retry_a_lost_claim_inside_same_delivery() -> None:
    """Fail closed on a conditional-claim race instead of creating concurrent execution."""
    store = _LostClaimStore()
    submitted = submit_async_analysis(
        _request(),
        idempotency_key="client-key-0001",
        store=store,
        publisher=_MemoryPublisher(),
    )

    claim = claim_async_worker_attempt(job_id=submitted.job.identity.job_id, store=store)

    assert claim.disposition is AsyncClaimDisposition.NOOP_CONCURRENT_CLAIM
    assert claim.job.state is AsyncJobState.RUNNING
    assert claim.job.attempt_count == 1


def test_result_read_requires_successful_admission() -> None:
    """Keep status/protocol success separate from admitted result availability."""
    store = _MemoryStore()
    submitted = submit_async_analysis(
        _request(),
        idempotency_key="client-key-0001",
        store=store,
        publisher=_MemoryPublisher(),
    )

    with pytest.raises(AsyncResultNotReadyError):
        get_async_job_result(job_id=submitted.job.identity.job_id, store=store)

    claim = claim_async_worker_attempt(job_id=submitted.job.identity.job_id, store=store)
    succeeded = complete_async_job_success(
        claim.job,
        serialized_result=b'{"status":"ok"}',
    )
    assert store.replace_if_current(current=claim.job, replacement=succeeded)

    assert get_async_job_result(job_id=submitted.job.identity.job_id, store=store) == (
        '{"status":"ok"}'
    )
