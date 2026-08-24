"""Unit tests for physical NVD incremental attempt identity."""

import json
from datetime import UTC, datetime

import pytest

from opslens.ingestion.nvd.application.incremental_attempt import (
    NvdIncrementalAttemptIdFactory,
)
from opslens.ingestion.nvd.application.incremental_key_factory import (
    NvdIncrementalKeyFactory,
)
from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPageParser,
    NvdCveApiPagination,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


def _window() -> NvdIncrementalWindow:
    """Build one fixed logical incremental window."""
    return NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            7,
            0,
            12,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            7,
            10,
            12,
            tzinfo=UTC,
        ),
    )


def _empty_pagination(
    *,
    source_timestamp: str,
) -> NvdCveApiPagination:
    """Build one exact zero-result NVD response pagination."""
    payload = json.dumps(
        {
            "resultsPerPage": 0,
            "startIndex": 0,
            "totalResults": 0,
            "format": "NVD_CVE",
            "version": "2.0",
            "timestamp": source_timestamp,
            "vulnerabilities": [],
        },
        separators=(",", ":"),
    ).encode()

    page = NvdCveApiPageParser().parse(payload)

    return NvdCveApiPagination(
        pages=(page,),
    )


def test_same_exact_observation_has_same_attempt_id() -> None:
    """Keep physical identity deterministic for identical source bytes."""
    factory = NvdIncrementalAttemptIdFactory()
    pagination = _empty_pagination(
        source_timestamp="2026-08-24T19:51:57.077",
    )

    first = factory.build(
        window=_window(),
        pagination=pagination,
    )

    second = factory.build(
        window=_window(),
        pagination=pagination,
    )

    assert first == second
    assert len(first) == 64


def test_changed_source_timestamp_changes_attempt_id() -> None:
    """Separate repeated NVD observations whose exact bytes changed."""
    factory = NvdIncrementalAttemptIdFactory()
    window = _window()

    first = factory.build(
        window=window,
        pagination=_empty_pagination(
            source_timestamp="2026-08-24T19:51:57.077",
        ),
    )

    second = factory.build(
        window=window,
        pagination=_empty_pagination(
            source_timestamp="2026-08-24T19:55:28.855",
        ),
    )

    assert first != second


def test_attempt_page_key_is_scoped_by_logical_and_physical_identity() -> None:
    """Keep physical observations isolated below the logical update id."""
    window = _window()
    attempt_id = "a" * 64

    key = NvdIncrementalKeyFactory().build_attempt_page_key(
        window=window,
        attempt_id=attempt_id,
        start_index=0,
    )

    assert key == (
        "bronze/nvd/cve/updates/"
        f"update_id={window.update_id}/"
        f"attempt_id={attempt_id}/"
        "page_start=000000/"
        "response.json"
    )


@pytest.mark.parametrize(
    "attempt_id",
    [
        "",
        "abc",
        "A" * 64,
        "g" * 64,
        "a" * 63,
        "a" * 65,
    ],
)
def test_attempt_page_key_rejects_invalid_attempt_identity(
    attempt_id: str,
) -> None:
    """Reject malformed physical-attempt identities."""
    with pytest.raises(
        ValueError,
        match="attempt id",
    ):
        NvdIncrementalKeyFactory().build_attempt_page_key(
            window=_window(),
            attempt_id=attempt_id,
            start_index=0,
        )
