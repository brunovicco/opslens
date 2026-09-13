"""Regression tests for the Bedrock-supported Gate 11.4 output schema subset."""

import json
from typing import cast

from opslens.agent_baseline.adapters.bedrock_reasoning import (
    BEDROCK_AGENT_REASONING_OUTPUT_SCHEMA_JSON,
)
from opslens.agent_baseline.domain import AgentCapability


def test_bedrock_reasoning_schema_avoids_unsupported_one_of() -> None:
    """Keep provider schema flat while deterministic code owns cross-field admission."""
    schema = cast(dict[str, object], json.loads(BEDROCK_AGENT_REASONING_OUTPUT_SCHEMA_JSON))

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["decision", "capability"]
    assert "oneOf" not in schema

    properties = cast(dict[str, object], schema["properties"])
    decision = cast(dict[str, object], properties["decision"])
    capability = cast(dict[str, object], properties["capability"])

    assert decision["enum"] == ["act", "abstain"]
    assert capability["enum"] == [
        *[item.value for item in AgentCapability],
        None,
    ]
