"""Tests for bounded end-to-end GHSA Bronze runtime composition."""

import json
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest

from opslens.ingestion.ghsa.application.attempt import GhsaAttemptIdFactory
from opslens.ingestion.ghsa.application.key_factory import GhsaBronzeKeyFactory
from opslens.ingestion.ghsa.application.manifest import (
    GhsaCompleteManifest,
    GhsaCompleteManifestFactory,
    GhsaCompleteManifestSerializer,
)
from opslens.ingestion.ghsa.application.models import GhsaBronzeWriteResult
from opslens.ingestion.ghsa.application.ports import GhsaFetchedPage
from opslens.ingestion.ghsa.application.runtime import (
    GhsaBronzeRuntimeService,
    GhsaSubdivisionBudgetExceededError,
)
from opslens.ingestion.ghsa.application.subdivision import GhsaWindowSubdivisionPlanner
from opslens.ingestion.ghsa.domain.api_page import (
    GhsaAdvisoryApiPage,
    GhsaAdvisoryApiPageParser,
    GhsaAdvisoryPagination,
    GhsaRequestUrlPolicy,
)
from opslens.ingestion.ghsa.domain.sync import GhsaSyncMode, GhsaSyncWindow


class _Telemetry:
    """No-op operational telemetry test double."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore informational events."""
        del message, fields

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore exception events."""
        del message, fields

    def metric(self, name: str, value: float, unit: str) -> None:
        """Ignore metrics."""
        del name, value, unit

    def span(self, name: str) -> AbstractContextManager[object]:
        """Return a no-op span."""
        del name
        return nullcontext(object())


class _QueueSource:
    """Return a deterministic queue of fetched source pages."""

    def __init__(self, pages: list[GhsaFetchedPage]) -> None:
        """Initialize the source queue."""
        self.pages = pages
        self.request_urls: list[str] = []

    def fetch(
        self,
        *,
        request_url: str,
        window: GhsaSyncWindow,
    ) -> GhsaFetchedPage:
        """Return the next controlled fetched page."""
        del window
        self.request_urls.append(request_url)
        return self.pages.pop(0)


class _SubdivisionSource:
    """Force only the root window to advertise a continuation page."""

    def __init__(self, root: GhsaSyncWindow) -> None:
        """Remember the root synchronization identity."""
        self.root = root
        self.requested_sync_ids: list[str] = []

    def fetch(
        self,
        *,
        request_url: str,
        window: GhsaSyncWindow,
    ) -> GhsaFetchedPage:
        """Return one overflowing root page and complete child pages."""
        del request_url
        self.requested_sync_ids.append(window.sync_id)
        published_at = window.start_at + timedelta(seconds=1)

        if window.sync_id == self.root.sync_id:
            next_url = _with_after_cursor(
                GhsaRequestUrlPolicy.build_initial(window),
                "root-overflow",
            )
            return GhsaFetchedPage(
                payload=_payload(
                    "GHSA-2345-6789-cfgh",
                    published_at=published_at,
                ),
                link_header=f'<{next_url}>; rel="next"',
            )

        ghsa_id = (
            "GHSA-2345-6789-cfgj"
            if window.start_at == self.root.start_at
            else "GHSA-2345-6789-cfgm"
        )
        return GhsaFetchedPage(
            payload=_payload(ghsa_id, published_at=published_at),
            link_header=None,
        )


class _Repository:
    """Record deterministic page and manifest persistence calls."""

    def __init__(self, *, fail_page_number: int | None = None) -> None:
        """Initialize persistence recording and optional failure injection."""
        self.fail_page_number = fail_page_number
        self.page_calls: list[tuple[str, str]] = []
        self.manifest_calls: list[str] = []
        self.call_order: list[str] = []

    def create_page(
        self,
        *,
        page: GhsaAdvisoryApiPage,
        window: GhsaSyncWindow,
        object_key: str,
    ) -> GhsaBronzeWriteResult:
        """Return exact synthetic version evidence for one page."""
        del page
        page_number = len(self.page_calls) + 1
        self.page_calls.append((window.sync_id, object_key))
        self.call_order.append("page")

        if self.fail_page_number == page_number:
            raise RuntimeError("synthetic page persistence failure")

        return GhsaBronzeWriteResult(
            key=object_key,
            version_id=f"page-version-{page_number}",
        )

    def create_manifest(
        self,
        *,
        manifest: GhsaCompleteManifest,
        payload: bytes,
        object_key: str,
    ) -> GhsaBronzeWriteResult:
        """Return exact synthetic version evidence for one COMPLETE manifest."""
        assert payload
        self.manifest_calls.append(manifest.attempt_id)
        self.call_order.append("manifest")
        return GhsaBronzeWriteResult(
            key=object_key,
            version_id=f"manifest-version-{len(self.manifest_calls)}",
        )


def _window(*, end_second: int = 10) -> GhsaSyncWindow:
    """Build one small whole-second published window."""
    return GhsaSyncWindow(
        mode=GhsaSyncMode.PUBLISHED,
        start_at=datetime(2026, 8, 1, 0, 0, 0, tzinfo=UTC),
        end_at=datetime(2026, 8, 1, 0, 0, end_second, tzinfo=UTC),
    )


def _payload(ghsa_id: str, *, published_at: datetime) -> bytes:
    """Build one minimum reviewed GitHub advisory response page."""
    timestamp = published_at.isoformat(timespec="seconds").replace("+00:00", "Z")
    return json.dumps(
        [
            {
                "ghsa_id": ghsa_id,
                "type": "reviewed",
                "published_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        separators=(",", ":"),
    ).encode()


def _with_after_cursor(url: str, cursor: str) -> str:
    """Append one exact opaque GitHub `after` cursor."""
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


def _service(
    *,
    source: _QueueSource | _SubdivisionSource,
    repository: _Repository,
    max_leaf_windows: int = 64,
) -> GhsaBronzeRuntimeService:
    """Compose the runtime with deterministic test dependencies."""
    attempt_factory = GhsaAttemptIdFactory()
    key_factory = GhsaBronzeKeyFactory()
    return GhsaBronzeRuntimeService(
        source=source,
        repository=repository,
        parser=GhsaAdvisoryApiPageParser(),
        attempt_factory=attempt_factory,
        key_factory=key_factory,
        manifest_factory=GhsaCompleteManifestFactory(
            attempt_factory=attempt_factory,
            key_factory=key_factory,
        ),
        manifest_serializer=GhsaCompleteManifestSerializer(),
        subdivision_planner=GhsaWindowSubdivisionPlanner(),
        telemetry=_Telemetry(),
        max_leaf_windows=max_leaf_windows,
    )


def test_runtime_completes_one_page_attempt_before_returning() -> None:
    """Persist the exact page followed by its COMPLETE manifest."""
    window = _window()
    source = _QueueSource(
        [
            GhsaFetchedPage(
                payload=_payload(
                    "GHSA-2345-6789-cfgh",
                    published_at=window.start_at + timedelta(seconds=1),
                ),
                link_header=None,
            )
        ]
    )
    repository = _Repository()

    completions = _service(source=source, repository=repository).run(window)

    assert len(completions) == 1
    assert completions[0].sync_id == window.sync_id
    assert completions[0].page_count == 1
    assert completions[0].total_items == 1
    assert completions[0].manifest_version_id == "manifest-version-1"
    assert repository.call_order == ["page", "manifest"]
    assert completions[0].manifest_key.endswith("/manifest.json")


def test_runtime_follows_complete_cursor_chain_before_persistence() -> None:
    """Fetch the exact rel=next chain and persist only after it is complete."""
    window = _window()
    initial_url = GhsaRequestUrlPolicy.build_initial(window)
    next_url = _with_after_cursor(initial_url, "cursor-1")
    source = _QueueSource(
        [
            GhsaFetchedPage(
                payload=_payload(
                    "GHSA-2345-6789-cfgh",
                    published_at=window.start_at + timedelta(seconds=1),
                ),
                link_header=f'<{next_url}>; rel="next"',
            ),
            GhsaFetchedPage(
                payload=_payload(
                    "GHSA-2345-6789-cfgj",
                    published_at=window.start_at + timedelta(seconds=2),
                ),
                link_header=None,
            ),
        ]
    )
    repository = _Repository()

    completions = _service(source=source, repository=repository).run(window)

    assert source.request_urls == [initial_url, next_url]
    assert completions[0].page_count == 2
    assert completions[0].total_items == 2
    assert repository.call_order == ["page", "page", "manifest"]


def test_runtime_never_publishes_complete_after_partial_page_persistence() -> None:
    """Leave a partial attempt without COMPLETE evidence when a page write fails."""
    window = _window()
    initial_url = GhsaRequestUrlPolicy.build_initial(window)
    next_url = _with_after_cursor(initial_url, "cursor-1")
    source = _QueueSource(
        [
            GhsaFetchedPage(
                payload=_payload(
                    "GHSA-2345-6789-cfgh",
                    published_at=window.start_at + timedelta(seconds=1),
                ),
                link_header=f'<{next_url}>; rel="next"',
            ),
            GhsaFetchedPage(
                payload=_payload(
                    "GHSA-2345-6789-cfgj",
                    published_at=window.start_at + timedelta(seconds=2),
                ),
                link_header=None,
            ),
        ]
    )
    repository = _Repository(fail_page_number=2)

    with pytest.raises(RuntimeError, match="synthetic page persistence failure"):
        _service(source=source, repository=repository).run(window)

    assert repository.call_order == ["page", "page"]
    assert repository.manifest_calls == []


def test_runtime_subdivides_capacity_overflow_before_persisting_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Split an oversized root and persist only deterministic leaf attempts."""
    monkeypatch.setattr(GhsaAdvisoryPagination, "MAX_PAGES", 1)
    root = _window()
    planner = GhsaWindowSubdivisionPlanner()
    left, right = planner.split(root)
    source = _SubdivisionSource(root)
    repository = _Repository()

    completions = _service(source=source, repository=repository).run(root)

    assert tuple(item.sync_id for item in completions) == (
        left.sync_id,
        right.sync_id,
    )
    assert tuple(sync_id for sync_id, _key in repository.page_calls) == (
        left.sync_id,
        right.sync_id,
    )
    assert root.sync_id not in {sync_id for sync_id, _key in repository.page_calls}
    assert repository.call_order == ["page", "manifest", "page", "manifest"]


def test_runtime_fails_closed_when_subdivision_exceeds_leaf_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bound recursive source expansion rather than creating unbounded child work."""
    monkeypatch.setattr(GhsaAdvisoryPagination, "MAX_PAGES", 1)
    root = _window()
    source = _SubdivisionSource(root)
    repository = _Repository()

    with pytest.raises(
        GhsaSubdivisionBudgetExceededError,
        match="leaf-window budget",
    ):
        _service(
            source=source,
            repository=repository,
            max_leaf_windows=1,
        ).run(root)

    assert repository.call_order == []
