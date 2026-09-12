"""Local visual projection over the deterministic OpsLens V1 demo results."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Literal

from opslens.demo.controlled_benign import ControlledBenignDemoResult
from opslens.demo.fail_closed import FailClosedDemoResult
from opslens.demo.material_vulnerability import DemoContractError, DemoRunResult

type VisualScenarioResult = DemoRunResult | ControlledBenignDemoResult | FailClosedDemoResult
type VisualTone = Literal["critical", "clear", "blocked"]

VISUAL_DEMO_CONTRACT_VERSION = "opslens-demo-visual:v1"


@dataclass(frozen=True, slots=True)
class VisualFact:
    """One already-admitted deterministic fact displayed by the visual adapter."""

    label: str
    value: str


@dataclass(frozen=True, slots=True)
class DemoVisualProjection:
    """Presentation-only projection of one deterministic demo result."""

    scenario_id: str
    title: str
    state: str
    tone: VisualTone
    repository: str
    commit_sha: str
    dependency: str
    finding_summary: str
    risk_summary: str
    evidence_summary: str
    result_id: str
    provenance: tuple[VisualFact, ...]
    notices: tuple[str, ...]
    canonical_json: str

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-ready presentation projection without new business truth."""
        return {
            "contract_version": VISUAL_DEMO_CONTRACT_VERSION,
            "scenario_id": self.scenario_id,
            "title": self.title,
            "state": self.state,
            "tone": self.tone,
            "repository": self.repository,
            "commit_sha": self.commit_sha,
            "dependency": self.dependency,
            "finding_summary": self.finding_summary,
            "risk_summary": self.risk_summary,
            "evidence_summary": self.evidence_summary,
            "result_id": self.result_id,
            "provenance": [
                {"label": fact.label, "value": fact.value} for fact in self.provenance
            ],
            "notices": list(self.notices),
            "authority": {
                "visual_projection_is_business_authority": False,
                "model_execution": False,
                "model_business_truth_authority": False,
            },
        }


def build_visual_projection(result: VisualScenarioResult) -> DemoVisualProjection:
    """Project retained demo truth for display without recalculating business decisions."""
    if isinstance(result, DemoRunResult):
        analysis = result.repository_analysis.analysis
        finding = analysis.findings[0]
        evaluation = result.prioritization.ranked_findings[0].evaluation
        return DemoVisualProjection(
            scenario_id=result.scenario_id,
            title="Material vulnerability",
            state="MATERIAL_FINDING",
            tone="critical",
            repository=analysis.repository_snapshot.repository.full_name,
            commit_sha=analysis.repository_snapshot.commit_sha,
            dependency=f"{finding.dependency_name}=={finding.installed_version}",
            finding_summary=(
                f"{finding.ghsa_id} / {finding.cve_id}; fixed in {finding.fixed_version}"
            ),
            risk_summary=(
                f"{evaluation.priority_tier.value} · {evaluation.priority_score}/100 · "
                f"KEV={evaluation.source.kev_state.value} · "
                f"EPSS={evaluation.source.epss_score} · "
                f"CVSS={evaluation.selected_cvss_base_score}"
            ),
            evidence_summary=(
                f"{analysis.finding_count} applicable finding; deterministic Risk Policy v1"
            ),
            result_id=result.result_id,
            provenance=(
                VisualFact("Repository evidence", result.source_execution.execution_id),
                VisualFact("Repository analysis", analysis.analysis_id),
                VisualFact("Risk policy", result.prioritization.policy.policy_id),
                VisualFact("Risk evaluation", evaluation.evaluation_id),
            ),
            notices=(
                "Synthetic inert fixture. No live repository safety or exposure claim.",
                "Applicability and prioritization are deterministic; no model call is involved.",
            ),
            canonical_json=result.canonical_json.decode("utf-8"),
        )

    if isinstance(result, ControlledBenignDemoResult):
        analysis = result.repository_analysis.analysis
        inventory = result.source_execution.normalization_inventory
        dependency = inventory.normalized_dependencies[0]
        return DemoVisualProjection(
            scenario_id="controlled-benign",
            title="Controlled no-finding",
            state="NO_MATERIAL_FINDING",
            tone="clear",
            repository=analysis.repository_snapshot.repository.full_name,
            commit_sha=analysis.repository_snapshot.commit_sha,
            dependency=f"{dependency.package.canonical}=={dependency.version.canonical}",
            finding_summary=(
                "No applicable vulnerability in the complete scoped fixture evidence."
            ),
            risk_summary=(
                "No risk evaluation was produced because the deterministic finding count is zero."
            ),
            evidence_summary=(
                "Complete admitted dependency identity and threat scope; "
                "unsupported normalization=0"
            ),
            result_id=result.result_id,
            provenance=(
                VisualFact("Repository evidence", result.source_execution.execution_id),
                VisualFact("Threat scope", result.threat_scope.scope_id),
                VisualFact("Repository analysis", analysis.analysis_id),
                VisualFact("Risk policy", result.prioritization.policy.policy_id),
            ),
            notices=(
                "Controlled fixture only; this is not a claim that a live repository is safe.",
                (
                    "No-finding is valid because scoped evidence is complete, "
                    "not because evidence is missing."
                ),
            ),
            canonical_json=result.canonical_json.decode("utf-8"),
        )

    if isinstance(result, FailClosedDemoResult):
        execution = result.source_execution
        snapshot = execution.snapshot_resolution.snapshot
        unsupported = execution.normalization_inventory.unsupported_normalization[0]
        return DemoVisualProjection(
            scenario_id="fail-closed-incomplete-evidence",
            title="Fail-closed incomplete evidence",
            state="REJECTED_INCOMPLETE_EVIDENCE",
            tone="blocked",
            repository=snapshot.repository.full_name,
            commit_sha=snapshot.commit_sha,
            dependency=(
                f"{unsupported.source_record.name_original}=="
                f"{unsupported.source_record.version_original}"
            ),
            finding_summary=(
                "Rejected at PUBLIC_THREAT_SCOPE_ADMISSION before repository analysis."
            ),
            risk_summary="No risk result and no benign conclusion were produced.",
            evidence_summary=(
                f"Unsupported dependency normalization: {unsupported.reason_code}; "
                f"{result.authority_message}"
            ),
            result_id=result.result_id,
            provenance=(
                VisualFact("Repository evidence", execution.execution_id),
                VisualFact("Rejected stage", "PUBLIC_THREAT_SCOPE_ADMISSION"),
                VisualFact("Normalization reason", unsupported.reason_code),
            ),
            notices=(
                "Missing evidence != benign evidence.",
                "The visual layer cannot override or repair the deterministic rejection.",
            ),
            canonical_json=result.canonical_json.decode("utf-8"),
        )

    raise DemoContractError("visual projection requires one admitted demo scenario result")


def _esc(value: object) -> str:
    """Escape every dynamic value before inserting it into local HTML."""
    return escape(str(value), quote=True)


def _tone_class(tone: VisualTone) -> str:
    """Map the closed visual tone set to an internal CSS class."""
    if tone == "critical":
        return "tone-critical"
    if tone == "clear":
        return "tone-clear"
    return "tone-blocked"


_BASE_CSS = """
:root {
  color-scheme: dark;
  --bg: #090d13;
  --panel: #111823;
  --text: #edf4ff;
  --muted: #97a8bc;
  --line: #253247;
  --accent: #67e8f9;
  --critical: #fb7185;
  --clear: #4ade80;
  --blocked: #fbbf24;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: radial-gradient(circle at 15% 0%, #132338 0, #090d13 34rem);
  color: var(--text);
  font: 15px/1.55 ui-sans-serif, system-ui, -apple-system, sans-serif;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
main { max-width: 1180px; margin: 0 auto; padding: 40px 24px 72px; }
.eyebrow {
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: .14em;
  font-size: 12px;
  font-weight: 700;
}
h1 {
  font-size: clamp(34px, 6vw, 64px);
  line-height: 1.02;
  margin: 8px 0 14px;
  letter-spacing: -.04em;
}
h2 { margin: 0 0 14px; font-size: 20px; }
p { color: var(--muted); }
.hero { margin-bottom: 30px; }
.hero p { max-width: 820px; font-size: 17px; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}
.card, .panel {
  background: linear-gradient(180deg, rgba(21,31,44,.96), rgba(17,24,35,.96));
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 18px 60px rgba(0,0,0,.22);
}
.card { display: flex; flex-direction: column; gap: 10px; min-height: 240px; }
.badge {
  width: max-content;
  border: 1px solid currentColor;
  border-radius: 999px;
  padding: 5px 9px;
  font: 700 11px/1 ui-monospace, monospace;
  letter-spacing: .04em;
}
.tone-critical { color: var(--critical); }
.tone-clear { color: var(--clear); }
.tone-blocked { color: var(--blocked); }
.kicker {
  color: var(--muted);
  font: 12px/1.4 ui-monospace, monospace;
  word-break: break-all;
}
.value { color: var(--text); font-weight: 650; }
.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, .6fr);
  gap: 16px;
  margin: 18px 0;
}
.stack { display: grid; gap: 16px; }
.facts { width: 100%; border-collapse: collapse; }
.facts th, .facts td {
  text-align: left;
  border-top: 1px solid var(--line);
  padding: 11px 8px;
  vertical-align: top;
}
.facts th { color: var(--muted); width: 180px; font-weight: 500; }
.facts td { word-break: break-word; }
.callout {
  border-left: 3px solid var(--accent);
  padding: 12px 14px;
  background: #0d1622;
  border-radius: 0 12px 12px 0;
  color: var(--muted);
}
.callout strong { color: var(--text); }
.danger { border-left-color: var(--blocked); }
pre {
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  background: #070b10;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px;
  color: #cfe1f7;
  font: 12px/1.55 ui-monospace, monospace;
}
details summary { cursor: pointer; color: var(--accent); font-weight: 650; }
nav { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; }
footer { margin-top: 28px; color: var(--muted); font-size: 13px; }
@media (max-width: 780px) {
  .detail-grid { grid-template-columns: 1fr; }
  main { padding: 28px 16px 56px; }
}
"""


def _shell(*, title: str, body: str) -> str:
    """Wrap local visual content with inline-only assets and no external dependencies."""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)} · OpsLens</title>
<style>{_BASE_CSS}</style>
</head>
<body><main>{body}</main></body>
</html>"""


def _scenario_card(projection: DemoVisualProjection) -> str:
    """Render one escaped scenario card for the local landing page."""
    tone = _tone_class(projection.tone)
    state = _esc(projection.state)
    title = _esc(projection.title)
    dependency = _esc(projection.dependency)
    risk = _esc(projection.risk_summary)
    scenario = _esc(projection.scenario_id)
    return f"""<article class="card">
<div class="badge {tone}">{state}</div>
<h2>{title}</h2>
<div>
<span class="kicker">dependency</span><br>
<span class="value">{dependency}</span>
</div>
<p>{risk}</p>
<a href="/scenario/{scenario}">Inspect evidence →</a>
</article>"""


def render_visual_index(projections: tuple[DemoVisualProjection, ...]) -> str:
    """Render the three admitted scenarios as a local reviewer landing page."""
    cards = "".join(_scenario_card(projection) for projection in projections)
    body = f"""<section class="hero">
<div class="eyebrow">OpsLens · V1 local evidence viewer</div>
<h1>Software risk, with the authority boundary visible.</h1>
<p>
Three synthetic, inert and deterministic scenarios reuse the same OpsLens
 evidence, correlation and risk-policy code as the CLI.
 This localhost UI is a presentation adapter only.
</p>
</section>
<section class="grid">{cards}</section>
<section class="panel" style="margin-top:16px">
<h2>Authority contract</h2>
<div class="callout">
<strong>Agents reason. Code verifies evidence.</strong><br>
Visual projection != business authority. No AWS, provider, model,
 repository-code execution or live repository safety claim occurs in this viewer.
</div>
</section>
<footer>
Localhost demo only · READ, NEVER EXECUTE third-party repository code ·
 demonstration readiness != production readiness
</footer>"""
    return _shell(title="V1 local evidence viewer", body=body)


def _fact_row(label: str, value: str, *, kicker: bool = False) -> str:
    """Render one escaped deterministic fact row."""
    css_class = ' class="kicker"' if kicker else ""
    return (
        f"<tr><th>{_esc(label)}</th>"
        f"<td{css_class}>{_esc(value)}</td></tr>"
    )


def render_visual_projection(projection: DemoVisualProjection) -> str:
    """Render one admitted scenario with evidence, provenance, and authority separation."""
    rows = [
        _fact_row("Repository fixture", projection.repository),
        _fact_row("Commit", projection.commit_sha, kicker=True),
        _fact_row("Dependency", projection.dependency),
        _fact_row("Finding", projection.finding_summary),
        _fact_row("Risk", projection.risk_summary),
        _fact_row("Evidence", projection.evidence_summary),
    ]
    provenance_rows = [
        _fact_row(fact.label, fact.value) for fact in projection.provenance
    ]
    provenance_rows.append(_fact_row("Visual result", projection.result_id, kicker=True))
    notices = "".join(f"<li>{_esc(notice)}</li>" for notice in projection.notices)
    tone = _tone_class(projection.tone)
    body = f"""<nav><a href="/">← All scenarios</a></nav>
<section class="hero">
<div class="eyebrow">{_esc(projection.scenario_id)}</div>
<h1>{_esc(projection.title)}</h1>
<div class="badge {tone}">{_esc(projection.state)}</div>
</section>
<section class="detail-grid">
<div class="stack">
<article class="panel">
<h2>Deterministic result</h2>
<table class="facts">{''.join(rows)}</table>
</article>
<article class="panel">
<h2>Source provenance</h2>
<table class="facts">{''.join(provenance_rows)}</table>
</article>
</div>
<div class="stack">
<article class="panel">
<h2>Authority boundary</h2>
<div class="callout">
<strong>Deterministic code owns business truth.</strong><br>
The visual adapter reads retained results. It does not recalculate applicability,
 evidence completeness, risk score, risk tier, no-finding, or rejection truth.
</div>
<ul>{notices}</ul>
</article>
<article class="panel">
<h2>AI explanation</h2>
<div class="callout danger">
<strong>Disabled in the V1 offline demo.</strong><br>
No model call was made. A future explanation may summarize admitted evidence,
 but it cannot authorize, override, repair, or invent deterministic truth.
</div>
</article>
</div>
</section>
<details class="panel">
<summary>Canonical machine evidence</summary>
<pre>{_esc(projection.canonical_json)}</pre>
</details>
<footer>visual projection != business authority · localhost demo != public service</footer>"""
    return _shell(title=projection.title, body=body)


__all__ = [
    "VISUAL_DEMO_CONTRACT_VERSION",
    "DemoVisualProjection",
    "VisualFact",
    "VisualScenarioResult",
    "build_visual_projection",
    "render_visual_index",
    "render_visual_projection",
]
