# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Deterministic PyArrow Parquet serialization for NVD Silver v1."""

from collections.abc import Iterable
from hashlib import sha256

import pyarrow as pa
import pyarrow.parquet as pq

from opslens.transformation.nvd.serialization.models import (
    NvdSilverParquetArtifactV1,
    NvdSilverRecordV1,
)
from opslens.transformation.nvd.serialization.row_mapper import (
    map_nvd_silver_record_v1,
)
from opslens.transformation.nvd.serialization.schema import (
    NVD_CVE_VERSIONS_SCHEMA_V1,
    NVD_CVE_VERSIONS_SCHEMA_VERSION,
)

NVD_PARQUET_WRITER_CONTRACT_VERSION = 1
NVD_PARQUET_FORMAT_VERSION = "1.0"
NVD_PARQUET_DATA_PAGE_VERSION = "1.0"
NVD_PARQUET_COMPRESSION = "snappy"
NVD_PARQUET_ROW_GROUP_SIZE = 5_000


class NvdSilverParquetSerializerV1:
    """Serialize one NVD source batch into deterministic Parquet bytes."""

    def serialize(
        self,
        records: Iterable[NvdSilverRecordV1],
    ) -> NvdSilverParquetArtifactV1:
        """Serialize one logical source batch using the frozen writer contract."""
        materialized = tuple(records)

        if not materialized:
            raise ValueError("NVD Silver Parquet serialization requires at least one record.")

        source_kind = materialized[0].provenance.source_kind
        source_batch_id = materialized[0].provenance.source_batch_id

        self._validate_batch_identity(
            records=materialized,
            source_kind=source_kind,
            source_batch_id=source_batch_id,
        )
        self._validate_unique_observations(
            records=materialized,
        )

        ordered = tuple(
            sorted(
                materialized,
                key=self._sort_key,
            )
        )

        rows = [map_nvd_silver_record_v1(record) for record in ordered]

        table = pa.Table.from_pylist(
            rows,
            schema=NVD_CVE_VERSIONS_SCHEMA_V1,
        )

        sink = pa.BufferOutputStream()

        pq.write_table(
            table,
            sink,
            version=NVD_PARQUET_FORMAT_VERSION,
            compression=NVD_PARQUET_COMPRESSION,
            use_dictionary=True,
            write_statistics=True,
            data_page_version=NVD_PARQUET_DATA_PAGE_VERSION,
            use_compliant_nested_type=True,
            use_deprecated_int96_timestamps=False,
            use_byte_stream_split=False,
            store_schema=True,
            write_page_index=False,
            write_page_checksum=False,
            row_group_size=NVD_PARQUET_ROW_GROUP_SIZE,
        )

        parquet_bytes = sink.getvalue().to_pybytes()
        parquet_sha256 = sha256(parquet_bytes).hexdigest()

        return NvdSilverParquetArtifactV1(
            parquet_bytes=parquet_bytes,
            parquet_sha256=parquet_sha256,
            row_count=len(ordered),
            size_bytes=len(parquet_bytes),
            schema_version=NVD_CVE_VERSIONS_SCHEMA_VERSION,
            source_kind=source_kind,
            source_batch_id=source_batch_id,
        )

    @staticmethod
    def _sort_key(
        record: NvdSilverRecordV1,
    ) -> tuple[str, str, str]:
        """Return the canonical artifact row-order key."""
        observed = record.core.observed_version

        return (
            observed.cve_id,
            observed.observed_cve_version_id,
            record.provenance.observation_id,
        )

    @staticmethod
    def _validate_batch_identity(
        *,
        records: tuple[NvdSilverRecordV1, ...],
        source_kind: object,
        source_batch_id: str,
    ) -> None:
        """Require one Parquet artifact to represent one source batch."""
        for record in records:
            if record.provenance.source_kind != source_kind:
                raise ValueError("NVD Silver Parquet artifact cannot mix source_kind values.")

            if record.provenance.source_batch_id != source_batch_id:
                raise ValueError("NVD Silver Parquet artifact cannot mix source_batch_id values.")

    @staticmethod
    def _validate_unique_observations(
        *,
        records: tuple[NvdSilverRecordV1, ...],
    ) -> None:
        """Reject duplicate observation identities inside one artifact."""
        seen: set[str] = set()

        for record in records:
            observation_id = record.provenance.observation_id

            if observation_id in seen:
                raise ValueError(
                    "NVD Silver Parquet artifact contains duplicate "
                    f"observation_id {observation_id!r}."
                )

            seen.add(observation_id)
