"""Unit tests for NVD CVE API page and pagination contracts."""

import hashlib
import json

import pytest

from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPageParser,
    NvdCveApiPagination,
)
from opslens.ingestion.nvd.domain.errors import (
    InvalidNvdCveApiPageError,
    InvalidNvdCveApiPaginationError,
)


def _payload(
    *,
    start_index: int,
    total_results: int,
    cve_ids: tuple[str, ...],
    results_per_page: int | None = None,
) -> bytes:
    """Build one deterministic synthetic NVD CVE API response."""
    resolved_results_per_page = len(cve_ids) if results_per_page is None else results_per_page

    document: dict[str, object] = {
        "resultsPerPage": resolved_results_per_page,
        "startIndex": start_index,
        "totalResults": total_results,
        "format": "NVD_CVE",
        "version": "2.0",
        "timestamp": "2026-08-18T20:00:00.000",
        "vulnerabilities": [
            {
                "cve": {
                    "id": cve_id,
                }
            }
            for cve_id in cve_ids
        ],
    }

    return json.dumps(
        document,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _page(
    *,
    start_index: int,
    total_results: int,
    cve_ids: tuple[str, ...],
):
    """Parse one valid synthetic API page."""
    return NvdCveApiPageParser().parse(
        _payload(
            start_index=start_index,
            total_results=total_results,
            cve_ids=cve_ids,
        )
    )


def test_parser_preserves_exact_page_evidence() -> None:
    """Preserve source bytes and their cryptographic identity."""
    payload = _payload(
        start_index=0,
        total_results=2,
        cve_ids=(
            "CVE-2026-1000",
            "CVE-2026-1001",
        ),
    )

    page = NvdCveApiPageParser().parse(payload)

    assert page.raw_bytes == payload
    assert page.sha256 == hashlib.sha256(payload).hexdigest()
    assert page.results_per_page == 2
    assert page.start_index == 0
    assert page.total_results == 2
    assert page.source_format == "NVD_CVE"
    assert page.source_version == "2.0"
    assert page.cve_ids == (
        "CVE-2026-1000",
        "CVE-2026-1001",
    )
    assert page.next_start_index == 2
    assert page.is_final_page


def test_parser_accepts_empty_result_page() -> None:
    """Represent a valid zero-result incremental window."""
    page = NvdCveApiPageParser().parse(
        _payload(
            start_index=0,
            total_results=0,
            cve_ids=(),
        )
    )

    assert page.results_per_page == 0
    assert page.total_results == 0
    assert page.cve_ids == ()
    assert page.is_final_page


def test_parser_rejects_invalid_utf8() -> None:
    """Reject source bytes that are not valid UTF-8."""
    with pytest.raises(
        InvalidNvdCveApiPageError,
        match="not valid UTF-8",
    ):
        NvdCveApiPageParser().parse(b"\xff")


def test_parser_rejects_invalid_json() -> None:
    """Reject malformed JSON before creating source evidence."""
    with pytest.raises(
        InvalidNvdCveApiPageError,
        match="not valid JSON",
    ):
        NvdCveApiPageParser().parse(b"{")


def test_parser_rejects_missing_required_field() -> None:
    """Require the complete NVD pagination envelope."""
    document = {
        "resultsPerPage": 0,
        "startIndex": 0,
        "totalResults": 0,
        "format": "NVD_CVE",
        "version": "2.0",
        "timestamp": "2026-08-18T20:00:00.000",
    }

    with pytest.raises(
        InvalidNvdCveApiPageError,
        match="vulnerabilities",
    ):
        NvdCveApiPageParser().parse(json.dumps(document).encode())


def test_parser_rejects_boolean_integer_field() -> None:
    """Reject booleans from integer pagination fields."""
    document: dict[str, object] = {
        "resultsPerPage": True,
        "startIndex": 0,
        "totalResults": 0,
        "format": "NVD_CVE",
        "version": "2.0",
        "timestamp": "2026-08-18T20:00:00.000",
        "vulnerabilities": [],
    }

    with pytest.raises(
        InvalidNvdCveApiPageError,
        match="resultsPerPage must be an integer",
    ):
        NvdCveApiPageParser().parse(json.dumps(document).encode())


def test_parser_rejects_results_per_page_over_limit() -> None:
    """Enforce the documented NVD CVE API page-size maximum."""
    document: dict[str, object] = {
        "resultsPerPage": 2001,
        "startIndex": 0,
        "totalResults": 2001,
        "format": "NVD_CVE",
        "version": "2.0",
        "timestamp": "2026-08-18T20:00:00.000",
        "vulnerabilities": [],
    }

    with pytest.raises(
        InvalidNvdCveApiPageError,
        match="must not exceed 2000",
    ):
        NvdCveApiPageParser().parse(json.dumps(document).encode())


def test_parser_rejects_record_count_mismatch() -> None:
    """Require resultsPerPage to match returned vulnerability count."""
    with pytest.raises(
        InvalidNvdCveApiPageError,
        match="does not match",
    ):
        NvdCveApiPageParser().parse(
            _payload(
                start_index=0,
                total_results=2,
                cve_ids=("CVE-2026-1000",),
                results_per_page=2,
            )
        )


def test_parser_rejects_invalid_cve_identifier() -> None:
    """Fail closed when required CVE identity is malformed."""
    with pytest.raises(
        InvalidNvdCveApiPageError,
        match="Invalid NVD CVE identifier",
    ):
        NvdCveApiPageParser().parse(
            _payload(
                start_index=0,
                total_results=1,
                cve_ids=("NOT-A-CVE",),
            )
        )


def test_parser_rejects_duplicate_cve_in_page() -> None:
    """Reject duplicate logical CVE records within one page."""
    with pytest.raises(
        InvalidNvdCveApiPageError,
        match="duplicate CVE identifiers",
    ):
        NvdCveApiPageParser().parse(
            _payload(
                start_index=0,
                total_results=2,
                cve_ids=(
                    "CVE-2026-1000",
                    "CVE-2026-1000",
                ),
            )
        )


def test_pagination_accepts_complete_contiguous_run() -> None:
    """Validate all records across contiguous response pages."""
    pagination = NvdCveApiPagination(
        pages=(
            _page(
                start_index=0,
                total_results=5,
                cve_ids=(
                    "CVE-2026-1000",
                    "CVE-2026-1001",
                ),
            ),
            _page(
                start_index=2,
                total_results=5,
                cve_ids=(
                    "CVE-2026-1002",
                    "CVE-2026-1003",
                ),
            ),
            _page(
                start_index=4,
                total_results=5,
                cve_ids=("CVE-2026-1004",),
            ),
        )
    )

    assert pagination.total_results == 5
    assert pagination.page_count == 3
    assert pagination.cve_ids == (
        "CVE-2026-1000",
        "CVE-2026-1001",
        "CVE-2026-1002",
        "CVE-2026-1003",
        "CVE-2026-1004",
    )


def test_pagination_rejects_total_results_change() -> None:
    """Fail when totalResults changes between requests."""
    with pytest.raises(
        InvalidNvdCveApiPaginationError,
        match="totalResults changed",
    ):
        NvdCveApiPagination(
            pages=(
                _page(
                    start_index=0,
                    total_results=4,
                    cve_ids=(
                        "CVE-2026-1000",
                        "CVE-2026-1001",
                    ),
                ),
                _page(
                    start_index=2,
                    total_results=5,
                    cve_ids=(
                        "CVE-2026-1002",
                        "CVE-2026-1003",
                    ),
                ),
            )
        )


def test_pagination_rejects_gap() -> None:
    """Fail closed when a page starts after the expected index."""
    with pytest.raises(
        InvalidNvdCveApiPaginationError,
        match="gap, overlap, or out-of-order",
    ):
        NvdCveApiPagination(
            pages=(
                _page(
                    start_index=0,
                    total_results=5,
                    cve_ids=(
                        "CVE-2026-1000",
                        "CVE-2026-1001",
                    ),
                ),
                _page(
                    start_index=3,
                    total_results=5,
                    cve_ids=(
                        "CVE-2026-1003",
                        "CVE-2026-1004",
                    ),
                ),
            )
        )


def test_pagination_rejects_overlap() -> None:
    """Fail closed when a page overlaps a previous page."""
    with pytest.raises(
        InvalidNvdCveApiPaginationError,
        match="gap, overlap, or out-of-order",
    ):
        NvdCveApiPagination(
            pages=(
                _page(
                    start_index=0,
                    total_results=4,
                    cve_ids=(
                        "CVE-2026-1000",
                        "CVE-2026-1001",
                    ),
                ),
                _page(
                    start_index=1,
                    total_results=4,
                    cve_ids=(
                        "CVE-2026-1002",
                        "CVE-2026-1003",
                    ),
                ),
            )
        )


def test_pagination_rejects_duplicate_cve_across_pages() -> None:
    """Fail when separate pages repeat the same logical CVE."""
    with pytest.raises(
        InvalidNvdCveApiPaginationError,
        match="duplicate CVE identifiers",
    ):
        NvdCveApiPagination(
            pages=(
                _page(
                    start_index=0,
                    total_results=4,
                    cve_ids=(
                        "CVE-2026-1000",
                        "CVE-2026-1001",
                    ),
                ),
                _page(
                    start_index=2,
                    total_results=4,
                    cve_ids=(
                        "CVE-2026-1001",
                        "CVE-2026-1002",
                    ),
                ),
            )
        )


def test_pagination_rejects_incomplete_run() -> None:
    """Require the page inventory to reach totalResults."""
    with pytest.raises(
        InvalidNvdCveApiPaginationError,
        match="pagination is incomplete",
    ):
        NvdCveApiPagination(
            pages=(
                _page(
                    start_index=0,
                    total_results=5,
                    cve_ids=(
                        "CVE-2026-1000",
                        "CVE-2026-1001",
                    ),
                ),
            )
        )


def test_pagination_rejects_empty_page_inventory() -> None:
    """Require explicit source evidence even for zero results."""
    with pytest.raises(
        InvalidNvdCveApiPaginationError,
        match="at least one page",
    ):
        NvdCveApiPagination(pages=())


def test_pagination_accepts_one_zero_result_page() -> None:
    """Treat one explicit empty response as complete evidence."""
    pagination = NvdCveApiPagination(
        pages=(
            _page(
                start_index=0,
                total_results=0,
                cve_ids=(),
            ),
        )
    )

    assert pagination.total_results == 0
    assert pagination.page_count == 1
    assert pagination.cve_ids == ()
