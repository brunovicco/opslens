"""PyArrow Parquet writer for normalized CISA KEV Silver records."""

from collections.abc import Iterable, Iterator
from datetime import UTC, date
from itertools import islice
from typing import BinaryIO

import pyarrow as pa
import pyarrow.parquet as pq

from opslens.transformation.kev.application.models import KevSilverWriteResult
from opslens.transformation.kev.application.schema import (
    KEV_SILVER_SCHEMA_VERSION,
)
from opslens.transformation.kev.domain.models import SilverKevRecord


class PyArrowSilverKevRecordWriter:
    """Serialize normalized KEV Silver records to Parquet."""

    DEFAULT_BATCH_SIZE = 50_000

    def __init__(self, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
        """Initialize the KEV Silver Parquet writer.

        Args:
            batch_size: Maximum records materialized in one Arrow batch.

        Raises:
            ValueError: If batch_size is not positive.
        """
        if batch_size <= 0:
            raise ValueError("KEV Silver Parquet batch size must be greater than zero.")

        self._batch_size = batch_size

    def write(
        self,
        records: Iterable[SilverKevRecord],
        destination: BinaryIO,
    ) -> KevSilverWriteResult:
        """Serialize normalized KEV records into one Parquet artifact.

        Args:
            records: Normalized KEV Silver records.
            destination: Writable binary destination.

        Returns:
            Metadata describing the serialized artifact.

        Raises:
            ValueError: If no records are supplied or multiple snapshot
                partitions are mixed in one artifact.
        """
        iterator = iter(records)
        first_batch = self._take_batch(iterator)

        if not first_batch:
            raise ValueError("KEV Silver Parquet serialization requires at least one record.")

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

        return KevSilverWriteResult(
            row_count=row_count,
            size_bytes=size_bytes,
            schema_version=KEV_SILVER_SCHEMA_VERSION,
        )

    def _take_batch(
        self,
        iterator: Iterator[SilverKevRecord],
    ) -> tuple[SilverKevRecord, ...]:
        """Read at most one bounded batch from the record iterator."""
        return tuple(islice(iterator, self._batch_size))

    @staticmethod
    def _validate_snapshot_partition(
        *,
        records: tuple[SilverKevRecord, ...],
        expected_snapshot_date: date,
    ) -> None:
        """Require all records in one artifact to share one partition."""
        if any(record.snapshot_date != expected_snapshot_date for record in records):
            raise ValueError(
                "KEV Silver Parquet artifact cannot contain records from multiple snapshot dates."
            )

    @staticmethod
    def _schema() -> pa.Schema:
        """Build the canonical Arrow representation of KEV Silver v1."""
        metadata = {
            b"opslens.dataset": b"kev-silver",
            b"opslens.schema_version": str(KEV_SILVER_SCHEMA_VERSION).encode("ascii"),
        }

        return pa.schema(
            [
                pa.field("cve", pa.string(), nullable=False),
                pa.field("vendor_project", pa.string(), nullable=False),
                pa.field("product", pa.string(), nullable=False),
                pa.field(
                    "vulnerability_name",
                    pa.string(),
                    nullable=False,
                ),
                pa.field("date_added", pa.date32(), nullable=False),
                pa.field(
                    "short_description",
                    pa.string(),
                    nullable=False,
                ),
                pa.field(
                    "required_action",
                    pa.string(),
                    nullable=False,
                ),
                pa.field("due_date", pa.date32(), nullable=False),
                pa.field(
                    "known_ransomware_campaign_use",
                    pa.string(),
                    nullable=False,
                ),
                pa.field("notes", pa.string(), nullable=False),
                pa.field(
                    "cwes",
                    pa.list_(pa.string()),
                    nullable=False,
                ),
                pa.field(
                    "catalog_version",
                    pa.string(),
                    nullable=False,
                ),
                pa.field(
                    "catalog_date_released",
                    pa.timestamp("us", tz="UTC"),
                    nullable=False,
                ),
                pa.field("source", pa.string(), nullable=False),
                pa.field(
                    "source_sha256",
                    pa.string(),
                    nullable=False,
                ),
                pa.field(
                    "retrieved_at",
                    pa.timestamp("us", tz="UTC"),
                    nullable=False,
                ),
            ],
            metadata=metadata,
        )

    @staticmethod
    def _to_record_batch(
        *,
        records: tuple[SilverKevRecord, ...],
        schema: pa.Schema,
    ) -> pa.RecordBatch:
        """Convert normalized records into one Arrow RecordBatch."""
        return pa.RecordBatch.from_arrays(
            [
                pa.array((record.cve for record in records), type=pa.string()),
                pa.array(
                    (record.vendor_project for record in records),
                    type=pa.string(),
                ),
                pa.array(
                    (record.product for record in records),
                    type=pa.string(),
                ),
                pa.array(
                    (record.vulnerability_name for record in records),
                    type=pa.string(),
                ),
                pa.array(
                    (record.date_added for record in records),
                    type=pa.date32(),
                ),
                pa.array(
                    (record.short_description for record in records),
                    type=pa.string(),
                ),
                pa.array(
                    (record.required_action for record in records),
                    type=pa.string(),
                ),
                pa.array(
                    (record.due_date for record in records),
                    type=pa.date32(),
                ),
                pa.array(
                    (record.known_ransomware_campaign_use.value for record in records),
                    type=pa.string(),
                ),
                pa.array(
                    (record.notes for record in records),
                    type=pa.string(),
                ),
                pa.array(
                    (list(record.cwes) for record in records),
                    type=pa.list_(pa.string()),
                ),
                pa.array(
                    (record.catalog_version for record in records),
                    type=pa.string(),
                ),
                pa.array(
                    (record.catalog_date_released.astimezone(UTC) for record in records),
                    type=pa.timestamp("us", tz="UTC"),
                ),
                pa.array(
                    (record.source for record in records),
                    type=pa.string(),
                ),
                pa.array(
                    (record.source_sha256 for record in records),
                    type=pa.string(),
                ),
                pa.array(
                    (record.retrieved_at.astimezone(UTC) for record in records),
                    type=pa.timestamp("us", tz="UTC"),
                ),
            ],
            schema=schema,
        )
