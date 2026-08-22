"""Tests for exact NVD Bronze evidence verification."""

import json
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)
from opslens.transformation.nvd.provenance.errors import (
    InvalidNvdBronzeEvidenceError,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectPayloadV1,
    NvdBronzeObjectRole,
)
from opslens.transformation.nvd.provenance.verifier import (
    NvdBronzeEvidenceVerifierV1,
    NvdSilverProvenanceFactoryV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)


def _canonical(document: dict[str, object]) -> bytes:
    """Serialize one Bronze manifest exactly like the producer."""
    text = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )

    return f"{text}\n".encode()


def _incremental_fixture() -> tuple[
    str,
    bytes,
    tuple[NvdBronzeObjectPayloadV1, ...],
]:
    """Build one canonical one-page incremental COMPLETE fixture."""
    window = NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            20,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            21,
            tzinfo=UTC,
        ),
    )

    update_id = window.update_id

    manifest_key = f"bronze/nvd/cve/updates/update_id={update_id}/manifest.json"

    page_key = f"bronze/nvd/cve/updates/update_id={update_id}/page_start=000000/response.json"

    page_bytes = b'{"resultsPerPage":1,"totalResults":1}\n'

    document: dict[str, object] = {
        "completion_status": "complete",
        "manifest_version": "1",
        "page_count": 1,
        "pages": [
            {
                "key": page_key,
                "results_per_page": 1,
                "sha256": sha256(page_bytes).hexdigest(),
                "size_bytes": len(page_bytes),
                "source_timestamp": ("2026-08-21T12:00:00.000"),
                "start_index": 0,
                "total_results": 1,
                "version_id": "page-version-1",
            }
        ],
        "source": "nvd-cve",
        "source_format": "NVD_CVE",
        "source_interface": "cve-api-2.0",
        "source_version": "2.0",
        "total_results": 1,
        "update_id": update_id,
        "window_end_at": window.canonical_end_at,
        "window_start_at": window.canonical_start_at,
    }

    payloads = (
        NvdBronzeObjectPayloadV1(
            key=page_key,
            version_id="page-version-1",
            raw_bytes=page_bytes,
        ),
    )

    return (
        manifest_key,
        _canonical(document),
        payloads,
    )


def _bootstrap_fixture() -> tuple[
    str,
    bytes,
    tuple[NvdBronzeObjectPayloadV1, ...],
]:
    """Build one canonical bootstrap COMPLETE fixture."""
    year = 2026
    revision = "revision-abc"

    base = f"bronze/nvd/cve/bootstrap/feed_year={year}/feed_revision={revision}"

    manifest_key = f"{base}/manifest.json"

    feed_key = f"{base}/nvdcve-2.0-{year}.json.gz"
    meta_key = f"{base}/nvdcve-2.0-{year}.meta"

    feed_bytes = b"exact-gzip-source-bytes"
    meta_bytes = b"lastModifiedDate:2026-08-21T00:00:00Z\n"

    document: dict[str, object] = {
        "completion_status": "complete",
        "feed_object": {
            "key": feed_key,
            "sha256": sha256(feed_bytes).hexdigest(),
            "size_bytes": len(feed_bytes),
            "version_id": "feed-version-1",
        },
        "feed_revision": revision,
        "feed_year": year,
        "gzip_size_bytes": len(feed_bytes),
        "manifest_version": "1",
        "meta_object": {
            "key": meta_key,
            "sha256": sha256(meta_bytes).hexdigest(),
            "size_bytes": len(meta_bytes),
            "version_id": "meta-version-1",
        },
        "source": "nvd-cve",
        "source_interface": "json-2.0-yearly-feed",
        "source_last_modified_at": ("2026-08-21T00:00:00Z"),
        "source_sha256": "a" * 64,
        "uncompressed_size_bytes": 100,
        "zip_size_bytes": 50,
    }

    payloads = (
        NvdBronzeObjectPayloadV1(
            key=feed_key,
            version_id="feed-version-1",
            raw_bytes=feed_bytes,
        ),
        NvdBronzeObjectPayloadV1(
            key=meta_key,
            version_id="meta-version-1",
            raw_bytes=meta_bytes,
        ),
    )

    return (
        manifest_key,
        _canonical(document),
        payloads,
    )


def test_incremental_exact_evidence_verifies() -> None:
    """Verify manifest identity and every exact incremental object."""
    manifest_key, manifest_bytes, payloads = _incremental_fixture()

    evidence = NvdBronzeEvidenceVerifierV1().verify_incremental(
        manifest_key=manifest_key,
        manifest_version_id="manifest-version-1",
        manifest_bytes=manifest_bytes,
        object_payloads=payloads,
    )

    assert evidence.source_kind is NvdSilverSourceKind.INCREMENTAL
    assert evidence.manifest_sha256 == sha256(manifest_bytes).hexdigest()
    assert len(evidence.objects) == 1
    assert evidence.objects[0].role is NvdBronzeObjectRole.PAGE


def test_noncanonical_incremental_manifest_fails_closed() -> None:
    """Reject semantically equal manifest bytes with noncanonical encoding."""
    manifest_key, manifest_bytes, payloads = _incremental_fixture()

    document = json.loads(manifest_bytes)

    noncanonical = json.dumps(
        document,
        indent=2,
    ).encode("utf-8")

    with pytest.raises(
        InvalidNvdBronzeEvidenceError,
        match="canonical",
    ):
        NvdBronzeEvidenceVerifierV1().verify_incremental(
            manifest_key=manifest_key,
            manifest_version_id="manifest-version-1",
            manifest_bytes=noncanonical,
            object_payloads=payloads,
        )


def test_incremental_update_id_must_match_window() -> None:
    """Reject a manifest whose batch ID is detached from its window."""
    manifest_key, manifest_bytes, payloads = _incremental_fixture()

    document = json.loads(manifest_bytes)
    document["update_id"] = "0" * 64

    invalid = _canonical(document)

    with pytest.raises(
        InvalidNvdBronzeEvidenceError,
        match="window identity",
    ):
        NvdBronzeEvidenceVerifierV1().verify_incremental(
            manifest_key=manifest_key,
            manifest_version_id="manifest-version-1",
            manifest_bytes=invalid,
            object_payloads=payloads,
        )


def test_missing_expected_page_fails_closed() -> None:
    """Require every manifest page to be supplied and verified."""
    manifest_key, manifest_bytes, _ = _incremental_fixture()

    with pytest.raises(
        InvalidNvdBronzeEvidenceError,
        match="incomplete",
    ):
        NvdBronzeEvidenceVerifierV1().verify_incremental(
            manifest_key=manifest_key,
            manifest_version_id="manifest-version-1",
            manifest_bytes=manifest_bytes,
            object_payloads=(),
        )


def test_unexpected_object_fails_closed() -> None:
    """Do not accept objects outside the COMPLETE manifest inventory."""
    manifest_key, manifest_bytes, payloads = _incremental_fixture()

    unexpected = NvdBronzeObjectPayloadV1(
        key="bronze/nvd/cve/unexpected.json",
        version_id="unexpected-version",
        raw_bytes=b"unexpected",
    )

    with pytest.raises(
        InvalidNvdBronzeEvidenceError,
        match="unexpected",
    ):
        NvdBronzeEvidenceVerifierV1().verify_incremental(
            manifest_key=manifest_key,
            manifest_version_id="manifest-version-1",
            manifest_bytes=manifest_bytes,
            object_payloads=(*payloads, unexpected),
        )


def test_object_version_mismatch_fails_closed() -> None:
    """Require the exact VersionId referenced by the manifest."""
    manifest_key, manifest_bytes, payloads = _incremental_fixture()

    original = payloads[0]

    changed = (
        NvdBronzeObjectPayloadV1(
            key=original.key,
            version_id="different-version",
            raw_bytes=original.raw_bytes,
        ),
    )

    with pytest.raises(
        InvalidNvdBronzeEvidenceError,
        match="VersionId mismatch",
    ):
        NvdBronzeEvidenceVerifierV1().verify_incremental(
            manifest_key=manifest_key,
            manifest_version_id="manifest-version-1",
            manifest_bytes=manifest_bytes,
            object_payloads=changed,
        )


def test_object_hash_mismatch_fails_closed() -> None:
    """Recompute the hash from exact object bytes."""
    manifest_key, manifest_bytes, payloads = _incremental_fixture()

    original = payloads[0]

    changed = (
        NvdBronzeObjectPayloadV1(
            key=original.key,
            version_id=original.version_id,
            raw_bytes=b"same-size-is-not-required-here",
        ),
    )

    with pytest.raises(
        InvalidNvdBronzeEvidenceError,
        match=r"size mismatch|SHA-256 mismatch",
    ):
        NvdBronzeEvidenceVerifierV1().verify_incremental(
            manifest_key=manifest_key,
            manifest_version_id="manifest-version-1",
            manifest_bytes=manifest_bytes,
            object_payloads=changed,
        )


def test_bootstrap_exact_feed_and_meta_verify() -> None:
    """Verify both exact objects required by Bootstrap COMPLETE."""
    manifest_key, manifest_bytes, payloads = _bootstrap_fixture()

    evidence = NvdBronzeEvidenceVerifierV1().verify_bootstrap(
        manifest_key=manifest_key,
        manifest_version_id="manifest-version-1",
        manifest_bytes=manifest_bytes,
        object_payloads=payloads,
    )

    assert evidence.source_kind is NvdSilverSourceKind.BOOTSTRAP
    assert evidence.bootstrap_feed_year == 2026
    assert len(evidence.objects) == 2
    assert evidence.objects[0].role is NvdBronzeObjectRole.FEED
    assert evidence.objects[1].role is NvdBronzeObjectRole.META


def test_bootstrap_manifest_key_is_bound_to_feed_identity() -> None:
    """Reject an exact manifest loaded through the wrong batch key."""
    _, manifest_bytes, payloads = _bootstrap_fixture()

    with pytest.raises(
        InvalidNvdBronzeEvidenceError,
        match="manifest key",
    ):
        NvdBronzeEvidenceVerifierV1().verify_bootstrap(
            manifest_key="bronze/nvd/cve/bootstrap/wrong/manifest.json",
            manifest_version_id="manifest-version-1",
            manifest_bytes=manifest_bytes,
            object_payloads=payloads,
        )


def test_observation_id_is_deterministic_and_record_scoped() -> None:
    """Bind occurrence identity to exact evidence and record position."""
    manifest_key, manifest_bytes, payloads = _incremental_fixture()

    evidence = NvdBronzeEvidenceVerifierV1().verify_incremental(
        manifest_key=manifest_key,
        manifest_version_id="manifest-version-1",
        manifest_bytes=manifest_bytes,
        object_payloads=payloads,
    )

    reference = evidence.objects[0]
    factory = NvdSilverProvenanceFactoryV1()

    first = factory.build_observation_id(
        evidence=evidence,
        reference=reference,
        record_index=0,
    )
    replay = factory.build_observation_id(
        evidence=evidence,
        reference=reference,
        record_index=0,
    )
    next_record = factory.build_observation_id(
        evidence=evidence,
        reference=reference,
        record_index=1,
    )

    assert first == replay
    assert first != next_record
    assert len(first) == 64


def test_incremental_provenance_binds_exact_page() -> None:
    """Create Silver provenance only from a verified page reference."""
    manifest_key, manifest_bytes, payloads = _incremental_fixture()

    evidence = NvdBronzeEvidenceVerifierV1().verify_incremental(
        manifest_key=manifest_key,
        manifest_version_id="manifest-version-1",
        manifest_bytes=manifest_bytes,
        object_payloads=payloads,
    )

    provenance = NvdSilverProvenanceFactoryV1().build(
        evidence=evidence,
        bronze_object_key=evidence.objects[0].key,
        record_index=3,
    )

    assert provenance.observation_id
    assert provenance.bronze_manifest_sha256 == (evidence.manifest_sha256)
    assert provenance.bronze_object_sha256 == (evidence.objects[0].sha256)
    assert provenance.bronze_record_index == 3
    assert provenance.incremental_page_start == 0
    assert provenance.source_observed_at == datetime(
        2026,
        8,
        21,
        12,
        0,
        tzinfo=UTC,
    )


def test_bootstrap_provenance_binds_only_feed_object() -> None:
    """Prevent META evidence from being used as a CVE record source."""
    manifest_key, manifest_bytes, payloads = _bootstrap_fixture()

    evidence = NvdBronzeEvidenceVerifierV1().verify_bootstrap(
        manifest_key=manifest_key,
        manifest_version_id="manifest-version-1",
        manifest_bytes=manifest_bytes,
        object_payloads=payloads,
    )

    meta = evidence.objects[1]

    with pytest.raises(
        InvalidNvdBronzeEvidenceError,
        match="feed object",
    ):
        NvdSilverProvenanceFactoryV1().build(
            evidence=evidence,
            bronze_object_key=meta.key,
            record_index=0,
        )


def test_bootstrap_provenance_uses_exact_feed_and_source_time() -> None:
    """Bind Bootstrap row provenance to the verified feed revision."""
    manifest_key, manifest_bytes, payloads = _bootstrap_fixture()

    evidence = NvdBronzeEvidenceVerifierV1().verify_bootstrap(
        manifest_key=manifest_key,
        manifest_version_id="manifest-version-1",
        manifest_bytes=manifest_bytes,
        object_payloads=payloads,
    )

    feed = evidence.objects[0]

    provenance = NvdSilverProvenanceFactoryV1().build(
        evidence=evidence,
        bronze_object_key=feed.key,
        record_index=42,
    )

    assert provenance.bootstrap_feed_year == 2026
    assert provenance.bootstrap_feed_revision == "revision-abc"
    assert provenance.incremental_update_id is None
    assert provenance.bronze_object_version_id == "feed-version-1"
    assert provenance.source_observed_at == datetime(
        2026,
        8,
        21,
        tzinfo=UTC,
    )
