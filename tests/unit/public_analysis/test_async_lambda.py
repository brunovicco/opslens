"""Unit tests for the thin fail-closed Gate 19.4 Lambda composition wrappers."""

from __future__ import annotations

from typing import cast

import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.public_analysis.async_lambda import worker_lambda_handler
from opslens.public_analysis.async_runtime_config import AsyncRuntimeConfigurationError

_QUEUE_ARN = "arn:aws:sqs:us-east-1:123456789012:opslens-dev-public-analysis-jobs"
_JOB_ID = "public-analysis-job:v1:" + ("a" * 64)


def _worker_event() -> dict[str, object]:
    """Build one exact minimal SQS event admitted by the disabled worker boundary."""
    return {
        "Records": [
            {
                "messageId": "message-1",
                "body": f'{{"job_id":"{_JOB_ID}"}}',
                "attributes": {
                    "ApproximateReceiveCount": "1",
                    "SentTimestamp": "2000000000000",
                },
                "eventSource": "aws:sqs",
                "eventSourceARN": _QUEUE_ARN,
                "awsRegion": "us-east-1",
            }
        ]
    }


def _set_worker_environment(
    monkeypatch: pytest.MonkeyPatch,
    *,
    enabled: str,
) -> None:
    """Install one explicit worker runtime environment for a test invocation."""
    monkeypatch.setenv("OPSLENS_ASYNC_JOB_TABLE_NAME", "opslens-dev-public-analysis-jobs")
    monkeypatch.setenv("OPSLENS_ASYNC_JOB_QUEUE_ARN", _QUEUE_ARN)
    monkeypatch.setenv("OPSLENS_ASYNC_WORKER_ENABLED", enabled)
    monkeypatch.setenv("AWS_REGION", "us-east-1")


def test_runtime_worker_disabled_retains_message_without_composing_aws_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the SQS record retryable while the provider-heavy worker is disabled."""
    _set_worker_environment(monkeypatch, enabled="false")

    response = worker_lambda_handler(
        _worker_event(),
        cast(LambdaContext, object()),
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}


def test_runtime_worker_enablement_fails_before_provider_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refuse accidental worker enablement until the retained executor is explicitly wired."""
    _set_worker_environment(monkeypatch, enabled="true")

    with pytest.raises(AsyncRuntimeConfigurationError):
        worker_lambda_handler({}, cast(LambdaContext, object()))
