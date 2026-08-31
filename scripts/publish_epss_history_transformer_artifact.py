#!/usr/bin/env python3
"""Publish the content-addressed EPSS history transformer artifact create-only."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = PROJECT_ROOT / "dist" / "opslens-epss-history-transformer.zip"


def parse_args() -> argparse.Namespace:
    """Parse immutable artifact publication arguments."""
    parser = argparse.ArgumentParser(description="Publish EPSS history transformer ZIP create-only.")
    parser.add_argument("--bucket", required=True, help="Versioned deployment-artifacts S3 bucket.")
    parser.add_argument(
        "--artifact",
        type=Path,
        default=DEFAULT_ARTIFACT,
        help="Path to the deterministic deployment ZIP.",
    )
    return parser.parse_args()


def _read_body(response: dict[str, Any]) -> bytes:
    """Read and close one S3 GetObject response body."""
    body = response.get("Body")
    if body is None:
        raise RuntimeError("Artifact replay GetObject response is missing Body.")
    try:
        return body.read()
    finally:
        body.close()


def main() -> None:
    """Create one content-addressed artifact or exact-replay-verify existing bytes."""
    args = parse_args()
    artifact_path = args.artifact.resolve()
    raw_bytes = artifact_path.read_bytes()
    if not raw_bytes:
        raise ValueError("Historical transformer deployment artifact cannot be empty.")
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    key = f"lambda/epss-history-transformer/{sha256}.zip"
    client = boto3.client("s3")

    status = "created"
    try:
        response = client.put_object(
            Bucket=args.bucket,
            Key=key,
            Body=raw_bytes,
            ContentType="application/zip",
            Metadata={"sha256": sha256, "component": "epss-history-transformer"},
            IfNoneMatch="*",
        )
        version_id = response.get("VersionId")
        if not isinstance(version_id, str) or not version_id.strip():
            raise RuntimeError("Successful artifact PutObject requires S3 VersionId.")
    except ClientError as exc:
        http_status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if http_status != 412:
            raise
        status = "replay_verified"
        head = client.head_object(Bucket=args.bucket, Key=key)
        version_id = head.get("VersionId")
        size = head.get("ContentLength")
        if not isinstance(version_id, str) or not version_id.strip():
            raise RuntimeError("Existing artifact HeadObject requires S3 VersionId.")
        if type(size) is not int or size != len(raw_bytes):
            raise ValueError("Existing artifact size differs from deterministic ZIP.")
        existing = _read_body(
            client.get_object(Bucket=args.bucket, Key=key, VersionId=version_id)
        )
        if existing != raw_bytes:
            raise ValueError("Existing content-addressed artifact bytes differ from deterministic ZIP.")

    print(
        json.dumps(
            {
                "artifact": str(artifact_path),
                "bucket": args.bucket,
                "key": key,
                "sha256": sha256,
                "size_bytes": len(raw_bytes),
                "status": status,
                "version_id": version_id,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
