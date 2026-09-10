"""Unit tests for the Phase 18 evidence-inventory validator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from opslens.evaluation_readiness import (
    EvidenceInventoryValidationError,
    validate_inventory,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _valid_inventory() -> dict[str, object]:
    return {
        "artifact_version": "phase-18-gate-18-1-evidence-inventory:v1",
        "allowed_classifications": [
            "MEASURED",
            "DERIVED",
            "UNMEASURED",
            "NOT_APPLICABLE",
        ],
        "comparability_matrix": {
            "groups": [
                {
                    "group_id": "quality",
                    "comparison_rule": "DIRECT_SAME_SEMANTICS",
                    "semantics": "Same frozen quality field.",
                    "members": ["metric.measured", "metric.derived"],
                },
                {
                    "group_id": "cost",
                    "comparison_rule": "DESCRIPTIVE_ONLY",
                    "semantics": "Missing or inapplicable cost stays explicit.",
                    "members": ["metric.unmeasured", "metric.na"],
                },
            ],
            "non_comparable_pairs": [
                {
                    "left_group": "quality",
                    "right_group": "cost",
                    "reason": "Quality and cost are independent dimensions.",
                }
            ],
        },
        "records": [
            {
                "metric_id": "metric.measured",
                "phase": 1,
                "dimension": "quality",
                "workload_id": "fixture:v1",
                "classification": "MEASURED",
                "value": 1.0,
                "unit": "ratio",
                "evidence_path": "labs/evidence/source-v1.json",
                "source_metric_path": "metrics.quality",
                "comparability_group": "quality",
                "scope": "Frozen fixture scope.",
            },
            {
                "metric_id": "metric.derived",
                "phase": 1,
                "dimension": "quality",
                "workload_id": "fixture:v1",
                "classification": "DERIVED",
                "value": 0.5,
                "unit": "ratio",
                "evidence_path": "labs/evidence/source-v1.json",
                "source_metric_path": None,
                "comparability_group": "quality",
                "scope": "Frozen fixture scope.",
                "derivation": "One supported case divided by two cases.",
            },
            {
                "metric_id": "metric.unmeasured",
                "phase": 1,
                "dimension": "cost",
                "workload_id": "fixture:v1",
                "classification": "UNMEASURED",
                "value": None,
                "unit": "usd",
                "evidence_path": "labs/evidence/source-v1.json",
                "source_metric_path": None,
                "comparability_group": "cost",
                "scope": "No complete cost observation.",
                "reason": "The canonical artifact has no complete USD cost field.",
            },
            {
                "metric_id": "metric.na",
                "phase": 1,
                "dimension": "cost",
                "workload_id": "offline-fixture:v1",
                "classification": "NOT_APPLICABLE",
                "value": None,
                "unit": "usd",
                "evidence_path": "labs/evidence/source-v1.json",
                "source_metric_path": None,
                "comparability_group": "cost",
                "scope": "Offline-only fixture.",
                "reason": "No cloud runtime exists for this fixture.",
            },
        ],
    }


def _prepare(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    evidence_path = tmp_path / "labs/evidence/source-v1.json"
    _write_json(evidence_path, {"metrics": {"quality": 1.0}})
    inventory = _valid_inventory()
    inventory_path = tmp_path / "labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json"
    _write_json(inventory_path, inventory)
    return inventory_path, evidence_path, inventory


def _records(inventory: dict[str, object]) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], inventory["records"])


def test_validate_inventory_accepts_explicit_evidence_semantics(tmp_path: Path) -> None:
    """The frozen valid shape resolves evidence and preserves null semantics."""
    inventory_path, _, _ = _prepare(tmp_path)

    summary = validate_inventory(inventory_path=inventory_path, repo_root=tmp_path)

    assert summary.record_count == 4
    assert summary.evidence_artifact_count == 1
    assert summary.comparability_group_count == 2
    assert summary.non_comparability_assertion_count == 1


def test_validate_inventory_rejects_unknown_classification(tmp_path: Path) -> None:
    """Classification vocabulary is frozen and fails closed on unknown values."""
    inventory_path, _, inventory = _prepare(tmp_path)
    _records(inventory)[0]["classification"] = "ESTIMATED"
    _write_json(inventory_path, inventory)

    with pytest.raises(EvidenceInventoryValidationError, match="unknown evidence classification"):
        validate_inventory(inventory_path=inventory_path, repo_root=tmp_path)


def test_validate_inventory_rejects_unmeasured_zero(tmp_path: Path) -> None:
    """An unmeasured value may not be normalized to numeric zero."""
    inventory_path, _, inventory = _prepare(tmp_path)
    _records(inventory)[2]["value"] = 0.0
    _write_json(inventory_path, inventory)

    with pytest.raises(EvidenceInventoryValidationError, match="unmeasured != zero"):
        validate_inventory(inventory_path=inventory_path, repo_root=tmp_path)


def test_validate_inventory_rejects_not_applicable_zero(tmp_path: Path) -> None:
    """A not-applicable value may not be normalized to numeric zero."""
    inventory_path, _, inventory = _prepare(tmp_path)
    _records(inventory)[3]["value"] = 0.0
    _write_json(inventory_path, inventory)

    with pytest.raises(EvidenceInventoryValidationError, match="N/A != zero"):
        validate_inventory(inventory_path=inventory_path, repo_root=tmp_path)


def test_validate_inventory_rejects_missing_canonical_artifact(tmp_path: Path) -> None:
    """Every record must resolve to a repository evidence artifact."""
    inventory_path, evidence_path, _ = _prepare(tmp_path)
    evidence_path.unlink()

    with pytest.raises(EvidenceInventoryValidationError, match="does not exist"):
        validate_inventory(inventory_path=inventory_path, repo_root=tmp_path)


def test_validate_inventory_rejects_measured_source_value_mismatch(tmp_path: Path) -> None:
    """Measured values must equal the field addressed in their canonical artifact."""
    inventory_path, _, inventory = _prepare(tmp_path)
    _records(inventory)[0]["value"] = 0.75
    _write_json(inventory_path, inventory)

    with pytest.raises(EvidenceInventoryValidationError, match="source value mismatch"):
        validate_inventory(inventory_path=inventory_path, repo_root=tmp_path)


def test_validate_inventory_rejects_unknown_comparability_group(tmp_path: Path) -> None:
    """Records cannot self-declare an unregistered comparison group."""
    inventory_path, _, inventory = _prepare(tmp_path)
    _records(inventory)[0]["comparability_group"] = "unknown"
    _write_json(inventory_path, inventory)

    with pytest.raises(EvidenceInventoryValidationError, match="unknown comparability group"):
        validate_inventory(inventory_path=inventory_path, repo_root=tmp_path)


def test_validate_inventory_rejects_duplicate_metric_membership(tmp_path: Path) -> None:
    """A metric belongs to exactly one comparison group."""
    inventory_path, _, inventory = _prepare(tmp_path)
    matrix = cast(dict[str, object], inventory["comparability_matrix"])
    groups = cast(list[dict[str, object]], matrix["groups"])
    members = cast(list[str], groups[1]["members"])
    members.append("metric.measured")
    _write_json(inventory_path, inventory)

    with pytest.raises(EvidenceInventoryValidationError, match="more than one comparability group"):
        validate_inventory(inventory_path=inventory_path, repo_root=tmp_path)


def test_validate_inventory_rejects_cross_semantic_comparable_group(tmp_path: Path) -> None:
    """Comparable groups cannot mix dimensions or units merely because values are numeric."""
    inventory_path, _, inventory = _prepare(tmp_path)
    records = _records(inventory)
    records[1]["dimension"] = "latency"
    records[1]["unit"] = "milliseconds"
    _write_json(inventory_path, inventory)

    with pytest.raises(EvidenceInventoryValidationError, match="preserve one dimension and unit"):
        validate_inventory(inventory_path=inventory_path, repo_root=tmp_path)
