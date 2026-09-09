# OpsLens — Current State

_Last updated: 2026-09-09_

This document is the authoritative implementation checkpoint for OpsLens. Detailed historical evidence remains in ADRs, gate labs, immutable evidence artifacts, merged PRs, workflow runs, and Git history.

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
  Gate 15.1 Capability fit / authority                         COMPLETE / GO OFFLINE ONLY
  Gate 15.1 Protocol-baseline correction                       COMPLETE / A2A 1.0.0
  Gate 15.2 Bounded offline reference adapter                  COMPLETE / MEASURED
  Gate 15.3 Official SDK conformance                           COMPLETE / PASS
  Gate 15.4 Retention / closeout                               COMPLETE / RETAIN BOUNDED OFFLINE
Phase 16   Runtime Exposure with Amazon Inspector              NEXT / PLANNED
Phase 17   Security Hardening                                  PLANNED
Phase 18   Evaluation, Cost & Portfolio Readiness              PLANNED
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
AuthorizedAgentAction != capability invocation
capability invocation != execution result
MCP tool name != capability authorization
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
A2A handoff proposal != handoff admission
A2A context/task identity != OpsLens source-task identity
A2A authentication != capability authorization
A2A protocol binding != business authority
A2A generated id != OpsLens content identity
A2A SDK acceptance != OpsLens admission authority
```

Deterministic code remains authoritative for evidence identity, vulnerability applicability, risk policy, structured-query compilation, retrieval admission, capability authorization, executable input binding, result admission, handoff admission, MCP admission/projection, A2A reference identity/resolution/admission, retry/fallback policy, and runtime-exposure truth.

## Retained reasoning reference — Phase 11

Phase 11 remains the default measured reasoning path:

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

The Phase 12 two-model topology remains rejected as default because it produced no quality lift while increasing invocations, tokens, latency, and cost. The deterministic specialization/handoff boundary remains retained.

## Phase 13 — MCP — final retained state

```text
mcp-capability-exposure:v1          RETAIN
mcp-capability-execution:v1         RETAIN
mcp-result-projection:v1            RETAIN
public/network MCP runtime          DO NOT RETAIN / NOT CREATED
MCP SDK deployment authority        NONE
```

MCP remains an offline interoperability boundary over existing typed capability authority.

## Phase 14 — AgentCore — final retained state

Measured experiment:

```text
Gate 14.2 replay:                6 / 6 PASS
AgentCore Runtime cost:          USD 0.002380345136128484
Bedrock inference cost:          USD 0.0041921
total observed cost:             USD 0.006572445136128483
runtime cleanup:                 RESOURCE_NOT_FOUND
Gate 14.4 IAM cleanup:           0 add / 0 change / 4 destroy
post-apply convergence:          NO CHANGES
```

Retention:

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

### Gate 15.1 — capability fit

Corrected authoritative protocol baseline:

```text
A2A protocol:                  1.0.0
standard bindings:             JSONRPC / GRPC / HTTP+JSON
first OpsLens binding choice:  JSONRPC
Python SDK observed:           1.1.4
```

Finding:

```text
retained independently deployed OpsLens peer: NO
current in-process handoff requires A2A:        NO
bounded interoperability hypothesis:           YES
decision:                                      GO OFFLINE ONLY
```

### Gate 15.2 — bounded offline reference adapter

Retained contract:

```text
a2a-reference-interoperability:v1
```

Path:

```text
pre-admitted SpecialistAgentTask
 -> content-addressed A2AReference
 -> code-owned local registry
 -> strict A2A 1.0 JSON-RPC SendMessage projection
 -> duplicate-key / exact-shape validation
 -> code-owned reference resolution
 -> bounded Message or terminal completed Task metadata
 -> deterministic OpsLens admission
 -> STOP
```

Measured evidence:

```text
Agent Card bytes:          582
protocol requests:         2
request bytes total:       1308
response bytes total:      989
client elapsed sum:        0.353039 ms
handler elapsed sum:       0.239397 ms
retries:                   0
model invocations:         0
capability executions:     0
new AWS resources:         0
new IAM roles/policies:    0
incremental AWS cost:      USD 0.00
```

### Gate 15.3 — official SDK conformance

Official oracle:

```text
distribution:  a2a-sdk
version:       1.1.4
release tag:   v1.1.4
source commit: 2d4d3048b245d2af854bad804f0e722ea9febc08
```

Protected merge:

```text
PR:                  #234
implementation head: bcf1ee4e7fa6ff948041696f6df4d735ef8b6cb5
merge:               f28a761bd666538cdfe24a53ee4e336b15b36398
A2A CI:              34408271518 / #16 — SUCCESS
Multi-Agent CI:      34408271444 / #48 — SUCCESS
AgentCore CI:        34408271466 / #75 — SUCCESS
```

Conformance:

```text
AgentCard parse / semantic round-trip:          PASS
SendMessageRequest parse / semantic round-trip: PASS
JSON-RPC 2.0 SendMessage construction:          PASS
Message response parse / semantic round-trip:   PASS
Task response parse / semantic round-trip:      PASS
project a2a-sdk dependency:                     0
protocol network requests:                      0
model invocations:                              0
capability executions:                          0
AWS/IAM changes:                                0
incremental AWS cost:                           USD 0.00
```

The SDK is an exact-source CI conformance oracle only. It is not added to `pyproject.toml` or `uv.lock`, and SDK acceptance never becomes OpsLens admission authority.

### Gate 15.4 — final retention decision

```text
content-addressed A2AReference contract:             RETAIN
strict raw JSON admission:                           RETAIN
code-owned reference resolution:                     RETAIN FOR BOUNDED LAB / CI
A2A 1.0 JSONRPC SendMessage profile:                 RETAIN
Message / terminal Task metadata admission:          RETAIN
A2A CI and fixtures:                                  RETAIN
official a2a-sdk exact-source conformance oracle:    RETAIN FOR CI
public/network A2A runtime:                           DO NOT CREATE
standing A2A cloud resources:                        NONE
new A2A IAM:                                          NONE
A2A capability/business-result authority:             DO NOT CREATE
a2a-sdk project/runtime dependency:                   DO NOT ADD
AgentCore hosting for A2A:                            DO NOT CREATE
MCP public-runtime promotion:                         DO NOT CREATE
```

Canonical closeout evidence:

```text
docs/adr/0059-phase15-a2a-closeout.md
labs/phase-15-closeout.md
labs/evidence/phase-15-closeout-v1.json
```

## Next planned phase

```text
Phase 16 — Runtime Exposure with Amazon Inspector
```

Phase 16 must preserve:

> **Repository Risk != Runtime Exposure.**

No Phase 16 AWS mutation is authorized merely by Phase 15 closeout. Phase 16 starts with its own capability-fit / evidence boundary.

## Deferred cross-project work

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains unrelated Governed LLM Gateway work and must remain untouched by Phase 15/16 changes unless explicitly resumed in a separate scope.
