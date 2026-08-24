"""Unit tests for replay-safe NVD incremental Bronze completion."""

import hashlib
import json
from datetime import UTC, datetime

from opslens.ingestion.nvd.application.incremental_attempt import (
    NvdIncrementalAttemptIdFactory,
)
from opslens.ingestion.nvd.application.incremental_complete import (
    NvdIncrementalCanonicalManifestAlreadyExistsError,
    NvdPersistedIncrementalManifest,
)
from opslens.ingestion.nvd.application.incremental_key_factory import (
    NvdIncrementalKeyFactory,
)
from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifest,
    NvdIncrementalManifestFactory,
    NvdIncrementalManifestSerializer,
    NvdIncrementalStoredPage,
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
)
from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPage,
    NvdCveApiPageParser,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


def _window() -> NvdIncrementalWindow:
    """Build the AWS replay-proof logical window."""
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


def _zero_payload(
    *,
    timestamp: str,
) -> bytes:
    """Build one exact zero-result NVD response."""
    return json.dumps(
        {
            "resultsPerPage": 0,
            "startIndex": 0,
            "totalResults": 0,
            "format": "NVD_CVE",
            "version": "2.0",
            "timestamp": timestamp,
            "vulnerabilities": [],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


class FakeSource:
    """Return one deterministic physical observation."""

    def __init__(
        self,
        *,
        payload: bytes,
    ) -> None:
        """Initialize the source response."""
        self._payload = payload
        self.calls = 0

    def fetch_page(
        self,
        *,
        window: NvdIncrementalWindow,
        start_index: int,
    ) -> bytes:
        """Return the single expected source page."""
        assert window == _window()
        assert start_index == 0

        self.calls += 1

        return self._payload


class FakeRepository:
    """Capture attempt pages and optionally simulate a canonical winner."""

    def __init__(
        self,
        *,
        canonical_collision: bool,
    ) -> None:
        """Initialize persistence behavior."""
        self._canonical_collision = canonical_collision
        self.page_keys: list[str] = []
        self.manifest: NvdIncrementalManifest | None = None
        self.manifest_payload: bytes | None = None
        self.manifest_key: str | None = None

    def create_page(
        self,
        *,
        page: NvdCveApiPage,
        window: NvdIncrementalWindow,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Persist one physical-attempt page."""
        assert window == _window()

        self.page_keys.append(
            object_key
        )

        return NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.CREATED,
            version_id="loser-attempt-page-version",
        )

    def create_manifest(
        self,
        *,
        manifest: NvdIncrementalManifest,
        payload: bytes,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Create canonical COMPLETE or simulate another winner."""
        self.manifest = manifest
        self.manifest_payload = payload
        self.manifest_key = object_key

        if self._canonical_collision:
            raise NvdIncrementalCanonicalManifestAlreadyExistsError(
                "Canonical NVD incremental COMPLETE manifest already exists."
            )

        return NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.CREATED,
            version_id="created-manifest-version",
            etag='"created-manifest-etag"',
        )


class FakeCompleteReader:
    """Return one exact persisted canonical winner."""

    def __init__(
        self,
        *,
        persisted: NvdPersistedIncrementalManifest | None = None,
    ) -> None:
        """Initialize optional canonical winner evidence."""
        self._persisted = persisted
        self.calls: list[tuple[NvdIncrementalWindow, str]] = []

    def load_existing(
        self,
        *,
        window: NvdIncrementalWindow,
        object_key: str,
    ) -> NvdPersistedIncrementalManifest:
        """Return known-existing canonical COMPLETE evidence."""
        self.calls.append(
            (
                window,
                object_key,
            )
        )

        if self._persisted is None:
            raise AssertionError(
                "Canonical COMPLETE reader was not expected."
            )

        return self._persisted


def _winner() -> NvdPersistedIncrementalManifest:
    """Build legacy-layout COMPLETE evidence representing the AWS winner."""
    window = _window()

    manifest = NvdIncrementalManifest(
        update_id=window.update_id,
        window_start_at=window.start_at,
        window_end_at=window.end_at,
        total_results=1,
        pages=(
            NvdIncrementalStoredPage(
                key=(
                    "bronze/nvd/cve/updates/"
                    f"update_id={window.update_id}/"
                    "page_start=000000/"
                    "response.json"
                ),
                version_id="winner-page-version",
                size_bytes=256,
                sha256="c" * 64,
                start_index=0,
                results_per_page=1,
                total_results=1,
                source_timestamp="2026-08-24T19:51:57.077",
            ),
        ),
    )

    payload = NvdIncrementalManifestSerializer().serialize(
        manifest
    )

    sha256 = hashlib.sha256(
        payload
    ).hexdigest()

    return NvdPersistedIncrementalManifest(
        manifest=manifest,
        payload=payload,
        version_id="winner-manifest-version",
        etag='"winner-manifest-etag"',
        sha256=sha256,
        size_bytes=len(
            payload
        ),
    )


def _use_case(
    *,
    source: FakeSource,
    repository: FakeRepository,
    complete_reader: FakeCompleteReader,
) -> IngestNvdIncrementalWindow:
    """Build the replay-safe application service."""
    return IngestNvdIncrementalWindow(
        source=source,
        repository=repository,
        complete_reader=complete_reader,
        page_parser=NvdCveApiPageParser(),
        attempt_id_factory=NvdIncrementalAttemptIdFactory(),
        key_factory=NvdIncrementalKeyFactory(),
        manifest_factory=NvdIncrementalManifestFactory(),
        manifest_serializer=NvdIncrementalManifestSerializer(),
        candidate_factory=NvdWatermarkCandidateFactory(),
    )


def test_new_complete_uses_attempt_scoped_page_keys() -> None:
    """Persist new physical pages below attempt identity."""
    source = FakeSource(
        payload=_zero_payload(
            timestamp="2026-08-24T20:00:00.000",
        )
    )
    repository = FakeRepository(
        canonical_collision=False
    )
    reader = FakeCompleteReader()

    result = _use_case(
        source=source,
        repository=repository,
        complete_reader=reader,
    ).execute(
        window=_window()
    )

    assert source.calls == 1
    assert len(repository.page_keys) == 1
    assert "/attempt_id=" in repository.page_keys[0]

    assert repository.manifest is not None
    assert repository.manifest.pages[0].key == repository.page_keys[0]

    assert result.page_keys == tuple(
        repository.page_keys
    )
    assert result.manifest_write.status is NvdBronzeWriteStatus.CREATED
    assert reader.calls == []


def test_manifest_collision_returns_canonical_winner_evidence() -> None:
    """Discard losing-attempt evidence from the externally visible result."""
    window = _window()
    winner = _winner()

    source = FakeSource(
        payload=_zero_payload(
            timestamp="2026-08-24T20:05:00.000",
        )
    )
    repository = FakeRepository(
        canonical_collision=True
    )
    reader = FakeCompleteReader(
        persisted=winner
    )

    result = _use_case(
        source=source,
        repository=repository,
        complete_reader=reader,
    ).execute(
        window=window
    )

    manifest_key = NvdIncrementalKeyFactory().build_manifest_key(
        window=window
    )

    assert source.calls == 1

    assert len(repository.page_keys) == 1
    assert "/attempt_id=" in repository.page_keys[0]

    assert reader.calls == [
        (
            window,
            manifest_key,
        )
    ]

    assert result.total_results == 1

    assert result.page_keys == (
        winner.manifest.pages[0].key,
    )

    assert result.page_keys[0] != repository.page_keys[0]

    assert (
        result.page_writes[0].status
        is NvdBronzeWriteStatus.ALREADY_EXISTS
    )
    assert result.page_writes[0].version_id == "winner-page-version"

    assert (
        result.manifest_write.status
        is NvdBronzeWriteStatus.ALREADY_EXISTS
    )
    assert result.manifest_write.version_id == "winner-manifest-version"
    assert result.manifest_write.etag == '"winner-manifest-etag"'

    assert (
        result.candidate.bronze_manifest_version_id
        == "winner-manifest-version"
    )
    assert (
        result.candidate.bronze_manifest_sha256
        == winner.sha256
    )
    assert result.candidate.total_results == 1
    assert result.candidate.page_count == 1


def test_changed_source_bytes_produce_different_attempt_page_keys() -> None:
    """Keep repeated physical observations isolated under one logical update."""
    first_repository = FakeRepository(
        canonical_collision=False
    )
    second_repository = FakeRepository(
        canonical_collision=False
    )

    _use_case(
        source=FakeSource(
            payload=_zero_payload(
                timestamp="2026-08-24T19:51:57.077",
            )
        ),
        repository=first_repository,
        complete_reader=FakeCompleteReader(),
    ).execute(
        window=_window()
    )

    _use_case(
        source=FakeSource(
            payload=_zero_payload(
                timestamp="2026-08-24T19:55:28.855",
            )
        ),
        repository=second_repository,
        complete_reader=FakeCompleteReader(),
    ).execute(
        window=_window()
    )

    assert first_repository.page_keys[0] != second_repository.page_keys[0]

    common_prefix = (
        "bronze/nvd/cve/updates/"
        f"update_id={_window().update_id}/"
    )

    assert first_repository.page_keys[0].startswith(
        common_prefix
    )
    assert second_repository.page_keys[0].startswith(
        common_prefix
    )
