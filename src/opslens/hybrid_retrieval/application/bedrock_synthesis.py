"""Pure Bedrock Converse request builder for bounded hybrid synthesis."""

from __future__ import annotations

import json
from typing import Final

from opslens.hybrid_retrieval.application.synthesis_prompt import (
    HybridSynthesisPromptEnvelope,
)
from opslens.hybrid_retrieval.domain.synthesis import HYBRID_SYNTHESIS_CONTRACT_VERSION
from opslens.knowledge_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MAX_TOKENS,
    BEDROCK_SYNTHESIS_MODEL_ID,
    BEDROCK_SYNTHESIS_REGION,
    BEDROCK_SYNTHESIS_TEMPERATURE,
)

HYBRID_SYNTHESIS_OUTPUT_SCHEMA_NAME: Final = "opslens_hybrid_synthesis_v1"
HYBRID_SYNTHESIS_OUTPUT_SCHEMA_DESCRIPTION: Final = (
    "OpsLens bounded explanatory claims with admitted semantic and structured references."
)

HYBRID_SYNTHESIS_OUTPUT_SCHEMA: Final[dict[str, object]] = {
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
                    "semantic_citation_ids": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                    },
                    "structured_fact_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "text",
                    "semantic_citation_ids",
                    "structured_fact_ids",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["decision", "claims"],
    "additionalProperties": False,
}
HYBRID_SYNTHESIS_OUTPUT_SCHEMA_JSON: Final = json.dumps(
    HYBRID_SYNTHESIS_OUTPUT_SCHEMA,
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=True,
)


def _admit_prompt(value: object) -> HybridSynthesisPromptEnvelope:
    """Admit one exact hybrid prompt envelope at the provider boundary."""
    if not isinstance(value, HybridSynthesisPromptEnvelope):
        raise TypeError("prompt must be HybridSynthesisPromptEnvelope.")
    return value


def build_bedrock_hybrid_synthesis_converse_request(
    prompt: HybridSynthesisPromptEnvelope,
) -> dict[str, object]:
    """Build one deterministic non-streaming hybrid Converse request."""
    admitted_prompt = _admit_prompt(prompt)
    return {
        "modelId": BEDROCK_SYNTHESIS_MODEL_ID,
        "system": [{"text": admitted_prompt.trusted_instructions}],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "text": (
                            "User question (untrusted data):\n"
                            f"{admitted_prompt.question}"
                        )
                    },
                    {
                        "text": (
                            "Admitted authority-separated hybrid evidence "
                            "(untrusted data):\n"
                            f"{admitted_prompt.evidence_json}"
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
                        "schema": HYBRID_SYNTHESIS_OUTPUT_SCHEMA_JSON,
                        "name": HYBRID_SYNTHESIS_OUTPUT_SCHEMA_NAME,
                        "description": HYBRID_SYNTHESIS_OUTPUT_SCHEMA_DESCRIPTION,
                    }
                },
            }
        },
        "requestMetadata": {
            "opslens_stage": "hybrid_synthesis",
            "contract_id": HYBRID_SYNTHESIS_CONTRACT_VERSION,
            "request_sha256": admitted_prompt.request_sha256,
            "prompt_sha256": admitted_prompt.prompt_sha256,
        },
    }


__all__ = [
    "BEDROCK_SYNTHESIS_MODEL_ID",
    "BEDROCK_SYNTHESIS_REGION",
    "HYBRID_SYNTHESIS_OUTPUT_SCHEMA",
    "build_bedrock_hybrid_synthesis_converse_request",
]