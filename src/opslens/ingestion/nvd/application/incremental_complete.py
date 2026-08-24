"""Strict parsing and persisted evidence for NVD incremental COMPLETE manifests."""

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifest,
    NvdIncrementalManifestSerializer,
    NvdIncrementalStoredPage,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class NvdIncrementalManifestParseError(ValueError):
    """Raised when incremental COMPLETE manifest bytes are invalid."""


@dataclass(frozen=True, slots=True)
class NvdPersistedIncrementalManifest:
    """Represent one exact persisted incremental COMPLETE manifest."""

    manifest: NvdIncrementalManifest
    payload: bytes
    version_id: str
    etag: str | None
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        """Validate persisted COMPLETE evidence."""
        if not self.payload:
            raise ValueError(
                "Persisted NVD incremental manifest payload cannot be empty."
            )

        if not self.version_id:
            raise ValueError(
                "Persisted NVD incremental manifest VersionId cannot be empty."
            )

        if not _SHA256_PATTERN.fullmatch(self.sha256):
            raise ValueError(
                "Persisted NVD incremental manifest SHA-256 must contain "
                "64 lowercase hexadecimal characters."
            )

        if self.size_bytes != len(self.payload):
            raise ValueError(
                "Persisted NVD incremental manifest size does not match payload."
            )

        actual_sha256 = hashlib.sha256(
            self.payload
        ).hexdigest()

        if actual_sha256 != self.sha256:
            raise ValueError(
                "Persisted NVD incremental manifest SHA-256 does not "
                "match payload bytes."
            )


class NvdIncrementalManifestParser:
    """Parse strict canonical incremental COMPLETE manifest bytes."""

    REQUIRED_FIELDS = frozenset(
        {
            "completion_status",
            "manifest_version",
            "page_count",
            "pages",
            "source",
            "source_format",
            "source_interface",
            "source_version",
            "total_results",
            "update_id",
            "window_end_at",
            "window_start_at",
        }
    )

    PAGE_REQUIRED_FIELDS = frozenset(
        {
            "key",
            "results_per_page",
            "sha256",
            "size_bytes",
            "source_timestamp",
            "start_index",
            "total_results",
            "version_id",
        }
    )

    def __init__(self) -> None:
        """Initialize the parser with canonical serialization support."""
        self._serializer = NvdIncrementalManifestSerializer()

    def parse(
        self,
        payload: bytes,
    ) -> NvdIncrementalManifest:
        """Parse and validate one canonical COMPLETE manifest."""
        if not payload:
            raise NvdIncrementalManifestParseError(
                "NVD incremental COMPLETE manifest payload cannot be empty."
            )

        try:
            document_value: object = json.loads(
                payload.decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NvdIncrementalManifestParseError(
                "NVD incremental COMPLETE manifest is not valid UTF-8 JSON."
            ) from exc

        document = self._require_mapping(
            document_value,
            context="manifest",
        )

        self._require_exact_fields(
            document,
            expected=self.REQUIRED_FIELDS,
            context="manifest",
        )

        self._require_constant(
            document["manifest_version"],
            NvdIncrementalManifest.MANIFEST_VERSION,
            field_name="manifest_version",
        )
        self._require_constant(
            document["completion_status"],
            NvdIncrementalManifest.COMPLETION_STATUS,
            field_name="completion_status",
        )
        self._require_constant(
            document["source"],
            NvdIncrementalManifest.SOURCE,
            field_name="source",
        )
        self._require_constant(
            document["source_interface"],
            NvdIncrementalManifest.SOURCE_INTERFACE,
            field_name="source_interface",
        )
        self._require_constant(
            document["source_format"],
            NvdIncrementalManifest.SOURCE_FORMAT,
            field_name="source_format",
        )
        self._require_constant(
            document["source_version"],
            NvdIncrementalManifest.SOURCE_VERSION,
            field_name="source_version",
        )

        pages_value = document["pages"]

        if not isinstance(pages_value, list):
            raise NvdIncrementalManifestParseError(
                "NVD incremental COMPLETE manifest pages must be an array."
            )

        page_values = cast(
            list[object],
            pages_value,
        )

        pages = tuple(
            self._parse_page(
                page_value,
                index=index,
            )
            for index, page_value in enumerate(page_values)
        )

        declared_page_count = self._require_integer(
            document["page_count"],
            field_name="page_count",
            minimum=1,
        )

        if declared_page_count != len(pages):
            raise NvdIncrementalManifestParseError(
                "NVD incremental COMPLETE manifest page_count does not "
                "match pages inventory."
            )

        try:
            manifest = NvdIncrementalManifest(
                update_id=self._require_string(
                    document["update_id"],
                    field_name="update_id",
                ),
                window_start_at=self._parse_datetime(
                    document["window_start_at"],
                    field_name="window_start_at",
                ),
                window_end_at=self._parse_datetime(
                    document["window_end_at"],
                    field_name="window_end_at",
                ),
                total_results=self._require_integer(
                    document["total_results"],
                    field_name="total_results",
                    minimum=0,
                ),
                pages=pages,
            )
        except ValueError as exc:
            raise NvdIncrementalManifestParseError(
                "NVD incremental COMPLETE manifest domain evidence is invalid."
            ) from exc

        canonical_payload = self._serializer.serialize(
            manifest
        )

        if canonical_payload != payload:
            raise NvdIncrementalManifestParseError(
                "NVD incremental COMPLETE manifest payload is not canonical."
            )

        return manifest

    def _parse_page(
        self,
        value: object,
        *,
        index: int,
    ) -> NvdIncrementalStoredPage:
        """Parse one strict persisted-page document."""
        page = self._require_mapping(
            value,
            context=f"page[{index}]",
        )

        self._require_exact_fields(
            page,
            expected=self.PAGE_REQUIRED_FIELDS,
            context=f"page[{index}]",
        )

        try:
            return NvdIncrementalStoredPage(
                key=self._require_string(
                    page["key"],
                    field_name="key",
                ),
                version_id=self._require_string(
                    page["version_id"],
                    field_name="version_id",
                ),
                size_bytes=self._require_integer(
                    page["size_bytes"],
                    field_name="size_bytes",
                    minimum=1,
                ),
                sha256=self._require_string(
                    page["sha256"],
                    field_name="sha256",
                ),
                start_index=self._require_integer(
                    page["start_index"],
                    field_name="start_index",
                    minimum=0,
                ),
                results_per_page=self._require_integer(
                    page["results_per_page"],
                    field_name="results_per_page",
                    minimum=0,
                ),
                total_results=self._require_integer(
                    page["total_results"],
                    field_name="total_results",
                    minimum=0,
                ),
                source_timestamp=self._require_string(
                    page["source_timestamp"],
                    field_name="source_timestamp",
                ),
            )
        except ValueError as exc:
            raise NvdIncrementalManifestParseError(
                f"NVD incremental COMPLETE manifest page[{index}] is invalid."
            ) from exc

    @staticmethod
    def _require_mapping(
        value: object,
        *,
        context: str,
    ) -> Mapping[str, object]:
        """Require one JSON object."""
        if not isinstance(value, dict):
            raise NvdIncrementalManifestParseError(
                f"NVD incremental COMPLETE {context} must be an object."
            )

        return cast(
            Mapping[str, object],
            value,
        )

    @staticmethod
    def _require_exact_fields(
        document: Mapping[str, object],
        *,
        expected: frozenset[str],
        context: str,
    ) -> None:
        """Require exactly the supported JSON fields."""
        actual = frozenset(document.keys())

        missing = expected - actual
        unexpected = actual - expected

        if missing:
            raise NvdIncrementalManifestParseError(
                "NVD incremental COMPLETE "
                f"{context} is missing fields: {sorted(missing)}."
            )

        if unexpected:
            raise NvdIncrementalManifestParseError(
                "NVD incremental COMPLETE "
                f"{context} contains unexpected fields: "
                f"{sorted(unexpected)}."
            )

    @staticmethod
    def _require_constant(
        value: object,
        expected: str,
        *,
        field_name: str,
    ) -> None:
        """Require one exact versioned/schema constant."""
        if value != expected:
            raise NvdIncrementalManifestParseError(
                "NVD incremental COMPLETE manifest "
                f"{field_name} must equal '{expected}'."
            )

    @staticmethod
    def _require_string(
        value: object,
        *,
        field_name: str,
    ) -> str:
        """Require one non-empty string."""
        if not isinstance(value, str) or not value:
            raise NvdIncrementalManifestParseError(
                "NVD incremental COMPLETE manifest "
                f"{field_name} must be a non-empty string."
            )

        return value

    @staticmethod
    def _require_integer(
        value: object,
        *,
        field_name: str,
        minimum: int,
    ) -> int:
        """Require one integer with a lower bound."""
        if type(value) is not int or value < minimum:
            raise NvdIncrementalManifestParseError(
                "NVD incremental COMPLETE manifest "
                f"{field_name} must be an integer >= {minimum}."
            )

        return value

    @staticmethod
    def _parse_datetime(
        value: object,
        *,
        field_name: str,
    ) -> datetime:
        """Parse one timezone-aware ISO-8601 timestamp."""
        text = NvdIncrementalManifestParser._require_string(
            value,
            field_name=field_name,
        )

        parse_value = (
            f"{text[:-1]}+00:00"
            if text.endswith("Z")
            else text
        )

        try:
            parsed = datetime.fromisoformat(
                parse_value
            )
        except ValueError as exc:
            raise NvdIncrementalManifestParseError(
                "NVD incremental COMPLETE manifest "
                f"{field_name} is not valid ISO-8601."
            ) from exc

        if (
            parsed.tzinfo is None
            or parsed.utcoffset() is None
        ):
            raise NvdIncrementalManifestParseError(
                "NVD incremental COMPLETE manifest "
                f"{field_name} must be timezone-aware."
            )

        return parsed
