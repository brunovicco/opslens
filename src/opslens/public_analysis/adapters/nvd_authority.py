# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Resolve exact NVD authority through immutable Silver-to-Bronze lineage."""

from __future__ import annotations

import gzip
import json
from hashlib import sha256
from typing import Protocol, cast

import pyarrow as pa
import pyarrow.parquet as pq

from opslens.public_analysis.adapters.exact_s3_authority_object import (
    ExactS3AuthorityObject,
)
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord
from opslens.transformation.nvd.domain.transformer import NvdCveCoreTransformer
from opslens.transformation.nvd.serialization.schema import NVD_CVE_VERSIONS_SCHEMA_V1


class NvdAuthorityDecodeError(RuntimeError):
    """Reject contradictory or incomplete NVD authority lineage."""


class ExactNvdAuthorityObjectReader(Protocol):
    """Read one already-admitted exact immutable authority object."""

    def read(self, *, object_key: str, version_id: str) -> ExactS3AuthorityObject:
        """Return bytes for exactly one explicit immutable object version."""
        ...


class ExactNvdBronzeAuthorityReader:
    """Derive NVD core authority only from the exact original Bronze source CVE."""

    def __init__(
        self,
        *,
        silver_object_reader: ExactNvdAuthorityObjectReader,
        bronze_object_reader: ExactNvdAuthorityObjectReader,
        core_transformer: NvdCveCoreTransformer | None = None,
    ) -> None:
        """Bind exact immutable readers without adding discovery or fallback."""
        self._silver_object_reader = silver_object_reader
        self._bronze_object_reader = bronze_object_reader
        self._core_transformer = core_transformer or NvdCveCoreTransformer()

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        cve_id: str,
        observed_cve_version_id: str,
    ) -> NvdCveCoreRecord:
        """Resolve one requested NVD observation through its exact Bronze lineage."""
        silver = self._silver_object_reader.read(
            object_key=object_key,
            version_id=version_id,
        )
        row = self._exact_silver_row(
            silver.payload,
            observed_cve_version_id=observed_cve_version_id,
        )
        source_sha = self._required_text(row, "source_cve_sha256")
        if self._required_text(row, "cve_id") != cve_id:
            raise NvdAuthorityDecodeError("NVD Silver CVE identity mismatch")
        expected_observed_id = f"{cve_id}@sha256:{source_sha}"
        if expected_observed_id != observed_cve_version_id:
            raise NvdAuthorityDecodeError(
                "NVD Silver observed-version identity does not match CVE and source hash"
            )

        bronze_key = self._required_text(row, "bronze_object_key")
        bronze_version = self._required_text(row, "bronze_object_version_id")
        bronze_sha = self._required_text(row, "bronze_object_sha256")
        record_index = self._required_index(row, "bronze_record_index")
        source_kind = self._required_text(row, "source_kind")
        if source_kind not in {"bootstrap", "incremental"}:
            raise NvdAuthorityDecodeError("Unsupported NVD Silver source_kind")

        bronze = self._bronze_object_reader.read(
            object_key=bronze_key,
            version_id=bronze_version,
        )
        if sha256(bronze.payload).hexdigest() != bronze_sha:
            raise NvdAuthorityDecodeError(
                "Exact NVD Bronze bytes do not match Silver lineage SHA-256"
            )

        source_cve = self._source_cve(
            bronze.payload,
            source_kind=source_kind,
            record_index=record_index,
        )
        core = self._core_transformer.transform(source_cve)
        observed = core.observed_version
        if observed.cve_id != cve_id:
            raise NvdAuthorityDecodeError("NVD Bronze CVE identity mismatch")
        if observed.source_cve_sha256 != source_sha:
            raise NvdAuthorityDecodeError(
                "NVD Bronze canonical source hash does not match Silver authority"
            )
        if observed.observed_cve_version_id != observed_cve_version_id:
            raise NvdAuthorityDecodeError(
                "NVD Bronze observed-version identity does not match Silver authority"
            )
        return core

    @staticmethod
    def _exact_silver_row(
        payload: bytes,
        *,
        observed_cve_version_id: str,
    ) -> dict[str, object]:
        """Require exact NVD Silver v1 schema and one requested observation row."""
        try:
            table = pq.read_table(pa.BufferReader(payload))
        except (pa.ArrowException, OSError, ValueError) as exc:
            raise NvdAuthorityDecodeError("NVD authority object is not readable Parquet") from exc
        if table.schema != NVD_CVE_VERSIONS_SCHEMA_V1:
            raise NvdAuthorityDecodeError("NVD authority Parquet schema is not Silver v1")
        rows = cast(list[dict[str, object]], table.to_pylist())
        matches = tuple(
            row
            for row in rows
            if row.get("observed_cve_version_id") == observed_cve_version_id
        )
        if len(matches) != 1:
            raise NvdAuthorityDecodeError(
                "NVD authority requires exactly one Silver row for observed version"
            )
        return matches[0]

    @classmethod
    def _source_cve(
        cls,
        payload: bytes,
        *,
        source_kind: str,
        record_index: int,
    ) -> dict[str, object]:
        """Extract the exact indexed CVE object from original NVD Bronze bytes."""
        raw_json = payload
        if source_kind == "bootstrap":
            try:
                raw_json = gzip.decompress(payload)
            except (OSError, EOFError) as exc:
                raise NvdAuthorityDecodeError(
                    "NVD bootstrap Bronze authority is not valid gzip"
                ) from exc
        document = cls._json_object(raw_json)
        vulnerabilities_value = document.get("vulnerabilities")
        if not isinstance(vulnerabilities_value, list):
            raise NvdAuthorityDecodeError(
                "NVD Bronze authority vulnerabilities must be an array"
            )
        vulnerabilities = cast(list[object], vulnerabilities_value)
        if record_index >= len(vulnerabilities):
            raise NvdAuthorityDecodeError("NVD Bronze record index is out of bounds")
        wrapped = vulnerabilities[record_index]
        if not isinstance(wrapped, dict):
            raise NvdAuthorityDecodeError("NVD Bronze vulnerability entry must be an object")
        wrapped_object = cast(dict[str, object], wrapped)
        cve_value = wrapped_object.get("cve")
        if not isinstance(cve_value, dict):
            raise NvdAuthorityDecodeError("NVD Bronze vulnerability entry requires a CVE object")
        return cast(dict[str, object], cve_value)

    @staticmethod
    def _json_object(payload: bytes) -> dict[str, object]:
        """Decode a UTF-8 JSON object without repairing source content."""
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise NvdAuthorityDecodeError("NVD Bronze authority must be UTF-8 JSON") from exc
        try:
            parsed = cast(object, json.loads(text))
        except json.JSONDecodeError as exc:
            raise NvdAuthorityDecodeError("NVD Bronze authority contains invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise NvdAuthorityDecodeError("NVD Bronze authority must contain a JSON object")
        return cast(dict[str, object], parsed)

    @staticmethod
    def _required_text(row: dict[str, object], field_name: str) -> str:
        """Require one non-empty exact Silver scalar without normalization."""
        value = row.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise NvdAuthorityDecodeError(
                f"NVD Silver field {field_name!r} must be a non-empty string"
            )
        return value

    @staticmethod
    def _required_index(row: dict[str, object], field_name: str) -> int:
        """Require one non-negative exact Bronze record index."""
        value = row.get(field_name)
        if type(value) is not int or value < 0:
            raise NvdAuthorityDecodeError(
                f"NVD Silver field {field_name!r} must be a non-negative integer"
            )
        return value


__all__ = [
    "ExactNvdAuthorityObjectReader",
    "ExactNvdBronzeAuthorityReader",
    "NvdAuthorityDecodeError",
]
