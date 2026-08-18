"""Unit tests for the NVD Bootstrap Bronze completion manifest."""

import gzip
import hashlib
import json
from datetime import UTC, datetime
from typing import cast

import pytest

from opslens.ingestion.nvd.application.key_factory import (
    NvdBootstrapKeyFactory,
    NvdBootstrapObjectKeys,
)
from opslens.ingestion.nvd.application.manifest import (
    NvdBootstrapManifest,
    NvdBootstrapManifestFactory,
    NvdBootstrapManifestSerializer,
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


def _build_source() -> tuple[
    NvdFeedArtifact,
    NvdBootstrapSourceIdentity,
    NvdBootstrapObjectKeys,
]:
    """Build verified source evidence for manifest tests."""
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

    meta = NvdFeedMetaParser().parse(meta_payload)

    artifact = NvdFeedIntegrityVerifier().verify(
        payload=gzip_payload,
        meta=meta,
    )

    identity = NvdBootstrapSourceIdentity(
        feed_year=2026,
        meta=meta,
    )

    keys = NvdBootstrapKeyFactory().build(identity)

    return artifact, identity, keys


def _manifest() -> NvdBootstrapManifest:
    """Build a valid COMPLETE manifest."""
    artifact, identity, keys = _build_source()

    return NvdBootstrapManifestFactory().build(
        artifact=artifact,
        identity=identity,
        keys=keys,
        feed_version_id="feed-version-123",
        meta_version_id="meta-version-456",
        retrieved_at=datetime(
            2026,
            8,
            18,
            22,
            0,
            tzinfo=UTC,
        ),
    )


def test_manifest_preserves_exact_s3_version_ids() -> None:
    """Preserve exact S3 object versions as completion evidence."""
    manifest = _manifest()

    assert manifest.feed_object.version_id == ("feed-version-123")
    assert manifest.meta_object.version_id == ("meta-version-456")


def test_manifest_preserves_exact_stored_object_hashes() -> None:
    """Preserve hashes of both exact Bronze source objects."""
    artifact, identity, keys = _build_source()

    manifest = NvdBootstrapManifestFactory().build(
        artifact=artifact,
        identity=identity,
        keys=keys,
        feed_version_id="feed-version",
        meta_version_id="meta-version",
        retrieved_at=datetime.now(UTC),
    )

    assert manifest.feed_object.sha256 == (artifact.bronze_object_sha256)
    assert manifest.meta_object.sha256 == hashlib.sha256(identity.meta.raw_bytes).hexdigest()


def test_manifest_preserves_source_sha256_separately() -> None:
    """Keep NVD source integrity separate from Bronze object integrity."""
    artifact, identity, keys = _build_source()

    manifest = NvdBootstrapManifestFactory().build(
        artifact=artifact,
        identity=identity,
        keys=keys,
        feed_version_id="feed-version",
        meta_version_id="meta-version",
        retrieved_at=datetime.now(UTC),
    )

    assert manifest.source_sha256 == (identity.meta.source_sha256)
    assert manifest.source_sha256 != (manifest.feed_object.sha256)


def test_manifest_serializer_is_deterministic() -> None:
    """Produce exactly the same bytes for identical manifest evidence."""
    manifest = _manifest()
    serializer = NvdBootstrapManifestSerializer()

    assert serializer.serialize(manifest) == (serializer.serialize(manifest))


def test_manifest_serializer_marks_complete_evidence() -> None:
    """Serialize the manifest explicitly as COMPLETE evidence."""
    serialized = NvdBootstrapManifestSerializer().serialize(_manifest())

    document = cast(
        dict[str, object],
        json.loads(serialized),
    )

    assert document["completion_status"] == "complete"
    assert document["manifest_version"] == "1"
    assert document["source"] == "nvd-cve"
    assert document["source_interface"] == ("json-2.0-yearly-feed")


def test_manifest_serializer_normalizes_timestamps_to_utc() -> None:
    """Serialize source and retrieval timestamps in canonical UTC."""
    serialized = NvdBootstrapManifestSerializer().serialize(_manifest())

    document = cast(
        dict[str, object],
        json.loads(serialized),
    )

    assert document["source_last_modified_at"] == ("2026-08-18T07:00:12Z")
    assert document["retrieved_at"] == ("2026-08-18T22:00:00Z")


def test_manifest_rejects_artifact_identity_mismatch() -> None:
    """Reject completion evidence assembled from different META sources."""
    artifact, _, keys = _build_source()

    different_meta_payload = (
        "lastModifiedDate:2026-08-19T03:00:12-04:00\n"
        f"size:{len(JSON_PAYLOAD)}\n"
        "zipSize:1\n"
        f"gzSize:{artifact.gzip_size_bytes}\n"
        f"sha256:{artifact.meta.source_sha256}\n"
    ).encode()

    different_identity = NvdBootstrapSourceIdentity(
        feed_year=2026,
        meta=NvdFeedMetaParser().parse(different_meta_payload),
    )

    with pytest.raises(
        ValueError,
        match="does not match source identity",
    ):
        NvdBootstrapManifestFactory().build(
            artifact=artifact,
            identity=different_identity,
            keys=keys,
            feed_version_id="feed-version",
            meta_version_id="meta-version",
            retrieved_at=datetime.now(UTC),
        )


def test_manifest_rejects_missing_feed_version_id() -> None:
    """Require the exact S3 feed VersionId before completion."""
    artifact, identity, keys = _build_source()

    with pytest.raises(
        ValueError,
        match="VersionId cannot be empty",
    ):
        NvdBootstrapManifestFactory().build(
            artifact=artifact,
            identity=identity,
            keys=keys,
            feed_version_id="",
            meta_version_id="meta-version",
            retrieved_at=datetime.now(UTC),
        )


def test_manifest_rejects_missing_meta_version_id() -> None:
    """Require the exact S3 META VersionId before completion."""
    artifact, identity, keys = _build_source()

    with pytest.raises(
        ValueError,
        match="VersionId cannot be empty",
    ):
        NvdBootstrapManifestFactory().build(
            artifact=artifact,
            identity=identity,
            keys=keys,
            feed_version_id="feed-version",
            meta_version_id="",
            retrieved_at=datetime.now(UTC),
        )


def test_manifest_rejects_naive_retrieval_timestamp() -> None:
    """Reject completion evidence without timezone-aware retrieval time."""
    artifact, identity, keys = _build_source()

    with pytest.raises(
        ValueError,
        match="retrieved_at must be timezone-aware",
    ):
        NvdBootstrapManifestFactory().build(
            artifact=artifact,
            identity=identity,
            keys=keys,
            feed_version_id="feed-version",
            meta_version_id="meta-version",
            retrieved_at=datetime(  # noqa: DTZ001 - intentionally naive for validation test
                2026,
                8,
                18,
                22,
                0,
            ),
        )
