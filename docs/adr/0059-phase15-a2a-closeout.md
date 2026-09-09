# ADR 0059 — Close Phase 15 at the bounded offline A2A interoperability boundary

- Status: Accepted
- Date: 2026-09-09
- Phase: 15 — A2A
- Gate: 15.4 — Phase 15 Retention and Closeout

## Context

Phase 15 evaluated whether A2A should become a runtime or authority boundary in OpsLens.

The phase began from the already-retained Gate 12.1 deterministic handoff boundary. No independently deployed OpsLens peer existed, and the existing in-process handoff did not require a network protocol.

Gate 15.1 therefore authorized only one bounded offline interoperability experiment. Gate 15.2 implemented a strict A2A 1.0 JSON-RPC `SendMessage` reference adapter over an already-admitted `SpecialistAgentTask`. Gate 15.3 then used the official Python A2A SDK v1.1.4 source commit as an independent CI-only protocol oracle.

Measured evidence now answers the protocol-fit question without creating network or business authority.

## Measured evidence

### Gate 15.1

```text
retained independently deployed OpsLens peer: NO
current in-process handoff requires A2A:        NO
bounded interoperability hypothesis:           YES
decision:                                      GO OFFLINE ONLY
```

The authoritative protocol baseline was corrected to A2A `1.0.0` before implementation.

### Gate 15.2

```text
contract:                 a2a-reference-interoperability:v1
binding:                  JSONRPC
operation:                SendMessage
Agent Card bytes:         582
protocol requests:        2
request bytes total:      1308
response bytes total:     989
retries:                  0
model invocations:        0
capability executions:    0
new AWS resources:        0
new IAM roles/policies:   0
incremental AWS cost:     USD 0.00
```

The strict local adapter passed exact-head CI and retained raw duplicate-key rejection, exact-shape validation, content-addressed reference identity, code-owned reference resolution, bounded Message/terminal Task metadata admission, and replay refusal.

### Gate 15.3

Official conformance oracle:

```text
distribution:  a2a-sdk
version:       1.1.4
release tag:   v1.1.4
source commit: 2d4d3048b245d2af854bad804f0e722ea9febc08
```

Measured result:

```text
AgentCard parse + semantic round-trip:          PASS
SendMessageRequest parse + semantic round-trip: PASS
JSON-RPC 2.0 SendMessage construction:          PASS
Message SendMessageResponse:                    PASS
Task SendMessageResponse:                       PASS
project a2a-sdk dependency:                     0
protocol network requests:                      0
model invocations:                              0
capability executions:                          0
new AWS resources:                              0
new IAM roles/policies:                         0
incremental AWS cost:                           USD 0.00
```

The SDK is acquired from the exact source commit only inside CI setup. It is not added to `pyproject.toml` or `uv.lock` and does not participate in OpsLens admission authority.

## Decision

Close Phase 15 with the following retained architecture.

Retain:

```text
content-addressed A2AReference contract
strict raw JSON duplicate-key / exact-shape validation
code-owned local reference resolution for bounded lab/CI use
A2A 1.0 JSONRPC SendMessage projection
Message / terminal completed Task metadata admission
replay refusal for bounded local exchanges
A2A-specific fixtures and CI checks
official a2a-sdk v1.1.4 exact-source CI conformance oracle
Gate 15.1 / 15.2 / 15.3 immutable evidence
```

Do not retain or create:

```text
public/network A2A runtime
standing A2A cloud resources
new A2A IAM
A2A capability authorization
A2A business-result authority
A2A SDK project/runtime dependency
AgentCore hosting for A2A
MCP public-runtime promotion
```

A future network experiment requires a concrete consumer/peer requirement and a new explicit gate. Protocol conformance alone is insufficient justification for deployment.

## Authority invariants

```text
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

## Consequences

Phase 15 demonstrates A2A protocol literacy and independent conformance without manufacturing a distributed runtime that the current architecture does not need.

The next planned project phase remains Phase 16 — Runtime Exposure with Amazon Inspector. Phase 15 does not authorize any Phase 16 AWS change by itself.

## Evidence

```text
docs/adr/0056-bounded-a2a-capability-fit.md
docs/adr/0057-bounded-offline-a2a-reference-adapter.md
docs/adr/0058-official-a2a-sdk-as-ci-conformance-oracle.md
labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v2.json
labs/evidence/phase-15-gate-15-2-bounded-offline-a2a-reference-adapter-v1.json
labs/evidence/phase-15-gate-15-3-official-sdk-conformance-v1.json
labs/evidence/phase-15-closeout-v1.json
```

## PR #89

The unrelated Governed LLM Gateway work remains untouched:

```text
PR:     #89
branch: feat/governed-gateway-semantic-planner
```
