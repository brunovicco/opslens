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
| 16 | Runtime Exposure with Amazon Inspector | 🚧 In progress — read boundary proven; zero current evidence; temporary IAM teardown pending |
| 17 | Security Hardening | ⏳ Planned |
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
```

## Completed platform through Phase 15

Phases 0–10 established the AWS foundation, threat-intelligence ingestion, deterministic vulnerability correlation, repository intelligence, risk prioritization, bounded semantic query, Bedrock Knowledge Base retrieval with Amazon S3 Vectors, hybrid evidence, governed public analysis, and operational telemetry.

Phase 11 retained the measured single-agent Bedrock reference. Phase 12 retained deterministic specialization/handoff but rejected the measured two-model topology as default. Phase 13 retained bounded offline MCP interoperability. Phase 14 retained AgentCore only as an optional lab target and removed standing experiment IAM. Phase 15 retained bounded offline A2A reference interoperability plus an exact-source official SDK CI oracle, without creating a public A2A runtime.

## Phase 16 — Runtime Exposure with Amazon Inspector — IN PROGRESS

Purpose: add independent runtime evidence while preserving:

> **Repository Risk != Runtime Exposure.**

### Gate 16.1 — capability fit / authority — COMPLETE

Amazon Inspector was accepted as an independent evidence authority. The first experiment was limited to:

```text
ListCoverage
ListFindings
```

No activation/configuration change, hybrid routing, runtime-risk scoring, model synthesis, or automatic repository/runtime correlation was authorized.

### Gate 16.2 — existing-role discovery — COMPLETE / BLOCKED_BY_EXISTING_IAM

```text
run:                 34411934819 / #1
ListCoverage:        ACCESS_DENIED
ListFindings:        NOT_ATTEMPTED / fail-closed
AWS mutations:       0
new IAM:             0
```

The result proved that GitHub OIDC authentication did not imply Inspector read authorization.

### Gate 16.3 — minimum read-only IAM decision — COMPLETE

```text
widen OpsLensGitHubDeployRole:                 REJECT
dedicated temporary Inspector discovery role: ACCEPT
stop before one bounded rerun:                 REJECT
```

The accepted role was limited to `ListCoverage` and `ListFindings`, `Resource = "*"`, `aws:RequestedRegion == us-east-1`, the immutable main-branch OIDC subject, a 900-second requested workflow session, and mandatory teardown.

### Gate 16.4 — temporary role + measured rerun — COMPLETE

Human bootstrap created exactly the temporary role/policy:

```text
plan:  2 add / 0 change / 0 destroy
apply: 2 added / 0 changed / 0 destroyed
```

One main-only rerun then measured:

```text
run:                      34414116549 / #2
job:                      102675000098
workflow conclusion:      success
experiment result:        SUCCESS
client elapsed:           465.877452 ms
ListCoverage:             SUCCESS / 1 page / 0 records
ListFindings:             SUCCESS / 1 page / 0 records
SDK retries:              0
AWS mutations:            0
new IAM during discovery: 0
model invocations:        0
capability executions:    0
```

The dedicated boundary was sufficient, but the current dev account returned no Inspector coverage or finding records. That result is current-account evidence only; it does not prove Inspector is disabled or valueless elsewhere.

Decision:

```text
Inspector read-only adapter/contract:        RETAIN
measured zero-evidence result:               RETAIN
standing Inspector discovery IAM:            DO NOT RETAIN / REMOVE
Inspector activation/configuration change:   DO NOT CREATE IN PHASE 16
repository/runtime automatic correlation:    DO NOT CREATE
runtime-risk composite scoring:              DO NOT CREATE
model synthesis over Inspector evidence:     DO NOT CREATE
```

Records:

```text
docs/adr/0062-retain-inspector-read-contract-without-standing-iam-or-scan-activation.md
labs/phase-16-gate-16-4-inspector-readonly-rerun.md
labs/evidence/phase-16-gate-16-4-inspector-readonly-rerun-v1.json
```

### Gate 16.5 — temporary Inspector IAM teardown — CURRENT

Repository cleanup removes the temporary role/policy from Terraform desired state and disables the historical discovery workflow by default unless a future explicitly authorized temporary role is confirmed.

After protected merge, the human bootstrap plane must produce and review an exact cleanup plan. Expected target:

```text
0 add / 0 change / 2 destroy
```

Only these addresses may be destroyed:

```text
aws_iam_role.github_actions_inspector_discovery
aws_iam_role_policy.github_actions_inspector_discovery
```

After apply, require a fresh convergent plan and independent verification that the temporary role is absent while `OpsLensGitHubDeployRole` remains present without Inspector authority.

Only after that evidence is immutable may Phase 16 close and Phase 17 begin.

## Phase 17 — Security Hardening — PLANNED

Cross-cutting IAM, data protection, abuse resistance, dependency, threat-model, and operational hardening.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure-path, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains separate Governed LLM Gateway work and must not be modified or merged as a side effect of Phase 16.
