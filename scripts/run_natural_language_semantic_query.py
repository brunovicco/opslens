#!/usr/bin/env python3
"""Run one bounded natural-language semantic query through Bedrock and Athena dev."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import cast

from boto3.session import Session
from botocore.config import Config

from opslens.semantic_query.adapters.outbound import (
    AthenaQueryClient,
    AthenaQueryExecutor,
    BedrockConverseClient,
    BedrockSemanticPlanner,
)
from opslens.semantic_query.application import (
    ExecutedNaturalLanguageSemanticQuery,
    ExecuteNaturalLanguageSemanticQuery,
    ExecuteSemanticQuery,
    UnsupportedNaturalLanguageSemanticQuery,
)
from opslens.semantic_query.planner import (
    BEDROCK_PLANNER_REGION,
    SemanticPlannerRequest,
)


def _parse_args() -> argparse.Namespace:
    """Parse one explicit natural-language question and local AWS client settings."""
    parser = argparse.ArgumentParser(
        description=(
            "Plan one bounded EPSS question with Bedrock and execute only a validated "
            "SemanticQuery in the Athena dev workgroup."
        )
    )
    parser.add_argument(
        "question",
        help=(
            "Natural-language question. The first slice requires an explicit YYYY-MM-DD "
            "snapshot date and supports only the frozen EPSS semantics."
        ),
    )
    parser.add_argument(
        "--athena-region",
        default="us-east-1",
        help="AWS Region used to create the Athena client (default: us-east-1).",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Optional local AWS profile; omitted uses the standard SDK credential chain.",
    )
    return parser.parse_args()


def main() -> int:
    """Execute the versioned bounded Bedrock-to-Athena path and print JSON evidence."""
    args = _parse_args()
    request = SemanticPlannerRequest(args.question)

    session = Session(profile_name=args.profile)
    bedrock_client = cast(
        BedrockConverseClient,
        session.client(
            "bedrock-runtime",
            region_name=BEDROCK_PLANNER_REGION,
            config=Config(
                connect_timeout=10,
                read_timeout=300,
                retries={"total_max_attempts": 1, "mode": "standard"},
            ),
        ),
    )
    athena_client = cast(
        AthenaQueryClient,
        session.client("athena", region_name=args.athena_region),
    )

    use_case = ExecuteNaturalLanguageSemanticQuery(
        BedrockSemanticPlanner(bedrock_client),
        ExecuteSemanticQuery(AthenaQueryExecutor(athena_client)),
    )
    outcome = use_case.execute(request)

    if isinstance(outcome, UnsupportedNaturalLanguageSemanticQuery):
        payload: dict[str, object] = {
            "question": request.question,
            "decision": "unsupported",
            "reason": outcome.reason.value,
            "planner_evidence": asdict(outcome.planner_evidence),
            "athena_invoked": False,
        }
    elif isinstance(outcome, ExecutedNaturalLanguageSemanticQuery):
        payload = {
            "question": request.question,
            "decision": "semantic_query",
            "semantic_query": repr(outcome.semantic_query),
            "planner_evidence": asdict(outcome.planner_evidence),
            "athena": {
                "query_execution_id": outcome.result.query_execution_id,
                "columns": outcome.result.columns,
                "rows": outcome.result.rows,
                "row_count": len(outcome.result.rows),
                "data_scanned_bytes": outcome.result.data_scanned_bytes,
                "engine_execution_time_ms": outcome.result.engine_execution_time_ms,
                "total_execution_time_ms": outcome.result.total_execution_time_ms,
            },
        }
    else:
        raise TypeError(f"Unknown natural-language semantic-query outcome: {type(outcome).__name__}")

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
