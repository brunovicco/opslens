"""Deterministic projection and validation for the Phase 18 consolidated view."""

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast

from opslens.evaluation_readiness.evidence_inventory import validate_inventory

_INVENTORY_ARTIFACT_VERSION = "phase-18-gate-18-1-evidence-inventory:v1"
_SIGNAL_ARTIFACT_VERSION = "phase-18-gate-18-2-decision-signals:v1"
_VIEW_ARTIFACT_VERSION = "phase-18-gate-18-2-consolidated-view:v1"
_EXPECTED_INVENTORY_PATH = Path(
    "labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json"
)
_EXPECTED_SECTION_IDS = {
    "groundedness_and_quality",
    "latency_surfaces",
    "token_and_cost",
    "execution_authority",
    "runtime_security_and_recovery",
}
_FORBIDDEN_PRESENTATION_KEYS = {
    "score",
    "rank",
    "ranking",
    "readiness_score",
    "overall_score",
    "composite_score",
}
_PROJECTED_METRIC_FIELDS = (
    "metric_id",
    "phase",
    "dimension",
    "workload_id",
    "classification",
    "value",
    "unit",
    "evidence_path",
    "source_metric_path",
    "comparability_group",
    "scope",
    "derivation",
    "reason",
)
_PROJECTED_SIGNAL_FIELDS = (
    "signal_id",
    "kind",
    "statement",
    "interpretation",
    "evidence_path",
    "supporting_document",
)


class DecisionSignalKind(StrEnum):
    """Allowed dispositions for retained negative or limiting evidence."""

    FAILURE_SIGNAL = "FAILURE_SIGNAL"
    REJECTED_DEFAULT = "REJECTED_DEFAULT"
    ZERO_OBSERVATION = "ZERO_OBSERVATION"
    LIMITATION = "LIMITATION"


class ConsolidatedViewValidationError(ValueError):
    """Raised when the Phase 18 consolidated view violates a frozen invariant."""


@dataclass(frozen=True, slots=True)
class ConsolidatedViewSummary:
    """Deterministic validation summary for the retained consolidated view."""

    section_count: int
    metric_count: int
    decision_signal_count: int
    unmeasured_count: int
    not_applicable_count: int
    non_comparability_assertion_count: int


def _load_json(path: Path) -> object:
    try:
        return cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConsolidatedViewValidationError(f"invalid JSON artifact: {path}: {exc}") from exc


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ConsolidatedViewValidationError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _list(value: object, *, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ConsolidatedViewValidationError(f"{label} must be a JSON array")
    return cast(list[object], value)


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConsolidatedViewValidationError(f"{label} must be a non-empty string")
    return value


def _safe_repo_path(
    *, repo_root: Path, path_text: str, label: str, allowed_suffixes: tuple[str, ...]
) -> Path:
    relative = Path(path_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise ConsolidatedViewValidationError(f"{label} must be repository-relative: {path_text}")
    if relative.suffix not in allowed_suffixes:
        raise ConsolidatedViewValidationError(
            f"{label} must use one of {allowed_suffixes}: {path_text}"
        )
    resolved = (repo_root / relative).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ConsolidatedViewValidationError(
            f"{label} escapes repository root: {path_text}"
        ) from exc
    if not resolved.is_file():
        raise ConsolidatedViewValidationError(f"{label} does not exist: {path_text}")
    return resolved


def _resolve_object_path(root: object, path: str) -> object:
    current = root
    for segment in path.split("."):
        if isinstance(current, dict):
            mapping = cast(dict[str, object], current)
            if segment not in mapping:
                raise ConsolidatedViewValidationError(
                    f"source assertion path {path!r} is missing segment {segment!r}"
                )
            current = mapping[segment]
            continue
        if isinstance(current, list):
            sequence = cast(list[object], current)
            try:
                index = int(segment)
            except ValueError as exc:
                raise ConsolidatedViewValidationError(
                    f"source assertion path {path!r} requires a numeric list index at {segment!r}"
                ) from exc
            if index < 0 or index >= len(sequence):
                raise ConsolidatedViewValidationError(
                    f"source assertion path {path!r} list index out of range: {index}"
                )
            current = sequence[index]
            continue
        raise ConsolidatedViewValidationError(
            f"source assertion path {path!r} traverses a scalar before {segment!r}"
        )
    return current


def _reject_forbidden_presentation_keys(value: object, *, path: str = "view") -> None:
    if isinstance(value, dict):
        mapping = cast(dict[str, object], value)
        for key, child in mapping.items():
            if key in _FORBIDDEN_PRESENTATION_KEYS:
                raise ConsolidatedViewValidationError(
                    f"forbidden composite/ranking field {key!r} at {path}"
                )
            _reject_forbidden_presentation_keys(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(cast(list[object], value)):
            _reject_forbidden_presentation_keys(child, path=f"{path}[{index}]")


def _load_inventory(
    *, inventory_path: Path, repo_root: Path
) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]], list[dict[str, object]]]:
    validate_inventory(inventory_path=inventory_path, repo_root=repo_root)
    root = _object(_load_json(inventory_path), label="inventory root")
    if _string(root.get("artifact_version"), label="inventory artifact_version") != (
        _INVENTORY_ARTIFACT_VERSION
    ):
        raise ConsolidatedViewValidationError("unexpected Gate 18.1 inventory artifact version")

    records: dict[str, dict[str, object]] = {}
    for index, value in enumerate(_list(root.get("records"), label="inventory records")):
        record = _object(value, label=f"inventory records[{index}]")
        metric_id = _string(record.get("metric_id"), label=f"inventory records[{index}].metric_id")
        records[metric_id] = record

    matrix = _object(root.get("comparability_matrix"), label="inventory comparability_matrix")
    groups: dict[str, dict[str, object]] = {}
    for index, value in enumerate(_list(matrix.get("groups"), label="inventory groups")):
        group = _object(value, label=f"inventory groups[{index}]")
        group_id = _string(group.get("group_id"), label=f"inventory groups[{index}].group_id")
        groups[group_id] = group

    assertions = [
        _object(value, label=f"inventory non_comparable_pairs[{index}]")
        for index, value in enumerate(
            _list(matrix.get("non_comparable_pairs"), label="inventory non_comparable_pairs")
        )
    ]
    return records, groups, assertions


def _validate_decision_signals(
    *, signal_path: Path, repo_root: Path
) -> dict[str, dict[str, object]]:
    root = _object(_load_json(signal_path), label="decision signal root")
    if _string(root.get("artifact_version"), label="decision signal artifact_version") != (
        _SIGNAL_ARTIFACT_VERSION
    ):
        raise ConsolidatedViewValidationError("unexpected decision signal artifact version")

    signals: dict[str, dict[str, object]] = {}
    for index, value in enumerate(_list(root.get("signals"), label="decision signals")):
        signal = _object(value, label=f"decision signals[{index}]")
        signal_id = _string(signal.get("signal_id"), label=f"decision signals[{index}].signal_id")
        if signal_id in signals:
            raise ConsolidatedViewValidationError(f"duplicate decision signal: {signal_id}")
        kind_text = _string(signal.get("kind"), label=f"{signal_id}.kind")
        try:
            DecisionSignalKind(kind_text)
        except ValueError as exc:
            raise ConsolidatedViewValidationError(
                f"unknown decision signal kind for {signal_id}: {kind_text}"
            ) from exc
        _string(signal.get("statement"), label=f"{signal_id}.statement")
        _string(signal.get("interpretation"), label=f"{signal_id}.interpretation")

        evidence_text = _string(signal.get("evidence_path"), label=f"{signal_id}.evidence_path")
        if not evidence_text.startswith("labs/evidence/"):
            raise ConsolidatedViewValidationError(
                f"{signal_id}.evidence_path must point to labs/evidence/*.json"
            )
        evidence_path = _safe_repo_path(
            repo_root=repo_root,
            path_text=evidence_text,
            label=f"{signal_id}.evidence_path",
            allowed_suffixes=(".json",),
        )
        evidence_root = _load_json(evidence_path)

        supporting_text = _string(
            signal.get("supporting_document"), label=f"{signal_id}.supporting_document"
        )
        _safe_repo_path(
            repo_root=repo_root,
            path_text=supporting_text,
            label=f"{signal_id}.supporting_document",
            allowed_suffixes=(".md",),
        )

        assertions = _list(signal.get("source_assertions"), label=f"{signal_id}.source_assertions")
        if not assertions:
            raise ConsolidatedViewValidationError(
                f"decision signal {signal_id} must have at least one source assertion"
            )
        seen_paths: set[str] = set()
        for assertion_index, assertion_value in enumerate(assertions):
            assertion = _object(
                assertion_value,
                label=f"{signal_id}.source_assertions[{assertion_index}]",
            )
            source_path = _string(
                assertion.get("path"),
                label=f"{signal_id}.source_assertions[{assertion_index}].path",
            )
            if source_path in seen_paths:
                raise ConsolidatedViewValidationError(
                    f"duplicate source assertion path for {signal_id}: {source_path}"
                )
            seen_paths.add(source_path)
            observed = _resolve_object_path(evidence_root, source_path)
            expected = assertion.get("expected")
            if observed != expected:
                raise ConsolidatedViewValidationError(
                    f"decision signal assertion mismatch for {signal_id} at {source_path}: "
                    f"expected={expected!r} observed={observed!r}"
                )
        signals[signal_id] = signal
    if not signals:
        raise ConsolidatedViewValidationError("decision signal manifest must not be empty")
    return signals


def _assert_projection_equal(
    *, projected: dict[str, object], source: dict[str, object], fields: tuple[str, ...], label: str
) -> None:
    for field in fields:
        projected_value = projected.get(field)
        source_value = source.get(field)
        if projected_value != source_value:
            raise ConsolidatedViewValidationError(
                f"{label}.{field} drifted from canonical source: "
                f"view={projected_value!r} source={source_value!r}"
            )


def _assert_non_comparability_equal(
    *, view_assertions: list[object], source_assertions: list[dict[str, object]]
) -> None:
    def normalized(values: list[object], *, label: str) -> set[tuple[str, str, str]]:
        output: set[tuple[str, str, str]] = set()
        for index, value in enumerate(values):
            assertion = _object(value, label=f"{label}[{index}]")
            left = _string(assertion.get("left_group"), label=f"{label}[{index}].left_group")
            right = _string(assertion.get("right_group"), label=f"{label}[{index}].right_group")
            reason = _string(assertion.get("reason"), label=f"{label}[{index}].reason")
            pair = (left, right, reason) if left < right else (right, left, reason)
            if pair in output:
                raise ConsolidatedViewValidationError(
                    f"duplicate non-comparability assertion in {label}: {left}, {right}"
                )
            output.add(pair)
        return output

    view_set = normalized(view_assertions, label="view non_comparable_pairs")
    source_set = normalized(
        cast(list[object], source_assertions), label="inventory non_comparable_pairs"
    )
    if view_set != source_set:
        raise ConsolidatedViewValidationError(
            "consolidated view non-comparability assertions must exactly match Gate 18.1"
        )


def validate_consolidated_view(
    *, inventory_path: Path, signal_path: Path, view_path: Path, repo_root: Path
) -> ConsolidatedViewSummary:
    """Validate the Gate 18.2 consolidated view without creating new evidence authority."""
    repo_root = repo_root.resolve()
    inventory_path = inventory_path.resolve()
    signal_path = signal_path.resolve()
    view_path = view_path.resolve()

    records, groups, source_assertions = _load_inventory(
        inventory_path=inventory_path,
        repo_root=repo_root,
    )
    signals = _validate_decision_signals(signal_path=signal_path, repo_root=repo_root)
    root = _object(_load_json(view_path), label="consolidated view root")
    _reject_forbidden_presentation_keys(root)

    if (
        _string(root.get("artifact_version"), label="view artifact_version")
        != _VIEW_ARTIFACT_VERSION
    ):
        raise ConsolidatedViewValidationError("unexpected consolidated view artifact version")

    source_inventory = _string(root.get("source_inventory"), label="source_inventory")
    if Path(source_inventory) != _EXPECTED_INVENTORY_PATH:
        raise ConsolidatedViewValidationError(
            f"source_inventory must remain {_EXPECTED_INVENTORY_PATH.as_posix()}"
        )
    if (repo_root / source_inventory).resolve() != inventory_path:
        raise ConsolidatedViewValidationError(
            "source_inventory path does not match validator input"
        )

    source_signals = _string(root.get("decision_signal_manifest"), label="decision_signal_manifest")
    if (repo_root / source_signals).resolve() != signal_path:
        raise ConsolidatedViewValidationError(
            "decision_signal_manifest path does not match validator input"
        )

    sections = _list(root.get("sections"), label="sections")
    seen_sections: set[str] = set()
    seen_metrics: set[str] = set()
    unmeasured_count = 0
    not_applicable_count = 0

    for section_index, section_value in enumerate(sections):
        section = _object(section_value, label=f"sections[{section_index}]")
        section_id = _string(
            section.get("section_id"),
            label=f"sections[{section_index}].section_id",
        )
        if section_id in seen_sections:
            raise ConsolidatedViewValidationError(f"duplicate section_id: {section_id}")
        seen_sections.add(section_id)
        _string(section.get("description"), label=f"{section_id}.description")
        metrics = _list(section.get("metrics"), label=f"{section_id}.metrics")
        if not metrics:
            raise ConsolidatedViewValidationError(f"section {section_id} must not be empty")

        for metric_index, metric_value in enumerate(metrics):
            metric = _object(metric_value, label=f"{section_id}.metrics[{metric_index}]")
            metric_id = _string(metric.get("metric_id"), label=f"{section_id}.metric_id")
            if metric_id in seen_metrics:
                raise ConsolidatedViewValidationError(
                    f"metric appears more than once in consolidated view: {metric_id}"
                )
            if metric_id not in records:
                raise ConsolidatedViewValidationError(
                    f"consolidated view references unknown Gate 18.1 metric: {metric_id}"
                )
            seen_metrics.add(metric_id)
            source_record = records[metric_id]
            _assert_projection_equal(
                projected=metric,
                source=source_record,
                fields=_PROJECTED_METRIC_FIELDS,
                label=metric_id,
            )
            group_id = _string(
                source_record.get("comparability_group"), label=f"{metric_id}.comparability_group"
            )
            group = groups[group_id]
            expected_rule = group.get("comparison_rule")
            if metric.get("comparison_rule") != expected_rule:
                raise ConsolidatedViewValidationError(
                    f"{metric_id}.comparison_rule drifted from Gate 18.1: "
                    f"view={metric.get('comparison_rule')!r} source={expected_rule!r}"
                )
            expected_semantics = group.get("semantics")
            if metric.get("comparison_semantics") != expected_semantics:
                raise ConsolidatedViewValidationError(
                    f"{metric_id}.comparison_semantics drifted from Gate 18.1"
                )
            classification = source_record.get("classification")
            if classification == "UNMEASURED":
                unmeasured_count += 1
            elif classification == "NOT_APPLICABLE":
                not_applicable_count += 1

    if seen_sections != _EXPECTED_SECTION_IDS:
        raise ConsolidatedViewValidationError(
            "consolidated view sections must match the frozen Gate 18.2 dimensions exactly: "
            f"expected={sorted(_EXPECTED_SECTION_IDS)} observed={sorted(seen_sections)}"
        )
    if seen_metrics != set(records):
        missing = sorted(set(records) - seen_metrics)
        extra = sorted(seen_metrics - set(records))
        raise ConsolidatedViewValidationError(
            f"consolidated view must project every Gate 18.1 metric exactly once; "
            f"missing={missing} extra={extra}"
        )

    view_assertions = _list(root.get("non_comparable_pairs"), label="non_comparable_pairs")
    _assert_non_comparability_equal(
        view_assertions=view_assertions,
        source_assertions=source_assertions,
    )

    projected_signal_values = _list(root.get("decision_signals"), label="decision_signals")
    seen_signals: set[str] = set()
    for signal_index, signal_value in enumerate(projected_signal_values):
        projected_signal = _object(signal_value, label=f"decision_signals[{signal_index}]")
        signal_id = _string(
            projected_signal.get("signal_id"), label=f"decision_signals[{signal_index}].signal_id"
        )
        if signal_id in seen_signals:
            raise ConsolidatedViewValidationError(
                f"decision signal appears more than once in view: {signal_id}"
            )
        if signal_id not in signals:
            raise ConsolidatedViewValidationError(
                f"view references unknown decision signal: {signal_id}"
            )
        seen_signals.add(signal_id)
        _assert_projection_equal(
            projected=projected_signal,
            source=signals[signal_id],
            fields=_PROJECTED_SIGNAL_FIELDS,
            label=signal_id,
        )
    if seen_signals != set(signals):
        missing_signals = sorted(set(signals) - seen_signals)
        raise ConsolidatedViewValidationError(
            f"consolidated view must preserve every decision signal; missing={missing_signals}"
        )

    summary = _object(root.get("summary"), label="summary")
    expected_summary = {
        "sections": len(seen_sections),
        "metrics": len(seen_metrics),
        "decision_signals": len(seen_signals),
        "unmeasured": unmeasured_count,
        "not_applicable": not_applicable_count,
        "non_comparable_pairs": len(source_assertions),
    }
    for field, expected in expected_summary.items():
        if summary.get(field) != expected:
            raise ConsolidatedViewValidationError(
                f"summary.{field} mismatch: expected={expected!r} observed={summary.get(field)!r}"
            )

    return ConsolidatedViewSummary(
        section_count=len(seen_sections),
        metric_count=len(seen_metrics),
        decision_signal_count=len(seen_signals),
        unmeasured_count=unmeasured_count,
        not_applicable_count=not_applicable_count,
        non_comparability_assertion_count=len(source_assertions),
    )
