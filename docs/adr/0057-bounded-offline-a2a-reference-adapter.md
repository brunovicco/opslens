# ADR 0057 — Retain a Strict Offline A2A Reference Adapter Before Any Real Peer Runtime

- Status: Accepted
- Date: 2026-09-09
- Phase: 15 — A2A
- Gate: 15.2 — Bounded Offline A2A 1.0 Reference Adapter

## Context

Gate 15.1 established that OpsLens has no retained independently deployed agent peer that currently requires A2A. It nevertheless authorized one falsifiable offline experiment over the retained Gate 12.1 deterministic specialization boundary.

The retained input authority is already admitted before A2A exists:

```text
TriageAgentTask
 -> untrusted MultiAgentHandoffProposal
 -> deterministic source-task binding
 -> code-owned specialization mapping
 -> deterministic capability intersection
 -> AuthorizedMultiAgentHandoff | abstention | fail closed
 -> SpecialistAgentTask
```

The corrected protocol baseline is A2A `1.0.0`. Gate 15.2 deliberately selects one JSON-RPC binding and the `SendMessage` operation while deferring network hosting, streaming, push notifications, extended authentication, business-result transport, model invocation, and capability execution.

## Problem

A useful first A2A implementation must demonstrate interoperability semantics without letting protocol input create OpsLens business or execution authority.

The experiment therefore needs to answer:

> Can a strict A2A 1.0 JSON-RPC profile carry only a content-addressed reference to one already-admitted `SpecialistAgentTask`, resolve it through code-owned state, and admit only bounded protocol metadata back into OpsLens?

The implementation must also avoid expanding runtime dependencies merely because an official SDK exists.

## Decision

Retain the Gate 15.2 implementation as a **bounded offline reference adapter**, not as a deployed agent runtime and not as proof that A2A should become production architecture.

Freeze the contract:

```text
a2a-reference-interoperability:v1
```

Retained path:

```text
pre-admitted SpecialistAgentTask
 -> deterministic content-addressed A2AReference
 -> lab-only in-memory code-owned registry
 -> strict A2A 1.0 JSON-RPC SendMessage projection
 -> raw duplicate-key + exact-shape validation
 -> code-owned reference resolution
 -> bounded Message or terminal completed Task metadata
 -> deterministic OpsLens result admission
 -> STOP before model/capability execution
```

## Reference-only input authority

The protocol can carry only:

```text
handoff_id
specialist_task_id
reference_sha256
```

The reference digest is computed from canonical semantics owned by OpsLens code. The protocol cannot author:

```text
source task text
capability allowlists
specialization authority
provider/model selection
SQL
URLs
credentials
executable args/kwargs
retry/fallback policy
business results
```

A2A-generated identifiers remain correlation evidence only.

## Raw validation decision

Gate 15.2 validates raw UTF-8 JSON before domain admission.

The adapter rejects:

```text
duplicate JSON keys
unknown/extra keys
wrong JSON-RPC version
unsupported method
malformed reference shape
unknown reference
reference digest mismatch
handoff/specialist mismatch
request id not bound to the reference
duplicate request id
messageId not bound to the reference
duplicate messageId
unsupported result shape
non-completed Task
Artifact/business payloads outside the frozen profile
```

This deliberately keeps framework coercion outside the trust boundary.

## Replay semantics

The first contract uses deterministic request/message correlation identifiers derived from the content-addressed reference.

For this bounded experiment:

```text
repeat request id  -> reject
repeat messageId   -> reject
automatic retry    -> none
exactly-once claim -> none
```

The experiment therefore proves explicit replay refusal, not a general distributed idempotency strategy.

## Agent Card profile

The local peer exposes exactly one selected interface:

```text
protocolBinding = JSONRPC
protocolVersion = 1.0
```

The bounded Agent Card declares:

```text
streaming = false
pushNotifications = false
extendedAgentCard = false
one reference-only skill
application/json input/output modes
```

The Agent Card advertises interoperability metadata only. It does not grant capability authority.

## SDK dependency placement decision

The official Python SDK `1.1.4` was inspected before any pin.

Its core package adds a non-trivial dependency surface including HTTP, Pydantic, protobuf, Google API, JSON-RPC, common-proto, and packaging libraries.

Gate 15.2 adds **no `a2a-sdk` dependency** because the selected offline wire profile can be implemented and tested deterministically with the Python standard library.

```text
a2a-sdk runtime dependency: 0
a2a-sdk dev dependency:     0 for Gate 15.2
new runtime dependencies:   0
```

This is a dependency-isolation decision, not a claim that the official SDK is unnecessary for every future A2A integration.

The next conformance gate may use the official SDK as a development-only independent oracle if that adds evidence without moving admission authority into the SDK.

## Measured result

Successful implementation head:

```text
c27a2362df4971a7b619be33dcaacd2bfe2a2369
```

Exact CI evidence:

```text
workflow: A2A CI
run:      34405966213 / run #2 / SUCCESS
job:      102648874518
Ruff:     PASS
Pyright:  PASS — 0 errors, 0 warnings
pytest:   PASS — 25 passed
```

Measured local experiment:

```text
Agent Card bytes:          582
protocol requests:         2
peer handler attempts:     2
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

Response paths measured independently:

```text
Message: request 654 B / response 564 B / client 0.210263 ms / handler 0.144480 ms
Task:    request 654 B / response 425 B / client 0.142776 ms / handler 0.094917 ms
```

These local latency values are lab evidence only. They do not represent network or production SLOs.

## Initial CI failure preserved

The first CI attempt at `025d032c0d5cf26fd03188f103c5a710fc631784` successfully ran the functional experiment but failed Ruff rule `RUF022` because `__all__` was not sorted.

The only remediation was export ordering. No protocol or runtime semantics changed.

Preserving this failure is part of the evidence trail rather than rewriting the gate as if the first attempt had passed.

## Permanent authority boundaries

```text
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

## What Gate 15.2 proves

Gate 15.2 supports these claims:

1. one pre-admitted specialist task can be represented by a deterministic reference;
2. the reference can cross a local A2A 1.0 JSON-RPC projection and be re-bound to the original task;
3. raw JSON validation can reject duplicate and unknown fields before domain admission;
4. direct Message and terminal completed Task metadata paths can be admitted without business-result authority;
5. model calls, capability execution, AWS/IAM changes, network hosting, and new runtime dependencies can all remain zero.

## What Gate 15.2 does not prove

```text
cross-implementation A2A interoperability
official SDK conformance
production network transport
production TLS/authentication
network latency or SLOs
exactly-once distributed execution
multi-turn task/context semantics
streaming
push notifications
business-result authority
A2A as retained production architecture
AgentCore hosting for A2A
MCP public runtime
runtime exposure truth
```

## Next decision

Authorize **Gate 15.3 only**:

> Run one bounded offline official-SDK conformance check against the frozen happy-path Agent Card and `SendMessage` profile, using the official Python SDK only as an independent protocol oracle while retaining OpsLens raw validation, content identity, and admission authority in deterministic code.

Gate 15.3 must remain development/offline only and keep:

```text
network deployment:      0
new AWS resources:       0
new IAM:                 0
model invocations:       0
capability executions:   0
business-result transport: 0
```

A real network peer remains unjustified until a concrete independent consumer/peer requirement exists.

## Evidence

```text
labs/evidence/phase-15-gate-15-2-bounded-offline-a2a-reference-adapter-v1.json
labs/phase-15-gate-15-2-bounded-offline-a2a-reference-adapter.md
```

## Production engineering / AIP-C01 learning connection

This gate reinforces production GenAI engineering principles relevant to AWS workloads: separate protocol interoperability from authorization, minimize dependency and IAM surface, keep untrusted protocol data outside business authority until deterministic admission, use content-addressed evidence for provenance, measure latency/cost/failure dimensions independently, and defer distributed runtime complexity until a concrete workload requires it.
