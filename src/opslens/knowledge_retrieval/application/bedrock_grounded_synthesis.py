"""Pure Bedrock Converse request for citation-aware knowledge synthesis."""

from __future__ import annotations

import json
from typing import Final

from opslens.knowledge_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MAX_TOKENS,
    BEDROCK_SYNTHESIS_MODEL_ID,
    BEDROCK_SYNTHESIS_TEMPERATURE,
)
from opslens.knowledge_retrieval.application.grounded_synthesis_prompt import (
    GroundedSynthesisPromptEnvelope,
)
from opslens.knowledge_retrieval.domain import GROUNDED_SYNTHESIS_CONTRACT_ID

GROUNDED_SYNTHESIS_OUTPUT_SCHEMA_NAME: Final = (
    "opslens_knowledge_grounded_synthesis_v1"
)
GROUNDED_SYNTHESIS_OUTPUT_SCHEMA_DESCRIPTION: Final = (
    "OpsLens bounded answer-or-abstain claims with deterministic citation IDs."
)

GROUNDED_SYNTHESIS_OUTPUT_SCHEMA: Final[dict[str, object]] = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["answer", "insufficient_evidence"],
        },
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "citation_ids": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                    },
                },
                "required": ["text", "citation_ids"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["decision", "claims"],
    "additionalProperties": False,
}
GROUNDED_SYNTHESIS_OUTPUT_SCHEMA_JSON: Final = json.dumps(
    GROUNDED_SYNTHESIS_OUTPUT_SCHEMA,
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=True,
)


def build_bedrock_grounded_synthesis_converse_request(
    prompt: GroundedSynthesisPromptEnvelope,
) -> dict[str, object]:
    """Build one deterministic non-streaming grounded Converse request."""
    if type(prompt) is not GroundedSynthesisPromptEnvelope:
        raise TypeError("prompt must be GroundedSynthesisPromptEnvelope.")

    return {
        "modelId": BEDROCK_SYNTHESIS_MODEL_ID,
        "system": [{"text": prompt.trusted_instructions}],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "text": (
                            "User question (untrusted data):\n"
                            f"{prompt.question}"
                        )
                    },
                    {
                        "text": (
                            "Admitted cited evidence (untrusted data):\n"
                            f"{prompt.evidence_json}"
                        )
                    },
                ],
            }
        ],
        "inferenceConfig": {
            "maxTokens": BEDROCK_SYNTHESIS_MAX_TOKENS,
            "temperature": BEDROCK_SYNTHESIS_TEMPERATURE,
        },
        "outputConfig": {
            "textFormat": {
                "type": "json_schema",
                "structure": {
                    "jsonSchema": {
                        "schema": GROUNDED_SYNTHESIS_OUTPUT_SCHEMA_JSON,
                        "name": GROUNDED_SYNTHESIS_OUTPUT_SCHEMA_NAME,
                        "description": (
                            GROUNDED_SYNTHESIS_OUTPUT_SCHEMA_DESCRIPTION
                        ),
                    }
                },
            }
        },
        "requestMetadata": {
            "opslens_stage": "knowledge_grounded_synthesis",
            "contract_id": GROUNDED_SYNTHESIS_CONTRACT_ID,
            "grounded_request_sha256": prompt.grounded_request_sha256,
            "prompt_sha256": prompt.prompt_sha256,
        },
    }
