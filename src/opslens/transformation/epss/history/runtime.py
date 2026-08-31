"""Runtime configuration and forward-authority discovery for historical EPSS."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date
from typing import Protocol, TypedDict

_FORWARD_PREFIX = "bronze/epss/"
_FORWARD_KEY_RE = re.compile(
    r"^bronze/epss/snapshot_date=(?P<snapshot_date>\d{4}-\d{2}-\d{2})/epss_scores\.csv\.gz$"
)


@dataclass(frozen=True, slots=True)
class HistoricalEpssRuntimeSettings:
    """Validated environment required by the dedicated historical transformer."""

    data_bucket: str
    approved_archive_commit: str

    @classmethod
    def from_environment(cls) -> "HistoricalEpssRuntimeSettings":
        """Load strict runtime settings from Lambda environment variables."""
        data_bucket = os.environ.get("EPSS_DATA_BUCKET", "").strip()
        approved_archive_commit = os.environ.get("EPSS_HISTORY_ARCHIVE_COMMIT", "").strip()
        if not data_bucket:
            raise ValueError("EPSS_DATA_BUCKET is required for historical EPSS runtime.")
        if not re.fullmatch(r"[0-9a-f]{40}", approved_archive_commit):
            raise ValueError(
                "EPSS_HISTORY_ARCHIVE_COMMIT must be a lowercase 40-character Git SHA."
            )
        return cls(
            data_bucket=data_bucket,
            approved_archive_commit=approved_archive_commit,
        )


class _S3ObjectSummary(TypedDict, total=False):
    """Represent the S3 object-list fields needed for boundary discovery."""

    Key: str


class _S3ListResponse(TypedDict, total=False):
    """Represent one ListObjectsV2 page used by boundary discovery."""

    Contents: list[_S3ObjectSummary]
    IsTruncated: bool
    NextContinuationToken: str


class HistoricalEpssForwardListClient(Protocol):
    """Define the narrow S3 list capability used for forward boundary discovery."""

    def list_objects_v2(
        self,
        *,
        Bucket: str,
        Prefix: str,
        ContinuationToken: str | None = None,
    ) -> _S3ListResponse:
        """List canonical forward EPSS object keys."""
        ...


class S3HistoricalEpssForwardBoundaryReader:
    """Discover earliest canonical forward EPSS snapshot from the target bucket."""

    def __init__(
        self,
        *,
        client: HistoricalEpssForwardListClient,
        bucket_name: str,
    ) -> None:
        """Initialize one bucket-scoped forward boundary reader."""
        normalized_bucket = bucket_name.strip()
        if not normalized_bucket:
            raise ValueError("Historical EPSS forward-boundary bucket cannot be empty.")
        self._client = client
        self._bucket_name = normalized_bucket

    def discover(self) -> date:
        """Return the earliest canonical forward snapshot date, failing closed when absent."""
        earliest: date | None = None
        continuation_token: str | None = None

        while True:
            response = self._client.list_objects_v2(
                Bucket=self._bucket_name,
                Prefix=_FORWARD_PREFIX,
                ContinuationToken=continuation_token,
            )
            for summary in response.get("Contents", []):
                key = summary.get("Key")
                if not isinstance(key, str):
                    continue
                match = _FORWARD_KEY_RE.fullmatch(key)
                if match is None:
                    continue
                raw_snapshot_date = match.group("snapshot_date")
                try:
                    snapshot_date = date.fromisoformat(raw_snapshot_date)
                except ValueError as exc:
                    raise ValueError("Forward EPSS object contains an invalid snapshot date.") from exc
                if snapshot_date.isoformat() != raw_snapshot_date:
                    raise ValueError("Forward EPSS snapshot date must be canonical.")
                if earliest is None or snapshot_date < earliest:
                    earliest = snapshot_date

            if response.get("IsTruncated") is not True:
                break
            next_token = response.get("NextContinuationToken")
            if not isinstance(next_token, str) or not next_token.strip():
                raise ValueError("Truncated forward EPSS listing is missing continuation token.")
            continuation_token = next_token

        if earliest is None:
            raise ValueError("No canonical forward EPSS snapshot exists in the target environment.")
        return earliest
