# Phase 19 — Gate 19.12 Minimal Local Visual Demo

## Source checkpoint

```text
protected main: 0c5bbe34792406ee5c66fcc5ac4b75923512703b
Gate 19.11 PR: #381 / merged
Gate 19.11 issue: #380 / closed completed
post-merge CodeQL: 34718268902 / run #424 / success
Gate 19.12 issue: #382
```

## Decision

Gate 19.12 adds a **localhost-only presentation adapter** over the exact deterministic V1 scenario results admitted by Gates 19.10–19.11.

```text
visual projection != business authority
localhost demo != public service
```

The visual surface does not introduce a second applicability engine, risk engine, benign classifier, fail-closed policy, retrieval path, provider adapter, or model authority. It reads the same typed scenario results used by the CLI and suite evaluator.

## Why standard-library HTTP

V1 is a demonstration and architecture lab, not a production SaaS. A framework such as React, Next.js, Streamlit, Gradio, or an additional Python web dependency would expand the supply chain and reviewer setup without strengthening the authority demonstration.

The selected implementation therefore uses Python's standard library:

```text
ThreadingHTTPServer
BaseHTTPRequestHandler
inline HTML/CSS
no JavaScript requirement
no external assets
```

The server is structurally bound to:

```text
127.0.0.1:8765
```

The launcher intentionally exposes only `--port`; there is no `--host` argument.

## Reviewer command

```bash
uv sync --frozen
uv run python scripts/demo_opslens_web.py
```

Then open:

```text
http://127.0.0.1:8765/
```

The port may be changed locally without changing the loopback-only host boundary:

```bash
uv run python scripts/demo_opslens_web.py --port 9000
```

## Visual scenario contract

The landing page exposes exactly three canonical scenario IDs:

```text
material-vulnerability
controlled-benign
fail-closed-incomplete-evidence
```

Each scenario page displays:

- synthetic repository fixture identity and immutable commit;
- dependency evidence;
- deterministic finding/no-finding/rejection state;
- risk result when one exists;
- content-addressed provenance identities;
- canonical machine evidence;
- an explicit deterministic-authority panel;
- a separate AI explanation panel marked disabled and non-authoritative.

### Material vulnerability

The UI presents the retained deterministic result:

```text
MATERIAL_FINDING
Requests 2.31.0
GHSA/CVE evidence
Risk Policy v1: P0 / 90
```

The UI does not calculate that score. It displays the retained risk-policy result.

### Controlled benign

The UI presents:

```text
NO_MATERIAL_FINDING
complete scoped fixture evidence
unsupported normalization = 0
controlled fixture only
live repository safety claim = false
```

This prevents visual wording from turning a controlled no-finding result into a live repository safety claim.

### Fail-closed incomplete evidence

The UI presents:

```text
REJECTED_INCOMPLETE_EVIDENCE
PUBLIC_THREAT_SCOPE_ADMISSION
analysis performed = false
risk result = none
benign conclusion = none
```

The viewer retains the invariant:

```text
missing evidence != benign evidence
```

## Browser and HTTP safety boundary

The local adapter is read-only and path-allowlisted.

Admitted routes:

```text
/
/health
/scenario/material-vulnerability
/scenario/controlled-benign
/scenario/fail-closed-incomplete-evidence
```

Unknown scenarios and routes fail closed. Query-string input is rejected. No route accepts repository URLs, arbitrary files, prompts, credentials, shell commands, provider coordinates, or tool instructions.

Every dynamic value is HTML-escaped before rendering. Responses set no-store and browser hardening headers including a restrictive Content Security Policy. The page requires no JavaScript and loads no remote styles, fonts, images, or scripts.

## AI boundary

The visual demo includes an explicit presentation panel stating:

```text
AI explanation: DISABLED in the V1 offline demo
model execution: false
model business-truth authority: false
```

A future model explanation may summarize already-admitted evidence, but it cannot authorize, override, repair, or invent deterministic applicability, prioritization, no-finding, or fail-closed truth.

## Verification

Gate 19.12 adds repository-only regression coverage for:

```text
exact three-scenario visual catalog
loopback host and default port
allowlisted scenario routing
unknown-route/scenario rejection
query-string rejection
provider/model-free health projection
HTML escaping of dynamic values
visual authority wording
```

Machine evidence:

```text
labs/evidence/phase-19-gate-19-12-local-visual-demo-v1.json
```

Offline verifier:

```bash
uv run python scripts/verify_phase19_gate19_12_visual_demo.py
```

## Hard boundary

```text
Terraform/provider operations:          0
AWS mutations:                          0
IAM mutations:                          0
artifact publications:                  0
runtime enablements:                    0
provider live executions:               0
model invocations:                      0
third-party repository code executions: 0
PR #89 modifications:                   0
```

## Exit semantics

Gate 19.12 is complete only after exact-head repository CI/security/CodeQL, HUMAN protected merge, and post-merge verification.

The next bounded slice is Gate 19.13 — Portfolio / README / Architecture Polish.

## Controlling invariants

```text
Agents reason. Code verifies evidence.
READ, NEVER EXECUTE third-party repository code.
missing evidence != benign evidence
model proposal != authorization
visual projection != business authority
localhost demo != public service
demonstration readiness != production readiness
```
