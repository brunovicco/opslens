"""Unit tests for read-only historical EPSS post-backfill evidence verification."""

import gzip
import hashlib
import json
from datetime import date

from opslens.bootstrap.epss_history import (
    APPROVED_ARCHIVE_COMMIT,
    APPROVED_ROOT_TREE_SHA,
    ARCHIVE_REPOSITORY,
    CANARY_DATES,
    HistoricalEpssArchiveInventoryV1,
    HistoricalEpssBootstrapPlanFactoryV1,
    HistoricalEpssWorkItemV1,
)
from opslens.bootstrap.epss_history_backfill import HistoricalEpssBackfillAuthorityV1
from opslens.bootstrap.epss_history_evidence import (
    HistoricalEpssEvidenceObjectV1,
    HistoricalEpssEvidenceVersionV1,
    VerifyHistoricalEpssBackfillEvidenceV1,
)
from opslens.ingestion.epss.domain.history import EpssModelEra, HistoricalEpssSnapshotParser
from opslens.transformation.epss.application.key_factory import EpssSilverKeyFactory
from opslens.transformation.epss.history.completion import HistoricalEpssCompletionManifestFactoryV1
from opslens.transformation.epss.history.manifest import HistoricalEpssBronzeManifestParserV1
from opslens.transformation.epss.history.models import (
    HistoricalEpssBronzeEvidenceV1,
    HistoricalEpssBronzeObjectPayloadV1,
    HistoricalEpssSilverArtifactV1,
    HistoricalEpssSilverPersistenceResultV1,
    HistoricalEpssSilverReplayStatus,
    HistoricalEpssSilverStoredObjectV1,
)
from opslens.transformation.epss.history.preparation import HistoricalEpssPreparedSilverV1

BOUNDARY = date(2026, 8, 14)
ABSENT_DATE = date(2021, 4, 22)


def _gzip(text: str) -> bytes:
    return gzip.compress(text.encode(), mtime=0)


def _source(snapshot_date: date) -> bytes:
    era = EpssModelEra.for_snapshot_date(snapshot_date)
    if era is EpssModelEra.V1:
        return _gzip("cve,epss\nCVE-2020-5902,0.65117\n")
    model = era.expected_source_model_version
    assert model is not None
    return _gzip(
        f"#model_version:{model},score_date:{snapshot_date.isoformat()}T00:00:00+00:00\n"
        "cve,epss,percentile\nCVE-2021-12345,0.01234,0.45678\n"
    )


def _git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(
        f"blob {len(payload)}\0".encode() + payload,
        usedforsecurity=False,
    ).hexdigest()


def _inventory() -> tuple[HistoricalEpssArchiveInventoryV1, dict[date, bytes]]:
    sources = {snapshot_date: _source(snapshot_date) for snapshot_date in CANARY_DATES}
    items = tuple(
        HistoricalEpssWorkItemV1(
            snapshot_date=snapshot_date,
            archive_path=(
                f"{snapshot_date.year}/epss_scores-{snapshot_date.isoformat()}.csv.gz"
            ),
            archive_git_blob_sha1=_git_blob_sha1(sources[snapshot_date]),
            compressed_size_bytes=len(sources[snapshot_date]),
            model_era=EpssModelEra.for_snapshot_date(snapshot_date),
        )
        for snapshot_date in CANARY_DATES
    )
    years = tuple(
        (year, str(index) * 40)
        for index, year in enumerate(sorted({value.year for value in CANARY_DATES}), start=1)
    )
    return (
        HistoricalEpssArchiveInventoryV1(
            archive_repository=ARCHIVE_REPOSITORY,
            archive_commit=APPROVED_ARCHIVE_COMMIT,
            root_tree_sha=APPROVED_ROOT_TREE_SHA,
            year_tree_shas=years,
            snapshots=items,
            source_absent_dates=(ABSENT_DATE,),
        ),
        sources,
    )


class BoundaryReader:
    def discover(self) -> date:
        return BOUNDARY


class InventoryReader:
    def __init__(self, inventory: HistoricalEpssArchiveInventoryV1) -> None:
        self.inventory = inventory

    def read(self) -> HistoricalEpssArchiveInventoryV1:
        return self.inventory


class FakePreparer:
    def __init__(self) -> None:
        self.key_factory = EpssSilverKeyFactory(prefix="silver/epss")

    def execute(self, evidence: HistoricalEpssBronzeEvidenceV1) -> HistoricalEpssPreparedSilverV1:
        payload = (
            f"parquet:{evidence.manifest.snapshot_date.isoformat()}:"
            f"{evidence.manifest.source_sha256}"
        ).encode()
        return HistoricalEpssPreparedSilverV1(
            key=self.key_factory.build(evidence.manifest.snapshot_date),
            artifact=HistoricalEpssSilverArtifactV1(
                parquet_bytes=payload,
                row_count=1,
                schema_version=2,
            ),
        )


class FakeEvidenceStore:
    def __init__(self) -> None:
        self.current_versions: dict[str, str] = {}
        self.objects: dict[tuple[str, str], bytes] = {}
        self.versions: dict[str, list[HistoricalEpssEvidenceVersionV1]] = {}

    def add_current(self, *, key: str, version_id: str, raw_bytes: bytes) -> None:
        previous = self.current_versions.get(key)
        if previous is not None:
            for index, version in enumerate(self.versions[key]):
                if version.version_id == previous:
                    self.versions[key][index] = HistoricalEpssEvidenceVersionV1(
                        key=key,
                        version_id=previous,
                        is_latest=False,
                    )
        self.current_versions[key] = version_id
        self.objects[(key, version_id)] = raw_bytes
        self.versions.setdefault(key, []).append(
            HistoricalEpssEvidenceVersionV1(
                key=key,
                version_id=version_id,
                is_latest=True,
            )
        )

    def add_old_version(self, *, key: str, version_id: str, raw_bytes: bytes) -> None:
        self.objects[(key, version_id)] = raw_bytes
        self.versions.setdefault(key, []).append(
            HistoricalEpssEvidenceVersionV1(
                key=key,
                version_id=version_id,
                is_latest=False,
            )
        )

    def replace_current_bytes(self, *, key: str, raw_bytes: bytes) -> None:
        version_id = self.current_versions[key]
        self.objects[(key, version_id)] = raw_bytes

    def delete_current(self, *, key: str) -> None:
        del self.current_versions[key]

    def list_current_keys(self, *, prefix: str) -> tuple[str, ...]:
        return tuple(sorted(key for key in self.current_versions if key.startswith(prefix)))

    def read_current(self, *, key: str) -> HistoricalEpssEvidenceObjectV1:
        version_id = self.current_versions.get(key)
        if version_id is None:
            raise KeyError(key)
        return self.read_version(key=key, version_id=version_id)

    def read_version(self, *, key: str, version_id: str) -> HistoricalEpssEvidenceObjectV1:
        raw_bytes = self.objects.get((key, version_id))
        if raw_bytes is None:
            raise KeyError(f"{key}@{version_id}")
        return HistoricalEpssEvidenceObjectV1(
            key=key,
            version_id=version_id,
            raw_bytes=raw_bytes,
        )

    def list_versions(self, *, key: str) -> tuple[HistoricalEpssEvidenceVersionV1, ...]:
        return tuple(self.versions.get(key, []))


def _keys(snapshot_date: date) -> dict[str, str]:
    value = snapshot_date.isoformat()
    bronze_prefix = (
        "bronze/epss-history/schema_version=1/"
        f"archive_commit={APPROVED_ARCHIVE_COMMIT}/snapshot_date={value}"
    )
    return {
        "source": f"{bronze_prefix}/epss_scores.csv.gz",
        "manifest": f"{bronze_prefix}/manifest.json",
        "silver": f"silver/epss/snapshot_date={value}/part-00000.parquet",
        "completion": (
            "silver/epss-history/completions/schema_version=1/"
            f"archive_commit={APPROVED_ARCHIVE_COMMIT}/snapshot_date={value}/manifest.json"
        ),
    }


def _manifest_bytes(
    *,
    work_item: HistoricalEpssWorkItemV1,
    source_bytes: bytes,
    source_version_id: str,
) -> bytes:
    snapshot = HistoricalEpssSnapshotParser().parse(
        source_bytes,
        snapshot_date=work_item.snapshot_date,
    )
    keys = _keys(work_item.snapshot_date)
    document = {
        "archive_commit": APPROVED_ARCHIVE_COMMIT,
        "archive_git_blob_sha1": work_item.archive_git_blob_sha1,
        "archive_path": work_item.archive_path,
        "archive_repository": ARCHIVE_REPOSITORY,
        "compressed_size_bytes": work_item.compressed_size_bytes,
        "model_era": work_item.model_era.value,
        "schema_version": 1,
        "snapshot_date": work_item.snapshot_date.isoformat(),
        "source_metadata_present": snapshot.source_metadata_present,
        "source_object_key": keys["source"],
        "source_object_version_id": source_version_id,
        "source_sha256": snapshot.sha256,
    }
    return (
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode()


def _authority(inventory: HistoricalEpssArchiveInventoryV1) -> HistoricalEpssBackfillAuthorityV1:
    plan = HistoricalEpssBootstrapPlanFactoryV1().build(
        inventory=inventory,
        first_forward_snapshot_date=BOUNDARY,
    )
    return HistoricalEpssBackfillAuthorityV1(
        first_forward_snapshot_date=BOUNDARY,
        candidate_count=plan.candidate_count,
        candidate_compressed_bytes=plan.candidate_compressed_bytes,
        plan_id=plan.plan_id,
        source_absent_dates=plan.source_absent_dates,
    )


def _fixture() -> tuple[
    HistoricalEpssArchiveInventoryV1,
    FakeEvidenceStore,
    FakePreparer,
    HistoricalEpssBackfillAuthorityV1,
]:
    inventory, sources = _inventory()
    store = FakeEvidenceStore()
    preparer = FakePreparer()
    manifest_parser = HistoricalEpssBronzeManifestParserV1()
    completion_factory = HistoricalEpssCompletionManifestFactoryV1(
        silver_key_factory=preparer.key_factory
    )

    for work_item in inventory.snapshots:
        snapshot_date = work_item.snapshot_date
        source_bytes = sources[snapshot_date]
        keys = _keys(snapshot_date)
        suffix = snapshot_date.isoformat()
        source_version = f"source-{suffix}"
        manifest_version = f"manifest-{suffix}"
        silver_version = f"silver-{suffix}"
        completion_version = f"completion-{suffix}"
        manifest_bytes = _manifest_bytes(
            work_item=work_item,
            source_bytes=source_bytes,
            source_version_id=source_version,
        )
        manifest = manifest_parser.parse(
            HistoricalEpssBronzeObjectPayloadV1(
                key=keys["manifest"],
                version_id=manifest_version,
                raw_bytes=manifest_bytes,
            )
        )
        bronze = HistoricalEpssBronzeEvidenceV1(
            manifest=manifest,
            source=HistoricalEpssBronzeObjectPayloadV1(
                key=keys["source"],
                version_id=source_version,
                raw_bytes=source_bytes,
            ),
        )
        prepared = preparer.execute(bronze)
        stored_silver = HistoricalEpssSilverStoredObjectV1(
            key=prepared.key,
            version_id=silver_version,
            parquet_sha256=prepared.artifact.parquet_sha256,
            size_bytes=prepared.artifact.size_bytes,
            row_count=prepared.artifact.row_count,
            schema_version=prepared.artifact.schema_version,
        )
        completion = completion_factory.build(
            bronze=bronze,
            silver=HistoricalEpssSilverPersistenceResultV1(
                stored_object=stored_silver,
                replay_status=HistoricalEpssSilverReplayStatus.CREATED,
            ),
        )

        store.add_current(key=keys["source"], version_id=source_version, raw_bytes=source_bytes)
        store.add_current(
            key=keys["manifest"],
            version_id=manifest_version,
            raw_bytes=manifest_bytes,
        )
        store.add_current(
            key=keys["silver"],
            version_id=silver_version,
            raw_bytes=prepared.artifact.parquet_bytes,
        )
        store.add_current(
            key=keys["completion"],
            version_id=completion_version,
            raw_bytes=completion.raw_bytes,
        )

    return inventory, store, preparer, _authority(inventory)


def _verifier(
    *,
    inventory: HistoricalEpssArchiveInventoryV1,
    store: FakeEvidenceStore,
    preparer: FakePreparer,
    authority: HistoricalEpssBackfillAuthorityV1,
) -> VerifyHistoricalEpssBackfillEvidenceV1:
    return VerifyHistoricalEpssBackfillEvidenceV1(
        forward_boundary_reader=BoundaryReader(),
        archive_inventory_reader=InventoryReader(inventory),
        evidence_store=store,
        silver_preparer=preparer,
        authority=authority,
        silver_key_factory=preparer.key_factory,
    )


def test_complete_exact_evidence_passes() -> None:
    inventory, store, preparer, authority = _fixture()

    summary = _verifier(
        inventory=inventory,
        store=store,
        preparer=preparer,
        authority=authority,
    ).execute()

    assert summary.result == "PASS"
    assert summary.expected_snapshots == 7
    assert summary.bronze_sources == 7
    assert summary.bronze_manifests == 7
    assert summary.silver_objects == 7
    assert summary.completion_manifests == 7
    assert summary.canary_dates_checked == 7
    assert summary.canary_divergent_versions == 0
    assert (summary.era_v1, summary.era_v2, summary.era_v3, summary.era_v4, summary.era_v5) == (
        2,
        1,
        1,
        1,
        2,
    )


def test_missing_expected_completion_fails() -> None:
    inventory, store, preparer, authority = _fixture()
    store.delete_current(key=_keys(CANARY_DATES[0])["completion"])

    summary = _verifier(
        inventory=inventory,
        store=store,
        preparer=preparer,
        authority=authority,
    ).execute()

    assert summary.result == "FAIL"
    assert summary.missing_expected == 1
    assert summary.completion_manifests == 6


def test_source_hash_divergence_fails() -> None:
    inventory, store, preparer, authority = _fixture()
    key = _keys(CANARY_DATES[0])["source"]
    store.replace_current_bytes(
        key=key,
        raw_bytes=_gzip("cve,epss\nCVE-2020-5902,0.99999\n"),
    )

    summary = _verifier(
        inventory=inventory,
        store=store,
        preparer=preparer,
        authority=authority,
    ).execute()

    assert summary.result == "FAIL"
    assert summary.hash_failures == 1


def test_completion_authority_divergence_fails() -> None:
    inventory, store, preparer, authority = _fixture()
    store.replace_current_bytes(
        key=_keys(CANARY_DATES[0])["completion"],
        raw_bytes=b"{}\n",
    )

    summary = _verifier(
        inventory=inventory,
        store=store,
        preparer=preparer,
        authority=authority,
    ).execute()

    assert summary.result == "FAIL"
    assert summary.completion_authority_failures == 1


def test_historical_boundary_overlap_is_rejected() -> None:
    inventory, store, preparer, authority = _fixture()
    key = (
        "bronze/epss-history/schema_version=1/"
        f"archive_commit={APPROVED_ARCHIVE_COMMIT}/"
        f"snapshot_date={BOUNDARY.isoformat()}/manifest.json"
    )
    store.add_current(key=key, version_id="unexpected-boundary", raw_bytes=b"{}\n")

    summary = _verifier(
        inventory=inventory,
        store=store,
        preparer=preparer,
        authority=authority,
    ).execute()

    assert summary.result == "FAIL"
    assert summary.boundary_violations == 1
    assert summary.unexpected_historical == 1


def test_source_absent_date_artifact_is_rejected() -> None:
    inventory, store, preparer, authority = _fixture()
    key = f"silver/epss/snapshot_date={ABSENT_DATE.isoformat()}/part-00000.parquet"
    store.add_current(key=key, version_id="absent-silver", raw_bytes=b"unexpected")

    summary = _verifier(
        inventory=inventory,
        store=store,
        preparer=preparer,
        authority=authority,
    ).execute()

    assert summary.result == "FAIL"
    assert summary.source_absent_dates_checked == 1
    assert summary.source_absent_artifacts_found == 1
    assert summary.unexpected_historical == 1


def test_canary_divergent_version_is_rejected() -> None:
    inventory, store, preparer, authority = _fixture()
    key = _keys(CANARY_DATES[0])["silver"]
    store.add_old_version(
        key=key,
        version_id="divergent-old-version",
        raw_bytes=b"different-parquet-bytes",
    )

    summary = _verifier(
        inventory=inventory,
        store=store,
        preparer=preparer,
        authority=authority,
    ).execute()

    assert summary.result == "FAIL"
    assert summary.canary_divergent_versions == 1


def test_source_current_version_must_match_manifest_authority() -> None:
    inventory, store, preparer, authority = _fixture()
    key = _keys(CANARY_DATES[0])["source"]
    current = store.read_current(key=key)
    store.add_current(
        key=key,
        version_id="identical-new-current-version",
        raw_bytes=current.raw_bytes,
    )

    summary = _verifier(
        inventory=inventory,
        store=store,
        preparer=preparer,
        authority=authority,
    ).execute()

    assert summary.result == "FAIL"
    assert summary.version_authority_failures >= 1
