"""Unit tests for the Phase 18 consolidated evaluation view validator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from opslens.evaluation_readiness import (
    ConsolidatedViewValidationError,
    validate_consolidated_view,
)

_SECTION_IDS = (
    "groundedness_and_quality",
    "latency_surfaces",
    "token_and_cost",
    "execution_authority",
    "runtime_security_and_recovery",
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _record(
    metric_id: str,
    *,
    dimension: str,
    classification: str,
    value: object,
    unit: str,
    group: str,
    source_path: str | None,
    derivation: str | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "metric_id": metric_id,
        "phase": 1,
        "dimension": dimension,
        "workload_id": "fixture:v1",
        "classification": classification,
        "value": value,
        "unit": unit,
        "evidence_path": "labs/evidence/source-v1.json",
        "source_metric_path": source_path,
        "comparability_group": group,
        "scope": f"Frozen fixture scope for {metric_id}.",
    }
    if derivation is not None:
        record["derivation"] = derivation
    if reason is not None:
        record["reason"] = reason
    return record


def _inventory() -> dict[str, object]:
    records = [
        _record(
            "metric.quality",
            dimension="quality",
            classification="MEASURED",
            value=1.0,
            unit="ratio",
            group="quality",
            source_path="metrics.quality",
        ),
        _record(
            "metric.latency",
            dimension="latency",
            classification="MEASURED",
            value=10,
            unit="milliseconds",
            group="latency",
            source_path="metrics.latency",
        ),
        _record(
            "metric.cost",
            dimension="cost",
            classification="UNMEASURED",
            value=None,
            unit="usd",
            group="cost",
            source_path=None,
            reason="Complete cost was not measured.",
        ),
        _record(
            "metric.execution",
            dimension="execution_authority",
            classification="MEASURED",
            value=0,
            unit="executions",
            group="execution",
            source_path="metrics.executions",
        ),
        _record(
            "metric.runtime",
            dimension="runtime_evidence",
            classification="NOT_APPLICABLE",
            value=None,
            unit="records",
            group="runtime",
            source_path=None,
            reason="The offline fixture has no runtime-evidence surface.",
        ),
    ]
    groups = [
        {
            "group_id": group,
            "comparison_rule": "DESCRIPTIVE_ONLY",
            "semantics": f"Descriptive fixture semantics for {group}.",
            "members": [metric_id],
        }
        for group, metric_id in (
            ("quality", "metric.quality"),
            ("latency", "metric.latency"),
            ("cost", "metric.cost"),
            ("execution", "metric.execution"),
            ("runtime", "metric.runtime"),
        )
    ]
    return {
        "artifact_version": "phase-18-gate-18-1-evidence-inventory:v1",
        "allowed_classifications": [
            "MEASURED",
            "DERIVED",
            "UNMEASURED",
            "NOT_APPLICABLE",
        ],
        "comparability_matrix": {
            "groups": groups,
            "non_comparable_pairs": [
                {
                    "left_group": "quality",
                    "right_group": "cost",
                    "reason": "Quality and missing cost are not comparable.",
                }
            ],
        },
        "records": records,
    }


def _signals() -> dict[str, object]:
    return {
        "artifact_version": "phase-18-gate-18-2-decision-signals:v1",
        "signals": [
            {
                "signal_id": "fixture-failure",
                "kind": "FAILURE_SIGNAL",
                "statement": "A frozen fixture failure remains visible.",
                "interpretation": "One failure signal is not a universal failure rate.",
                "evidence_path": "labs/evidence/source-v1.json",
                "supporting_document": "labs/source.md",
                "source_assertions": [
                    {"path": "signals.0.failed", "expected": True},
                ],
            }
        ],
    }


def _projected_metric(
    record: dict[str, object], groups: dict[str, dict[str, object]]
) -> dict[str, object]:
    projection = dict(record)
    group_id = cast(str, record["comparability_group"])
    group = groups[group_id]
    projection["comparison_rule"] = group["comparison_rule"]
    projection["comparison_semantics"] = group["semantics"]
    return projection


def _view(inventory: dict[str, object], signals: dict[str, object]) -> dict[str, object]:
    matrix = cast(dict[str, object], inventory["comparability_matrix"])
    group_values = cast(list[dict[str, object]], matrix["groups"])
    groups = {cast(str, group["group_id"]): group for group in group_values}
    records = cast(list[dict[str, object]], inventory["records"])
    by_id = {cast(str, record["metric_id"]): record for record in records}
    section_metrics = (
        "metric.quality",
        "metric.latency",
        "metric.cost",
        "metric.execution",
        "metric.runtime",
    )
    sections = [
        {
            "section_id": section_id,
            "description": f"Frozen {section_id} fixture section.",
            "metrics": [_projected_metric(by_id[metric_id], groups)],
        }
        for section_id, metric_id in zip(_SECTION_IDS, section_metrics, strict=True)
    ]
    signal_values = cast(list[dict[str, object]], signals["signals"])
    projected_signal = {
        key: signal_values[0][key]
        for key in (
            "signal_id",
            "kind",
            "statement",
            "interpretation",
            "evidence_path",
            "supporting_document",
        )
    }
    return {
        "artifact_version": "phase-18-gate-18-2-consolidated-view:v1",
        "source_inventory": "labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json",
        "decision_signal_manifest": "labs/evidence/phase-18-gate-18-2-decision-signals-v1.json",
        "summary": {
            "sections": 5,
            "metrics": 5,
            "decision_signals": 1,
            "unmeasured": 1,
            "not_applicable": 1,
            "non_comparable_pairs": 1,
        },
        "sections": sections,
        "decision_signals": [projected_signal],
        "non_comparable_pairs": matrix["non_comparable_pairs"],
    }


def _prepare(
    tmp_path: Path,
) -> tuple[Path, Path, Path, dict[str, object], dict[str, object], dict[str, object]]:
    source_path = tmp_path / "labs/evidence/source-v1.json"
    _write_json(
        source_path,
        {
            "metrics": {"quality": 1.0, "latency": 10, "executions": 0},
            "signals": [{"failed": True}],
        },
    )
    supporting_path = tmp_path / "labs/source.md"
    supporting_path.parent.mkdir(parents=True, exist_ok=True)
    supporting_path.write_text("# Frozen fixture support\n", encoding="utf-8")

    inventory = _inventory()
    signals = _signals()
    view = _view(inventory, signals)
    inventory_path = tmp_path / "labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json"
    signal_path = tmp_path / "labs/evidence/phase-18-gate-18-2-decision-signals-v1.json"
    view_path = tmp_path / "labs/evidence/phase-18-gate-18-2-consolidated-view-v1.json"
    _write_json(inventory_path, inventory)
    _write_json(signal_path, signals)
    _write_json(view_path, view)
    return inventory_path, signal_path, view_path, inventory, signals, view


def _validate(tmp_path: Path, inventory_path: Path, signal_path: Path, view_path: Path) -> None:
    validate_consolidated_view(
        inventory_path=inventory_path,
        signal_path=signal_path,
        view_path=view_path,
        repo_root=tmp_path,
    )


def _sections(view: dict[str, object]) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], view["sections"])


def _metrics(section: dict[str, object]) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], section["metrics"])


def test_validate_consolidated_view_accepts_frozen_projection(tmp_path: Path) -> None:
    """A valid view preserves every metric, signal and null disposition."""
    inventory_path, signal_path, view_path, _, _, _ = _prepare(tmp_path)
    summary = validate_consolidated_view(
        inventory_path=inventory_path,
        signal_path=signal_path,
        view_path=view_path,
        repo_root=tmp_path,
    )
    assert summary.section_count == 5
    assert summary.metric_count == 5
    assert summary.decision_signal_count == 1
    assert summary.unmeasured_count == 1
    assert summary.not_applicable_count == 1
    assert summary.non_comparability_assertion_count == 1


def test_rejects_unknown_metric(tmp_path: Path) -> None:
    """A view may not invent a metric outside the Gate 18.1 inventory."""
    inventory_path, signal_path, view_path, _, _, view = _prepare(tmp_path)
    _metrics(_sections(view)[0])[0]["metric_id"] = "metric.unknown"
    _write_json(view_path, view)
    with pytest.raises(ConsolidatedViewValidationError, match="unknown Gate 18.1 metric"):
        _validate(tmp_path, inventory_path, signal_path, view_path)


def test_rejects_duplicate_metric(tmp_path: Path) -> None:
    """A metric may appear in exactly one consolidated-view section."""
    inventory_path, signal_path, view_path, _, _, view = _prepare(tmp_path)
    duplicate = dict(_metrics(_sections(view)[0])[0])
    _metrics(_sections(view)[1]).append(duplicate)
    _write_json(view_path, view)
    with pytest.raises(ConsolidatedViewValidationError, match="appears more than once"):
        _validate(tmp_path, inventory_path, signal_path, view_path)


def test_rejects_missing_metric(tmp_path: Path) -> None:
    """Dropping admitted evidence from the view fails closed."""
    inventory_path, signal_path, view_path, _, _, view = _prepare(tmp_path)
    _metrics(_sections(view)[4]).clear()
    _write_json(view_path, view)
    with pytest.raises(ConsolidatedViewValidationError, match="must not be empty"):
        _validate(tmp_path, inventory_path, signal_path, view_path)


def test_rejects_metric_value_drift(tmp_path: Path) -> None:
    """Presentation cannot rewrite a canonical metric value."""
    inventory_path, signal_path, view_path, _, _, view = _prepare(tmp_path)
    _metrics(_sections(view)[0])[0]["value"] = 0.9
    _write_json(view_path, view)
    with pytest.raises(ConsolidatedViewValidationError, match="drifted from canonical source"):
        _validate(tmp_path, inventory_path, signal_path, view_path)


def test_rejects_comparison_rule_drift(tmp_path: Path) -> None:
    """The view cannot widen descriptive evidence into direct comparison."""
    inventory_path, signal_path, view_path, _, _, view = _prepare(tmp_path)
    _metrics(_sections(view)[0])[0]["comparison_rule"] = "DIRECT_SAME_SEMANTICS"
    _write_json(view_path, view)
    with pytest.raises(ConsolidatedViewValidationError, match="comparison_rule drifted"):
        _validate(tmp_path, inventory_path, signal_path, view_path)


def test_rejects_decision_signal_assertion_mismatch(tmp_path: Path) -> None:
    """Decision signals must resolve to exact canonical source assertions."""
    inventory_path, signal_path, view_path, _, signals, _ = _prepare(tmp_path)
    signal_values = cast(list[dict[str, object]], signals["signals"])
    assertions = cast(list[dict[str, object]], signal_values[0]["source_assertions"])
    assertions[0]["expected"] = False
    _write_json(signal_path, signals)
    with pytest.raises(ConsolidatedViewValidationError, match="assertion mismatch"):
        _validate(tmp_path, inventory_path, signal_path, view_path)


def test_rejects_unsafe_decision_evidence_path(tmp_path: Path) -> None:
    """Decision evidence must remain inside the repository evidence tree."""
    inventory_path, signal_path, view_path, _, signals, _ = _prepare(tmp_path)
    signal_values = cast(list[dict[str, object]], signals["signals"])
    signal_values[0]["evidence_path"] = "../outside.json"
    _write_json(signal_path, signals)
    with pytest.raises(ConsolidatedViewValidationError, match="labs/evidence"):
        _validate(tmp_path, inventory_path, signal_path, view_path)


def test_rejects_missing_projected_decision_signal(tmp_path: Path) -> None:
    """Negative/rejected evidence cannot disappear from the presentation layer."""
    inventory_path, signal_path, view_path, _, _, view = _prepare(tmp_path)
    view["decision_signals"] = []
    view_summary = cast(dict[str, object], view["summary"])
    view_summary["decision_signals"] = 0
    _write_json(view_path, view)
    with pytest.raises(ConsolidatedViewValidationError, match="preserve every decision signal"):
        _validate(tmp_path, inventory_path, signal_path, view_path)


def test_rejects_non_comparability_drift(tmp_path: Path) -> None:
    """Gate 18.1 non-comparability assertions are immutable view inputs."""
    inventory_path, signal_path, view_path, _, _, view = _prepare(tmp_path)
    pairs = cast(list[dict[str, object]], view["non_comparable_pairs"])
    pairs[0]["reason"] = "Rewritten presentation reason."
    _write_json(view_path, view)
    with pytest.raises(ConsolidatedViewValidationError, match="exactly match Gate 18.1"):
        _validate(tmp_path, inventory_path, signal_path, view_path)


def test_rejects_composite_or_ranking_field(tmp_path: Path) -> None:
    """Gate 18.2 refuses synthetic composite scores and rankings."""
    inventory_path, signal_path, view_path, _, _, view = _prepare(tmp_path)
    view["readiness_score"] = 1.0
    _write_json(view_path, view)
    with pytest.raises(ConsolidatedViewValidationError, match="forbidden composite/ranking field"):
        _validate(tmp_path, inventory_path, signal_path, view_path)
