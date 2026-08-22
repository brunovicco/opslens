"""Deterministic NVD watermark promotion eligibility proof."""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import ClassVar, cast

from opslens.ingestion.nvd.application.watermark import (
    NvdWatermarkCandidate,
    NvdWatermarkTransitionValidator,
)
from opslens.transformation.nvd.serialization.parquet import (
    NVD_PARQUET_WRITER_CONTRACT_VERSION,
)
from opslens.transformation.nvd.serialization.schema import (
    NVD_CVE_VERSIONS_SCHEMA_NAME,
    NVD_CVE_VERSIONS_SCHEMA_VERSION,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class InvalidNvdWatermarkPromotionEvidenceError(ValueError):
    """Raised when persisted Silver evidence cannot authorize promotion."""


@dataclass(frozen=True, slots=True)
class NvdPersistedObjectPayloadV1:
    """Represent exact bytes read from one immutable persisted object."""

    key: str
    version_id: str
    raw_bytes: bytes

    def __post_init__(self) -> None:
        """Validate exact persisted-object coordinates."""
        if not self.key.strip():
            raise ValueError("Persisted NVD object key cannot be empty.")

        if not self.version_id.strip():
            raise ValueError("Persisted NVD object VersionId cannot be empty.")

        if not self.raw_bytes:
            raise ValueError("Persisted NVD object bytes cannot be empty.")

    @property
    def sha256(self) -> str:
        """Return SHA-256 of the exact persisted bytes."""
        return sha256(self.raw_bytes).hexdigest()

    @property
    def size_bytes(self) -> int:
        """Return exact persisted byte size."""
        return len(self.raw_bytes)


@dataclass(frozen=True, slots=True)
class NvdWatermarkPromotionEligibilityV1:
    """Prove that one Bronze candidate reached verified Silver completion."""

    PROMOTION_VERSION: ClassVar[str] = "1"
    STATE: ClassVar[str] = "silver_complete"
    ELIGIBLE: ClassVar[bool] = True
    SOURCE: ClassVar[str] = "nvd-cve"
    SOURCE_INTERFACE: ClassVar[str] = "cve-api-2.0"

    update_id: str
    validated_committed_through_at: datetime
    next_committed_through_at: datetime

    bronze_manifest_key: str
    bronze_manifest_version_id: str
    bronze_manifest_sha256: str

    silver_manifest_key: str
    silver_manifest_version_id: str
    silver_manifest_sha256: str

    silver_parquet_key: str
    silver_parquet_version_id: str
    silver_parquet_sha256: str

    logical_record_set_sha256: str

    total_results: int
    row_count: int
    page_count: int
    warning_count: int

    def __post_init__(self) -> None:
        """Validate immutable promotion-proof invariants."""
        if _SHA256_PATTERN.fullmatch(self.update_id) is None:
            raise ValueError("NVD promotion update_id must be a lowercase SHA-256.")

        committed = self._require_utc(
            self.validated_committed_through_at,
            "validated committed watermark",
        )
        next_boundary = self._require_utc(
            self.next_committed_through_at,
            "next committed watermark",
        )

        if committed >= next_boundary:
            raise ValueError("NVD promotion next boundary must advance watermark.")

        object.__setattr__(
            self,
            "validated_committed_through_at",
            committed,
        )
        object.__setattr__(
            self,
            "next_committed_through_at",
            next_boundary,
        )

        for label, value in (
            ("bronze manifest key", self.bronze_manifest_key),
            (
                "bronze manifest VersionId",
                self.bronze_manifest_version_id,
            ),
            ("silver manifest key", self.silver_manifest_key),
            (
                "silver manifest VersionId",
                self.silver_manifest_version_id,
            ),
            ("silver Parquet key", self.silver_parquet_key),
            (
                "silver Parquet VersionId",
                self.silver_parquet_version_id,
            ),
        ):
            if not value.strip():
                raise ValueError(f"NVD promotion {label} cannot be empty.")

        for label, value in (
            (
                "bronze manifest SHA-256",
                self.bronze_manifest_sha256,
            ),
            (
                "silver manifest SHA-256",
                self.silver_manifest_sha256,
            ),
            (
                "silver Parquet SHA-256",
                self.silver_parquet_sha256,
            ),
            (
                "logical record-set SHA-256",
                self.logical_record_set_sha256,
            ),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"NVD promotion {label} is invalid.")

        if type(self.total_results) is not int or self.total_results < 0:
            raise ValueError("NVD promotion total_results must be non-negative.")

        if type(self.row_count) is not int or self.row_count < 0:
            raise ValueError("NVD promotion row_count must be non-negative.")

        if self.row_count != self.total_results:
            raise ValueError("NVD promotion row_count must equal total_results.")

        if type(self.page_count) is not int or self.page_count <= 0:
            raise ValueError("NVD promotion page_count must be positive.")

        if type(self.warning_count) is not int or self.warning_count < 0:
            raise ValueError("NVD promotion warning_count must be non-negative.")

    @staticmethod
    def _require_utc(
        value: datetime,
        label: str,
    ) -> datetime:
        """Normalize one timezone-aware timestamp to UTC."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"NVD promotion {label} must be timezone-aware.")

        return value.astimezone(UTC)


class NvdWatermarkPromotionVerifierV1:
    """Verify persisted Silver COMPLETE evidence before promotion."""

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

    _BRONZE_PAGE_REQUIRED_KEYS = frozenset(
        {
            "key",
            "page_start",
            "role",
            "sha256",
            "size_bytes",
            "source_timestamp",
            "version_id",
        }
    )

    def __init__(
        self,
        *,
        transition_validator: (NvdWatermarkTransitionValidator | None) = None,
    ) -> None:
        """Initialize promotion validator dependencies."""
        self._transition_validator = (
            transition_validator
            if transition_validator is not None
            else NvdWatermarkTransitionValidator()
        )

    def verify(
        self,
        *,
        committed_through_at: datetime,
        candidate: NvdWatermarkCandidate,
        silver_manifest: NvdPersistedObjectPayloadV1,
        silver_parquet: NvdPersistedObjectPayloadV1,
    ) -> NvdWatermarkPromotionEligibilityV1:
        """Return eligibility only after all persisted evidence verifies."""
        try:
            self._transition_validator.validate(
                committed_through_at=committed_through_at,
                candidate=candidate,
            )
        except ValueError as exc:
            raise InvalidNvdWatermarkPromotionEvidenceError(str(exc)) from exc

        document = self._parse_canonical_manifest(silver_manifest.raw_bytes)

        self._require_exact_keys(
            document,
            self._TOP_LEVEL_KEYS,
            "Silver COMPLETE manifest",
        )

        if (
            self._require_str(
                document,
                "completion_status",
            )
            != "complete"
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError("NVD Silver manifest is not COMPLETE.")

        if (
            self._require_str(
                document,
                "manifest_version",
            )
            != "1"
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Unsupported NVD Silver manifest version."
            )

        if (
            self._require_str(
                document,
                "dataset",
            )
            != NVD_CVE_VERSIONS_SCHEMA_NAME
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "NVD Silver manifest dataset is invalid."
            )

        if (
            self._require_int(
                document,
                "schema_version",
                minimum=1,
            )
            != NVD_CVE_VERSIONS_SCHEMA_VERSION
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "NVD Silver schema version does not match contract."
            )

        if (
            self._require_int(
                document,
                "writer_contract_version",
                minimum=1,
            )
            != NVD_PARQUET_WRITER_CONTRACT_VERSION
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "NVD Silver writer contract version is invalid."
            )

        if (
            self._require_str(
                document,
                "source_kind",
            )
            != "incremental"
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Only incremental NVD Silver batches are eligible for watermark promotion."
            )

        if (
            self._require_str(
                document,
                "source_batch_id",
            )
            != candidate.update_id
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "NVD Silver source_batch_id does not match watermark candidate."
            )

        expected_base = (
            "silver/nvd/cve/"
            f"schema_version={NVD_CVE_VERSIONS_SCHEMA_VERSION}/"
            "source_kind=incremental/"
            f"update_id={candidate.update_id}"
        )

        expected_manifest_key = f"{expected_base}/manifest.json"
        expected_parquet_key = f"{expected_base}/part-00000.parquet"

        if silver_manifest.key != expected_manifest_key:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Persisted NVD Silver manifest key is not deterministic."
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

        if (
            self._require_str(
                bronze_manifest,
                "key",
            )
            != candidate.bronze_manifest_key
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Silver manifest Bronze key does not match candidate."
            )

        if (
            self._require_str(
                bronze_manifest,
                "version_id",
            )
            != candidate.bronze_manifest_version_id
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Silver manifest Bronze VersionId does not match candidate."
            )

        if (
            self._require_sha256(
                bronze_manifest,
                "sha256",
            )
            != candidate.bronze_manifest_sha256
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Silver manifest Bronze SHA-256 does not match candidate."
            )

        self._require_int(
            bronze_manifest,
            "size_bytes",
            minimum=1,
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

        if (
            self._require_str(
                source_coordinates,
                "update_id",
            )
            != candidate.update_id
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Silver source update_id does not match candidate."
            )

        if (
            self._require_str(
                source_coordinates,
                "window_start_at",
            )
            != candidate.canonical_window_start_at
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Silver source window start does not match candidate."
            )

        if (
            self._require_str(
                source_coordinates,
                "window_end_at",
            )
            != candidate.canonical_window_end_at
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Silver source window end does not match candidate."
            )

        manifest_total_results = self._require_int(
            source_coordinates,
            "total_results",
            minimum=0,
        )

        if manifest_total_results != candidate.total_results:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Silver total_results does not match candidate."
            )

        bronze_objects = self._require_list(
            document,
            "bronze_objects",
        )

        if len(bronze_objects) != candidate.page_count:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Silver Bronze page inventory count does not match candidate."
            )

        seen_page_keys: set[str] = set()

        for index, value in enumerate(bronze_objects):
            page = self._require_object_value(
                value,
                f"bronze_objects[{index}]",
            )

            self._require_exact_keys(
                page,
                self._BRONZE_PAGE_REQUIRED_KEYS,
                f"bronze_objects[{index}]",
            )

            if self._require_str(page, "role") != "page":
                raise InvalidNvdWatermarkPromotionEvidenceError(
                    "Watermark promotion requires only incremental Bronze page objects."
                )

            key = self._require_str(
                page,
                "key",
            )

            if key in seen_page_keys:
                raise InvalidNvdWatermarkPromotionEvidenceError(
                    "Silver Bronze inventory contains duplicate page key."
                )

            seen_page_keys.add(key)

            self._require_str(
                page,
                "version_id",
            )
            self._require_sha256(
                page,
                "sha256",
            )
            self._require_int(
                page,
                "size_bytes",
                minimum=1,
            )
            self._require_int(
                page,
                "page_start",
                minimum=0,
            )
            self._require_str(
                page,
                "source_timestamp",
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

        if (
            self._require_str(
                silver_object,
                "key",
            )
            != expected_parquet_key
        ):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Silver Parquet key is not deterministic."
            )

        if silver_parquet.key != expected_parquet_key:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Persisted Silver Parquet key does not match manifest."
            )

        expected_parquet_version = self._require_str(
            silver_object,
            "version_id",
        )

        if silver_parquet.version_id != expected_parquet_version:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Persisted Silver Parquet VersionId does not match COMPLETE manifest."
            )

        expected_parquet_sha256 = self._require_sha256(
            silver_object,
            "sha256",
        )

        if silver_parquet.sha256 != expected_parquet_sha256:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Persisted Silver Parquet SHA-256 does not match COMPLETE manifest."
            )

        expected_parquet_size = self._require_int(
            silver_object,
            "size_bytes",
            minimum=1,
        )

        if silver_parquet.size_bytes != expected_parquet_size:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Persisted Silver Parquet size does not match COMPLETE manifest."
            )

        if not silver_parquet.raw_bytes.startswith(
            b"PAR1"
        ) or not silver_parquet.raw_bytes.endswith(b"PAR1"):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Persisted Silver object does not have Parquet framing."
            )

        row_count = self._require_int(
            silver_object,
            "row_count",
            minimum=0,
        )

        if row_count != candidate.total_results:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Silver row_count does not match candidate total_results."
            )

        logical_record_set_sha256 = self._require_sha256(
            document,
            "logical_record_set_sha256",
        )

        warnings = self._require_list(
            document,
            "warnings",
        )
        normalized_warnings: list[str] = []

        for index, warning in enumerate(warnings):
            if not isinstance(warning, str) or not warning.strip():
                raise InvalidNvdWatermarkPromotionEvidenceError(
                    f"Silver warning at index {index} is invalid."
                )

            normalized_warnings.append(warning)

        if normalized_warnings != sorted(set(normalized_warnings)):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "Silver manifest warnings must be sorted and unique."
            )

        return NvdWatermarkPromotionEligibilityV1(
            update_id=candidate.update_id,
            validated_committed_through_at=(committed_through_at),
            next_committed_through_at=(candidate.window_end_at),
            bronze_manifest_key=(candidate.bronze_manifest_key),
            bronze_manifest_version_id=(candidate.bronze_manifest_version_id),
            bronze_manifest_sha256=(candidate.bronze_manifest_sha256),
            silver_manifest_key=(silver_manifest.key),
            silver_manifest_version_id=(silver_manifest.version_id),
            silver_manifest_sha256=(silver_manifest.sha256),
            silver_parquet_key=(silver_parquet.key),
            silver_parquet_version_id=(silver_parquet.version_id),
            silver_parquet_sha256=(silver_parquet.sha256),
            logical_record_set_sha256=(logical_record_set_sha256),
            total_results=candidate.total_results,
            row_count=row_count,
            page_count=candidate.page_count,
            warning_count=len(normalized_warnings),
        )

    def _parse_canonical_manifest(
        self,
        raw_bytes: bytes,
    ) -> dict[str, object]:
        """Parse and require exact canonical Silver manifest encoding."""
        try:
            decoded = json.loads(raw_bytes.decode("utf-8"))
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "NVD Silver manifest is not valid UTF-8 JSON."
            ) from exc

        document = self._require_object_value(
            decoded,
            "Silver COMPLETE manifest",
        )

        try:
            canonical = (
                json.dumps(
                    document,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                    allow_nan=False,
                )
                + "\n"
            ).encode("utf-8")
        except ValueError as exc:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "NVD Silver manifest contains non-canonical JSON values."
            ) from exc

        if raw_bytes != canonical:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                "NVD Silver manifest bytes are not canonical."
            )

        return document

    @staticmethod
    def _require_exact_keys(
        document: dict[str, object],
        expected: frozenset[str],
        label: str,
    ) -> None:
        """Require an internal manifest object to match contract exactly."""
        actual = frozenset(document)

        if actual != expected:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                f"{label} fields do not match the v1 contract."
            )

    @staticmethod
    def _require_object(
        document: dict[str, object],
        key: str,
    ) -> dict[str, object]:
        """Read one required JSON object field."""
        if key not in document:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                f"Missing Silver manifest field {key!r}."
            )

        return NvdWatermarkPromotionVerifierV1._require_object_value(
            document[key],
            key,
        )

    @staticmethod
    def _require_object_value(
        value: object,
        label: str,
    ) -> dict[str, object]:
        """Validate and narrow one JSON object."""
        if not isinstance(value, dict):
            raise InvalidNvdWatermarkPromotionEvidenceError(f"{label} must be a JSON object.")

        raw_mapping = cast(
            dict[object, object],
            value,
        )

        result: dict[str, object] = {}

        for key, item in raw_mapping.items():
            if not isinstance(key, str):
                raise InvalidNvdWatermarkPromotionEvidenceError(
                    f"{label} contains a non-string key."
                )

            result[key] = item

        return result

    @staticmethod
    def _require_list(
        document: dict[str, object],
        key: str,
    ) -> list[object]:
        """Read one required JSON array field."""
        if key not in document:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                f"Missing Silver manifest field {key!r}."
            )

        value = document[key]

        if not isinstance(value, list):
            raise InvalidNvdWatermarkPromotionEvidenceError(
                f"Silver manifest field {key!r} must be an array."
            )

        return cast(
            list[object],
            value,
        )

    @staticmethod
    def _require_str(
        document: dict[str, object],
        key: str,
    ) -> str:
        """Read one required non-empty string field."""
        if key not in document:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                f"Missing Silver manifest field {key!r}."
            )

        value = document[key]

        if not isinstance(value, str) or not value.strip():
            raise InvalidNvdWatermarkPromotionEvidenceError(
                f"Silver manifest field {key!r} must be a non-empty string."
            )

        return value

    @staticmethod
    def _require_int(
        document: dict[str, object],
        key: str,
        *,
        minimum: int,
    ) -> int:
        """Read one required bounded integer field."""
        if key not in document:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                f"Missing Silver manifest field {key!r}."
            )

        value = document[key]

        if type(value) is not int or value < minimum:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                f"Silver manifest field {key!r} must be an integer >= {minimum}."
            )

        return value

    @staticmethod
    def _require_sha256(
        document: dict[str, object],
        key: str,
    ) -> str:
        """Read one required lowercase SHA-256 field."""
        value = NvdWatermarkPromotionVerifierV1._require_str(
            document,
            key,
        )

        if _SHA256_PATTERN.fullmatch(value) is None:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                f"Silver manifest field {key!r} is not SHA-256."
            )

        return value


class NvdWatermarkPromotionEligibilitySerializerV1:
    """Serialize watermark promotion eligibility deterministically."""

    def serialize(
        self,
        eligibility: NvdWatermarkPromotionEligibilityV1,
    ) -> bytes:
        """Return canonical promotion-proof JSON bytes."""
        document: dict[str, object] = {
            "bronze_manifest": {
                "key": eligibility.bronze_manifest_key,
                "sha256": eligibility.bronze_manifest_sha256,
                "version_id": (eligibility.bronze_manifest_version_id),
            },
            "eligible": eligibility.ELIGIBLE,
            "logical_record_set_sha256": (eligibility.logical_record_set_sha256),
            "next_committed_through_at": self._format_utc(eligibility.next_committed_through_at),
            "page_count": eligibility.page_count,
            "promotion_version": eligibility.PROMOTION_VERSION,
            "row_count": eligibility.row_count,
            "silver_manifest": {
                "key": eligibility.silver_manifest_key,
                "sha256": eligibility.silver_manifest_sha256,
                "version_id": (eligibility.silver_manifest_version_id),
            },
            "silver_parquet": {
                "key": eligibility.silver_parquet_key,
                "sha256": eligibility.silver_parquet_sha256,
                "version_id": (eligibility.silver_parquet_version_id),
            },
            "source": eligibility.SOURCE,
            "source_interface": eligibility.SOURCE_INTERFACE,
            "state": eligibility.STATE,
            "total_results": eligibility.total_results,
            "update_id": eligibility.update_id,
            "validated_committed_through_at": self._format_utc(
                eligibility.validated_committed_through_at
            ),
            "warning_count": eligibility.warning_count,
        }

        text = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )

        return f"{text}\n".encode()

    @staticmethod
    def _format_utc(
        value: datetime,
    ) -> str:
        """Serialize one UTC timestamp deterministically."""
        normalized = value.astimezone(UTC)

        timespec = "microseconds" if normalized.microsecond else "seconds"

        return normalized.isoformat(timespec=timespec).replace("+00:00", "Z")
