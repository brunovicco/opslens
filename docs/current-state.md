# OpsLens — Current State

_Last updated: 2026-09-10_

This document is the authoritative implementation checkpoint for OpsLens. Detailed historical evidence remains in ADRs, gate labs, immutable evidence artifacts, protected PRs, workflow runs, provider reads, and Git history.

## Status

```text
Phase 0    AWS Foundation                                      COMPLETE
Phase 1    EPSS Vertical Slice                                 COMPLETE
Phase 2    Threat Intelligence Data Lake                       COMPLETE
Phase 3    Vulnerability Correlation Engine                    COMPLETE
Phase 4    Repository Intelligence                             COMPLETE
Phase 5    Risk Prioritization Engine                          COMPLETE
Phase 6    Semantic Query Layer                                COMPLETE
Phase 7    Knowledge Retrieval with Bedrock                    COMPLETE
Phase 8    Hybrid Retrieval                                    COMPLETE
Phase 9    Public Analyze Your Repository                      COMPLETE
Phase 10   Observability & Operational Excellence              COMPLETE
Phase 11   Single-Agent Baseline                               COMPLETE
Phase 12   Multi-Agent Architecture                            COMPLETE
Phase 13   MCP                                                 COMPLETE
Phase 14   Amazon Bedrock AgentCore                            COMPLETE
Phase 15   A2A                                                 COMPLETE
Phase 16   Runtime Exposure with Amazon Inspector              COMPLETE
Phase 17   Security Hardening                                  COMPLETE
  Gate 17.1 Cross-cutting threat/control-gap inventory         COMPLETE
  Gate 17.2 CI/CD and workflow authority hardening             COMPLETE / REQUIRED CONTEXT ENFORCED
  Gate 17.3 Dependency and code-scanning hardening             COMPLETE / DEPENDENCY REVIEW + CODEQL
  Gate 17.4 Adversarial authority-boundary regression          COMPLETE / 8 CASES / 7 THREAT CLASSES
  Gate 17.5 Sensitive-data / logging / telemetry hardening     COMPLETE / 12 LAMBDA HANDLERS HARDENED
  Gate 17.6 Operational recovery / abuse-cost controls         COMPLETE / MEASURED PAUSE-RESUME PROOF
  Gate 17.7 Architecture documentation synchronization         COMPLETE / SEC17-DOC-001 CLOSED
  Gate 17.8 Security Hardening closeout                        COMPLETE BY CLOSEOUT PR
Phase 18   Evaluation, Cost & Portfolio Readiness              NEXT
```

## Permanent architecture boundaries

> **Agents reason. Code verifies evidence.**

> **MCP is an interoperability boundary, not new business authority.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
capability invocation != execution result
execution result != admitted evidence
MCP call admission != capability execution
MCP result projection != public runtime exposure
AgentCore hosting != business authorization
A2A message != capability authorization
A2A transport success != business/evidence truth
A2A SDK acceptance != OpsLens admission authority
AWS authentication != Inspector read authorization
Inspector API success != runtime evidence presence
Inspector finding != repository finding
runtime evidence correlation != capability authorization
CI evidence != enforced merge gate
historical workflow != inert workflow
repository checkout != persisted Git credential requirement
OIDC authentication != authorization to reuse a shared deployment role
dependency finding != vulnerability applicability authority
code-scanning alert != runtime exploitability truth
security scan success != absence of vulnerabilities
scanner output != model authority
untrusted text != instruction authority
retrieved content != system/developer authority
failed/forged capability result != admissible business result
adversarial test success != proof of universal safety
log event suppression != trace response/error suppression
exception text != safe telemetry by default
trace metadata != business/evidence truth
telemetry correlation != capability authorization
scheduler pause != global workload termination
scheduler state != business/evidence authority
pause request != applied AWS state
Terraform apply success != independent AWS state verification
bounded retry != guaranteed delivery
model token budget != tenant quota
historical evidence != standing authority
```

Deterministic code remains authoritative for evidence identity, vulnerability applicability, Risk Policy v1, structured-query compilation, retrieval admission, capability authorization, executable input binding, result admission, handoff admission, MCP admission/projection, A2A reference identity/resolution/admission, retry/fallback policy, and runtime-evidence admission/correlation.

## Retained measured reasoning reference — Phase 11

```text
provider:                     Amazon Bedrock Converse
model/profile:                us.anthropic.claude-haiku-4-5-20251001-v1:0
quality:                      6/6
model invocations:            6
input/output/total tokens:    3291 / 104 / 3395
provider latency median:      809.5 ms
client elapsed median:        977.5 ms
SDK retries:                  0
capability executions:        0
derived six-case cost:        USD 0.0041921
```

Phase 12 retained deterministic specialization/handoff but rejected the measured two-model topology as the default because it added calls, tokens, latency, and cost without measured quality lift.

## Retained interoperability/runtime posture

### Phase 13 — MCP

```text
mcp-capability-exposure:v1          RETAIN
mcp-capability-execution:v1         RETAIN
mcp-result-projection:v1            RETAIN
public/network MCP runtime          DO NOT RETAIN / NOT CREATED
```

### Phase 14 — AgentCore

```text
Phase 11 direct Bedrock reasoning:          RETAIN / DEFAULT
AgentCore implementation/evidence:          RETAIN AS OPTIONAL LAB TARGET
AgentCore managed Runtime as default:        DO NOT RETAIN
standing AgentCore Runtime resources:        NONE
standing experiment-specific GitHub IAM:    REMOVED
historical mutating workflow:                RETIRED / FAIL-CLOSED
```

### Phase 15 — A2A

```text
A2A release:                                   1.0.0
first retained binding:                       JSONRPC / SendMessage
content-addressed A2AReference:               RETAIN
strict raw JSON admission:                    RETAIN
official a2a-sdk exact-source CI oracle:      RETAIN FOR CI
public/network A2A runtime:                    DO NOT CREATE
standing A2A cloud resources / IAM:           NONE
```

### Phase 16 — Amazon Inspector runtime evidence

Measured read-only discovery:

```text
workflow:                    Inspector Read-Only Discovery
run:                         34414116549 / #2
result:                      SUCCESS
ListCoverage:                SUCCESS / 1 page / 0 records / 0 retries
ListFindings:                SUCCESS / 1 page / 0 records / 0 retries
AWS mutations:               0
model invocations:           0
capability executions:       0
```

Final retention:

```text
Inspector read-only domain/adapter contract:   RETAIN
historical discovery workflow:                 RETAIN / DISABLED BY DEFAULT
measured zero-record evidence:                 RETAIN
standing Inspector discovery IAM:              NONE
Inspector activation/configuration:             NOT CREATED
repository/runtime automatic correlation:       NOT CREATED
runtime-risk composite scoring:                 NOT CREATED
```

Canonical Phase 16 closeout:

```text
docs/adr/0063-phase16-runtime-exposure-closeout.md
labs/phase-16-closeout.md
labs/evidence/phase-16-closeout-v1.json
```

## Phase 17 — Security Hardening — COMPLETE

Phase 17 used an evidence-first threat inventory and closed only observed gaps. It did not adopt speculative controls solely for checklist coverage.

### Gate 17.1 — threat/control-gap inventory

The initial actionable gaps covered protected-main required-status enforcement, unnecessary checkout credentials, EPSS plan/execution authority mismatch, historical AgentCore shared-role reuse, continuous repository security signals, and stale accumulated architecture status.

Canonical records:

```text
docs/adr/0064-evidence-first-security-hardening-priorities.md
labs/phase-17-gate-17-1-threat-model.md
labs/evidence/phase-17-gate-17-1-threat-model-v1.json
```

### Gate 17.2 — CI/CD and workflow authority

Retained controls:

```text
required protected-main context:          Repository security invariants
external actions:                         full 40-hex SHA pins
checkout persisted credentials:           disabled where unnecessary
pull_request_target/workflow_run:          rejected by default
EPSS planning identity:                   read-only evidence role
EPSS execution identity:                  separate coordinator role
21600-second STS session:                 full-backfill execute path only
historical AgentCore mutation workflow:   retired / fail-closed
```

The protected-main ruleset independently rejected a direct write, proving enforcement rather than documentation-only policy.

### Gate 17.3 — dependency and code scanning

```text
Dependency Review:  retained / pull_request / high severity threshold
CodeQL Python:      retained / PR + main + weekly + manual
AWS/OIDC authority: none for scanner workflows
```

Dependabot version updates and additional continuous `pip-audit` remain deferred; their absence is not hidden by the Gate 17.3 closure.

### Gate 17.4 — adversarial authority regression

```text
cases:                 8
threat classes:        7
AWS/OIDC authority:    none
model invocations:     0
capability executions: 0
```

Coverage includes public-input abuse, direct/indirect prompt injection, capability widening, forged result evidence, MCP abuse, A2A reference smuggling, and amplification attempts.

### Gate 17.5 — telemetry hardening

Across 12 retained Powertools Lambda handlers:

```text
log event auto-capture:                 DISABLED
trace response auto-capture:            DISABLED
trace error auto-capture:               DISABLED
implicit active-exception traceback:    DISABLED
repository telemetry safety verifier:   RETAIN
```

### Gate 17.6 — operational recovery / abuse-cost controls

Retained recurring trigger set:

```text
aws_scheduler_schedule.epss_daily
aws_scheduler_schedule.kev_daily
aws_scheduler_schedule.nvd_incremental_hourly
```

Retained Terraform control:

```text
scheduled_ingestion_enabled=true   -> ENABLED
scheduled_ingestion_enabled=false  -> DISABLED
```

Retained Scheduler delivery budget:

```text
maximum_event_age_in_seconds = 3600
maximum_retry_attempts       = 2
```

Measured live proof:

```text
default convergence                 PASS
pause plan/apply                    0 add / 3 change / 0 destroy
independent Scheduler reads         3/3 DISABLED
paused Terraform convergence        PASS
resume plan/apply                   0 add / 3 change / 0 destroy
independent Scheduler reads         3/3 ENABLED
final default Terraform convergence PASS
```

No resource was created or destroyed. The control remains a scheduled-ingestion pause, not a global workload kill switch.

Canonical closeout:

```text
docs/adr/0069-bounded-scheduled-ingestion-pause.md
labs/phase-17-gate-17-6-closeout.md
labs/evidence/phase-17-gate-17-6-closeout-v1.json
```

### Gate 17.7 — architecture synchronization

`SEC17-DOC-001` is closed. `docs/architecture.md` and `docs/architecture.pt-br.md` describe the same retained system through the Phase 17 security controls.

```text
PR:                #276
exact head:        ea0460e549dd1b904d139632bfc2988671e23880
protected merge:   3938c6469a979f5b574755ce9fd56a56523626dc
Security Hardening CI: 34474712369 / #34 / SUCCESS
Dependency Review:     34474712371 / #19 / SUCCESS
CodeQL / Python:       34474712380 / #27 / SUCCESS
```

### Phase 17 closeout retention

```text
protected-main security enforcement:          RETAIN
bounded dependency/code security signals:     RETAIN
adversarial authority regression:             RETAIN
content-minimized Lambda telemetry:            RETAIN
bounded scheduled-ingestion pause:             RETAIN
operational recovery runbook:                 RETAIN
synchronized EN/PT-BR architecture:            RETAIN
```

Explicitly deferred/not-created:

```text
Dependabot version-update automation
additional continuous pip-audit
broad dependency upgrades
mandatory independent approval until governance requires it
public WAF / rate limiting / tenant quota without public runtime
public HTTP runtime
global kill switch
S3 event-chain kill switch
Lambda concurrency kill switch
automatic alarm-triggered remediation
standing Inspector experiment IAM
Inspector activation to manufacture evidence
public MCP/A2A runtime
AgentCore as default OpsLens runtime
```

Canonical Phase 17 closeout:

```text
docs/adr/0070-phase17-security-hardening-closeout.md
labs/phase-17-closeout.md
labs/evidence/phase-17-closeout-v1.json
```

## Next — Phase 18

Proceed to **Phase 18 — Evaluation, Cost & Portfolio Readiness**.

Start with consolidation rather than a new runtime. Phase 18 must distinguish measured values, derived estimates, and unmeasured dimensions; preserve independent quality/security/latency/cost metrics; and avoid turning dev/lab evidence into production claims.

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work and must stay untouched unless explicitly resumed in a separate scope.
