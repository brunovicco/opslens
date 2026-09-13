"""Decode one complete EPSS authority snapshot from exact immutable S3 evidence."""

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.public_analysis.adapters.exact_s3_authority_object import (
    ExactS3AuthorityObject,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_METADATA = frozenset({"source", "model_version", "score_date", "sha256"})


class ExactEpssAuthorityError(ValueError):
    """Reject incomplete or contradictory EPSS source authority."""


class ExactEpssAuthorityObjectReader(Protocol):
    """Read one exact immutable object previously admitted by physical locator."""

    def read(self, *, object_key: str, version_id: str) -> ExactS3AuthorityObject:
        """Return exact S3 bytes and same-version user metadata."""
        ...


class ExactEpssAuthorityReader:
    """Reconstruct complete EPSS authority only from exact source bytes and metadata."""

    def __init__(
        self,
        *,
        object_reader: ExactEpssAuthorityObjectReader,
        parser: EpssSnapshotParser,
    ) -> None:
        """Bind the exact object reader and retained EPSS source parser."""
        self._object_reader = object_reader
        self._parser = parser

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        snapshot_date: str,
    ) -> EpssSnapshot:
        """Materialize and verify one complete snapshot with no inferred authority."""
        source = self._object_reader.read(
            object_key=object_key,
            version_id=version_id,
        )
        metadata = self._metadata(source.metadata)

        if frozenset(metadata) != _REQUIRED_METADATA:
            raise ExactEpssAuthorityError(
                "EPSS authority metadata must contain exactly the required provenance fields"
            )
        if metadata["source"] != "first-epss":
            raise ExactEpssAuthorityError("EPSS authority source must equal 'first-epss'")

        score_timestamp = self._timestamp(metadata["score_date"])
        sha256 = metadata["sha256"]
        if _SHA256_RE.fullmatch(sha256) is None:
            raise ExactEpssAuthorityError(
                "EPSS authority sha256 must contain 64 lowercase hexadecimal characters"
            )

        snapshot = self._parser.parse(source.payload)
        if snapshot.sha256 != sha256:
            raise ExactEpssAuthorityError("EPSS authority payload sha256 mismatch")
        if snapshot.model_version != metadata["model_version"]:
            raise ExactEpssAuthorityError("EPSS authority model version mismatch")
        if snapshot.score_timestamp != score_timestamp:
            raise ExactEpssAuthorityError("EPSS authority score timestamp mismatch")
        if snapshot.snapshot_date != snapshot_date:
            raise ExactEpssAuthorityError("EPSS authority snapshot date mismatch")
        return snapshot

    @staticmethod
    def _metadata(items: tuple[tuple[str, str], ...]) -> Mapping[str, str]:
        """Require normalized unique metadata keys from the exact S3 boundary."""
        metadata: dict[str, str] = {}
        for key, value in items:
            normalized = key.lower()
            if normalized in metadata:
                raise ExactEpssAuthorityError(
                    "EPSS authority metadata contains duplicate keys"
                )
            metadata[normalized] = value
        return metadata

    @staticmethod
    def _timestamp(value: str) -> datetime:
        """Require one timezone-aware ISO-8601 score timestamp."""
        normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ExactEpssAuthorityError(
                "EPSS authority score_date must be an ISO-8601 timestamp"
            ) from exc
        if parsed.tzinfo is None:
            raise ExactEpssAuthorityError(
                "EPSS authority score_date must include timezone information"
            )
        return parsed


__all__ = [
    "ExactEpssAuthorityError",
    "ExactEpssAuthorityObjectReader",
    "ExactEpssAuthorityReader",
]
