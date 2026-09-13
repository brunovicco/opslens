"""Materialize Gate 19.2 threat authority through an explicit human-run read-only boundary."""

import argparse
import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import boto3
from botocore.config import Config

from opslens.public_analysis.adapters.exact_s3_authority_object import (
    ExactS3AuthorityObjectClient,
)
from opslens.public_analysis.adapters.representative_threat_authority_reader_factory import (
    RepresentativeThreatAuthorityByteLimits,
    build_representative_threat_authority_readers,
)
from opslens.public_analysis.application.representative_pre_measurement_authority import (
    materialize_pre_measurement_threat_evidence,
)
from opslens.public_analysis.application.representative_threat_evidence_coordinate_loaders import (
    parse_representative_threat_evidence_coordinates,
)
from opslens.public_analysis.application.representative_threat_evidence_preparation import (
    summarize_representative_threat_evidence_preparation,
)


def _positive_int(value: str) -> int:
    """Parse one required positive integer CLI value."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def parse_args() -> argparse.Namespace:
    """Parse explicit operator inputs; no physical authority coordinate is inferred."""
    parser = argparse.ArgumentParser(
        description=(
            "Materialize Gate 19.2 threat evidence from explicit immutable source locators. "
            "This performs read-only pre-measurement S3 GetObject calls."
        )
    )
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--locator-manifest", required=True, type=Path)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--ghsa-silver-max-bytes", required=True, type=_positive_int)
    parser.add_argument("--nvd-silver-max-bytes", required=True, type=_positive_int)
    parser.add_argument("--nvd-bronze-max-bytes", required=True, type=_positive_int)
    parser.add_argument("--kev-bronze-max-bytes", required=True, type=_positive_int)
    parser.add_argument("--epss-bronze-max-bytes", required=True, type=_positive_int)
    return parser.parse_args()


def _load_json_object(path: Path) -> tuple[bytes, Mapping[str, object]]:
    """Read one local JSON input exactly once and require a top-level object."""
    payload = path.read_bytes()
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path} must contain valid UTF-8 JSON") from exc
    if not isinstance(decoded, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload, cast(Mapping[str, object], decoded)


def main() -> None:
    """Run explicit read-only authority materialization and print a bounded proof summary."""
    args = parse_args()
    bundle_bytes, bundle = _load_json_object(args.bundle)
    manifest_bytes, locator_manifest = _load_json_object(args.locator_manifest)

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    s3_client = cast(
        ExactS3AuthorityObjectClient,
        session.client(
            "s3",
            config=Config(retries={"mode": "standard", "total_max_attempts": 1}),
        ),
    )
    readers = build_representative_threat_authority_readers(
        client=s3_client,
        bucket_name=args.bucket,
        byte_limits=RepresentativeThreatAuthorityByteLimits(
            ghsa_silver=args.ghsa_silver_max_bytes,
            nvd_silver=args.nvd_silver_max_bytes,
            nvd_bronze=args.nvd_bronze_max_bytes,
            kev_bronze=args.kev_bronze_max_bytes,
            epss_bronze=args.epss_bronze_max_bytes,
        ),
    )
    evidence = materialize_pre_measurement_threat_evidence(
        bundle,
        locator_manifest=locator_manifest,
        readers=readers,
    )
    coordinates = parse_representative_threat_evidence_coordinates(bundle)
    summary = summarize_representative_threat_evidence_preparation(
        coordinates=coordinates,
        evidence=evidence,
        bundle_sha256=sha256(bundle_bytes).hexdigest(),
        locator_manifest_sha256=sha256(manifest_bytes).hexdigest(),
    )
    print(json.dumps(summary.to_json_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
