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
| 17 | Security Hardening | 🚧 In progress — Gates 17.1–17.3 complete; Gate 17.4 next |
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

### Gate 17.4 — application input / prompt-injection / tool-abuse adversarial tests — NEXT

The next gate should attack already-retained public and agentic boundaries before creating any new model/runtime authority. Minimum evaluation targets:

```text
public repository/request admission
semantic planner proposal-only boundary
retrieved-content prompt-injection resistance
single/multi-agent capability authorization
MCP raw admission / result projection
A2A raw admission / reference resolution
malformed or contradictory tool/result evidence
cost-amplification attempts within bounded model-call budgets
```

Gate 17.4 should add adversarial fixtures and deterministic pass/fail evidence first. New AWS IAM, new public runtime surfaces, or new model/tool authority are not implied by this gate.

### Candidate later gates — EVIDENCE-DRIVEN

```text
17.5 sensitive-data / logging / telemetry hardening
17.6 operational recovery / kill-switch / abuse-cost controls
17.7 architecture-document synchronization if still pending
17.8 Security Hardening closeout
```

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure-path, architecture, security, and portfolio evidence after Phase 17 closes.

## Deferred cross-project integration

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains separate Governed LLM Gateway work and must not be modified or merged as a side effect of Phase 17.
