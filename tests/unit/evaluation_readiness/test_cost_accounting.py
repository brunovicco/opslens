"""Unit tests for the Phase 18 cost-accounting and budget-envelope validator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from opslens.evaluation_readiness import (
    CostAccountingValidationError,
    validate_cost_accounting,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CANONICAL_ARTIFACT = (
    _REPO_ROOT / "labs/evidence/phase-18-gate-18-3-cost-accounting-v1.json"
)


OBSERVATION_METRICS: dict[str, tuple[str, str, object, str]] = {
    "p8.hybrid.cost": ("cost", "UNMEASURED", None, "usd"),
    "p11.reasoning.derived_inference_cost": ("cost", "DERIVED", 0.0041921, "usd"),
    "p12.reasoning.derived_inference_cost": ("cost", "DERIVED", 0.0074338, "usd"),
    "p14.agentcore.total_experiment_cost": (
        "cost",
        "DERIVED",
        0.006572445136128483,
        "usd",
    ),
    "p14.agentcore.monthly_extrapolation": ("cost", "UNMEASURED", None, "usd_per_month"),
    "p15.a2a.aws_runtime_cost": ("cost", "NOT_APPLICABLE", None, "usd"),
    "p16.inspector.aws_cost": ("cost", "UNMEASURED", None, "usd"),
    "p11.reasoning.total_tokens": ("token_volume", "MEASURED", 3395, "tokens"),
    "p12.reasoning.total_tokens": ("token_volume", "MEASURED", 5982, "tokens"),
}


SOURCE_LITERALS = {
    "src/opslens/semantic_query/planner/bedrock.py": "BEDROCK_PLANNER_MAX_TOKENS: Final = 256",
    "src/opslens/agent_baseline/adapters/bedrock_reasoning.py": (
        "BEDROCK_AGENT_REASONING_MAX_TOKENS: Final = 96"
    ),
    "src/opslens/multi_agent/adapters/bedrock_triage_reasoning.py": (
        "BEDROCK_TRIAGE_REASONING_MAX_TOKENS: Final = 64"
    ),
    "src/opslens/knowledge_retrieval/application/bedrock_synthesis.py": (
        "BEDROCK_SYNTHESIS_MAX_TOKENS: Final = 2_048"
    ),
    "infra/environments/dev/analytics_athena.tf": (
        "bytes_scanned_cutoff_per_query = 10485760"
    ),
    "infra/environments/dev/operational_recovery.tf": (
        "scheduled_ingestion_maximum_event_age_in_seconds = 3600\n"
        "scheduled_ingestion_maximum_retry_attempts       = 2"
    ),
}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _artifact() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(_CANONICAL_ARTIFACT.read_text(encoding="utf-8")),
    )


def _prepare(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    view_metrics = [
        {
            "metric_id": metric_id,
            "dimension": dimension,
            "classification": classification,
            "value": value,
            "unit": unit,
        }
        for metric_id, (dimension, classification, value, unit) in OBSERVATION_METRICS.items()
    ]
    _write_json(
        tmp_path / "labs/evidence/phase-18-gate-18-2-consolidated-view-v1.json",
        {"sections": [{"metrics": view_metrics}]},
    )
    _write_json(
        tmp_path / "labs/evidence/phase-17-gate-17-6-operational-recovery-v1.json",
        {
            "existing_abuse_cost_controls": {
                "semantic_planner_max_tokens": 256,
                "single_agent_reasoning_max_tokens": 96,
                "triage_reasoning_max_tokens": 64,
                "knowledge_synthesis_max_tokens": 2048,
                "athena_bytes_scanned_cutoff_per_query": 10485760,
            },
            "delivery_budget": {
                "maximum_event_age_seconds": 3600,
                "maximum_retry_attempts": 2,
            },
        },
    )
    for relative, content in SOURCE_LITERALS.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
    artifact = _artifact()
    artifact_path = tmp_path / "labs/evidence/phase-18-gate-18-3-cost-accounting-v1.json"
    _write_json(artifact_path, artifact)
    return artifact_path, artifact


def _entries(artifact: dict[str, object]) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], artifact["entries"])


def _entry(artifact: dict[str, object], entry_id: str) -> dict[str, object]:
    return next(entry for entry in _entries(artifact) if entry["entry_id"] == entry_id)


def test_accepts_frozen_first_slice(tmp_path: Path) -> None:
    """The canonical first slice preserves observations, nulls, and configured limits."""
    artifact_path, _ = _prepare(tmp_path)
    summary = validate_cost_accounting(artifact_path=artifact_path, repo_root=tmp_path)
    assert summary.entry_count == 16
    assert summary.cost_observation_count == 7
    assert summary.resource_observation_count == 2
    assert summary.configured_limit_count == 7
    assert summary.unmeasured_count == 3
    assert summary.not_applicable_count == 1


def test_rejects_unknown_observation_metric(tmp_path: Path) -> None:
    """An entry cannot switch to a different Gate 18.2 metric."""
    artifact_path, artifact = _prepare(tmp_path)
    _entry(artifact, "cost.p11.reasoning.inference")["source_metric_id"] = "unknown.metric"
    _write_json(artifact_path, artifact)
    with pytest.raises(CostAccountingValidationError, match="must retain source metric"):
        validate_cost_accounting(artifact_path=artifact_path, repo_root=tmp_path)


def test_rejects_unmeasured_zero_laundering(tmp_path: Path) -> None:
    """UNMEASURED cost remains null rather than becoming a synthetic zero."""
    artifact_path, artifact = _prepare(tmp_path)
    _entry(artifact, "cost.p8.hybrid.complete")["value"] = 0
    _write_json(artifact_path, artifact)
    with pytest.raises(CostAccountingValidationError, match="value drifted"):
        validate_cost_accounting(artifact_path=artifact_path, repo_root=tmp_path)


def test_rejects_not_applicable_zero_laundering(tmp_path: Path) -> None:
    """NOT_APPLICABLE cloud cost remains null rather than becoming zero spend."""
    artifact_path, artifact = _prepare(tmp_path)
    _entry(artifact, "cost.p15.a2a.aws_runtime")["value"] = 0
    _write_json(artifact_path, artifact)
    with pytest.raises(CostAccountingValidationError, match="value drifted"):
        validate_cost_accounting(artifact_path=artifact_path, repo_root=tmp_path)


def test_rejects_observation_classification_drift(tmp_path: Path) -> None:
    """Derived cost cannot be relabeled as observed provider spend."""
    artifact_path, artifact = _prepare(tmp_path)
    _entry(artifact, "cost.p11.reasoning.inference")["classification"] = "OBSERVED"
    _write_json(artifact_path, artifact)
    with pytest.raises(CostAccountingValidationError, match="classification drift"):
        validate_cost_accounting(artifact_path=artifact_path, repo_root=tmp_path)


def test_rejects_configured_limit_literal_drift(tmp_path: Path) -> None:
    """Configured limits must still exist in the retained repository source."""
    artifact_path, artifact = _prepare(tmp_path)
    entry = _entry(artifact, "limit.single_agent.output_tokens")
    entry["source_literal"] = "BEDROCK_AGENT_REASONING_MAX_TOKENS: Final = 999"
    _write_json(artifact_path, artifact)
    with pytest.raises(CostAccountingValidationError, match="source_literal not found"):
        validate_cost_accounting(artifact_path=artifact_path, repo_root=tmp_path)


def test_rejects_configured_limit_evidence_drift(tmp_path: Path) -> None:
    """Repository limits must agree with retained control evidence."""
    artifact_path, artifact = _prepare(tmp_path)
    _entry(artifact, "limit.scheduler.maximum_retry_attempts")["value"] = 3
    _write_json(artifact_path, artifact)
    with pytest.raises(
        CostAccountingValidationError, match="differs from retained control evidence"
    ):
        validate_cost_accounting(artifact_path=artifact_path, repo_root=tmp_path)


def test_rejects_non_positive_configured_limit(tmp_path: Path) -> None:
    """A configured safety limit cannot be zero or negative."""
    artifact_path, artifact = _prepare(tmp_path)
    _entry(artifact, "limit.scheduler.maximum_retry_attempts")["value"] = 0
    _write_json(artifact_path, artifact)
    with pytest.raises(CostAccountingValidationError, match="must be positive"):
        validate_cost_accounting(artifact_path=artifact_path, repo_root=tmp_path)


def test_rejects_configured_source_binding_drift(tmp_path: Path) -> None:
    """A configured limit cannot silently switch its authoritative source path."""
    artifact_path, artifact = _prepare(tmp_path)
    entry = _entry(artifact, "limit.scheduler.maximum_event_age")
    entry["control_evidence_value_path"] = "delivery_budget.maximum_retry_attempts"
    _write_json(artifact_path, artifact)
    with pytest.raises(CostAccountingValidationError, match="source binding drifted"):
        validate_cost_accounting(artifact_path=artifact_path, repo_root=tmp_path)


def test_rejects_configured_literal_binding_swap(tmp_path: Path) -> None:
    """An existing literal from the same file cannot replace the frozen source literal."""
    artifact_path, artifact = _prepare(tmp_path)
    entry = _entry(artifact, "limit.scheduler.maximum_event_age")
    entry["source_literal"] = "scheduled_ingestion_maximum_retry_attempts       = 2"
    _write_json(artifact_path, artifact)
    with pytest.raises(CostAccountingValidationError, match="source binding drifted"):
        validate_cost_accounting(artifact_path=artifact_path, repo_root=tmp_path)


def test_rejects_missing_frozen_entry(tmp_path: Path) -> None:
    """The first-slice cost envelope cannot silently drop an admitted boundary."""
    artifact_path, artifact = _prepare(tmp_path)
    entries = _entries(artifact)
    entries.pop()
    summary = cast(dict[str, object], artifact["summary"])
    summary["entries"] = 15
    summary["configured_limits"] = 6
    _write_json(artifact_path, artifact)
    with pytest.raises(
        CostAccountingValidationError, match="entries drifted from frozen first slice"
    ):
        validate_cost_accounting(artifact_path=artifact_path, repo_root=tmp_path)


def test_rejects_cross_component_aggregation_policy_drift(tmp_path: Path) -> None:
    """Gate 18.3 cannot authorize cross-component summation by presentation change."""
    artifact_path, artifact = _prepare(tmp_path)
    policy = cast(dict[str, object], artifact["aggregation_policy"])
    policy["cross_component_sum"] = "ALLOWED"
    _write_json(artifact_path, artifact)
    with pytest.raises(CostAccountingValidationError, match="aggregation_policy"):
        validate_cost_accounting(artifact_path=artifact_path, repo_root=tmp_path)


def test_rejects_production_tco_field(tmp_path: Path) -> None:
    """A bounded lab artifact cannot manufacture a production TCO."""
    artifact_path, artifact = _prepare(tmp_path)
    artifact["production_tco_usd"] = 0.0
    _write_json(artifact_path, artifact)
    with pytest.raises(CostAccountingValidationError, match="forbidden production/composite cost"):
        validate_cost_accounting(artifact_path=artifact_path, repo_root=tmp_path)
