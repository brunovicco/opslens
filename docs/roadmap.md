# OpsLens — Incremental Roadmap

_Last updated: 2026-09-10_

OpsLens advances in small, demonstrable, observable, reversible gates.

Default engineering loop:

```text
real gap
 -> issue
 -> architecture decision
 -> IAM / trust boundary when applicable
 -> small implementation or documentation slice
 -> success test
 -> meaningful failure test
 -> observability
 -> cost
 -> evidence
 -> draft PR
 -> exact-head CI
 -> protected squash merge
 -> post-merge verification
 -> issue closure
```

## Current roadmap status

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | AWS Foundation | ✅ Complete |
| 1 | EPSS Vertical Slice | ✅ Complete |
| 2 | Threat Intelligence Data Lake | ✅ Complete |
| 3 | Vulnerability Correlation Engine | ✅ Complete |
| 4 | Repository Intelligence | ✅ Complete |
| 5 | Risk Prioritization Engine | ✅ Complete |
| 6 | Semantic Query Layer | ✅ Complete |
| 7 | Knowledge Retrieval with Bedrock | ✅ Complete |
| 8 | Hybrid Retrieval | ✅ Complete |
| 9 | Public Analyze Your Repository | ✅ Complete |
| 10 | Observability & Operational Excellence | ✅ Complete |
| 11 | Single-Agent Baseline | ✅ Complete |
| 12 | Multi-Agent Architecture | ✅ Complete |
| 13 | MCP | ✅ Complete — bounded offline interoperability retained |
| 14 | Amazon Bedrock AgentCore | ✅ Complete — optional lab target retained; standing experiment IAM removed |
| 15 | A2A | ✅ Complete — bounded offline reference interoperability + official SDK conformance retained |
| 16 | Runtime Exposure with Amazon Inspector | ✅ Complete — read contract proven; zero current records; temporary IAM removed |
| 17 | Security Hardening | 🚧 In progress — Gates 17.1–17.5 complete; Gate 17.6 next |
| 18 | Evaluation, Cost & Portfolio Readiness | ⏳ Planned |

## Permanent engineering boundaries

> **Agents reason. Code verifies evidence.**

> **MCP is an interoperability boundary, not new business authority.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
capability invocation != execution result
MCP call admission != capability execution
MCP result projection != public runtime exposure
AgentCore hosting != business authorization
A2A message != capability authorization
A2A transport success != business/evidence truth
AWS authentication != Inspector read authorization
Inspector API success != runtime evidence presence
Inspector finding != repository finding
runtime evidence correlation != capability authorization
security control name != proven enforcement
historical workflow != inert workflow
plan-only intent != write-authority requirement
CI evidence != enforced merge gate
repository checkout != persisted Git credential requirement
OIDC authentication != authorization to reuse a shared deployment role
dependency finding != vulnerability applicability authority
code-scanning alert != runtime exploitability truth
security scan success != absence of vulnerabilities
scanner output != model authority
GitHub security permission != AWS authority
scanner platform prerequisite != scanner permission requirement
untrusted text != instruction authority
retrieved content != system/developer authority
failed/forged capability result != admissible business result
adversarial test success != proof of universal safety
log event suppression != trace response/error suppression
exception text != safe telemetry by default
trace metadata != business/evidence truth
loggable identifier != authorization
telemetry correlation != capability authorization
content-minimized failure log != execution result
redaction success != proof source content is non-sensitive
```

## Completed platform through Phase 16

Phases 0–10 established the AWS foundation, threat-intelligence ingestion, deterministic vulnerability correlation, repository intelligence, risk prioritization, bounded semantic query, Bedrock Knowledge Base retrieval with Amazon S3 Vectors, hybrid evidence, governed public analysis, and operational telemetry.

Phase 11 retained the measured single-agent Bedrock reference. Phase 12 retained deterministic specialization/handoff but rejected the measured two-model topology as default. Phase 13 retained bounded offline MCP interoperability. Phase 14 retained AgentCore only as an optional lab target and removed standing experiment IAM. Phase 15 retained bounded offline A2A reference interoperability plus an exact-source official SDK CI oracle without creating a public A2A runtime.

Phase 16 added a typed read-only Amazon Inspector evidence boundary without equating runtime evidence with repository-risk truth. The existing shared deployment role correctly failed with `AccessDeniedException`; a temporary dedicated two-action role then proved `ListCoverage` and `ListFindings` access with zero current records. The role was removed afterward and Terraform reconverged.

Canonical Phase 16 closeout:

```text
docs/adr/0063-phase16-runtime-exposure-closeout.md
labs/phase-16-closeout.md
labs/evidence/phase-16-closeout-v1.json
```

## Phase 17 — Security Hardening — IN PROGRESS

Purpose: evaluate the retained platform as an attacker and operator would, then harden only evidenced gaps while preserving deterministic authority and least privilege.

### Gate 17.1 — cross-cutting threat model and control-gap inventory — COMPLETE

Gate 17.1 established an evidence-first security inventory before new implementation authority.

Canonical evidence:

```text
docs/adr/0064-evidence-first-security-hardening-priorities.md
labs/phase-17-gate-17-1-threat-model.md
labs/evidence/phase-17-gate-17-1-threat-model-v1.json
```

The initial highest-priority gaps were protected-main CI enforcement, EPSS plan/execution authority separation, and historical AgentCore shared-role reuse. Continuous dependency/code scanning was a medium-priority gap. Architecture-header drift remains a lower-priority documentation gap.

### Gate 17.2 — CI/CD and workflow authority hardening — COMPLETE

Gate 17.2 added one universal protected-main security context and froze repository-wide workflow authority:

```text
required PR context:                         Repository security invariants
external actions:                            full 40-hex SHA pins
checkout persisted credentials:              disabled
pull_request_target/workflow_run:             rejected by default
EPSS plan identity:                          OpsLensEpssHistoryEvidenceRole
EPSS execution identity:                     OpsLensEpssHistoryCoordinatorRole
21600-second STS session:                    full-backfill execute only
historical AgentCore mutating workflow:      retired / fail-closed
```

The active `Protect main` ruleset (`20873628`) now requires `Repository security invariants`. A later direct write attempt to `main` was rejected, independently proving enforcement.

Canonical records:

```text
docs/adr/0065-ci-cd-and-workflow-authority-hardening.md
labs/phase-17-gate-17-2-workflow-authority-hardening.md
labs/evidence/phase-17-gate-17-2-workflow-authority-hardening-v1.json
labs/phase-17-gate-17-2-main-ruleset-enforcement.md
labs/evidence/phase-17-gate-17-2-main-ruleset-enforcement-v1.json
```

### Gate 17.3 — dependency and code-scanning hardening — COMPLETE

Gate 17.3 retained two bounded GitHub-native security signals:

```text
Dependency Review
  action:            actions/dependency-review-action
  release:           v5.0.0
  exact SHA:         a1d282b36b6f3519aa1f3fc636f609c47dddb294
  fail threshold:    high
  permission:        contents: read

CodeQL / Python
  action:            github/codeql-action
  release line:      v4.38.0
  exact SHA:         b96794f015dfd88f77b49b1c93e0fa7110f94c63
  permissions:       contents: read + security-events: write
```

The first Dependency Review attempt identified a GitHub platform prerequisite rather than an authority gap: the repository Dependency graph was disabled. After a human enabled it, the unchanged read-only workflow succeeded. No permission widening occurred.

Final exact PR-head CI:

```text
head:                           f9ee70d772d28987c45008b723e3efc07b65680e
Repository security invariants: 34424002745 / #19 / SUCCESS
Dependency Review:              34424002767 / #4  / SUCCESS
CodeQL / Python:                34424003077 / #4  / SUCCESS
```

Implementation PR #261 was protected-squash merged as:

```text
b3f4a11df1a826c850cc16f1a4e0dd44efb3edd3
```

Canonical records:

```text
docs/adr/0066-bounded-dependency-and-code-scanning-signals.md
labs/phase-17-gate-17-3-dependency-code-scanning.md
labs/evidence/phase-17-gate-17-3-dependency-code-scanning-v1.json
labs/phase-17-gate-17-3-closeout.md
labs/evidence/phase-17-gate-17-3-closeout-v1.json
```

Deferred from Gate 17.3:

```text
Dependabot version-update automation: DEFER
additional continuous pip-audit:      DEFER
broad dependency upgrades:            NOT AUTHORIZED
```

### Gate 17.4 — application input / prompt-injection / tool-abuse adversarial tests — COMPLETE

Gate 17.4 retained a dedicated offline attacker-oriented regression suite over real OpsLens boundaries rather than introducing speculative guardrails.

Evaluation coverage:

```text
ADV17-PUBLIC  public request admission abuse
ADV17-PROMPT  direct + indirect prompt injection
ADV17-TOOL    single/multi-agent capability widening attempts
ADV17-RESULT  forged result binding
ADV17-MCP     dynamic/cross-capability MCP tool abuse
ADV17-A2A     A2A reference authority smuggling
ADV17-COST    input/call/retry/fallback amplification
```

Retained implementation:

```text
tests/security_hardening/test_adversarial_boundaries.py
.github/workflows/adversarial-security-ci.yml
```

The first retained dataset contains eight deterministic cases across seven threat classes. Every case matched its expected reject or bounded disposition, so no business-logic redesign was justified by observed evidence.

Final exact implementation PR-head CI:

```text
head:                           60010d4fcb5d6142c9748bbf764fb074dc3a4dc8
Adversarial Security CI:        34426092786 / #5  / SUCCESS
Repository security invariants: 34426092824 / #25 / SUCCESS
Dependency Review:              34426092798 / #10 / SUCCESS
CodeQL / Python:                34426092795 / #12 / SUCCESS
```

Implementation PR #264 was protected-squash merged as:

```text
cfad2680ca9e1977c754977ea58f9ab8865601dd
```

Canonical records:

```text
docs/adr/0067-bounded-adversarial-authority-regression-suite.md
labs/phase-17-gate-17-4-adversarial-boundaries.md
labs/evidence/phase-17-gate-17-4-adversarial-boundaries-v1.json
labs/phase-17-gate-17-4-closeout.md
labs/evidence/phase-17-gate-17-4-closeout-v1.json
```

Retained authority posture:

```text
Adversarial Security CI permission:          contents: read
AWS/OIDC authority:                          none
model invocations during Gate 17.4:          0
capability executions during Gate 17.4:      0
new model/tool authority:                    none
live-model jailbreak as authority proof:     rejected
```

`adversarial test success != proof of universal safety` remains a permanent interpretation boundary.

### Gate 17.5 — sensitive-data / logging / telemetry hardening — COMPLETE

Gate 17.5 began from repository evidence and closed two concrete content-bearing telemetry gaps:

```text
TRACE17-001  bare Powertools Lambda tracer response/error capture
LOG17-001    implicit active exception/traceback serialization through logger.exception
```

Retained implementation:

```text
Powertools Lambda handlers:                   12
logger input-event capture:                    disabled / log_event=False
tracer response capture:                       disabled / capture_response=False
tracer error capture:                          disabled / capture_error=False
shared active exception/traceback logging:     disabled
shared failure logger:                         bounded logger.error
repository verifier:                           scripts/verify_telemetry_safety.py
regression test:                               tests/unit/shared/observability/test_powertools_telemetry_safety.py
```

Final exact implementation PR-head validation:

```text
head:                           5ad6e7d9aae224d188f11b1f0bae27fc25ea59df
Security Hardening CI:          34429102027 / #30 / SUCCESS
Operational Observability CI:   34429102108 / #23 / SUCCESS
Dependency Review:              34429102025 / #15 / SUCCESS
CodeQL / Python:                34429102142 / #19 / SUCCESS
```

The repository-wide telemetry verifier emitted:

```text
telemetry_safety_invariants=PASS handlers=12
```

Implementation PR #268 was protected-squash merged as:

```text
9e967acdd1a5ae611a3a1db47aee164272d11380
```

Canonical records:

```text
docs/adr/0068-content-minimized-lambda-telemetry.md
labs/phase-17-gate-17-5-telemetry-safety.md
labs/evidence/phase-17-gate-17-5-telemetry-safety-v1.json
labs/phase-17-gate-17-5-closeout.md
labs/evidence/phase-17-gate-17-5-closeout-v1.json
```

Retained authority posture:

```text
AWS/IAM mutation:                  none
new observability vendor/service:  none
new public runtime:                none
new model/tool authority:          none
business/evidence authority move:  none
PR #89 modification:               none
```

`log event suppression != trace response/error suppression` and `exception text != safe telemetry by default` are permanent interpretation boundaries.

### Gate 17.6 — operational recovery / kill-switch / abuse-cost controls — NEXT

Begin from concrete retained runtime and operational evidence. The first slice should inventory which workloads can incur repeated calls, writes, retries, or costs; which already have deterministic stop/retry bounds; and where an operator can safely halt or recover execution without creating broader authority.

Minimum evaluation targets:

```text
existing retry/fallback/execution budgets
scheduled/manual workflow execution authority
Lambda asynchronous retry/failure destinations where retained
Bedrock/model call budgets and cost-amplification paths
bounded cancellation/disable mechanisms already present
recovery from partial writes or failed deterministic evidence admission
operator actions that could become over-broad kill-switch authority
re-entry and rollback evidence after an operational stop
```

Gate 17.6 must not invent a global kill switch merely for portfolio completeness. Any new stop/recovery mechanism must correspond to a concrete retained runtime risk and must preserve least privilege, deterministic evidence, and reversibility.

### Candidate later gates — EVIDENCE-DRIVEN

```text
17.7 architecture-document synchronization if still pending
17.8 Security Hardening closeout
```

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure-path, architecture, security, and portfolio evidence after Phase 17 closes.

## Deferred cross-project integration

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains separate Governed LLM Gateway work and must not be modified or merged as a side effect of Phase 17.
