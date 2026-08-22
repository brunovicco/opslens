"""Tests for complete pre-persistence NVD Silver application orchestration."""

import gzip
import json
from datetime import UTC, datetime
from hashlib import sha256

from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)
from opslens.transformation.nvd.application.models import (
    NvdSilverTransformRequestV1,
)
from opslens.transformation.nvd.application.record_composer import (
    NvdSilverRecordComposerV1,
)
from opslens.transformation.nvd.application.service import (
    NvdSilverPrepareServiceV1,
)
from opslens.transformation.nvd.application.source_reader import (
    NvdSilverSourceBatchReaderV1,
)
from opslens.transformation.nvd.completion.key_factory import (
    NvdSilverKeyFactoryV1,
)
from opslens.transformation.nvd.domain.collections_transformer import (
    NvdCveCollectionsTransformer,
)
from opslens.transformation.nvd.domain.configurations_transformer import (
    NvdCpeConfigurationsTransformer,
)
from opslens.transformation.nvd.domain.cvss_transformer import (
    NvdCvssMetricsTransformer,
)
from opslens.transformation.nvd.domain.transformer import (
    NvdCveCoreTransformer,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectPayloadV1,
)
from opslens.transformation.nvd.provenance.verifier import (
    NvdBronzeEvidenceVerifierV1,
    NvdSilverProvenanceFactoryV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)
from opslens.transformation.nvd.serialization.parquet import (
    NvdSilverParquetSerializerV1,
)


def _canonical_json_bytes(
    document: dict[str, object],
) -> bytes:
    """Serialize one internal manifest using the frozen canonical encoding."""
    return (
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _source_cve(
    cve_id: str,
) -> dict[str, object]:
    """Build one minimal valid NVD CVE for complete Silver preparation."""
    return {
        "id": cve_id,
        "sourceIdentifier": "security@example.com",
        "published": "2026-08-20T10:00:00.000Z",
        "lastModified": "2026-08-21T11:00:00.000Z",
        "vulnStatus": "Analyzed",
        "descriptions": [
            {
                "lang": "en",
                "value": f"Example vulnerability {cve_id}.",
            }
        ],
        "references": [],
    }


def _service() -> NvdSilverPrepareServiceV1:
    """Compose the real deterministic application graph."""
    return NvdSilverPrepareServiceV1(
        evidence_verifier=NvdBronzeEvidenceVerifierV1(),
        source_reader=NvdSilverSourceBatchReaderV1(),
        record_composer=NvdSilverRecordComposerV1(
            core_transformer=NvdCveCoreTransformer(),
            collections_transformer=NvdCveCollectionsTransformer(),
            cvss_transformer=NvdCvssMetricsTransformer(),
            configurations_transformer=NvdCpeConfigurationsTransformer(),
            provenance_factory=NvdSilverProvenanceFactoryV1(),
        ),
        parquet_serializer=NvdSilverParquetSerializerV1(),
        key_factory=NvdSilverKeyFactoryV1(),
    )


def test_prepares_incremental_batch_end_to_end() -> None:
    """Verify Bronze and prepare deterministic incremental Silver output."""
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

    page_key = f"bronze/nvd/cve/updates/update_id={update_id}/page_start=000000/response.json"
    manifest_key = f"bronze/nvd/cve/updates/update_id={update_id}/manifest.json"

    page_bytes = json.dumps(
        {
            "resultsPerPage": 1,
            "startIndex": 0,
            "totalResults": 1,
            "format": "NVD_CVE",
            "version": "2.0",
            "timestamp": "2026-08-21T12:00:00.000",
            "vulnerabilities": [
                {
                    "cve": _source_cve("CVE-2026-5000"),
                }
            ],
        },
        separators=(",", ":"),
    ).encode("utf-8")

    manifest_bytes = _canonical_json_bytes(
        {
            "completion_status": "complete",
            "manifest_version": "1",
            "source": "nvd-cve",
            "source_interface": "cve-api-2.0",
            "source_format": "NVD_CVE",
            "source_version": "2.0",
            "update_id": update_id,
            "window_start_at": (window.start_at.isoformat().replace("+00:00", "Z")),
            "window_end_at": (window.end_at.isoformat().replace("+00:00", "Z")),
            "total_results": 1,
            "page_count": 1,
            "pages": [
                {
                    "start_index": 0,
                    "results_per_page": 1,
                    "total_results": 1,
                    "key": page_key,
                    "version_id": "page-version-1",
                    "size_bytes": len(page_bytes),
                    "sha256": sha256(page_bytes).hexdigest(),
                    "source_timestamp": "2026-08-21T12:00:00.000",
                }
            ],
        }
    )

    request = NvdSilverTransformRequestV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        manifest_key=manifest_key,
        manifest_version_id="manifest-version-1",
        manifest_bytes=manifest_bytes,
        object_payloads=(
            NvdBronzeObjectPayloadV1(
                key=page_key,
                version_id="page-version-1",
                raw_bytes=page_bytes,
            ),
        ),
    )

    prepared = _service().prepare(request)

    assert prepared.evidence.source_kind is NvdSilverSourceKind.INCREMENTAL
    assert prepared.evidence.source_batch_id == update_id

    assert len(prepared.records) == 1
    assert prepared.records[0].core.observed_version.cve_id == ("CVE-2026-5000")

    assert prepared.parquet_artifact.row_count == 1
    assert prepared.parquet_artifact.parquet_bytes.startswith(b"PAR1")
    assert prepared.parquet_artifact.parquet_bytes.endswith(b"PAR1")

    assert prepared.keys.parquet_key == (
        "silver/nvd/cve/"
        "schema_version=1/"
        "source_kind=incremental/"
        f"update_id={update_id}/"
        "part-00000.parquet"
    )

    assert prepared.keys.manifest_key == (
        "silver/nvd/cve/"
        "schema_version=1/"
        "source_kind=incremental/"
        f"update_id={update_id}/"
        "manifest.json"
    )


def test_prepares_zero_result_incremental_batch() -> None:
    """Keep zero-result updates valid through the complete prepare boundary."""
    window = NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            21,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            22,
            tzinfo=UTC,
        ),
    )

    update_id = window.update_id

    page_key = f"bronze/nvd/cve/updates/update_id={update_id}/page_start=000000/response.json"
    manifest_key = f"bronze/nvd/cve/updates/update_id={update_id}/manifest.json"

    page_bytes = json.dumps(
        {
            "resultsPerPage": 0,
            "startIndex": 0,
            "totalResults": 0,
            "format": "NVD_CVE",
            "version": "2.0",
            "timestamp": "2026-08-22T12:00:00.000",
            "vulnerabilities": [],
        },
        separators=(",", ":"),
    ).encode("utf-8")

    manifest_bytes = _canonical_json_bytes(
        {
            "completion_status": "complete",
            "manifest_version": "1",
            "source": "nvd-cve",
            "source_interface": "cve-api-2.0",
            "source_format": "NVD_CVE",
            "source_version": "2.0",
            "update_id": update_id,
            "window_start_at": (window.start_at.isoformat().replace("+00:00", "Z")),
            "window_end_at": (window.end_at.isoformat().replace("+00:00", "Z")),
            "total_results": 0,
            "page_count": 1,
            "pages": [
                {
                    "start_index": 0,
                    "results_per_page": 0,
                    "total_results": 0,
                    "key": page_key,
                    "version_id": "page-version-1",
                    "size_bytes": len(page_bytes),
                    "sha256": sha256(page_bytes).hexdigest(),
                    "source_timestamp": "2026-08-22T12:00:00.000",
                }
            ],
        }
    )

    request = NvdSilverTransformRequestV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        manifest_key=manifest_key,
        manifest_version_id="manifest-version-1",
        manifest_bytes=manifest_bytes,
        object_payloads=(
            NvdBronzeObjectPayloadV1(
                key=page_key,
                version_id="page-version-1",
                raw_bytes=page_bytes,
            ),
        ),
    )

    prepared = _service().prepare(request)

    assert prepared.records == ()
    assert prepared.parquet_artifact.row_count == 0
    assert prepared.parquet_artifact.source_batch_id == update_id
    assert prepared.parquet_artifact.parquet_bytes.startswith(b"PAR1")
    assert prepared.parquet_artifact.parquet_bytes.endswith(b"PAR1")


def test_prepares_bootstrap_batch_end_to_end() -> None:
    """Verify exact yearly-feed evidence and prepare bootstrap Silver output."""
    feed_year = 2026
    feed_revision = "20260818T070012Z-example-revision"

    base = f"bronze/nvd/cve/bootstrap/feed_year={feed_year}/feed_revision={feed_revision}"

    feed_key = f"{base}/nvdcve-2.0-{feed_year}.json.gz"
    meta_key = f"{base}/nvdcve-2.0-{feed_year}.meta"
    manifest_key = f"{base}/manifest.json"

    source_bytes = json.dumps(
        {
            "vulnerabilities": [
                {
                    "cve": _source_cve("CVE-2026-6000"),
                }
            ]
        },
        separators=(",", ":"),
    ).encode("utf-8")

    feed_bytes = gzip.compress(
        source_bytes,
        mtime=0,
    )
    meta_bytes = b"lastModifiedDate:2026-08-18T07:00:12Z\n"

    manifest_bytes = _canonical_json_bytes(
        {
            "completion_status": "complete",
            "manifest_version": "1",
            "source": "nvd-cve",
            "source_interface": "json-2.0-yearly-feed",
            "feed_year": feed_year,
            "feed_revision": feed_revision,
            "source_last_modified_at": "2026-08-18T07:00:12Z",
            "feed_object": {
                "key": feed_key,
                "version_id": "feed-version-1",
                "size_bytes": len(feed_bytes),
                "sha256": sha256(feed_bytes).hexdigest(),
            },
            "meta_object": {
                "key": meta_key,
                "version_id": "meta-version-1",
                "size_bytes": len(meta_bytes),
                "sha256": sha256(meta_bytes).hexdigest(),
            },
        }
    )

    request = NvdSilverTransformRequestV1(
        source_kind=NvdSilverSourceKind.BOOTSTRAP,
        manifest_key=manifest_key,
        manifest_version_id="manifest-version-1",
        manifest_bytes=manifest_bytes,
        object_payloads=(
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
        ),
    )

    prepared = _service().prepare(request)

    assert prepared.evidence.source_kind is NvdSilverSourceKind.BOOTSTRAP
    assert prepared.evidence.bootstrap_feed_year == 2026

    assert len(prepared.records) == 1
    assert prepared.records[0].core.observed_version.cve_id == ("CVE-2026-6000")

    assert prepared.parquet_artifact.row_count == 1

    assert prepared.keys.parquet_key == (
        "silver/nvd/cve/"
        "schema_version=1/"
        "source_kind=bootstrap/"
        "feed_year=2026/"
        f"feed_revision={feed_revision}/"
        "part-00000.parquet"
    )
