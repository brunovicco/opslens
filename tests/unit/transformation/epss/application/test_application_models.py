"""Unit tests for EPSS Silver application models."""

import pytest

from opslens.transformation.epss.application.models import SilverWriteResult


def test_accepts_valid_silver_write_result() -> None:
    """Accept metadata describing a successfully serialized Silver artifact."""
    result = SilverWriteResult(
        row_count=360_142,
        size_bytes=1_500_000,
        schema_version=1,
    )

    assert result.row_count == 360_142
    assert result.size_bytes == 1_500_000
    assert result.schema_version == 1


@pytest.mark.parametrize("row_count", [0, -1])
def test_rejects_non_positive_row_count(row_count: int) -> None:
    """Reject serialization results without persisted rows."""
    with pytest.raises(ValueError, match="at least one row"):
        SilverWriteResult(
            row_count=row_count,
            size_bytes=100,
            schema_version=1,
        )


@pytest.mark.parametrize("size_bytes", [0, -1])
def test_rejects_non_positive_size(size_bytes: int) -> None:
    """Reject serialization results without a physical artifact."""
    with pytest.raises(ValueError, match="greater than zero"):
        SilverWriteResult(
            row_count=1,
            size_bytes=size_bytes,
            schema_version=1,
        )


@pytest.mark.parametrize("schema_version", [0, -1])
def test_rejects_non_positive_schema_version(schema_version: int) -> None:
    """Reject invalid physical schema versions."""
    with pytest.raises(ValueError, match="schema version"):
        SilverWriteResult(
            row_count=1,
            size_bytes=100,
            schema_version=schema_version,
        )
