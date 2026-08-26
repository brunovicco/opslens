"""Load exact persisted authority for permanent NVD analytics projection."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, cast

from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkParserV1,
    NvdWatermarkSilverPromotionCommitV1,
)
from opslens.transformation.nvd.application.analytics_projection_models import (
    NvdAnalyticsExactObjectRefV1,
    NvdBootstrapAnalyticsProjectionRequestV1,
    NvdIncrementalAnalyticsProjectionRequestV1,
)
from opslens.transformation.nvd.completion.promotion import (
    NvdPersistedObjectPayloadV1,
)
from opslens.transformation.nvd.serialization.parquet import (
    NVD_PARQUET_WRITER_CONTRACT_VERSION,
)
from opslens.transformation.nvd.serialization.schema import (
    NVD_CVE_VERSIONS_SCHEMA_NAME,
    NVD_CVE_VERSIONS_SCHEMA_VERSION,
)

NVD_ANALYTICS_MAX_WATERMARK_BYTES = 1 * 1024 * 1024
NVD_ANALYTICS_MAX_SILVER_COMPLETE_BYTES = 1 * 1024 * 1024
NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY = (
    "control/nvd/cve/incremental/watermark.json"
)


class InvalidNvdAnalyticsProjectionEvidenceError(ValueError):
    """Raised when exact persisted evidence cannot authorize analytics."""


class NvdAnalyticsProjectionNotEligibleError(ValueError):
    """Raised when persisted authority is valid but not projection-eligible."""


class NvdAnalyticsExactObjectReader(Protocol):
    """Read one exact immutable S3 object version within a hard byte bound."""

    def read_exact(
        self,
        *,
        key: str,
        version_id: str,
        max_bytes: int,
    ) -> NvdPersistedObjectPayloadV1:
        """Return exact persisted bytes for one key and VersionId."""
        ...


@dataclass(frozen=True, slots=True)
class _ParsedSilverCompletionV1:
    """Carry the subset of canonical Silver COMPLETE needed by analytics."""

    source_kind: str
    source_batch_id: str
    source_coordinates: dict[str, object]
    silver_parquet: NvdAnalyticsExactObjectRefV1
    row_count: int
    logical_record_set_sha256: str


class NvdAnalyticsProjectionEvidenceLoaderV1:
    """Derive analytics eligibility only from exact persisted authority."""

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
    _SILVER_OBJECT_KEYS = frozenset(
        {
            "key",
            "row_count",
            "sha256",
            "size_bytes",
            "version_id",
        }
    )
    _INCREMENTAL_COORDINATE_KEYS = frozenset(
        {
            "total_results",
            "update_id",
            "window_end_at",
            "window_start_at",
        }
    )
    _BOOTSTRAP_COORDINATE_KEYS = frozenset(
        {
            "feed_revision",
            "feed_year",
            "source_observed_at",
        }
    )

    def __init__(
        self,
        *,
        object_reader: NvdAnalyticsExactObjectReader,
        watermark_parser: NvdAuthoritativeWatermarkParserV1 | None = None,
    ) -> None:
        """Initialize exact-read and canonical-watermark dependencies."""
        self._object_reader = object_reader
        self._watermark_parser = (
            watermark_parser
            if watermark_parser is not None
            else NvdAuthoritativeWatermarkParserV1()
        )

    def load_incremental(
        self,
        *,
        watermark_key: str,
        watermark_version_id: str,
    ) -> NvdIncrementalAnalyticsProjectionRequestV1:
        """Load one exact committed watermark and derive incremental eligibility."""
        if watermark_key != NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics incremental watermark key is not canonical."
            )

        watermark_payload = self._object_reader.read_exact(
            key=watermark_key,
            version_id=watermark_version_id,
            max_bytes=NVD_ANALYTICS_MAX_WATERMARK_BYTES,
        )

        try:
            watermark = self._watermark_parser.parse(
                watermark_payload.raw_bytes
            )
        except ValueError as exc:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics watermark evidence is invalid."
            ) from exc

        basis = watermark.commit_basis
        if not isinstance(
            basis,
            NvdWatermarkSilverPromotionCommitV1,
        ):
            raise NvdAnalyticsProjectionNotEligibleError(
                "NVD analytics incremental projection requires "
                "silver_complete_promotion authority."
            )

        manifest_payload = self._object_reader.read_exact(
            key=basis.silver_manifest.key,
            version_id=basis.silver_manifest.version_id,
            max_bytes=NVD_ANALYTICS_MAX_SILVER_COMPLETE_BYTES,
        )

        if manifest_payload.sha256 != basis.silver_manifest.sha256:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Silver COMPLETE SHA-256 does not match watermark authority."
            )

        parsed = self._parse_silver_completion(
            manifest_payload.raw_bytes
        )

        if parsed.source_kind != "incremental":
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics watermark must reference incremental Silver COMPLETE."
            )

        if parsed.source_batch_id != basis.update_id:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Silver source_batch_id does not match watermark update_id."
            )

        self._require_exact_keys(
            parsed.source_coordinates,
            self._INCREMENTAL_COORDINATE_KEYS,
            "incremental Silver source_coordinates",
        )

        if (
            self._require_str(
                parsed.source_coordinates,
                "update_id",
            )
            != basis.update_id
        ):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Silver source update_id does not match watermark authority."
            )

        if (
            self._require_int(
                parsed.source_coordinates,
                "total_results",
                minimum=0,
            )
            != parsed.row_count
        ):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics incremental total_results does not match row_count."
            )

        if (
            self._require_str(
                parsed.source_coordinates,
                "window_start_at",
            )
            != self._canonical_utc(
                basis.previous_committed_through_at
            )
        ):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Silver window start does not match committed authority."
            )

        if (
            self._require_str(
                parsed.source_coordinates,
                "window_end_at",
            )
            != self._canonical_utc(
                watermark.committed_through_at
            )
        ):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Silver window end does not match committed authority."
            )

        if parsed.logical_record_set_sha256 != basis.logical_record_set_sha256:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics logical record-set SHA-256 does not match watermark authority."
            )

        expected_parquet = basis.silver_parquet
        if (
            parsed.silver_parquet.key != expected_parquet.key
            or parsed.silver_parquet.version_id
            != expected_parquet.version_id
            or parsed.silver_parquet.sha256 != expected_parquet.sha256
        ):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Silver Parquet evidence does not match watermark authority."
            )

        return NvdIncrementalAnalyticsProjectionRequestV1(
            update_id=basis.update_id,
            committed_through_at=watermark.committed_through_at,
            silver_manifest=NvdAnalyticsExactObjectRefV1(
                key=manifest_payload.key,
                version_id=manifest_payload.version_id,
                sha256=manifest_payload.sha256,
                size_bytes=manifest_payload.size_bytes,
            ),
            silver_parquet=parsed.silver_parquet,
            row_count=parsed.row_count,
            logical_record_set_sha256=(
                parsed.logical_record_set_sha256
            ),
        )

    def load_bootstrap(
        self,
        *,
        silver_complete_key: str,
        silver_complete_version_id: str,
    ) -> NvdBootstrapAnalyticsProjectionRequestV1:
        """Load one explicit exact Bootstrap Silver COMPLETE seed."""
        manifest_payload = self._object_reader.read_exact(
            key=silver_complete_key,
            version_id=silver_complete_version_id,
            max_bytes=NVD_ANALYTICS_MAX_SILVER_COMPLETE_BYTES,
        )
        parsed = self._parse_silver_completion(
            manifest_payload.raw_bytes
        )

        if parsed.source_kind != "bootstrap":
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Bootstrap seed requires Bootstrap Silver COMPLETE."
            )

        self._require_exact_keys(
            parsed.source_coordinates,
            self._BOOTSTRAP_COORDINATE_KEYS,
            "Bootstrap Silver source_coordinates",
        )

        feed_year = self._require_int(
            parsed.source_coordinates,
            "feed_year",
            minimum=1900,
        )
        feed_revision = self._require_str(
            parsed.source_coordinates,
            "feed_revision",
        )
        source_observed_at = self._parse_canonical_timestamp(
            self._require_str(
                parsed.source_coordinates,
                "source_observed_at",
            ),
            label="Bootstrap source_observed_at",
        )

        expected_batch_id = (
            f"feed_year={feed_year}/"
            f"feed_revision={feed_revision}"
        )
        if parsed.source_batch_id != expected_batch_id:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Bootstrap source_batch_id is not deterministic."
            )

        return NvdBootstrapAnalyticsProjectionRequestV1(
            feed_year=feed_year,
            feed_revision=feed_revision,
            source_observed_at=source_observed_at,
            silver_manifest=NvdAnalyticsExactObjectRefV1(
                key=manifest_payload.key,
                version_id=manifest_payload.version_id,
                sha256=manifest_payload.sha256,
                size_bytes=manifest_payload.size_bytes,
            ),
            silver_parquet=parsed.silver_parquet,
            row_count=parsed.row_count,
            logical_record_set_sha256=(
                parsed.logical_record_set_sha256
            ),
        )

    def _parse_silver_completion(
        self,
        payload: bytes,
    ) -> _ParsedSilverCompletionV1:
        """Parse only the canonical NVD Silver v1 COMPLETE shape."""
        document = self._parse_canonical_json_object(
            payload,
            label="NVD Silver COMPLETE",
        )
        self._require_exact_keys(
            document,
            self._TOP_LEVEL_KEYS,
            "NVD Silver COMPLETE",
        )

        if self._require_str(document, "completion_status") != "complete":
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Silver manifest is not COMPLETE."
            )

        if self._require_str(document, "manifest_version") != "1":
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Silver manifest version is unsupported."
            )

        if (
            self._require_str(document, "dataset")
            != NVD_CVE_VERSIONS_SCHEMA_NAME
        ):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Silver dataset is invalid."
            )

        if (
            self._require_int(
                document,
                "schema_version",
                minimum=1,
            )
            != NVD_CVE_VERSIONS_SCHEMA_VERSION
        ):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Silver schema version is invalid."
            )

        if (
            self._require_int(
                document,
                "writer_contract_version",
                minimum=1,
            )
            != NVD_PARQUET_WRITER_CONTRACT_VERSION
        ):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Silver writer contract version is invalid."
            )

        self._require_object(document, "bronze_manifest")
        self._require_list(document, "bronze_objects")
        self._validate_warnings(
            self._require_list(document, "warnings")
        )

        silver_object = self._require_object(
            document,
            "silver_object",
        )
        self._require_exact_keys(
            silver_object,
            self._SILVER_OBJECT_KEYS,
            "NVD Silver silver_object",
        )

        row_count = self._require_int(
            silver_object,
            "row_count",
            minimum=0,
        )
        silver_parquet = NvdAnalyticsExactObjectRefV1(
            key=self._require_str(silver_object, "key"),
            version_id=self._require_str(
                silver_object,
                "version_id",
            ),
            sha256=self._require_sha256(
                silver_object,
                "sha256",
            ),
            size_bytes=self._require_int(
                silver_object,
                "size_bytes",
                minimum=1,
            ),
        )

        return _ParsedSilverCompletionV1(
            source_kind=self._require_str(
                document,
                "source_kind",
            ),
            source_batch_id=self._require_str(
                document,
                "source_batch_id",
            ),
            source_coordinates=self._require_object(
                document,
                "source_coordinates",
            ),
            silver_parquet=silver_parquet,
            row_count=row_count,
            logical_record_set_sha256=self._require_sha256(
                document,
                "logical_record_set_sha256",
            ),
        )

    @staticmethod
    def _parse_canonical_json_object(
        payload: bytes,
        *,
        label: str,
    ) -> dict[str, object]:
        """Parse one canonical UTF-8 JSON object emitted by OpsLens."""
        if not payload:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"{label} payload cannot be empty."
            )

        try:
            decoded = json.loads(
                payload.decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"{label} must be valid UTF-8 JSON."
            ) from exc

        if not isinstance(decoded, dict):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"{label} must be a JSON object."
            )

        document = cast(dict[str, object], decoded)

        try:
            canonical_text = json.dumps(
                document,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"{label} cannot be canonicalized."
            ) from exc

        if f"{canonical_text}\n".encode() != payload:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"{label} payload is not canonical."
            )

        return document

    @staticmethod
    def _require_exact_keys(
        document: dict[str, object],
        expected: frozenset[str],
        label: str,
    ) -> None:
        """Require an exact closed JSON-object key set."""
        if frozenset(document) != expected:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"{label} fields do not match the supported contract."
            )

    @staticmethod
    def _require_object(
        document: dict[str, object],
        key: str,
    ) -> dict[str, object]:
        """Require one JSON object field."""
        value = document.get(key)
        if not isinstance(value, dict):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"NVD analytics {key} must be an object."
            )
        return cast(dict[str, object], value)

    @staticmethod
    def _require_list(
        document: dict[str, object],
        key: str,
    ) -> list[object]:
        """Require one JSON list field."""
        value = document.get(key)
        if not isinstance(value, list):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"NVD analytics {key} must be a list."
            )
        return cast(list[object], value)

    @staticmethod
    def _require_str(
        document: dict[str, object],
        key: str,
    ) -> str:
        """Require one non-empty trimmed string field."""
        value = document.get(key)
        if (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
        ):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"NVD analytics {key} must be a non-empty trimmed string."
            )
        return value

    @staticmethod
    def _require_int(
        document: dict[str, object],
        key: str,
        *,
        minimum: int,
    ) -> int:
        """Require one integer field bounded below."""
        value = document.get(key)
        if type(value) is not int or value < minimum:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"NVD analytics {key} must be an integer >= {minimum}."
            )
        return value

    @classmethod
    def _require_sha256(
        cls,
        document: dict[str, object],
        key: str,
    ) -> str:
        """Require one lowercase SHA-256 string field."""
        value = cls._require_str(document, key)
        if len(value) != 64 or any(
            character not in "0123456789abcdef"
            for character in value
        ):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"NVD analytics {key} must be a lowercase SHA-256."
            )
        return value

    @staticmethod
    def _validate_warnings(values: list[object]) -> None:
        """Require canonical sorted unique non-empty warning strings."""
        warnings: list[str] = []
        for value in values:
            if (
                not isinstance(value, str)
                or not value.strip()
                or value != value.strip()
            ):
                raise InvalidNvdAnalyticsProjectionEvidenceError(
                    "NVD analytics Silver warnings are invalid."
                )
            warnings.append(value)

        if warnings != sorted(set(warnings)):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics Silver warnings are not canonical."
            )

    @staticmethod
    def _parse_canonical_timestamp(
        value: str,
        *,
        label: str,
    ) -> datetime:
        """Parse an OpsLens canonical UTC timestamp ending in Z."""
        if not value.endswith("Z"):
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"NVD analytics {label} must be canonical UTC."
            )

        try:
            parsed = datetime.fromisoformat(
                value[:-1] + "+00:00"
            ).astimezone(UTC)
        except ValueError as exc:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"NVD analytics {label} timestamp is invalid."
            ) from exc

        if NvdAnalyticsProjectionEvidenceLoaderV1._canonical_utc(parsed) != value:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                f"NVD analytics {label} timestamp is not canonical."
            )

        return parsed

    @staticmethod
    def _canonical_utc(value: datetime) -> str:
        """Serialize a timezone-aware instant exactly like OpsLens contracts."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise InvalidNvdAnalyticsProjectionEvidenceError(
                "NVD analytics timestamp must be timezone-aware."
            )

        normalized = value.astimezone(UTC)
        timespec = (
            "microseconds"
            if normalized.microsecond
            else "seconds"
        )
        return normalized.isoformat(
            timespec=timespec
        ).replace("+00:00", "Z")
