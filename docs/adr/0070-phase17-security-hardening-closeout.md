# ADR 0070 — Close Phase 17 at the Evidence-Backed Security Hardening Boundary

- Status: Accepted
- Date: 2026-09-10
- Phase: 17 — Security Hardening
- Gate: 17.8 — Phase closeout
- Issue: #277

## Context

Phase 17 began with a cross-cutting threat/control-gap inventory rather than a preselected security product. The phase then hardened only observed gaps while preserving the OpsLens authority model:

> **Agents reason. Code verifies evidence.**

> **Repository Risk != Runtime Exposure.**

The completed sequence is:

```text
17.1  evidence-first threat/control-gap inventory
17.2  CI/CD and workflow authority hardening
17.3  bounded Dependency Review + CodeQL signals
17.4  adversarial authority-boundary regression
17.5  content-minimized Lambda telemetry hardening
17.6  bounded scheduled-ingestion recovery + measured live proof
17.7  accumulated architecture synchronization
17.8  phase closeout
```

Gate 17.7 closed the final low-priority documentation gap from the original Gate 17.1 inventory. No later evidence justified another runtime/security control before closeout.

## Decision

Close Phase 17 and retain the following controls and boundaries.

### Repository and workflow authority

```text
protected-main required context:     Repository security invariants
external GitHub Actions:             full 40-hex SHA pins
checkout persisted credentials:      disabled where unnecessary
pull_request_target/workflow_run:     rejected by default
EPSS planning authority:             read-only evidence identity
EPSS execution authority:            separate coordinator identity
long STS session:                    execute-only bounded backfill path
historical AgentCore mutation path:  retired / fail-closed
```

The required context is enforced by the active protected-main ruleset; it is not documentation-only intent.

### Dependency/code security signals

```text
Dependency Review:  pull_request / fail-on-severity=high / contents:read
CodeQL Python:      PR + main + weekly + manual / security-events:write only where required
AWS/OIDC authority: none for scanner workflows
```

Scanner output remains an engineering signal, not deterministic vulnerability applicability or runtime exploitability truth.

### Adversarial authority regression

Retain the bounded offline suite covering public-input abuse, direct/indirect prompt injection, capability widening, forged result evidence, MCP abuse, A2A reference smuggling, and amplification attempts.

```text
adversarial test success != proof of universal safety
```

The suite does not gain AWS, model, or capability execution authority.

### Telemetry safety

Retain explicit suppression of automatic Lambda event/response/error capture and bounded failure logging across the 12 Powertools Lambda handlers.

```text
log event suppression != trace response/error suppression
exception text != safe telemetry by default
trace metadata != business/evidence truth
```

### Operational recovery

Retain one Terraform-owned, reversible pause for exactly the three recurring source-ingestion schedules:

```text
scheduled_ingestion_enabled=true   -> ENABLED
scheduled_ingestion_enabled=false  -> DISABLED
```

with the retained Scheduler delivery budget:

```text
maximum_event_age_in_seconds = 3600
maximum_retry_attempts       = 2
```

The live post-merge experiment proved an exact three-resource disable/verify/re-enable cycle and final Terraform convergence without creating or destroying resources.

This control is deliberately a **scheduled-ingestion pause**, not a global kill switch.

```text
scheduler pause != global workload termination
pause request != applied AWS state
Terraform apply success != independent AWS state verification
bounded retry != guaranteed delivery
failure destination != successful recovery
model token budget != tenant quota
```

### Documentation authority

The accumulated EN/PT-BR architecture baselines are synchronized with the retained platform. Documentation synchronization does not redefine runtime authority; ADRs, immutable evidence, protected merges, provider reads, and deterministic code remain the proof sources for the underlying controls.

## Original gap disposition

The Gate 17.1 observed gaps are closed or explicitly deferred as follows:

```text
SEC17-CICD-001  required-status enforcement         CLOSED / Gate 17.2
SEC17-CICD-003  persisted checkout credentials     CLOSED / Gate 17.2
SEC17-IAM-002   EPSS plan/write authority mismatch CLOSED / Gate 17.2
SEC17-IAM-003   historical AgentCore shared role   CLOSED / Gate 17.2
SEC17-SUPPLY-001 continuous security signals       CLOSED FOR RETAINED SCOPE / Gate 17.3
SEC17-DOC-001   architecture header/state drift    CLOSED / Gate 17.7
OPS17-001       recurring ingestion pause gap      CLOSED / Gate 17.6
```

`SEC17-SUPPLY-001` is closed for the retained requirement because continuous PR dependency review and Python CodeQL now exist. Automated dependency version updates and additional continuous `pip-audit` remain separate deferred choices, not silently implied by that closure.

## Explicit deferrals and non-claims

Phase 17 does **not** retain or claim:

```text
Dependabot version-update automation
additional continuous pip-audit
broad dependency upgrades
mandatory independent human approval for a single-maintainer portfolio repository
public WAF / edge rate limiting / tenant quotas without a public runtime
public HTTP application runtime
global platform kill switch
S3 event-chain emergency disablement
Lambda reserved-concurrency emergency kill switch
automatic alarm-triggered remediation
standing Inspector experiment IAM
Inspector activation solely to manufacture evidence
repository/runtime automatic correlation
runtime-risk composite scoring
public MCP runtime
public A2A peer runtime
AgentCore as the default OpsLens runtime
```

These items require a new concrete requirement, threat model, or evidence-backed hypothesis before implementation.

## Phase 18 entry boundary

Phase 18 — Evaluation, Cost & Portfolio Readiness may now begin.

It should consolidate existing measured evidence before adding new complexity. At minimum it must preserve these distinctions:

```text
measured value != derived estimate
unmeasured != zero
one experiment != production distribution
quality metric != security metric
latency metric != cost metric
scanner signal != vulnerability authority
repository risk != runtime exposure
portfolio summary != new technical authority
```

Phase 18 may improve discoverability, evidence maps, evaluation summaries, cost accounting, and portfolio presentation, but it must not create a new public runtime or broaden IAM merely to make the project look more complete.

## Authority impact of Gate 17.8

```text
AWS mutations:          0
new IAM permissions:    0
new IAM principals:     0
new AWS services:       0
runtime changes:        0
model invocations:      0
capability executions:  0
business authority:     unchanged
PR #89 modification:    0
```

## Canonical evidence

```text
labs/phase-17-closeout.md
labs/evidence/phase-17-closeout-v1.json
labs/phase-17-gate-17-6-closeout.md
labs/evidence/phase-17-gate-17-6-closeout-v1.json
labs/phase-17-gate-17-7-architecture-sync.md
labs/evidence/phase-17-gate-17-7-architecture-sync-v1.json
```

## Consequence

Phase 17 is complete at the smallest security boundary supported by evidence. The next project phase is Phase 18 — Evaluation, Cost & Portfolio Readiness.