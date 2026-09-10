"""Deterministic validation for the Phase 18 portfolio and AIP-C01 evidence pack."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast

_PORTFOLIO_VERSION = "phase-18-gate-18-4-portfolio-evidence-pack:v1"
_AIP_VERSION = "phase-18-gate-18-4-aip-c01-evidence-map:v1"
_VIEW = Path("labs/evidence/phase-18-gate-18-2-consolidated-view-v1.json")
_COST = Path("labs/evidence/phase-18-gate-18-3-cost-accounting-v1.json")
_SIGNALS = Path("labs/evidence/phase-18-gate-18-2-decision-signals-v1.json")

_METRIC_CLAIMS = {
    "portfolio.rag.claim_supportedness_rate": "p7.grounding.claim_supportedness_rate",
    "portfolio.reasoning.phase11.passed_cases": "p11.reasoning.passed_cases",
    "portfolio.reasoning.phase11.provider_latency_median": "p11.reasoning.provider_latency_median",
    "portfolio.reasoning.phase11.total_tokens": "p11.reasoning.total_tokens",
    "portfolio.reasoning.phase11.derived_inference_cost": "p11.reasoning.derived_inference_cost",
    "portfolio.reasoning.phase12.passed_cases": "p12.reasoning.passed_cases",
    "portfolio.reasoning.phase12.provider_latency_median": (
        "p12.reasoning.provider_latency_median_by_case"
    ),
    "portfolio.reasoning.phase12.total_tokens": "p12.reasoning.total_tokens",
    "portfolio.reasoning.phase12.derived_inference_cost": "p12.reasoning.derived_inference_cost",
    "portfolio.agentcore.passed_cases": "p14.agentcore.passed_cases",
    "portfolio.agentcore.derived_experiment_total": "p14.agentcore.total_experiment_cost",
}
_LIMIT_CLAIMS = {
    "portfolio.limit.semantic_planner.output_tokens": "limit.semantic_planner.output_tokens",
    "portfolio.limit.single_agent.output_tokens": "limit.single_agent.output_tokens",
    "portfolio.limit.multi_agent_triage.output_tokens": "limit.multi_agent_triage.output_tokens",
    "portfolio.limit.knowledge_synthesis.output_tokens": "limit.knowledge_synthesis.output_tokens",
    "portfolio.limit.athena.bytes_scanned_per_query": "limit.athena.bytes_scanned_per_query",
    "portfolio.limit.scheduler.maximum_event_age": "limit.scheduler.maximum_event_age",
    "portfolio.limit.scheduler.maximum_retry_attempts": "limit.scheduler.maximum_retry_attempts",
}
_SIGNAL_IDS = {
    "phase7-isolation-grounding-failure",
    "phase12-two-model-no-lift",
    "phase14-agentcore-not-default",
    "phase16-zero-records-not-zero-exposure",
}
_NOT_CLAIMED = {
    "public_http_production_runtime",
    "production_slo_from_lab_measurements",
    "production_tco_or_monthly_run_rate",
    "public_mcp_or_a2a_runtime",
    "agentcore_as_default_runtime",
    "zero_runtime_exposure_from_zero_inspector_records",
    "global_platform_kill_switch",
    "configured_limits_as_measured_utilization",
    "certification_readiness_score_or_pass_probability",
}
_AUTHORITY = {
    "aws_mutations": 0,
    "iam_mutations": 0,
    "runtime_mutations": 0,
    "model_invocations": 0,
    "capability_executions": 0,
    "new_benchmark_runs": 0,
    "pricing_refresh": False,
    "production_tco_created": False,
    "pr_89_touched": False,
}
_DOMAINS = {
    "1": ("Foundation Model Integration, Data Management, and Compliance", 31),
    "2": ("Implementation and Integration", 26),
    "3": ("AI Safety, Security, and Governance", 20),
    "4": ("Operational Efficiency and Optimization for GenAI Applications", 12),
    "5": ("Testing, Validation, and Troubleshooting", 11),
}
_TASKS = {
    "1.1": "Analyze requirements and design GenAI solutions.",
    "1.2": "Select and configure FMs.",
    "1.3": "Implement data validation and processing pipelines for FM consumption.",
    "1.4": "Design and implement vector store solutions.",
    "1.5": "Design retrieval mechanisms for FM augmentation.",
    "1.6": "Implement prompt engineering strategies and governance for FM interactions.",
    "2.1": "Implement agentic AI solutions and tool integrations.",
    "2.2": "Implement model deployment strategies.",
    "2.3": "Design and implement enterprise integration architectures.",
    "2.4": "Implement FM API integrations.",
    "2.5": "Implement application integration patterns and development tools.",
    "3.1": "Implement input and output safety controls.",
    "3.2": "Implement data security and privacy controls.",
    "3.3": "Implement AI governance and compliance mechanisms.",
    "3.4": "Implement responsible AI principles.",
    "4.1": "Implement cost optimization and resource efficiency strategies.",
    "4.2": "Optimize application performance.",
    "4.3": "Implement monitoring systems for GenAI applications.",
    "5.1": "Implement evaluation systems for GenAI.",
    "5.2": "Troubleshoot GenAI applications.",
}
_FORBIDDEN_KEYS = {
    "readiness_score",
    "coverage_score",
    "exam_readiness_percent",
    "certification_probability",
    "production_tco_usd",
    "monthly_run_rate_usd",
}


class AIPCoverageStatus(StrEnum):
    """Allowed evidence state for an AIP-C01 task."""

    EVIDENCED = "EVIDENCED"
    PARTIAL = "PARTIAL"
    STUDY_ONLY = "STUDY_ONLY"


class PortfolioPackValidationError(ValueError):
    """Raised when a portfolio/AIP artifact violates a frozen invariant."""


@dataclass(frozen=True, slots=True)
class PortfolioPackSummary:
    """Summary emitted after Gate 18.4 validation succeeds."""

    headline_metric_claim_count: int
    configured_budget_claim_count: int
    decision_signal_count: int
    aip_task_count: int
    aip_evidenced_count: int
    aip_partial_count: int
    aip_study_only_count: int


def _load(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PortfolioPackValidationError(f"invalid JSON artifact: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PortfolioPackValidationError(f"artifact must be a JSON object: {path}")
    return cast(dict[str, object], value)


def _items(value: object, *, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise PortfolioPackValidationError(f"{label} must be a JSON array")
    raw_items = cast(list[object], value)
    if not all(isinstance(item, dict) for item in raw_items):
        raise PortfolioPackValidationError(f"{label} must contain JSON objects")
    return cast(list[dict[str, object]], raw_items)


def _text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PortfolioPackValidationError(f"{label} must be a non-empty string")
    return value


def _repo_file(repo_root: Path, path_text: str) -> Path:
    relative = Path(path_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise PortfolioPackValidationError(f"unsafe repository evidence path: {path_text}")
    path = (repo_root / relative).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise PortfolioPackValidationError(
            f"evidence path escapes repository: {path_text}"
        ) from exc
    if not path.is_file():
        raise PortfolioPackValidationError(f"repository evidence does not exist: {path_text}")
    return path


def _reject_forbidden(value: object) -> None:
    if isinstance(value, dict):
        for key, child in cast(dict[str, object], value).items():
            if key in _FORBIDDEN_KEYS:
                raise PortfolioPackValidationError(f"forbidden synthetic field: {key}")
            _reject_forbidden(child)
    elif isinstance(value, list):
        for child in cast(list[object], value):
            _reject_forbidden(child)


def _view_metrics(path: Path) -> dict[str, dict[str, object]]:
    metrics: dict[str, dict[str, object]] = {}
    for section in _items(_load(path).get("sections"), label="sections"):
        for metric in _items(section.get("metrics"), label="section.metrics"):
            metric_id = _text(metric.get("metric_id"), label="metric_id")
            metrics[metric_id] = metric
    return metrics


def _cost_entries(path: Path) -> dict[str, dict[str, object]]:
    return {
        _text(entry.get("entry_id"), label="entry_id"): entry
        for entry in _items(_load(path).get("entries"), label="entries")
    }


def _signal_ids(path: Path) -> set[str]:
    return {
        _text(signal.get("signal_id"), label="signal_id")
        for signal in _items(_load(path).get("signals"), label="signals")
    }


def _validate_portfolio(path: Path, repo_root: Path) -> tuple[int, int, int]:
    root = _load(path)
    _reject_forbidden(root)
    if root.get("artifact_version") != _PORTFOLIO_VERSION:
        raise PortfolioPackValidationError("unexpected portfolio artifact_version")

    view = _repo_file(repo_root, _text(root.get("source_consolidated_view"), label="view"))
    cost = _repo_file(repo_root, _text(root.get("source_cost_accounting"), label="cost"))
    signals = _repo_file(repo_root, _text(root.get("source_decision_signals"), label="signals"))
    if view.relative_to(repo_root) != _VIEW or cost.relative_to(repo_root) != _COST:
        raise PortfolioPackValidationError("portfolio source artifact binding drifted")
    if signals.relative_to(repo_root) != _SIGNALS:
        raise PortfolioPackValidationError("portfolio signal artifact binding drifted")

    metrics = _view_metrics(view)
    entries = _cost_entries(cost)
    source_signal_ids = _signal_ids(signals)

    claims = _items(root.get("headline_metric_claims"), label="headline_metric_claims")
    seen_claims: set[str] = set()
    for claim in claims:
        claim_id = _text(claim.get("claim_id"), label="claim_id")
        source_id = _text(claim.get("source_metric_id"), label=f"{claim_id}.source_metric_id")
        if _METRIC_CLAIMS.get(claim_id) != source_id or source_id not in metrics:
            raise PortfolioPackValidationError(f"headline source binding drifted: {claim_id}")
        source = metrics[source_id]
        for field in ("classification", "value", "unit", "scope"):
            if claim.get(field) != source.get(field):
                raise PortfolioPackValidationError(f"{claim_id}.{field} drifted from Gate 18.2")
        _text(claim.get("statement"), label=f"{claim_id}.statement")
        seen_claims.add(claim_id)
    if seen_claims != set(_METRIC_CLAIMS):
        raise PortfolioPackValidationError("headline metric claim set drifted")

    limits = _items(root.get("configured_budget_claims"), label="configured_budget_claims")
    seen_limits: set[str] = set()
    for claim in limits:
        claim_id = _text(claim.get("claim_id"), label="limit claim_id")
        source_id = _text(claim.get("source_entry_id"), label=f"{claim_id}.source_entry_id")
        if _LIMIT_CLAIMS.get(claim_id) != source_id or source_id not in entries:
            raise PortfolioPackValidationError(
                f"configured-limit source binding drifted: {claim_id}"
            )
        source = entries[source_id]
        for field in ("classification", "value", "unit"):
            if claim.get(field) != source.get(field):
                raise PortfolioPackValidationError(f"{claim_id}.{field} drifted from Gate 18.3")
        seen_limits.add(claim_id)
    if seen_limits != set(_LIMIT_CLAIMS):
        raise PortfolioPackValidationError("configured budget claim set drifted")

    decision_signals = set(cast(list[str], root.get("decision_signals")))
    if decision_signals != _SIGNAL_IDS or not decision_signals.issubset(source_signal_ids):
        raise PortfolioPackValidationError("portfolio decision-signal set must remain exact")
    if set(cast(list[str], root.get("not_claimed"))) != _NOT_CLAIMED:
        raise PortfolioPackValidationError("portfolio not_claimed boundary drifted")
    if root.get("authority_impact") != _AUTHORITY:
        raise PortfolioPackValidationError("Gate 18.4 must remain repository-local/read-only")
    return len(seen_claims), len(seen_limits), len(decision_signals)


def _validate_aip(path: Path, repo_root: Path) -> tuple[int, int, int, int]:
    root = _load(path)
    _reject_forbidden(root)
    if root.get("artifact_version") != _AIP_VERSION:
        raise PortfolioPackValidationError("unexpected AIP map artifact_version")

    guide = cast(dict[str, object], root.get("exam_guide"))
    if guide.get("exam_code") != "AIP-C01" or guide.get("guide_year") != 2026:
        raise PortfolioPackValidationError("AIP exam guide identity drifted")
    if guide.get("title") != "AWS Certified Generative AI Developer - Professional":
        raise PortfolioPackValidationError("AIP exam guide title drifted")

    domains = _items(guide.get("domains"), label="exam_guide.domains")
    seen_domains: set[str] = set()
    for domain in domains:
        domain_id = _text(domain.get("domain_id"), label="domain_id")
        expected = _DOMAINS.get(domain_id)
        if expected is None:
            raise PortfolioPackValidationError(f"unknown AIP domain: {domain_id}")
        if (domain.get("title"), domain.get("weight_percent")) != expected:
            raise PortfolioPackValidationError(f"AIP domain {domain_id} title/weight drifted")
        seen_domains.add(domain_id)
    if seen_domains != set(_DOMAINS) or sum(weight for _, weight in _DOMAINS.values()) != 100:
        raise PortfolioPackValidationError("AIP domain set/weight total drifted")

    tasks = _items(root.get("task_coverage"), label="task_coverage")
    seen_tasks: set[str] = set()
    evidenced = partial = study_only = 0
    for task in tasks:
        task_id = _text(task.get("task_id"), label="task_id")
        if _TASKS.get(task_id) != task.get("title"):
            raise PortfolioPackValidationError(f"AIP task {task_id} title drifted")
        try:
            status = AIPCoverageStatus(_text(task.get("status"), label=f"{task_id}.status"))
        except ValueError as exc:
            raise PortfolioPackValidationError(f"unknown AIP status: {task_id}") from exc
        raw_paths = task.get("evidence_paths")
        if not isinstance(raw_paths, list):
            raise PortfolioPackValidationError(f"{task_id}.evidence_paths must be a list")
        raw_path_values = cast(list[object], raw_paths)
        evidence_paths = [_text(value, label="evidence_path") for value in raw_path_values]
        if status is AIPCoverageStatus.STUDY_ONLY:
            if evidence_paths:
                raise PortfolioPackValidationError(
                    f"STUDY_ONLY task {task_id} must not imply implementation evidence"
                )
            study_only += 1
        else:
            if not evidence_paths:
                raise PortfolioPackValidationError(
                    f"{status.value} task {task_id} requires repository evidence"
                )
            for evidence_path in evidence_paths:
                _repo_file(repo_root, evidence_path)
            if status is AIPCoverageStatus.EVIDENCED:
                evidenced += 1
            else:
                partial += 1
        _text(task.get("notes"), label=f"{task_id}.notes")
        seen_tasks.add(task_id)
    if seen_tasks != set(_TASKS):
        raise PortfolioPackValidationError("AIP task set drifted")

    if not _items(root.get("study_only_topics"), label="study_only_topics"):
        raise PortfolioPackValidationError("study_only_topics must remain explicit")
    boundaries = set(cast(list[str], root.get("boundaries")))
    required = {
        "AIP-C01 topic != product requirement",
        "exam coverage != certification guarantee",
        "service mentioned in exam guide != service required by OpsLens",
        "PARTIAL != EVIDENCED",
        "STUDY_ONLY != implemented",
    }
    if not required.issubset(boundaries):
        raise PortfolioPackValidationError("AIP mapping boundaries are incomplete")
    return len(seen_tasks), evidenced, partial, study_only


def validate_portfolio_pack(
    *, portfolio_path: Path, aip_map_path: Path, repo_root: Path
) -> PortfolioPackSummary:
    """Validate portfolio and AIP-C01 projections against retained evidence."""
    repo_root = repo_root.resolve()
    headline, limits, signals = _validate_portfolio(portfolio_path, repo_root)
    task_count, evidenced, partial, study_only = _validate_aip(aip_map_path, repo_root)
    return PortfolioPackSummary(
        headline_metric_claim_count=headline,
        configured_budget_claim_count=limits,
        decision_signal_count=signals,
        aip_task_count=task_count,
        aip_evidenced_count=evidenced,
        aip_partial_count=partial,
        aip_study_only_count=study_only,
    )
