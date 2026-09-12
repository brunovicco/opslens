# Phase 19 — Gate 19.11 Curated Demo Scenarios + Deterministic Evaluation

## Source checkpoint

```text
protected main: 50456d304e7847fadd0d29373079afa1669acc9d
Gate 19.10 PR: #379 / merged
Gate 19.10 issue: #378 / closed completed
post-merge CodeQL: 34716596100 / run #421 / success
Gate 19.11 issue: #380
```

## Decision

Gate 19.11 admits exactly three canonical offline scenario classes over the Gate 19.10 runner boundary:

```text
material-vulnerability
controlled-benign
fail-closed-incomplete-evidence
```

All fixtures are synthetic, inert, content-addressed demonstration evidence. They require no AWS credentials, provider calls, model calls, network access after dependency installation, or execution of third-party repository code.

## Scenario 1 — material-vulnerability

The retained Gate 19.10 scenario remains the positive finding control:

```text
Requests 2.31.0
 -> applicable synthetic GHSA / CVE-2026-12345
 -> fixed version 2.32.0
 -> KEV present
 -> EPSS 0.42
 -> CVSS 9.8
 -> Risk Policy v1 90 / P0
```

This path proves admitted dependency evidence can produce deterministic applicability, enrichment, provenance, and risk prioritization.

## Scenario 2 — controlled-benign

The controlled benign fixture uses `Requests==2.32.0`, the first patched release for the same synthetic advisory range `>= 2, < 2.32`.

The threat-source fixture remains complete and explicitly scoped. `build_public_threat_evidence_scope` succeeds, unsupported normalization is empty, and the retained Phase 3/4 analysis deterministically produces zero applicable findings.

```text
state: NO_MATERIAL_FINDING
finding_count: 0
scoped_evidence_complete: true
unsupported_normalization_count: 0
benign claim scope: controlled fixture only
live repository safety claim: false
```

This is not evidence that a live repository is safe. It proves only that complete admitted fixture evidence can deterministically yield no material finding.

## Scenario 3 — fail-closed-incomplete-evidence

The fail-closed fixture contains one canonical-PyPI source record whose version is deliberately unprovable:

```text
requests == "not a version"
```

The retained Phase 3 normalization bridge records `invalid_version`. Gate 19.8 threat-scope authority then rejects the repository evidence with:

```text
public threat scope refuses incomplete PyPI normalization evidence
```

The scenario stops at `PUBLIC_THREAT_SCOPE_ADMISSION`.

```text
analysis performed: false
risk prioritization performed: false
benign conclusion: false
missing evidence treated as benign: false
```

This mechanically demonstrates:

```text
missing evidence != benign evidence
```

No model may repair or reinterpret missing deterministic authority into benign truth.

## Deterministic suite evaluation

The suite evaluator executes the three scenarios and produces a stable cross-scenario projection without adding business authority.

```bash
uv run python scripts/evaluate_opslens_demo.py --format text
uv run python scripts/evaluate_opslens_demo.py --format json
```

The evaluation asserts:

```text
controlled no-finding requires complete scoped evidence
controlled no-finding is fixture-scoped
missing evidence is not benign
fail-closed precedes risk prioritization
model has no business-truth authority
third-party repository code execution = false
```

The evaluator is a regression/reporting surface. Source applicability and risk truth remain owned by retained deterministic OpsLens authorities.

## Canonical reviewer commands

```bash
uv sync --frozen

uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
uv run python scripts/demo_opslens.py --scenario controlled-benign --format text
uv run python scripts/demo_opslens.py --scenario fail-closed-incomplete-evidence --format text

uv run python scripts/evaluate_opslens_demo.py --format text
```

Every scenario also supports `--format json` for byte-stable machine comparison.

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

Gate 19.11 is complete only after exact-head CI/security/CodeQL, HUMAN protected merge, and post-merge verification.

The next bounded slice is Gate 19.12 — Minimal Local Visual Demo.

## Controlling invariants

```text
Agents reason. Code verifies evidence.
READ, NEVER EXECUTE third-party repository code.
missing evidence != benign evidence
model proposal != authorization
materialized != enabled
demonstration readiness != production readiness
```
