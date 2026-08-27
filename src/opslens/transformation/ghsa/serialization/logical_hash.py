"""Logical record-set hashing for GHSA Silver v1."""

import json
import math
from datetime import UTC, datetime
from hashlib import sha256
from typing import cast

from opslens.transformation.ghsa.serialization.models import GhsaSilverRecordV1
from opslens.transformation.ghsa.serialization.row_mapper import (
    map_ghsa_silver_record_v1,
)


class GhsaLogicalRecordSetHasherV1:
    """Hash normalized GHSA Silver content independently of Parquet bytes."""

    DOMAIN_SEPARATOR = b"opslens-ghsa-logical-record-set-v1\n"

    def digest(self, records: tuple[GhsaSilverRecordV1, ...]) -> str:
        """Return a deterministic SHA-256 over canonical logical rows."""
        self._validate_unique_versions(records)

        ordered = tuple(sorted(records, key=self._sort_key))
        rows = [
            self._normalize_json_value(map_ghsa_silver_record_v1(record))
            for record in ordered
        ]

        canonical = json.dumps(
            rows,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")

        return sha256(self.DOMAIN_SEPARATOR + canonical).hexdigest()

    @staticmethod
    def _sort_key(record: GhsaSilverRecordV1) -> tuple[str, str]:
        """Return canonical logical-row ordering."""
        observed = record.core.observed_version
        return observed.ghsa_id, observed.observed_advisory_version_id

    @staticmethod
    def _validate_unique_versions(records: tuple[GhsaSilverRecordV1, ...]) -> None:
        """Reject duplicate advisory-content versions in one logical record set."""
        version_ids = tuple(
            record.core.observed_version.observed_advisory_version_id
            for record in records
        )

        if len(version_ids) != len(set(version_ids)):
            raise ValueError(
                "GHSA logical record set contains duplicate observed_advisory_version_id."
            )

    @classmethod
    def _normalize_json_value(cls, value: object) -> object:
        """Convert one mapped Arrow row value to canonical JSON data."""
        if value is None or isinstance(value, (str, bool)) or type(value) is int:
            return value

        if type(value) is float:
            if not math.isfinite(value):
                raise ValueError("GHSA logical record set contains non-finite float.")
            return value

        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("GHSA logical record set contains naive datetime.")

            return (
                value.astimezone(UTC)
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z")
            )

        if isinstance(value, dict):
            mapping = cast(dict[object, object], value)
            normalized: dict[str, object] = {}

            for key, item in mapping.items():
                if not isinstance(key, str):
                    raise ValueError("GHSA logical row object keys must be strings.")
                normalized[key] = cls._normalize_json_value(item)

            return normalized

        if isinstance(value, list):
            items = cast(list[object], value)
            return [cls._normalize_json_value(item) for item in items]

        if isinstance(value, tuple):
            items = cast(tuple[object, ...], value)
            return [cls._normalize_json_value(item) for item in items]

        raise ValueError(
            "GHSA logical record set contains unsupported value type "
            f"{type(value).__name__!r}."
        )
