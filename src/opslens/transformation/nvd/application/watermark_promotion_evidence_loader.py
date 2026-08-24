"""Load exact persisted NVD Silver evidence for watermark promotion."""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, cast

from opslens.ingestion.nvd.application.watermark import (
    NvdWatermarkCandidate,
)
from opslens.transformation.nvd.completion.promotion import (
    NvdPersistedObjectPayloadV1,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SILVER_COMPLETE_KEY_PATTERN = re.compile(
    r"^silver/nvd/cve/"
    r"schema_version=1/"
    r"source_kind=incremental/"
    r"update_id=([0-9a-f]{64})/"
    r"manifest\.json$"
)


class NvdWatermarkPromotionEvidenceLoadError(ValueError):
    """Raised when exact Silver evidence cannot be loaded safely."""


@dataclass(frozen=True, slots=True)
class NvdSilverCompleteRefV1:
    """Identify the exact Silver COMPLETE object selected by a trigger."""

    key: str
    version_id: str

    def __post_init__(self) -> None:
        """Require exact non-empty object coordinates."""
        if not self.key or self.key != self.key.strip():
            raise ValueError(
                "NVD Silver COMPLETE key must be exact and non-empty."
            )

        if not self.version_id or self.version_id != self.version_id.strip():
            raise ValueError(
                "NVD Silver COMPLETE VersionId must be exact and non-empty."
            )


class NvdPromotionExactObjectReaderV1(Protocol):
    """Read one exact immutable persisted object version with a size bound."""

    def read_exact(
        self,
        *,
        key: str,
        version_id: str,
        max_bytes: int,
    ) -> NvdPersistedObjectPayloadV1:
        """Return the exact requested object version and bytes."""
        ...


@dataclass(frozen=True, slots=True)
class NvdWatermarkPromotionEvidenceV1:
    """Bundle the exact evidence required by the promotion verifier."""

    candidate: NvdWatermarkCandidate
    silver_manifest: NvdPersistedObjectPayloadV1
    silver_parquet: NvdPersistedObjectPayloadV1


class NvdWatermarkPromotionEvidenceLoaderV1:
    """Reconstruct a Bronze candidate from exact Silver COMPLETE evidence.

    The trigger supplies only the exact Silver COMPLETE key and VersionId.
    Authority remains in persisted object bytes. The loader reads that exact
    COMPLETE version, derives the candidate coordinates from the manifest,
    then reads the exact Parquet version declared by that manifest.

    The downstream ``NvdWatermarkPromotionVerifierV1`` remains responsible
    for the full promotion-eligibility proof before any watermark mutation.
    """

    MAX_SILVER_MANIFEST_BYTES = 1024 * 1024
    MAX_SILVER_PARQUET_BYTES = 128 * 1024 * 1024

    _TOP_LEVEL_KEYS = frozenset(
        {
            "bronze_manifest",
            "bronze_objects",
            "completion_status",
            "dataset",
            "logical_record_set_sha256",
            "manifest_version",
            "schema_version",
            "silver_object",
            "source_batch_id",
            "source_coordinates",
            "source_kind",
            "warnings",
            "writer_contract_version",
        }
    )
    _BRONZE_MANIFEST_KEYS = frozenset(
        {
            "key",
            "sha256",
            "size_bytes",
            "version_id",
        }
    )
    _SILVER_OBJECT_KEYS = frozenset(
        {
            "key",
            "row_count",
            "sha256",
            "size_bytes",
            "version_id",
        }
    )
    _SOURCE_COORDINATE_KEYS = frozenset(
        {
            "total_results",
            "update_id",
            "window_end_at",
            "window_start_at",
        }
    )

    def __init__(
        self,
        *,
        object_reader: NvdPromotionExactObjectReaderV1,
    ) -> None:
        """Initialize the exact object-version reader dependency."""
        self._object_reader = object_reader

    def load(
        self,
        *,
        silver_complete: NvdSilverCompleteRefV1,
    ) -> NvdWatermarkPromotionEvidenceV1:
        """Load exact Silver COMPLETE + Parquet and reconstruct candidate."""
        update_id = self._extract_update_id(silver_complete.key)

        silver_manifest = self._object_reader.read_exact(
            key=silver_complete.key,
            version_id=silver_complete.version_id,
            max_bytes=self.MAX_SILVER_MANIFEST_BYTES,
        )
        self._require_exact_returned_object(
            payload=silver_manifest,
            expected_key=silver_complete.key,
            expected_version_id=silver_complete.version_id,
            max_bytes=self.MAX_SILVER_MANIFEST_BYTES,
            label="Silver COMPLETE",
        )

        document = self._parse_json_object(silver_manifest.raw_bytes)
        self._require_exact_keys(
            document,
            self._TOP_LEVEL_KEYS,
            "Silver COMPLETE manifest",
        )

        if self._require_str(document, "completion_status") != "complete":
            raise NvdWatermarkPromotionEvidenceLoadError(
                "NVD Silver promotion requires a COMPLETE manifest."
            )

        if self._require_str(document, "manifest_version") != "1":
            raise NvdWatermarkPromotionEvidenceLoadError(
                "Unsupported NVD Silver manifest version."
            )

        if self._require_int(document, "schema_version", minimum=1) != 1:
            raise NvdWatermarkPromotionEvidenceLoadError(
                "Unsupported NVD Silver schema version."
            )

        if (
            self._require_int(
                document,
                "writer_contract_version",
                minimum=1,
            )
            != 1
        ):
            raise NvdWatermarkPromotionEvidenceLoadError(
                "Unsupported NVD Silver writer contract version."
            )

        if self._require_str(document, "source_kind") != "incremental":
            raise NvdWatermarkPromotionEvidenceLoadError(
                "Only incremental NVD Silver COMPLETE evidence is promotable."
            )

        if self._require_str(document, "source_batch_id") != update_id:
            raise NvdWatermarkPromotionEvidenceLoadError(
                "NVD Silver source_batch_id does not match the trigger key."
            )

        source_coordinates = self._require_object(
            document,
            "source_coordinates",
        )
        self._require_exact_keys(
            source_coordinates,
            self._SOURCE_COORDINATE_KEYS,
            "Silver source_coordinates",
        )

        coordinate_update_id = self._require_sha256(
            source_coordinates,
            "update_id",
        )
        if coordinate_update_id != update_id:
            raise NvdWatermarkPromotionEvidenceLoadError(
                "NVD Silver source_coordinates update_id does not match "
                "the trigger key."
            )

        bronze_manifest = self._require_object(
            document,
            "bronze_manifest",
        )
        self._require_exact_keys(
            bronze_manifest,
            self._BRONZE_MANIFEST_KEYS,
            "Silver bronze_manifest",
        )

        bronze_objects = self._require_list(
            document,
            "bronze_objects",
        )
        if not bronze_objects:
            raise NvdWatermarkPromotionEvidenceLoadError(
                "NVD Silver COMPLETE must reference at least one Bronze page."
            )

        candidate = NvdWatermarkCandidate(
            update_id=update_id,
            window_start_at=self._parse_timestamp(
                self._require_str(
                    source_coordinates,
                    "window_start_at",
                ),
                label="window_start_at",
            ),
            window_end_at=self._parse_timestamp(
                self._require_str(
                    source_coordinates,
                    "window_end_at",
                ),
                label="window_end_at",
            ),
            bronze_manifest_key=self._require_str(
                bronze_manifest,
                "key",
            ),
            bronze_manifest_version_id=self._require_str(
                bronze_manifest,
                "version_id",
            ),
            bronze_manifest_sha256=self._require_sha256(
                bronze_manifest,
                "sha256",
            ),
            total_results=self._require_int(
                source_coordinates,
                "total_results",
                minimum=0,
            ),
            page_count=len(bronze_objects),
        )

        silver_object = self._require_object(
            document,
            "silver_object",
        )
        self._require_exact_keys(
            silver_object,
            self._SILVER_OBJECT_KEYS,
            "Silver silver_object",
        )

        expected_parquet_key = (
            "silver/nvd/cve/"
            "schema_version=1/"
            "source_kind=incremental/"
            f"update_id={update_id}/"
            "part-00000.parquet"
        )
        parquet_key = self._require_str(
            silver_object,
            "key",
        )
        if parquet_key != expected_parquet_key:
            raise NvdWatermarkPromotionEvidenceLoadError(
                "NVD Silver Parquet key is not deterministic for the update."
            )

        parquet_version_id = self._require_str(
            silver_object,
            "version_id",
        )
        declared_parquet_size = self._require_int(
            silver_object,
            "size_bytes",
            minimum=1,
        )
        declared_parquet_sha256 = self._require_sha256(
            silver_object,
            "sha256",
        )

        if declared_parquet_size > self.MAX_SILVER_PARQUET_BYTES:
            raise NvdWatermarkPromotionEvidenceLoadError(
                "NVD Silver Parquet exceeds the promotion read bound."
            )

        silver_parquet = self._object_reader.read_exact(
            key=parquet_key,
            version_id=parquet_version_id,
            max_bytes=self.MAX_SILVER_PARQUET_BYTES,
        )
        self._require_exact_returned_object(
            payload=silver_parquet,
            expected_key=parquet_key,
            expected_version_id=parquet_version_id,
            max_bytes=self.MAX_SILVER_PARQUET_BYTES,
            label="Silver Parquet",
        )

        if silver_parquet.size_bytes != declared_parquet_size:
            raise NvdWatermarkPromotionEvidenceLoadError(
                "NVD Silver Parquet byte size does not match COMPLETE evidence."
            )

        if silver_parquet.sha256 != declared_parquet_sha256:
            raise NvdWatermarkPromotionEvidenceLoadError(
                "NVD Silver Parquet SHA-256 does not match COMPLETE evidence."
            )

        return NvdWatermarkPromotionEvidenceV1(
            candidate=candidate,
            silver_manifest=silver_manifest,
            silver_parquet=silver_parquet,
        )

    @staticmethod
    def _extract_update_id(key: str) -> str:
        """Require the canonical incremental Silver COMPLETE key."""
        match = _SILVER_COMPLETE_KEY_PATTERN.fullmatch(key)
        if match is None:
            raise NvdWatermarkPromotionEvidenceLoadError(
                "NVD promotion trigger key is not the canonical incremental "
                "Silver COMPLETE path."
            )

        return match.group(1)

    @staticmethod
    def _require_exact_returned_object(
        *,
        payload: NvdPersistedObjectPayloadV1,
        expected_key: str,
        expected_version_id: str,
        max_bytes: int,
        label: str,
    ) -> None:
        """Verify the reader returned the exact object version requested."""
        if payload.key != expected_key:
            raise NvdWatermarkPromotionEvidenceLoadError(
                f"{label} reader returned a different object key."
            )

        if payload.version_id != expected_version_id:
            raise NvdWatermarkPromotionEvidenceLoadError(
                f"{label} reader returned a different VersionId."
            )

        if payload.size_bytes > max_bytes:
            raise NvdWatermarkPromotionEvidenceLoadError(
                f"{label} exceeds the promotion read bound."
            )

    @staticmethod
    def _parse_json_object(payload: bytes) -> dict[str, object]:
        """Parse one UTF-8 JSON object without granting it authority."""
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NvdWatermarkPromotionEvidenceLoadError(
                "NVD Silver COMPLETE is not valid UTF-8 JSON."
            ) from exc

        if not isinstance(decoded, dict):
            raise NvdWatermarkPromotionEvidenceLoadError(
                "NVD Silver COMPLETE must be a JSON object."
            )

        return cast(dict[str, object], decoded)

    @staticmethod
    def _require_exact_keys(
        document: dict[str, object],
        expected: frozenset[str],
        label: str,
    ) -> None:
        """Require an exact closed JSON-object shape."""
        actual = frozenset(document)
        if actual != expected:
            raise NvdWatermarkPromotionEvidenceLoadError(
                f"{label} keys do not match the supported contract."
            )

    @staticmethod
    def _require_object(
        document: dict[str, object],
        key: str,
    ) -> dict[str, object]:
        """Return one required nested JSON object."""
        value = document.get(key)
        if not isinstance(value, dict):
            raise NvdWatermarkPromotionEvidenceLoadError(
                f"NVD Silver field {key!r} must be an object."
            )

        return cast(dict[str, object], value)

    @staticmethod
    def _require_list(
        document: dict[str, object],
        key: str,
    ) -> list[object]:
        """Return one required JSON list."""
        value = document.get(key)
        if not isinstance(value, list):
            raise NvdWatermarkPromotionEvidenceLoadError(
                f"NVD Silver field {key!r} must be a list."
            )

        return cast(list[object], value)

    @staticmethod
    def _require_str(
        document: dict[str, object],
        key: str,
    ) -> str:
        """Return one required non-empty string."""
        value = document.get(key)
        if not isinstance(value, str) or not value:
            raise NvdWatermarkPromotionEvidenceLoadError(
                f"NVD Silver field {key!r} must be a non-empty string."
            )

        return value

    @staticmethod
    def _require_int(
        document: dict[str, object],
        key: str,
        *,
        minimum: int,
    ) -> int:
        """Return one required integer at or above the lower bound."""
        value = document.get(key)
        if type(value) is not int or value < minimum:
            raise NvdWatermarkPromotionEvidenceLoadError(
                f"NVD Silver field {key!r} must be an integer >= {minimum}."
            )

        return value

    @staticmethod
    def _require_sha256(
        document: dict[str, object],
        key: str,
    ) -> str:
        """Return one required lowercase SHA-256 string."""
        value = NvdWatermarkPromotionEvidenceLoaderV1._require_str(
            document,
            key,
        )
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise NvdWatermarkPromotionEvidenceLoadError(
                f"NVD Silver field {key!r} must be a lowercase SHA-256."
            )

        return value

    @staticmethod
    def _parse_timestamp(
        value: str,
        *,
        label: str,
    ) -> datetime:
        """Parse one ISO-8601 timestamp with explicit timezone evidence."""
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise NvdWatermarkPromotionEvidenceLoadError(
                f"NVD Silver {label} is not a valid ISO-8601 timestamp."
            ) from exc

        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise NvdWatermarkPromotionEvidenceLoadError(
                f"NVD Silver {label} must include an explicit timezone."
            )

        return parsed.astimezone(UTC)
