# OpsLens — Incremental Roadmap

_Last updated: 2026-09-09_

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
| 17 | Security Hardening | 🚧 In progress — Gate 17.1 complete; Gate 17.2 next |
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
AuthorizedAgentAction != capability invocation
capability invocation != execution result
MCP call admission != capability execution
MCP result projection != public runtime exposure
AgentCore hosting != business authorization
runtime deployment != runtime-exposure truth
A2A message != capability authorization
A2A transport success != business/evidence truth
A2A SDK acceptance != OpsLens admission authority
AWS authentication != Inspector read authorization
Inspector API success != runtime evidence presence
Inspector coverage != vulnerability finding
Inspector finding != repository finding
Inspector package match != deployed application ownership
Inspector resource presence != network exposure
Inspector PACKAGE_VULNERABILITY != NETWORK_REACHABILITY
Inspector score != Risk Policy v1
Inspector EPSS != OpsLens source-authority replacement
Inspector finding status != business remediation state
Inspector evidence != model authority
runtime evidence correlation != capability authorization
security control name != proven enforcement
historical workflow != inert workflow
plan-only intent != write-authority requirement
CI evidence != enforced merge gate
```

## Completed platform through Phase 16

Phases 0–10 established the AWS foundation, threat-intelligence ingestion, deterministic vulnerability correlation, repository intelligence, risk prioritization, bounded semantic query, Bedrock Knowledge Base retrieval with Amazon S3 Vectors, hybrid evidence, governed public analysis, and operational telemetry.

Phase 11 retained the measured single-agent Bedrock reference. Phase 12 retained deterministic specialization/handoff but rejected the measured two-model topology as default. Phase 13 retained bounded offline MCP interoperability. Phase 14 retained AgentCore only as an optional lab target and removed standing experiment IAM. Phase 15 retained bounded offline A2A reference interoperability plus an exact-source official SDK CI oracle, without creating a public A2A runtime.

Phase 16 added a typed read-only Amazon Inspector evidence boundary without equating runtime evidence with repository-risk truth. The existing shared deployment role correctly failed with `AccessDeniedException`; one temporary dedicated two-action role was then created for a single measured rerun. `ListCoverage` and `ListFindings` both succeeded with one page and zero records. The temporary role was subsequently removed with an exact `0 add / 0 change / 2 destroy` cleanup and a convergent post-apply plan.

Final Phase 16 retention:

```text
Inspector read-only domain/adapter contract:   RETAIN
historical discovery workflow:                 RETAIN / DISABLED BY DEFAULT
measured zero-record evidence:                 RETAIN
standing Inspector discovery IAM:              NONE
Inspector activation/configuration:             NOT CREATED
hybrid runtime_exposure routing:                NOT CREATED
repository/runtime automatic correlation:       NOT CREATED
runtime-risk composite scoring:                 NOT CREATED
model synthesis over Inspector evidence:        NOT CREATED
```

Canonical Phase 16 closeout:

```text
docs/adr/0063-phase16-runtime-exposure-closeout.md
labs/phase-16-closeout.md
labs/evidence/phase-16-closeout-v1.json
```

## Phase 17 — Security Hardening — IN PROGRESS

Purpose: evaluate the retained platform as an attacker and operator would, then harden only evidenced gaps while preserving deterministic authority and least privilege.

### Gate 17.1 — cross-cutting threat model and control-gap inventory — COMPLETE

Gate 17.1 reviewed retained code, IaC, workflows, GitHub ruleset behavior, historical runtime experiments, protocol boundaries, and current security guidance before authorizing any new implementation authority.

Canonical evidence:

```text
labs/evidence/phase-17-gate-17-1-threat-model-v1.json
docs/adr/0064-evidence-first-security-hardening-priorities.md
labs/phase-17-gate-17-1-threat-model.md
```

High-priority gaps:

```text
SEC17-CICD-001  main ruleset lacks required CI status checks
SEC17-IAM-002   EPSS plan-only paths assume write/invoke-capable authority
SEC17-IAM-003   historical AgentCore workflow retains shared deploy-role mutation authority
```

Medium-priority gaps:

```text
SEC17-CICD-003  checkout credentials persist where authenticated git is unnecessary
SEC17-SUPPLY-001 continuous repository-local dependency security automation not observed
```

Low-priority gap:

```text
SEC17-DOC-001   architecture header/current-phase documentation drift
```

Gate 17.1 also records already-proven controls so Phase 17 does not rebuild them without evidence: immutable main-only GitHub OIDC trust, full-SHA action pinning in sampled workflows, bounded public input/acquisition, proposal-only semantic planning, untrusted RAG content handling, deterministic agent authorization/result admission, strict MCP/A2A raw admission, content-minimized telemetry, and bounded model-call budgets.

### Gate 17.2 — CI/CD and workflow authority hardening — NEXT / AUTHORIZED

Gate 17.2 is intentionally narrow. It may change repository/workflow behavior only where Gate 17.1 proved an authority gap.

Authorized repository scope:

```text
freeze repository-wide external-action full-SHA invariant
reject privileged pull_request_target/workflow_run triggers unless separately authorized
set checkout persist-credentials:false where authenticated git is unnecessary
make EPSS history plan-only paths use read-only/no-write credentials
limit 21600-second EPSS coordinator session to actual execution only
disable historical AgentCore mutating workflow by default until dedicated minimum authority is explicitly recreated
define exact required CI status contexts for main
```

Human/platform boundary:

```text
change GitHub main ruleset required status checks
```

Not authorized in Gate 17.2:

```text
AWS IAM mutation
new AWS service
new public runtime
Inspector reactivation
dependency-platform enablement
PR #89 modification
```

### Candidate later gates — EVIDENCE-DRIVEN

The Gate 17.1 inventory justifies evaluating these later slices, but they remain separate decisions:

```text
17.3 dependency / dependency-review / code-scanning hardening
17.4 application input / prompt-injection / tool-abuse adversarial tests
17.5 sensitive-data / logging / telemetry hardening
17.6 operational recovery / kill-switch / abuse-cost controls
17.7 architecture-document synchronization if still pending
17.8 Security Hardening closeout
```

Later gates must preserve the same distinction between a missing repository artifact, a platform setting that is not observable, a real implementation gap, and a control already proven by earlier phases.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure-path, architecture, security, and portfolio evidence after Phase 17 closes.

## Deferred cross-project integration

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains separate Governed LLM Gateway work and must not be modified or merged as a side effect of Phase 16 or Phase 17.
