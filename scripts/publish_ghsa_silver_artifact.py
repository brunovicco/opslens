#!/usr/bin/env python3
"""Publish the content-addressed GHSA Silver artifact create-only, and emit its pins.

ADR 0085 changed the GHSA Silver transformation contract, but the lambda runs the
artifact published in S3 rather than the working tree, so the change takes effect only
once a rebuilt artifact is published and Terraform is pointed at it.

Terraform pins that artifact by three hand-maintained locals in
`infra/environments/dev/ghsa_silver_lambda.tf`: the hex digest, the base64 digest Lambda
compares as `source_code_hash`, and the S3 object version id. Copying three values by
hand is where a mistake silently pins the wrong bytes — and the pin is the control that
stops the function running code nobody admitted. So this prints the exact block to
paste, rather than leaving a reader to assemble it.

It does not edit the Terraform. Publication authority is human-only and create-only
throughout this repository, and a publish script that rewrites infrastructure would be
taking a decision it was not given.

```text
CREATE ONLY. An existing key is verified byte-for-byte, never overwritten.
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
from botocore.exceptions import ClientError

PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT: Final = PROJECT_ROOT / "dist" / "opslens-ghsa-silver.zip"
_COMPONENT: Final = "ghsa-silver"


def parse_args() -> argparse.Namespace:
    """Parse immutable artifact publication arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Publish the GHSA Silver ZIP create-only and print the Terraform pins. "
            "Build it first with scripts/build_ghsa_silver_lambda_package.py."
        )
    )
    parser.add_argument("--bucket", required=True, help="Versioned deployment-artifacts S3 bucket.")
    parser.add_argument(
        "--artifact",
        type=Path,
        default=DEFAULT_ARTIFACT,
        help="Path to the deterministic deployment ZIP.",
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


def _terraform_locals(*, sha256: str, sha256_base64: str, version_id: str) -> str:
    """Render the exact locals block `ghsa_silver_lambda.tf` requires.

    Args:
        sha256: Hex digest of the artifact.
        sha256_base64: Base64 of the raw digest bytes, which Lambda compares as
            `source_code_hash`.
        version_id: The published S3 object version id.

    Returns:
        The block to paste, formatted as the file already formats it.
    """
    return f'''locals {{
  ghsa_silver_lambda_artifact_sha256 = (
    "{sha256}"
  )

  ghsa_silver_lambda_artifact_sha256_base64 = (
    "{sha256_base64}"
  )

  ghsa_silver_lambda_artifact_version = (
    "{version_id}"
  )

  ghsa_silver_lambda_artifact_key = (
    "lambda/ghsa-silver/${{local.ghsa_silver_lambda_artifact_sha256}}.zip"
  )
}}'''


def main() -> None:
    """Publish the artifact create-only and print its pins.

    Raises:
        RuntimeError: If the artifact is missing, or an existing object cannot be
            verified as byte identical.
    """
    args = parse_args()
    artifact_path = Path(args.artifact)

    if not artifact_path.is_file():
        raise RuntimeError(
            f"missing artifact {artifact_path}; "
            "run scripts/build_ghsa_silver_lambda_package.py first"
        )

    raw_bytes = artifact_path.read_bytes()
    digest = hashlib.sha256(raw_bytes)
    sha256 = digest.hexdigest()
    sha256_base64 = base64.b64encode(digest.digest()).decode("ascii")
    key = f"lambda/{_COMPONENT}/{sha256}.zip"

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
            Metadata={"sha256": sha256, "component": _COMPONENT},
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
    print("Paste this over the locals block in infra/environments/dev/ghsa_silver_lambda.tf:")
    print()
    print(
        _terraform_locals(
            sha256=sha256,
            sha256_base64=sha256_base64,
            version_id=version_id,
        )
    )
    print()
    print("Then plan, admit the plan, and apply. Publishing pins nothing on its own.")


if __name__ == "__main__":
    main()
