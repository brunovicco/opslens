"""Tests for deterministic historical EPSS Silver preparation."""

import gzip
import hashlib
from datetime import date

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
    evidence = _evidence()
    parser = HistoricalEpssSnapshotParser()
    transformer = HistoricalEpssSilverRecordTransformer()
    snapshot = parser.parse(
        evidence.source.raw_bytes,
        snapshot_date=evidence.manifest.snapshot_date,
    )
    records = tuple(transformer.iter_records(snapshot))

    assert [record.cve for record in records] == ["CVE-2021-0001", "CVE-2021-0002"]
    assert [record.epss for record in records] == [0.1, 0.9]
    assert [record.percentile for record in records] == [None, None]
    assert [record.model_version for record in records] == [None, None]
    assert [record.score_timestamp for record in records] == [None, None]

    service = PrepareHistoricalEpssSilver(
        parser=parser,
        transformer=transformer,
        record_writer=PyArrowSilverEpssRecordWriter(batch_size=1),
        key_factory=EpssSilverKeyFactory(),
    )
    prepared = service.execute(evidence)

    assert prepared.key == "silver/epss/snapshot_date=2021-04-14/part-00000.parquet"
    assert prepared.artifact.row_count == 2
    assert prepared.artifact.schema_version == 2
    assert prepared.artifact.parquet_bytes.startswith(b"PAR1")
