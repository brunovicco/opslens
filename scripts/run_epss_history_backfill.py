#!/usr/bin/env python3
"""Plan or execute the frozen full historical EPSS backfill."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, cast

import boto3

from opslens.bootstrap.epss_history_backfill import (
    BACKFILL_CONFIRMATION,
    ExecuteHistoricalEpssBackfillV1,
    HistoricalEpssBackfillItemResultV1,
    frozen_backfill_plan_summary,
)
from opslens.transformation.epss.history.runtime import (
    HistoricalEpssForwardListClient,
    S3HistoricalEpssForwardBoundaryReader,
)
from run_epss_history_canary import (
    GitHubArchiveReader,
    GitHubArchiveSourceReader,
    LambdaHistoricalTransformerInvoker,
    S3HistoricalBronzePublisher,
)


def parse_args() -> argparse.Namespace:
    """Parse only the fixed-scope full-backfill execution controls."""
    parser = argparse.ArgumentParser(
        description="Plan or execute the reviewed Phase 2.5D-5 full historical EPSS backfill."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute all 1,939 frozen candidates sequentially after exact confirmation.",
    )
    parser.add_argument(
        "--confirmation",
        default="",
        help=f"Execution requires the exact value {BACKFILL_CONFIRMATION!r}.",
    )
    parser.add_argument(
        "--github-timeout-seconds",
        type=float,
        default=30.0,
        help="Per-request GitHub timeout (default: 30 seconds).",
    )
    return parser.parse_args()


def _progress(item: HistoricalEpssBackfillItemResultV1) -> None:
    """Emit one machine-readable durable progress record after completed work."""
    print(
        json.dumps(
            {
                "event": "historical_epss_backfill_progress",
                "snapshot_date": item.work_item.snapshot_date.isoformat(),
                "ordinal": item.ordinal,
                "total": item.total,
                "source_sha256": item.source_sha256,
                "bronze_manifest_key": item.bronze_manifest_key,
                "bronze_manifest_version_id": item.bronze_manifest_version_id,
                "lambda_request_id": item.transformer.request_id,
                "silver_key": item.transformer.silver_key,
                "silver_version_id": item.transformer.silver_version_id,
                "silver_sha256": item.transformer.silver_sha256,
                "silver_replay_status": item.transformer.silver_replay_status,
                "completion_key": item.transformer.completion_key,
                "completion_version_id": item.transformer.completion_version_id,
                "completion_sha256": item.transformer.completion_sha256,
                "completion_replay_status": item.transformer.completion_replay_status,
            },
            sort_keys=True,
        ),
        flush=True,
    )


def _coordinator(*, github_timeout_seconds: float) -> ExecuteHistoricalEpssBackfillV1:
    """Compose the same pinned source/Bronze/transformer adapters proven by the canary."""
    data_bucket = os.environ.get("EPSS_DATA_BUCKET", "").strip()
    transformer_function = os.environ.get("EPSS_HISTORY_TRANSFORMER_FUNCTION", "").strip()
    if not data_bucket:
        raise ValueError("EPSS_DATA_BUCKET is required.")
    if not transformer_function:
        raise ValueError("EPSS_HISTORY_TRANSFORMER_FUNCTION is required.")

    s3_client = boto3.client("s3")
    lambda_client = boto3.client("lambda")
    archive_reader = GitHubArchiveReader(timeout_seconds=github_timeout_seconds)
    return ExecuteHistoricalEpssBackfillV1(
        forward_boundary_reader=S3HistoricalEpssForwardBoundaryReader(
            client=cast(HistoricalEpssForwardListClient, s3_client),
            bucket_name=data_bucket,
        ),
        archive_inventory_reader=archive_reader,
        source_reader=GitHubArchiveSourceReader(archive_reader=archive_reader),
        bronze_publisher=S3HistoricalBronzePublisher(
            client=s3_client,
            bucket_name=data_bucket,
        ),
        transformer_invoker=LambdaHistoricalTransformerInvoker(
            client=lambda_client,
            function_name=transformer_function,
        ),
    )


def main() -> None:
    """Plan read-only by default; execute only the complete frozen scope when authorized."""
    args = parse_args()
    if args.execute and args.confirmation != BACKFILL_CONFIRMATION:
        raise ValueError(f"Execution requires --confirmation {BACKFILL_CONFIRMATION!r}.")

    coordinator = _coordinator(github_timeout_seconds=args.github_timeout_seconds)
    if not args.execute:
        result: dict[str, Any] = frozen_backfill_plan_summary(coordinator.prepare())
    else:
        run = coordinator.execute(
            confirmation=args.confirmation,
            progress_reporter=_progress,
        )
        result = {
            "mode": "execute",
            "plan_id": run.plan_id,
            "run_id": run.run_id,
            "first_forward_snapshot_date": run.first_forward_snapshot_date.isoformat(),
            "processed_snapshots": run.processed_snapshots,
            "failed_snapshots": run.failed_snapshots,
        }

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
