"""Read-only Phase 2.5D-5 historical EPSS post-backfill evidence verification."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from typing import Protocol

from opslens.bootstrap.epss_history import (
    APPROVED_ARCHIVE_COMMIT,
    ARCHIVE_REPOSITORY,
    CANARY_DATES,
    HistoricalEpssArchiveInventoryReader,
    HistoricalEpssBootstrapPlanFactoryV1,
    HistoricalEpssBootstrapPlanV1,
    HistoricalEpssForwardBoundaryReader,
    HistoricalEpssWorkItemV1,
)
from opslens.bootstrap.epss_history_backfill import HistoricalEpssBackfillAuthorityV1
from opslens.ingestion.epss.domain.history import EpssModelEra, HistoricalEpssSnapshotParser
from opslens.transformation.epss.application.key_factory import EpssSilverKeyFactory
from opslens.transformation.epss.history.completion import HistoricalEpssCompletionManifestFactoryV1
from opslens.transformation.epss.history.manifest import HistoricalEpssBronzeManifestParserV1
from opslens.transformation.epss.history.models import (
    HistoricalEpssBronzeEvidenceV1,
    HistoricalEpssBronzeManifestV1,
    HistoricalEpssBronzeObjectPayloadV1,
    HistoricalEpssSilverPersistenceResultV1,
    HistoricalEpssSilverReplayStatus,
    HistoricalEpssSilverStoredObjectV1,
)
from opslens.transformation.epss.history.preparation import HistoricalEpssPreparedSilverV1

BRONZE_ROOT_PREFIX = "bronze/epss-history/"
COMPLETION_ROOT_PREFIX = "silver/epss-history/completions/"
SILVER_PREFIX = "silver/epss/"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_BRONZE_DATE_RE = re.compile(r"^bronze/epss-history/.+/snapshot_date=(\d{4}-\d{2}-\d{2})/")
_COMPLETION_DATE_RE = re.compile(
    r"^silver/epss-history/completions/.+/snapshot_date=(\d{4}-\d{2}-\d{2})/"
)
_SILVER_KEY_RE = re.compile(
    r"^silver/epss/snapshot_date=(\d{4}-\d{2}-\d{2})/part-00000\.parquet$"
)


@dataclass(frozen=True, slots=True)
class HistoricalEpssEvidenceObjectV1:
    """Represent exact read-only bytes observed at one S3 object version."""

    key: str
    version_id: str
    raw_bytes: bytes

    def __post_init__(self) -> None:
        """Validate exact object identity and payload."""
        if not self.key.strip():
            raise ValueError("Historical EPSS evidence object key cannot be empty.")
        if not self.version_id.strip():
            raise ValueError("Historical EPSS evidence VersionId cannot be empty.")
        if not self.raw_bytes:
            raise ValueError("Historical EPSS evidence object bytes cannot be empty.")

    @property
    def sha256(self) -> str:
        """Return SHA-256 for the exact observed bytes."""
        return hashlib.sha256(self.raw_bytes).hexdigest()


@dataclass(frozen=True, slots=True)
class HistoricalEpssEvidenceVersionV1:
    """Represent one read-only S3 version coordinate for divergence checks."""

    key: str
    version_id: str
    is_latest: bool

    def __post_init__(self) -> None:
        """Validate version-list coordinates."""
        if not self.key.strip() or not self.version_id.strip():
            raise ValueError("Historical EPSS evidence version coordinate cannot be empty.")


class HistoricalEpssSilverPreparer(Protocol):
    """Prepare deterministic Silver bytes from verified Bronze evidence."""

    def execute(
        self,
        evidence: HistoricalEpssBronzeEvidenceV1,
    ) -> HistoricalEpssPreparedSilverV1:
        """Return the deterministic Silver key and artifact."""
        ...


class HistoricalEpssEvidenceStore(Protocol):
    """Expose only read-only object capabilities required by D5-E."""

    def list_current_keys(self, *, prefix: str) -> tuple[str, ...]:
        """List current object keys under one prefix."""
        ...

    def read_current(self, *, key: str) -> HistoricalEpssEvidenceObjectV1:
        """Read current bytes and exact VersionId for one key."""
        ...

    def read_version(self, *, key: str, version_id: str) -> HistoricalEpssEvidenceObjectV1:
        """Read one exact object version."""
        ...

    def list_versions(self, *, key: str) -> tuple[HistoricalEpssEvidenceVersionV1, ...]:
        """List non-delete object versions for one exact key."""
        ...


@dataclass(frozen=True, slots=True)
class HistoricalEpssEvidenceSummaryV1:
    """Machine-readable D5-E evidence summary."""

    archive_commit: str
    plan_id: str
    expected_snapshots: int
    bronze_sources: int
    bronze_manifests: int
    silver_objects: int
    completion_manifests: int
    missing_expected: int
    unexpected_historical: int
    provenance_failures: int
    hash_failures: int
    version_authority_failures: int
    completion_authority_failures: int
    source_absent_dates_checked: int
    source_absent_artifacts_found: int
    first_historical_date: str
    last_historical_date: str
    boundary: str
    boundary_violations: int
    canary_dates_checked: int
    canary_divergent_versions: int
    era_v1: int
    era_v2: int
    era_v3: int
    era_v4: int
    era_v5: int
    result: str

    def __post_init__(self) -> None:
        """Validate terminal evidence summary shape."""
        if _SHA256_RE.fullmatch(self.plan_id) is None:
            raise ValueError("Historical EPSS evidence summary plan_id is invalid.")
        if self.result not in {"PASS", "FAIL"}:
            raise ValueError("Historical EPSS evidence result must be PASS or FAIL.")

    @property
    def passed(self) -> bool:
        """Return whether every D5-E gate passed."""
        return self.result == "PASS"

    def to_dict(self) -> dict[str, object]:
        """Serialize the summary without mutating evidence."""
        return asdict(self)


@dataclass(slots=True)
class _EvidenceCounters:
    provenance_failures: int = 0
    hash_failures: int = 0
    version_authority_failures: int = 0
    completion_authority_failures: int = 0
    canary_divergent_versions: int = 0


class VerifyHistoricalEpssBackfillEvidenceV1:
    """Verify all frozen historical EPSS evidence without any mutation capability."""

    def __init__(
        self,
        *,
        forward_boundary_reader: HistoricalEpssForwardBoundaryReader,
        archive_inventory_reader: HistoricalEpssArchiveInventoryReader,
        evidence_store: HistoricalEpssEvidenceStore,
        silver_preparer: HistoricalEpssSilverPreparer,
        plan_factory: HistoricalEpssBootstrapPlanFactoryV1 | None = None,
        authority: HistoricalEpssBackfillAuthorityV1 | None = None,
        manifest_parser: HistoricalEpssBronzeManifestParserV1 | None = None,
        snapshot_parser: HistoricalEpssSnapshotParser | None = None,
        completion_factory: HistoricalEpssCompletionManifestFactoryV1 | None = None,
        silver_key_factory: EpssSilverKeyFactory | None = None,
    ) -> None:
        """Initialize only read-only evidence dependencies."""
        self._forward_boundary_reader = forward_boundary_reader
        self._archive_inventory_reader = archive_inventory_reader
        self._evidence_store = evidence_store
        self._silver_preparer = silver_preparer
        self._plan_factory = plan_factory or HistoricalEpssBootstrapPlanFactoryV1()
        self._authority = authority or HistoricalEpssBackfillAuthorityV1()
        self._manifest_parser = manifest_parser or HistoricalEpssBronzeManifestParserV1()
        self._snapshot_parser = snapshot_parser or HistoricalEpssSnapshotParser()
        self._silver_key_factory = silver_key_factory or EpssSilverKeyFactory(prefix="silver/epss")
        self._completion_factory = completion_factory or HistoricalEpssCompletionManifestFactoryV1(
            silver_key_factory=self._silver_key_factory
        )

    def prepare(self) -> HistoricalEpssBootstrapPlanV1:
        """Rebuild and validate the frozen plan before reading historical evidence."""
        boundary = self._forward_boundary_reader.discover()
        inventory = self._archive_inventory_reader.read()
        plan = self._plan_factory.build(
            inventory=inventory,
            first_forward_snapshot_date=boundary,
        )
        self._authority.validate(plan)
        return plan

    def execute(self) -> HistoricalEpssEvidenceSummaryV1:
        """Verify inventories, exact bytes, version authorities, and canary replay history."""
        plan = self.prepare()
        expected = self._expected_keys(plan)
        bronze_keys = set(self._evidence_store.list_current_keys(prefix=BRONZE_ROOT_PREFIX))
        completion_keys = set(
            self._evidence_store.list_current_keys(prefix=COMPLETION_ROOT_PREFIX)
        )
        silver_keys = set(self._evidence_store.list_current_keys(prefix=SILVER_PREFIX))

        expected_bronze_sources = expected["bronze_sources"]
        expected_bronze_manifests = expected["bronze_manifests"]
        expected_silver = expected["silver"]
        expected_completion = expected["completion"]
        expected_bronze = expected_bronze_sources | expected_bronze_manifests

        current_historical_silver = {
            key
            for key in silver_keys
            if (snapshot_date := _silver_snapshot_date(key)) is not None
            and snapshot_date < plan.first_forward_snapshot_date
        }

        missing_expected = (
            len(expected_bronze - bronze_keys)
            + len(expected_silver - current_historical_silver)
            + len(expected_completion - completion_keys)
        )
        unexpected_historical = (
            len(bronze_keys - expected_bronze)
            + len(current_historical_silver - expected_silver)
            + len(completion_keys - expected_completion)
        )
        boundary_violations = _boundary_violations(
            bronze_keys=bronze_keys,
            completion_keys=completion_keys,
            boundary=plan.first_forward_snapshot_date,
        )
        source_absent_artifacts_found = self._source_absent_artifacts_found(
            plan=plan,
            bronze_keys=bronze_keys,
            silver_keys=silver_keys,
            completion_keys=completion_keys,
        )

        counters = _EvidenceCounters()
        expected_payload_sha256: dict[str, str] = {}
        for work_item in plan.work_items:
            keys = _keys_for_item(work_item, silver_key_factory=self._silver_key_factory)
            if not all(
                (
                    keys["source"] in bronze_keys,
                    keys["manifest"] in bronze_keys,
                    keys["silver"] in current_historical_silver,
                    keys["completion"] in completion_keys,
                )
            ):
                continue
            self._verify_item(
                work_item=work_item,
                keys=keys,
                counters=counters,
                expected_payload_sha256=expected_payload_sha256,
            )

        self._verify_canary_versions(
            plan=plan,
            expected_payload_sha256=expected_payload_sha256,
            counters=counters,
        )

        era_counts = Counter(item.model_era for item in plan.work_items)
        failure_counts = (
            missing_expected,
            unexpected_historical,
            counters.provenance_failures,
            counters.hash_failures,
            counters.version_authority_failures,
            counters.completion_authority_failures,
            source_absent_artifacts_found,
            boundary_violations,
            counters.canary_divergent_versions,
        )
        counts_match = (
            len(expected_bronze_sources & bronze_keys) == plan.candidate_count
            and len(expected_bronze_manifests & bronze_keys) == plan.candidate_count
            and len(expected_silver & current_historical_silver) == plan.candidate_count
            and len(expected_completion & completion_keys) == plan.candidate_count
        )
        result = "PASS" if counts_match and all(value == 0 for value in failure_counts) else "FAIL"

        return HistoricalEpssEvidenceSummaryV1(
            archive_commit=APPROVED_ARCHIVE_COMMIT,
            plan_id=plan.plan_id,
            expected_snapshots=plan.candidate_count,
            bronze_sources=len(expected_bronze_sources & bronze_keys),
            bronze_manifests=len(expected_bronze_manifests & bronze_keys),
            silver_objects=len(expected_silver & current_historical_silver),
            completion_manifests=len(expected_completion & completion_keys),
            missing_expected=missing_expected,
            unexpected_historical=unexpected_historical,
            provenance_failures=counters.provenance_failures,
            hash_failures=counters.hash_failures,
            version_authority_failures=counters.version_authority_failures,
            completion_authority_failures=counters.completion_authority_failures,
            source_absent_dates_checked=len(plan.source_absent_dates),
            source_absent_artifacts_found=source_absent_artifacts_found,
            first_historical_date=plan.work_items[0].snapshot_date.isoformat(),
            last_historical_date=plan.work_items[-1].snapshot_date.isoformat(),
            boundary=plan.first_forward_snapshot_date.isoformat(),
            boundary_violations=boundary_violations,
            canary_dates_checked=len(CANARY_DATES),
            canary_divergent_versions=counters.canary_divergent_versions,
            era_v1=era_counts[EpssModelEra.V1],
            era_v2=era_counts[EpssModelEra.V2],
            era_v3=era_counts[EpssModelEra.V3],
            era_v4=era_counts[EpssModelEra.V4],
            era_v5=era_counts[EpssModelEra.V5],
            result=result,
        )

    def _verify_item(
        self,
        *,
        work_item: HistoricalEpssWorkItemV1,
        keys: dict[str, str],
        counters: _EvidenceCounters,
        expected_payload_sha256: dict[str, str],
    ) -> None:
        """Verify one complete snapshot evidence chain from Bronze through completion."""
        try:
            manifest_object = self._evidence_store.read_current(key=keys["manifest"])
            manifest = self._manifest_parser.parse(
                HistoricalEpssBronzeObjectPayloadV1(
                    key=manifest_object.key,
                    version_id=manifest_object.version_id,
                    raw_bytes=manifest_object.raw_bytes,
                )
            )
            self._validate_manifest_work_item(manifest=manifest, work_item=work_item)
        except (KeyError, ValueError):
            counters.provenance_failures += 1
            return

        try:
            source_current = self._evidence_store.read_current(key=keys["source"])
            if source_current.version_id != manifest.source_object_version_id:
                counters.version_authority_failures += 1
            source_object = self._evidence_store.read_version(
                key=keys["source"],
                version_id=manifest.source_object_version_id,
            )
            if source_object.version_id != manifest.source_object_version_id:
                raise ValueError(
                    "Historical EPSS source exact read returned a different VersionId."
                )
            snapshot = self._snapshot_parser.parse(
                source_object.raw_bytes,
                snapshot_date=work_item.snapshot_date,
            )
            if (
                source_object.sha256 != manifest.source_sha256
                or source_object.sha256 != snapshot.sha256
                or len(source_object.raw_bytes) != work_item.compressed_size_bytes
                or _git_blob_sha1(source_object.raw_bytes) != work_item.archive_git_blob_sha1
            ):
                counters.hash_failures += 1
                return
        except KeyError:
            counters.version_authority_failures += 1
            return
        except ValueError:
            counters.hash_failures += 1
            return

        canonical_manifest = _canonical_manifest_bytes(
            work_item=work_item,
            snapshot_sha256=snapshot.sha256,
            source_metadata_present=snapshot.source_metadata_present,
            source_version_id=manifest.source_object_version_id,
        )
        if manifest_object.raw_bytes != canonical_manifest:
            counters.provenance_failures += 1
            return

        bronze = HistoricalEpssBronzeEvidenceV1(
            manifest=manifest,
            source=HistoricalEpssBronzeObjectPayloadV1(
                key=source_object.key,
                version_id=source_object.version_id,
                raw_bytes=source_object.raw_bytes,
            ),
        )
        try:
            prepared = self._silver_preparer.execute(bronze)
        except ValueError:
            counters.provenance_failures += 1
            return
        if prepared.key != keys["silver"]:
            counters.provenance_failures += 1
            return

        try:
            silver_object = self._evidence_store.read_current(key=keys["silver"])
        except KeyError:
            counters.version_authority_failures += 1
            return
        if (
            silver_object.raw_bytes != prepared.artifact.parquet_bytes
            or silver_object.sha256 != prepared.artifact.parquet_sha256
        ):
            counters.hash_failures += 1
            return

        stored_silver = HistoricalEpssSilverStoredObjectV1(
            key=silver_object.key,
            version_id=silver_object.version_id,
            parquet_sha256=silver_object.sha256,
            size_bytes=len(silver_object.raw_bytes),
            row_count=prepared.artifact.row_count,
            schema_version=prepared.artifact.schema_version,
        )
        silver_result = HistoricalEpssSilverPersistenceResultV1(
            stored_object=stored_silver,
            replay_status=HistoricalEpssSilverReplayStatus.CREATED,
        )
        expected_completion = self._completion_factory.build(
            bronze=bronze,
            silver=silver_result,
        )
        if expected_completion.key != keys["completion"]:
            counters.completion_authority_failures += 1
            return

        try:
            completion_object = self._evidence_store.read_current(key=keys["completion"])
        except KeyError:
            counters.completion_authority_failures += 1
            return
        if completion_object.raw_bytes != expected_completion.raw_bytes:
            counters.completion_authority_failures += 1
            return

        expected_payload_sha256.update(
            {
                source_object.key: source_object.sha256,
                manifest_object.key: manifest_object.sha256,
                silver_object.key: silver_object.sha256,
                completion_object.key: completion_object.sha256,
            }
        )

    def _verify_canary_versions(
        self,
        *,
        plan: HistoricalEpssBootstrapPlanV1,
        expected_payload_sha256: dict[str, str],
        counters: _EvidenceCounters,
    ) -> None:
        """Require every retained canary version to match the verified current payload."""
        by_date = {item.snapshot_date: item for item in plan.work_items}
        for snapshot_date in CANARY_DATES:
            work_item = by_date.get(snapshot_date)
            if work_item is None:
                counters.provenance_failures += 1
                continue
            keys = _keys_for_item(work_item, silver_key_factory=self._silver_key_factory)
            for key in keys.values():
                expected_sha256 = expected_payload_sha256.get(key)
                if expected_sha256 is None:
                    continue
                try:
                    current = self._evidence_store.read_current(key=key)
                    versions = self._evidence_store.list_versions(key=key)
                except KeyError:
                    counters.version_authority_failures += 1
                    continue
                if not any(
                    version.version_id == current.version_id and version.is_latest
                    for version in versions
                ):
                    counters.version_authority_failures += 1
                for version in versions:
                    try:
                        observed = self._evidence_store.read_version(
                            key=key,
                            version_id=version.version_id,
                        )
                    except KeyError:
                        counters.version_authority_failures += 1
                        continue
                    if observed.sha256 != expected_sha256:
                        counters.canary_divergent_versions += 1

    @staticmethod
    def _expected_keys(plan: HistoricalEpssBootstrapPlanV1) -> dict[str, set[str]]:
        """Build exact current-object inventories from the frozen worklist."""
        silver_key_factory = EpssSilverKeyFactory(prefix="silver/epss")
        expected: dict[str, set[str]] = {
            "bronze_sources": set(),
            "bronze_manifests": set(),
            "silver": set(),
            "completion": set(),
        }
        for item in plan.work_items:
            keys = _keys_for_item(item, silver_key_factory=silver_key_factory)
            expected["bronze_sources"].add(keys["source"])
            expected["bronze_manifests"].add(keys["manifest"])
            expected["silver"].add(keys["silver"])
            expected["completion"].add(keys["completion"])
        return expected

    @staticmethod
    def _validate_manifest_work_item(
        *,
        manifest: HistoricalEpssBronzeManifestV1,
        work_item: HistoricalEpssWorkItemV1,
    ) -> None:
        """Validate manifest provenance against one frozen work item."""
        if (
            manifest.snapshot_date != work_item.snapshot_date
            or manifest.archive_repository != ARCHIVE_REPOSITORY
            or manifest.archive_commit != APPROVED_ARCHIVE_COMMIT
            or manifest.archive_path != work_item.archive_path
            or manifest.archive_git_blob_sha1 != work_item.archive_git_blob_sha1
            or manifest.compressed_size_bytes != work_item.compressed_size_bytes
            or manifest.model_era is not work_item.model_era
        ):
            raise ValueError("Historical EPSS Bronze manifest disagrees with frozen work item.")

    @staticmethod
    def _source_absent_artifacts_found(
        *,
        plan: HistoricalEpssBootstrapPlanV1,
        bronze_keys: set[str],
        silver_keys: set[str],
        completion_keys: set[str],
    ) -> int:
        """Count any persisted artifact for the nine source-absent dates."""
        absent = set(plan.source_absent_dates)
        found = 0
        for key in bronze_keys:
            snapshot_date = _bronze_snapshot_date(key)
            if snapshot_date in absent:
                found += 1
        for key in completion_keys:
            snapshot_date = _completion_snapshot_date(key)
            if snapshot_date in absent:
                found += 1
        for key in silver_keys:
            snapshot_date = _silver_snapshot_date(key)
            if snapshot_date in absent:
                found += 1
        return found


def _keys_for_item(
    work_item: HistoricalEpssWorkItemV1,
    *,
    silver_key_factory: EpssSilverKeyFactory,
) -> dict[str, str]:
    """Return the four deterministic evidence keys for one historical snapshot."""
    snapshot_date = work_item.snapshot_date.isoformat()
    bronze_prefix = (
        "bronze/epss-history/schema_version=1/"
        f"archive_commit={APPROVED_ARCHIVE_COMMIT}/snapshot_date={snapshot_date}"
    )
    completion_key = (
        "silver/epss-history/completions/schema_version=1/"
        f"archive_commit={APPROVED_ARCHIVE_COMMIT}/snapshot_date={snapshot_date}/manifest.json"
    )
    return {
        "source": f"{bronze_prefix}/epss_scores.csv.gz",
        "manifest": f"{bronze_prefix}/manifest.json",
        "silver": silver_key_factory.build(work_item.snapshot_date),
        "completion": completion_key,
    }


def _canonical_manifest_bytes(
    *,
    work_item: HistoricalEpssWorkItemV1,
    snapshot_sha256: str,
    source_metadata_present: bool,
    source_version_id: str,
) -> bytes:
    """Rebuild the canonical historical Bronze manifest bytes without mutation."""
    keys = _keys_for_item(work_item, silver_key_factory=EpssSilverKeyFactory(prefix="silver/epss"))
    document = {
        "archive_commit": APPROVED_ARCHIVE_COMMIT,
        "archive_git_blob_sha1": work_item.archive_git_blob_sha1,
        "archive_path": work_item.archive_path,
        "archive_repository": ARCHIVE_REPOSITORY,
        "compressed_size_bytes": work_item.compressed_size_bytes,
        "model_era": work_item.model_era.value,
        "schema_version": 1,
        "snapshot_date": work_item.snapshot_date.isoformat(),
        "source_metadata_present": source_metadata_present,
        "source_object_key": keys["source"],
        "source_object_version_id": source_version_id,
        "source_sha256": snapshot_sha256,
    }
    text = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return f"{text}\n".encode()


def _git_blob_sha1(payload: bytes) -> str:
    """Return the Git blob SHA-1 identity for exact source bytes."""
    return hashlib.sha1(
        f"blob {len(payload)}\0".encode() + payload,
        usedforsecurity=False,
    ).hexdigest()


def _parse_key_date(pattern: re.Pattern[str], key: str) -> date | None:
    """Extract a canonical snapshot date from one supported object key."""
    match = pattern.match(key)
    if match is None:
        return None
    try:
        snapshot_date = date.fromisoformat(match.group(1))
    except ValueError:
        return None
    return snapshot_date if snapshot_date.isoformat() == match.group(1) else None


def _bronze_snapshot_date(key: str) -> date | None:
    return _parse_key_date(_BRONZE_DATE_RE, key)


def _completion_snapshot_date(key: str) -> date | None:
    return _parse_key_date(_COMPLETION_DATE_RE, key)


def _silver_snapshot_date(key: str) -> date | None:
    return _parse_key_date(_SILVER_KEY_RE, key)


def _boundary_violations(
    *,
    bronze_keys: set[str],
    completion_keys: set[str],
    boundary: date,
) -> int:
    """Count historical-only objects that overlap the forward authority boundary."""
    bronze_violations = sum(
        snapshot_date >= boundary
        for key in bronze_keys
        if (snapshot_date := _bronze_snapshot_date(key)) is not None
    )
    completion_violations = sum(
        snapshot_date >= boundary
        for key in completion_keys
        if (snapshot_date := _completion_snapshot_date(key)) is not None
    )
    return bronze_violations + completion_violations
