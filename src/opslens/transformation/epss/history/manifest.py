"""Strict parser for historical EPSS Bronze manifest v1."""

from __future__ import annotations

import json
import re
from datetime import date
from typing import cast

from opslens.ingestion.epss.domain.history import EpssModelEra
from opslens.transformation.epss.history.models import (
    HistoricalEpssBronzeManifestV1,
    HistoricalEpssBronzeObjectPayloadV1,
)

_ARCHIVE_REPOSITORY = "empiricalsec/epss_scores"
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_KEYS = frozenset(
    {
        "schema_version",
        "snapshot_date",
        "archive_repository",
        "archive_commit",
        "archive_path",
        "archive_git_blob_sha1",
        "model_era",
        "source_metadata_present",
        "source_object_key",
        "source_object_version_id",
        "source_sha256",
        "compressed_size_bytes",
    }
)


class InvalidHistoricalEpssBronzeManifestError(ValueError):
    """Raised when historical Bronze manifest evidence violates v1 contract."""


class HistoricalEpssBronzeManifestParserV1:
    """Parse and validate one exact historical EPSS Bronze manifest."""

    def parse(
        self,
        payload: HistoricalEpssBronzeObjectPayloadV1,
    ) -> HistoricalEpssBronzeManifestV1:
        """Parse exact manifest bytes and bind them to their S3 coordinate."""
        try:
            decoded: object = json.loads(payload.raw_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS Bronze manifest must be valid UTF-8 JSON."
            ) from exc

        if not isinstance(decoded, dict):
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS Bronze manifest must be a JSON object."
            )
        if not all(isinstance(key, str) for key in decoded):
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS Bronze manifest keys must be strings."
            )

        value = cast(dict[str, object], decoded)
        keys: frozenset[str] = frozenset(value)
        if keys != _REQUIRED_KEYS:
            missing = sorted(_REQUIRED_KEYS - keys)
            extra = sorted(keys - _REQUIRED_KEYS)
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS Bronze manifest keys do not match schema v1: "
                f"missing={missing}, extra={extra}."
            )

        schema_version = value["schema_version"]
        if type(schema_version) is not int or schema_version != 1:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS Bronze manifest schema_version must be integer 1."
            )

        snapshot_date = self._parse_date(value["snapshot_date"])
        archive_repository = self._required_string(value, "archive_repository")
        archive_commit = self._required_string(value, "archive_commit")
        archive_path = self._required_string(value, "archive_path")
        archive_git_blob_sha1 = self._required_string(value, "archive_git_blob_sha1")
        model_era_raw = self._required_string(value, "model_era")
        source_object_key = self._required_string(value, "source_object_key")
        source_object_version_id = self._required_string(value, "source_object_version_id")
        source_sha256 = self._required_string(value, "source_sha256")

        if archive_repository != _ARCHIVE_REPOSITORY:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS archive_repository is not the approved source."
            )
        if _COMMIT_RE.fullmatch(archive_commit) is None:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS archive_commit must be a lowercase 40-character Git SHA."
            )
        if _SHA1_RE.fullmatch(archive_git_blob_sha1) is None:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS archive Git blob SHA-1 is invalid."
            )
        if _SHA256_RE.fullmatch(source_sha256) is None:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS source SHA-256 is invalid."
            )

        try:
            model_era = EpssModelEra(model_era_raw)
        except ValueError as exc:
            raise InvalidHistoricalEpssBronzeManifestError(
                f"Unsupported historical EPSS model_era: {model_era_raw!r}."
            ) from exc

        expected_model_era = EpssModelEra.for_snapshot_date(snapshot_date)
        if model_era is not expected_model_era:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS manifest model_era does not match snapshot_date."
            )

        metadata_raw = value["source_metadata_present"]
        if type(metadata_raw) is not bool:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS source_metadata_present must be boolean."
            )
        metadata_present = cast(bool, metadata_raw)
        if metadata_present is (model_era is EpssModelEra.V1):
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS source metadata presence conflicts with model era."
            )

        compressed_size_raw = value["compressed_size_bytes"]
        if type(compressed_size_raw) is not int or compressed_size_raw <= 0:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS compressed_size_bytes must be a positive integer."
            )
        compressed_size = cast(int, compressed_size_raw)

        expected_archive_path = (
            f"{snapshot_date.year}/epss_scores-{snapshot_date.isoformat()}.csv.gz"
        )
        if archive_path != expected_archive_path:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS archive_path does not match snapshot_date."
            )

        prefix = (
            "bronze/epss-history/schema_version=1/"
            f"archive_commit={archive_commit}/"
            f"snapshot_date={snapshot_date.isoformat()}"
        )
        expected_manifest_key = f"{prefix}/manifest.json"
        expected_source_key = f"{prefix}/epss_scores.csv.gz"

        if payload.key != expected_manifest_key:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS manifest S3 key does not match its internal coordinates."
            )
        if source_object_key != expected_source_key:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS source object key does not match manifest coordinates."
            )

        return HistoricalEpssBronzeManifestV1(
            snapshot_date=snapshot_date,
            archive_repository=archive_repository,
            archive_commit=archive_commit,
            archive_path=archive_path,
            archive_git_blob_sha1=archive_git_blob_sha1,
            model_era=model_era,
            source_metadata_present=metadata_present,
            source_object_key=source_object_key,
            source_object_version_id=source_object_version_id,
            source_sha256=source_sha256,
            compressed_size_bytes=compressed_size,
            manifest_key=payload.key,
            manifest_version_id=payload.version_id,
        )

    @staticmethod
    def _required_string(value: dict[str, object], key: str) -> str:
        """Return one validated non-empty manifest string field."""
        raw = value[key]
        if not isinstance(raw, str) or not raw.strip():
            raise InvalidHistoricalEpssBronzeManifestError(
                f"Historical EPSS manifest {key} must be a non-empty string."
            )
        return raw

    @staticmethod
    def _parse_date(raw: object) -> date:
        """Parse one canonical ISO snapshot date from manifest evidence."""
        if not isinstance(raw, str):
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS snapshot_date must be an ISO date string."
            )
        try:
            parsed = date.fromisoformat(raw)
        except ValueError as exc:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS snapshot_date is not a valid ISO date."
            ) from exc
        if parsed.isoformat() != raw:
            raise InvalidHistoricalEpssBronzeManifestError(
                "Historical EPSS snapshot_date must use canonical YYYY-MM-DD format."
            )
        return parsed
