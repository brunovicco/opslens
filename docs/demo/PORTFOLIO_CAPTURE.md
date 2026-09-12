# OpsLens V1 — Portfolio Capture Guide

This guide produces consistent screenshots or a short terminal/browser recording without changing OpsLens authority or requiring provider access.

## Capture boundary

Capture only the synthetic V1 demo fixtures and public documentation.

```text
AWS credentials required: NO
live provider execution: NO
model execution: NO
third-party repository code execution: NO
public service exposure: NO
```

Do not include local credentials, environment files, AWS account identifiers, unrelated browser tabs, private repository URLs, or live customer/repository data.

## Recommended capture sequence

### 1. Terminal — material finding

```bash
uv sync --frozen
uv run python scripts/demo_opslens.py \
  --scenario material-vulnerability \
  --format text
```

Capture the result showing the material finding and deterministic `P0 (90/100)` prioritization.

### 2. Terminal — controlled no-finding

```bash
uv run python scripts/demo_opslens.py \
  --scenario controlled-benign \
  --format text
```

Capture the wording that limits the result to complete scoped fixture evidence.

### 3. Terminal — fail-closed path

```bash
uv run python scripts/demo_opslens.py \
  --scenario fail-closed-incomplete-evidence \
  --format text
```

Capture the rejection showing no analysis, no risk result, and no benign conclusion.

### 4. Browser — scenario catalog

Start:

```bash
uv run python scripts/demo_opslens_web.py
```

Open:

```text
http://127.0.0.1:8765/
```

Capture the three scenario cards in one frame.

### 5. Browser — detailed material finding

Open the material-vulnerability scenario from the catalog and capture:

- deterministic state;
- dependency and finding;
- risk summary;
- provenance identifiers;
- authority-boundary panel.

### 6. Browser — fail-closed evidence

Capture the fail-closed scenario page showing that incomplete evidence did not produce a benign result.

### 7. GitHub — architecture diagram

Open `docs/architecture.md` on GitHub and capture the rendered Mermaid authority diagram plus the deterministic-authority vs model-role table.

## Suggested 60–90 second recording

A compact portfolio recording can follow this order:

```text
00:00  README problem statement + Agents reason. Code verifies evidence.
00:10  material-vulnerability CLI -> P0 / 90
00:30  fail-closed CLI -> no risk / no benign conclusion
00:45  localhost viewer -> three scenario cards
01:00  detailed provenance / authority panel
01:15  architecture Mermaid diagram
01:25  finish on demonstration readiness != production readiness
```

## Framing guidance

Prefer one terminal window and one browser window. Keep font size large enough to read package identity, risk tier, and authority text without zooming during the recording.

Avoid decorative editing that hides evidence identifiers or failure semantics. The portfolio value is that the result can be traced to deterministic evidence, not that the UI resembles a production SaaS.

## Screenshot naming convention

If media is captured later, use stable names such as:

```text
opslens-v1-01-material-finding.png
opslens-v1-02-controlled-no-finding.png
opslens-v1-03-fail-closed.png
opslens-v1-04-visual-catalog.png
opslens-v1-05-material-provenance.png
opslens-v1-06-architecture.png
```

Binary screenshots/recordings are intentionally optional for Gate 19.13. The reproducible source-of-truth remains the deterministic demo plus this capture procedure; media may be refreshed without changing business authority.

## Claims to avoid in captions

Do not say:

- “production vulnerability scanner”;
- “real-time production service”;
- “safe repository” for the controlled-benign fixture;
- “production latency/SLO” for retained lab measurements;
- “production TCO” from bounded cost evidence;
- “AI decided the risk score.”

Prefer:

```text
Deterministic vulnerability applicability and risk authority
Synthetic/inert reproducible V1 scenario
Evidence-backed P0 prioritization
Fail-closed incomplete-evidence behavior
Local presentation over retained business truth
```
