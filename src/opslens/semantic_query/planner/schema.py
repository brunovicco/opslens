"""Bedrock structured-output schema for the frozen semantic planner contract."""

from __future__ import annotations

import json
from typing import Final

from opslens.semantic_query.planner.models import PlannerDecision, UnsupportedReason

PLANNER_SCHEMA_NAME: Final = "opslens_semantic_query_plan_v1"
PLANNER_SCHEMA_DESCRIPTION: Final = (
    "Plan only the first allowlisted OpsLens EPSS semantic-query slice or fail closed."
)

PLANNER_OUTPUT_SCHEMA: Final[dict[str, object]] = {
    "anyOf": [
        {
            "type": "object",
            "properties": {
                "decision": {"const": PlannerDecision.SEMANTIC_QUERY.value},
                "metric": {"enum": ["epss_score"]},
                "dimensions": {
                    "type": "array",
                    "items": {"enum": ["cve"]},
                    "minItems": 1,
                },
                "filters": {
                    "type": "object",
                    "properties": {
                        "snapshot_date": {"type": "string", "format": "date"},
                        "minimum_score": {
                            "anyOf": [
                                {"type": "number"},
                                {"type": "null"},
                            ]
                        },
                    },
                    "required": ["snapshot_date", "minimum_score"],
                    "additionalProperties": False,
                },
                "order_by": {"enum": ["epss_score"]},
                "order_direction": {"enum": ["asc", "desc"]},
                "limit": {"type": "integer"},
            },
            "required": [
                "decision",
                "metric",
                "dimensions",
                "filters",
                "order_by",
                "order_direction",
                "limit",
            ],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "decision": {"const": PlannerDecision.UNSUPPORTED.value},
                "reason": {"enum": [reason.value for reason in UnsupportedReason]},
            },
            "required": ["decision", "reason"],
            "additionalProperties": False,
        },
    ]
}

PLANNER_OUTPUT_SCHEMA_JSON: Final = json.dumps(
    PLANNER_OUTPUT_SCHEMA,
    sort_keys=True,
    separators=(",", ":"),
)
