"""Discover real AWS coordinates for the Phase 2.4F cross-source proof."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections.abc import Iterable
from typing import Any

import boto3
from botocore.client import BaseClient

SNAPSHOT_RE = re.compile(r"snapshot_date=(\d{4}-\d{2}-\d{2})/$")
PROJECTION_RE = re.compile(r"projection_date=(\d{4}-\d{2}-\d{2})/$")


def parse_args() -> argparse.Namespace:
    """Parse operator-facing discovery arguments."""
    parser = argparse.ArgumentParser(
        description="Discover read-only Phase 2.4F proof coordinates from AWS."
    )
    parser.add_argument(
        "--profile",
        default=os.getenv("AWS_PROFILE", "opslens-bootstrap"),
        help="AWS profile name (default: AWS_PROFILE or opslens-bootstrap).",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION", "us-east-1"),
        help="AWS Region (default: AWS_REGION or us-east-1).",
    )
    parser.add_argument(
        "--database",
        default="opslens_dev",
        help="Glue/Athena database name.",
    )
    parser.add_argument(
        "--workgroup",
        default="opslens-dev",
        help="Athena workgroup name.",
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="Optional data bucket override. Default is derived from account and Region.",
    )
    return parser.parse_args()


def list_common_prefixes(s3: BaseClient, *, bucket: str, prefix: str) -> list[str]:
    """Return every immediate S3 child prefix below a prefix."""
    paginator = s3.get_paginator("list_objects_v2")
    result: list[str] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
        for item in page.get("CommonPrefixes", []):
            child = item.get("Prefix")
            if isinstance(child, str):
                result.append(child)
    return sorted(set(result))


def list_current_objects(s3: BaseClient, *, bucket: str, prefix: str) -> list[dict[str, Any]]:
    """Return current non-directory objects under an S3 prefix."""
    paginator = s3.get_paginator("list_objects_v2")
    result: list[dict[str, Any]] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            key = item.get("Key")
            if not isinstance(key, str) or key.endswith("/"):
                continue
            result.append(
                {
                    "key": key,
                    "size": item.get("Size"),
                    "etag": item.get("ETag"),
                    "last_modified": (
                        item["LastModified"].isoformat()
                        if item.get("LastModified") is not None
                        else None
                    ),
                }
            )
    return sorted(result, key=lambda item: str(item["key"]))


def extract_dates(prefixes: Iterable[str], pattern: re.Pattern[str]) -> list[str]:
    """Extract and sort ISO dates from deterministic partition prefixes."""
    dates: list[str] = []
    for prefix in prefixes:
        match = pattern.search(prefix)
        if match is not None:
            dates.append(match.group(1))
    return sorted(set(dates))


def latest_snapshot(
    s3: BaseClient,
    *,
    bucket: str,
    root: str,
) -> dict[str, Any]:
    """Discover the latest existing injected snapshot partition."""
    prefixes = list_common_prefixes(s3, bucket=bucket, prefix=root)
    dates = extract_dates(prefixes, SNAPSHOT_RE)
    if not dates:
        raise RuntimeError(f"No snapshot_date partitions found below s3://{bucket}/{root}")

    latest = dates[-1]
    latest_prefix = f"{root}snapshot_date={latest}/"
    objects = list_current_objects(s3, bucket=bucket, prefix=latest_prefix)
    parquet_objects = [item for item in objects if str(item["key"]).endswith(".parquet")]
    if not parquet_objects:
        raise RuntimeError(f"Latest partition has no Parquet object: {latest_prefix}")

    return {
        "latest_snapshot_date": latest,
        "available_snapshot_dates": dates,
        "latest_prefix": latest_prefix,
        "parquet_object_count": len(parquet_objects),
        "parquet_objects": parquet_objects,
    }


def nvd_projection_coordinates(s3: BaseClient, *, bucket: str) -> dict[str, Any]:
    """Discover actual permanent NVD projection dates from S3."""
    root = "analytics/nvd/cve/schema_version=1/"
    result: dict[str, Any] = {}

    for source_kind in ("bootstrap", "incremental"):
        kind_root = f"{root}source_kind={source_kind}/"
        prefixes = list_common_prefixes(s3, bucket=bucket, prefix=kind_root)
        dates = extract_dates(prefixes, PROJECTION_RE)

        date_details: list[dict[str, Any]] = []
        for projection_date in dates:
            prefix = f"{kind_root}projection_date={projection_date}/"
            objects = list_current_objects(s3, bucket=bucket, prefix=prefix)
            parquet_objects = [item for item in objects if str(item["key"]).endswith(".parquet")]
            date_details.append(
                {
                    "projection_date": projection_date,
                    "prefix": prefix,
                    "parquet_object_count": len(parquet_objects),
                    "parquet_objects": parquet_objects,
                }
            )

        result[source_kind] = {
            "available_projection_dates": dates,
            "latest_projection_date": dates[-1] if dates else None,
            "dates": date_details,
        }

    return result


def glue_table_summary(glue: BaseClient, *, database: str, table_name: str) -> dict[str, Any]:
    """Return the deployed analytical table boundary needed by the proof."""
    table = glue.get_table(DatabaseName=database, Name=table_name)["Table"]
    descriptor = table.get("StorageDescriptor", {})
    columns = descriptor.get("Columns", [])
    partition_keys = table.get("PartitionKeys", [])
    return {
        "name": table.get("Name"),
        "table_type": table.get("TableType"),
        "location": descriptor.get("Location"),
        "column_count": len(columns),
        "columns": [column.get("Name") for column in columns],
        "partition_keys": [partition.get("Name") for partition in partition_keys],
        "parameters": table.get("Parameters", {}),
    }


def workgroup_summary(athena: BaseClient, *, workgroup: str) -> dict[str, Any]:
    """Return the Athena workgroup cost and result boundary."""
    value = athena.get_work_group(WorkGroup=workgroup)["WorkGroup"]
    configuration = value.get("Configuration", {})
    result_configuration = configuration.get("ResultConfiguration", {})
    encryption = result_configuration.get("EncryptionConfiguration", {})
    return {
        "name": value.get("Name"),
        "state": value.get("State"),
        "enforce_workgroup_configuration": configuration.get("EnforceWorkGroupConfiguration"),
        "bytes_scanned_cutoff_per_query": configuration.get("BytesScannedCutoffPerQuery"),
        "output_location": result_configuration.get("OutputLocation"),
        "encryption_option": encryption.get("EncryptionOption"),
        "publish_cloudwatch_metrics_enabled": configuration.get(
            "PublishCloudWatchMetricsEnabled"
        ),
        "engine_version": configuration.get("EngineVersion", {}),
    }


def main() -> None:
    """Discover and print the real read-only 2.4F proof coordinates."""
    args = parse_args()
    session = boto3.Session(profile_name=args.profile, region_name=args.region)

    sts = session.client("sts")
    s3 = session.client("s3")
    glue = session.client("glue")
    athena = session.client("athena")

    identity = sts.get_caller_identity()
    account_id = str(identity["Account"])
    bucket = args.bucket or f"opslens-dev-data-{account_id}-{args.region}"

    tables = {
        table_name: glue_table_summary(glue, database=args.database, table_name=table_name)
        for table_name in (
            "epss_scores",
            "kev_entries",
            "nvd_cve_versions",
            "ghsa_advisory_versions",
        )
    }

    ghsa_root = "silver/ghsa/advisory_versions/schema_version=1/"
    ghsa_objects = [
        item
        for item in list_current_objects(s3, bucket=bucket, prefix=ghsa_root)
        if str(item["key"]).endswith(".parquet")
    ]

    result = {
        "schema_version": 1,
        "read_only": True,
        "identity": {
            "account": account_id,
            "arn": identity.get("Arn"),
        },
        "region": args.region,
        "data_bucket": bucket,
        "database": args.database,
        "epss": latest_snapshot(s3, bucket=bucket, root="silver/epss/"),
        "kev": latest_snapshot(s3, bucket=bucket, root="silver/kev/"),
        "nvd": nvd_projection_coordinates(s3, bucket=bucket),
        "ghsa": {
            "root": ghsa_root,
            "parquet_object_count": len(ghsa_objects),
            "parquet_objects": ghsa_objects,
        },
        "glue_tables": tables,
        "athena_workgroup": workgroup_summary(athena, workgroup=args.workgroup),
    }

    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
