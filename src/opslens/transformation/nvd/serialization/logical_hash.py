"""Logical record-set hashing for NVD Silver v1."""

import json
import math
from datetime import UTC, datetime
from hashlib import sha256
from typing import cast

from opslens.transformation.nvd.serialization.models import (
    NvdSilverRecordV1,
)
from opslens.transformation.nvd.serialization.row_mapper import (
    map_nvd_silver_record_v1,
)


class NvdLogicalRecordSetHasherV1:
    """Hash the logical Silver record set independently of Parquet bytes."""

    DOMAIN_SEPARATOR = b"opslens-nvd-logical-record-set-v1\n"

    def digest(
        self,
        records: tuple[NvdSilverRecordV1, ...],
    ) -> str:
        """Return a deterministic SHA-256 over canonical logical rows."""
        if records:
            self._validate_batch(records)
            self._validate_unique_observations(records)

        ordered = tuple(
            sorted(
                records,
                key=self._sort_key,
            )
        )

        rows = [self._normalize_json_value(map_nvd_silver_record_v1(record)) for record in ordered]

        canonical = json.dumps(
            rows,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")

        return sha256(self.DOMAIN_SEPARATOR + canonical).hexdigest()

    @staticmethod
    def _sort_key(
        record: NvdSilverRecordV1,
    ) -> tuple[str, str, str]:
        """Return canonical logical-row ordering."""
        observed = record.core.observed_version

        return (
            observed.cve_id,
            observed.observed_cve_version_id,
            record.provenance.observation_id,
        )

    @staticmethod
    def _validate_batch(
        records: tuple[NvdSilverRecordV1, ...],
    ) -> None:
        """Require one logical record set to describe one source batch."""
        source_kind = records[0].provenance.source_kind
        source_batch_id = records[0].provenance.source_batch_id

        for record in records:
            if record.provenance.source_kind is not source_kind:
                raise ValueError("NVD logical record set cannot mix source_kind.")

            if record.provenance.source_batch_id != source_batch_id:
                raise ValueError("NVD logical record set cannot mix source_batch_id.")

    @staticmethod
    def _validate_unique_observations(
        records: tuple[NvdSilverRecordV1, ...],
    ) -> None:
        """Reject duplicate Bronze occurrences."""
        observation_ids = tuple(record.provenance.observation_id for record in records)

        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("NVD logical record set contains duplicate observation_id.")

    @classmethod
    def _normalize_json_value(
        cls,
        value: object,
    ) -> object:
        """Convert one mapped Arrow row value to canonical JSON data."""
        if value is None:
            return None

        if isinstance(value, str):
            return value

        if isinstance(value, bool):
            return value

        if type(value) is int:
            return value

        if type(value) is float:
            if not math.isfinite(value):
                raise ValueError("NVD logical record set contains non-finite float.")

            return value

        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("NVD logical record set contains naive datetime.")

            return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")

        if isinstance(value, dict):
            mapping = cast(
                dict[object, object],
                value,
            )
            normalized: dict[str, object] = {}

            for key, item in mapping.items():
                if not isinstance(key, str):
                    raise ValueError("NVD logical row object keys must be strings.")

                normalized[key] = cls._normalize_json_value(item)

            return normalized

        if isinstance(value, list):
            items = cast(
                list[object],
                value,
            )

            return [cls._normalize_json_value(item) for item in items]

        if isinstance(value, tuple):
            items = cast(
                tuple[object, ...],
                value,
            )

            return [cls._normalize_json_value(item) for item in items]

        raise ValueError(
            f"NVD logical record set contains unsupported value type {type(value).__name__!r}."
        )
