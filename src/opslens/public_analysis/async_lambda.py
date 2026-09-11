"""Thin AWS Lambda composition wrappers for the disabled Gate 19.4 async topology."""

from __future__ import annotations

from collections.abc import Mapping
from time import time
from typing import Literal, Protocol, cast

from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.session import Session

from opslens.public_analysis.adapters.async_aws import (
    DynamoDbAsyncJobStore,
    SqsAsyncJobPublisher,
    _DynamoDbClient,
    _SqsClient,
)
from opslens.public_analysis.adapters.async_http_api import handle_async_http_event
from opslens.public_analysis.adapters.async_sqs_event import handle_async_sqs_event
from opslens.public_analysis.application.async_job_service import AsyncJobStore
from opslens.public_analysis.application.async_worker_service import AsyncAnalysisExecutor
from opslens.public_analysis.async_runtime_config import (
    AsyncApiRuntimeSettings,
    AsyncRuntimeConfigurationError,
    AsyncWorkerRuntimeSettings,
)


class _DynamoDbClientFactory(Protocol):
    """Minimal boto3 factory contract required by the async composition root."""

    def client(self, service_name: Literal["dynamodb"]) -> _DynamoDbClient:
        """Create the DynamoDB client used by the async job store."""
        ...


class _SqsClientFactory(Protocol):
    """Minimal boto3 factory contract required by the async composition root."""

    def client(self, service_name: Literal["sqs"]) -> _SqsClient:
        """Create the SQS client used by the async job publisher."""
        ...


def _epoch_seconds() -> int:
    """Return one positive wall-clock reading at the Lambda composition boundary."""
    value = int(time())
    if value <= 0:
        raise AsyncRuntimeConfigurationError("runtime clock did not return positive epoch seconds")
    return value


def _build_job_store(table_name: str) -> DynamoDbAsyncJobStore:
    """Build the DynamoDB store lazily at invocation time."""
    factory = cast(_DynamoDbClientFactory, Session())
    return DynamoDbAsyncJobStore(
        client=factory.client("dynamodb"),
        table_name=table_name,
    )


def _build_job_publisher(queue_url: str) -> SqsAsyncJobPublisher:
    """Build the SQS publisher lazily at invocation time."""
    factory = cast(_SqsClientFactory, Session())
    return SqsAsyncJobPublisher(
        client=factory.client("sqs"),
        queue_url=queue_url,
    )


def execute_api_lambda(
    event: Mapping[str, object],
    *,
    settings: AsyncApiRuntimeSettings,
    store: AsyncJobStore,
    publisher: SqsAsyncJobPublisher,
    now_epoch_seconds: int,
) -> dict[str, object]:
    """Execute one already-composed API Lambda invocation."""
    return handle_async_http_event(
        event,
        store=store,
        publisher=publisher,
        now_epoch_seconds=now_epoch_seconds,
        submission_lease_seconds=settings.submission_lease_seconds,
        submit_enabled=settings.submit_enabled,
    )


def api_lambda_handler(
    event: Mapping[str, object],
    context: LambdaContext,
) -> dict[str, object]:
    """Compose the API control path; no provider-heavy public analysis runs here."""
    del context
    settings = AsyncApiRuntimeSettings.from_environment()
    return execute_api_lambda(
        event,
        settings=settings,
        store=_build_job_store(settings.table_name),
        publisher=_build_job_publisher(settings.queue_url),
        now_epoch_seconds=_epoch_seconds(),
    )


def execute_worker_lambda(
    event: Mapping[str, object],
    *,
    settings: AsyncWorkerRuntimeSettings,
    store: AsyncJobStore,
    executor: AsyncAnalysisExecutor,
    now_epoch_seconds: int,
) -> dict[str, object]:
    """Execute one already-composed worker invocation with explicit execution authority."""
    return handle_async_sqs_event(
        event,
        expected_queue_arn=settings.queue_arn,
        expected_region=settings.region,
        store=store,
        executor=executor,
        now_epoch_seconds=now_epoch_seconds,
        worker_lease_seconds=settings.worker_lease_seconds,
        max_attempts=settings.max_attempts,
        worker_enabled=settings.worker_enabled,
    )


def worker_lambda_handler(
    event: Mapping[str, object],
    context: LambdaContext,
) -> dict[str, object]:
    """Fail closed until the retained provider-heavy executor is explicitly composed."""
    del context
    settings = AsyncWorkerRuntimeSettings.from_environment()
    if settings.worker_enabled:
        raise AsyncRuntimeConfigurationError(
            "async worker execution is enabled but provider executor composition is not admitted"
        )

    class _NeverStore:
        def get_by_idempotency_key_sha256(self, digest: str):
            del digest
            raise AssertionError("disabled worker must not access DynamoDB")

        def put_if_absent(self, job):
            del job
            raise AssertionError("disabled worker must not access DynamoDB")

        def get(self, job_id: str):
            del job_id
            raise AssertionError("disabled worker must not access DynamoDB")

        def replace_if_current(self, *, current, replacement):
            del current, replacement
            raise AssertionError("disabled worker must not access DynamoDB")

    class _NeverExecutor:
        def execute(self, request):
            del request
            raise AssertionError("disabled worker must not execute provider-heavy analysis")

    return execute_worker_lambda(
        event,
        settings=settings,
        store=cast(AsyncJobStore, _NeverStore()),
        executor=cast(AsyncAnalysisExecutor, _NeverExecutor()),
        now_epoch_seconds=_epoch_seconds(),
    )


__all__ = [
    "api_lambda_handler",
    "execute_api_lambda",
    "execute_worker_lambda",
    "worker_lambda_handler",
]
