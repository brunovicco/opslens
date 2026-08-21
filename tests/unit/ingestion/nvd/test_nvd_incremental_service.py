"""Unit tests for NVD incremental Bronze application orchestration."""

import json
from datetime import UTC, datetime

import pytest

from opslens.ingestion.nvd.application.incremental_key_factory import (
    NvdIncrementalKeyFactory,
)
from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifest,
    NvdIncrementalManifestFactory,
    NvdIncrementalManifestSerializer,
)
from opslens.ingestion.nvd.application.incremental_service import (
    IngestNvdIncrementalWindow,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
    NvdBronzeWriteStatus,
)
from opslens.ingestion.nvd.application.watermark import (
    NvdWatermarkCandidateFactory,
    NvdWatermarkCandidateSerializer,
    NvdWatermarkTransitionValidator,
)
from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPage,
    NvdCveApiPageParser,
)
from opslens.ingestion.nvd.domain.errors import (
    InvalidNvdCveApiPaginationError,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


def _window() -> NvdIncrementalWindow:
    """Build the deterministic Phase 2.3 incremental test window."""
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


def _payload(
    *,
    start_index: int,
    total_results: int,
    cve_ids: tuple[str, ...],
    timestamp: str,
) -> bytes:
    """Build one deterministic synthetic CVE API response."""
    document: dict[str, object] = {
        "resultsPerPage": len(cve_ids),
        "startIndex": start_index,
        "totalResults": total_results,
        "format": "NVD_CVE",
        "version": "2.0",
        "timestamp": timestamp,
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
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _three_page_payloads() -> dict[
    int,
    bytes,
]:
    """Build one complete deterministic three-page run."""
    return {
        0: _payload(
            start_index=0,
            total_results=5,
            cve_ids=(
                "CVE-2026-1000",
                "CVE-2026-1001",
            ),
            timestamp=("2026-08-18T20:00:01.000"),
        ),
        2: _payload(
            start_index=2,
            total_results=5,
            cve_ids=(
                "CVE-2026-1002",
                "CVE-2026-1003",
            ),
            timestamp=("2026-08-18T20:00:07.000"),
        ),
        4: _payload(
            start_index=4,
            total_results=5,
            cve_ids=("CVE-2026-1004",),
            timestamp=("2026-08-18T20:00:13.000"),
        ),
    }


class FakeSource:
    """Return exact synthetic source pages while recording access order."""

    def __init__(
        self,
        *,
        payloads: dict[int, bytes],
        calls: list[str],
    ) -> None:
        """Initialize deterministic source responses."""
        self._payloads = payloads
        self._calls = calls

    def fetch_page(
        self,
        *,
        window: NvdIncrementalWindow,
        start_index: int,
    ) -> bytes:
        """Return one requested source page."""
        self._calls.append(f"fetch:{start_index}")

        payload = self._payloads.get(start_index)

        if payload is None:
            raise AssertionError(f"Unexpected NVD page request: {start_index}.")

        return payload


class FakeRepository:
    """Simulate immutable Bronze persistence with deterministic replay."""

    def __init__(
        self,
        *,
        calls: list[str],
        fail_page_start: int | None = None,
    ) -> None:
        """Initialize fake immutable object storage."""
        self._calls = calls
        self._fail_page_start = fail_page_start
        self.objects: dict[
            str,
            tuple[bytes, str],
        ] = {}
        self.manifest_payloads: list[bytes] = []
        self.manifests: list[NvdIncrementalManifest] = []

    def create_page(
        self,
        *,
        page: NvdCveApiPage,
        window: NvdIncrementalWindow,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Create or replay one exact API page."""
        self._calls.append(f"page:{page.start_index}")

        if self._fail_page_start == page.start_index:
            raise RuntimeError("page write failed")

        return self._persist(
            object_key=object_key,
            payload=page.raw_bytes,
            version_id=(f"page-version-{page.start_index}"),
        )

    def create_manifest(
        self,
        *,
        manifest: NvdIncrementalManifest,
        payload: bytes,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Create or replay one exact COMPLETE manifest."""
        self._calls.append("manifest")
        self.manifests.append(manifest)
        self.manifest_payloads.append(payload)

        return self._persist(
            object_key=object_key,
            payload=payload,
            version_id=("manifest-version-123"),
        )

    def _persist(
        self,
        *,
        object_key: str,
        payload: bytes,
        version_id: str,
    ) -> NvdBronzeWriteResult:
        """Persist one exact immutable object or replay it."""
        existing = self.objects.get(object_key)

        if existing is not None:
            existing_payload, existing_version = existing

            if existing_payload != payload:
                raise AssertionError("Immutable fake object payload changed.")

            return NvdBronzeWriteResult(
                status=(NvdBronzeWriteStatus.ALREADY_EXISTS),
                version_id=existing_version,
            )

        self.objects[object_key] = (
            payload,
            version_id,
        )

        return NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.CREATED,
            version_id=version_id,
        )


def _use_case(
    *,
    source: FakeSource,
    repository: FakeRepository,
) -> IngestNvdIncrementalWindow:
    """Build the use case with real deterministic domain components."""
    return IngestNvdIncrementalWindow(
        source=source,
        repository=repository,
        page_parser=NvdCveApiPageParser(),
        key_factory=NvdIncrementalKeyFactory(),
        manifest_factory=(NvdIncrementalManifestFactory()),
        manifest_serializer=(NvdIncrementalManifestSerializer()),
        candidate_factory=(NvdWatermarkCandidateFactory()),
    )


def test_execute_validates_all_pages_before_any_bronze_write() -> None:
    """Fetch and validate the entire page sequence before persistence."""
    calls: list[str] = []

    source = FakeSource(
        payloads=_three_page_payloads(),
        calls=calls,
    )
    repository = FakeRepository(calls=calls)

    result = _use_case(
        source=source,
        repository=repository,
    ).execute(window=_window())

    assert calls == [
        "fetch:0",
        "fetch:2",
        "fetch:4",
        "page:0",
        "page:2",
        "page:4",
        "manifest",
    ]

    assert result.total_results == 5
    assert len(result.page_writes) == 3
    assert result.manifest_write.version_id == "manifest-version-123"


def test_pagination_inconsistency_prevents_all_bronze_writes() -> None:
    """Fail before persistence when totalResults changes mid-run."""
    calls: list[str] = []

    source = FakeSource(
        payloads={
            0: _payload(
                start_index=0,
                total_results=4,
                cve_ids=(
                    "CVE-2026-1000",
                    "CVE-2026-1001",
                ),
                timestamp=("2026-08-18T20:00:01.000"),
            ),
            2: _payload(
                start_index=2,
                total_results=5,
                cve_ids=(
                    "CVE-2026-1002",
                    "CVE-2026-1003",
                ),
                timestamp=("2026-08-18T20:00:07.000"),
            ),
        },
        calls=calls,
    )

    repository = FakeRepository(calls=calls)

    with pytest.raises(
        InvalidNvdCveApiPaginationError,
        match="totalResults changed",
    ):
        _use_case(
            source=source,
            repository=repository,
        ).execute(window=_window())

    assert calls == [
        "fetch:0",
        "fetch:2",
    ]
    assert repository.objects == {}


def test_cross_page_duplicate_prevents_all_bronze_writes() -> None:
    """Fail closed before persistence on duplicate CVE identity."""
    calls: list[str] = []

    source = FakeSource(
        payloads={
            0: _payload(
                start_index=0,
                total_results=4,
                cve_ids=(
                    "CVE-2026-1000",
                    "CVE-2026-1001",
                ),
                timestamp=("2026-08-18T20:00:01.000"),
            ),
            2: _payload(
                start_index=2,
                total_results=4,
                cve_ids=(
                    "CVE-2026-1001",
                    "CVE-2026-1002",
                ),
                timestamp=("2026-08-18T20:00:07.000"),
            ),
        },
        calls=calls,
    )

    repository = FakeRepository(calls=calls)

    with pytest.raises(
        InvalidNvdCveApiPaginationError,
        match="duplicate CVE identifiers",
    ):
        _use_case(
            source=source,
            repository=repository,
        ).execute(window=_window())

    assert calls == [
        "fetch:0",
        "fetch:2",
    ]
    assert repository.objects == {}


def test_response_start_index_mismatch_prevents_persistence() -> None:
    """Reject a response that does not match the requested offset."""
    calls: list[str] = []

    source = FakeSource(
        payloads={
            0: _payload(
                start_index=1,
                total_results=2,
                cve_ids=("CVE-2026-1001",),
                timestamp=("2026-08-18T20:00:01.000"),
            ),
        },
        calls=calls,
    )

    repository = FakeRepository(calls=calls)

    with pytest.raises(
        InvalidNvdCveApiPaginationError,
        match="requested page offset",
    ):
        _use_case(
            source=source,
            repository=repository,
        ).execute(window=_window())

    assert calls == ["fetch:0"]
    assert repository.objects == {}


def test_page_write_failure_prevents_complete_manifest() -> None:
    """Never publish COMPLETE after a partial page persistence failure."""
    calls: list[str] = []

    source = FakeSource(
        payloads=_three_page_payloads(),
        calls=calls,
    )
    repository = FakeRepository(
        calls=calls,
        fail_page_start=2,
    )

    with pytest.raises(
        RuntimeError,
        match="page write failed",
    ):
        _use_case(
            source=source,
            repository=repository,
        ).execute(window=_window())

    assert calls == [
        "fetch:0",
        "fetch:2",
        "fetch:4",
        "page:0",
        "page:2",
    ]
    assert repository.manifest_payloads == []


def test_replay_produces_same_logical_completion_evidence() -> None:
    """Replay one window without creating a new logical source identity."""
    calls: list[str] = []
    repository = FakeRepository(calls=calls)

    first = _use_case(
        source=FakeSource(
            payloads=_three_page_payloads(),
            calls=calls,
        ),
        repository=repository,
    ).execute(window=_window())

    replay = _use_case(
        source=FakeSource(
            payloads=_three_page_payloads(),
            calls=calls,
        ),
        repository=repository,
    ).execute(window=_window())

    assert first.update_id == replay.update_id
    assert first.page_keys == replay.page_keys
    assert first.manifest_key == replay.manifest_key

    assert all(write.status is NvdBronzeWriteStatus.CREATED for write in first.page_writes)
    assert all(write.status is NvdBronzeWriteStatus.ALREADY_EXISTS for write in replay.page_writes)

    assert first.manifest_write.status is NvdBronzeWriteStatus.CREATED
    assert replay.manifest_write.status is NvdBronzeWriteStatus.ALREADY_EXISTS

    assert len(repository.manifest_payloads) == 2
    assert repository.manifest_payloads[0] == repository.manifest_payloads[1]

    serializer = NvdWatermarkCandidateSerializer()

    assert serializer.serialize(first.candidate) == serializer.serialize(replay.candidate)


def test_result_candidate_is_contiguous_but_not_committed() -> None:
    """Expose a Bronze candidate without advancing authoritative state."""
    calls: list[str] = []

    result = _use_case(
        source=FakeSource(
            payloads=_three_page_payloads(),
            calls=calls,
        ),
        repository=FakeRepository(calls=calls),
    ).execute(window=_window())

    NvdWatermarkTransitionValidator().validate(
        committed_through_at=(_window().start_at),
        candidate=result.candidate,
    )

    assert result.candidate.STATE == "bronze_complete"
    assert result.candidate.window_end_at == _window().end_at


def test_zero_result_window_still_publishes_complete_evidence() -> None:
    """Persist an explicit empty response and COMPLETE manifest."""
    calls: list[str] = []

    source = FakeSource(
        payloads={
            0: _payload(
                start_index=0,
                total_results=0,
                cve_ids=(),
                timestamp=("2026-08-18T20:00:01.000"),
            ),
        },
        calls=calls,
    )
    repository = FakeRepository(calls=calls)

    result = _use_case(
        source=source,
        repository=repository,
    ).execute(window=_window())

    assert calls == [
        "fetch:0",
        "page:0",
        "manifest",
    ]
    assert result.total_results == 0
    assert len(result.page_writes) == 1
    assert result.candidate.total_results == 0
    assert result.candidate.page_count == 1
