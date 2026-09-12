# OpsLens Demo

The canonical V1 demonstration path is **offline-first, deterministic, and reviewer-oriented**. It reuses retained OpsLens authority and never executes third-party repository code.

## Deterministic CLI

Install the locked environment:

```bash
uv sync --frozen
```

Run any of the three canonical scenarios:

```bash
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
uv run python scripts/demo_opslens.py --scenario controlled-benign --format text
uv run python scripts/demo_opslens.py --scenario fail-closed-incomplete-evidence --format text
```

Stable machine-readable projection:

```bash
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format json
```

Cross-scenario deterministic evaluation:

```bash
uv run python scripts/evaluate_opslens_demo.py --format text
uv run python scripts/evaluate_opslens_demo.py --format json
```

Every scenario is a synthetic inert fixture. The demo does not describe or scan a live repository. The runner uses existing typed repository-evidence, vulnerability correlation/enrichment, threat-scope, and Risk Policy v1 code to demonstrate the authority chain end to end.

## Local visual demo

Launch the localhost-only browser surface:

```bash
uv run python scripts/demo_opslens_web.py
```

Open:

```text
http://127.0.0.1:8765/
```

The visual demo shows all three deterministic scenarios, dependency evidence, finding/no-finding/fail-closed state, risk evidence, source provenance, and the exact content-addressed result identity.

The browser layer is deliberately a **presentation adapter**, not another decision engine:

```text
visual projection != business authority
localhost demo != public service
```

There is no `--host` option. The server binds to IPv4 loopback only. A local port override is supported:

```bash
uv run python scripts/demo_opslens_web.py --port 9000
```

The page loads no remote JavaScript, styles, fonts, or images. Dynamic values are HTML-escaped and the HTTP adapter uses allowlisted read-only routes plus browser hardening headers.

The **AI explanation** panel is intentionally present but marked **disabled and non-authoritative**. V1 makes no model call. A future explanation may summarize admitted evidence, but it cannot decide or override applicability, risk, no-finding, or fail-closed truth.

## Canonical properties

```text
AWS credentials required: NO
network after setup: NO
live provider execution: NO
model execution: NO
third-party repository code execution: NO
stable JSON output: YES
human-readable CLI output: YES
localhost visual output: YES
```

## Scenario semantics

```text
material-vulnerability
 -> complete admitted fixture evidence
 -> one material finding
 -> deterministic Risk Policy v1: 90 / P0

controlled-benign
 -> complete admitted scoped fixture evidence
 -> zero applicable findings
 -> fixture-only NO_MATERIAL_FINDING
 -> no live repository safety claim

fail-closed-incomplete-evidence
 -> unsupported dependency identity
 -> deterministic threat-scope rejection
 -> no repository analysis
 -> no risk result
 -> no benign conclusion
```

The visual and CLI surfaces preserve the same core distinction:

```text
complete evidence + no finding != incomplete evidence
missing evidence != benign evidence
```

## Reviewer / portfolio flow

For interviews or architecture reviews, use:

- [`WALKTHROUGH.md`](WALKTHROUGH.md) — a three-to-five-minute reviewer flow;
- [`PORTFOLIO_CAPTURE.md`](PORTFOLIO_CAPTURE.md) — reproducible screenshot/terminal-recording guidance;
- [`SCENARIOS.md`](SCENARIOS.md) — exact scenario semantics;
- [`AUTHORITY.md`](AUTHORITY.md) — deterministic vs probabilistic authority;
- [`QUICKSTART_TARGET.md`](QUICKSTART_TARGET.md) — V1 setup and quickstart target.

Supporting Gate 19.12 authority evidence:

- [`../../labs/phase-19-gate-19-12-local-visual-demo.md`](../../labs/phase-19-gate-19-12-local-visual-demo.md)

Remaining V1 slice after portfolio polish:

```text
Gate 19.14  V1 closeout + release readiness
```
