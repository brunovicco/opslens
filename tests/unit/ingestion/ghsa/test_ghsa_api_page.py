"""Tests for validated GHSA REST pages and exact cursor pagination."""

import json
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest

from opslens.ingestion.ghsa.domain.api_page import (
    GhsaAdvisoryApiPageParser,
    GhsaAdvisoryPagination,
    GhsaRequestUrlPolicy,
)
from opslens.ingestion.ghsa.domain.errors import (
    InvalidGhsaApiPageError,
    InvalidGhsaPaginationError,
    InvalidGhsaRequestUrlError,
)
from opslens.ingestion.ghsa.domain.sync import (
    GhsaSyncMode,
    GhsaSyncWindow,
)


def _window(mode: GhsaSyncMode = GhsaSyncMode.PUBLISHED) -> GhsaSyncWindow:
    """Build one bounded July 2026 source window."""
    return GhsaSyncWindow(
        mode=mode,
        start_at=datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC),
        end_at=datetime(2026, 7, 31, 23, 59, 59, tzinfo=UTC),
    )


def _advisory(
    ghsa_id: str,
    *,
    published_at: str,
    updated_at: str,
    advisory_type: str = "reviewed",
) -> dict[str, object]:
    """Build the minimum advisory fields required by the Bronze parser."""
    return {
        "ghsa_id": ghsa_id,
        "type": advisory_type,
        "published_at": published_at,
        "updated_at": updated_at,
    }


def _payload(*items: dict[str, object]) -> bytes:
    """Serialize one exact source-like response array."""
    return json.dumps(
        list(items),
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _with_after_cursor(url: str, cursor: str) -> str:
    """Append one opaque `after` cursor without changing source query fields."""
    parsed = urlsplit(url)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    pairs.append(("after", cursor))
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(pairs),
            "",
        )
    )


def test_parses_reviewed_page_and_binds_exact_response_bytes() -> None:
    """Preserve exact bytes, GHSA identities, timestamps, and source URL."""
    window = _window()
    request_url = GhsaRequestUrlPolicy.build_initial(window)
    payload = _payload(
        _advisory(
            "GHSA-2345-6789-cfgh",
            published_at="2026-07-02T10:00:00Z",
            updated_at="2026-07-03T10:00:00Z",
        ),
        _advisory(
            "GHSA-2345-6789-cfgj",
            published_at="2026-07-04T10:00:00Z",
            updated_at="2026-07-05T10:00:00Z",
        ),
    )

    page = GhsaAdvisoryApiPageParser().parse(
        payload,
        request_url=request_url,
        link_header=None,
        window=window,
    )

    assert page.raw_bytes == payload
    assert page.size_bytes == len(payload)
    assert len(page.sha256) == 64
    assert page.item_count == 2
    assert page.ghsa_ids == (
        "GHSA-2345-6789-cfgh",
        "GHSA-2345-6789-cfgj",
    )
    assert page.next_url is None


def test_modified_window_accepts_old_advisory_updated_inside_range() -> None:
    """Match GitHub modified semantics using published-or-updated timestamps."""
    window = _window(GhsaSyncMode.MODIFIED)
    payload = _payload(
        _advisory(
            "GHSA-2345-6789-cfgh",
            published_at="2025-01-02T10:00:00Z",
            updated_at="2026-07-03T10:00:00Z",
        )
    )

    page = GhsaAdvisoryApiPageParser().parse(
        payload,
        request_url=GhsaRequestUrlPolicy.build_initial(window),
        link_header=None,
        window=window,
    )

    assert page.item_count == 1


def test_rejects_non_reviewed_advisory() -> None:
    """Fail closed if the source violates the reviewed-only filter contract."""
    window = _window()
    payload = _payload(
        _advisory(
            "GHSA-2345-6789-cfgh",
            published_at="2026-07-02T10:00:00Z",
            updated_at="2026-07-03T10:00:00Z",
            advisory_type="unreviewed",
        )
    )

    with pytest.raises(
        InvalidGhsaApiPageError,
        match="reviewed-only scope",
    ):
        GhsaAdvisoryApiPageParser().parse(
            payload,
            request_url=GhsaRequestUrlPolicy.build_initial(window),
            link_header=None,
            window=window,
        )


def test_rejects_advisory_outside_published_window() -> None:
    """Verify the response satisfies the exact bounded published filter."""
    window = _window()
    payload = _payload(
        _advisory(
            "GHSA-2345-6789-cfgh",
            published_at="2026-08-01T00:00:00Z",
            updated_at="2026-08-01T00:00:00Z",
        )
    )

    with pytest.raises(
        InvalidGhsaApiPageError,
        match="outside the published window",
    ):
        GhsaAdvisoryApiPageParser().parse(
            payload,
            request_url=GhsaRequestUrlPolicy.build_initial(window),
            link_header=None,
            window=window,
        )


def test_rejects_duplicate_advisory_ids_inside_page() -> None:
    """Prevent one source page from silently duplicating a GHSA occurrence."""
    window = _window()
    item = _advisory(
        "GHSA-2345-6789-cfgh",
        published_at="2026-07-02T10:00:00Z",
        updated_at="2026-07-03T10:00:00Z",
    )

    with pytest.raises(
        InvalidGhsaApiPageError,
        match="duplicate advisory identifiers",
    ):
        GhsaAdvisoryApiPageParser().parse(
            _payload(item, item),
            request_url=GhsaRequestUrlPolicy.build_initial(window),
            link_header=None,
            window=window,
        )


def test_rejects_external_rel_next_url() -> None:
    """Treat the source Link header as untrusted input for outbound navigation."""
    window = _window()
    payload = _payload(
        _advisory(
            "GHSA-2345-6789-cfgh",
            published_at="2026-07-02T10:00:00Z",
            updated_at="2026-07-03T10:00:00Z",
        )
    )
    hostile = (
        "https://example.com/advisories?type=reviewed&"
        "published=2026-07-01T00%3A00%3A00%2B00%3A00.."
        "2026-07-31T23%3A59%3A59%2B00%3A00&sort=published&"
        "direction=asc&per_page=100&after=cursor"
    )

    with pytest.raises(
        InvalidGhsaApiPageError,
        match=r"host must be api\.github\.com",
    ):
        GhsaAdvisoryApiPageParser().parse(
            payload,
            request_url=GhsaRequestUrlPolicy.build_initial(window),
            link_header=f'<{hostile}>; rel="next"',
            window=window,
        )


def test_rejects_malformed_query_as_domain_request_url_error() -> None:
    """Keep strict query parsing failures inside the GHSA request-URL boundary."""
    window = _window()
    malformed = f"{GhsaRequestUrlPolicy.build_initial(window)}&broken"

    with pytest.raises(
        InvalidGhsaRequestUrlError,
        match="request URL is malformed",
    ):
        GhsaRequestUrlPolicy.validate(
            malformed,
            window=window,
            require_cursor=None,
        )


def test_complete_pagination_follows_exact_rel_next_url() -> None:
    """Accept only the exact cursor chain ending with a page without rel=next."""
    window = _window()
    initial_url = GhsaRequestUrlPolicy.build_initial(window)
    next_url = _with_after_cursor(initial_url, "opaque-cursor-1")
    parser = GhsaAdvisoryApiPageParser()

    first = parser.parse(
        _payload(
            _advisory(
                "GHSA-2345-6789-cfgh",
                published_at="2026-07-02T10:00:00Z",
                updated_at="2026-07-03T10:00:00Z",
            )
        ),
        request_url=initial_url,
        link_header=f'<{next_url}>; rel="next"',
        window=window,
    )
    second = parser.parse(
        _payload(
            _advisory(
                "GHSA-2345-6789-cfgj",
                published_at="2026-07-04T10:00:00Z",
                updated_at="2026-07-05T10:00:00Z",
            )
        ),
        request_url=next_url,
        link_header=None,
        window=window,
    )

    pagination = GhsaAdvisoryPagination(
        window=window,
        pages=(first, second),
    )

    assert pagination.total_items == 2
    assert pagination.total_bytes == first.size_bytes + second.size_bytes


def test_rejects_incomplete_final_page_with_next_cursor() -> None:
    """Do not declare a synchronization complete while GitHub advertises more data."""
    window = _window()
    initial_url = GhsaRequestUrlPolicy.build_initial(window)
    next_url = _with_after_cursor(initial_url, "opaque-cursor-1")
    first = GhsaAdvisoryApiPageParser().parse(
        _payload(
            _advisory(
                "GHSA-2345-6789-cfgh",
                published_at="2026-07-02T10:00:00Z",
                updated_at="2026-07-03T10:00:00Z",
            )
        ),
        request_url=initial_url,
        link_header=f'<{next_url}>; rel="next"',
        window=window,
    )

    with pytest.raises(
        InvalidGhsaPaginationError,
        match="final page still has rel=next",
    ):
        GhsaAdvisoryPagination(
            window=window,
            pages=(first,),
        )


def test_rejects_cross_page_duplicate_advisory_id() -> None:
    """Detect cursor instability that repeats an advisory across pages."""
    window = _window()
    initial_url = GhsaRequestUrlPolicy.build_initial(window)
    next_url = _with_after_cursor(initial_url, "opaque-cursor-1")
    parser = GhsaAdvisoryApiPageParser()
    common = _advisory(
        "GHSA-2345-6789-cfgh",
        published_at="2026-07-02T10:00:00Z",
        updated_at="2026-07-03T10:00:00Z",
    )
    first = parser.parse(
        _payload(common),
        request_url=initial_url,
        link_header=f'<{next_url}>; rel="next"',
        window=window,
    )
    second = parser.parse(
        _payload(dict(common)),
        request_url=next_url,
        link_header=None,
        window=window,
    )

    with pytest.raises(
        InvalidGhsaPaginationError,
        match="duplicate advisory identifiers",
    ):
        GhsaAdvisoryPagination(
            window=window,
            pages=(first, second),
        )


def test_rejects_cross_page_published_sort_regression() -> None:
    """Detect a cursor sequence that violates the frozen published ascending order."""
    window = _window()
    initial_url = GhsaRequestUrlPolicy.build_initial(window)
    next_url = _with_after_cursor(initial_url, "opaque-cursor-1")
    parser = GhsaAdvisoryApiPageParser()
    first = parser.parse(
        _payload(
            _advisory(
                "GHSA-2345-6789-cfgh",
                published_at="2026-07-20T10:00:00Z",
                updated_at="2026-07-20T10:00:00Z",
            )
        ),
        request_url=initial_url,
        link_header=f'<{next_url}>; rel="next"',
        window=window,
    )
    second = parser.parse(
        _payload(
            _advisory(
                "GHSA-2345-6789-cfgj",
                published_at="2026-07-10T10:00:00Z",
                updated_at="2026-07-10T10:00:00Z",
            )
        ),
        request_url=next_url,
        link_header=None,
        window=window,
    )

    with pytest.raises(
        InvalidGhsaPaginationError,
        match="cross-page published ordering",
    ):
        GhsaAdvisoryPagination(
            window=window,
            pages=(first, second),
        )
