"""Tests for deterministic historical EPSS Silver preparation."""

import gzip
import hashlib
from datetime import date
from io import BytesIO

import pyarrow.parquet as pq

from opslens.ingestion.epss.domain.history import (
    EpssModelEra,
    HistoricalEpssSnapshotParser,
)
from opslens.transformation.epss.adapters.outbound.parquet import PyArrowSilverEpssRecordWriter
from opslens.transformation.epss.application.key_factory import EpssSilverKeyFactory
from opslens.transformation.epss.history.models import (
    HistoricalEpssBronzeEvidenceV1,
    HistoricalEpssBronzeManifestV1,
    HistoricalEpssBronzeObjectPayloadV1,
)
from opslens.transformation.epss.history.preparation import (
    HistoricalEpssSilverRecordTransformer,
    PrepareHistoricalEpssSilver,
)

SNAPSHOT_DATE = date(2021, 4, 14)
COMMIT = "a" * 40


def _evidence() -> HistoricalEpssBronzeEvidenceV1:
    """Build exact early-v1 Bronze evidence for preparation tests."""
    source_bytes = gzip.compress(
        b"cve,epss\nCVE-2021-0001,0.100000\nCVE-2021-0002,0.900000\n",
        mtime=0,
    )
    source_key = (
        "bronze/epss-history/schema_version=1/"
        f"archive_commit={COMMIT}/snapshot_date={SNAPSHOT_DATE.isoformat()}/epss_scores.csv.gz"
    )
    manifest_key = source_key.removesuffix("epss_scores.csv.gz") + "manifest.json"
    manifest = HistoricalEpssBronzeManifestV1(
        snapshot_date=SNAPSHOT_DATE,
        archive_repository="empiricalsec/epss_scores",
        archive_commit=COMMIT,
        archive_path=f"2021/epss_scores-{SNAPSHOT_DATE.isoformat()}.csv.gz",
        archive_git_blob_sha1="b" * 40,
        model_era=EpssModelEra.V1,
        source_metadata_present=False,
        source_object_key=source_key,
        source_object_version_id="source-version",
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        compressed_size_bytes=len(source_bytes),
        manifest_key=manifest_key,
        manifest_version_id="manifest-version",
    )
    return HistoricalEpssBronzeEvidenceV1(
        manifest=manifest,
        source=HistoricalEpssBronzeObjectPayloadV1(
            key=source_key,
            version_id="source-version",
            raw_bytes=source_bytes,
        ),
    )


def test_prepares_early_v1_without_fabricating_nullable_fields() -> None:
    """Serialize exact legacy rows with unavailable evidence preserved as NULL."""
    service = PrepareHistoricalEpssSilver(
        parser=HistoricalEpssSnapshotParser(),
        transformer=HistoricalEpssSilverRecordTransformer(),
        record_writer=PyArrowSilverEpssRecordWriter(batch_size=1),
        key_factory=EpssSilverKeyFactory(),
    )

    prepared = service.execute(_evidence())

    assert prepared.key == "silver/epss/snapshot_date=2021-04-14/part-00000.parquet"
    assert prepared.artifact.row_count == 2
    assert prepared.artifact.schema_version == 2

    table = pq.read_table(BytesIO(prepared.artifact.parquet_bytes))
    assert table.column("cve").to_pylist() == ["CVE-2021-0001", "CVE-2021-0002"]
    assert table.column("epss").to_pylist() == [0.1, 0.9]
    assert table.column("percentile").to_pylist() == [None, None]
    assert table.column("model_version").to_pylist() == [None, None]
    assert table.column("score_timestamp").to_pylist() == [None, None]
