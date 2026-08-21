"""Unit tests for deterministic NVD incremental Bronze keys."""

from datetime import UTC, datetime

import pytest

from opslens.ingestion.nvd.application.incremental_key_factory import (
    NvdIncrementalKeyFactory,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


def _window() -> NvdIncrementalWindow:
    """Build one deterministic incremental window."""
    return NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            20,
            0,
            tzinfo=UTC,
        ),
    )


def test_build_page_key_uses_update_identity_and_padded_start() -> None:
    """Place one page under its immutable logical update identity."""
    window = _window()

    key = NvdIncrementalKeyFactory().build_page_key(
        window=window,
        start_index=0,
    )

    assert key == (
        f"bronze/nvd/cve/updates/update_id={window.update_id}/page_start=000000/response.json"
    )


def test_build_page_key_formats_nvd_default_page_offset() -> None:
    """Pad a normal NVD 2000-record page offset deterministically."""
    key = NvdIncrementalKeyFactory().build_page_key(
        window=_window(),
        start_index=2000,
    )

    assert "/page_start=002000/" in key


def test_build_page_key_is_deterministic() -> None:
    """Return the same key for the same window and page offset."""
    factory = NvdIncrementalKeyFactory()
    window = _window()

    first = factory.build_page_key(
        window=window,
        start_index=2000,
    )
    second = factory.build_page_key(
        window=window,
        start_index=2000,
    )

    assert first == second


def test_build_page_key_supports_custom_prefix() -> None:
    """Normalize one explicitly configured Bronze prefix."""
    key = NvdIncrementalKeyFactory(
        "/custom/nvd/updates/",
    ).build_page_key(
        window=_window(),
        start_index=0,
    )

    assert key.startswith("custom/nvd/updates/update_id=")


@pytest.mark.parametrize(
    "prefix",
    [
        "",
        "/",
        "///",
    ],
)
def test_factory_rejects_empty_prefix(
    prefix: str,
) -> None:
    """Reject prefixes empty after normalization."""
    with pytest.raises(
        ValueError,
        match="prefix cannot be empty",
    ):
        NvdIncrementalKeyFactory(prefix)


def test_build_page_key_rejects_negative_start_index() -> None:
    """Reject negative API pagination offsets."""
    with pytest.raises(
        ValueError,
        match="must not be negative",
    ):
        NvdIncrementalKeyFactory().build_page_key(
            window=_window(),
            start_index=-1,
        )


def test_build_page_key_rejects_boolean_start_index() -> None:
    """Reject booleans even though bool subclasses int."""
    with pytest.raises(
        ValueError,
        match="must be an integer",
    ):
        NvdIncrementalKeyFactory().build_page_key(
            window=_window(),
            start_index=True,
        )
