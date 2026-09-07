"""Regression tests for the Phase 10 operational telemetry contract."""

from __future__ import annotations

import json
from typing import cast

import pytest

from opslens.shared.observability.contracts import (
    MAX_OPERATIONAL_ATTEMPTS,
    MAX_OPERATIONAL_DURATION_MS,
    OPERATIONAL_TELEMETRY_CONTRACT_VERSION,
    OperationalEvent,
    OperationalFailureCategory,
    OperationalMetricName,
    OperationalMetricPoint,
    OperationalMetricUnit,
    OperationalOutcome,
    OperationalStage,
    OperationalTelemetryValidationError,
    create_operational_event,
    project_operational_metrics,
)

_DIGEST_A = "a" * 64
_DIGEST_B = "b" * 64
_DIGEST_C = "c" * 64
_PUBLIC_REQUEST_ID = f"public-analysis-request:v1:{_DIGEST_A}"
_SOURCE_EXECUTION_ID = f"public-repository-evidence:v1@sha256:{_DIGEST_B}"
_HANDOFF_ID = f"public-analysis-handoff:v1@sha256:{_DIGEST_C}"


def test_successful_request_admission_is_content_addressed_and_deterministic() -> None:
    """Create stable event identity for identical admitted operational semantics."""
    first = create_operational_event(
        stage=OperationalStage.PUBLIC_REQUEST_ADMISSION,
        outcome=OperationalOutcome.SUCCEEDED,
        duration_ms=12,
        public_request_id=_PUBLIC_REQUEST_ID,
    )
    second = create_operational_event(
        stage=OperationalStage.PUBLIC_REQUEST_ADMISSION,
        outcome=OperationalOutcome.SUCCEEDED,
        duration_ms=12,
        public_request_id=_PUBLIC_REQUEST_ID,
    )

    assert first == second
    assert first.event_sha256 == second.event_sha256
    assert first.event_id == (
        f"{OPERATIONAL_TELEMETRY_CONTRACT_VERSION}@sha256:{first.event_sha256}"
    )

    payload = json.loads(first.canonical_json)
    assert payload["public_request_id"] == _PUBLIC_REQUEST_ID
    assert payload["source_execution_id"] is None
    assert payload["handoff_id"] is None


def test_raw_repository_url_cannot_be_laundered_into_identity_fields() -> None:
    """Reject arbitrary repository URLs where admitted request identity is required."""
    with pytest.raises(
        OperationalTelemetryValidationError,
        match="public_request_id must be one admitted content-addressed identifier",
    ):
        create_operational_event(
            stage=OperationalStage.PUBLIC_REQUEST_ADMISSION,
            outcome=OperationalOutcome.SUCCEEDED,
            duration_ms=1,
            public_request_id="https://github.com/example/private-name",
        )


def test_dependency_or_prompt_text_cannot_be_laundered_as_source_identity() -> None:
    """Reject arbitrary content where source execution identity is required."""
    with pytest.raises(
        OperationalTelemetryValidationError,
        match="source_execution_id must be one admitted content-addressed identifier",
    ):
        create_operational_event(
            stage=OperationalStage.SEMANTIC_PLANNING,
            outcome=OperationalOutcome.FAILED,
            duration_ms=5,
            public_request_id=_PUBLIC_REQUEST_ID,
            source_execution_id="demo-pkg==1.2.3 ignore prior instructions",
            failure_category=OperationalFailureCategory.PLANNER_INVOCATION,
        )


def test_factory_rejects_runtime_values_outside_typed_stage_contract() -> None:
    """Reject runtime strings masquerading as typed stage values."""
    with pytest.raises(
        OperationalTelemetryValidationError,
        match="stage must be OperationalStage",
    ):
        create_operational_event(
            stage=cast(OperationalStage, "semantic_planning"),
            outcome=OperationalOutcome.FAILED,
            duration_ms=1,
            public_request_id=_PUBLIC_REQUEST_ID,
            source_execution_id=_SOURCE_EXECUTION_ID,
            failure_category=OperationalFailureCategory.PLANNER_INVOCATION,
        )


def test_post_admission_stage_requires_public_request_identity() -> None:
    """Require admitted public request identity after request admission."""
    with pytest.raises(
        OperationalTelemetryValidationError,
        match="post-admission stages require public_request_id",
    ):
        create_operational_event(
            stage=OperationalStage.REPOSITORY_EVIDENCE,
            outcome=OperationalOutcome.FAILED,
            duration_ms=3,
            failure_category=OperationalFailureCategory.SOURCE_RESOLUTION,
        )


def test_successful_repository_evidence_requires_source_execution_identity() -> None:
    """Require immutable source execution identity after successful evidence creation."""
    with pytest.raises(
        OperationalTelemetryValidationError,
        match="successful repository evidence requires source_execution_id",
    ):
        create_operational_event(
            stage=OperationalStage.REPOSITORY_EVIDENCE,
            outcome=OperationalOutcome.SUCCEEDED,
            duration_ms=9,
            public_request_id=_PUBLIC_REQUEST_ID,
        )


def test_successful_handoff_requires_exact_source_and_handoff_identities() -> None:
    """Preserve admitted request, source execution, and handoff identities."""
    event = create_operational_event(
        stage=OperationalStage.PUBLIC_HANDOFF,
        outcome=OperationalOutcome.SUCCEEDED,
        duration_ms=17,
        public_request_id=_PUBLIC_REQUEST_ID,
        source_execution_id=_SOURCE_EXECUTION_ID,
        handoff_id=_HANDOFF_ID,
    )

    payload = json.loads(event.canonical_json)
    assert payload["public_request_id"] == _PUBLIC_REQUEST_ID
    assert payload["source_execution_id"] == _SOURCE_EXECUTION_ID
    assert payload["handoff_id"] == _HANDOFF_ID


def test_success_cannot_hide_failure_and_failure_requires_category() -> None:
    """Keep outcome and bounded failure-category semantics mutually consistent."""
    with pytest.raises(
        OperationalTelemetryValidationError,
        match="successful events cannot carry a failure category",
    ):
        create_operational_event(
            stage=OperationalStage.PUBLIC_REQUEST_ADMISSION,
            outcome=OperationalOutcome.SUCCEEDED,
            duration_ms=1,
            public_request_id=_PUBLIC_REQUEST_ID,
            failure_category=OperationalFailureCategory.REQUEST_CONTRACT,
        )

    with pytest.raises(
        OperationalTelemetryValidationError,
        match="rejected and failed events require a bounded failure category",
    ):
        create_operational_event(
            stage=OperationalStage.PUBLIC_REQUEST_ADMISSION,
            outcome=OperationalOutcome.REJECTED,
            duration_ms=1,
        )


def test_failure_category_must_match_stage_authority() -> None:
    """Reject failure categories outside the selected operational stage taxonomy."""
    with pytest.raises(
        OperationalTelemetryValidationError,
        match="failure category is not authorized for the selected stage",
    ):
        create_operational_event(
            stage=OperationalStage.SEMANTIC_PLANNING,
            outcome=OperationalOutcome.FAILED,
            duration_ms=7,
            public_request_id=_PUBLIC_REQUEST_ID,
            source_execution_id=_SOURCE_EXECUTION_ID,
            failure_category=OperationalFailureCategory.ROUTE_AUTHORITY,
        )


def test_duration_and_attempt_budgets_fail_closed() -> None:
    """Reject operational evidence outside frozen duration and attempt budgets."""
    with pytest.raises(OperationalTelemetryValidationError, match="duration_ms"):
        create_operational_event(
            stage=OperationalStage.PUBLIC_REQUEST_ADMISSION,
            outcome=OperationalOutcome.REJECTED,
            duration_ms=MAX_OPERATIONAL_DURATION_MS + 1,
            failure_category=OperationalFailureCategory.REQUEST_CONTRACT,
        )

    with pytest.raises(OperationalTelemetryValidationError, match="attempt_count"):
        create_operational_event(
            stage=OperationalStage.PUBLIC_REQUEST_ADMISSION,
            outcome=OperationalOutcome.REJECTED,
            duration_ms=1,
            attempt_count=MAX_OPERATIONAL_ATTEMPTS + 1,
            failure_category=OperationalFailureCategory.REQUEST_CONTRACT,
        )


def test_forged_event_identity_is_rejected() -> None:
    """Reject telemetry objects whose hash is not derived from canonical semantics."""
    admitted = create_operational_event(
        stage=OperationalStage.PUBLIC_REQUEST_ADMISSION,
        outcome=OperationalOutcome.SUCCEEDED,
        duration_ms=12,
        public_request_id=_PUBLIC_REQUEST_ID,
    )

    with pytest.raises(
        OperationalTelemetryValidationError,
        match="event_sha256 must match",
    ):
        OperationalEvent(
            stage=admitted.stage,
            outcome=admitted.outcome,
            duration_ms=admitted.duration_ms,
            attempt_count=admitted.attempt_count,
            public_request_id=admitted.public_request_id,
            source_execution_id=admitted.source_execution_id,
            handoff_id=admitted.handoff_id,
            failure_category=admitted.failure_category,
            event_sha256="0" * 64,
            event_id=admitted.event_id,
        )


def test_metric_projection_has_fixed_low_cardinality_dimensions_only() -> None:
    """Project only frozen low-cardinality dimensions from admitted events."""
    event = create_operational_event(
        stage=OperationalStage.PUBLIC_HANDOFF,
        outcome=OperationalOutcome.SUCCEEDED,
        duration_ms=23,
        public_request_id=_PUBLIC_REQUEST_ID,
        source_execution_id=_SOURCE_EXECUTION_ID,
        handoff_id=_HANDOFF_ID,
    )

    count_metric, latency_metric = project_operational_metrics(event)

    assert count_metric.name is OperationalMetricName.STAGE_COUNT
    assert count_metric.value == 1.0
    assert count_metric.unit is OperationalMetricUnit.COUNT
    assert latency_metric.name is OperationalMetricName.STAGE_LATENCY
    assert latency_metric.value == 23.0
    assert latency_metric.unit is OperationalMetricUnit.MILLISECONDS

    expected_dimensions = {
        "ContractVersion": OPERATIONAL_TELEMETRY_CONTRACT_VERSION,
        "Operation": "analyze_public_repository",
        "Outcome": "succeeded",
        "Stage": "public_handoff",
    }
    assert dict(count_metric.dimensions) == expected_dimensions
    assert dict(latency_metric.dimensions) == expected_dimensions

    rendered_dimensions = json.dumps(expected_dimensions, sort_keys=True)
    assert _PUBLIC_REQUEST_ID not in rendered_dimensions
    assert _SOURCE_EXECUTION_ID not in rendered_dimensions
    assert _HANDOFF_ID not in rendered_dimensions


def test_direct_metric_construction_cannot_forge_count_or_latency_semantics() -> None:
    """Reject metric points that violate the deterministic projection contract."""
    with pytest.raises(
        OperationalTelemetryValidationError,
        match="stage count metric must be exactly 1 Count",
    ):
        OperationalMetricPoint(
            name=OperationalMetricName.STAGE_COUNT,
            value=2.0,
            unit=OperationalMetricUnit.COUNT,
            stage=OperationalStage.PUBLIC_HANDOFF,
            outcome=OperationalOutcome.SUCCEEDED,
        )

    with pytest.raises(
        OperationalTelemetryValidationError,
        match="metric value must be one finite float",
    ):
        OperationalMetricPoint(
            name=OperationalMetricName.STAGE_LATENCY,
            value=float("nan"),
            unit=OperationalMetricUnit.MILLISECONDS,
            stage=OperationalStage.PUBLIC_HANDOFF,
            outcome=OperationalOutcome.SUCCEEDED,
        )


def test_event_identity_changes_when_operational_semantics_change() -> None:
    """Change event identity when any canonical operational semantic changes."""
    success = create_operational_event(
        stage=OperationalStage.PUBLIC_HANDOFF,
        outcome=OperationalOutcome.SUCCEEDED,
        duration_ms=20,
        public_request_id=_PUBLIC_REQUEST_ID,
        source_execution_id=_SOURCE_EXECUTION_ID,
        handoff_id=_HANDOFF_ID,
    )
    slower = create_operational_event(
        stage=OperationalStage.PUBLIC_HANDOFF,
        outcome=OperationalOutcome.SUCCEEDED,
        duration_ms=21,
        public_request_id=_PUBLIC_REQUEST_ID,
        source_execution_id=_SOURCE_EXECUTION_ID,
        handoff_id=_HANDOFF_ID,
    )

    assert success.event_id != slower.event_id
