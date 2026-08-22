"""Serialization-boundary models for NVD Silver schema v1."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from opslens.transformation.nvd.domain.models import (
    NvdCpeConfigurations,
    NvdCveCollections,
    NvdCveCoreRecord,
    NvdCvssMetrics,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class NvdSilverSourceKind(StrEnum):
    """Supported Bronze source forms for NVD Silver v1."""

    BOOTSTRAP = "bootstrap"
    INCREMENTAL = "incremental"


@dataclass(frozen=True, slots=True)
class NvdSilverProvenanceV1:
    """Carry exact source evidence identifiers into Silver schema v1."""

    source_kind: NvdSilverSourceKind
    source_batch_id: str
    observation_id: str
    source_observed_at: datetime

    bronze_manifest_key: str
    bronze_manifest_version_id: str
    bronze_manifest_sha256: str

    bronze_object_key: str
    bronze_object_version_id: str
    bronze_object_sha256: str
    bronze_record_index: int

    bootstrap_feed_year: int | None
    bootstrap_feed_revision: str | None

    incremental_update_id: str | None
    incremental_page_start: int | None

    retrieved_at: datetime

    def __post_init__(self) -> None:
        """Validate serialization-level provenance shape."""
        for field_name in (
            "source_batch_id",
            "observation_id",
            "bronze_manifest_key",
            "bronze_manifest_version_id",
            "bronze_object_key",
            "bronze_object_version_id",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"NVD Silver {field_name} cannot be empty.")

        for field_name in (
            "bronze_manifest_sha256",
            "bronze_object_sha256",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, str):
                raise ValueError(f"NVD Silver {field_name} must be a string.")

            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"NVD Silver {field_name} must be a lowercase SHA-256 digest.")

        if type(self.bronze_record_index) is not int:
            raise ValueError("NVD Silver bronze_record_index must be an integer.")

        if self.bronze_record_index < 0:
            raise ValueError("NVD Silver bronze_record_index cannot be negative.")

        self._require_utc(
            self.source_observed_at,
            "source_observed_at",
        )
        self._require_utc(
            self.retrieved_at,
            "retrieved_at",
        )

        if self.source_kind is NvdSilverSourceKind.BOOTSTRAP:
            self._validate_bootstrap()
        elif self.source_kind is NvdSilverSourceKind.INCREMENTAL:
            self._validate_incremental()
        else:
            raise ValueError(f"Unsupported NVD Silver source_kind {self.source_kind!r}.")

    def _validate_bootstrap(self) -> None:
        """Require bootstrap-only source coordinates."""
        if type(self.bootstrap_feed_year) is not int:
            raise ValueError("Bootstrap NVD Silver provenance requires bootstrap_feed_year.")

        if self.bootstrap_feed_year < 1900:
            raise ValueError("NVD bootstrap_feed_year is outside the supported range.")

        if self.bootstrap_feed_revision is None or not self.bootstrap_feed_revision.strip():
            raise ValueError("Bootstrap NVD Silver provenance requires bootstrap_feed_revision.")

        if self.incremental_update_id is not None:
            raise ValueError("Bootstrap provenance cannot contain incremental_update_id.")

        if self.incremental_page_start is not None:
            raise ValueError("Bootstrap provenance cannot contain incremental_page_start.")

    def _validate_incremental(self) -> None:
        """Require incremental-only source coordinates."""
        if self.incremental_update_id is None or not self.incremental_update_id.strip():
            raise ValueError("Incremental NVD Silver provenance requires incremental_update_id.")

        if type(self.incremental_page_start) is not int:
            raise ValueError("Incremental NVD Silver provenance requires incremental_page_start.")

        if self.incremental_page_start < 0:
            raise ValueError("NVD incremental_page_start cannot be negative.")

        if self.bootstrap_feed_year is not None:
            raise ValueError("Incremental provenance cannot contain bootstrap_feed_year.")

        if self.bootstrap_feed_revision is not None:
            raise ValueError("Incremental provenance cannot contain bootstrap_feed_revision.")

    @staticmethod
    def _require_utc(
        value: datetime,
        field_name: str,
    ) -> None:
        """Require an offset-aware UTC datetime."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"NVD Silver {field_name} must be timezone-aware.")

        offset = value.utcoffset()

        if offset is None or offset.total_seconds() != 0:
            raise ValueError(f"NVD Silver {field_name} must be normalized to UTC.")


@dataclass(frozen=True, slots=True)
class NvdSilverRecordV1:
    """Aggregate one fully normalized observed NVD CVE for serialization."""

    core: NvdCveCoreRecord
    collections: NvdCveCollections
    cvss: NvdCvssMetrics
    configurations: NvdCpeConfigurations
    provenance: NvdSilverProvenanceV1
