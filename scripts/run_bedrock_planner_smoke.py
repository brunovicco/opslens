"""Run one bounded Phase 6 Gate 6.4 Bedrock planner invocation."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import cast

import boto3

from opslens.semantic_query.adapters.outbound.bedrock_planner import (
    BedrockConverseClient,
    BedrockSemanticPlanner,
)
from opslens.semantic_query.planner.bedrock import BEDROCK_PLANNER_REGION
from opslens.semantic_query.planner.models import PlannedSemanticQuery, SemanticPlannerRequest

SMOKE_QUESTION = "Show the 5 CVEs with the highest EPSS score on 2026-09-01."
PRICING_SNAPSHOT_DATE = "2026-09-04"
INPUT_USD_PER_MILLION = Decimal("1.10")
OUTPUT_USD_PER_MILLION = Decimal("5.50")


def _observed_cost_usd(input_tokens: int, output_tokens: int) -> Decimal:
    """Calculate smoke cost only from measured tokens and the dated pricing snapshot."""
    million = Decimal(1_000_000)
    return (
        Decimal(input_tokens) * INPUT_USD_PER_MILLION
        + Decimal(output_tokens) * OUTPUT_USD_PER_MILLION
    ) / million


def main() -> int:
    """Invoke the frozen model once and print bounded evidence only."""
    client = cast(
        BedrockConverseClient,
        boto3.client("bedrock-runtime", region_name=BEDROCK_PLANNER_REGION),
    )
    result = BedrockSemanticPlanner(client).plan(SemanticPlannerRequest(SMOKE_QUESTION))
    if not isinstance(result.outcome, PlannedSemanticQuery):
        raise RuntimeError("Gate 6.4 smoke question did not produce a semantic_query proposal.")

    query = result.outcome.query
    evidence = {
        "gate": "6.4",
        "region": BEDROCK_PLANNER_REGION,
        "pricing_snapshot_date": PRICING_SNAPSHOT_DATE,
        "input_usd_per_million": str(INPUT_USD_PER_MILLION),
        "output_usd_per_million": str(OUTPUT_USD_PER_MILLION),
        "observed_cost_usd": str(
            _observed_cost_usd(result.usage.input_tokens, result.usage.output_tokens)
        ),
        "usage": {
            "input_tokens": result.usage.input_tokens,
            "output_tokens": result.usage.output_tokens,
            "total_tokens": result.usage.total_tokens,
            "latency_ms": result.usage.latency_ms,
        },
        "proposal": {
            "metric": query.metric.value,
            "dimensions": [dimension.value for dimension in query.dimensions],
            "snapshot_date": query.filters.snapshot_date.isoformat(),
            "minimum_score": query.filters.minimum_score,
            "order_by": query.order_by.value,
            "order_direction": query.order_direction.value,
            "limit": query.limit,
        },
    }
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
