"""Unit tests for the Phase 18 portfolio and AIP-C01 evidence-pack validator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from opslens.evaluation_readiness import (
    PortfolioPackValidationError,
    validate_portfolio_pack,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PORTFOLIO = _REPO_ROOT / "labs/evidence/phase-18-gate-18-4-portfolio-evidence-pack-v1.json"
_AIP_MAP = _REPO_ROOT / "labs/evidence/phase-18-gate-18-4-aip-c01-evidence-map-v1.json"


def _json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _write_json(tmp_path: Path, name: str, payload: dict[str, object]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_canonical_portfolio_pack_passes() -> None:
    """Validate the canonical portfolio and AIP-C01 artifacts end to end."""
    summary = validate_portfolio_pack(
        portfolio_path=_PORTFOLIO,
        aip_map_path=_AIP_MAP,
        repo_root=_REPO_ROOT,
    )

    assert summary.headline_metric_claim_count == 11
    assert summary.configured_budget_claim_count == 7
    assert summary.decision_signal_count == 4
    assert summary.aip_task_count == 20
    assert summary.aip_evidenced_count == 14
    assert summary.aip_partial_count == 6
    assert summary.aip_study_only_count == 0


def test_rejects_headline_metric_value_drift(tmp_path: Path) -> None:
    """Reject a portfolio metric whose value drifts from Gate 18.2 evidence."""
    payload = _json_object(_PORTFOLIO)
    claims = cast(list[dict[str, object]], payload["headline_metric_claims"])
    claims[0]["value"] = 1.0

    with pytest.raises(PortfolioPackValidationError, match=r"drifted from Gate 18\.2"):
        validate_portfolio_pack(
            portfolio_path=_write_json(tmp_path, "portfolio.json", payload),
            aip_map_path=_AIP_MAP,
            repo_root=_REPO_ROOT,
        )


def test_rejects_missing_decision_signal(tmp_path: Path) -> None:
    """Reject removal of a frozen negative or rejected-default signal."""
    payload = _json_object(_PORTFOLIO)
    signals = cast(list[object], payload["decision_signals"])
    signals.pop()

    with pytest.raises(PortfolioPackValidationError, match="decision-signal set"):
        validate_portfolio_pack(
            portfolio_path=_write_json(tmp_path, "portfolio.json", payload),
            aip_map_path=_AIP_MAP,
            repo_root=_REPO_ROOT,
        )


def test_rejects_hidden_production_readiness_score(tmp_path: Path) -> None:
    """Reject synthetic portfolio readiness scores outside evidence authority."""
    payload = _json_object(_PORTFOLIO)
    payload["readiness_score"] = 100

    with pytest.raises(PortfolioPackValidationError, match="forbidden synthetic"):
        validate_portfolio_pack(
            portfolio_path=_write_json(tmp_path, "portfolio.json", payload),
            aip_map_path=_AIP_MAP,
            repo_root=_REPO_ROOT,
        )


def test_rejects_not_claimed_boundary_drift(tmp_path: Path) -> None:
    """Reject removal of a portfolio boundary that must remain explicitly unclaimed."""
    payload = _json_object(_PORTFOLIO)
    not_claimed = cast(list[object], payload["not_claimed"])
    not_claimed.pop()

    with pytest.raises(PortfolioPackValidationError, match="not_claimed boundary"):
        validate_portfolio_pack(
            portfolio_path=_write_json(tmp_path, "portfolio.json", payload),
            aip_map_path=_AIP_MAP,
            repo_root=_REPO_ROOT,
        )


def test_rejects_missing_aip_task(tmp_path: Path) -> None:
    """Reject an AIP-C01 map that omits any frozen task identifier."""
    payload = _json_object(_AIP_MAP)
    tasks = cast(list[object], payload["task_coverage"])
    tasks.pop()

    with pytest.raises(PortfolioPackValidationError, match="AIP task set drifted"):
        validate_portfolio_pack(
            portfolio_path=_PORTFOLIO,
            aip_map_path=_write_json(tmp_path, "aip.json", payload),
            repo_root=_REPO_ROOT,
        )


def test_rejects_evidenced_task_without_repository_evidence(tmp_path: Path) -> None:
    """Reject EVIDENCED coverage when no repository evidence path is retained."""
    payload = _json_object(_AIP_MAP)
    tasks = cast(list[dict[str, object]], payload["task_coverage"])
    tasks[0]["evidence_paths"] = []

    with pytest.raises(PortfolioPackValidationError, match="requires repository evidence"):
        validate_portfolio_pack(
            portfolio_path=_PORTFOLIO,
            aip_map_path=_write_json(tmp_path, "aip.json", payload),
            repo_root=_REPO_ROOT,
        )


def test_rejects_study_only_task_with_implementation_evidence(tmp_path: Path) -> None:
    """Reject STUDY_ONLY coverage that falsely implies implementation evidence."""
    payload = _json_object(_AIP_MAP)
    tasks = cast(list[dict[str, object]], payload["task_coverage"])
    tasks[0]["status"] = "STUDY_ONLY"

    with pytest.raises(
        PortfolioPackValidationError, match="must not imply implementation evidence"
    ):
        validate_portfolio_pack(
            portfolio_path=_PORTFOLIO,
            aip_map_path=_write_json(tmp_path, "aip.json", payload),
            repo_root=_REPO_ROOT,
        )


def test_rejects_aip_domain_weight_drift(tmp_path: Path) -> None:
    """Reject domain-weight drift from the frozen human-reviewed exam baseline."""
    payload = _json_object(_AIP_MAP)
    guide = cast(dict[str, object], payload["exam_guide"])
    domains = cast(list[dict[str, object]], guide["domains"])
    domains[0]["weight_percent"] = 30

    with pytest.raises(PortfolioPackValidationError, match="title/weight drifted"):
        validate_portfolio_pack(
            portfolio_path=_PORTFOLIO,
            aip_map_path=_write_json(tmp_path, "aip.json", payload),
            repo_root=_REPO_ROOT,
        )
