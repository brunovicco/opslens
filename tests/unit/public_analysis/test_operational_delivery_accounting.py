"""Tests for Gate 10.2 operational delivery-accounting integrity."""

from __future__ import annotations

import pytest

from opslens.public_analysis.application import PublicAnalysisOperationalFailure
from opslens.shared.observability.contracts import (
    OperationalFailureCategory,
    OperationalOutcome,
    OperationalStage,
    create_operational_event,
)


def _terminal_request_rejection_event():
    """Create one valid terminal event without external delivery."""
    return create_operational_event(
        stage=OperationalStage.PUBLIC_REQUEST_ADMISSION,
        outcome=OperationalOutcome.REJECTED,
        duration_ms=1,
        failure_category=OperationalFailureCategory.REQUEST_CONTRACT,
    )


def test_operational_failure_rejects_forged_undelivered_event_identity() -> None:
    """Undelivered accounting cannot reference an event that was never admitted."""
    event = _terminal_request_rejection_event()
    forged_id = "operational-telemetry:v1@sha256:" + ("0" * 64)

    with pytest.raises(
        ValueError,
        match="undelivered identities must reference admitted events",
    ):
        PublicAnalysisOperationalFailure(
            stage=OperationalStage.PUBLIC_REQUEST_ADMISSION,
            events=(event,),
            undelivered_event_ids=(forged_id,),
        )


def test_operational_failure_rejects_duplicate_undelivered_event_identity() -> None:
    """One admitted event cannot be counted as multiple sink-delivery failures."""
    event = _terminal_request_rejection_event()

    with pytest.raises(
        ValueError,
        match="undelivered event identities cannot contain duplicates",
    ):
        PublicAnalysisOperationalFailure(
            stage=OperationalStage.PUBLIC_REQUEST_ADMISSION,
            events=(event,),
            undelivered_event_ids=(event.event_id, event.event_id),
        )
