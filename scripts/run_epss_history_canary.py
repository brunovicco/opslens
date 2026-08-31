#!/usr/bin/env python3
"""Plan or execute the frozen seven-snapshot historical EPSS canary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from typing import Any, cast

import boto3
from botocore.exceptions import ClientError

from opslens.bootstrap.epss_history import (
    APPROVED_ARCHIVE_COMMIT,
    APPROVED_ROOT_TREE_SHA,
    ARCHIVE_REPOSITORY,
    CANARY_CONFIRMATION,
    ExecuteHistoricalEpssCanaryV1,
    HistoricalEpssArchiveInventoryV1,
    HistoricalEpssBronzeInvocationCoordinateV1,
    HistoricalEpssCanaryRunResultV1,
    HistoricalEpssTransformerResultV1,
    HistoricalEpssWorkItemV1,
)
from opslens.ingestion.epss.domain.history import EpssModelEra, HistoricalEpssSnapshot
from opslens.transformation.epss.history.runtime import (
    HistoricalEpssForwardListClient,
    S3HistoricalEpssForwardBoundaryReader,
)

GITHUB_API = "https://api.github.com"
RAW_GITHUB = "https://raw.githubusercontent.com"
ARCHIVE_FIRST_DATE = date(2021, 4, 14)
ARCHIVE_PIN_END_DATE = date(2026, 8, 30)
FILE_RE = re.compile(r"^epss_scores-(\d{4}-\d{2}-\d{2})\.csv\.gz$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_ATTEMPTS = 3
USER_AGENT = "opslens-epss-history-canary/1"


def parse_args() -> argparse.Namespace:
    """Parse bounded canary command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Plan or execute only the Phase 2.5D frozen seven-snapshot EPSS canary."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform historical Bronze writes and synchronous transformer invocations.",
    )
    parser.add_argument(
        "--confirmation",
        default="",
        help=f"Execution requires the exact value {CANARY_CONFIRMATION!r}.",
    )
    parser.add_argument(
        "--github-timeout-seconds",
        type=float,
        default=30.0,
        help="Per-request GitHub timeout (default: 30 seconds).",
    )
    return parser.parse_args()


class GitHubArchiveReader:
    """Read exact pinned Git metadata and source bytes without executing archive code."""

    def __init__(self, *, timeout_seconds: float) -> None:
        """Initialize a bounded serial public GitHub reader."""
        if timeout_seconds <= 0:
            raise ValueError("GitHub timeout must be positive.")
        self._timeout_seconds = timeout_seconds

    def read(self) -> HistoricalEpssArchiveInventoryV1:
        """Enumerate the approved commit, root tree, year trees, snapshots, and absences."""
        commit = self._get_json(
            f"{GITHUB_API}/repos/{ARCHIVE_REPOSITORY}/git/commits/{APPROVED_ARCHIVE_COMMIT}"
        )
        tree = commit.get("tree")
        if not isinstance(tree, dict):
            raise ValueError("Pinned EPSS Git commit response is missing tree metadata.")
        root_tree_sha = tree.get("sha")
        if root_tree_sha != APPROVED_ROOT_TREE_SHA:
            raise ValueError("Pinned EPSS commit root tree does not match the approved coordinate.")

        root_entries = self._tree_entries(APPROVED_ROOT_TREE_SHA)
        year_tree_shas: dict[int, str] = {}
        for entry in root_entries:
            path = entry.get("path")
            entry_type = entry.get("type")
            sha = entry.get("sha")
            if (
                isinstance(path, str)
                and path.isdigit()
                and len(path) == 4
                and entry_type == "tree"
                and isinstance(sha, str)
                and SHA1_RE.fullmatch(sha) is not None
            ):
                year_tree_shas[int(path)] = sha

        expected_years = set(range(2021, 2027))
        if set(year_tree_shas) != expected_years:
            raise ValueError(
                "Pinned EPSS root tree does not contain exactly the expected year trees."
            )

        work_items: list[HistoricalEpssWorkItemV1] = []
        observed_dates: set[date] = set()
        for year in sorted(year_tree_shas):
            for entry in self._tree_entries(year_tree_shas[year]):
                filename = entry.get("path")
                if not isinstance(filename, str):
                    raise ValueError("Pinned EPSS year tree contains an entry without a path.")
                match = FILE_RE.fullmatch(filename)
                if match is None:
                    continue
                if entry.get("type") != "blob":
                    raise ValueError("Pinned EPSS score entry must be a Git blob.")
                blob_sha = entry.get("sha")
                size = entry.get("size")
                if not isinstance(blob_sha, str) or SHA1_RE.fullmatch(blob_sha) is None:
                    raise ValueError("Pinned EPSS score entry contains an invalid blob SHA-1.")
                if type(size) is not int or size <= 0:
                    raise ValueError("Pinned EPSS score entry contains an invalid compressed size.")
                snapshot_date = date.fromisoformat(match.group(1))
                if snapshot_date.year != year:
                    raise ValueError("Pinned EPSS year tree and score filename disagree.")
                if snapshot_date in observed_dates:
                    raise ValueError("Pinned EPSS archive contains a duplicate snapshot date.")
                observed_dates.add(snapshot_date)
                work_items.append(
                    HistoricalEpssWorkItemV1(
                        snapshot_date=snapshot_date,
                        archive_path=f"{year}/{filename}",
                        archive_git_blob_sha1=blob_sha,
                        compressed_size_bytes=size,
                        model_era=EpssModelEra.for_snapshot_date(snapshot_date),
                    )
                )

        expected_dates = _calendar_dates(ARCHIVE_FIRST_DATE, ARCHIVE_PIN_END_DATE)
        unexpected = observed_dates - expected_dates
        if unexpected:
            raise ValueError(
                "Pinned EPSS archive contains snapshots outside the approved date range."
            )
        source_absent_dates = tuple(sorted(expected_dates - observed_dates))

        return HistoricalEpssArchiveInventoryV1(
            archive_repository=ARCHIVE_REPOSITORY,
            archive_commit=APPROVED_ARCHIVE_COMMIT,
            root_tree_sha=APPROVED_ROOT_TREE_SHA,
            year_tree_shas=tuple(sorted(year_tree_shas.items())),
            snapshots=tuple(sorted(work_items, key=lambda item: item.snapshot_date)),
            source_absent_dates=source_absent_dates,
        )

    def read_source(self, work_item: HistoricalEpssWorkItemV1) -> bytes:
        """Download one commit-pinned source object as inert bytes."""
        url = (
            f"{RAW_GITHUB}/{ARCHIVE_REPOSITORY}/{APPROVED_ARCHIVE_COMMIT}/"
            f"{work_item.archive_path}"
        )
        return self._get_bytes(url)

    def _tree_entries(self, tree_sha: str) -> list[dict[str, Any]]:
        """Read one non-recursive Git tree and fail closed on truncation."""
        value = self._get_json(
            f"{GITHUB_API}/repos/{ARCHIVE_REPOSITORY}/git/trees/{tree_sha}"
        )
        if value.get("truncated") is True:
            raise ValueError(f"Pinned EPSS Git tree {tree_sha} is truncated.")
        raw_entries = value.get("tree")
        if not isinstance(raw_entries, list):
            raise ValueError("Pinned EPSS Git tree response is missing its tree array.")
        entries: list[dict[str, Any]] = []
        for entry in raw_entries:
            if not isinstance(entry, dict):
                raise ValueError("Pinned EPSS Git tree contains a non-object entry.")
            entries.append(cast(dict[str, Any], entry))
        return entries

    def _get_json(self, url: str) -> dict[str, Any]:
        """Read one bounded GitHub JSON object."""
        raw = self._get_bytes(url)
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise ValueError("GitHub metadata response must be a JSON object.")
        return cast(dict[str, Any], decoded)

    def _get_bytes(self, url: str) -> bytes:
        """Read public GitHub bytes with bounded retry for transient failures."""
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": USER_AGENT,
                    "X-GitHub-Api-Version": "2026-03-10",
                },
                method="GET",
            )
            try:
                with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                    return response.read()
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {403, 429, 500, 502, 503, 504} or attempt == MAX_ATTEMPTS:
                    raise
                delay = _http_retry_delay(exc, attempt)
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt == MAX_ATTEMPTS:
                    raise
                delay = float(2 ** (attempt - 1))
            time.sleep(delay)
        raise RuntimeError("GitHub request exhausted retries.") from last_error


class S3HistoricalBronzePublisher:
    """Create or exact-replay-verify historical Bronze source and manifest objects."""

    def __init__(self, *, client: Any, bucket_name: str) -> None:
        """Initialize one bucket-scoped historical Bronze publisher."""
        if not bucket_name.strip():
            raise ValueError("Historical EPSS Bronze bucket cannot be empty.")
        self._client = client
        self._bucket_name = bucket_name

    def publish(
        self,
        *,
        work_item: HistoricalEpssWorkItemV1,
        snapshot: HistoricalEpssSnapshot,
    ) -> HistoricalEpssBronzeInvocationCoordinateV1:
        """Persist source first, then a canonical manifest bound to exact VersionId evidence."""
        if snapshot.snapshot_date != work_item.snapshot_date:
            raise ValueError("Historical EPSS source snapshot does not match work item.")
        prefix = (
            "bronze/epss-history/schema_version=1/"
            f"archive_commit={APPROVED_ARCHIVE_COMMIT}/"
            f"snapshot_date={work_item.snapshot_date.isoformat()}"
        )
        source_key = f"{prefix}/epss_scores.csv.gz"
        manifest_key = f"{prefix}/manifest.json"
        source_version_id = self._put_or_verify(
            key=source_key,
            raw_bytes=snapshot.raw_bytes,
            content_type="application/gzip",
            metadata={
                "dataset": "epss_history_source",
                "snapshot_date": work_item.snapshot_date.isoformat(),
                "archive_commit": APPROVED_ARCHIVE_COMMIT,
                "sha256": snapshot.sha256,
            },
        )
        manifest_document = {
            "archive_commit": APPROVED_ARCHIVE_COMMIT,
            "archive_git_blob_sha1": work_item.archive_git_blob_sha1,
            "archive_path": work_item.archive_path,
            "archive_repository": ARCHIVE_REPOSITORY,
            "compressed_size_bytes": work_item.compressed_size_bytes,
            "model_era": work_item.model_era.value,
            "schema_version": 1,
            "snapshot_date": work_item.snapshot_date.isoformat(),
            "source_metadata_present": snapshot.source_metadata_present,
            "source_object_key": source_key,
            "source_object_version_id": source_version_id,
            "source_sha256": snapshot.sha256,
        }
        manifest_text = json.dumps(
            manifest_document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        manifest_bytes = f"{manifest_text}\n".encode()
        manifest_version_id = self._put_or_verify(
            key=manifest_key,
            raw_bytes=manifest_bytes,
            content_type="application/json",
            metadata={
                "dataset": "epss_history_manifest",
                "snapshot_date": work_item.snapshot_date.isoformat(),
                "archive_commit": APPROVED_ARCHIVE_COMMIT,
                "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            },
        )
        return HistoricalEpssBronzeInvocationCoordinateV1(
            snapshot_date=work_item.snapshot_date,
            manifest_key=manifest_key,
            manifest_version_id=manifest_version_id,
        )

    def _put_or_verify(
        self,
        *,
        key: str,
        raw_bytes: bytes,
        content_type: str,
        metadata: dict[str, str],
    ) -> str:
        """Create bytes once or verify the current exact version is identical."""
        try:
            response = self._client.put_object(
                Bucket=self._bucket_name,
                Key=key,
                Body=raw_bytes,
                ContentType=content_type,
                Metadata=metadata,
                IfNoneMatch="*",
            )
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status == 409:
                raise RuntimeError("Concurrent historical EPSS Bronze conditional write.") from exc
            if status != 412:
                raise
            return self._verify_current(key=key, expected_bytes=raw_bytes)

        version_id = response.get("VersionId")
        if not isinstance(version_id, str) or not version_id.strip():
            raise RuntimeError("Successful historical EPSS Bronze write requires S3 VersionId.")
        return version_id

    def _verify_current(self, *, key: str, expected_bytes: bytes) -> str:
        """Verify an existing deterministic Bronze key by its exact current VersionId."""
        head = self._client.head_object(Bucket=self._bucket_name, Key=key)
        version_id = head.get("VersionId")
        content_length = head.get("ContentLength")
        if not isinstance(version_id, str) or not version_id.strip():
            raise RuntimeError("Historical EPSS Bronze replay HeadObject requires VersionId.")
        if type(content_length) is not int or content_length != len(expected_bytes):
            raise ValueError("Historical EPSS Bronze replay size differs from expected bytes.")
        response = self._client.get_object(
            Bucket=self._bucket_name,
            Key=key,
            VersionId=version_id,
        )
        if response.get("VersionId") != version_id:
            raise ValueError(
                "Historical EPSS Bronze replay GetObject VersionId changed after head."
            )
        body = response.get("Body")
        if body is None:
            raise ValueError("Historical EPSS Bronze replay response is missing Body.")
        try:
            existing_bytes = body.read()
        finally:
            body.close()
        if existing_bytes != expected_bytes:
            raise ValueError("Historical EPSS Bronze replay bytes differ from deterministic bytes.")
        return version_id


class LambdaHistoricalTransformerInvoker:
    """Invoke one dedicated historical transformer synchronously and validate its response."""

    def __init__(self, *, client: Any, function_name: str) -> None:
        """Initialize the exact Lambda function target."""
        if not function_name.strip():
            raise ValueError("Historical EPSS transformer function name cannot be empty.")
        self._client = client
        self._function_name = function_name

    def invoke(
        self,
        coordinate: HistoricalEpssBronzeInvocationCoordinateV1,
    ) -> HistoricalEpssTransformerResultV1:
        """Invoke RequestResponse for exactly one Bronze manifest VersionId."""
        payload = json.dumps(
            {
                "schema_version": "1",
                "bronze_manifest_key": coordinate.manifest_key,
                "bronze_manifest_version_id": coordinate.manifest_version_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        response = self._client.invoke(
            FunctionName=self._function_name,
            InvocationType="RequestResponse",
            Payload=payload,
        )
        if response.get("StatusCode") != 200:
            raise RuntimeError("Historical EPSS transformer returned a non-200 invoke status.")
        if response.get("FunctionError"):
            raise RuntimeError("Historical EPSS transformer Lambda reported FunctionError.")
        stream = response.get("Payload")
        if stream is None:
            raise RuntimeError("Historical EPSS transformer response is missing Payload.")
        raw_response = stream.read()
        decoded = json.loads(raw_response)
        if not isinstance(decoded, dict):
            raise RuntimeError("Historical EPSS transformer payload must be a JSON object.")
        result = cast(dict[str, object], decoded)
        snapshot_date = _required_date(result, "snapshot_date")
        if snapshot_date != coordinate.snapshot_date:
            raise ValueError(
                "Historical EPSS transformer response snapshot does not match request."
            )
        return HistoricalEpssTransformerResultV1(
            snapshot_date=snapshot_date,
            request_id=_required_string(result, "request_id"),
            silver_key=_required_string(result, "silver_key"),
            silver_version_id=_required_string(result, "silver_version_id"),
            silver_sha256=_required_string(result, "silver_sha256"),
            silver_replay_status=_required_string(result, "silver_replay_status"),
            completion_key=_required_string(result, "completion_key"),
            completion_version_id=_required_string(result, "completion_version_id"),
            completion_sha256=_required_string(result, "completion_sha256"),
            completion_replay_status=_required_string(result, "completion_replay_status"),
        )


def _calendar_dates(start: date, end: date) -> set[date]:
    """Return all calendar dates in one inclusive range."""
    values: set[date] = set()
    current = start
    while current <= end:
        values.add(current)
        current += timedelta(days=1)
    return values


def _http_retry_delay(error: urllib.error.HTTPError, attempt: int) -> float:
    """Resolve bounded provider-aware retry delay for one HTTP error."""
    retry_after = error.headers.get("Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), 120.0)
        except ValueError:
            pass
    remaining = error.headers.get("X-RateLimit-Remaining")
    reset = error.headers.get("X-RateLimit-Reset")
    if remaining == "0" and reset:
        try:
            return min(max(float(reset) - time.time(), 1.0), 120.0)
        except ValueError:
            pass
    return float(min(2 ** (attempt - 1), 60))


def _required_string(value: dict[str, object], key: str) -> str:
    """Return one required non-empty transformer response string."""
    raw = value.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError(f"Historical EPSS transformer response {key} is invalid.")
    return raw


def _required_date(value: dict[str, object], key: str) -> date:
    """Return one required canonical transformer response date."""
    raw = _required_string(value, key)
    parsed = date.fromisoformat(raw)
    if parsed.isoformat() != raw:
        raise RuntimeError(f"Historical EPSS transformer response {key} is not canonical.")
    return parsed


def _serialize_plan(canary: Any) -> dict[str, object]:
    """Serialize dry-run plan evidence without exposing source payloads."""
    return {
        "mode": "plan",
        "plan_id": canary.plan.plan_id,
        "first_forward_snapshot_date": canary.plan.first_forward_snapshot_date.isoformat(),
        "candidate_count": canary.plan.candidate_count,
        "candidate_compressed_bytes": canary.plan.candidate_compressed_bytes,
        "source_absent_dates": [value.isoformat() for value in canary.plan.source_absent_dates],
        "canary_dates": [item.snapshot_date.isoformat() for item in canary.canary_items],
        "canary_compressed_bytes": sum(
            item.compressed_size_bytes for item in canary.canary_items
        ),
    }


def _serialize_run(run: HistoricalEpssCanaryRunResultV1) -> dict[str, object]:
    """Serialize exact canary run evidence returned by the transformer."""
    return {
        "mode": "execute",
        "plan_id": run.plan_id,
        "run_id": run.run_id,
        "first_forward_snapshot_date": run.first_forward_snapshot_date.isoformat(),
        "processed_snapshots": len(run.items),
        "items": [
            {
                "snapshot_date": item.work_item.snapshot_date.isoformat(),
                "source_sha256": item.source_sha256,
                "lambda_request_id": item.transformer.request_id,
                "silver_key": item.transformer.silver_key,
                "silver_version_id": item.transformer.silver_version_id,
                "silver_sha256": item.transformer.silver_sha256,
                "silver_replay_status": item.transformer.silver_replay_status,
                "completion_key": item.transformer.completion_key,
                "completion_version_id": item.transformer.completion_version_id,
                "completion_sha256": item.transformer.completion_sha256,
                "completion_replay_status": item.transformer.completion_replay_status,
            }
            for item in run.items
        ],
    }


def main() -> None:
    """Plan read-only by default or execute only after exact bounded confirmation."""
    args = parse_args()
    data_bucket = os.environ.get("EPSS_DATA_BUCKET", "").strip()
    transformer_function = os.environ.get("EPSS_HISTORY_TRANSFORMER_FUNCTION", "").strip()
    if not data_bucket:
        raise ValueError("EPSS_DATA_BUCKET is required.")
    if not transformer_function:
        raise ValueError("EPSS_HISTORY_TRANSFORMER_FUNCTION is required.")
    if args.execute and args.confirmation != CANARY_CONFIRMATION:
        raise ValueError(f"Execution requires --confirmation {CANARY_CONFIRMATION!r}.")

    s3_client = boto3.client("s3")
    lambda_client = boto3.client("lambda")
    archive_reader = GitHubArchiveReader(timeout_seconds=args.github_timeout_seconds)
    coordinator = ExecuteHistoricalEpssCanaryV1(
        forward_boundary_reader=S3HistoricalEpssForwardBoundaryReader(
            client=cast(HistoricalEpssForwardListClient, s3_client),
            bucket_name=data_bucket,
        ),
        archive_inventory_reader=archive_reader,
        source_reader=archive_reader,
        bronze_publisher=S3HistoricalBronzePublisher(
            client=s3_client,
            bucket_name=data_bucket,
        ),
        transformer_invoker=LambdaHistoricalTransformerInvoker(
            client=lambda_client,
            function_name=transformer_function,
        ),
    )

    if args.execute:
        result = _serialize_run(coordinator.execute(confirmation=args.confirmation))
    else:
        result = _serialize_plan(coordinator.prepare())
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
