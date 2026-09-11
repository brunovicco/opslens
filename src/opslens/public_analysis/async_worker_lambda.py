"""Role-specific worker Lambda composition for the bounded async public runtime."""

from __future__ import annotations

from collections.abc import Mapping

from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.public_analysis.adapters.async_sqs_event import (
    admit_async_sqs_deliveries,
    handle_async_sqs_event,
)
from opslens.public_analysis.application.async_job_service import AsyncJobStore
from opslens.public_analysis.application.async_worker_service import AsyncAnalysisExecutor
from opslens.public_analysis.async_runtime_config import (
    AsyncRuntimeConfigurationError,
    AsyncWorkerRuntimeSettings,
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
    """Retain admitted messages while provider-heavy worker composition is disabled."""
    del context
    settings = AsyncWorkerRuntimeSettings.from_environment()
    if settings.worker_enabled:
        raise AsyncRuntimeConfigurationError(
            "async worker execution is enabled but provider executor composition is not admitted"
        )

    # Gate 19.4/19.5 fail-closed invariants:
    # disabled worker must not access DynamoDB
    # disabled worker must not execute provider-heavy analysis
    deliveries = admit_async_sqs_deliveries(
        event,
        expected_queue_arn=settings.queue_arn,
        expected_region=settings.region,
    )
    return {
        "batchItemFailures": [
            {"itemIdentifier": delivery.message_id} for delivery in deliveries
        ]
    }


__all__ = ["execute_worker_lambda", "worker_lambda_handler"]
