"""Unit tests for NVD incremental watermark candidate semantics."""

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from opslens.ingestion.nvd.application.incremental_key_factory import (
    NvdIncrementalKeyFactory,
)
from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifest,
    NvdIncrementalManifestFactory,
    NvdIncrementalManifestSerializer,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
    NvdBronzeWriteStatus,
)
from opslens.ingestion.nvd.application.watermark import (
    NvdWatermarkCandidate,
    NvdWatermarkCandidateFactory,
    NvdWatermarkCandidateSerializer,
    NvdWatermarkTransitionValidator,
)
from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPageParser,
    NvdCveApiPagination,
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


def _manifest_evidence() -> tuple[
    NvdIncrementalWindow,
    NvdIncrementalManifest,
    bytes,
    str,
]:
    """Build one COMPLETE Bronze manifest and exact bytes."""
    document: dict[str, object] = {
        "resultsPerPage": 1,
        "startIndex": 0,
        "totalResults": 1,
        "format": "NVD_CVE",
        "version": "2.0",
        "timestamp": ("2026-08-18T20:00:01.000"),
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2026-1000",
                }
            }
        ],
    }

    page = NvdCveApiPageParser().parse(
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )

    pagination = NvdCveApiPagination(pages=(page,))

    window = _window()
    key_factory = NvdIncrementalKeyFactory()

    manifest = NvdIncrementalManifestFactory().build(
        window=window,
        pagination=pagination,
        page_keys=(
            key_factory.build_attempt_page_key(
                window=window,
                attempt_id="a" * 64,
                start_index=page.start_index,
            ),
        ),
        page_writes=(
            NvdBronzeWriteResult(
                status=NvdBronzeWriteStatus.CREATED,
                version_id="page-version-123",
            ),
        ),
    )

    payload = NvdIncrementalManifestSerializer().serialize(manifest)

    return (
        window,
        manifest,
        payload,
        key_factory.build_manifest_key(window=window),
    )


def _candidate(
    *,
    write_status: NvdBronzeWriteStatus = (NvdBronzeWriteStatus.CREATED),
) -> NvdWatermarkCandidate:
    """Build one Bronze-complete watermark candidate."""
    (
        window,
        manifest,
        payload,
        manifest_key,
    ) = _manifest_evidence()

    return NvdWatermarkCandidateFactory().build(
        window=window,
        manifest=manifest,
        manifest_payload=payload,
        manifest_key=manifest_key,
        manifest_write=NvdBronzeWriteResult(
            status=write_status,
            version_id=("manifest-version-123"),
        ),
        key_factory=NvdIncrementalKeyFactory(),
    )


def test_candidate_binds_exact_complete_manifest() -> None:
    """Bind the candidate to exact immutable Bronze completion evidence."""
    (
        _,
        _,
        payload,
        manifest_key,
    ) = _manifest_evidence()

    candidate = _candidate()

    assert candidate.bronze_manifest_key == manifest_key
    assert candidate.bronze_manifest_version_id == "manifest-version-123"
    assert candidate.bronze_manifest_sha256 == hashlib.sha256(payload).hexdigest()
    assert candidate.total_results == 1
    assert candidate.page_count == 1


def test_candidate_proposes_window_end_without_committing_it() -> None:
    """Represent the proposed boundary separately from committed state."""
    candidate = _candidate()

    assert candidate.canonical_window_start_at == "2026-08-18T18:00:00Z"
    assert candidate.canonical_window_end_at == "2026-08-18T20:00:00Z"
    assert candidate.STATE == "bronze_complete"


def test_candidate_serializer_is_retry_stable() -> None:
    """Ignore created-versus-replay write outcome in candidate bytes."""
    serializer = NvdWatermarkCandidateSerializer()

    first = _candidate(write_status=(NvdBronzeWriteStatus.CREATED))
    replay = _candidate(write_status=(NvdBronzeWriteStatus.ALREADY_EXISTS))

    assert serializer.serialize(first) == serializer.serialize(replay)


def test_candidate_serializer_excludes_volatile_runtime_fields() -> None:
    """Exclude runtime attempt metadata from candidate evidence."""
    payload = NvdWatermarkCandidateSerializer().serialize(_candidate())

    document = cast(
        dict[str, object],
        json.loads(payload),
    )

    assert document["state"] == "bronze_complete"
    assert "retrieved_at" not in document
    assert "etag" not in document
    assert "write_status" not in document
    assert "committed" not in document


def test_candidate_factory_rejects_wrong_manifest_key() -> None:
    """Reject completion evidence persisted under a different logical key."""
    (
        window,
        manifest,
        payload,
        _,
    ) = _manifest_evidence()

    with pytest.raises(
        ValueError,
        match="manifest key",
    ):
        NvdWatermarkCandidateFactory().build(
            window=window,
            manifest=manifest,
            manifest_payload=payload,
            manifest_key=("bronze/nvd/cve/updates/wrong/manifest.json"),
            manifest_write=(
                NvdBronzeWriteResult(
                    status=(NvdBronzeWriteStatus.CREATED),
                    version_id=("manifest-version-123"),
                )
            ),
            key_factory=(NvdIncrementalKeyFactory()),
        )


def test_candidate_factory_rejects_different_update_id() -> None:
    """Reject manifest evidence from another logical update run."""
    (
        window,
        manifest,
        payload,
        manifest_key,
    ) = _manifest_evidence()

    different_manifest = replace(
        manifest,
        update_id="0" * 64,
    )

    with pytest.raises(
        ValueError,
        match="update id",
    ):
        NvdWatermarkCandidateFactory().build(
            window=window,
            manifest=different_manifest,
            manifest_payload=payload,
            manifest_key=manifest_key,
            manifest_write=(
                NvdBronzeWriteResult(
                    status=(NvdBronzeWriteStatus.CREATED),
                    version_id=("manifest-version-123"),
                )
            ),
            key_factory=(NvdIncrementalKeyFactory()),
        )


def test_transition_accepts_exact_contiguous_candidate() -> None:
    """Accept a candidate beginning at the committed boundary."""
    NvdWatermarkTransitionValidator().validate(
        committed_through_at=datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        candidate=_candidate(),
    )


def test_transition_normalizes_committed_boundary_timezone() -> None:
    """Compare committed state using the underlying UTC instant."""
    eastern = datetime(
        2026,
        8,
        18,
        14,
        0,
        tzinfo=timezone_from_hours(-4),
    )

    NvdWatermarkTransitionValidator().validate(
        committed_through_at=eastern,
        candidate=_candidate(),
    )


def timezone_from_hours(
    hours: int,
):
    """Build one fixed timezone for transition tests."""
    from datetime import timezone

    return timezone(timedelta(hours=hours))


def test_transition_rejects_gap() -> None:
    """Reject a candidate starting after the committed boundary."""
    with pytest.raises(
        ValueError,
        match="current committed boundary",
    ):
        NvdWatermarkTransitionValidator().validate(
            committed_through_at=datetime(
                2026,
                8,
                18,
                17,
                59,
                tzinfo=UTC,
            ),
            candidate=_candidate(),
        )


def test_transition_rejects_overlap() -> None:
    """Reject a candidate starting before the committed boundary."""
    with pytest.raises(
        ValueError,
        match="current committed boundary",
    ):
        NvdWatermarkTransitionValidator().validate(
            committed_through_at=datetime(
                2026,
                8,
                18,
                18,
                1,
                tzinfo=UTC,
            ),
            candidate=_candidate(),
        )


def test_transition_rejects_naive_committed_boundary() -> None:
    """Require explicit timezone evidence for committed state."""
    naive = datetime(
        2026,
        8,
        18,
        18,
        0,
        tzinfo=UTC,
    ).replace(tzinfo=None)

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        NvdWatermarkTransitionValidator().validate(
            committed_through_at=naive,
            candidate=_candidate(),
        )
