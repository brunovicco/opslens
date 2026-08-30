"""Strict explicit invocation composition for historical EPSS transformation."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from opslens.transformation.epss.history.completion import (
    HistoricalEpssCompletionArtifactV1,
    HistoricalEpssCompletionPersistenceResultV1,
)
from opslens.transformation.epss.history.models import (
    HistoricalEpssBronzeEvidenceV1,
    HistoricalEpssSilverArtifactV1,
    HistoricalEpssSilverPersistenceResultV1,
)
from opslens.transformation.epss.history.preparation import HistoricalEpssPreparedSilverV1

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_MANIFEST_KEY_RE = re.compile(
    r"^bronze/epss-history/schema_version=1/"
    r"archive_commit=(?P<commit>[0-9a-f]{40})/"
    r"snapshot_date=(?P<snapshot_date>\d{4}-\d{2}-\d{2})/manifest\.json$"
)
_REQUIRED_EVENT_KEYS = frozenset(
    {"schema_version", "bronze_manifest_key", "bronze_manifest_version_id"}
)


@dataclass(frozen=True, slots=True)
class HistoricalEpssInvocationV1:
    """Represent the only authority-bearing coordinates accepted by C5."""

    bronze_manifest_key: str
    bronze_manifest_version_id: str
    snapshot_date: date
    archive_commit: str


@dataclass(frozen=True, slots=True)
class HistoricalEpssInvocationResultV1:
    """Describe one completed explicit historical transformation invocation."""

    snapshot_date: date
    silver: HistoricalEpssSilverPersistenceResultV1
    completion: HistoricalEpssCompletionPersistenceResultV1


class HistoricalEpssBronzeEvidenceReader(Protocol):
    """Read one exact historical Bronze evidence pair."""

    def execute(
        self,
        *,
        manifest_key: str,
        manifest_version_id: str,
    ) -> HistoricalEpssBronzeEvidenceV1:
        """Return exact manifest and source evidence."""
        ...


class HistoricalEpssSilverPreparer(Protocol):
    """Prepare deterministic Silver from verified Bronze evidence."""

    def execute(
        self,
        evidence: HistoricalEpssBronzeEvidenceV1,
    ) -> HistoricalEpssPreparedSilverV1:
        """Return exact deterministic Parquet and key."""
        ...


class HistoricalEpssSilverPersister(Protocol):
    """Persist or replay-verify deterministic historical Silver."""

    def execute(
        self,
        *,
        key: str,
        artifact: HistoricalEpssSilverArtifactV1,
    ) -> HistoricalEpssSilverPersistenceResultV1:
        """Return exact persisted Silver evidence."""
        ...


class HistoricalEpssCompletionFactory(Protocol):
    """Build deterministic completion evidence."""

    def build(
        self,
        *,
        bronze: HistoricalEpssBronzeEvidenceV1,
        silver: HistoricalEpssSilverPersistenceResultV1,
    ) -> HistoricalEpssCompletionArtifactV1:
        """Bind exact Bronze and Silver evidence."""
        ...


class HistoricalEpssCompletionPersister(Protocol):
    """Persist completion evidence last."""

    def execute(
        self,
        artifact: HistoricalEpssCompletionArtifactV1,
    ) -> HistoricalEpssCompletionPersistenceResultV1:
        """Return exact persisted completion evidence."""
        ...


class HistoricalEpssInvocationParserV1:
    """Reject implicit, partial, or scope-changing historical invocations."""

    SCHEMA_VERSION = "1"

    def __init__(self, *, approved_archive_commit: str) -> None:
        """Initialize the exact approved archive revision."""
        normalized = approved_archive_commit.strip()
        if _COMMIT_RE.fullmatch(normalized) is None:
            raise ValueError("Approved historical EPSS archive commit must be a 40-char Git SHA.")
        self._approved_archive_commit = normalized

    def parse(self, event: Mapping[str, object]) -> HistoricalEpssInvocationV1:
        """Parse an exact one-snapshot explicit invocation contract."""
        keys = frozenset(event)
        if keys != _REQUIRED_EVENT_KEYS:
            missing = sorted(_REQUIRED_EVENT_KEYS - keys)
            extra = sorted(keys - _REQUIRED_EVENT_KEYS)
            raise ValueError(
                "Historical EPSS invocation keys do not match schema v1: "
                f"missing={missing}, extra={extra}."
            )

        schema_version = event["schema_version"]
        if schema_version != self.SCHEMA_VERSION:
            raise ValueError("Historical EPSS invocation schema_version must be string '1'.")

        manifest_key = self._required_string(event, "bronze_manifest_key")
        manifest_version_id = self._required_string(event, "bronze_manifest_version_id")
        match = _MANIFEST_KEY_RE.fullmatch(manifest_key)

        if match is None:
            raise ValueError(
                "Historical EPSS invocation manifest key is outside the exact history namespace."
            )

        archive_commit = match.group("commit")
        if archive_commit != self._approved_archive_commit:
            raise ValueError(
                "Historical EPSS invocation archive commit is not the approved pinned revision."
            )

        raw_snapshot_date = match.group("snapshot_date")
        try:
            snapshot_date = date.fromisoformat(raw_snapshot_date)
        except ValueError as exc:
            raise ValueError("Historical EPSS invocation snapshot date is invalid.") from exc

        if snapshot_date.isoformat() != raw_snapshot_date:
            raise ValueError("Historical EPSS invocation snapshot date must be canonical.")

        return HistoricalEpssInvocationV1(
            bronze_manifest_key=manifest_key,
            bronze_manifest_version_id=manifest_version_id,
            snapshot_date=snapshot_date,
            archive_commit=archive_commit,
        )

    @staticmethod
    def _required_string(event: Mapping[str, object], key: str) -> str:
        """Return one exact non-empty invocation string."""
        value = event[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Historical EPSS invocation {key} must be a non-empty string.")
        return value


class ExecuteHistoricalEpssInvocationV1:
    """Compose exact Bronze read, Silver persistence, then completion written last."""

    def __init__(
        self,
        *,
        parser: HistoricalEpssInvocationParserV1,
        bronze_reader: HistoricalEpssBronzeEvidenceReader,
        silver_preparer: HistoricalEpssSilverPreparer,
        silver_persistence: HistoricalEpssSilverPersister,
        completion_factory: HistoricalEpssCompletionFactory,
        completion_persistence: HistoricalEpssCompletionPersister,
        first_forward_snapshot_date: date,
    ) -> None:
        """Initialize strict one-snapshot historical composition dependencies."""
        self._parser = parser
        self._bronze_reader = bronze_reader
        self._silver_preparer = silver_preparer
        self._silver_persistence = silver_persistence
        self._completion_factory = completion_factory
        self._completion_persistence = completion_persistence
        self._first_forward_snapshot_date = first_forward_snapshot_date

    def execute(self, event: Mapping[str, object]) -> HistoricalEpssInvocationResultV1:
        """Execute one historical snapshot without implicit fan-out."""
        invocation = self._parser.parse(event)

        if invocation.snapshot_date >= self._first_forward_snapshot_date:
            raise ValueError(
                "Historical EPSS invocation overlaps forward-authority snapshot range."
            )

        bronze = self._bronze_reader.execute(
            manifest_key=invocation.bronze_manifest_key,
            manifest_version_id=invocation.bronze_manifest_version_id,
        )

        if bronze.manifest.snapshot_date != invocation.snapshot_date:
            raise ValueError(
                "Historical EPSS invocation snapshot_date does not match Bronze manifest."
            )
        if bronze.manifest.archive_commit != invocation.archive_commit:
            raise ValueError(
                "Historical EPSS invocation archive commit does not match Bronze manifest."
            )

        prepared = self._silver_preparer.execute(bronze)
        silver = self._silver_persistence.execute(
            key=prepared.key,
            artifact=prepared.artifact,
        )

        completion_artifact = self._completion_factory.build(
            bronze=bronze,
            silver=silver,
        )
        completion = self._completion_persistence.execute(completion_artifact)

        return HistoricalEpssInvocationResultV1(
            snapshot_date=invocation.snapshot_date,
            silver=silver,
            completion=completion,
        )
