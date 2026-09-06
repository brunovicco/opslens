"""Tests for the Gate 7.7 real grounding evaluation CLI evidence serializer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from opslens.knowledge_retrieval.application.grounding_evaluation import (
    load_golden_grounding_dataset,
)
from opslens.knowledge_retrieval.application.grounding_runtime_runner import (
    GroundingRuntimeCaseExecution,
    GroundingRuntimeExecution,
)
from opslens.knowledge_retrieval.cli.run_bedrock_grounding_evaluation import (
    GroundingRuntimeCliError,
    require_grounding_region,
    serialize_grounding_runtime_execution,
)

_REPO_ROOT = Path(__file__).parents[3]
_FIXTURE = (
    _REPO_ROOT
    / "tests"
    / "fixtures"
    / "knowledge_retrieval"
    / "golden_grounding_v1.json"
)


def _partial_execution() -> GroundingRuntimeExecution:
    """Return one content-free failed prefix without requiring any AWS-shaped objects."""
    dataset = load_golden_grounding_dataset(_FIXTURE)
    attempt = GroundingRuntimeCaseExecution(
        case=dataset.cases[0],
        retrieval=None,
        context=None,
        citation_catalog=None,
        synthesis=None,
        failure_category="BedrockRetrievalProviderError",
    )
    return GroundingRuntimeExecution(
        dataset_id=dataset.dataset_id,
        attempts=(attempt,),
        planned_case_count=len(dataset.cases),
    )


def test_cli_region_is_fail_closed_to_frozen_phase_region() -> None:
    """The real harness cannot silently move the evaluation to another Region."""
    assert require_grounding_region("us-east-1") == "us-east-1"
    with pytest.raises(GroundingRuntimeCliError, match="frozen Phase 7 region"):
        require_grounding_region("us-west-2")


def test_serializer_preserves_partial_failure_without_question_or_source_text() -> None:
    """A failed first run remains inspectable without persisting raw input/source bodies."""
    dataset = load_golden_grounding_dataset(_FIXTURE)
    serialized = serialize_grounding_runtime_execution(
        _partial_execution(),
        knowledge_base_id="TESTKB1234",
        region="us-east-1",
    )
    payload = json.loads(serialized)

    assert payload["complete"] is False
    assert payload["application_case_attempt_count"] == 1
    assert payload["planned_case_count"] == 4
    assert payload["planned_top_k"] == 5
    assert payload["semantic_judgments_collected"] is False
    assert payload["cases"][0]["failure_category"] == "BedrockRetrievalProviderError"
    assert payload["cases"][0]["retrieval"] is None
    assert payload["cases"][0]["context"] is None
    assert payload["cases"][0]["synthesis"] is None
    assert dataset.cases[0].question not in serialized


def test_serializer_identifies_frozen_dataset_and_model_profile() -> None:
    """Operational evidence records the evaluated contract/model identities explicitly."""
    payload = json.loads(
        serialize_grounding_runtime_execution(
            _partial_execution(),
            knowledge_base_id="TESTKB1234",
            region="us-east-1",
        )
    )

    assert payload["dataset_id"] == "knowledge-grounding-golden:v1"
    assert payload["knowledge_base_id"] == "TESTKB1234"
    assert payload["model_id"] == "us.anthropic.claude-haiku-4-5-20251001-v1:0"
