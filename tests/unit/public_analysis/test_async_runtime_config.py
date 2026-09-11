"""Unit tests for fail-closed Gate 19.4 async runtime configuration."""

from __future__ import annotations

import pytest

from opslens.public_analysis.async_runtime_config import (
    AsyncApiRuntimeSettings,
    AsyncRuntimeConfigurationError,
    AsyncWorkerRuntimeSettings,
)


def test_api_submit_switch_defaults_false() -> None:
    """Require explicit opt-in before new jobs can cross the SQS dual-write boundary."""
    settings = AsyncApiRuntimeSettings.from_environment(
        {
            "OPSLENS_ASYNC_JOB_TABLE_NAME": "opslens-dev-public-analysis-jobs",
            "OPSLENS_ASYNC_JOB_QUEUE_URL": "https://sqs.example/jobs",
        }
    )

    assert settings.submit_enabled is False
    assert settings.submission_lease_seconds == 30


def test_worker_switch_defaults_false() -> None:
    """Require explicit opt-in before provider-heavy worker execution is admitted."""
    settings = AsyncWorkerRuntimeSettings.from_environment(
        {
            "OPSLENS_ASYNC_JOB_TABLE_NAME": "opslens-dev-public-analysis-jobs",
            "OPSLENS_ASYNC_JOB_QUEUE_ARN": "arn:aws:sqs:us-east-1:123:jobs",
            "AWS_REGION": "us-east-1",
        }
    )

    assert settings.worker_enabled is False
    assert settings.worker_lease_seconds == 90
    assert settings.max_attempts == 3


def test_switches_accept_only_exact_lowercase_boolean_vocabulary() -> None:
    """Reject permissive truthiness that could accidentally enable runtime work."""
    with pytest.raises(AsyncRuntimeConfigurationError):
        AsyncApiRuntimeSettings.from_environment(
            {
                "OPSLENS_ASYNC_JOB_TABLE_NAME": "jobs",
                "OPSLENS_ASYNC_JOB_QUEUE_URL": "https://sqs.example/jobs",
                "OPSLENS_ASYNC_SUBMIT_ENABLED": "TRUE",
            }
        )


def test_worker_limits_are_bounded_configured_limits() -> None:
    """Reject unbounded retry/lease configuration before any provider client is composed."""
    with pytest.raises(AsyncRuntimeConfigurationError):
        AsyncWorkerRuntimeSettings.from_environment(
            {
                "OPSLENS_ASYNC_JOB_TABLE_NAME": "jobs",
                "OPSLENS_ASYNC_JOB_QUEUE_ARN": "arn:aws:sqs:us-east-1:123:jobs",
                "AWS_REGION": "us-east-1",
                "OPSLENS_ASYNC_MAX_ATTEMPTS": "11",
            }
        )


def test_missing_runtime_coordinates_fail_closed() -> None:
    """Do not infer queue/table coordinates from ambient AWS state."""
    with pytest.raises(AsyncRuntimeConfigurationError):
        AsyncApiRuntimeSettings.from_environment({})
