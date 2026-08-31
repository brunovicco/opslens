"""Deterministic historical EPSS Silver completion evidence."""

import json
import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

from opslens.transformation.epss.application.key_factory import EpssSilverKeyFactory
from opslens.transformation.epss.history.models import (
    HistoricalEpssBronzeEvidenceV1,
    HistoricalEpssSilverPersistenceResultV1,
)

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class HistoricalEpssCompletionManifestV1:
    """Represent COMPLETE evidence for one historical EPSS snapshot."""

    snapshot_date: date
    archive_commit: str
    bronze_manifest_key: str
    bronze_manifest_version_id: str
    source_object_key: str
    source_object_version_id: str
    source_sha256: str
    silver_key: str
    silver_version_id: str
    silver_sha256: str
    silver_schema_version: int
    row_count: int
    replay_status: str

    def __post_init__(self) -> None:
        """Validate exact completion evidence coordinates."""
        if _COMMIT_RE.fullmatch(self.archive_commit) is None:
            raise ValueError("Historical EPSS completion archive_commit is invalid.")
        for value, name in (
            (self.bronze_manifest_key, "bronze_manifest_key"),
            (self.bronze_manifest_version_id, "bronze_manifest_version_id"),
            (self.source_object_key, "source_object_key"),
            (self.source_object_version_id, "source_object_version_id"),
            (self.silver_key, "silver_key"),
            (self.silver_version_id, "silver_version_id"),
            (self.replay_status, "replay_status"),
        ):
            if not value.strip():
                raise ValueError(f"Historical EPSS completion {name} cannot be empty.")
        if _SHA256_RE.fullmatch(self.source_sha256) is None:
            raise ValueError("Historical EPSS completion source SHA-256 is invalid.")
        if _SHA256_RE.fullmatch(self.silver_sha256) is None:
            raise ValueError("Historical EPSS completion Silver SHA-256 is invalid.")
        if self.silver_schema_version <= 0:
            raise ValueError("Historical EPSS completion Silver schema version must be positive.")
        if self.row_count <= 0:
            raise ValueError("Historical EPSS completion row_count must be positive.")


@dataclass(frozen=True, slots=True)
class HistoricalEpssCompletionArtifactV1:
    """Represent deterministic completion manifest bytes and destination key."""

    manifest: HistoricalEpssCompletionManifestV1
    key: str
    raw_bytes: bytes
    sha256: str

    def __post_init__(self) -> None:
        """Validate completion artifact integrity."""
        if not self.key.strip():
            raise ValueError("Historical EPSS completion key cannot be empty.")
        if not self.raw_bytes:
            raise ValueError("Historical EPSS completion bytes cannot be empty.")
        if self.sha256 != sha256(self.raw_bytes).hexdigest():
            raise ValueError("Historical EPSS completion SHA-256 does not match bytes.")

    @property
    def size_bytes(self) -> int:
        """Return exact completion manifest byte size."""
        return len(self.raw_bytes)


@dataclass(frozen=True, slots=True)
class HistoricalEpssCompletionStoredObjectV1:
    """Represent exact persisted completion-manifest evidence."""

    key: str
    version_id: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        """Validate persisted completion evidence."""
        if not self.key.strip():
            raise ValueError("Historical EPSS completion stored key cannot be empty.")
        if not self.version_id.strip():
            raise ValueError("Historical EPSS completion VersionId cannot be empty.")
        if _SHA256_RE.fullmatch(self.sha256) is None:
            raise ValueError("Historical EPSS completion stored SHA-256 is invalid.")
        if self.size_bytes <= 0:
            raise ValueError("Historical EPSS completion stored size must be positive.")


class HistoricalEpssCompletionReplayStatus(StrEnum):
    """Describe how immutable completion persistence succeeded."""

    CREATED = "created"
    REPLAY_VERIFIED = "replay_verified"


@dataclass(frozen=True, slots=True)
class HistoricalEpssCompletionPersistenceResultV1:
    """Bind exact completion persistence evidence to replay outcome."""

    stored_object: HistoricalEpssCompletionStoredObjectV1
    replay_status: HistoricalEpssCompletionReplayStatus


class HistoricalEpssCompletionManifestFactoryV1:
    """Build deterministic COMPLETE bytes only from verified Bronze and Silver evidence."""

    SCHEMA_VERSION = 1
    PREFIX = "silver/epss-history/completions"

    def __init__(self, *, silver_key_factory: EpssSilverKeyFactory | None = None) -> None:
        """Initialize deterministic key validation dependency."""
        self._silver_key_factory = silver_key_factory or EpssSilverKeyFactory()

    def build(
        self,
        *,
        bronze: HistoricalEpssBronzeEvidenceV1,
        silver: HistoricalEpssSilverPersistenceResultV1,
    ) -> HistoricalEpssCompletionArtifactV1:
        """Bind one exact Bronze observation to its exact persisted Silver output."""
        manifest = bronze.manifest
        stored = silver.stored_object
        expected_silver_key = self._silver_key_factory.build(manifest.snapshot_date)

        if stored.key != expected_silver_key:
            raise ValueError(
                "Historical EPSS completion Silver key does not match snapshot_date."
            )

        completion = HistoricalEpssCompletionManifestV1(
            snapshot_date=manifest.snapshot_date,
            archive_commit=manifest.archive_commit,
            bronze_manifest_key=manifest.manifest_key,
            bronze_manifest_version_id=manifest.manifest_version_id,
            source_object_key=manifest.source_object_key,
            source_object_version_id=manifest.source_object_version_id,
            source_sha256=manifest.source_sha256,
            silver_key=stored.key,
            silver_version_id=stored.version_id,
            silver_sha256=stored.parquet_sha256,
            silver_schema_version=stored.schema_version,
            row_count=stored.row_count,
            replay_status=silver.replay_status.value,
        )

        document = {
            "archive_commit": completion.archive_commit,
            "bronze_manifest_key": completion.bronze_manifest_key,
            "bronze_manifest_version_id": completion.bronze_manifest_version_id,
            "replay_status": completion.replay_status,
            "row_count": completion.row_count,
            "schema_version": self.SCHEMA_VERSION,
            "silver_key": completion.silver_key,
            "silver_schema_version": completion.silver_schema_version,
            "silver_sha256": completion.silver_sha256,
            "silver_version_id": completion.silver_version_id,
            "snapshot_date": completion.snapshot_date.isoformat(),
            "source_object_key": completion.source_object_key,
            "source_object_version_id": completion.source_object_version_id,
            "source_sha256": completion.source_sha256,
        }
        text = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        raw_bytes = f"{text}\n".encode()
        key = (
            f"{self.PREFIX}/schema_version={self.SCHEMA_VERSION}/"
            f"archive_commit={completion.archive_commit}/"
            f"snapshot_date={completion.snapshot_date.isoformat()}/manifest.json"
        )

        return HistoricalEpssCompletionArtifactV1(
            manifest=completion,
            key=key,
            raw_bytes=raw_bytes,
            sha256=sha256(raw_bytes).hexdigest(),
        )


class HistoricalEpssCompletionAlreadyExistsError(RuntimeError):
    """Signal that completion exists and requires exact replay verification."""


class HistoricalEpssCompletionRepository(Protocol):
    """Persist one immutable completion manifest."""

    def put_if_absent(
        self,
        *,
        artifact: HistoricalEpssCompletionArtifactV1,
    ) -> HistoricalEpssCompletionStoredObjectV1:
        """Create completion or require exact replay verification."""
        ...


class HistoricalEpssCompletionReplayVerifier(Protocol):
    """Verify one existing immutable completion manifest."""

    def verify_current(
        self,
        *,
        artifact: HistoricalEpssCompletionArtifactV1,
    ) -> HistoricalEpssCompletionStoredObjectV1:
        """Verify exact current completion bytes."""
        ...


class PersistHistoricalEpssCompletion:
    """Persist completion last, accepting replay only after exact verification."""

    def __init__(
        self,
        *,
        repository: HistoricalEpssCompletionRepository,
        replay_verifier: HistoricalEpssCompletionReplayVerifier,
    ) -> None:
        """Initialize exact completion persistence dependencies."""
        self._repository = repository
        self._replay_verifier = replay_verifier

    def execute(
        self,
        artifact: HistoricalEpssCompletionArtifactV1,
    ) -> HistoricalEpssCompletionPersistenceResultV1:
        """Persist deterministic completion bytes or verify an existing exact replay."""
        try:
            stored = self._repository.put_if_absent(artifact=artifact)
            replay_status = HistoricalEpssCompletionReplayStatus.CREATED
        except HistoricalEpssCompletionAlreadyExistsError:
            stored = self._replay_verifier.verify_current(artifact=artifact)
            replay_status = HistoricalEpssCompletionReplayStatus.REPLAY_VERIFIED

        if stored.key != artifact.key:
            raise ValueError("Historical EPSS completion stored key does not match artifact.")
        if stored.sha256 != artifact.sha256:
            raise ValueError("Historical EPSS completion stored SHA-256 does not match artifact.")
        if stored.size_bytes != artifact.size_bytes:
            raise ValueError("Historical EPSS completion stored size does not match artifact.")

        return HistoricalEpssCompletionPersistenceResultV1(
            stored_object=stored,
            replay_status=replay_status,
        )
