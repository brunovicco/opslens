"""Narrow DynamoDB and SQS adapters for the disabled Gate 19.4 async runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol, cast

from botocore.exceptions import BotoCoreError, ClientError

from opslens.public_analysis.application.async_job_service import (
    AsyncJobPutOutcome,
    AsyncQueuePublishError,
)
from opslens.public_analysis.domain.async_job import (
    AsyncJobIdentity,
    AsyncJobRecord,
    AsyncJobState,
)
from opslens.public_analysis.domain.errors import PublicAnalysisValidationError

 type _AttributeValue = dict[str, str]
 type _DynamoItem = dict[str, _AttributeValue]


class AsyncJobPersistenceError(RuntimeError):
    """Raised when the DynamoDB persistence boundary cannot preserve job authority."""


class _DynamoDbClient(Protocol):
    """Exact DynamoDB client operations required by the async job adapter."""

    def get_item(self, **kwargs: object) -> dict[str, object]:
        """Get one item."""
        ...

    def transact_write_items(self, **kwargs: object) -> dict[str, object]:
        """Create the job and idempotency alias atomically."""
        ...

    def update_item(self, **kwargs: object) -> dict[str, object]:
        """Conditionally replace mutable job state."""
        ...


class _SqsClient(Protocol):
    """Exact SQS client operation required by the job publisher."""

    def send_message(self, **kwargs: object) -> dict[str, object]:
        """Publish one queue message."""
        ...


def _s(value: str) -> _AttributeValue:
    """Encode one DynamoDB string attribute."""
    return {"S": value}


def _n(value: int) -> _AttributeValue:
    """Encode one DynamoDB integer attribute."""
    return {"N": str(value)}


def _required_string(item: _DynamoItem, name: str) -> str:
    """Decode one exact DynamoDB string attribute."""
    value = item.get(name)
    if not isinstance(value, dict) or set(value) != {"S"}:
        raise AsyncJobPersistenceError(f"DynamoDB item is missing string attribute {name!r}")
    decoded = value.get("S")
    if type(decoded) is not str or not decoded:
        raise AsyncJobPersistenceError(f"DynamoDB string attribute {name!r} is invalid")
    return decoded


def _required_int(item: _DynamoItem, name: str) -> int:
    """Decode one exact non-negative DynamoDB integer attribute."""
    value = item.get(name)
    if not isinstance(value, dict) or set(value) != {"N"}:
        raise AsyncJobPersistenceError(f"DynamoDB item is missing number attribute {name!r}")
    raw = value.get("N")
    if type(raw) is not str or not raw.isdecimal():
        raise AsyncJobPersistenceError(f"DynamoDB number attribute {name!r} is invalid")
    return int(raw)


def _optional_string(item: _DynamoItem, name: str) -> str | None:
    """Decode one optional DynamoDB string attribute."""
    value = item.get(name)
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"S"}:
        raise AsyncJobPersistenceError(f"DynamoDB optional string attribute {name!r} is invalid")
    decoded = value.get("S")
    if type(decoded) is not str or not decoded:
        raise AsyncJobPersistenceError(f"DynamoDB optional string attribute {name!r} is empty")
    return decoded


def _optional_int(item: _DynamoItem, name: str) -> int | None:
    """Decode one optional DynamoDB integer attribute."""
    value = item.get(name)
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"N"}:
        raise AsyncJobPersistenceError(f"DynamoDB optional number attribute {name!r} is invalid")
    raw = value.get("N")
    if type(raw) is not str or not raw.isdecimal():
        raise AsyncJobPersistenceError(f"DynamoDB optional number attribute {name!r} is invalid")
    return int(raw)


def _job_key(job_id: str) -> _DynamoItem:
    """Return one exact job record primary key."""
    return {"pk": _s(f"JOB#{job_id}")}


def _idempotency_key(digest: str) -> _DynamoItem:
    """Return one exact immutable idempotency alias primary key."""
    return {"pk": _s(f"IDEMPOTENCY#{digest}")}


def _serialize_job(job: AsyncJobRecord) -> _DynamoItem:
    """Serialize one admitted job to the exact mutable DynamoDB job record."""
    item: _DynamoItem = {
        "pk": _s(f"JOB#{job.identity.job_id}"),
        "entity_type": _s("JOB"),
        "job_id": _s(job.identity.job_id),
        "idempotency_key_sha256": _s(job.identity.idempotency_key_sha256),
        "request_id": _s(job.identity.request_id),
        "request_sha256": _s(job.identity.request_sha256),
        "state": _s(job.state.value),
        "attempt_count": _n(job.attempt_count),
        "version": _n(job.version),
    }
    if job.result_sha256 is not None:
        item["result_sha256"] = _s(job.result_sha256)
    if job.result_bytes is not None:
        item["result_bytes"] = _n(job.result_bytes)
    if job.result_json is not None:
        item["result_json"] = _s(job.result_json)
    if job.failure_code is not None:
        item["failure_code"] = _s(job.failure_code)
    return item


def _serialize_idempotency_alias(job: AsyncJobRecord) -> _DynamoItem:
    """Serialize the immutable key-to-job binding used to detect semantic conflicts."""
    return {
        "pk": _s(f"IDEMPOTENCY#{job.identity.idempotency_key_sha256}"),
        "entity_type": _s("IDEMPOTENCY"),
        "idempotency_key_sha256": _s(job.identity.idempotency_key_sha256),
        "job_id": _s(job.identity.job_id),
        "request_sha256": _s(job.identity.request_sha256),
    }


def _deserialize_job(item: _DynamoItem) -> AsyncJobRecord:
    """Deserialize one exact DynamoDB job record back into domain authority."""
    if _required_string(item, "entity_type") != "JOB":
        raise AsyncJobPersistenceError("DynamoDB item is not a JOB entity")
    try:
        state = AsyncJobState(_required_string(item, "state"))
        identity = AsyncJobIdentity(
            job_id=_required_string(item, "job_id"),
            idempotency_key_sha256=_required_string(item, "idempotency_key_sha256"),
            request_id=_required_string(item, "request_id"),
            request_sha256=_required_string(item, "request_sha256"),
        )
        return AsyncJobRecord(
            identity=identity,
            state=state,
            attempt_count=_required_int(item, "attempt_count"),
            version=_required_int(item, "version"),
            result_sha256=_optional_string(item, "result_sha256"),
            result_bytes=_optional_int(item, "result_bytes"),
            result_json=_optional_string(item, "result_json"),
            failure_code=_optional_string(item, "failure_code"),
        )
    except (ValueError, PublicAnalysisValidationError) as exc:
        raise AsyncJobPersistenceError("DynamoDB job record violates domain authority") from exc


def _response_item(response: dict[str, object]) -> _DynamoItem | None:
    """Validate the untyped AWS response Item boundary."""
    raw_item = response.get("Item")
    if raw_item is None:
        return None
    if not isinstance(raw_item, dict):
        raise AsyncJobPersistenceError("DynamoDB GetItem returned a non-object Item")
    item = cast(dict[object, object], raw_item)
    normalized: _DynamoItem = {}
    for key, value in item.items():
        if type(key) is not str or not isinstance(value, dict):
            raise AsyncJobPersistenceError("DynamoDB Item contains an invalid attribute")
        attribute = cast(dict[object, object], value)
        if len(attribute) != 1:
            raise AsyncJobPersistenceError("DynamoDB attribute must contain one scalar type")
        attribute_key, attribute_value = next(iter(attribute.items()))
        if type(attribute_key) is not str or type(attribute_value) is not str:
            raise AsyncJobPersistenceError("DynamoDB attribute must be a string scalar")
        normalized[key] = {attribute_key: attribute_value}
    return normalized


def _client_error_code(exc: ClientError) -> str | None:
    """Extract one AWS error code without allowing untyped response data downstream."""
    response = cast(dict[str, object], exc.response)
    error = response.get("Error")
    if not isinstance(error, dict):
        return None
    error_object = cast(dict[object, object], error)
    code = error_object.get("Code")
    return code if type(code) is str else None


@dataclass(frozen=True, slots=True)
class DynamoDbAsyncJobStore:
    """Conditional DynamoDB implementation of the provider-neutral async job store."""

    client: _DynamoDbClient
    table_name: str

    def __post_init__(self) -> None:
        """Reject empty persistence coordinates."""
        if not self.table_name:
            raise ValueError("table_name must not be empty")

    def get_by_idempotency_key_sha256(self, digest: str) -> AsyncJobRecord | None:
        """Resolve the immutable alias and then read the authoritative job record."""
        response = self.client.get_item(
            TableName=self.table_name,
            Key=_idempotency_key(digest),
            ConsistentRead=True,
        )
        alias = _response_item(response)
        if alias is None:
            return None
        if _required_string(alias, "entity_type") != "IDEMPOTENCY":
            raise AsyncJobPersistenceError("idempotency key resolved to the wrong entity type")
        if _required_string(alias, "idempotency_key_sha256") != digest:
            raise AsyncJobPersistenceError("idempotency alias digest does not match lookup key")
        return self.get(_required_string(alias, "job_id"))

    def put_if_absent(self, job: AsyncJobRecord) -> AsyncJobPutOutcome:
        """Atomically bind key and job, or return the previously admitted binding."""
        if type(job) is not AsyncJobRecord or job.state is not AsyncJobState.SUBMITTING:
            raise PublicAnalysisValidationError("only a SUBMITTING AsyncJobRecord may be created")
        transaction = [
            {
                "Put": {
                    "TableName": self.table_name,
                    "Item": _serialize_job(job),
                    "ConditionExpression": "attribute_not_exists(pk)",
                }
            },
            {
                "Put": {
                    "TableName": self.table_name,
                    "Item": _serialize_idempotency_alias(job),
                    "ConditionExpression": "attribute_not_exists(pk)",
                }
            },
        ]
        try:
            self.client.transact_write_items(TransactItems=transaction)
        except ClientError as exc:
            if _client_error_code(exc) != "TransactionCanceledException":
                raise AsyncJobPersistenceError("DynamoDB job creation failed") from exc
            existing = self.get_by_idempotency_key_sha256(
                job.identity.idempotency_key_sha256
            )
            if existing is None:
                raise AsyncJobPersistenceError(
                    "DynamoDB transaction was cancelled without an admitted idempotency binding"
                ) from exc
            return AsyncJobPutOutcome(created=False, job=existing)
        except BotoCoreError as exc:
            raise AsyncJobPersistenceError("DynamoDB job creation failed") from exc
        return AsyncJobPutOutcome(created=True, job=job)

    def get(self, job_id: str) -> AsyncJobRecord | None:
        """Read one authoritative job record by deterministic job id."""
        response = self.client.get_item(
            TableName=self.table_name,
            Key=_job_key(job_id),
            ConsistentRead=True,
        )
        item = _response_item(response)
        return None if item is None else _deserialize_job(item)

    def replace_if_current(
        self,
        *,
        current: AsyncJobRecord,
        replacement: AsyncJobRecord,
    ) -> bool:
        """Conditionally update mutable state using the exact optimistic version authority."""
        if current.identity != replacement.identity:
            raise PublicAnalysisValidationError("async job identity is immutable")
        if replacement.version != current.version + 1:
            raise PublicAnalysisValidationError("replacement must advance version by exactly one")

        names = {"#state": "state", "#version": "version"}
        values: dict[str, _AttributeValue] = {
            ":state": _s(replacement.state.value),
            ":attempt_count": _n(replacement.attempt_count),
            ":next_version": _n(replacement.version),
            ":expected_version": _n(current.version),
        }
        set_parts = [
            "#state = :state",
            "attempt_count = :attempt_count",
            "#version = :next_version",
        ]
        remove_parts: list[str] = []
        optional_strings = {
            "result_sha256": replacement.result_sha256,
            "result_json": replacement.result_json,
            "failure_code": replacement.failure_code,
        }
        for attribute_name, value in optional_strings.items():
            if value is None:
                remove_parts.append(attribute_name)
            else:
                token = f":{attribute_name}"
                values[token] = _s(value)
                set_parts.append(f"{attribute_name} = {token}")
        if replacement.result_bytes is None:
            remove_parts.append("result_bytes")
        else:
            values[":result_bytes"] = _n(replacement.result_bytes)
            set_parts.append("result_bytes = :result_bytes")

        update_expression = "SET " + ", ".join(set_parts)
        if remove_parts:
            update_expression += " REMOVE " + ", ".join(remove_parts)
        try:
            self.client.update_item(
                TableName=self.table_name,
                Key=_job_key(current.identity.job_id),
                UpdateExpression=update_expression,
                ConditionExpression="#version = :expected_version",
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
            )
        except ClientError as exc:
            if _client_error_code(exc) == "ConditionalCheckFailedException":
                return False
            raise AsyncJobPersistenceError("DynamoDB conditional job update failed") from exc
        except BotoCoreError as exc:
            raise AsyncJobPersistenceError("DynamoDB conditional job update failed") from exc
        return True


@dataclass(frozen=True, slots=True)
class SqsAsyncJobPublisher:
    """Publish only deterministic job identity to one preconfigured standard SQS queue."""

    client: _SqsClient
    queue_url: str

    def __post_init__(self) -> None:
        """Reject empty queue coordinates."""
        if not self.queue_url:
            raise ValueError("queue_url must not be empty")

    def publish(self, job_id: str) -> None:
        """Publish one content-minimized job message and normalize transport failures."""
        if type(job_id) is not str or not job_id:
            raise PublicAnalysisValidationError("job_id must be a non-empty string")
        body = json.dumps(
            {"job_id": job_id},
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        try:
            self.client.send_message(QueueUrl=self.queue_url, MessageBody=body)
        except (BotoCoreError, ClientError) as exc:
            raise AsyncQueuePublishError("SQS job publication failed") from exc


__all__ = [
    "AsyncJobPersistenceError",
    "DynamoDbAsyncJobStore",
    "SqsAsyncJobPublisher",
]
