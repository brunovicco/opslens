"""Tests for GHSA Bronze Lambda invocation and response contracts."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest

from opslens.ingestion.ghsa.adapters.inbound.invocation import (
    GhsaBronzeInvocationParserV1,
    InvalidGhsaInvocationError,
)
from opslens.ingestion.ghsa.application.runtime import GhsaBronzeAttemptCompletion
from opslens.ingestion.ghsa.lambda_handler import execute_bronze_request
from opslens.ingestion.ghsa.runtime_config import GhsaBronzeRuntimeSettingsV1


class _Telemetry:
    """Minimal deterministic telemetry double."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore structured info."""
        del message, fields

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore structured exceptions."""
        del message, fields

    def metric(self, name: str, value: float, unit: str) -> None:
        """Ignore metrics."""
        del name, value, unit

    def span(self, name: str) -> AbstractContextManager[object]:
        """Return a no-op span."""
        del name
        return nullcontext(object())


class _Runtime:
    """Return controlled COMPLETE leaf results."""

    def __init__(
        self,
        completions: tuple[GhsaBronzeAttemptCompletion, ...],
    ) -> None:
        """Initialize the controlled runtime result."""
        self.completions = completions
        self.calls = 0

    def run(self, window: object) -> tuple[GhsaBronzeAttemptCompletion, ...]:
        """Return the configured leaf results."""
        del window
        self.calls += 1
        return self.completions


def _event() -> dict[str, object]:
    """Return one canonical manual v1 invocation."""
    return {
        "schema_version": 1,
        "mode": "published",
        "start_at": "2026-08-01T00:00:00Z",
        "end_at": "2026-08-02T00:00:00Z",
    }


def test_invocation_parser_accepts_exact_v1_shape() -> None:
    """Build one deterministic published sync window from canonical UTC input."""
    window = GhsaBronzeInvocationParserV1().parse(_event())

    assert window.mode.value == "published"
    assert window.canonical_start_at == "2026-08-01T00:00:00+00:00"
    assert window.canonical_end_at == "2026-08-02T00:00:00+00:00"
    assert len(window.sync_id) == 64


def test_invocation_parser_rejects_unknown_fields() -> None:
    """Fail closed instead of accepting undeclared scheduler or runtime knobs."""
    event = _event()
    event["retry"] = 3

    with pytest.raises(InvalidGhsaInvocationError, match="unsupported fields"):
        GhsaBronzeInvocationParserV1().parse(event)


def test_invocation_parser_rejects_noncanonical_timestamp() -> None:
    """Require explicit Zulu whole-second boundaries at the Lambda edge."""
    event = _event()
    event["start_at"] = "2026-08-01T00:00:00+00:00"

    with pytest.raises(InvalidGhsaInvocationError, match="YYYY-MM-DDTHH:MM:SSZ"):
        GhsaBronzeInvocationParserV1().parse(event)


def test_invocation_parser_rejects_unknown_schema_version() -> None:
    """Make future event contracts opt-in rather than silently compatible."""
    event = _event()
    event["schema_version"] = 2

    with pytest.raises(InvalidGhsaInvocationError, match="schema_version"):
        GhsaBronzeInvocationParserV1().parse(event)


def test_runtime_settings_load_only_secret_identifier_from_environment() -> None:
    """Keep GitHub credential material out of Lambda environment configuration."""
    settings = GhsaBronzeRuntimeSettingsV1.from_environment(
        {
            "GHSA_DATA_BUCKET": "opslens-dev-data-example",
            "GHSA_GITHUB_TOKEN_SECRET_ID": "opslens/dev/ghsa/github-token",
            "GHSA_BRONZE_PREFIX": "bronze/ghsa/advisories",
            "GHSA_HTTP_TIMEOUT_SECONDS": "20",
            "GHSA_HTTP_MAX_ATTEMPTS": "4",
            "GHSA_SECRET_CACHE_TTL_SECONDS": "240",
            "GHSA_MAX_LEAF_WINDOWS": "32",
        }
    )

    assert settings.bucket_name == "opslens-dev-data-example"
    assert settings.github_token_secret_id == "opslens/dev/ghsa/github-token"
    assert settings.http_timeout_seconds == 20.0
    assert settings.http_max_attempts == 4
    assert settings.secret_cache_ttl_seconds == 240.0
    assert settings.max_leaf_windows == 32


def test_execute_bronze_request_serializes_complete_leaf_evidence() -> None:
    """Return root and leaf evidence without exposing credentials or HTTP headers."""
    window = GhsaBronzeInvocationParserV1().parse(_event())
    runtime = _Runtime(
        (
            GhsaBronzeAttemptCompletion(
                sync_id="1" * 64,
                attempt_id="2" * 64,
                page_count=2,
                total_items=150,
                total_bytes=5000,
                manifest_key="bronze/ghsa/left/manifest.json",
                manifest_version_id="left-version",
            ),
            GhsaBronzeAttemptCompletion(
                sync_id="3" * 64,
                attempt_id="4" * 64,
                page_count=1,
                total_items=20,
                total_bytes=1000,
                manifest_key="bronze/ghsa/right/manifest.json",
                manifest_version_id="right-version",
            ),
        )
    )

    response = execute_bronze_request(
        window=window,
        runtime=runtime,
        telemetry=_Telemetry(),
        request_id="request-123",
    )

    assert runtime.calls == 1
    assert response["request_id"] == "request-123"
    assert response["status"] == "complete"
    assert response["schema_version"] == 1
    assert response["mode"] == "published"
    assert response["root_sync_id"] == window.sync_id
    assert response["leaf_count"] == 2
    assert response["total_items"] == 170
    assert response["total_bytes"] == 6000
    assert response["leaves"][0]["manifest_version_id"] == "left-version"
    assert response["leaves"][1]["manifest_version_id"] == "right-version"
    assert "token" not in response
    assert "authorization" not in response
