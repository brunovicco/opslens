"""Regression tests for content-minimized AWS Lambda Powertools telemetry."""

from unittest.mock import MagicMock

from aws_lambda_powertools import Logger, Metrics, Tracer

from opslens.shared.observability.powertools import PowertoolsTelemetry


def test_exception_logging_does_not_forward_active_exception_or_traceback() -> None:
    """Attacker-controlled exception text must not cross the shared logger adapter."""
    logger = MagicMock(spec=Logger)
    telemetry = PowertoolsTelemetry(
        logger=logger,
        metrics=MagicMock(spec=Metrics),
        tracer=MagicMock(spec=Tracer),
    )
    attacker_content = "attacker-secret-field=do-not-log-this-value"

    try:
        raise RuntimeError(attacker_content)
    except RuntimeError:
        telemetry.exception(
            "Bounded operation failed",
            fields={"request_id": "request-123"},
        )

    logger.error.assert_called_once_with(
        "Bounded operation failed",
        extra={"request_id": "request-123"},
    )
    logger.exception.assert_not_called()
    assert attacker_content not in repr(logger.mock_calls)


def test_exception_logging_does_not_enable_implicit_stack_capture() -> None:
    """Failure logging must remain explicit structured data, not logging internals."""
    logger = MagicMock(spec=Logger)
    telemetry = PowertoolsTelemetry(
        logger=logger,
        metrics=MagicMock(spec=Metrics),
        tracer=MagicMock(spec=Tracer),
    )

    telemetry.exception("Operation failed")

    logger.error.assert_called_once_with("Operation failed", extra={})
    _, kwargs = logger.error.call_args
    assert "exc_info" not in kwargs
    assert "stack_info" not in kwargs
