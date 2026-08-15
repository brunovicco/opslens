"""PyArrow Parquet writer for normalized EPSS Silver records."""

from collections.abc import Iterable, Iterator
from datetime import UTC, date
from itertools import islice
from typing import BinaryIO

import pyarrow as pa
import pyarrow.parquet as pq

from opslens.transformation.epss.application.models import SilverWriteResult
from opslens.transformation.epss.application.schema import EPSS_SILVER_SCHEMA_VERSION
from opslens.transformation.epss.domain.models import SilverEpssRecord


class PyArrowSilverEpssRecordWriter:
    """Serialize EPSS Silver records into Parquet using bounded batches."""

    DEFAULT_BATCH_SIZE = 50_000

    def __init__(self, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
        """Initialize the Parquet writer adapter.

        Args:
            batch_size: Maximum number of EPSS records materialized per batch.

        Raises:
            ValueError: If batch_size is not positive.
        """
        if batch_size <= 0:
            raise ValueError("Silver Parquet batch size must be greater than zero.")

        self._batch_size = batch_size

    def write(
        self,
        records: Iterable[SilverEpssRecord],
        destination: BinaryIO,
    ) -> SilverWriteResult:
        """Serialize normalized EPSS records into a Parquet destination.

        Args:
            records: Normalized EPSS Silver records.
            destination: Writable binary destination.

        Returns:
            Metadata describing the serialized Parquet artifact.

        Raises:
            ValueError: If no records are supplied or records from different
                snapshot partitions are mixed in one artifact.
        """
        iterator = iter(records)
        first_batch = self._take_batch(iterator)

        if not first_batch:
            raise ValueError("Silver Parquet serialization requires at least one record.")

        snapshot_date = first_batch[0].snapshot_date
        start_position = destination.tell()
        schema = self._schema()

        parquet_writer = pq.ParquetWriter(
            where=destination,
            schema=schema,
            version="1.0",
            compression="snappy",
            use_dictionary=True,
            write_statistics=True,
        )

        row_count = 0

        try:
            batch = first_batch

            while batch:
                self._validate_snapshot_partition(
                    records=batch,
                    expected_snapshot_date=snapshot_date,
                )

                parquet_writer.write_batch(
                    self._to_record_batch(
                        records=batch,
                        schema=schema,
                    )
                )

                row_count += len(batch)
                batch = self._take_batch(iterator)
        finally:
            parquet_writer.close()

        size_bytes = destination.tell() - start_position

        return SilverWriteResult(
            row_count=row_count,
            size_bytes=size_bytes,
            schema_version=EPSS_SILVER_SCHEMA_VERSION,
        )

    def _take_batch(
        self,
        iterator: Iterator[SilverEpssRecord],
    ) -> tuple[SilverEpssRecord, ...]:
        """Read at most one bounded batch from the record iterator."""
        return tuple(islice(iterator, self._batch_size))

    @staticmethod
    def _validate_snapshot_partition(
        *,
        records: tuple[SilverEpssRecord, ...],
        expected_snapshot_date: date,
    ) -> None:
        """Ensure one Parquet artifact contains only one snapshot partition."""
        if any(record.snapshot_date != expected_snapshot_date for record in records):
            raise ValueError(
                "Silver Parquet artifact cannot contain records from multiple snapshot dates."
            )

    @staticmethod
    def _schema() -> pa.Schema:
        """Build the canonical Arrow representation of the EPSS Silver schema."""
        metadata = {
            b"opslens.dataset": b"epss-silver",
            b"opslens.schema_version": str(EPSS_SILVER_SCHEMA_VERSION).encode("ascii"),
        }

        return pa.schema(
            [
                pa.field("cve", pa.string(), nullable=False),
                pa.field("epss", pa.float64(), nullable=False),
                pa.field("percentile", pa.float64(), nullable=False),
                pa.field("model_version", pa.string(), nullable=False),
                pa.field(
                    "score_timestamp",
                    pa.timestamp("us", tz="UTC"),
                    nullable=False,
                ),
                pa.field("source", pa.string(), nullable=False),
                pa.field("source_sha256", pa.string(), nullable=False),
            ],
            metadata=metadata,
        )

    @staticmethod
    def _to_record_batch(
        *,
        records: tuple[SilverEpssRecord, ...],
        schema: pa.Schema,
    ) -> pa.RecordBatch:
        """Convert one bounded domain-record batch into an Arrow RecordBatch."""
        return pa.RecordBatch.from_arrays(
            [
                pa.array((record.cve for record in records), type=pa.string()),
                pa.array((record.epss for record in records), type=pa.float64()),
                pa.array((record.percentile for record in records), type=pa.float64()),
                pa.array((record.model_version for record in records), type=pa.string()),
                pa.array(
                    (record.score_timestamp.astimezone(UTC) for record in records),
                    type=pa.timestamp("us", tz="UTC"),
                ),
                pa.array((record.source for record in records), type=pa.string()),
                pa.array((record.source_sha256 for record in records), type=pa.string()),
            ],
            schema=schema,
        )
