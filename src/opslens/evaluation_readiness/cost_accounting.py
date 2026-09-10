"""Deterministic validation for Phase 18 cost accounting and budget envelopes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast


_ARTIFACT_VERSION = "phase-18-gate-18-3-cost-accounting:v1"
_EXPECTED_VIEW = Path("labs/evidence/phase-18-gate-18-2-consolidated-view-v1.json")
_EXPECTED_CONTROL_EVIDENCE = Path(
    "labs/evidence/phase-17-gate-17-6-operational-recovery-v1.json"
)
_EXPECTED_AGGREGATION_POLICY = {
    "cross_component_sum": "FORBIDDEN",
    "alternative_workload_sum": "FORBIDDEN",
    "monthly_extrapolation_without_frozen_workload": "FORBIDDEN",
}

_EXPECTED_OBSERVATION_SOURCES = {
    "cost.p8.hybrid.complete": "p8.hybrid.cost",
    "cost.p11.reasoning.inference": "p11.reasoning.derived_inference_cost",
    "cost.p12.reasoning.inference": "p12.reasoning.derived_inference_cost",
    "cost.p14.agentcore.experiment_total": "p14.agentcore.total_experiment_cost",
    "cost.p14.agentcore.monthly": "p14.agentcore.monthly_extrapolation",
    "cost.p15.a2a.aws_runtime": "p15.a2a.aws_runtime_cost",
    "cost.p16.inspector.complete": "p16.inspector.aws_cost",
    "resource.p11.reasoning.total_tokens": "p11.reasoning.total_tokens",
    "resource.p12.reasoning.total_tokens": "p12.reasoning.total_tokens",
}
_EXPECTED_CONFIGURED_SOURCES = {
    "limit.semantic_planner.output_tokens": (
        "src/opslens/semantic_query/planner/bedrock.py",
        "existing_abuse_cost_controls.semantic_planner_max_tokens",
    ),
    "limit.single_agent.output_tokens": (
        "src/opslens/agent_baseline/adapters/bedrock_reasoning.py",
        "existing_abuse_cost_controls.single_agent_reasoning_max_tokens",
    ),
    "limit.multi_agent_triage.output_tokens": (
        "src/opslens/multi_agent/adapters/bedrock_triage_reasoning.py",
        "existing_abuse_cost_controls.triage_reasoning_max_tokens",
    ),
    "limit.knowledge_synthesis.output_tokens": (
        "src/opslens/knowledge_retrieval/application/bedrock_synthesis.py",
        "existing_abuse_cost_controls.knowledge_synthesis_max_tokens",
    ),
    "limit.athena.bytes_scanned_per_query": (
        "infra/environments/dev/analytics_athena.tf",
        "existing_abuse_cost_controls.athena_bytes_scanned_cutoff_per_query",
    ),
    "limit.scheduler.maximum_event_age": (
        "infra/environments/dev/operational_recovery.tf",
        "delivery_budget.maximum_event_age_seconds",
    ),
    "limit.scheduler.maximum_retry_attempts": (
        "infra/environments/dev/operational_recovery.tf",
        "delivery_budget.maximum_retry_attempts",
    ),
}
_EXPECTED_ENTRY_IDS = set(_EXPECTED_OBSERVATION_SOURCES) | set(_EXPECTED_CONFIGURED_SOURCES)
_FORBIDDEN_KEYS = {
    "production_tco_usd",
    "monthly_run_rate_usd",
    "projected_monthly_cost_usd",
    "portfolio_total_usd",
    "composite_cost_score",
    "readiness_score",
}


class CostAccountingClassification(StrEnum):
    """Allowed evidence and budget classifications for Gate 18.3."""

    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    CONFIGURED_LIMIT = "CONFIGURED_LIMIT"
    UNMEASURED = "UNMEASURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CostEntryKind(StrEnum):
    """Allowed Gate 18.3 entry kinds."""

    COST_OBSERVATION = "COST_OBSERVATION"
    RESOURCE_OBSERVATION = "RESOURCE_OBSERVATION"
    CONFIGURED_LIMIT = "CONFIGURED_LIMIT"


class CostAccountingValidationError(ValueError):
    """Raised when a Gate 18.3 cost-accounting invariant is violated."""


@dataclass(frozen=True, slots=True)
class CostAccountingSummary:
    """Validated summary for the Gate 18.3 cost-accounting artifact."""

    entry_count: int
    cost_observation_count: int
    resource_observation_count: int
    configured_limit_count: int
    unmeasured_count: int
    not_applicable_count: int


def _load_json(path: Path) -> object:
    try:
        return cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise CostAccountingValidationError(f"invalid JSON artifact: {path}: {exc}") from exc


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CostAccountingValidationError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _list(value: object, *, label: str) -> list[object]:
    if not isinstance(value, list):
        raise CostAccountingValidationError(f"{label} must be a JSON array")
    return cast(list[object], value)


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CostAccountingValidationError(f"{label} must be a non-empty string")
    return value


def _number(value: object, *, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise CostAccountingValidationError(f"{label} must be a number")
    return value


def _safe_repo_path(
    *, repo_root: Path, path_text: str, label: str, suffixes: tuple[str, ...]
) -> Path:
    relative = Path(path_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise CostAccountingValidationError(f"{label} must be repository-relative")
    if relative.suffix not in suffixes:
        raise CostAccountingValidationError(
            f"{label} must use one of {suffixes}: {path_text}"
        )
    resolved = (repo_root / relative).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise CostAccountingValidationError(f"{label} escapes repository root") from exc
    if not resolved.is_file():
        raise CostAccountingValidationError(f"{label} does not exist: {path_text}")
    return resolved


def _resolve_object_path(root: object, path: str) -> object:
    current = root
    for segment in path.split("."):
        if isinstance(current, dict):
            mapping = cast(dict[str, object], current)
            if segment not in mapping:
                raise CostAccountingValidationError(
                    f"source path {path!r} is missing segment {segment!r}"
                )
            current = mapping[segment]
            continue
        if isinstance(current, list):
            values = cast(list[object], current)
            try:
                index = int(segment)
            except ValueError as exc:
                raise CostAccountingValidationError(
                    f"source path {path!r} requires a numeric index at {segment!r}"
                ) from exc
            if index < 0 or index >= len(values):
                raise CostAccountingValidationError(
                    f"source path {path!r} index out of range: {index}"
                )
            current = values[index]
            continue
        raise CostAccountingValidationError(
            f"source path {path!r} traverses a scalar before {segment!r}"
        )
    return current


def _reject_forbidden_keys(value: object, *, path: str = "artifact") -> None:
    if isinstance(value, dict):
        mapping = cast(dict[str, object], value)
        for key, child in mapping.items():
            if key in _FORBIDDEN_KEYS:
                raise CostAccountingValidationError(
                    f"forbidden production/composite cost field {key!r} at {path}"
                )
            _reject_forbidden_keys(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(cast(list[object], value)):
            _reject_forbidden_keys(child, path=f"{path}[{index}]")


def _load_view_metrics(view_path: Path) -> dict[str, dict[str, object]]:
    root = _object(_load_json(view_path), label="consolidated view root")
    metrics: dict[str, dict[str, object]] = {}
    for section_index, section_value in enumerate(_list(root.get("sections"), label="sections")):
        section = _object(section_value, label=f"sections[{section_index}]")
        for metric_index, metric_value in enumerate(
            _list(section.get("metrics"), label=f"sections[{section_index}].metrics")
        ):
            metric = _object(
                metric_value,
                label=f"sections[{section_index}].metrics[{metric_index}]",
            )
            metric_id = _string(metric.get("metric_id"), label="metric_id")
            if metric_id in metrics:
                raise CostAccountingValidationError(
                    f"duplicate metric in consolidated view: {metric_id}"
                )
            metrics[metric_id] = metric
    if not metrics:
        raise CostAccountingValidationError("consolidated view contains no metrics")
    return metrics


def _expected_classification(source_classification: str) -> CostAccountingClassification:
    mapping = {
        "MEASURED": CostAccountingClassification.OBSERVED,
        "DERIVED": CostAccountingClassification.DERIVED,
        "UNMEASURED": CostAccountingClassification.UNMEASURED,
        "NOT_APPLICABLE": CostAccountingClassification.NOT_APPLICABLE,
    }
    try:
        return mapping[source_classification]
    except KeyError as exc:
        raise CostAccountingValidationError(
            f"unsupported source metric classification: {source_classification}"
        ) from exc


def _validate_observation_entry(
    *, entry: dict[str, object], metrics: dict[str, dict[str, object]], entry_id: str
) -> CostAccountingClassification:
    metric_id = _string(entry.get("source_metric_id"), label=f"{entry_id}.source_metric_id")
    expected_metric_id = _EXPECTED_OBSERVATION_SOURCES.get(entry_id)
    if expected_metric_id is None or metric_id != expected_metric_id:
        raise CostAccountingValidationError(
            f"{entry_id} must retain source metric {expected_metric_id!r}"
        )
    if metric_id not in metrics:
        raise CostAccountingValidationError(
            f"{entry_id} references unknown Gate 18.2 metric: {metric_id}"
        )
    metric = metrics[metric_id]
    source_dimension = _string(metric.get("dimension"), label=f"{metric_id}.dimension")
    kind = CostEntryKind(_string(entry.get("kind"), label=f"{entry_id}.kind"))
    expected_dimension = (
        "cost" if kind is CostEntryKind.COST_OBSERVATION else "token_volume"
    )
    if source_dimension != expected_dimension:
        raise CostAccountingValidationError(
            f"{entry_id} source dimension must be {expected_dimension}: {source_dimension}"
        )
    source_classification = _string(
        metric.get("classification"), label=f"{metric_id}.classification"
    )
    expected = _expected_classification(source_classification)
    classification_text = _string(
        entry.get("classification"), label=f"{entry_id}.classification"
    )
    try:
        classification = CostAccountingClassification(classification_text)
    except ValueError as exc:
        raise CostAccountingValidationError(
            f"unknown classification for {entry_id}: {classification_text}"
        ) from exc
    if classification is not expected:
        raise CostAccountingValidationError(
            f"{entry_id} classification drift: expected={expected.value} "
            f"observed={classification.value}"
        )
    if entry.get("value") != metric.get("value"):
        raise CostAccountingValidationError(f"{entry_id}.value drifted from Gate 18.2")
    if entry.get("unit") != metric.get("unit"):
        raise CostAccountingValidationError(f"{entry_id}.unit drifted from Gate 18.2")
    if classification in {
        CostAccountingClassification.UNMEASURED,
        CostAccountingClassification.NOT_APPLICABLE,
    }:
        if entry.get("value") is not None:
            raise CostAccountingValidationError(
                f"{entry_id} must preserve null; missing/inapplicable != zero"
            )
        _string(entry.get("reason"), label=f"{entry_id}.reason")
    elif entry.get("value") is None:
        raise CostAccountingValidationError(f"{entry_id} must preserve a non-null value")
    return classification


def _validate_configured_limit(
    *,
    entry: dict[str, object],
    repo_root: Path,
    control_evidence: object,
    entry_id: str,
) -> CostAccountingClassification:
    classification_text = _string(
        entry.get("classification"), label=f"{entry_id}.classification"
    )
    try:
        classification = CostAccountingClassification(classification_text)
    except ValueError as exc:
        raise CostAccountingValidationError(
            f"unknown classification for {entry_id}: {classification_text}"
        ) from exc
    if classification is not CostAccountingClassification.CONFIGURED_LIMIT:
        raise CostAccountingValidationError(
            f"configured limit {entry_id} must use CONFIGURED_LIMIT classification"
        )
    value = _number(entry.get("value"), label=f"{entry_id}.value")
    if value <= 0:
        raise CostAccountingValidationError(f"{entry_id}.value must be positive")
    source_path_text = _string(
        entry.get("source_repository_path"), label=f"{entry_id}.source_repository_path"
    )
    source_path = _safe_repo_path(
        repo_root=repo_root,
        path_text=source_path_text,
        label=f"{entry_id}.source_repository_path",
        suffixes=(".py", ".tf"),
    )
    source_literal = _string(entry.get("source_literal"), label=f"{entry_id}.source_literal")
    if source_literal not in source_path.read_text(encoding="utf-8"):
        raise CostAccountingValidationError(
            f"{entry_id}.source_literal not found in retained repository configuration"
        )
    evidence_value_path = _string(
        entry.get("control_evidence_value_path"),
        label=f"{entry_id}.control_evidence_value_path",
    )
    expected_source = _EXPECTED_CONFIGURED_SOURCES.get(entry_id)
    if expected_source is None or (source_path_text, evidence_value_path) != expected_source:
        raise CostAccountingValidationError(
            f"configured limit {entry_id} source binding drifted from the frozen contract"
        )
    observed_control_value = _resolve_object_path(control_evidence, evidence_value_path)
    if observed_control_value != value:
        raise CostAccountingValidationError(
            f"{entry_id} differs from retained control evidence: "
            f"artifact={value!r} evidence={observed_control_value!r}"
        )
    if entry.get("source_metric_id") is not None:
        raise CostAccountingValidationError(
            f"configured limit {entry_id} must not masquerade as an observed metric"
        )
    return classification


def validate_cost_accounting(
    *, artifact_path: Path, repo_root: Path
) -> CostAccountingSummary:
    """Validate the Gate 18.3 cost/resource envelope without creating spend authority."""
    repo_root = repo_root.resolve()
    root = _object(_load_json(artifact_path), label="cost-accounting root")
    _reject_forbidden_keys(root)

    version = _string(root.get("artifact_version"), label="artifact_version")
    if version != _ARTIFACT_VERSION:
        raise CostAccountingValidationError(f"unexpected artifact_version: {version}")

    view_text = _string(root.get("source_consolidated_view"), label="source_consolidated_view")
    if Path(view_text) != _EXPECTED_VIEW:
        raise CostAccountingValidationError(
            f"source_consolidated_view must remain {_EXPECTED_VIEW.as_posix()}"
        )
    view_path = _safe_repo_path(
        repo_root=repo_root,
        path_text=view_text,
        label="source_consolidated_view",
        suffixes=(".json",),
    )
    metrics = _load_view_metrics(view_path)

    control_text = _string(root.get("control_evidence"), label="control_evidence")
    if Path(control_text) != _EXPECTED_CONTROL_EVIDENCE:
        raise CostAccountingValidationError(
            f"control_evidence must remain {_EXPECTED_CONTROL_EVIDENCE.as_posix()}"
        )
    control_path = _safe_repo_path(
        repo_root=repo_root,
        path_text=control_text,
        label="control_evidence",
        suffixes=(".json",),
    )
    control_evidence = _load_json(control_path)

    policy = _object(root.get("aggregation_policy"), label="aggregation_policy")
    if policy != _EXPECTED_AGGREGATION_POLICY:
        raise CostAccountingValidationError(
            "aggregation_policy must preserve the frozen no-cross-component-sum boundary"
        )

    entries = _list(root.get("entries"), label="entries")
    if not entries:
        raise CostAccountingValidationError("cost-accounting artifact must contain entries")

    seen_ids: set[str] = set()
    cost_observations = 0
    resource_observations = 0
    configured_limits = 0
    unmeasured = 0
    not_applicable = 0

    for index, entry_value in enumerate(entries):
        entry = _object(entry_value, label=f"entries[{index}]")
        entry_id = _string(entry.get("entry_id"), label=f"entries[{index}].entry_id")
        if entry_id in seen_ids:
            raise CostAccountingValidationError(f"duplicate entry_id: {entry_id}")
        seen_ids.add(entry_id)
        _string(entry.get("component_boundary"), label=f"{entry_id}.component_boundary")
        _string(entry.get("scope"), label=f"{entry_id}.scope")
        _string(entry.get("unit"), label=f"{entry_id}.unit")

        kind_text = _string(entry.get("kind"), label=f"{entry_id}.kind")
        try:
            kind = CostEntryKind(kind_text)
        except ValueError as exc:
            raise CostAccountingValidationError(
                f"unknown entry kind for {entry_id}: {kind_text}"
            ) from exc

        if kind is CostEntryKind.CONFIGURED_LIMIT:
            classification = _validate_configured_limit(
                entry=entry,
                repo_root=repo_root,
                control_evidence=control_evidence,
                entry_id=entry_id,
            )
            configured_limits += 1
        else:
            classification = _validate_observation_entry(
                entry=entry,
                metrics=metrics,
                entry_id=entry_id,
            )
            if kind is CostEntryKind.COST_OBSERVATION:
                cost_observations += 1
            else:
                resource_observations += 1

        if classification is CostAccountingClassification.UNMEASURED:
            unmeasured += 1
        elif classification is CostAccountingClassification.NOT_APPLICABLE:
            not_applicable += 1

    if seen_ids != _EXPECTED_ENTRY_IDS:
        missing = sorted(_EXPECTED_ENTRY_IDS - seen_ids)
        extra = sorted(seen_ids - _EXPECTED_ENTRY_IDS)
        raise CostAccountingValidationError(
            f"Gate 18.3 entries drifted from frozen first slice; missing={missing} extra={extra}"
        )

    summary = _object(root.get("summary"), label="summary")
    expected_summary = {
        "entries": len(seen_ids),
        "cost_observations": cost_observations,
        "resource_observations": resource_observations,
        "configured_limits": configured_limits,
        "unmeasured": unmeasured,
        "not_applicable": not_applicable,
    }
    for field, expected in expected_summary.items():
        if summary.get(field) != expected:
            raise CostAccountingValidationError(
                f"summary.{field} mismatch: expected={expected} observed={summary.get(field)!r}"
            )

    return CostAccountingSummary(
        entry_count=len(seen_ids),
        cost_observation_count=cost_observations,
        resource_observation_count=resource_observations,
        configured_limit_count=configured_limits,
        unmeasured_count=unmeasured,
        not_applicable_count=not_applicable,
    )
