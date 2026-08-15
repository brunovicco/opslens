"""Streaming transformation from validated EPSS snapshots to Silver records."""

import csv
import gzip
import io
from collections.abc import Iterator

from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.transformation.epss.domain.errors import InvalidEpssSilverSourceError
from opslens.transformation.epss.domain.models import SilverEpssRecord


class EpssSilverTransformer:
    """Transform validated FIRST EPSS snapshots into normalized Silver records."""

    EXPECTED_HEADER = ("cve", "epss", "percentile")
    SOURCE = "first-epss"

    def iter_records(self, snapshot: EpssSnapshot) -> Iterator[SilverEpssRecord]:
        """Yield normalized Silver records from one validated EPSS snapshot.

        Args:
            snapshot: Validated immutable FIRST EPSS source snapshot.

        Yields:
            Normalized EPSS Silver records in source order.

        Raises:
            InvalidEpssSilverSourceError: If the source payload cannot be
                decoded or contains malformed EPSS data rows.
        """
        emitted_count = 0

        try:
            with (
                gzip.GzipFile(
                    fileobj=io.BytesIO(snapshot.raw_bytes),
                    mode="rb",
                ) as gzip_stream,
                io.TextIOWrapper(
                    gzip_stream,
                    encoding="utf-8",
                    newline="",
                ) as text_stream,
            ):
                reader = csv.reader(text_stream)

                self._consume_metadata(reader)
                self._validate_header(reader)

                for line_number, row in enumerate(reader, start=3):
                    emitted_count += 1
                    yield self._build_record(
                        snapshot=snapshot,
                        row=row,
                        line_number=line_number,
                    )

        except InvalidEpssSilverSourceError:
            raise
        except (gzip.BadGzipFile, EOFError, OSError, UnicodeDecodeError, csv.Error) as exc:
            raise InvalidEpssSilverSourceError(
                "EPSS Bronze payload cannot be decoded as the expected gzip CSV artifact."
            ) from exc

        if emitted_count != snapshot.row_count:
            raise InvalidEpssSilverSourceError(
                "EPSS transformed row count does not match Bronze snapshot metadata: "
                f"expected {snapshot.row_count}, emitted {emitted_count}."
            )

    @staticmethod
    def _consume_metadata(reader: Iterator[list[str]]) -> None:
        """Consume and minimally validate the FIRST metadata row."""
        metadata_row = next(reader, None)

        if not metadata_row or not metadata_row[0].startswith("#"):
            raise InvalidEpssSilverSourceError(
                "EPSS Bronze payload is missing the expected metadata row."
            )

    def _validate_header(self, reader: Iterator[list[str]]) -> None:
        """Validate the EPSS CSV header before transforming data rows."""
        header = next(reader, None)

        if header is None or tuple(header) != self.EXPECTED_HEADER:
            raise InvalidEpssSilverSourceError(
                "Unexpected EPSS Bronze CSV header. "
                f"Expected {self.EXPECTED_HEADER}, received {tuple(header or ())}."
            )

    def _build_record(
        self,
        *,
        snapshot: EpssSnapshot,
        row: list[str],
        line_number: int,
    ) -> SilverEpssRecord:
        """Convert one CSV row into a validated Silver record."""
        if len(row) != len(self.EXPECTED_HEADER):
            raise InvalidEpssSilverSourceError(
                f"Malformed EPSS row at line {line_number}: "
                f"expected 3 columns, received {len(row)}."
            )

        cve = row[0].strip()
        epss_value = row[1].strip()
        percentile_value = row[2].strip()

        try:
            epss = float(epss_value)
            percentile = float(percentile_value)
        except ValueError as exc:
            raise InvalidEpssSilverSourceError(
                f"Malformed EPSS numeric value at line {line_number}."
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
                snapshot_date=snapshot.score_timestamp.date(),
            )
        except ValueError as exc:
            raise InvalidEpssSilverSourceError(
                f"Invalid EPSS row at line {line_number}: {exc}"
            ) from exc
