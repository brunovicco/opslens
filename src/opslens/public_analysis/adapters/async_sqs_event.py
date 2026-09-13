"""Strict SQS event admission and partial-batch projection for the async worker."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from opslens.public_analysis.application.async_job_service import AsyncJobStore
from opslens.public_analysis.application.async_worker_service import (
    AsyncAnalysisExecutor,
    AsyncWorkerExecutionDisposition,
    execute_async_worker_delivery,
)
from opslens.public_analysis.domain.async_job import validate_async_job_id
from opslens.public_analysis.domain.errors import PublicAnalysisValidationError

MAX_SQS_JOB_BODY_BYTES = 512
MAX_SQS_BATCH_RECORDS = 10


class AsyncSqsAdmissionError(ValueError):
    """Raised when an untrusted SQS Lambda event violates the frozen worker contract."""


@dataclass(frozen=True, slots=True)
class AsyncSqsJobDelivery:
    """Content-minimized admitted projection of one SQS record."""

    message_id: str
    job_id: str
    receive_count: int
    sent_timestamp_ms: int


def _mapping(value: object, *, field: str) -> dict[str, object]:
    """Project one untyped event object into a string-keyed mapping."""
    if not isinstance(value, dict):
        raise AsyncSqsAdmissionError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise AsyncSqsAdmissionError(f"{field} keys must be strings")
    return cast(dict[str, object], raw)


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate keys in the minimized SQS message body."""
    projected: dict[str, object] = {}
    for key, value in pairs:
        if key in projected:
            raise AsyncSqsAdmissionError("SQS message body cannot contain duplicate keys")
        projected[key] = value
    return projected


def _positive_decimal(value: object, *, field: str) -> int:
    """Decode one positive decimal string from SQS record attributes."""
    if type(value) is not str or not value.isdecimal():
        raise AsyncSqsAdmissionError(f"{field} must be a decimal string")
    decoded = int(value)
    if decoded <= 0:
        raise AsyncSqsAdmissionError(f"{field} must be positive")
    return decoded


def _decode_job_id(body: object) -> str:
    """Decode the exact content-minimized SQS body."""
    if type(body) is not str or not body:
        raise AsyncSqsAdmissionError("SQS body must be a non-empty string")
    try:
        body_bytes = body.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise AsyncSqsAdmissionError("SQS body must encode as UTF-8") from exc
    if len(body_bytes) > MAX_SQS_JOB_BODY_BYTES:
        raise AsyncSqsAdmissionError("SQS body exceeds the worker message byte bound")
    try:
        decoded: object = json.loads(body, object_pairs_hook=_unique_json_object)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise AsyncSqsAdmissionError("SQS body must contain valid JSON") from exc
    mapping = _mapping(decoded, field="SQS body")
    if set(mapping) != {"job_id"}:
        raise AsyncSqsAdmissionError("SQS body must contain exactly job_id")
    raw_job_id = mapping["job_id"]
    if type(raw_job_id) is not str:
        raise AsyncSqsAdmissionError("SQS job_id must be a string")
    try:
        return validate_async_job_id(raw_job_id)
    except PublicAnalysisValidationError as exc:
        raise AsyncSqsAdmissionError("SQS job_id violates the async identity contract") from exc


def admit_async_sqs_deliveries(
    event: Mapping[str, object],
    *,
    expected_queue_arn: str,
    expected_region: str,
) -> tuple[AsyncSqsJobDelivery, ...]:
    """Admit one bounded SQS batch from exactly the configured queue and region."""
    if not expected_queue_arn or not expected_region:
        raise ValueError("expected queue ARN and region must be non-empty")
    raw_records = event.get("Records")
    if not isinstance(raw_records, list):
        raise AsyncSqsAdmissionError("Records must be an array")
    records = cast(list[object], raw_records)
    if not records or len(records) > MAX_SQS_BATCH_RECORDS:
        raise AsyncSqsAdmissionError("SQS batch size is outside the admitted bound")

    deliveries: list[AsyncSqsJobDelivery] = []
    seen_message_ids: set[str] = set()
    for index, candidate in enumerate(records):
        record = _mapping(candidate, field=f"Records[{index}]")
        if record.get("eventSource") != "aws:sqs":
            raise AsyncSqsAdmissionError("record eventSource must be aws:sqs")
        if record.get("eventSourceARN") != expected_queue_arn:
            raise AsyncSqsAdmissionError("record eventSourceARN does not match configured queue")
        if record.get("awsRegion") != expected_region:
            raise AsyncSqsAdmissionError("record awsRegion does not match configured region")
        message_id = record.get("messageId")
        if type(message_id) is not str or not message_id or len(message_id) > 128:
            raise AsyncSqsAdmissionError("messageId must be a bounded non-empty string")
        if message_id in seen_message_ids:
            raise AsyncSqsAdmissionError("SQS batch contains a duplicate messageId")
        seen_message_ids.add(message_id)

        attributes = _mapping(record.get("attributes"), field="record.attributes")
        receive_count = _positive_decimal(
            attributes.get("ApproximateReceiveCount"),
            field="ApproximateReceiveCount",
        )
        sent_timestamp_ms = _positive_decimal(
            attributes.get("SentTimestamp"),
            field="SentTimestamp",
        )
        deliveries.append(
            AsyncSqsJobDelivery(
                message_id=message_id,
                job_id=_decode_job_id(record.get("body")),
                receive_count=receive_count,
                sent_timestamp_ms=sent_timestamp_ms,
            )
        )
    return tuple(deliveries)


def _partial_batch_response(failed_message_ids: list[str]) -> dict[str, object]:
    """Render the Lambda SQS partial-batch failure contract deterministically."""
    return {
        "batchItemFailures": [
            {"itemIdentifier": message_id} for message_id in failed_message_ids
        ]
    }


def handle_async_sqs_event(
    event: Mapping[str, object],
    *,
    expected_queue_arn: str,
    expected_region: str,
    store: AsyncJobStore,
    executor: AsyncAnalysisExecutor,
    now_epoch_seconds: int,
    worker_lease_seconds: int,
    max_attempts: int,
    worker_enabled: bool,
) -> dict[str, object]:
    """Process a bounded SQS batch while preserving retry authority with partial failures."""
    deliveries = admit_async_sqs_deliveries(
        event,
        expected_queue_arn=expected_queue_arn,
        expected_region=expected_region,
    )
    if not worker_enabled:
        return _partial_batch_response([delivery.message_id for delivery in deliveries])

    failed_message_ids: list[str] = []
    for delivery in deliveries:
        try:
            result = execute_async_worker_delivery(
                job_id=delivery.job_id,
                store=store,
                executor=executor,
                now_epoch_seconds=now_epoch_seconds,
                worker_lease_seconds=worker_lease_seconds,
                max_attempts=max_attempts,
            )
        except Exception:
            failed_message_ids.append(delivery.message_id)
            continue
        if result.disposition in {
            AsyncWorkerExecutionDisposition.RETAIN_ACTIVE_LEASE,
            AsyncWorkerExecutionDisposition.RETAIN_CONCURRENT_CLAIM,
        }:
            failed_message_ids.append(delivery.message_id)
    return _partial_batch_response(failed_message_ids)


__all__ = [
    "MAX_SQS_BATCH_RECORDS",
    "MAX_SQS_JOB_BODY_BYTES",
    "AsyncSqsAdmissionError",
    "AsyncSqsJobDelivery",
    "admit_async_sqs_deliveries",
    "handle_async_sqs_event",
]
