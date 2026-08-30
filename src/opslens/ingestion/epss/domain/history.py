"""Historical FIRST EPSS source models and compatibility parser."""

import csv
import gzip
import hashlib
import io
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from opslens.ingestion.epss.domain.errors import InvalidEpssSnapshotError
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser


class EpssModelEra(StrEnum):
    """Represent documented production EPSS model eras."""

    V1 = "v1"
    V2 = "v2"
    V3 = "v3"
    V4 = "v4"
    V5 = "v5"

    @classmethod
    def for_snapshot_date(cls, snapshot_date: date) -> "EpssModelEra":
        """Resolve the documented EPSS model era for one archive date."""
        if snapshot_date < date(2021, 4, 14):
            raise InvalidEpssSnapshotError(
                "Historical EPSS snapshots are unavailable before 2021-04-14."
            )
        if snapshot_date < date(2022, 2, 4):
            return cls.V1
        if snapshot_date < date(2023, 3, 7):
            return cls.V2
        if snapshot_date < date(2025, 3, 17):
            return cls.V3
        if snapshot_date < date(2026, 6, 15):
            return cls.V4
        return cls.V5

    @property
    def expected_source_model_version(self) -> str | None:
        """Return source-declared version expected for this documented era."""
        return {
            EpssModelEra.V1: None,
            EpssModelEra.V2: "v2022.01.01",
            EpssModelEra.V3: "v2023.03.01",
            EpssModelEra.V4: "v2025.03.14",
            EpssModelEra.V5: "v2026.06.15",
        }[self]


class EpssHistoricalSourceShape(StrEnum):
    """Represent physical CSV shapes observed in the pinned EPSS archive."""

    LEGACY_TWO_COLUMN = "legacy_two_column"
    LEGACY_THREE_COLUMN = "legacy_three_column"
    MODERN_METADATA = "modern_metadata"


@dataclass(frozen=True, slots=True)
class HistoricalEpssSnapshot:
    """Represent one validated historical EPSS archive snapshot.

    Source-declared metadata remains nullable because EPSS v1 files do not
    contain the modern metadata comment. Early v1 files also omit percentile,
    while later pre-v2 files can physically contain a percentile column.
    """

    raw_bytes: bytes
    snapshot_date: date
    model_era: EpssModelEra
    source_shape: EpssHistoricalSourceShape
    source_metadata_present: bool
    model_version: str | None
    score_timestamp: datetime | None
    sha256: str
    row_count: int
    percentile_available: bool

    def __post_init__(self) -> None:
        """Validate invariants shared by every historical source shape."""
        if not self.raw_bytes:
            raise ValueError("Historical EPSS payload cannot be empty.")
        if len(self.sha256) != 64:
            raise ValueError("Historical EPSS SHA-256 must contain 64 characters.")
        if self.row_count <= 0:
            raise ValueError("Historical EPSS snapshot must contain data rows.")

        if self.source_metadata_present:
            if self.model_version is None or not self.model_version.strip():
                raise ValueError("Source metadata requires a model version.")
            if self.score_timestamp is None or self.score_timestamp.tzinfo is None:
                raise ValueError("Source metadata requires a timezone-aware score timestamp.")
            if self.score_timestamp.date() != self.snapshot_date:
                raise ValueError("Source score timestamp must match the archive snapshot date.")
        elif self.model_version is not None or self.score_timestamp is not None:
            raise ValueError(
                "Metadata-absent historical snapshots cannot contain fabricated source metadata."
            )

        if self.model_era is EpssModelEra.V1:
            if self.source_metadata_present:
                raise ValueError("EPSS v1 must not claim modern source metadata.")
            if self.source_shape is EpssHistoricalSourceShape.MODERN_METADATA:
                raise ValueError("EPSS v1 cannot use the modern metadata source shape.")
            expected_percentile = (
                self.source_shape is EpssHistoricalSourceShape.LEGACY_THREE_COLUMN
            )
            if self.percentile_available is not expected_percentile:
                raise ValueError(
                    "EPSS v1 percentile availability must match the physical source header."
                )
        else:
            if self.source_shape is not EpssHistoricalSourceShape.MODERN_METADATA:
                raise ValueError("EPSS v2+ snapshots require the modern metadata source shape.")
            if not self.source_metadata_present or not self.percentile_available:
                raise ValueError("Modern EPSS snapshots require metadata and percentile values.")


class HistoricalEpssSnapshotParser:
    """Parse immutable EPSS archive bytes across legacy and modern shapes."""

    LEGACY_TWO_COLUMN_HEADER = ("cve", "epss")
    LEGACY_THREE_COLUMN_HEADER = ("cve", "epss", "percentile")

    def __init__(self, modern_parser: EpssSnapshotParser | None = None) -> None:
        """Initialize with the proven current-snapshot parser for v2+ files."""
        self._modern_parser = modern_parser or EpssSnapshotParser()

    def parse(self, payload: bytes, *, snapshot_date: date) -> HistoricalEpssSnapshot:
        """Parse one historical archive artifact using its immutable date coordinate."""
        if not payload:
            raise InvalidEpssSnapshotError("Historical EPSS snapshot payload is empty.")

        model_era = EpssModelEra.for_snapshot_date(snapshot_date)

        if model_era is EpssModelEra.V1:
            return self._parse_v1(payload=payload, snapshot_date=snapshot_date)

        snapshot = self._modern_parser.parse(payload)

        if snapshot.snapshot_date != snapshot_date.isoformat():
            raise InvalidEpssSnapshotError(
                "Historical EPSS source score_date does not match the archive snapshot date: "
                f"source={snapshot.snapshot_date}, archive={snapshot_date.isoformat()}."
            )

        expected_model_version = model_era.expected_source_model_version
        if snapshot.model_version != expected_model_version:
            raise InvalidEpssSnapshotError(
                "Historical EPSS model version does not match the documented model era: "
                f"expected={expected_model_version!r}, received={snapshot.model_version!r}."
            )

        return HistoricalEpssSnapshot(
            raw_bytes=payload,
            snapshot_date=snapshot_date,
            model_era=model_era,
            source_shape=EpssHistoricalSourceShape.MODERN_METADATA,
            source_metadata_present=True,
            model_version=snapshot.model_version,
            score_timestamp=snapshot.score_timestamp,
            sha256=snapshot.sha256,
            row_count=snapshot.row_count,
            percentile_available=True,
        )

    @classmethod
    def _parse_v1(cls, *, payload: bytes, snapshot_date: date) -> HistoricalEpssSnapshot:
        """Parse an observed metadata-free EPSS v1 physical source contract."""
        try:
            decompressed = gzip.decompress(payload)
        except (gzip.BadGzipFile, EOFError, OSError) as exc:
            raise InvalidEpssSnapshotError(
                "Historical EPSS v1 snapshot is not a valid gzip artifact."
            ) from exc

        try:
            text_stream = io.StringIO(decompressed.decode("utf-8"), newline="")
        except UnicodeDecodeError as exc:
            raise InvalidEpssSnapshotError(
                "Historical EPSS v1 snapshot is not valid UTF-8."
            ) from exc

        reader = csv.reader(text_stream)
        header = next(reader, None)
        header_tuple = tuple(header or ())

        if header_tuple == cls.LEGACY_TWO_COLUMN_HEADER:
            source_shape = EpssHistoricalSourceShape.LEGACY_TWO_COLUMN
            percentile_available = False
        elif header_tuple == cls.LEGACY_THREE_COLUMN_HEADER:
            source_shape = EpssHistoricalSourceShape.LEGACY_THREE_COLUMN
            percentile_available = True
        else:
            raise InvalidEpssSnapshotError(
                "Unexpected historical EPSS v1 CSV header. Expected one of "
                f"{cls.LEGACY_TWO_COLUMN_HEADER!r} or "
                f"{cls.LEGACY_THREE_COLUMN_HEADER!r}, received {header_tuple!r}."
            )

        row_count = 0
        expected_columns = len(header_tuple)

        try:
            for line_number, row in enumerate(reader, start=2):
                if not row or all(not value.strip() for value in row):
                    continue
                if len(row) != expected_columns:
                    raise InvalidEpssSnapshotError(
                        f"Malformed historical EPSS v1 row at line {line_number}: "
                        f"expected exactly {expected_columns} columns."
                    )
                row_count += 1
        except csv.Error as exc:
            raise InvalidEpssSnapshotError(
                "Historical EPSS v1 snapshot contains malformed CSV."
            ) from exc

        if row_count <= 0:
            raise InvalidEpssSnapshotError(
                "Historical EPSS v1 snapshot does not contain data rows."
            )

        return HistoricalEpssSnapshot(
            raw_bytes=payload,
            snapshot_date=snapshot_date,
            model_era=EpssModelEra.V1,
            source_shape=source_shape,
            source_metadata_present=False,
            model_version=None,
            score_timestamp=None,
            sha256=hashlib.sha256(payload).hexdigest(),
            row_count=row_count,
            percentile_available=percentile_available,
        )
