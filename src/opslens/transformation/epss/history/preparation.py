"""Deterministic preparation of historical EPSS Silver Parquet artifacts."""

import csv
import gzip
import io
from dataclasses import dataclass
from io import BytesIO
from typing import Iterator

from opslens.ingestion.epss.domain.history import (
    EpssHistoricalSourceShape,
    HistoricalEpssSnapshot,
    HistoricalEpssSnapshotParser,
)
from opslens.transformation.epss.application.key_factory import EpssSilverKeyFactory
from opslens.transformation.epss.application.ports import SilverEpssRecordWriter
from opslens.transformation.epss.domain.errors import InvalidEpssSilverSourceError
from opslens.transformation.epss.domain.models import SilverEpssRecord
from opslens.transformation.epss.history.models import (
    HistoricalEpssBronzeEvidenceV1,
    HistoricalEpssSilverArtifactV1,
)


@dataclass(frozen=True, slots=True)
class HistoricalEpssPreparedSilverV1:
    """Bind one deterministic Silver key to exact prepared Parquet bytes."""

    key: str
    artifact: HistoricalEpssSilverArtifactV1

    def __post_init__(self) -> None:
        """Validate the deterministic destination coordinate."""
        if not self.key.strip():
            raise ValueError("Historical EPSS prepared Silver key cannot be empty.")


class HistoricalEpssSilverRecordTransformer:
    """Transform a validated historical EPSS snapshot into Silver v2 records."""

    SOURCE = "first-epss"
    LEGACY_TWO_COLUMN_HEADER = ("cve", "epss")
    LEGACY_THREE_COLUMN_HEADER = ("cve", "epss", "percentile")
    MODERN_HEADER = ("cve", "epss", "percentile")

    def iter_records(self, snapshot: HistoricalEpssSnapshot) -> Iterator[SilverEpssRecord]:
        """Yield exact historical Silver rows without fabricating unavailable values."""
        emitted_count = 0
        seen_cves: set[str] = set()

        try:
            with (
                gzip.GzipFile(fileobj=io.BytesIO(snapshot.raw_bytes), mode="rb") as gzip_stream,
                io.TextIOWrapper(gzip_stream, encoding="utf-8", newline="") as text_stream,
            ):
                reader = csv.reader(text_stream)
                header, first_data_line = self._consume_prefix(reader, snapshot)

                for line_number, row in enumerate(reader, start=first_data_line):
                    if not row or all(not value.strip() for value in row):
                        continue

                    record = self._build_record(
                        row=row,
                        header=header,
                        snapshot=snapshot,
                        line_number=line_number,
                    )

                    if record.cve in seen_cves:
                        raise InvalidEpssSilverSourceError(
                            f"Historical EPSS source contains duplicate CVE {record.cve!r} "
                            f"at source line {line_number}."
                        )

                    seen_cves.add(record.cve)
                    emitted_count += 1
                    yield record

        except InvalidEpssSilverSourceError:
            raise
        except (gzip.BadGzipFile, EOFError, OSError, UnicodeDecodeError, csv.Error) as exc:
            raise InvalidEpssSilverSourceError(
                "Historical EPSS source cannot be decoded as the validated gzip CSV shape."
            ) from exc

        if emitted_count != snapshot.row_count:
            raise InvalidEpssSilverSourceError(
                "Historical EPSS transformed row count does not match validated source evidence: "
                f"expected {snapshot.row_count}, emitted {emitted_count}."
            )

    def _consume_prefix(
        self,
        reader: Iterator[list[str]],
        snapshot: HistoricalEpssSnapshot,
    ) -> tuple[tuple[str, ...], int]:
        """Consume the exact prefix required by the validated historical source shape."""
        if snapshot.source_shape is EpssHistoricalSourceShape.MODERN_METADATA:
            metadata = next(reader, None)
            if not metadata or not metadata[0].startswith("#"):
                raise InvalidEpssSilverSourceError(
                    "Historical modern EPSS source is missing its validated metadata row."
                )
            header = tuple(next(reader, None) or ())
            expected = self.MODERN_HEADER
            first_data_line = 3
        else:
            header = tuple(next(reader, None) or ())
            expected = (
                self.LEGACY_TWO_COLUMN_HEADER
                if snapshot.source_shape is EpssHistoricalSourceShape.LEGACY_TWO_COLUMN
                else self.LEGACY_THREE_COLUMN_HEADER
            )
            first_data_line = 2

        if header != expected:
            raise InvalidEpssSilverSourceError(
                "Historical EPSS source header changed after validation: "
                f"expected {expected!r}, received {header!r}."
            )

        return header, first_data_line

    def _build_record(
        self,
        *,
        row: list[str],
        header: tuple[str, ...],
        snapshot: HistoricalEpssSnapshot,
        line_number: int,
    ) -> SilverEpssRecord:
        """Convert one source row into a validated nullable Silver v2 record."""
        if len(row) != len(header):
            raise InvalidEpssSilverSourceError(
                f"Malformed historical EPSS row at line {line_number}: "
                f"expected {len(header)} columns, received {len(row)}."
            )

        cve = row[0].strip()

        try:
            epss = float(row[1].strip())
            percentile = float(row[2].strip()) if len(header) == 3 else None
        except ValueError as exc:
            raise InvalidEpssSilverSourceError(
                f"Malformed historical EPSS numeric value at line {line_number}."
            ) from exc

        try:
            return SilverEpssRecord(
                cve=cve,
                epss=epss,
                percentile=percentile,
                model_version=snapshot.model_version,
                score_timestamp=snapshot.score_timestamp,
                source=self.SOURCE,
                source_sha256=snapshot.sha256,
                snapshot_date=snapshot.snapshot_date,
            )
        except ValueError as exc:
            raise InvalidEpssSilverSourceError(
                f"Invalid historical EPSS row at line {line_number}: {exc}"
            ) from exc


class PrepareHistoricalEpssSilver:
    """Prepare exact deterministic Silver Parquet from verified Bronze evidence."""

    def __init__(
        self,
        *,
        parser: HistoricalEpssSnapshotParser,
        transformer: HistoricalEpssSilverRecordTransformer,
        record_writer: SilverEpssRecordWriter,
        key_factory: EpssSilverKeyFactory,
    ) -> None:
        """Initialize deterministic historical transformation dependencies."""
        self._parser = parser
        self._transformer = transformer
        self._record_writer = record_writer
        self._key_factory = key_factory

    def execute(
        self,
        evidence: HistoricalEpssBronzeEvidenceV1,
    ) -> HistoricalEpssPreparedSilverV1:
        """Parse, transform, and serialize one exact historical Bronze observation."""
        manifest = evidence.manifest
        snapshot = self._parser.parse(
            evidence.source.raw_bytes,
            snapshot_date=manifest.snapshot_date,
        )

        if snapshot.sha256 != manifest.source_sha256:
            raise ValueError("Historical EPSS parsed source SHA-256 does not match Bronze evidence.")
        if snapshot.model_era is not manifest.model_era:
            raise ValueError("Historical EPSS parsed model era does not match Bronze evidence.")
        if snapshot.source_metadata_present is not manifest.source_metadata_present:
            raise ValueError(
                "Historical EPSS parsed metadata-presence evidence does not match Bronze manifest."
            )

        with BytesIO() as destination:
            write_result = self._record_writer.write(
                self._transformer.iter_records(snapshot),
                destination,
            )
            parquet_bytes = destination.getvalue()

        if write_result.row_count != snapshot.row_count:
            raise ValueError(
                "Historical EPSS Silver serialization row_count does not match source evidence."
            )
        if write_result.size_bytes != len(parquet_bytes):
            raise ValueError(
                "Historical EPSS Silver serialization size does not match prepared bytes."
            )

        artifact = HistoricalEpssSilverArtifactV1(
            parquet_bytes=parquet_bytes,
            row_count=write_result.row_count,
            schema_version=write_result.schema_version,
        )

        return HistoricalEpssPreparedSilverV1(
            key=self._key_factory.build(manifest.snapshot_date),
            artifact=artifact,
        )
