"""Offline adapter tests for the Gate 19.4 DynamoDB and SQS boundaries."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import cast

from botocore.exceptions import ClientError

from opslens.public_analysis.adapters.async_aws import (
    DynamoDbAsyncJobStore,
    SqsAsyncJobPublisher,
)
from opslens.public_analysis.domain.async_job import (
    AsyncJobRecord,
    AsyncJobState,
    claim_async_job_attempt,
    create_async_job_identity,
    create_submitting_job,
    transition_async_job,
)
from opslens.public_analysis.domain.request import (
    PublicRepositoryTarget,
    create_public_analysis_request,
)

_NOW = 2_000_000_000


def _job() -> AsyncJobRecord:
    """Build one deterministic leased SUBMITTING job."""
    request = create_public_analysis_request(
        PublicRepositoryTarget(
            owner="openedx",
            name="mockprock",
            requested_ref="18c954d8604df4740c829ba17fa2f3640b92b900",
        )
    )
    identity = create_async_job_identity(request, idempotency_key="client-key-0001")
    return create_submitting_job(
        identity,
        lease_expires_at_epoch_seconds=_NOW + 30,
    )


def _new_response_list() -> list[dict[str, object]]:
    """Return one typed fake-response queue."""
    return []


def _new_call_list() -> list[dict[str, object]]:
    """Return one typed fake-call list."""
    return []


@dataclass(slots=True)
class _FakeDynamoDbClient:
    """Record exact adapter calls without any AWS execution."""

    get_responses: list[dict[str, object]] = field(default_factory=_new_response_list)
    get_calls: list[dict[str, object]] = field(default_factory=_new_call_list)
    transact_calls: list[dict[str, object]] = field(default_factory=_new_call_list)
    update_calls: list[dict[str, object]] = field(default_factory=_new_call_list)
    update_error: ClientError | None = None

    def get_item(self, **kwargs: object) -> dict[str, object]:
        """Return one preloaded response."""
        self.get_calls.append(dict(kwargs))
        if not self.get_responses:
            return {}
        return self.get_responses.pop(0)

    def transact_write_items(self, **kwargs: object) -> dict[str, object]:
        """Record one atomic-create request."""
        self.transact_calls.append(dict(kwargs))
        return {}

    def update_item(self, **kwargs: object) -> dict[str, object]:
        """Record one conditional-update request."""
        self.update_calls.append(dict(kwargs))
        if self.update_error is not None:
            raise self.update_error
        return {}


@dataclass(slots=True)
class _FakeSqsClient:
    """Record exact queue publication without any AWS execution."""

    calls: list[dict[str, object]] = field(default_factory=_new_call_list)

    def send_message(self, **kwargs: object) -> dict[str, object]:
        """Record one outbound queue request."""
        self.calls.append(dict(kwargs))
        return {"MessageId": "test-message"}


def _job_item(job: AsyncJobRecord) -> dict[str, object]:
    """Build one exact raw DynamoDB response item for adapter decoding."""
    item: dict[str, object] = {
        "pk": {"S": f"JOB#{job.identity.job_id}"},
        "entity_type": {"S": "JOB"},
        "job_id": {"S": job.identity.job_id},
        "idempotency_key_sha256": {"S": job.identity.idempotency_key_sha256},
        "request_id": {"S": job.identity.request_id},
        "request_sha256": {"S": job.identity.request_sha256},
        "repository_owner": {"S": job.identity.repository_owner},
        "repository_name": {"S": job.identity.repository_name},
        "state": {"S": job.state.value},
        "attempt_count": {"N": str(job.attempt_count)},
        "version": {"N": str(job.version)},
    }
    if job.identity.requested_ref is not None:
        item["requested_ref"] = {"S": job.identity.requested_ref}
    if job.lease_expires_at_epoch_seconds is not None:
        item["lease_expires_at_epoch_seconds"] = {
            "N": str(job.lease_expires_at_epoch_seconds)
        }
    return item


def test_put_if_absent_uses_two_conditional_items_without_query_or_scan() -> None:
    """Bind job/idempotency aliases atomically using only the allowed DDB write authority."""
    client = _FakeDynamoDbClient()
    store = DynamoDbAsyncJobStore(client=client, table_name="opslens-dev-public-jobs")
    job = _job()

    outcome = store.put_if_absent(job)

    assert outcome.created is True
    assert outcome.job == job
    assert len(client.transact_calls) == 1
    transaction = client.transact_calls[0]
    raw_transact_items = transaction["TransactItems"]
    assert isinstance(raw_transact_items, list)
    transact_items = cast(list[object], raw_transact_items)
    assert len(transact_items) == 2
    rendered = json.dumps(transact_items, sort_keys=True)
    assert f"JOB#{job.identity.job_id}" in rendered
    assert f"IDEMPOTENCY#{job.identity.idempotency_key_sha256}" in rendered
    assert job.identity.repository_owner in rendered
    assert job.identity.repository_name in rendered
    assert rendered.count("attribute_not_exists(pk)") == 2


def test_get_decodes_exact_job_record_and_reconstructs_request() -> None:
    """Reject storage as authority until it reconstructs the strict domain request and job."""
    job = transition_async_job(_job(), target_state=AsyncJobState.ACCEPTED)
    client = _FakeDynamoDbClient(get_responses=[{"Item": _job_item(job)}])
    store = DynamoDbAsyncJobStore(client=client, table_name="opslens-dev-public-jobs")

    observed = store.get(job.identity.job_id)

    assert observed == job
    assert observed is not None
    assert observed.identity.request.target.owner == "openedx"
    assert observed.identity.request.target.name == "mockprock"
    assert client.get_calls == [
        {
            "TableName": "opslens-dev-public-jobs",
            "Key": {"pk": {"S": f"JOB#{job.identity.job_id}"}},
            "ConsistentRead": True,
        }
    ]


def test_replace_if_current_binds_conditional_update_to_exact_state_and_version() -> None:
    """Make DynamoDB state/version compare-and-swap authority explicit."""
    current = _job()
    replacement = transition_async_job(current, target_state=AsyncJobState.ACCEPTED)
    client = _FakeDynamoDbClient()
    store = DynamoDbAsyncJobStore(client=client, table_name="opslens-dev-public-jobs")

    assert store.replace_if_current(current=current, replacement=replacement) is True

    assert len(client.update_calls) == 1
    call = client.update_calls[0]
    assert call["ConditionExpression"] == (
        "#version = :expected_version AND #state = :expected_state"
    )
    raw_values = call["ExpressionAttributeValues"]
    assert isinstance(raw_values, dict)
    values = cast(dict[str, object], raw_values)
    assert values[":expected_version"] == {"N": "0"}
    assert values[":expected_state"] == {"S": "SUBMITTING"}
    assert values[":next_version"] == {"N": "1"}


def test_replace_if_current_persists_worker_lease_and_attempt() -> None:
    """Persist the explicit worker lease that blocks overlapping duplicate execution."""
    current = transition_async_job(_job(), target_state=AsyncJobState.ACCEPTED)
    replacement = claim_async_job_attempt(
        current,
        now_epoch_seconds=_NOW,
        lease_seconds=60,
    )
    client = _FakeDynamoDbClient()
    store = DynamoDbAsyncJobStore(client=client, table_name="opslens-dev-public-jobs")

    assert store.replace_if_current(current=current, replacement=replacement) is True

    call = client.update_calls[0]
    rendered = json.dumps(call, sort_keys=True)
    assert '"attempt_count": {"N": "1"}' not in rendered
    assert ':lease_expires_at_epoch_seconds' in rendered
    assert str(_NOW + 60) in rendered


def test_replace_if_current_returns_false_on_conditional_race() -> None:
    """Expose a lost optimistic claim as a deterministic false result, not an implicit retry."""
    current = transition_async_job(_job(), target_state=AsyncJobState.ACCEPTED)
    replacement = claim_async_job_attempt(
        current,
        now_epoch_seconds=_NOW,
        lease_seconds=60,
    )
    error = ClientError(
        {
            "Error": {
                "Code": "ConditionalCheckFailedException",
                "Message": "simulated conditional race",
            }
        },
        "UpdateItem",
    )
    client = _FakeDynamoDbClient(update_error=error)
    store = DynamoDbAsyncJobStore(client=client, table_name="opslens-dev-public-jobs")

    assert store.replace_if_current(current=current, replacement=replacement) is False


def test_sqs_publisher_emits_only_deterministic_job_identity() -> None:
    """Keep repository/request/result contents out of the at-least-once queue message."""
    client = _FakeSqsClient()
    publisher = SqsAsyncJobPublisher(
        client=client,
        queue_url="https://sqs.us-east-1.amazonaws.com/123/opslens-dev-public-jobs",
    )
    job = _job()

    publisher.publish(job.identity.job_id)

    assert client.calls == [
        {
            "QueueUrl": "https://sqs.us-east-1.amazonaws.com/123/opslens-dev-public-jobs",
            "MessageBody": json.dumps(
                {"job_id": job.identity.job_id},
                separators=(",", ":"),
                sort_keys=True,
            ),
        }
    ]
