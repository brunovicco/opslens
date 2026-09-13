"""Local visual projection over the deterministic OpsLens V1 demo results."""

from dataclasses import dataclass
from html import escape
from typing import Literal

from opslens.demo.controlled_benign import ControlledBenignDemoResult
from opslens.demo.fail_closed import FailClosedDemoResult
from opslens.demo.material_vulnerability import DemoRunResult

type VisualScenarioResult = DemoRunResult | ControlledBenignDemoResult | FailClosedDemoResult
type VisualTone = Literal["critical", "clear", "blocked"]

VISUAL_DEMO_CONTRACT_VERSION = "opslens-demo-visual:v2"

_DIGEST_PREFIX = "sha256:"
_DIGEST_HEAD = 8
_DIGEST_TAIL = 8


@dataclass(frozen=True, slots=True)
class VisualFact:
    """One already-admitted deterministic fact displayed by the visual adapter."""

    label: str
    value: str


@dataclass(frozen=True, slots=True)
class TierBand:
    """One priority tier boundary read from the deterministic policy, never invented."""

    tier: str
    minimum_score: int


@dataclass(frozen=True, slots=True)
class EvidenceChip:
    """One admitted evidence input displayed beside the score that consumed it."""

    label: str
    value: str
    tone: VisualTone | None = None
    """Set only where the value is a state. Magnitudes stay neutral."""


@dataclass(frozen=True, slots=True)
class RiskMeter:
    """A deterministic risk score projected against its own policy tier bands.

    Present only when deterministic code actually produced a risk evaluation. A
    scenario with no evaluation has no meter, because drawing an empty track at
    zero would state a risk truth the policy never emitted.
    """

    score: int
    tier: str
    maximum_score: int
    bands: tuple[TierBand, ...]

    def __post_init__(self) -> None:
        """Reject a meter that could misstate the deterministic evaluation."""
        if self.maximum_score <= 0:
            raise ValueError("risk meter maximum must be positive")
        if not 0 <= self.score <= self.maximum_score:
            raise ValueError("risk meter score must fall inside the policy scale")
        if not self.bands:
            raise ValueError("risk meter requires the policy tier bands")

    @property
    def filled_percent(self) -> float:
        """Return the fraction of the policy scale the score occupies."""
        return 100.0 * self.score / self.maximum_score

    def band_percent(self, band: TierBand) -> float:
        """Return where one tier boundary sits on the policy scale."""
        return 100.0 * band.minimum_score / self.maximum_score


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
    risk: RiskMeter | None = None
    evidence_chips: tuple[EvidenceChip, ...] = ()

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-ready presentation projection without new business truth."""
        risk: dict[str, object] | None = None
        if self.risk is not None:
            risk = {
                "score": self.risk.score,
                "tier": self.risk.tier,
                "maximum_score": self.risk.maximum_score,
                "bands": [
                    {"tier": band.tier, "minimum_score": band.minimum_score}
                    for band in self.risk.bands
                ],
            }
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
            "risk": risk,
            "evidence_chips": [
                {"label": chip.label, "value": chip.value, "tone": chip.tone}
                for chip in self.evidence_chips
            ],
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
        policy = result.prioritization.policy
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
            risk=RiskMeter(
                score=evaluation.priority_score,
                tier=evaluation.priority_tier.value,
                maximum_score=100,
                bands=(
                    TierBand("P0", policy.p0_threshold),
                    TierBand("P1", policy.p1_threshold),
                    TierBand("P2", policy.p2_threshold),
                ),
            ),
            evidence_chips=(
                EvidenceChip("KEV", evaluation.source.kev_state.value, tone="critical"),
                EvidenceChip("EPSS", str(evaluation.source.epss_score)),
                EvidenceChip("CVSS", str(evaluation.selected_cvss_base_score)),
            ),
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
            evidence_chips=(
                EvidenceChip("Applicable findings", "0"),
                EvidenceChip("Scoped evidence", "complete", tone="clear"),
                EvidenceChip("Unsupported normalization", "0"),
            ),
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
        evidence_chips=(
            EvidenceChip("Rejected at", "PUBLIC_THREAT_SCOPE_ADMISSION", tone="blocked"),
            EvidenceChip("Analysis performed", "no"),
            EvidenceChip("Risk evaluated", "no"),
        ),
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


def abbreviate_digest(value: str) -> str:
    """Shorten one ``sha256:<64 hex>`` identity for display, keeping both ends.

    The full value stays in the DOM as a ``title`` and in the canonical evidence
    block, so nothing is hidden — only the middle of the digest stops consuming
    four lines of the page.

    Args:
        value: An identity string that may embed a SHA-256 digest.

    Returns:
        The identity with any 64-character digest shortened, or the input
        unchanged when it carries none.
    """
    marker = value.find(_DIGEST_PREFIX)
    if marker < 0:
        return value
    start = marker + len(_DIGEST_PREFIX)
    digest = value[start : start + 64]
    if len(digest) != 64 or not all(character in "0123456789abcdef" for character in digest):
        return value
    shortened = f"{digest[:_DIGEST_HEAD]}…{digest[-_DIGEST_TAIL:]}"
    return f"{value[:start]}{shortened}{value[start + 64 :]}"


_BASE_CSS = """
:root {
  color-scheme: light dark;
  --bg: #090d13;
  --bg-glow: #132338;
  --panel: #111823;
  --panel-top: rgba(21,31,44,.96);
  --panel-bottom: rgba(17,24,35,.96);
  --sunk: #0d1622;
  --code-bg: #070b10;
  --code-text: #cfe1f7;
  --text: #edf4ff;
  --muted: #97a8bc;
  --line: #253247;
  --accent: #67e8f9;
  --critical: #fb7185;
  --critical-track: #3b2230;
  --clear: #4ade80;
  --clear-track: #1c3227;
  --blocked: #fbbf24;
  --blocked-track: #352b16;
  --shadow: 0 18px 60px rgba(0,0,0,.22);
}
@media (prefers-color-scheme: light) {
  :root {
    --bg: #f6f8fb;
    --bg-glow: #e4ecf6;
    --panel: #ffffff;
    --panel-top: rgba(255,255,255,.96);
    --panel-bottom: rgba(247,250,253,.96);
    --sunk: #eef3f9;
    --code-bg: #f2f5f9;
    --code-text: #1d2836;
    --text: #101722;
    --muted: #566274;
    --line: #d6dee8;
    --accent: #0f6f88;
    --critical: #b0313f;
    --critical-track: #f5dcdf;
    --clear: #1f6b45;
    --clear-track: #dbeee3;
    --blocked: #8a5a09;
    --blocked-track: #f6ead2;
    --shadow: 0 10px 34px rgba(16,23,34,.08);
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: radial-gradient(circle at 15% 0%, var(--bg-glow) 0, var(--bg) 34rem);
  color: var(--text);
  font: 15px/1.55 ui-sans-serif, system-ui, -apple-system, sans-serif;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
a:focus-visible, summary:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-radius: 4px;
}
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
  background: linear-gradient(180deg, var(--panel-top), var(--panel-bottom));
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 20px;
  box-shadow: var(--shadow);
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

/* ---- verdict: the deterministic outcome, read before anything else ---- */

.verdict { display: grid; gap: 18px; margin-bottom: 18px; }
.verdict-head { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 10px 18px; }
.score {
  display: flex;
  align-items: baseline;
  gap: 4px;
  line-height: 1;
}
.score b {
  font: 700 clamp(48px, 8vw, 68px)/1 ui-sans-serif, system-ui, -apple-system, sans-serif;
  letter-spacing: -.04em;
}
.score span { color: var(--muted); font-size: 20px; font-weight: 600; }
.tier {
  width: max-content;
  max-width: 100%;
  align-self: flex-start;
  font: 700 15px/1 ui-monospace, monospace;
  border: 1px solid currentColor;
  border-radius: 999px;
  padding: 7px 12px;
  letter-spacing: .05em;
}
.headline { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 14px; }
.verdict-state { margin-left: auto; }

.meter { display: grid; gap: 7px; }
.meter-track {
  position: relative;
  height: 12px;
  border-radius: 999px;
  overflow: hidden;
}
.meter-fill { height: 100%; border-radius: 999px; }
.meter-scale {
  position: relative;
  height: 20px;
  color: var(--muted);
  font: 11px/1 ui-monospace, monospace;
  letter-spacing: .04em;
}
.meter-scale span { position: absolute; top: 7px; transform: translateX(-50%); }
.meter-scale .at-start { left: 0; transform: none; }
.meter-scale .at-end { right: 0; left: auto; transform: none; }
.meter-tick {
  position: absolute;
  top: 0;
  width: 1px;
  height: 5px;
  background: var(--line);
}
.meter-legend { color: var(--muted); font-size: 13px; margin: 0; }

.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  display: inline-flex;
  align-items: baseline;
  flex-wrap: wrap;
  max-width: 100%;
  gap: 7px;
  border: 1px solid var(--line);
  background: var(--sunk);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 13px;
}
.chip .chip-label {
  color: var(--muted);
  font: 600 11px/1.4 ui-monospace, monospace;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.chip .chip-value { color: var(--text); font-weight: 650; overflow-wrap: anywhere; }
.chip.tone-critical, .chip.tone-clear, .chip.tone-blocked { border-color: currentColor; }
.chip.tone-critical .chip-value,
.chip.tone-clear .chip-value,
.chip.tone-blocked .chip-value { color: currentColor; }

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
  background: var(--sunk);
  border-radius: 0 12px 12px 0;
  color: var(--muted);
}
.callout strong { color: var(--text); }
.danger { border-left-color: var(--blocked); }
pre {
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  background: var(--code-bg);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px;
  color: var(--code-text);
  font: 12px/1.55 ui-monospace, monospace;
}
details summary { cursor: pointer; color: var(--accent); font-weight: 650; }
nav { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; }
footer { margin-top: 28px; color: var(--muted); font-size: 13px; }
@media (max-width: 780px) {
  .detail-grid { grid-template-columns: 1fr; }
  main { padding: 28px 16px 56px; }
  .verdict-state { margin-left: 0; }
}
"""

_FAVICON = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='7' fill='%23090d13'/%3E"
    "%3Ccircle cx='16' cy='16' r='8' fill='none' stroke='%2367e8f9' stroke-width='2.5'/%3E"
    "%3Cpath d='M16 11.5v5.5l3.4 2' fill='none' stroke='%2367e8f9' "
    "stroke-width='2.5' stroke-linecap='round'/%3E%3C/svg%3E"
)


def _shell(*, title: str, body: str) -> str:
    """Wrap local visual content with inline-only assets and no external dependencies."""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)} · OpsLens</title>
<link rel="icon" href="{_FAVICON}">
<style>{_BASE_CSS}</style>
</head>
<body><main>{body}</main></body>
</html>"""


def _chips(projection: DemoVisualProjection) -> str:
    """Render the admitted evidence inputs beside the outcome they produced."""
    if not projection.evidence_chips:
        return ""
    rendered = "".join(
        f'<span class="chip{" " + _tone_class(chip.tone) if chip.tone else ""}">'
        f'<span class="chip-label">{_esc(chip.label)}</span>'
        f'<span class="chip-value">{_esc(chip.value)}</span></span>'
        for chip in projection.evidence_chips
    )
    return f'<div class="chips">{rendered}</div>'


def _meter(meter: RiskMeter, tone: VisualTone) -> str:
    """Render one deterministic score against its own policy tier boundaries.

    Tier boundaries are ticks below the track, never dividers drawn across the
    fill: a segmented bar would read as four measured parts rather than one
    score placed on a scale.
    """
    tone_class = _tone_class(tone)
    ticks = "".join(
        f'<span class="meter-tick" style="left:{meter.band_percent(band):.4g}%"></span>'
        f'<span style="left:{meter.band_percent(band):.4g}%">'
        f"{_esc(band.tier)} {band.minimum_score}</span>"
        for band in meter.bands
    )
    return f"""<div class="meter">
<div class="meter-track {tone_class}" style="background:var(--{tone}-track)">
<div class="meter-fill" style="width:{meter.filled_percent:.4g}%;background:currentColor"></div>
</div>
<div class="meter-scale">
<span class="at-start">0</span>{ticks}<span class="at-end">{meter.maximum_score}</span>
</div>
<p class="meter-legend">Deterministic Risk Policy v1 score on its own tier scale.</p>
</div>"""


def _verdict(projection: DemoVisualProjection) -> str:
    """Render the deterministic outcome as the first thing on the page."""
    tone_class = _tone_class(projection.tone)
    state = f'<div class="badge {tone_class} verdict-state">{_esc(projection.state)}</div>'
    if projection.risk is None:
        head = (
            f'<div class="verdict-head">'
            f'<div class="eyebrow">Deterministic outcome</div>{state}</div>'
        )
        body = f'<p class="meter-legend">{_esc(projection.risk_summary)}</p>'
    else:
        head = f"""<div class="verdict-head">
<div class="score {tone_class}"><b>{projection.risk.score}</b><span>/{
            projection.risk.maximum_score
        }</span></div>
<div class="tier {tone_class}">{_esc(projection.risk.tier)}</div>
{state}
</div>"""
        body = _meter(projection.risk, projection.tone)
    return f'<section class="panel verdict">{head}{body}{_chips(projection)}</section>'


def _scenario_card(projection: DemoVisualProjection) -> str:
    """Render one escaped scenario card for the local landing page."""
    tone = _tone_class(projection.tone)
    state = _esc(projection.state)
    title = _esc(projection.title)
    dependency = _esc(projection.dependency)
    risk = _esc(projection.risk_summary)
    scenario = _esc(projection.scenario_id)
    if projection.risk is None:
        headline = f'<p>{risk}</p>'
    else:
        headline = (
            f'<div class="headline">'
            f'<div class="score {tone}"><b>{projection.risk.score}</b>'
            f'<span>/{projection.risk.maximum_score}</span></div>'
            f'<div class="tier {tone}">{_esc(projection.risk.tier)}</div>'
            f"</div>"
        )
    return f"""<article class="card">
<div class="badge {tone}">{state}</div>
<h2>{title}</h2>
{headline}
<div>
<span class="kicker">dependency</span><br>
<span class="value">{dependency}</span>
</div>
{_chips(projection)}
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
 A scenario with no deterministic risk evaluation shows no score, because an
 empty meter would state a risk truth the policy never emitted.
</div>
</section>
<footer>
Localhost demo only · READ, NEVER EXECUTE third-party repository code ·
 demonstration readiness != production readiness
</footer>"""
    return _shell(title="V1 local evidence viewer", body=body)


def _fact_row(label: str, value: str, *, kicker: bool = False) -> str:
    """Render one escaped deterministic fact row, shortening any embedded digest."""
    css_class = ' class="kicker"' if kicker else ""
    display = abbreviate_digest(value)
    title = f' title="{_esc(value)}"' if display != value else ""
    return (
        f"<tr><th>{_esc(label)}</th>"
        f"<td{css_class}{title}>{_esc(display)}</td></tr>"
    )


def render_visual_projection(projection: DemoVisualProjection) -> str:
    """Render one admitted scenario with evidence, provenance, and authority separation."""
    rows = [
        _fact_row("Repository fixture", projection.repository),
        _fact_row("Commit", projection.commit_sha, kicker=True),
        _fact_row("Dependency", projection.dependency),
        _fact_row("Finding", projection.finding_summary),
        _fact_row("Evidence", projection.evidence_summary),
    ]
    if projection.risk is None:
        # Without a verdict score above, the table is the only place the
        # deterministic non-outcome is stated.
        rows.insert(4, _fact_row("Risk", projection.risk_summary))
    provenance_rows = [
        _fact_row(fact.label, fact.value) for fact in projection.provenance
    ]
    provenance_rows.append(_fact_row("Visual result", projection.result_id, kicker=True))
    notices = "".join(f"<li>{_esc(notice)}</li>" for notice in projection.notices)
    body = f"""<nav><a href="/">← All scenarios</a></nav>
<section class="hero">
<div class="eyebrow">{_esc(projection.scenario_id)}</div>
<h1>{_esc(projection.title)}</h1>
</section>
{_verdict(projection)}
<section class="detail-grid">
<div class="stack">
<article class="panel">
<h2>Deterministic result</h2>
<table class="facts">{''.join(rows)}</table>
</article>
<article class="panel">
<h2>Source provenance</h2>
<table class="facts">{''.join(provenance_rows)}</table>
<p class="meter-legend">
Digests are shortened for reading; hover a value for the full identity, or open
 the canonical machine evidence below.
</p>
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
    "EvidenceChip",
    "RiskMeter",
    "TierBand",
    "VisualFact",
    "VisualScenarioResult",
    "abbreviate_digest",
    "build_visual_projection",
    "render_visual_index",
    "render_visual_projection",
]
