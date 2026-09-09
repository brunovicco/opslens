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
| 17 | Security Hardening | ▶️ Next |
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

## Phase 17 — Security Hardening — NEXT

Purpose: evaluate the retained platform as an attacker and operator would, then harden only evidenced gaps while preserving deterministic authority and least privilege.

### Gate 17.1 — cross-cutting threat model and control-gap inventory — NEXT

Start with a repository-wide review before changing runtime behavior or adding AWS services.

Required review domains:

```text
identity / IAM / OIDC trust
CI/CD and artifact integrity
third-party dependency and supply-chain integrity
public input / repository acquisition abuse
semantic planning and prompt-injection boundaries
RAG / retrieved-content instruction resistance
agent proposal / capability authorization boundaries
MCP and A2A protocol admission
AgentCore optional runtime assumptions
runtime evidence / Inspector boundaries
secrets and sensitive-data handling
telemetry content minimization
failure recovery / kill switch / rollback
rate / quota / denial-of-wallet exposure
```

Expected output:

```text
threat inventory
existing control mapping
residual-risk classification
proof references
prioritized gaps
explicit non-gaps / already-proven controls
recommended next gate only when evidence justifies change
```

Do not convert a checklist into speculative implementation. Controls already proven by earlier phases should be referenced, not rebuilt.

### Candidate later gates — NOT YET AUTHORIZED

Depending on Gate 17.1 evidence, later slices may include:

```text
17.2 IAM / OIDC least-privilege verification
17.3 CI/CD / dependency / artifact integrity hardening
17.4 application input / prompt-injection / tool-abuse adversarial tests
17.5 sensitive-data / logging / telemetry hardening
17.6 operational recovery / kill-switch / abuse-cost controls
17.7 Security Hardening closeout
```

These labels are planning aids only. Gate 17.1 must decide whether each one is actually necessary.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure-path, architecture, security, and portfolio evidence after Phase 17 closes.

## Deferred cross-project integration

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains separate Governed LLM Gateway work and must not be modified or merged as a side effect of Phase 16 or Phase 17.
