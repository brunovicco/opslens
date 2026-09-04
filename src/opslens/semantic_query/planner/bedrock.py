"""Pure Amazon Bedrock Converse request contract for the bounded semantic planner."""

from __future__ import annotations

from typing import Final

from opslens.semantic_query.planner.models import SemanticPlannerRequest
from opslens.semantic_query.planner.prompt import PLANNER_MAX_TOKENS, PLANNER_SYSTEM_PROMPT
from opslens.semantic_query.planner.schema import (
    PLANNER_OUTPUT_SCHEMA_JSON,
    PLANNER_SCHEMA_DESCRIPTION,
    PLANNER_SCHEMA_NAME,
)

BEDROCK_PLANNER_REGION: Final = "us-east-1"
BEDROCK_PLANNER_MODEL_ID: Final = "anthropic.claude-haiku-4-5-20251001-v1:0"
BEDROCK_PLANNER_MAX_TOKENS: Final = PLANNER_MAX_TOKENS
BEDROCK_PLANNER_TEMPERATURE: Final = 0.0


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
