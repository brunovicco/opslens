#!/usr/bin/env python3
"""Verify the offline Gate 19.13 V1 portfolio-presentation contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "labs/evidence/phase-19-gate-19-13-portfolio-polish-v1.json"
LAB_PATH = ROOT / "labs/phase-19-gate-19-13-portfolio-polish.md"

EXPECTED_MAIN_SHA = "4d001ba33e157c48891ccff3d5189263877f22b1"
EXPECTED_CODEQL_RUN_ID = 34719883927

PUBLIC_DOCS = {
    "readme_en": ROOT / "README.md",
    "readme_pt": ROOT / "README.pt-br.md",
    "docs_index": ROOT / "docs/README.md",
    "architecture_en": ROOT / "docs/architecture.md",
    "architecture_pt": ROOT / "docs/architecture.pt-br.md",
    "portfolio": ROOT / "docs/portfolio-evidence.md",
    "demo": ROOT / "docs/demo/README.md",
    "walkthrough": ROOT / "docs/demo/WALKTHROUGH.md",
    "capture": ROOT / "docs/demo/PORTFOLIO_CAPTURE.md",
    "checklist": ROOT / "docs/v1-completion-checklist.md",
    "current_state": ROOT / "docs/current-state.md",
    "roadmap": ROOT / "docs/roadmap.md",
}


def _load_json(path: Path) -> dict[str, JsonValue]:
    payload = cast(JsonValue, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(payload, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return payload


def _object(value: JsonValue, *, field: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise AssertionError(f"{field} must be an object")
    return value


def _read(name: str) -> str:
    return PUBLIC_DOCS[name].read_text(encoding="utf-8")


def _require(text: str, *markers: str, label: str) -> None:
    for marker in markers:
        assert marker in text, f"{label} is missing {marker!r}"


def _verify_contract() -> None:
    evidence = _load_json(EVIDENCE_PATH)
    assert evidence["schema_version"] == "opslens.phase19.gate19_13.portfolio_polish.v1"
    assert evidence["phase"] == 19
    assert evidence["gate"] == "19.13"
    assert evidence["issue"] == 384
    assert evidence["source_protected_main_sha"] == EXPECTED_MAIN_SHA
    assert evidence["decision"] == "POLISH_PUBLIC_V1_PRESENTATION_WITHOUT_NEW_AUTHORITY"

    gate_19_12 = _object(evidence["gate_19_12"], field="gate_19_12")
    assert gate_19_12["issue"] == 382
    assert gate_19_12["pull_request"] == 383
    assert gate_19_12["merge_sha"] == EXPECTED_MAIN_SHA
    assert gate_19_12["post_merge_codeql_run_id"] == EXPECTED_CODEQL_RUN_ID
    assert gate_19_12["post_merge_codeql_run_number"] == 430
    assert gate_19_12["post_merge_codeql_conclusion"] == "success"

    required = _object(evidence["required_properties"], field="required_properties")
    true_fields = (
        "readme_english_current",
        "readme_portuguese_current",
        "github_rendered_architecture_diagram",
        "deterministic_vs_model_authority_table",
        "measured_evidence_without_production_extrapolation",
        "security_failure_model",
        "reviewer_walkthrough_3_to_5_minutes",
        "portfolio_capture_guide",
    )
    for field in true_fields:
        assert required[field] is True, field
    assert required["binary_media_required"] is False
    assert required["business_authority_changed"] is False

    authority = _object(evidence["authority_impact"], field="authority_impact")
    assert all(
        isinstance(value, int) and not isinstance(value, bool) and value == 0
        for value in authority.values()
    )
    assert evidence["next_gate"] == "19.14_v1_closeout_release_readiness"


def _verify_readmes() -> None:
    readme_en = _read("readme_en")
    readme_pt = _read("readme_pt")
    shared = (
        "scripts/demo_opslens.py --scenario material-vulnerability --format text",
        "scripts/demo_opslens_web.py",
        "material-vulnerability",
        "controlled-benign",
        "fail-closed-incomplete-evidence",
        "ASYNC_SUBMIT_STATUS_RESULT",
        "Phase 19 — Bounded Public Runtime & Productization",
        "READ, NEVER EXECUTE third-party repository code.",
        "visual projection != business authority",
    )
    _require(readme_en, *shared, label="README.md")
    _require(readme_pt, *shared, label="README.pt-br.md")
    _require(
        readme_en,
        "Phases 0–18 are complete.",
        "historical decision: DEFERRED_PENDING_MEASUREMENT",
        label="README.md historical markers",
    )
    _require(
        readme_pt,
        "Phases 0–18 estão completas.",
        "decisão histórica: DEFERRED_PENDING_MEASUREMENT",
        label="README.pt-br.md historical markers",
    )


def _verify_architecture_and_portfolio() -> None:
    architecture_en = _read("architecture_en")
    architecture_pt = _read("architecture_pt")
    portfolio = _read("portfolio")

    _require(
        architecture_en,
        "Phases 0–18 are complete.",
        "Phase 19 — Bounded Public Runtime & Productization",
        "```mermaid",
        "## 3. Authority model",
        "## 8. Security and failure model",
        "lab metric != production SLO",
        "cost evidence != production TCO",
        "visual projection != business authority",
        label="English architecture",
    )
    _require(
        architecture_pt,
        "As Phases 0–18 estão completas.",
        "Phase 19 — Bounded Public Runtime & Productization",
        "```mermaid",
        "## 3. Modelo de autoridade",
        "## 8. Modelo de segurança e falhas",
        "lab metric != production SLO",
        "cost evidence != production TCO",
        label="Portuguese architecture",
    )
    _require(
        portfolio,
        "demonstration and architecture lab",
        "Portfolio claim != new evidence authority.",
        "17,748 ms MEASURED",
        "Throttle count | UNMEASURED",
        "missing evidence != benign evidence",
        "visual projection != business authority",
        "## What is not claimed",
        label="portfolio evidence",
    )
    assert "production-oriented GenAI" not in portfolio


def _verify_reviewer_assets() -> None:
    demo = _read("demo")
    walkthrough = _read("walkthrough")
    capture = _read("capture")

    _require(
        demo,
        "WALKTHROUGH.md",
        "PORTFOLIO_CAPTURE.md",
        "Gate 19.14  V1 closeout + release readiness",
        label="demo index",
    )
    _require(
        walkthrough,
        "3–5 Minute Reviewer Walkthrough",
        "material-vulnerability",
        "controlled-benign",
        "fail-closed-incomplete-evidence",
        "17,748 ms MEASURED",
        "lab metric != production SLO",
        "Portfolio claim != new evidence authority.",
        label="reviewer walkthrough",
    )
    _require(
        capture,
        "AWS credentials required: NO",
        "http://127.0.0.1:8765/",
        "opslens-v1-01-material-finding.png",
        "Binary screenshots/recordings are intentionally optional",
        label="portfolio capture guide",
    )


def _verify_current_docs() -> None:
    docs_index = _read("docs_index")
    checklist = _read("checklist")
    current_state = _read("current_state")
    roadmap = _read("roadmap")

    _require(
        docs_index,
        EXPECTED_MAIN_SHA,
        "34719883927 / run #430 / success",
        "Gate 19.13: IN PROGRESS / issue #384",
        "runtime decision: DEFERRED_PENDING_MEASUREMENT",
        label="documentation index",
    )
    _require(
        checklist,
        "Gate 19.12 — Local visual demo — COMPLETE",
        "Gate 19.13 — Portfolio polish — IN PROGRESS",
        "Gate 19.14 — V1 closeout",
        label="V1 completion checklist",
    )
    current_markers = (
        EXPECTED_MAIN_SHA,
        "34719883927 / run #430 / success",
        "19.12 Minimal Local Visual Demo                                COMPLETE",
        "19.13 Portfolio / README / Architecture Polish                 IN PROGRESS",
        "Gate 19.8 source protected main: 8700478c7fca230e5984c3ce034194ea3bd337e4",
        "34711607099",
        "#374",
        "materialized != enabled",
    )
    _require(current_state, *current_markers, label="current state")

    roadmap_markers = (
        EXPECTED_MAIN_SHA,
        "34719883927 / run #430 / success",
        "19.12 PR #383",
        "19.13 issue #384",
        "Gate 19.2 — Representative Workload Measurement — COMPLETE",
        "DEFERRED_PENDING_MEASUREMENT",
        "ASYNC_SUBMIT_STATUS_RESULT",
        "DEFERRED_PENDING_BOUNDED_RUNTIME_ADAPTER_EVIDENCE",
        "materialized != enabled",
    )
    _require(roadmap, *roadmap_markers, label="roadmap")


def _verify_lab() -> None:
    lab = LAB_PATH.read_text(encoding="utf-8")
    _require(
        lab,
        EXPECTED_MAIN_SHA,
        "Gate 19.13 issue: #384",
        "portfolio claim != new evidence authority",
        "HUMAN protected-merge boundary",
        "Terraform/provider operations:          0",
        "PR #89 modifications:                   0",
        label="Gate 19.13 lab",
    )


def main() -> None:
    """Run every provider-free Gate 19.13 verification."""
    _verify_contract()
    _verify_readmes()
    _verify_architecture_and_portfolio()
    _verify_reviewer_assets()
    _verify_current_docs()
    _verify_lab()

    source = Path(__file__).read_text(encoding="utf-8")
    for marker in ("import " + "boto3", "from " + "boto3", "subprocess"):
        assert marker not in source, marker

    print("Gate 19.13 portfolio/readme/architecture verification: PASS")


if __name__ == "__main__":
    main()
