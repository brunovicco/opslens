"""Role-specific API Lambda composition for the bounded async public runtime."""

from __future__ import annotations

from collections.abc import Mapping
from time import time
from typing import Literal, Protocol, cast

from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.session import Session

from opslens.public_analysis.adapters.async_aws import (
    DynamoDbAsyncJobStore,
    SqsAsyncJobPublisher,
)
from opslens.public_analysis.adapters.async_http_api import handle_async_http_event
from opslens.public_analysis.application.async_job_service import (
    AsyncJobPublisher,
    AsyncJobStore,
)
from opslens.public_analysis.async_runtime_config import (
    AsyncApiRuntimeSettings,
    AsyncRuntimeConfigurationError,
)


class _DynamoDbClient(Protocol):
    """Structural subset of the DynamoDB client required by the API control path."""

    def get_item(self, **kwargs: object) -> dict[str, object]:
        """Get one item."""
        ...

    def transact_write_items(self, **kwargs: object) -> dict[str, object]:
        """Create job and idempotency alias atomically."""
        ...

    def update_item(self, **kwargs: object) -> dict[str, object]:
        """Conditionally update one job."""
        ...


class _SqsClient(Protocol):
    """Structural subset of the SQS client required by the API control path."""

    def send_message(self, **kwargs: object) -> dict[str, object]:
        """Publish one queue message."""
        ...


class _DynamoDbClientFactory(Protocol):
    """Minimal boto3 factory contract required by the API composition root."""

    def client(self, service_name: Literal["dynamodb"]) -> _DynamoDbClient:
        """Create the DynamoDB client used by the async job store."""
        ...


class _SqsClientFactory(Protocol):
    """Minimal boto3 factory contract required by the API composition root."""

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
    publisher: AsyncJobPublisher,
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
    """Compose only the API control path; provider-heavy analysis is excluded."""
    del context
    settings = AsyncApiRuntimeSettings.from_environment()
    return execute_api_lambda(
        event,
        settings=settings,
        store=_build_job_store(settings.table_name),
        publisher=_build_job_publisher(settings.queue_url),
        now_epoch_seconds=_epoch_seconds(),
    )


__all__ = ["api_lambda_handler", "execute_api_lambda"]
