# ADR 0066 — Bounded dependency and code-scanning signals

- Status: Accepted
- Date: 2026-09-10
- Phase: 17 — Security Hardening
- Gate: 17.3 — Dependency and code-scanning hardening
- Issue: #256

## Context

Gate 17.1 identified `SEC17-SUPPLY-001`: OpsLens had deterministic dependency locking and historical vulnerability-audit evidence, but no retained repository-local continuous dependency-review or code-scanning workflow. Gate 17.2 then hardened GitHub Actions authority and made `Repository security invariants` an enforced protected-main prerequisite before new security automation was introduced.

Gate 17.3 therefore evaluates the smallest GitHub-native controls that add useful supply-chain and static-analysis evidence without expanding AWS/runtime authority.

The repository is primarily Python and retains a checked-in `uv.lock`. Pull requests can therefore benefit from dependency-diff review, while the Python source tree is a direct fit for CodeQL static analysis.

## Decision

### 1. Retain pull-request dependency review

Use the official GitHub Dependency Review Action on pull requests:

```text
actions/dependency-review-action
release: v5.0.0
exact commit: a1d282b36b6f3519aa1f3fc636f609c47dddb294
failure threshold: HIGH
```

The workflow receives only:

```text
contents: read
```

It receives no OIDC token, AWS credentials, security-event write permission, pull-request write permission, or repository-content write permission.

The initial threshold is `high`, not because lower-severity findings are unimportant, but because Gate 17.3 is introducing a new merge-time signal. A future threshold change should be based on observed signal/noise and maintenance behavior rather than assumed severity policy.

### 2. Retain CodeQL for Python

Use the official CodeQL Action for Python on:

```text
pull requests targeting main
pushes to main
weekly schedule
manual dispatch
```

Frozen action source:

```text
github/codeql-action
release line: v4.38.0
exact commit: b96794f015dfd88f77b49b1c93e0fa7110f94c63
language: python
```

The workflow receives only the repository read permission plus the GitHub code-scanning upload permission required by CodeQL:

```text
contents: read
security-events: write
```

It receives no GitHub OIDC token and no AWS authority.

### 3. Scanner output remains engineering evidence

Dependency Review and CodeQL are security evidence sources, not OpsLens business-authority sources.

Permanent separations:

```text
dependency finding != vulnerability applicability authority
code-scanning alert != runtime exploitability truth
security scan success != absence of vulnerabilities
scanner output != model authority
GitHub security permission != AWS authority
```

Repository vulnerability applicability, Risk Policy v1, runtime exposure, model/capability authorization, and evidence admission remain under their existing deterministic contracts.

### 4. Extend the Gate 17.2 workflow verifier

`scripts/verify_workflow_security.py` remains the repository-local workflow policy authority and now additionally freezes:

- exact Dependency Review Action SHA;
- exact CodeQL Action SHA;
- dependency review as PR-only with `contents: read` and `fail-on-severity: high`;
- CodeQL Python triggers and `security-events: write` as its only additional write capability;
- absence of OIDC/AWS credentials in both scanner workflows.

This preserves the Gate 17.2 rule that new security tooling must not weaken workflow authority merely because the tooling itself is security-related.

### 5. Defer update automation and duplicate audit mechanisms

Do not add Dependabot version-update PR automation or another continuous `pip-audit` workflow in this slice.

Reasons:

- dependency review and CodeQL directly close the observed continuous-review/static-analysis gap with a small surface;
- automated version-update policy introduces cadence/grouping/noise decisions that are independent from vulnerability-diff admission;
- adding multiple vulnerability mechanisms in the same gate would make first-run signal and maintenance cost harder to attribute;
- no current evidence requires a broad dependency upgrade.

These controls may be evaluated later from measured repository needs.

## Alternatives rejected

### Enable every available GitHub security control at once

Rejected. Security automation also expands maintenance and permission surface. Gate 17.3 intentionally measures two controls that map directly to the observed repository shape.

### Make scanner output part of OpsLens Risk Policy v1

Rejected. GitHub dependency/code-scanning findings have different evidence semantics from the repository vulnerability correlation pipeline. Introducing them as business-risk authority would require a separate correlation/admission design.

### Grant broad write permissions for future convenience

Rejected. Dependency Review needs read access only. CodeQL receives `security-events: write` solely to publish code-scanning results. Neither scanner needs OIDC or AWS credentials.

### Add automatic dependency upgrades in the same gate

Rejected. Detection/review and upgrade policy are separate concerns. Gate 17.3 first establishes measurable security signals.

## Consequences

Positive:

- dependency changes receive continuous pull-request vulnerability review;
- Python source receives pull-request/default-branch/scheduled static analysis;
- every new external action remains exact-SHA pinned;
- scanner permissions are explicit and bounded;
- the already-enforced `Repository security invariants` context protects the workflow policy itself;
- no AWS or runtime authority is added.

Trade-offs:

- Dependency Review may depend on repository dependency-graph/platform availability;
- CodeQL upload may depend on repository code-scanning platform state;
- scanners can produce false positives/negatives and must not be treated as proof of absence or exploitability;
- weekly CodeQL execution adds GitHub Actions compute, not AWS spend.

## Cloud/runtime impact

```text
AWS mutations:          0
new IAM permissions:    0
new AWS services:       0
model invocations:      0
capability executions:  0
public runtime changes: 0
Inspector activation:   0
PR #89 changes:         0
```

## Evidence

```text
labs/phase-17-gate-17-3-dependency-code-scanning.md
labs/evidence/phase-17-gate-17-3-dependency-code-scanning-v1.json
```

The implementation must be validated on an exact PR head before Gate 17.3 is closed. Scanner success is interpreted as successful scanner execution, not as proof that the repository is vulnerability-free.
