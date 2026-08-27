# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false
"""Deterministic PyArrow Parquet serialization for GHSA Silver v1."""

from collections.abc import Iterable
from hashlib import sha256

import pyarrow as pa
import pyarrow.parquet as pq

from opslens.transformation.ghsa.serialization.models import (
    GhsaSilverParquetArtifactV1,
    GhsaSilverRecordV1,
)
from opslens.transformation.ghsa.serialization.row_mapper import (
    map_ghsa_silver_record_v1,
)
from opslens.transformation.ghsa.serialization.schema import (
    GHSA_ADVISORY_VERSIONS_SCHEMA_V1,
    GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION,
)

GHSA_PARQUET_WRITER_CONTRACT_VERSION = 1
GHSA_PARQUET_FORMAT_VERSION = "1.0"
GHSA_PARQUET_DATA_PAGE_VERSION = "1.0"
GHSA_PARQUET_COMPRESSION = "snappy"
GHSA_PARQUET_ROW_GROUP_SIZE = 5_000


class GhsaSilverParquetSerializerV1:
    """Serialize normalized GHSA advisory versions into deterministic Parquet bytes."""

    def serialize(
        self,
        records: Iterable[GhsaSilverRecordV1],
    ) -> GhsaSilverParquetArtifactV1:
        """Serialize one non-empty logical record set using the frozen writer contract."""
        materialized = tuple(records)

        if not materialized:
            raise ValueError("GHSA Silver Parquet serialization requires at least one record.")

        self._validate_unique_versions(materialized)
        ordered = tuple(sorted(materialized, key=self._sort_key))
        rows = [map_ghsa_silver_record_v1(record) for record in ordered]

        table = pa.Table.from_pylist(
            rows,
            schema=GHSA_ADVISORY_VERSIONS_SCHEMA_V1,
        )

        sink = pa.BufferOutputStream()

        pq.write_table(
            table,
            sink,
            version=GHSA_PARQUET_FORMAT_VERSION,
            compression=GHSA_PARQUET_COMPRESSION,
            use_dictionary=True,
            write_statistics=True,
            data_page_version=GHSA_PARQUET_DATA_PAGE_VERSION,
            use_compliant_nested_type=True,
            use_deprecated_int96_timestamps=False,
            use_byte_stream_split=False,
            store_schema=True,
            write_page_index=False,
            write_page_checksum=False,
            row_group_size=GHSA_PARQUET_ROW_GROUP_SIZE,
        )

        parquet_bytes = sink.getvalue().to_pybytes()

        return GhsaSilverParquetArtifactV1(
            parquet_bytes=parquet_bytes,
            parquet_sha256=sha256(parquet_bytes).hexdigest(),
            row_count=len(ordered),
            size_bytes=len(parquet_bytes),
            schema_version=GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION,
        )

    @staticmethod
    def _sort_key(record: GhsaSilverRecordV1) -> tuple[str, str]:
        """Return the canonical artifact row-order key."""
        observed = record.core.observed_version
        return observed.ghsa_id, observed.observed_advisory_version_id

    @staticmethod
    def _validate_unique_versions(records: tuple[GhsaSilverRecordV1, ...]) -> None:
        """Reject duplicate advisory-content versions inside one artifact."""
        version_ids = tuple(
            record.core.observed_version.observed_advisory_version_id
            for record in records
        )

        if len(version_ids) != len(set(version_ids)):
            raise ValueError(
                "GHSA Silver Parquet artifact contains duplicate observed_advisory_version_id."
            )
