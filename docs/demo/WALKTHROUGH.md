# OpsLens V1 — 3–5 Minute Reviewer Walkthrough

This walkthrough is designed for an interview, recruiter screen, architecture review, or portfolio recording. It demonstrates the V1 authority model without live provider access.

## Before the walkthrough

From a clean clone:

```bash
uv sync --frozen
```

The demo scenarios are synthetic and inert. They do not execute third-party repository code and do not make live GitHub, AWS, Bedrock, or model calls after dependency installation.

## 0:00–0:30 — State the problem and invariant

Say:

> OpsLens answers a software-supply-chain question: given the dependencies a repository actually uses, which vulnerabilities materially affect it, what evidence proves that, and what should be prioritized?

Then show the core invariant:

```text
Agents reason. Code verifies evidence.
```

Explain in one sentence: models can propose or explain, while deterministic code owns identity, applicability, provenance, risk, authorization, and fail-closed behavior.

## 0:30–1:30 — Material vulnerability

Run:

```bash
uv run python scripts/demo_opslens.py \
  --scenario material-vulnerability \
  --format text
```

Point out:

- synthetic repository/dependency evidence;
- one applicable material finding;
- source-preserving GHSA/NVD/KEV/EPSS/CVSS evidence;
- deterministic Risk Policy v1 result: `90 / P0`;
- content-addressed result identity;
- no model or provider authority involved.

Key message:

```text
model explanation can describe the result; it cannot create or change it
```

## 1:30–2:15 — Controlled no-finding

Run:

```bash
uv run python scripts/demo_opslens.py \
  --scenario controlled-benign \
  --format text
```

Explain that this path is intentionally narrow:

```text
complete scoped fixture evidence + zero applicable findings
 -> NO_MATERIAL_FINDING
```

It is **not** a claim that a live repository is safe. The no-finding conclusion is valid only because the admitted fixture evidence is complete.

## 2:15–3:00 — Fail closed on incomplete evidence

Run:

```bash
uv run python scripts/demo_opslens.py \
  --scenario fail-closed-incomplete-evidence \
  --format text
```

Point out that unsupported dependency identity is rejected before repository analysis or risk prioritization.

```text
analysis performed: false
risk prioritization performed: false
benign conclusion: false
```

Key message:

```text
missing evidence != benign evidence
```

## 3:00–4:00 — Visual evidence viewer

Run:

```bash
uv run python scripts/demo_opslens_web.py
```

Open:

```text
http://127.0.0.1:8765/
```

Show the three scenario cards and one detailed scenario page. Highlight:

- repository/dependency identity;
- finding/no-finding/rejection state;
- risk evidence when present;
- provenance and content-addressed identifiers;
- canonical machine evidence;
- the visible authority-boundary panel;
- the AI explanation panel marked disabled/non-authoritative.

Explain that the browser layer does not recalculate any business truth:

```text
visual projection != business authority
localhost demo != public service
```

## 4:00–5:00 — Architecture and measured evidence

Open `docs/architecture.md` and show the Mermaid diagram.

Summarize the three architectural lanes:

1. deterministic software-supply-chain evidence and risk;
2. bounded structured/semantic GenAI paths;
3. presentation and interoperability layers that do not acquire business authority.

Then mention the retained Phase 19 representative workload only as bounded evidence:

```text
end-to-end duration: 17,748 ms MEASURED
GitHub HTTP requests: 4 MEASURED
Bedrock Retrieve: 1 MEASURED
Bedrock model call: 1 MEASURED
input/output tokens: 5,936 / 408 MEASURED
```

Close with:

```text
MEASURED != DERIVED
lab metric != production SLO
cost evidence != production TCO
materialized != enabled
demonstration readiness != production readiness
```

## Optional machine-readable proof

For an engineering reviewer, show the stable JSON:

```bash
uv run python scripts/demo_opslens.py \
  --scenario material-vulnerability \
  --format json

uv run python scripts/evaluate_opslens_demo.py --format json
```

The suite evaluation is deterministic and byte-stable; it verifies retained scenario outcomes without adding model or business authority.

## Interview talking points

Use these when the reviewer wants architecture depth:

- Why not put vulnerability applicability inside the LLM? Because package/version applicability is structured, testable business truth and should fail deterministically.
- Why keep RAG? For knowledge/remediation questions where semantic retrieval adds value, with evidence admission and citations.
- Why no unrestricted text-to-SQL? The model proposes bounded intent; deterministic code admits and compiles the query.
- Why retain an AWS async runtime if V1 is local? It is evidence of runtime, IAM, artifact, queue/state, Terraform, observability, and cost engineering, but V1 does not need to expose it publicly.
- Why three scenarios? A useful demo must prove success, controlled no-finding, and failure semantics—not only the happy path.

## Do not overclaim

Do not describe the V1 demo as a production SaaS, live vulnerability scanner, production SLO benchmark, production TCO model, or runtime-exposure authority.

```text
Repository Risk != Runtime Exposure.
Portfolio claim != new evidence authority.
```
