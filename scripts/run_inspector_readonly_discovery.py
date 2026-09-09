"""Run the bounded Gate 16.2 Amazon Inspector read-only discovery."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import cast

import boto3

from opslens.runtime_exposure.adapters.inspector_readonly import (
    InspectorReadClient,
    run_readonly_inspector_discovery,
)


def _parser() -> argparse.ArgumentParser:
    """Build the small command-line surface for the read-only experiment."""
    parser = argparse.ArgumentParser(
        description="Run content-minimized Amazon Inspector read-only discovery."
    )
    parser.add_argument("--region", required=True)
    parser.add_argument("--expected-account-id")
    return parser


def main() -> int:
    """Execute only ListCoverage/ListFindings and emit machine-readable evidence."""
    args = _parser().parse_args()
    client = cast(InspectorReadClient, boto3.client("inspector2", region_name=args.region))
    evidence = run_readonly_inspector_discovery(
        client=client,
        region=args.region,
        expected_account_id=args.expected_account_id,
    )
    print(json.dumps(asdict(evidence), allow_nan=False, indent=2, sort_keys=True))
    if evidence.result in {"SUCCESS", "BLOCKED_BY_EXISTING_IAM"}:
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
