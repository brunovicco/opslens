"""Run one bounded real Bedrock Knowledge Base ingestion job."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import cast

from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from botocore.session import get_session

from opslens.knowledge_retrieval.adapters.bedrock_ingestion import (
    BedrockIngestionAdapterError,
    BedrockIngestionClient,
    BoundedBedrockIngestionControl,
)
from opslens.knowledge_retrieval.application.bedrock_ingestion import (
    BedrockIngestionFailed,
    BedrockIngestionTimeout,
    BedrockIngestionValidationError,
    IngestionJobEvidence,
    run_bounded_ingestion,
)

_REQUIRED_REGION = "us-east-1"


class IngestionCliError(ValueError):
    """Raised when CLI inputs do not authorize one bounded ingestion run."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Start exactly one Bedrock Knowledge Base ingestion job, poll within a fixed "
            "budget, and emit only target/status/statistics evidence."
        )
    )
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--data-source-id", required=True)
    parser.add_argument("--region", default=_REQUIRED_REGION)
    parser.add_argument("--max-polls", type=int, default=30)
    parser.add_argument("--poll-interval-seconds", type=float, default=5.0)
    return parser


def require_ingestion_region(value: object) -> str:
    """Require the single frozen Gate 7.3 AWS region."""
    if not isinstance(value, str) or value != _REQUIRED_REGION:
        raise IngestionCliError(
            f"region must equal the frozen Gate 7.3 region {_REQUIRED_REGION!r}"
        )
    return value


def serialize_ingestion_evidence(evidence: IngestionJobEvidence, *, region: str) -> str:
    """Serialize terminal ingestion evidence deterministically without corpus text."""
    return json.dumps(
        {
            "data_source_id": evidence.data_source_id,
            "failure_reasons": list(evidence.failure_reasons),
            "ingestion_job_id": evidence.ingestion_job_id,
            "knowledge_base_id": evidence.knowledge_base_id,
            "region": region,
            "statistics": evidence.statistics,
            "status": evidence.status,
        },
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Run one real bounded ingestion job against explicit KB/data-source identifiers."""
    args = _parser().parse_args(argv)
    knowledge_base_id = cast(str, args.knowledge_base_id)
    data_source_id = cast(str, args.data_source_id)
    max_polls = cast(int, args.max_polls)
    poll_interval_seconds = cast(float, args.poll_interval_seconds)

    try:
        region = require_ingestion_region(args.region)
        dynamic_client = get_session().create_client(
            "bedrock-agent",
            region_name=region,
            config=Config(
                connect_timeout=5,
                read_timeout=30,
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
        client = cast(BedrockIngestionClient, dynamic_client)
        evidence = run_bounded_ingestion(
            BoundedBedrockIngestionControl(client),
            knowledge_base_id=knowledge_base_id,
            data_source_id=data_source_id,
            max_polls=max_polls,
            poll_interval_seconds=poll_interval_seconds,
        )
    except (
        BedrockIngestionAdapterError,
        BedrockIngestionFailed,
        BedrockIngestionTimeout,
        BedrockIngestionValidationError,
        BotoCoreError,
        ClientError,
        IngestionCliError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(serialize_ingestion_evidence(evidence, region=region), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
