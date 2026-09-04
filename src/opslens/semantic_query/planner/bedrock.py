"""Pure Amazon Bedrock Converse request contract for the bounded semantic planner."""

from __future__ import annotations

from typing import Final

from opslens.semantic_query.planner.models import SemanticPlannerRequest
from opslens.semantic_query.planner.schema import (
    PLANNER_OUTPUT_SCHEMA_JSON,
    PLANNER_SCHEMA_DESCRIPTION,
    PLANNER_SCHEMA_NAME,
)

BEDROCK_PLANNER_REGION: Final = "us-east-1"
BEDROCK_PLANNER_MODEL_ID: Final = "anthropic.claude-haiku-4-5-20251001-v1:0"
BEDROCK_PLANNER_MAX_TOKENS: Final = 256
BEDROCK_PLANNER_TEMPERATURE: Final = 0.0

PLANNER_SYSTEM_PROMPT: Final = """\
You are the bounded structured-query planner for OpsLens.

You may plan only this exact semantic surface:
- metric: epss_score
- dimensions: exactly [cve]
- snapshot_date: an explicit YYYY-MM-DD calendar date supplied by the user
- minimum_score: optional EPSS threshold in the inclusive range 0.0 through 1.0
- threshold semantics: only "at least" or >= are supported
- order_by: epss_score
- order_direction: asc or desc
- limit: integer 1 through 100; default 20

Rules:
- Never output SQL or invent SQL identifiers.
- Never invent, infer, or substitute a date.
- "today", "current", "latest", relative dates, or missing dates are unsupported.
- Strict greater-than threshold semantics such as "above", "greater than", or > are unsupported.
- Normalize a valid percentage threshold such as 70% to 0.7.
- "highest" means desc and "lowest" means asc.
- Questions about KEV, remediation, priority tiers, repositories, knowledge retrieval, or
  any semantic surface not listed above are unsupported.
- If the request is ambiguous, return the ambiguous unsupported reason.
- Emit only the structured decision required by the response schema.
"""


def build_bedrock_converse_request(
    request: SemanticPlannerRequest,
) -> dict[str, object]:
    """Build a deterministic Converse request without invoking Amazon Bedrock."""
    if type(request) is not SemanticPlannerRequest:
        raise TypeError("request must be SemanticPlannerRequest.")

    return {
        "modelId": BEDROCK_PLANNER_MODEL_ID,
        "system": [{"text": PLANNER_SYSTEM_PROMPT}],
        "messages": [
            {
                "role": "user",
                "content": [{"text": request.question}],
            }
        ],
        "inferenceConfig": {
            "maxTokens": BEDROCK_PLANNER_MAX_TOKENS,
            "temperature": BEDROCK_PLANNER_TEMPERATURE,
        },
        "outputConfig": {
            "textFormat": {
                "type": "json_schema",
                "structure": {
                    "jsonSchema": {
                        "schema": PLANNER_OUTPUT_SCHEMA_JSON,
                        "name": PLANNER_SCHEMA_NAME,
                        "description": PLANNER_SCHEMA_DESCRIPTION,
                    }
                },
            }
        },
    }
