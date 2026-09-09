#!/usr/bin/env python3
"""Publish the bounded AgentCore direct-code ZIP under a content-addressed S3 key."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, cast

import boto3

from opslens.agentcore_runtime.artifact_publication import (
    S3AgentCoreArtifactClient,
    publish_agentcore_artifact,
    verify_agentcore_artifact,
)

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "dist" / "agentcore-runtime"
_DEFAULT_ARTIFACT = _DEFAULT_OUTPUT_DIR / "opslens-agentcore-runtime.zip"
_DEFAULT_MANIFEST = _DEFAULT_OUTPUT_DIR / "opslens-agentcore-runtime-package.json"


class _Boto3S3ClientFactory(Protocol):
    """Narrow boto3 to the only deployment service required by this script."""

    def client(self, service_name: Literal["s3"]) -> S3Client:
        """Create a typed S3 client."""
        ...


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish the bounded AgentCore direct-code ZIP create-only."
    )
    parser.add_argument(
        "--bucket",
        required=True,
        help="Versioned private OpsLens deployment-artifacts S3 bucket.",
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        default=_DEFAULT_ARTIFACT,
        help="Path to the deterministic AgentCore Runtime ZIP.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=_DEFAULT_MANIFEST,
        help="Path to the deterministic AgentCore package manifest.",
    )
    return parser.parse_args()


def main() -> int:
    """Verify package identity, publish create-only, and emit bounded evidence JSON."""
    args = _parse_args()
    artifact = verify_agentcore_artifact(
        artifact_path=cast(Path, args.artifact).resolve(),
        manifest_path=cast(Path, args.manifest).resolve(),
    )
    sdk = cast(_Boto3S3ClientFactory, boto3)
    raw_client = sdk.client("s3")
    evidence = publish_agentcore_artifact(
        client=cast(S3AgentCoreArtifactClient, raw_client),
        bucket=cast(str, args.bucket),
        artifact=artifact,
    )
    print(json.dumps(evidence.to_payload(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
