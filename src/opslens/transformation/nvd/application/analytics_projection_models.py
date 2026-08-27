"""Application contracts for authority-preserving NVD analytics projection."""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import ClassVar

from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_BOOTSTRAP_FEED_REVISION_PATTERN = re.compile(
    r"^(?P<timestamp>\d{8}T\d{6}Z)-(?P<sha256>[0-9a-f]{64})$"
)


@dataclass(frozen=True, slots=True)
class NvdAnalyticsExactObjectRefV1:
    """Identify one exact persisted object used by analytics projection."""

    key: str
    version_id: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        """Validate exact immutable object coordinates."""
        if not self.key.strip() or self.key != self.key.strip():
            raise ValueError(
                "NVD analytics exact object key must be non-empty and trimmed."
            )

        if not self.version_id.strip() or self.version_id != self.version_id.strip():
            raise ValueError(
                "NVD analytics exact object VersionId must be non-empty and trimmed."
            )

        if _SHA256_PATTERN.fullmatch(self.sha256) is None:
            raise ValueError(
                "NVD analytics exact object SHA-256 must be 64 lowercase hex characters."
            )

        if type(self.size_bytes) is not int or self.size_bytes <= 0:
            raise ValueError(
                "NVD analytics exact object size_bytes must be a positive integer."
            )


@dataclass(frozen=True, slots=True)
class NvdIncrementalAnalyticsProjectionRequestV1:
    """Carry one exact watermark-authorized incremental batch into projection."""

    SOURCE_KIND: ClassVar[NvdSilverSourceKind] = NvdSilverSourceKind.INCREMENTAL
    AUTHORITY_STATE: ClassVar[str] = "watermark_committed"

    update_id: str
    committed_through_at: datetime
    silver_manifest: NvdAnalyticsExactObjectRefV1
    silver_parquet: NvdAnalyticsExactObjectRefV1
    row_count: int
    logical_record_set_sha256: str

    def __post_init__(self) -> None:
        """Require exact canonical incremental projection authority."""
        if _SHA256_PATTERN.fullmatch(self.update_id) is None:
            raise ValueError(
                "NVD incremental analytics update_id must be a lowercase SHA-256."
            )

        committed = _require_utc(
            self.committed_through_at,
            label="incremental committed_through_at",
        )
        object.__setattr__(self, "committed_through_at", committed)

        if type(self.row_count) is not int or self.row_count < 0:
            raise ValueError(
                "NVD incremental analytics row_count must be a non-negative integer."
            )

        _require_sha256(
            self.logical_record_set_sha256,
            label="incremental logical_record_set_sha256",
        )

        expected_base = (
            "silver/nvd/cve/schema_version=1/"
            "source_kind=incremental/"
            f"update_id={self.update_id}"
        )
        _require_exact_key(
            actual=self.silver_manifest.key,
            expected=f"{expected_base}/manifest.json",
            label="incremental Silver COMPLETE",
        )
        _require_exact_key(
            actual=self.silver_parquet.key,
            expected=f"{expected_base}/part-00000.parquet",
            label="incremental Silver Parquet",
        )

    @property
    def source_kind(self) -> NvdSilverSourceKind:
        """Return the exact source kind represented by this request."""
        return self.SOURCE_KIND

    @property
    def source_batch_id(self) -> str:
        """Return the deterministic source batch identity."""
        return self.update_id

    @property
    def authority_state(self) -> str:
        """Return the authority state required for this request."""
        return self.AUTHORITY_STATE

    @property
    def projection_date(self) -> date:
        """Return the UTC partition date derived from committed authority."""
        return self.committed_through_at.date()


@dataclass(frozen=True, slots=True)
class NvdBootstrapAnalyticsProjectionRequestV1:
    """Carry one explicitly authorized Bootstrap Silver seed into projection."""

    SOURCE_KIND: ClassVar[NvdSilverSourceKind] = NvdSilverSourceKind.BOOTSTRAP
    AUTHORITY_STATE: ClassVar[str] = "bootstrap_verified_seed"

    feed_year: int
    feed_revision: str
    source_observed_at: datetime
    silver_manifest: NvdAnalyticsExactObjectRefV1
    silver_parquet: NvdAnalyticsExactObjectRefV1
    row_count: int
    logical_record_set_sha256: str

    def __post_init__(self) -> None:
        """Require exact canonical Bootstrap projection authority."""
        if type(self.feed_year) is not int or not 1900 <= self.feed_year <= 9999:
            raise ValueError(
                "NVD Bootstrap analytics feed_year must be an integer in [1900, 9999]."
            )

        revision_at = parse_nvd_bootstrap_feed_revision(self.feed_revision)
        if revision_at.year != self.feed_year:
            raise ValueError(
                "NVD Bootstrap analytics feed_year must match feed_revision timestamp year."
            )

        observed = _require_utc(
            self.source_observed_at,
            label="Bootstrap source_observed_at",
        )
        object.__setattr__(self, "source_observed_at", observed)

        if type(self.row_count) is not int or self.row_count <= 0:
            raise ValueError(
                "NVD Bootstrap analytics row_count must be a positive integer."
            )

        _require_sha256(
            self.logical_record_set_sha256,
            label="Bootstrap logical_record_set_sha256",
        )

        expected_base = (
            "silver/nvd/cve/schema_version=1/"
            "source_kind=bootstrap/"
            f"feed_year={self.feed_year}/"
            f"feed_revision={self.feed_revision}"
        )
        _require_exact_key(
            actual=self.silver_manifest.key,
            expected=f"{expected_base}/manifest.json",
            label="Bootstrap Silver COMPLETE",
        )
        _require_exact_key(
            actual=self.silver_parquet.key,
            expected=f"{expected_base}/part-00000.parquet",
            label="Bootstrap Silver Parquet",
        )

    @property
    def source_kind(self) -> NvdSilverSourceKind:
        """Return the exact source kind represented by this request."""
        return self.SOURCE_KIND

    @property
    def source_batch_id(self) -> str:
        """Return the deterministic source batch identity."""
        return f"feed_year={self.feed_year}/feed_revision={self.feed_revision}"

    @property
    def authority_state(self) -> str:
        """Return the authority state required for this request."""
        return self.AUTHORITY_STATE

    @property
    def projection_date(self) -> date:
        """Return the UTC partition date encoded by the feed revision."""
        return parse_nvd_bootstrap_feed_revision(self.feed_revision).date()


def parse_nvd_bootstrap_feed_revision(value: str) -> datetime:
    """Parse one canonical Bootstrap feed revision into an exact UTC instant."""
    if not value or value != value.strip():
        raise ValueError(
            "NVD Bootstrap analytics feed_revision must be non-empty and trimmed."
        )

    match = _BOOTSTRAP_FEED_REVISION_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(
            "NVD Bootstrap analytics feed_revision must match YYYYMMDDTHHMMSSZ-<sha256>."
        )

    timestamp = match.group("timestamp")

    try:
        parsed = datetime.strptime(
            timestamp,
            "%Y%m%dT%H%M%SZ",
        ).replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(
            "NVD Bootstrap analytics feed_revision timestamp is invalid."
        ) from exc

    if parsed.strftime("%Y%m%dT%H%M%SZ") != timestamp:
        raise ValueError(
            "NVD Bootstrap analytics feed_revision timestamp is not canonical."
        )

    return parsed


def _require_utc(value: datetime, *, label: str) -> datetime:
    """Require timezone evidence and normalize one timestamp to UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"NVD analytics {label} must be timezone-aware.")

    return value.astimezone(UTC)


def _require_sha256(value: str, *, label: str) -> None:
    """Require one lowercase SHA-256 digest."""
    if _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"NVD analytics {label} must be a lowercase SHA-256.")


def _require_exact_key(*, actual: str, expected: str, label: str) -> None:
    """Require one source key to match its deterministic Silver coordinate."""
    if actual != expected:
        raise ValueError(f"NVD analytics {label} key is not deterministic.")
