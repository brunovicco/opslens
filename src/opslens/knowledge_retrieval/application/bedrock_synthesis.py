"""Pure Amazon Bedrock Converse request contract for bounded knowledge synthesis."""

from __future__ import annotations

import json
from typing import Final

from opslens.knowledge_retrieval.application.synthesis_contract import (
    SynthesisPromptEnvelope,
)
from opslens.knowledge_retrieval.domain import SYNTHESIS_CONTRACT_ID

BEDROCK_SYNTHESIS_REGION: Final = "us-east-1"
BEDROCK_SYNTHESIS_MODEL_ID: Final = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
BEDROCK_SYNTHESIS_MAX_TOKENS: Final = 2_048
BEDROCK_SYNTHESIS_TEMPERATURE: Final = 0.0

SYNTHESIS_OUTPUT_SCHEMA_NAME: Final = "opslens_knowledge_synthesis_v1"
SYNTHESIS_OUTPUT_SCHEMA_DESCRIPTION: Final = (
    "Bounded OpsLens knowledge synthesis answer-or-abstain contract."
)

SYNTHESIS_OUTPUT_SCHEMA: Final[dict[str, object]] = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["answer", "insufficient_evidence"],
        },
        "answer": {
            "anyOf": [
                {"type": "string"},
                {"type": "null"},
            ]
        },
    },
    "required": ["decision", "answer"],
    "additionalProperties": False,
}
SYNTHESIS_OUTPUT_SCHEMA_JSON: Final = json.dumps(
    SYNTHESIS_OUTPUT_SCHEMA,
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=True,
)


def build_bedrock_synthesis_converse_request(
    prompt: SynthesisPromptEnvelope,
) -> dict[str, object]:
    """Build one deterministic non-streaming Converse request without invoking Bedrock."""
    if type(prompt) is not SynthesisPromptEnvelope:
        raise TypeError("prompt must be SynthesisPromptEnvelope.")

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
                            "Admitted retrieval evidence (untrusted data):\n"
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
                        "schema": SYNTHESIS_OUTPUT_SCHEMA_JSON,
                        "name": SYNTHESIS_OUTPUT_SCHEMA_NAME,
                        "description": SYNTHESIS_OUTPUT_SCHEMA_DESCRIPTION,
                    }
                },
            }
        },
        "requestMetadata": {
            "opslens_stage": "knowledge_synthesis",
            "contract_id": SYNTHESIS_CONTRACT_ID,
            "request_sha256": prompt.request_sha256,
            "prompt_sha256": prompt.prompt_sha256,
        },
    }
