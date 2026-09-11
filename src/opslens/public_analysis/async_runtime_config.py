"""Validated fail-closed runtime configuration for the Gate 19.4 async topology."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class AsyncRuntimeConfigurationError(ValueError):
    """Raised when async runtime configuration is missing, malformed, or unsafe."""


class AsyncRuntimeSwitch(StrEnum):
    """Exact boolean vocabulary accepted from environment variables."""

    FALSE = "false"
    TRUE = "true"


def _required_text(environment: Mapping[str, str], name: str) -> str:
    """Read one normalized required environment value."""
    value = environment.get(name)
    if value is None or not value or value != value.strip():
        raise AsyncRuntimeConfigurationError(f"{name} must be a normalized non-empty string")
    return value


def _disabled_by_default(environment: Mapping[str, str], name: str) -> bool:
    """Parse one exact lower-case runtime switch with a fail-closed false default."""
    raw = environment.get(name, AsyncRuntimeSwitch.FALSE.value)
    try:
        return AsyncRuntimeSwitch(raw) is AsyncRuntimeSwitch.TRUE
    except ValueError as exc:
        raise AsyncRuntimeConfigurationError(
            f"{name} must be exactly 'true' or 'false'"
        ) from exc


def _positive_int(
    environment: Mapping[str, str],
    name: str,
    *,
    default: int,
    maximum: int,
) -> int:
    """Parse one bounded positive configured limit without relabeling it as utilization."""
    raw = environment.get(name, str(default))
    if not raw.isdecimal():
        raise AsyncRuntimeConfigurationError(f"{name} must be a positive decimal integer")
    value = int(raw)
    if value <= 0 or value > maximum:
        raise AsyncRuntimeConfigurationError(
            f"{name} must be between 1 and {maximum} inclusive"
        )
    return value


@dataclass(frozen=True, slots=True)
class AsyncApiRuntimeSettings:
    """Configuration required by the API Lambda control path."""

    table_name: str
    queue_url: str
    submit_enabled: bool
    submission_lease_seconds: int

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> AsyncApiRuntimeSettings:
        """Load API settings with new-job admission disabled unless explicitly enabled."""
        source = os.environ if environment is None else environment
        return cls(
            table_name=_required_text(source, "OPSLENS_ASYNC_JOB_TABLE_NAME"),
            queue_url=_required_text(source, "OPSLENS_ASYNC_JOB_QUEUE_URL"),
            submit_enabled=_disabled_by_default(source, "OPSLENS_ASYNC_SUBMIT_ENABLED"),
            submission_lease_seconds=_positive_int(
                source,
                "OPSLENS_ASYNC_SUBMISSION_LEASE_SECONDS",
                default=30,
                maximum=300,
            ),
        )


@dataclass(frozen=True, slots=True)
class AsyncWorkerRuntimeSettings:
    """Configuration required by the SQS-triggered worker Lambda."""

    table_name: str
    queue_arn: str
    region: str
    worker_enabled: bool
    worker_lease_seconds: int
    max_attempts: int

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> AsyncWorkerRuntimeSettings:
        """Load worker settings with provider-heavy execution disabled by default."""
        source = os.environ if environment is None else environment
        return cls(
            table_name=_required_text(source, "OPSLENS_ASYNC_JOB_TABLE_NAME"),
            queue_arn=_required_text(source, "OPSLENS_ASYNC_JOB_QUEUE_ARN"),
            region=_required_text(source, "AWS_REGION"),
            worker_enabled=_disabled_by_default(source, "OPSLENS_ASYNC_WORKER_ENABLED"),
            worker_lease_seconds=_positive_int(
                source,
                "OPSLENS_ASYNC_WORKER_LEASE_SECONDS",
                default=90,
                maximum=900,
            ),
            max_attempts=_positive_int(
                source,
                "OPSLENS_ASYNC_MAX_ATTEMPTS",
                default=3,
                maximum=10,
            ),
        )


__all__ = [
    "AsyncApiRuntimeSettings",
    "AsyncRuntimeConfigurationError",
    "AsyncRuntimeSwitch",
    "AsyncWorkerRuntimeSettings",
]
