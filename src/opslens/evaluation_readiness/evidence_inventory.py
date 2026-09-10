"""Deterministic validation for the Phase 18 cross-phase evidence inventory."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast


class EvidenceClassification(StrEnum):
    """Allowed evidence classifications for portfolio-facing metrics."""

    MEASURED = "MEASURED"
    DERIVED = "DERIVED"
    UNMEASURED = "UNMEASURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ComparisonRule(StrEnum):
    """Allowed comparability dispositions for a metric group."""

    DIRECT_SAME_SEMANTICS = "DIRECT_SAME_SEMANTICS"
    CONDITIONAL_SAME_WORKLOAD_FAMILY = "CONDITIONAL_SAME_WORKLOAD_FAMILY"
    WITHIN_WORKLOAD_ONLY = "WITHIN_WORKLOAD_ONLY"
    DESCRIPTIVE_ONLY = "DESCRIPTIVE_ONLY"


class EvidenceInventoryValidationError(ValueError):
    """Raised when the cross-phase evidence inventory violates a frozen invariant."""


@dataclass(frozen=True, slots=True)
class ValidationSummary:
    """Deterministic summary emitted after inventory validation succeeds."""

    record_count: int
    evidence_artifact_count: int
    comparability_group_count: int
    non_comparability_assertion_count: int


def _load_json(path: Path) -> object:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceInventoryValidationError(f"invalid JSON artifact: {path}: {exc}") from exc
    return cast(object, payload)


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise EvidenceInventoryValidationError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _list(value: object, *, label: str) -> list[object]:
    if not isinstance(value, list):
        raise EvidenceInventoryValidationError(f"{label} must be a JSON array")
    return cast(list[object], value)


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceInventoryValidationError(f"{label} must be a non-empty string")
    return value


def _optional_string(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    return _string(value, label=label)


def _resolve_object_path(root: object, path: str) -> object:
    current = root
    for segment in path.split("."):
        mapping = _object(current, label=f"source path parent for {path}")
        if segment not in mapping:
            raise EvidenceInventoryValidationError(
                f"source_metric_path {path!r} is missing segment {segment!r}"
            )
        current = mapping[segment]
    return current


def _validate_evidence_path(
    *, repo_root: Path, inventory_path: Path, evidence_path_text: str
) -> tuple[Path, object]:
    evidence_relative = Path(evidence_path_text)
    if evidence_relative.is_absolute() or ".." in evidence_relative.parts:
        raise EvidenceInventoryValidationError(
            f"evidence_path must be a repository-relative path: {evidence_path_text}"
        )
    if evidence_relative.suffix != ".json" or evidence_relative.parts[:2] != (
        "labs",
        "evidence",
    ):
        raise EvidenceInventoryValidationError(
            f"evidence_path must point to labs/evidence/*.json: {evidence_path_text}"
        )

    resolved_inventory = inventory_path.resolve()
    evidence_path = (repo_root / evidence_relative).resolve()
    if evidence_path == resolved_inventory:
        raise EvidenceInventoryValidationError(
            f"inventory records may not cite the inventory itself: {evidence_path_text}"
        )
    if not evidence_path.is_file():
        raise EvidenceInventoryValidationError(
            f"canonical evidence artifact does not exist: {evidence_path_text}"
        )
    return evidence_path, _load_json(evidence_path)


def _validate_classification(
    *,
    classification: EvidenceClassification,
    value: object,
    derivation: str | None,
    reason: str | None,
    metric_id: str,
) -> None:
    if classification is EvidenceClassification.MEASURED:
        if value is None:
            raise EvidenceInventoryValidationError(
                f"MEASURED record {metric_id} must have a non-null value"
            )
        if derivation is not None:
            raise EvidenceInventoryValidationError(
                f"MEASURED record {metric_id} must not declare derivation"
            )
        return

    if classification is EvidenceClassification.DERIVED:
        if value is None:
            raise EvidenceInventoryValidationError(
                f"DERIVED record {metric_id} must have a non-null value"
            )
        if derivation is None:
            raise EvidenceInventoryValidationError(
                f"DERIVED record {metric_id} must declare derivation"
            )
        return

    if classification is EvidenceClassification.UNMEASURED:
        if value is not None:
            raise EvidenceInventoryValidationError(
                f"UNMEASURED record {metric_id} must keep value=null; unmeasured != zero"
            )
        if reason is None:
            raise EvidenceInventoryValidationError(
                f"UNMEASURED record {metric_id} must declare why it is unmeasured"
            )
        return

    if value is not None:
        raise EvidenceInventoryValidationError(
            f"NOT_APPLICABLE record {metric_id} must keep value=null; N/A != zero"
        )
    if reason is None:
        raise EvidenceInventoryValidationError(
            f"NOT_APPLICABLE record {metric_id} must declare why it is not applicable"
        )


def validate_inventory(*, inventory_path: Path, repo_root: Path) -> ValidationSummary:
    """Validate the frozen Phase 18 evidence inventory against repository artifacts."""

    root = _object(_load_json(inventory_path), label="inventory root")
    artifact_version = _string(root.get("artifact_version"), label="artifact_version")
    if artifact_version != "phase-18-gate-18-1-evidence-inventory:v1":
        raise EvidenceInventoryValidationError(
            f"unexpected artifact_version: {artifact_version}"
        )

    declared_classifications = _list(
        root.get("allowed_classifications"), label="allowed_classifications"
    )
    declared_values = {
        _string(value, label="allowed_classifications[]") for value in declared_classifications
    }
    expected_values = {member.value for member in EvidenceClassification}
    if declared_values != expected_values:
        raise EvidenceInventoryValidationError(
            "allowed_classifications must match the frozen classification enum exactly"
        )

    matrix = _object(root.get("comparability_matrix"), label="comparability_matrix")
    groups_raw = _list(matrix.get("groups"), label="comparability_matrix.groups")
    groups: dict[str, dict[str, object]] = {}
    for index, group_value in enumerate(groups_raw):
        group = _object(group_value, label=f"comparability_matrix.groups[{index}]")
        group_id = _string(group.get("group_id"), label=f"groups[{index}].group_id")
        if group_id in groups:
            raise EvidenceInventoryValidationError(f"duplicate comparability group: {group_id}")
        rule_text = _string(group.get("comparison_rule"), label=f"{group_id}.comparison_rule")
        try:
            ComparisonRule(rule_text)
        except ValueError as exc:
            raise EvidenceInventoryValidationError(
                f"unknown comparison_rule for {group_id}: {rule_text}"
            ) from exc
        _string(group.get("semantics"), label=f"{group_id}.semantics")
        members = _list(group.get("members"), label=f"{group_id}.members")
        if not members:
            raise EvidenceInventoryValidationError(f"comparability group {group_id} has no members")
        groups[group_id] = group

    records_raw = _list(root.get("records"), label="records")
    if not records_raw:
        raise EvidenceInventoryValidationError("inventory must contain at least one metric record")

    record_ids: set[str] = set()
    record_group_membership: dict[str, str] = {}
    record_dimensions: dict[str, str] = {}
    record_units: dict[str, str] = {}
    evidence_artifacts: set[str] = set()

    for index, record_value in enumerate(records_raw):
        record = _object(record_value, label=f"records[{index}]")
        metric_id = _string(record.get("metric_id"), label=f"records[{index}].metric_id")
        if metric_id in record_ids:
            raise EvidenceInventoryValidationError(f"duplicate metric_id: {metric_id}")
        record_ids.add(metric_id)

        dimension = _string(record.get("dimension"), label=f"{metric_id}.dimension")
        _string(record.get("workload_id"), label=f"{metric_id}.workload_id")
        _string(record.get("scope"), label=f"{metric_id}.scope")
        unit = _string(record.get("unit"), label=f"{metric_id}.unit")
        record_dimensions[metric_id] = dimension
        record_units[metric_id] = unit

        phase = record.get("phase")
        if not isinstance(phase, int) or isinstance(phase, bool) or phase < 0:
            raise EvidenceInventoryValidationError(f"{metric_id}.phase must be a non-negative int")

        classification_text = _string(
            record.get("classification"), label=f"{metric_id}.classification"
        )
        try:
            classification = EvidenceClassification(classification_text)
        except ValueError as exc:
            raise EvidenceInventoryValidationError(
                f"unknown evidence classification for {metric_id}: {classification_text}"
            ) from exc

        derivation = _optional_string(record.get("derivation"), label=f"{metric_id}.derivation")
        reason = _optional_string(record.get("reason"), label=f"{metric_id}.reason")
        value = record.get("value")
        _validate_classification(
            classification=classification,
            value=value,
            derivation=derivation,
            reason=reason,
            metric_id=metric_id,
        )

        group_id = _string(
            record.get("comparability_group"), label=f"{metric_id}.comparability_group"
        )
        if group_id not in groups:
            raise EvidenceInventoryValidationError(
                f"record {metric_id} references unknown comparability group {group_id}"
            )
        record_group_membership[metric_id] = group_id

        evidence_path_text = _string(
            record.get("evidence_path"), label=f"{metric_id}.evidence_path"
        )
        _, evidence_root = _validate_evidence_path(
            repo_root=repo_root,
            inventory_path=inventory_path,
            evidence_path_text=evidence_path_text,
        )
        evidence_artifacts.add(evidence_path_text)

        source_metric_path = _optional_string(
            record.get("source_metric_path"), label=f"{metric_id}.source_metric_path"
        )
        if classification is EvidenceClassification.MEASURED and source_metric_path is None:
            raise EvidenceInventoryValidationError(
                f"MEASURED record {metric_id} must point to a source_metric_path"
            )
        if source_metric_path is not None:
            observed_source_value = _resolve_object_path(evidence_root, source_metric_path)
            if observed_source_value != value:
                raise EvidenceInventoryValidationError(
                    f"source value mismatch for {metric_id}: "
                    f"inventory={value!r} source={observed_source_value!r}"
                )

    declared_members: set[str] = set()
    for group_id, group in groups.items():
        members = _list(group["members"], label=f"{group_id}.members")
        for member_value in members:
            member = _string(member_value, label=f"{group_id}.members[]")
            if member in declared_members:
                raise EvidenceInventoryValidationError(
                    f"metric {member} appears in more than one comparability group"
                )
            if member not in record_ids:
                raise EvidenceInventoryValidationError(
                    f"comparability group {group_id} references unknown metric {member}"
                )
            if record_group_membership[member] != group_id:
                raise EvidenceInventoryValidationError(
                    f"metric {member} group mismatch: record={record_group_membership[member]} "
                    f"matrix={group_id}"
                )
            declared_members.add(member)

    if declared_members != record_ids:
        missing = sorted(record_ids - declared_members)
        raise EvidenceInventoryValidationError(
            f"every metric must appear in exactly one comparability group; missing={missing}"
        )

    for group_id, group in groups.items():
        rule = ComparisonRule(
            _string(group["comparison_rule"], label=f"{group_id}.comparison_rule")
        )
        members = [
            _string(value, label=f"{group_id}.members[]")
            for value in _list(group["members"], label=f"{group_id}.members")
        ]
        if rule is ComparisonRule.DESCRIPTIVE_ONLY:
            continue
        if len(members) < 2:
            raise EvidenceInventoryValidationError(
                f"comparable group {group_id} must contain at least two metrics"
            )
        dimensions = {record_dimensions[member] for member in members}
        units = {record_units[member] for member in members}
        if len(dimensions) != 1 or len(units) != 1:
            raise EvidenceInventoryValidationError(
                f"comparable group {group_id} must preserve one dimension and unit; "
                f"dimensions={sorted(dimensions)} units={sorted(units)}"
            )

    assertions_raw = _list(
        matrix.get("non_comparable_pairs"), label="comparability_matrix.non_comparable_pairs"
    )
    seen_pairs: set[tuple[str, str]] = set()
    for index, assertion_value in enumerate(assertions_raw):
        assertion = _object(
            assertion_value, label=f"comparability_matrix.non_comparable_pairs[{index}]"
        )
        left = _string(assertion.get("left_group"), label=f"non_comparable_pairs[{index}].left")
        right = _string(
            assertion.get("right_group"), label=f"non_comparable_pairs[{index}].right"
        )
        _string(assertion.get("reason"), label=f"non_comparable_pairs[{index}].reason")
        if left not in groups or right not in groups:
            raise EvidenceInventoryValidationError(
                f"non-comparability assertion references unknown group: {left}, {right}"
            )
        if left == right:
            raise EvidenceInventoryValidationError(
                f"non-comparability assertion may not compare a group to itself: {left}"
            )
        pair = (left, right) if left < right else (right, left)
        if pair in seen_pairs:
            raise EvidenceInventoryValidationError(
                f"duplicate non-comparability assertion: {pair[0]}, {pair[1]}"
            )
        seen_pairs.add(pair)

    return ValidationSummary(
        record_count=len(record_ids),
        evidence_artifact_count=len(evidence_artifacts),
        comparability_group_count=len(groups),
        non_comparability_assertion_count=len(seen_pairs),
    )
