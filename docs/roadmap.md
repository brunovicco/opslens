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
| 16 | Runtime Exposure with Amazon Inspector | 🚧 In progress — Gate 16.1 complete; read-only discovery next |
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

Canonical prior closeouts remain in ADRs, labs, immutable evidence, and Git history.

## Phase 16 — Runtime Exposure with Amazon Inspector — IN PROGRESS

Purpose: add independent runtime evidence while preserving:

> **Repository Risk != Runtime Exposure.**

### Gate 16.1 — Inspector capability fit / authority — COMPLETE

Current Inspector capability facts used by this gate:

```text
read APIs selected:       ListCoverage / ListFindings
finding types:            NETWORK_REACHABILITY / PACKAGE_VULNERABILITY / CODE_VULNERABILITY
network reachability:     EC2-only in current Inspector contract
```

Evidence taxonomy:

```text
runtime_coverage
runtime_vulnerability
network_reachability
code_vulnerability
```

These are intentionally independent. A Lambda/ECR package finding is runtime-resource vulnerability evidence, not network-reachability evidence.

Decision:

```text
Amazon Inspector capability fit:       YES
runtime evidence source:               INDEPENDENT AUTHORITY
first experiment:                      READ-ONLY DISCOVERY ONLY
allowed APIs:                          ListCoverage + ListFindings
Inspector activation/change:           NOT AUTHORIZED
new IAM:                               NOT AUTHORIZED
hybrid routing integration:            NOT AUTHORIZED
repository/runtime auto-correlation:    NOT AUTHORIZED
```

Target authority boundary:

```text
Amazon Inspector read response
 -> source-preserving raw snapshot
 -> exact account / region / pagination context
 -> deterministic resource/finding admission
 -> type-specific runtime evidence
 -> RuntimeEvidenceEnvelope
 -> correlate only when identity is provable
 -> otherwise preserve independent evidence / fail closed
```

Records:

```text
docs/adr/0060-bounded-amazon-inspector-runtime-evidence-fit.md
labs/phase-16-gate-16-1-inspector-runtime-evidence-fit.md
labs/evidence/phase-16-gate-16-1-inspector-runtime-evidence-fit-v1.json
```

### Gate 16.2 — bounded read-only Inspector discovery — NEXT / AUTHORIZED

Run exactly one discovery experiment against the existing dev account using existing credentials first.

Allowed cloud calls:

```text
inspector2:ListCoverage
inspector2:ListFindings
```

Required behavior:

```text
read only
no automatic IAM widening
AccessDenied is valid terminal evidence
zero resources/findings is valid evidence
preserve pagination/source identity
measure API outcome, counts, latency, retries
AWS mutations = 0
new IAM = 0
model invocations = 0
capability executions = 0
```

Not authorized:

```text
Enable/Disable Inspector
ECR scanning changes
EC2 scan-mode changes
Lambda scan activation
EventBridge integration
suppression filters
hybrid runtime_exposure routing
runtime-risk composite scoring
model synthesis
repository/runtime automatic correlation
```

A later gate may propose a minimum read-only IAM boundary only if the measured Gate 16.2 result proves it is necessary. It may not be silently created as part of discovery.

## Phase 17 — Security Hardening — PLANNED

Cross-cutting IAM, data protection, abuse resistance, dependency, threat-model, and operational hardening.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure-path, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains separate Governed LLM Gateway work and must not be modified or merged as a side effect of Phase 16.
