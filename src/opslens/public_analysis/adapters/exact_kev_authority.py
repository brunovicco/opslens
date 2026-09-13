"""Decode one complete KEV authority snapshot from exact immutable S3 evidence."""

import re
from collections.abc import Mapping
from datetime import date, datetime
from typing import Protocol

from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.ingestion.kev.domain.parser import KevCatalogParser
from opslens.public_analysis.adapters.exact_s3_authority_object import (
    ExactS3AuthorityObject,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_METADATA = frozenset(
    {
        "source",
        "catalog_version",
        "date_released",
        "retrieved_at",
        "sha256",
        "record_count",
    }
)


class ExactKevAuthorityError(ValueError):
    """Reject incomplete or contradictory KEV source authority."""


class ExactKevAuthorityObjectReader(Protocol):
    """Read one exact immutable object previously admitted by physical locator."""

    def read(self, *, object_key: str, version_id: str) -> ExactS3AuthorityObject:
        """Return exact S3 bytes and same-version user metadata."""
        ...


class ExactKevAuthorityReader:
    """Reconstruct complete KEV authority only from exact source bytes and metadata."""

    def __init__(
        self,
        *,
        object_reader: ExactKevAuthorityObjectReader,
        parser: KevCatalogParser,
    ) -> None:
        """Bind the exact object reader and retained KEV source parser."""
        self._object_reader = object_reader
        self._parser = parser

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        snapshot_date: str,
    ) -> KevCatalogSnapshot:
        """Materialize and verify one complete snapshot with no inferred authority."""
        expected_snapshot_date = self._snapshot_date(snapshot_date)
        source = self._object_reader.read(
            object_key=object_key,
            version_id=version_id,
        )
        metadata = self._metadata(source.metadata)

        if frozenset(metadata) != _REQUIRED_METADATA:
            raise ExactKevAuthorityError(
                "KEV authority metadata must contain exactly the required provenance fields"
            )
        if metadata["source"] != "cisa-kev":
            raise ExactKevAuthorityError("KEV authority source must equal 'cisa-kev'")

        retrieved_at = self._timestamp(metadata["retrieved_at"], field="retrieved_at")
        date_released = self._timestamp(metadata["date_released"], field="date_released")
        sha256 = metadata["sha256"]
        if _SHA256_RE.fullmatch(sha256) is None:
            raise ExactKevAuthorityError(
                "KEV authority sha256 must contain 64 lowercase hexadecimal characters"
            )
        record_count = self._positive_integer(metadata["record_count"])

        snapshot = self._parser.parse(source.payload, retrieved_at=retrieved_at)
        if snapshot.sha256 != sha256:
            raise ExactKevAuthorityError("KEV authority payload sha256 mismatch")
        if snapshot.catalog_version != metadata["catalog_version"]:
            raise ExactKevAuthorityError("KEV authority catalog version mismatch")
        if snapshot.date_released != date_released:
            raise ExactKevAuthorityError("KEV authority dateReleased mismatch")
        if snapshot.record_count != record_count:
            raise ExactKevAuthorityError("KEV authority record count mismatch")
        if snapshot.snapshot_date != expected_snapshot_date:
            raise ExactKevAuthorityError("KEV authority snapshot date mismatch")
        return snapshot

    @staticmethod
    def _metadata(items: tuple[tuple[str, str], ...]) -> Mapping[str, str]:
        """Require normalized unique metadata keys from the exact S3 boundary."""
        metadata: dict[str, str] = {}
        for key, value in items:
            normalized = key.lower()
            if normalized in metadata:
                raise ExactKevAuthorityError("KEV authority metadata contains duplicate keys")
            metadata[normalized] = value
        return metadata

    @staticmethod
    def _snapshot_date(value: str) -> str:
        """Require one canonical ISO calendar date without rewriting it."""
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ExactKevAuthorityError("snapshot_date must use YYYY-MM-DD") from exc
        if parsed.isoformat() != value:
            raise ExactKevAuthorityError("snapshot_date must use canonical YYYY-MM-DD")
        return value

    @staticmethod
    def _timestamp(value: str, *, field: str) -> datetime:
        """Require one timezone-aware ISO-8601 metadata timestamp."""
        normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ExactKevAuthorityError(
                f"KEV authority {field} must be an ISO-8601 timestamp"
            ) from exc
        if parsed.tzinfo is None:
            raise ExactKevAuthorityError(
                f"KEV authority {field} must include timezone information"
            )
        return parsed

    @staticmethod
    def _positive_integer(value: str) -> int:
        """Require one canonical positive decimal metadata integer."""
        if not value.isdigit():
            raise ExactKevAuthorityError("KEV authority record_count must be positive decimal")
        parsed = int(value)
        if parsed <= 0 or str(parsed) != value:
            raise ExactKevAuthorityError("KEV authority record_count must be canonical")
        return parsed


__all__ = [
    "ExactKevAuthorityError",
    "ExactKevAuthorityObjectReader",
    "ExactKevAuthorityReader",
]
