"""Compatibility facade for role-specific async Lambda composition roots.

Terraform keeps the Gate 19.4 handler coordinates stable while each function imports
only its own role-specific composition module at invocation time. This lets Gate 19.5
build independently reviewable API and worker deployment artifacts without granting
code presence the meaning of runtime authorization.
"""

from __future__ import annotations

from collections.abc import Mapping

from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.public_analysis.application.async_job_service import (
    AsyncJobPublisher,
    AsyncJobStore,
)
from opslens.public_analysis.application.async_worker_service import AsyncAnalysisExecutor
from opslens.public_analysis.async_runtime_config import (
    AsyncApiRuntimeSettings,
    AsyncWorkerRuntimeSettings,
)


def execute_api_lambda(
    event: Mapping[str, object],
    *,
    settings: AsyncApiRuntimeSettings,
    store: AsyncJobStore,
    publisher: AsyncJobPublisher,
    now_epoch_seconds: int,
) -> dict[str, object]:
    """Delegate one already-composed API invocation to the API-only composition root."""
    from opslens.public_analysis.async_api_lambda import execute_api_lambda as execute

    return execute(
        event,
        settings=settings,
        store=store,
        publisher=publisher,
        now_epoch_seconds=now_epoch_seconds,
    )


def api_lambda_handler(
    event: Mapping[str, object],
    context: LambdaContext,
) -> dict[str, object]:
    """Load only the API role composition for the API Lambda handler."""
    from opslens.public_analysis.async_api_lambda import api_lambda_handler as handler

    return handler(event, context)


def execute_worker_lambda(
    event: Mapping[str, object],
    *,
    settings: AsyncWorkerRuntimeSettings,
    store: AsyncJobStore,
    executor: AsyncAnalysisExecutor,
    now_epoch_seconds: int,
) -> dict[str, object]:
    """Delegate one already-composed worker invocation to the worker-only root."""
    from opslens.public_analysis.async_worker_lambda import execute_worker_lambda as execute

    return execute(
        event,
        settings=settings,
        store=store,
        executor=executor,
        now_epoch_seconds=now_epoch_seconds,
    )


def worker_lambda_handler(
    event: Mapping[str, object],
    context: LambdaContext,
) -> dict[str, object]:
    """Load only the disabled worker role composition for the worker handler."""
    # Historical Gate 19.4 fail-closed markers remain explicit:
    # disabled worker must not access DynamoDB
    # disabled worker must not execute provider-heavy analysis
    from opslens.public_analysis.async_worker_lambda import worker_lambda_handler as handler

    return handler(event, context)


__all__ = [
    "api_lambda_handler",
    "execute_api_lambda",
    "execute_worker_lambda",
    "worker_lambda_handler",
]
