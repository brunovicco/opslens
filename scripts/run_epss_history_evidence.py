#!/usr/bin/env python3
"""Run read-only Phase 2.5D-5 historical EPSS post-backfill evidence verification."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, cast

import boto3
from botocore.exceptions import ClientError

from opslens.bootstrap.epss_history_evidence import (
    HistoricalEpssEvidenceObjectV1,
    HistoricalEpssEvidenceVersionV1,
    VerifyHistoricalEpssBackfillEvidenceV1,
)
from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshotParser
from opslens.transformation.epss.adapters.outbound.parquet import PyArrowSilverEpssRecordWriter
from opslens.transformation.epss.application.key_factory import EpssSilverKeyFactory
from opslens.transformation.epss.history.preparation import (
    HistoricalEpssSilverRecordTransformer,
    PrepareHistoricalEpssSilver,
)
from opslens.transformation.epss.history.runtime import (
    HistoricalEpssForwardListClient,
    S3HistoricalEpssForwardBoundaryReader,
)
from run_epss_history_canary import GitHubArchiveReader


def parse_args() -> argparse.Namespace:
    """Parse bounded read-only evidence controls."""
    parser = argparse.ArgumentParser(
        description="Verify all frozen historical EPSS evidence without mutating AWS."
    )
    parser.add_argument(
        "--github-timeout-seconds",
        type=float,
        default=30.0,
        help="Per-request GitHub timeout for immutable inventory reads (default: 30 seconds).",
    )
    return parser.parse_args()


class S3HistoricalEpssEvidenceStore:
    """Read current and exact historical EPSS evidence from one versioned S3 bucket."""

    def __init__(self, *, client: Any, bucket_name: str) -> None:
        """Initialize the bucket-scoped read-only S3 adapter."""
        normalized_bucket = bucket_name.strip()
        if not normalized_bucket:
            raise ValueError("Historical EPSS evidence bucket cannot be empty.")
        self._client = client
        self._bucket_name = normalized_bucket

    def list_current_keys(self, *, prefix: str) -> tuple[str, ...]:
        """List all current object keys under one exact prefix."""
        paginator = self._client.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=self._bucket_name, Prefix=prefix):
            for value in page.get("Contents", []):
                key = value.get("Key")
                if not isinstance(key, str) or not key:
                    raise ValueError("S3 evidence listing returned an invalid object key.")
                keys.append(key)
        return tuple(sorted(keys))

    def read_current(self, *, key: str) -> HistoricalEpssEvidenceObjectV1:
        """Read current object bytes and the exact S3 VersionId returned with them."""
        try:
            response = self._client.get_object(Bucket=self._bucket_name, Key=key)
        except ClientError as exc:
            if _is_missing_object(exc):
                raise KeyError(key) from exc
            raise
        return self._read_response(key=key, expected_version_id=None, response=response)

    def read_version(self, *, key: str, version_id: str) -> HistoricalEpssEvidenceObjectV1:
        """Read one explicitly addressed S3 object version."""
        try:
            response = self._client.get_object(
                Bucket=self._bucket_name,
                Key=key,
                VersionId=version_id,
            )
        except ClientError as exc:
            if _is_missing_object(exc):
                raise KeyError(f"{key}@{version_id}") from exc
            raise
        return self._read_response(
            key=key,
            expected_version_id=version_id,
            response=response,
        )

    def list_versions(self, *, key: str) -> tuple[HistoricalEpssEvidenceVersionV1, ...]:
        """List retained non-delete versions for one exact object key."""
        paginator = self._client.get_paginator("list_object_versions")
        versions: list[HistoricalEpssEvidenceVersionV1] = []
        for page in paginator.paginate(Bucket=self._bucket_name, Prefix=key):
            for value in page.get("Versions", []):
                if value.get("Key") != key:
                    continue
                version_id = value.get("VersionId")
                is_latest = value.get("IsLatest")
                if not isinstance(version_id, str) or not version_id:
                    raise ValueError("S3 evidence version listing returned an invalid VersionId.")
                if type(is_latest) is not bool:
                    raise ValueError("S3 evidence version listing returned invalid IsLatest.")
                versions.append(
                    HistoricalEpssEvidenceVersionV1(
                        key=key,
                        version_id=version_id,
                        is_latest=is_latest,
                    )
                )
        return tuple(versions)

    @staticmethod
    def _read_response(
        *,
        key: str,
        expected_version_id: str | None,
        response: dict[str, Any],
    ) -> HistoricalEpssEvidenceObjectV1:
        """Normalize one GetObject response into exact read-only evidence."""
        version_id = response.get("VersionId")
        if not isinstance(version_id, str) or not version_id:
            raise ValueError("S3 evidence GetObject response requires VersionId.")
        if expected_version_id is not None and version_id != expected_version_id:
            raise ValueError("S3 evidence GetObject returned a different VersionId.")
        body = response.get("Body")
        if body is None:
            raise ValueError("S3 evidence GetObject response requires Body.")
        try:
            raw_bytes = body.read()
        finally:
            body.close()
        content_length = response.get("ContentLength")
        if type(content_length) is not int or content_length != len(raw_bytes):
            raise ValueError("S3 evidence GetObject ContentLength does not match bytes.")
        return HistoricalEpssEvidenceObjectV1(
            key=key,
            version_id=version_id,
            raw_bytes=raw_bytes,
        )


def _is_missing_object(exc: ClientError) -> bool:
    """Return whether an S3 client error represents missing key/version evidence."""
    error = exc.response.get("Error", {})
    code = error.get("Code")
    status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return code in {"NoSuchKey", "NoSuchVersion", "404", "NotFound"} or status == 404


def _verifier(*, github_timeout_seconds: float) -> VerifyHistoricalEpssBackfillEvidenceV1:
    """Compose the frozen read-only verifier from S3 and immutable Git inventory reads."""
    data_bucket = os.environ.get("EPSS_DATA_BUCKET", "").strip()
    if not data_bucket:
        raise ValueError("EPSS_DATA_BUCKET is required.")

    s3_client = boto3.client("s3")
    snapshot_parser = HistoricalEpssSnapshotParser()
    silver_key_factory = EpssSilverKeyFactory(prefix="silver/epss")
    return VerifyHistoricalEpssBackfillEvidenceV1(
        forward_boundary_reader=S3HistoricalEpssForwardBoundaryReader(
            client=cast(HistoricalEpssForwardListClient, s3_client),
            bucket_name=data_bucket,
        ),
        archive_inventory_reader=GitHubArchiveReader(timeout_seconds=github_timeout_seconds),
        evidence_store=S3HistoricalEpssEvidenceStore(
            client=s3_client,
            bucket_name=data_bucket,
        ),
        silver_preparer=PrepareHistoricalEpssSilver(
            parser=snapshot_parser,
            transformer=HistoricalEpssSilverRecordTransformer(),
            record_writer=PyArrowSilverEpssRecordWriter(),
            key_factory=silver_key_factory,
        ),
        snapshot_parser=snapshot_parser,
        silver_key_factory=silver_key_factory,
    )


def main() -> None:
    """Emit one machine-readable summary and fail the process if any D5-E gate fails."""
    args = parse_args()
    summary = _verifier(github_timeout_seconds=args.github_timeout_seconds).execute()
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True), flush=True)
    if not summary.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
