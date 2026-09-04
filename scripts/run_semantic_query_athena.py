#!/usr/bin/env python3
"""Run the first bounded OpsLens semantic query against the real dev Athena workgroup."""

from __future__ import annotations

import argparse
import json
from datetime import date
from typing import cast

from boto3.session import Session

from opslens.semantic_query.adapters.outbound import AthenaQueryClient, AthenaQueryExecutor
from opslens.semantic_query.application import ExecuteSemanticQuery
from opslens.semantic_query.domain import (
    EpssFilters,
    SemanticDimension,
    SemanticMetric,
    SemanticQuery,
)


def _parse_args() -> argparse.Namespace:
    """Parse explicit temporal and execution inputs for the dev smoke test."""
    parser = argparse.ArgumentParser(
        description="Execute the bounded EPSS semantic-query slice in Athena dev."
    )
    parser.add_argument(
        "--snapshot-date",
        required=True,
        type=date.fromisoformat,
        help="Explicit EPSS snapshot date in YYYY-MM-DD form; latest is intentionally unsupported.",
    )
    parser.add_argument(
        "--epss-min",
        type=float,
        default=0.7,
        help="Minimum EPSS score from 0.0 through 1.0 (default: 0.7).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum result rows from 1 through 100 (default: 20).",
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS Region used to create the Athena client (default: us-east-1).",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Optional local AWS profile; omitted uses the standard SDK credential chain.",
    )
    return parser.parse_args()


def _athena_client(session: Session, region: str) -> AthenaQueryClient:
    """Create the Athena client behind the bounded executor Protocol boundary."""
    return cast(
        AthenaQueryClient,
        session.client(  # pyright: ignore[reportUnknownMemberType]
            "athena",
            region_name=region,
        ),
    )


def main() -> int:
    """Compile the typed query, execute it, and print bounded evidence as JSON."""
    args = _parse_args()
    query = SemanticQuery(
        metric=SemanticMetric.EPSS_SCORE,
        dimensions=(SemanticDimension.CVE,),
        filters=EpssFilters(
            snapshot_date=args.snapshot_date,
            minimum_score=args.epss_min,
        ),
        limit=args.limit,
    )

    session = Session(profile_name=args.profile, region_name=args.region)
    client = _athena_client(session, args.region)
    use_case = ExecuteSemanticQuery(AthenaQueryExecutor(client))
    result = use_case.execute(query)

    print(
        json.dumps(
            {
                "query_execution_id": result.query_execution_id,
                "columns": result.columns,
                "rows": result.rows,
                "row_count": len(result.rows),
                "data_scanned_bytes": result.data_scanned_bytes,
                "engine_execution_time_ms": result.engine_execution_time_ms,
                "total_execution_time_ms": result.total_execution_time_ms,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
