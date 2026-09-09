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
| 16 | Runtime Exposure with Amazon Inspector | ▶️ Next / Planned |
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
runtime authentication != capability authorization
runtime deployment != runtime-exposure truth
A2A message != capability authorization
A2A peer identity != business authority
A2A AgentCard skill != OpsLens capability authorization
A2A task state != business/evidence truth
A2A transport success != business/evidence truth
A2A artifact != admitted OpsLens evidence
A2A authentication != capability authorization
A2A protocol binding != business authority
A2A generated id != OpsLens content identity
A2A SDK acceptance != OpsLens admission authority
```

## Completed foundation — Phases 0–10

Phases 0–10 established AWS foundation, threat-intelligence ingestion, deterministic vulnerability correlation, immutable public-repository evidence, risk prioritization, bounded semantic query planning/SQL compilation, Bedrock Knowledge Base retrieval with Amazon S3 Vectors, hybrid retrieval, governed public-analysis admission, and operational telemetry.

Detailed historical implementation/evidence remains in ADRs, labs, immutable artifacts, and Git history.

## Phase 11 — Single-Agent Baseline — COMPLETE

Retained measured reference:

```text
quality:                    6/6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
SDK retries:                0
capability executions:      0
derived inference cost:     USD 0.0041921
```

This remains the default/reference reasoning path.

## Phase 12 — Multi-Agent Architecture — COMPLETE

Retained deterministic handoff/specialization and comparison discipline; rejected the measured two-model topology as the default because it produced no quality lift while increasing invocations, tokens, latency, and cost.

## Phase 13 — MCP — COMPLETE

Retained:

```text
mcp-capability-exposure:v1
mcp-capability-execution:v1
mcp-result-projection:v1
```

MCP remains a bounded offline interoperability layer over existing typed capability authority. A public/network MCP runtime is not retained.

## Phase 14 — Amazon Bedrock AgentCore — COMPLETE

Measured one bounded HTTP/SigV4 Runtime experiment and retained AgentCore only as an optional lab target.

Final state:

```text
Phase 11 direct Bedrock reasoning:          RETAIN / DEFAULT
AgentCore implementation/evidence:          RETAIN AS OPTIONAL LAB TARGET
AgentCore managed Runtime as default:        DO NOT RETAIN
standing AgentCore Runtime resources:        NONE
standing experiment-specific GitHub IAM:    REMOVED
Gate 14.2 PUBLIC exception:                  NOT RETAINED
Runtime Identity service-linked role:        RETAIN pending separate safety proof
```

## Phase 15 — A2A — COMPLETE

### Gate 15.1 — capability fit / protocol correction — COMPLETE

```text
A2A protocol:                  1.0.0
standard bindings:             JSONRPC / GRPC / HTTP+JSON
first OpsLens binding choice:  JSONRPC
independent retained peer:     NO
network A2A required today:    NO
decision:                      GO OFFLINE ONLY
```

### Gate 15.2 — bounded offline reference adapter — COMPLETE / MEASURED

```text
contract:                    a2a-reference-interoperability:v1
Agent Card bytes:            582
protocol requests:           2
request bytes total:         1308
response bytes total:        989
client elapsed sum:          0.353039 ms
handler elapsed sum:         0.239397 ms
retries:                     0
model invocations:           0
capability executions:       0
new AWS/IAM:                 0
incremental AWS cost:        USD 0.00
```

The retained profile carries only `{handoff_id, specialist_task_id, reference_sha256}` for an already-admitted specialist task and stops before model/capability execution.

### Gate 15.3 — official SDK conformance — COMPLETE / PASS

```text
a2a-sdk version:             1.1.4
release tag:                 v1.1.4
source commit:               2d4d3048b245d2af854bad804f0e722ea9febc08
AgentCard conformance:       PASS
SendMessage request:         PASS
JSON-RPC construction:       PASS
Message response:            PASS
Task response:               PASS
project/runtime dependency:  0
protocol network requests:   0
model/capability execution:  0
AWS/IAM changes:             0
```

The SDK is retained only as an exact-source CI conformance oracle. Package acquisition is CI setup, not A2A protocol traffic.

### Gate 15.4 — retention / closeout — COMPLETE

Retain:

```text
content-addressed A2AReference
strict raw JSON admission
code-owned reference resolution for bounded lab / CI
A2A 1.0 JSONRPC SendMessage profile
Message / terminal Task metadata admission
A2A fixtures / CI
official a2a-sdk exact-source CI oracle
Phase 15 immutable evidence
```

Do not create/retain:

```text
public/network A2A runtime
standing A2A cloud resources
new A2A IAM
A2A capability authorization
A2A business-result authority
a2a-sdk project/runtime dependency
AgentCore hosting for A2A
MCP public-runtime promotion
```

Canonical closeout:

```text
docs/adr/0059-phase15-a2a-closeout.md
labs/phase-15-closeout.md
labs/evidence/phase-15-closeout-v1.json
```

## Phase 16 — Runtime Exposure with Amazon Inspector — NEXT / PLANNED

Purpose: add independent runtime exposure evidence while preserving:

> **Repository Risk != Runtime Exposure.**

Phase 16 must begin with a fresh capability-fit/evidence boundary before any AWS mutation. Phase 15 closeout does not authorize Phase 16 infrastructure changes.

## Phase 17 — Security Hardening — PLANNED

Cross-cutting IAM, data protection, abuse resistance, dependency, threat-model, and operational hardening.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure-path, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains separate Governed LLM Gateway work and must not be modified or merged as a side effect of Phase 15 or Phase 16.
