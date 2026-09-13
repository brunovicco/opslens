"""Offline SQS worker tests for the Gate 19.4 asynchronous execution boundary."""

import json
from dataclasses import dataclass, field

import pytest

from opslens.public_analysis.adapters.async_sqs_event import (
    AsyncSqsAdmissionError,
    handle_async_sqs_event,
)
from opslens.public_analysis.application.async_job_service import (
    AsyncJobPutOutcome,
    submit_async_analysis,
)
from opslens.public_analysis.domain.async_job import (
    AsyncJobRecord,
    AsyncJobState,
    claim_async_job_attempt,
)
from opslens.public_analysis.domain.request import (
    PublicAnalysisRequest,
    PublicRepositoryTarget,
    create_public_analysis_request,
)

_NOW = 2_000_000_000
_QUEUE_ARN = "arn:aws:sqs:us-east-1:123456789012:opslens-dev-public-analysis-jobs"


def _new_job_map() -> dict[str, AsyncJobRecord]:
    """Return one typed job map."""
    return {}


def _new_key_map() -> dict[str, str]:
    """Return one typed idempotency map."""
    return {}


def _new_request_list() -> list[PublicAnalysisRequest]:
    """Return one typed execution record."""
    return []


@dataclass(slots=True)
class _MemoryStore:
    """Conditional in-memory job store for worker tests."""

    by_job_id: dict[str, AsyncJobRecord] = field(default_factory=_new_job_map)
    by_key_hash: dict[str, str] = field(default_factory=_new_key_map)

    def get_by_idempotency_key_sha256(self, digest: str) -> AsyncJobRecord | None:
        """Resolve one hashed idempotency key."""
        job_id = self.by_key_hash.get(digest)
        return None if job_id is None else self.by_job_id[job_id]

    def put_if_absent(self, job: AsyncJobRecord) -> AsyncJobPutOutcome:
        """Create one job or return the existing binding."""
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
        """Replace one exact current record."""
        if self.by_job_id.get(current.identity.job_id) != current:
            return False
        self.by_job_id[current.identity.job_id] = replacement
        return True


@dataclass(slots=True)
class _Publisher:
    """No-network queue publisher used only to establish ACCEPTED state."""

    def publish(self, job_id: str) -> None:
        """Accept one logical publication without side effects."""
        assert job_id


@dataclass(slots=True)
class _Executor:
    """Record normalized requests and optionally fail provider-heavy execution."""

    fail: bool = False
    requests: list[PublicAnalysisRequest] = field(default_factory=_new_request_list)

    def execute(self, request: PublicAnalysisRequest) -> bytes:
        """Return one deterministic result or raise a simulated execution failure."""
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("simulated provider-heavy failure")
        return b'{"risk":"bounded"}'


def _request() -> PublicAnalysisRequest:
    """Build the frozen representative repository request."""
    return create_public_analysis_request(
        PublicRepositoryTarget(
            owner="openedx",
            name="mockprock",
            requested_ref="18c954d8604df4740c829ba17fa2f3640b92b900",
        )
    )


def _accepted_job(store: _MemoryStore) -> AsyncJobRecord:
    """Create one ACCEPTED job through the real provider-neutral submit service."""
    result = submit_async_analysis(
        _request(),
        idempotency_key="client-key-0001",
        store=store,
        publisher=_Publisher(),
        now_epoch_seconds=_NOW,
        submission_lease_seconds=30,
    )
    return result.job


def _record(job_id: str, *, message_id: str = "message-1") -> dict[str, object]:
    """Build one exact SQS Lambda event record."""
    return {
        "messageId": message_id,
        "body": json.dumps({"job_id": job_id}, separators=(",", ":"), sort_keys=True),
        "attributes": {
            "ApproximateReceiveCount": "1",
            "SentTimestamp": "2000000000000",
        },
        "eventSource": "aws:sqs",
        "eventSourceARN": _QUEUE_ARN,
        "awsRegion": "us-east-1",
    }


def _event(*records: dict[str, object]) -> dict[str, object]:
    """Build one SQS Lambda batch event."""
    return {"Records": list(records)}


def _handle(
    event: dict[str, object],
    *,
    store: _MemoryStore,
    executor: _Executor,
    max_attempts: int = 3,
    worker_enabled: bool = True,
) -> dict[str, object]:
    """Invoke the SQS adapter with deterministic worker configuration."""
    return handle_async_sqs_event(
        event,
        expected_queue_arn=_QUEUE_ARN,
        expected_region="us-east-1",
        store=store,
        executor=executor,
        now_epoch_seconds=_NOW,
        worker_lease_seconds=60,
        max_attempts=max_attempts,
        worker_enabled=worker_enabled,
    )


def test_worker_success_reconstructs_request_and_admits_terminal_result() -> None:
    """Execute only after claim and persist the deterministic result before acknowledging."""
    store = _MemoryStore()
    job = _accepted_job(store)
    executor = _Executor()

    response = _handle(_event(_record(job.identity.job_id)), store=store, executor=executor)
    final = store.get(job.identity.job_id)

    assert response == {"batchItemFailures": []}
    assert executor.requests == [_request()]
    assert final is not None
    assert final.state is AsyncJobState.SUCCEEDED
    assert final.result_json == '{"risk":"bounded"}'


def test_worker_disabled_retains_message_without_execution() -> None:
    """Make the runtime worker guard fail closed without deleting queued work."""
    store = _MemoryStore()
    job = _accepted_job(store)
    executor = _Executor()

    response = _handle(
        _event(_record(job.identity.job_id)),
        store=store,
        executor=executor,
        worker_enabled=False,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert executor.requests == []
    assert store.get(job.identity.job_id) == job


def test_active_worker_lease_retains_duplicate_message_without_second_execution() -> None:
    """Do not delete a redelivery that arrives while the authoritative attempt is in flight."""
    store = _MemoryStore()
    accepted = _accepted_job(store)
    running = claim_async_job_attempt(
        accepted,
        now_epoch_seconds=_NOW,
        lease_seconds=60,
    )
    store.by_job_id[accepted.identity.job_id] = running
    executor = _Executor()

    response = _handle(
        _event(_record(accepted.identity.job_id)),
        store=store,
        executor=executor,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert executor.requests == []
    assert store.get(accepted.identity.job_id) == running


def test_retryable_execution_failure_retains_message_below_attempt_ceiling() -> None:
    """Let SQS redelivery own retry scheduling while preserving the RUNNING lease."""
    store = _MemoryStore()
    job = _accepted_job(store)
    executor = _Executor(fail=True)

    response = _handle(
        _event(_record(job.identity.job_id)),
        store=store,
        executor=executor,
        max_attempts=3,
    )
    current = store.get(job.identity.job_id)

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert current is not None
    assert current.state is AsyncJobState.RUNNING
    assert current.attempt_count == 1


def test_attempt_ceiling_terminalizes_failure_and_acknowledges_message() -> None:
    """Bound automatic provider retry instead of relying on unlimited redelivery."""
    store = _MemoryStore()
    job = _accepted_job(store)
    executor = _Executor(fail=True)

    response = _handle(
        _event(_record(job.identity.job_id)),
        store=store,
        executor=executor,
        max_attempts=1,
    )
    final = store.get(job.identity.job_id)

    assert response == {"batchItemFailures": []}
    assert final is not None
    assert final.state is AsyncJobState.FAILED
    assert final.failure_code == "EXECUTION_ATTEMPT_LIMIT"


def test_terminal_duplicate_delivery_is_acknowledged_without_execution() -> None:
    """Treat queue redelivery as transport evidence, not authority to rerun completed work."""
    store = _MemoryStore()
    job = _accepted_job(store)
    executor = _Executor()
    first = _handle(_event(_record(job.identity.job_id)), store=store, executor=executor)
    assert first == {"batchItemFailures": []}
    executor.requests.clear()

    duplicate = _handle(
        _event(_record(job.identity.job_id, message_id="message-2")),
        store=store,
        executor=executor,
    )

    assert duplicate == {"batchItemFailures": []}
    assert executor.requests == []


def test_wrong_queue_arn_fails_closed_before_job_lookup_or_execution() -> None:
    """Bind worker transport authority to the exact configured SQS queue ARN."""
    store = _MemoryStore()
    job = _accepted_job(store)
    executor = _Executor()
    record = _record(job.identity.job_id)
    record["eventSourceARN"] = "arn:aws:sqs:us-east-1:123456789012:unexpected"

    with pytest.raises(AsyncSqsAdmissionError):
        _handle(_event(record), store=store, executor=executor)

    assert executor.requests == []
