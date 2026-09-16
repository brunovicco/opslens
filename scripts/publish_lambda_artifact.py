#!/usr/bin/env python3
"""Publish any content-addressed Lambda artifact create-only, and emit its pins.

A lambda runs the artifact published in S3, not the working tree, so a source change
takes effect only once a rebuilt artifact is published and Terraform is pointed at it.
Terraform pins it by three hand-maintained locals: the hex digest, the base64 digest
Lambda compares as `source_code_hash`, and the S3 object version id. Copying three
values by hand is where a mistake silently pins the wrong bytes — and the pin is the
control that stops a function running code nobody admitted. So this prints the exact
block to paste rather than leaving a reader to assemble it.

This replaces the per-lambda publish scripts. They carried one copy each of the key
prefix, and a fourth lambda needed the same thing; the target registry in
`opslens.shared.deployment` now holds that decision once, and refuses a name it does
not declare rather than guessing a prefix and publishing real bytes, permanently, to a
path nothing reads.

It does not edit the Terraform. Publication authority is human-only and create-only
throughout this repository, and a publish script that rewrites infrastructure would be
taking a decision it was not given.

```text
CREATE ONLY. An existing key is verified byte-for-byte, never overwritten.
unknown target != guess a prefix
published artifact != pinned artifact
pinned artifact != applied artifact
```
"""

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Final

import boto3
from _bootstrap import ensure_repository_src_on_path
from botocore.exceptions import ClientError

ensure_repository_src_on_path()

from opslens.shared.deployment import (  # noqa: E402
    PUBLISHABLE_TARGETS,
    artifact_key,
    render_terraform_locals,
    resolve_target,
)

PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    """Parse immutable artifact publication arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Publish one declared Lambda ZIP create-only and print the Terraform pins. "
            "Build the artifact with its own scripts/build_*.py first."
        )
    )
    parser.add_argument(
        "--target",
        required=True,
        choices=sorted(PUBLISHABLE_TARGETS),
        help="Which declared lambda artifact to publish.",
    )
    parser.add_argument("--bucket", help="Versioned deployment-artifacts S3 bucket.")
    parser.add_argument(
        "--artifact",
        type=Path,
        default=None,
        help="Override the deterministic ZIP path; defaults to the target's own.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="compute and print the digests without uploading anything",
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


def _verify_existing_artifact(
    *,
    client: Any,
    bucket: str,
    key: str,
    raw_bytes: bytes,
) -> str:
    """Verify an existing content-addressed artifact byte for byte.

    A content-addressed key that already exists should hold exactly these bytes. If it
    does not, the digest and the content disagree and publishing anything on top would
    hide that rather than resolve it.

    Args:
        client: S3 client.
        bucket: Deployment artifacts bucket.
        key: Content-addressed object key.
        raw_bytes: The locally built artifact bytes.

    Returns:
        The existing object's version id.

    Raises:
        RuntimeError: If the object carries no version id or different bytes.
    """
    head = client.head_object(Bucket=bucket, Key=key)
    version_id = head.get("VersionId")

    if not isinstance(version_id, str) or not version_id.strip():
        raise RuntimeError(f"Existing artifact {key} carries no S3 version id.")

    existing = _read_body(client.get_object(Bucket=bucket, Key=key, VersionId=version_id))
    if existing != raw_bytes:
        raise RuntimeError(
            f"Existing artifact {key} does not match the locally built bytes; "
            "the content-addressed key and its content disagree."
        )

    return version_id


def main() -> None:
    """Publish the artifact create-only and print its pins.

    Raises:
        RuntimeError: If the artifact is missing, or an existing object cannot be
            verified as byte identical.
    """
    args = parse_args()
    target = resolve_target(str(args.target))
    artifact_path = (
        Path(args.artifact)
        if args.artifact is not None
        else PROJECT_ROOT / "dist" / target.artifact_filename
    )

    if not artifact_path.is_file():
        raise RuntimeError(
            f"missing artifact {artifact_path}; build it before publishing"
        )

    if not args.dry_run and not args.bucket:
        raise RuntimeError("--bucket is required for a real publish")

    raw_bytes = artifact_path.read_bytes()
    digest = hashlib.sha256(raw_bytes)
    sha256 = digest.hexdigest()
    sha256_base64 = base64.b64encode(digest.digest()).decode("ascii")
    key = artifact_key(target, sha256)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "artifact": str(artifact_path),
                    "key": key,
                    "sha256": sha256,
                    "sha256_base64": sha256_base64,
                    "size_bytes": len(raw_bytes),
                    "status": "dry-run",
                },
                sort_keys=True,
            )
        )
        print("\nNothing was uploaded. The version id is only known after a real publish.")
        return

    client: Any = boto3.client("s3")  # pyright: ignore[reportUnknownMemberType]

    try:
        response = client.put_object(
            Bucket=args.bucket,
            Key=key,
            Body=raw_bytes,
            ChecksumSHA256=base64.b64encode(digest.digest()).decode("ascii"),
            Metadata={"sha256": sha256, "component": target.component},
            IfNoneMatch="*",
        )
        published: dict[str, Any] = response
        version_id = published.get("VersionId")
        if not isinstance(version_id, str) or not version_id.strip():
            raise RuntimeError("S3 PutObject returned no version id.")
        status = "published"
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code not in {"PreconditionFailed", "ConditionalRequestConflict"}:
            raise
        # The content-addressed key already exists. Verify rather than republish:
        # identical bytes are already published, and different bytes are a defect.
        version_id = _verify_existing_artifact(
            client=client,
            bucket=args.bucket,
            key=key,
            raw_bytes=raw_bytes,
        )
        status = "already-published"

    print(
        json.dumps(
            {
                "artifact": str(artifact_path),
                "bucket": args.bucket,
                "key": key,
                "sha256": sha256,
                "sha256_base64": sha256_base64,
                "size_bytes": len(raw_bytes),
                "status": status,
                "version_id": version_id,
            },
            sort_keys=True,
        )
    )
    print()
    print(f"Paste this over the locals block in {target.terraform_file}:")
    print()
    print(
        render_terraform_locals(
            target,
            sha256=sha256,
            sha256_base64=sha256_base64,
            version_id=version_id,
        )
    )
    print()
    print("Then plan, admit the plan, and apply. Publishing pins nothing on its own.")


if __name__ == "__main__":
    main()
