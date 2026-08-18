"""Unit tests for NVD Bootstrap Bronze application orchestration."""

import gzip
import hashlib

import pytest

from opslens.ingestion.nvd.application.key_factory import (
    NvdBootstrapKeyFactory,
)
from opslens.ingestion.nvd.application.manifest import (
    NvdBootstrapManifest,
    NvdBootstrapManifestFactory,
    NvdBootstrapManifestSerializer,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
    NvdBronzeWriteStatus,
)
from opslens.ingestion.nvd.application.service import (
    IngestNvdBootstrapFeed,
)
from opslens.ingestion.nvd.domain.feed_artifact import NvdFeedArtifact
from opslens.ingestion.nvd.domain.feed_integrity import (
    NvdFeedIntegrityVerifier,
)
from opslens.ingestion.nvd.domain.meta_parser import NvdFeedMetaParser
from opslens.ingestion.nvd.domain.source_identity import (
    NvdBootstrapSourceIdentity,
)

JSON_PAYLOAD = b'{"format":"NVD_CVE","version":"2.0"}'


def _source_payloads() -> tuple[bytes, bytes]:
    """Build deterministic matching META and gzip source artifacts."""
    gzip_payload = gzip.compress(
        JSON_PAYLOAD,
        mtime=0,
    )

    source_sha256 = hashlib.sha256(JSON_PAYLOAD).hexdigest()

    meta_payload = (
        "lastModifiedDate:2026-08-18T03:00:12-04:00\n"
        f"size:{len(JSON_PAYLOAD)}\n"
        "zipSize:1\n"
        f"gzSize:{len(gzip_payload)}\n"
        f"sha256:{source_sha256}\n"
    ).encode()

    return meta_payload, gzip_payload


class FakeSource:
    """Return deterministic NVD artifacts while recording call order."""

    def __init__(
        self,
        *,
        meta_payload: bytes,
        gzip_payload: bytes,
        calls: list[str],
    ) -> None:
        """Initialize deterministic source data."""
        self._meta_payload = meta_payload
        self._gzip_payload = gzip_payload
        self._calls = calls

    def fetch_meta(self, feed_year: int) -> bytes:
        """Return META bytes and record source ordering."""
        self._calls.append("fetch_meta")
        return self._meta_payload

    def fetch_gzip(self, feed_year: int) -> bytes:
        """Return gzip bytes and record source ordering."""
        self._calls.append("fetch_gzip")
        return self._gzip_payload


class FakeRepository:
    """Capture Bronze writes and enforce deterministic test outcomes."""

    def __init__(
        self,
        *,
        calls: list[str],
        fail_on: str | None = None,
    ) -> None:
        """Initialize repository behavior."""
        self._calls = calls
        self._fail_on = fail_on
        self.manifest: NvdBootstrapManifest | None = None
        self.manifest_payload: bytes | None = None

    def create_feed(
        self,
        *,
        artifact: NvdFeedArtifact,
        identity: NvdBootstrapSourceIdentity,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Capture the feed write."""
        self._calls.append("create_feed")

        if self._fail_on == "feed":
            raise RuntimeError("feed write failed")

        return NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.CREATED,
            version_id="feed-version-123",
        )

    def create_meta(
        self,
        *,
        identity: NvdBootstrapSourceIdentity,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Capture the META write."""
        self._calls.append("create_meta")

        if self._fail_on == "meta":
            raise RuntimeError("meta write failed")

        return NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.CREATED,
            version_id="meta-version-456",
        )

    def create_manifest(
        self,
        *,
        manifest: NvdBootstrapManifest,
        payload: bytes,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Capture the completion-manifest write."""
        self._calls.append("create_manifest")
        self.manifest = manifest
        self.manifest_payload = payload

        if self._fail_on == "manifest":
            raise RuntimeError("manifest write failed")

        return NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.CREATED,
            version_id="manifest-version-789",
        )


def _use_case(
    *,
    repository: FakeRepository,
    source: FakeSource,
) -> IngestNvdBootstrapFeed:
    """Build the application service with real deterministic domain logic."""
    return IngestNvdBootstrapFeed(
        source=source,
        repository=repository,
        meta_parser=NvdFeedMetaParser(),
        integrity_verifier=NvdFeedIntegrityVerifier(),
        key_factory=NvdBootstrapKeyFactory(),
        manifest_factory=NvdBootstrapManifestFactory(),
        manifest_serializer=NvdBootstrapManifestSerializer(),
    )


def test_execute_enforces_complete_bootstrap_order() -> None:
    """Fetch META first and publish the completion manifest last."""
    calls: list[str] = []
    meta_payload, gzip_payload = _source_payloads()

    source = FakeSource(
        meta_payload=meta_payload,
        gzip_payload=gzip_payload,
        calls=calls,
    )
    repository = FakeRepository(calls=calls)

    result = _use_case(
        repository=repository,
        source=source,
    ).execute(feed_year=2026)

    assert calls == [
        "fetch_meta",
        "fetch_gzip",
        "create_feed",
        "create_meta",
        "create_manifest",
    ]

    assert result.feed_write.version_id == "feed-version-123"
    assert result.meta_write.version_id == "meta-version-456"
    assert result.manifest_write.version_id == ("manifest-version-789")


def test_manifest_uses_exact_source_object_version_ids() -> None:
    """Bind COMPLETE evidence to exact persisted source-object versions."""
    calls: list[str] = []
    meta_payload, gzip_payload = _source_payloads()

    source = FakeSource(
        meta_payload=meta_payload,
        gzip_payload=gzip_payload,
        calls=calls,
    )
    repository = FakeRepository(calls=calls)

    _use_case(
        repository=repository,
        source=source,
    ).execute(feed_year=2026)

    assert repository.manifest is not None
    assert repository.manifest.feed_object.version_id == ("feed-version-123")
    assert repository.manifest.meta_object.version_id == ("meta-version-456")


def test_feed_failure_prevents_meta_and_manifest_writes() -> None:
    """Never publish later evidence after a feed persistence failure."""
    calls: list[str] = []
    meta_payload, gzip_payload = _source_payloads()

    source = FakeSource(
        meta_payload=meta_payload,
        gzip_payload=gzip_payload,
        calls=calls,
    )
    repository = FakeRepository(
        calls=calls,
        fail_on="feed",
    )

    with pytest.raises(
        RuntimeError,
        match="feed write failed",
    ):
        _use_case(
            repository=repository,
            source=source,
        ).execute(feed_year=2026)

    assert calls == [
        "fetch_meta",
        "fetch_gzip",
        "create_feed",
    ]


def test_meta_failure_prevents_manifest_write() -> None:
    """Never publish COMPLETE evidence after a META persistence failure."""
    calls: list[str] = []
    meta_payload, gzip_payload = _source_payloads()

    source = FakeSource(
        meta_payload=meta_payload,
        gzip_payload=gzip_payload,
        calls=calls,
    )
    repository = FakeRepository(
        calls=calls,
        fail_on="meta",
    )

    with pytest.raises(
        RuntimeError,
        match="meta write failed",
    ):
        _use_case(
            repository=repository,
            source=source,
        ).execute(feed_year=2026)

    assert calls == [
        "fetch_meta",
        "fetch_gzip",
        "create_feed",
        "create_meta",
    ]


def test_invalid_year_fails_before_source_access() -> None:
    """Reject invalid input before contacting NVD."""
    calls: list[str] = []
    meta_payload, gzip_payload = _source_payloads()

    source = FakeSource(
        meta_payload=meta_payload,
        gzip_payload=gzip_payload,
        calls=calls,
    )
    repository = FakeRepository(calls=calls)

    with pytest.raises(
        ValueError,
        match="exactly four digits",
    ):
        _use_case(
            repository=repository,
            source=source,
        ).execute(feed_year=999)

    assert calls == []


def test_result_exposes_deterministic_revision_and_keys() -> None:
    """Expose the exact source identity completed by the bootstrap."""
    calls: list[str] = []
    meta_payload, gzip_payload = _source_payloads()

    source = FakeSource(
        meta_payload=meta_payload,
        gzip_payload=gzip_payload,
        calls=calls,
    )
    repository = FakeRepository(calls=calls)

    result = _use_case(
        repository=repository,
        source=source,
    ).execute(feed_year=2026)

    assert result.feed_revision.startswith("20260818T070012Z-")
    assert result.feed_key.endswith("/nvdcve-2.0-2026.json.gz")
    assert result.meta_key.endswith("/nvdcve-2.0-2026.meta")
    assert result.manifest_key.endswith("/manifest.json")


def test_integrity_failure_prevents_all_bronze_writes() -> None:
    """Fail closed before persistence when gzip and META do not agree."""
    calls: list[str] = []
    meta_payload, _ = _source_payloads()

    mismatched_gzip = gzip.compress(
        b'{"different":true}',
        mtime=0,
    )

    source = FakeSource(
        meta_payload=meta_payload,
        gzip_payload=mismatched_gzip,
        calls=calls,
    )
    repository = FakeRepository(calls=calls)

    with pytest.raises(ValueError):
        _use_case(
            repository=repository,
            source=source,
        ).execute(feed_year=2026)

    assert calls == [
        "fetch_meta",
        "fetch_gzip",
    ]
