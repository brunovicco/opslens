# Phase 15 — Gate 15.2: Bounded Offline A2A 1.0 Reference Adapter

_Date: 2026-09-09_

## Status

**COMPLETE — BOUNDED OFFLINE REFERENCE ADAPTER PROVEN; NO NETWORK OR EXECUTION AUTHORITY ADDED.**

```text
issue:              #230
PR:                 #231
source main:        ef6d59916d415ed16564543cf39ff5eb82384e12
measurement head:   c27a2362df4971a7b619be33dcaacd2bfe2a2369
contract:           a2a-reference-interoperability:v1
A2A release:        1.0.0
binding:            JSONRPC
operation:          SendMessage
```

## Why this gate exists

Gate 15.1 found no retained independently deployed OpsLens peer. It authorized only one local protocol-fit experiment over the already-admitted Gate 12.1 specialist-task boundary.

The goal was not to create another runtime. It was to prove that A2A can remain outside business authority.

## Implemented boundary

```text
pre-admitted SpecialistAgentTask
 -> create_a2a_reference(...)
 -> A2AReference
      handoff_id
      specialist_task_id
      reference_sha256
      reference_id
 -> A2AReferenceRegistry.register(...)
 -> build_send_message_request(...)
 -> strict raw JSON-RPC validation
 -> OfflineA2AReferencePeer.handle(...)
 -> code-owned registry.resolve(...)
 -> bounded Message OR terminal completed Task metadata
 -> admit_send_message_response(...)
 -> A2AReferenceResult
 -> STOP
```

No model or capability execution exists anywhere in this path.

## Deterministic reference identity

The reference contract is:

```text
a2a-reference-interoperability:v1
```

Reference identity is derived from canonical JSON over:

```text
contract_version
handoff_id
specialist_task_id
```

The resulting SHA-256 owns `reference_sha256` and `reference_id`.

The protocol therefore carries a pointer to already-admitted state rather than reconstructing authority from remote text or metadata.

## Frozen A2A profile

```text
A2A protocol release:          1.0.0
AgentInterface version:        1.0
protocol binding:              JSONRPC
JSON-RPC version:              2.0
operation:                     SendMessage
supported interfaces:          exactly 1
streaming:                     false
push notifications:            false
extended Agent Card:           false
input/output media:             application/json
business artifacts:            rejected
network endpoint:               none
```

The Agent Card URL uses the `.invalid` reserved domain because the peer is intentionally offline and not a deployable endpoint claim.

## Raw protocol validation

The adapter decodes UTF-8 JSON directly and uses an `object_pairs_hook` to reject duplicate keys before ordinary dictionary coercion.

Then exact-key-set admission rejects widening at every frozen object boundary.

Covered failure classes include:

```text
duplicate JSON key
unknown/extra object field
invalid UTF-8 / malformed JSON
wrong JSON-RPC version
unsupported method
wrong Message role
malformed Part
unknown/extra reference field
reference digest mismatch
request id mismatch
messageId mismatch
unknown registry reference
registered-state mismatch
duplicate request id
duplicate messageId
response id mismatch
response Message metadata mismatch
response Task context/id mismatch
non-completed Task
unexpected response result shape
Artifact/business payload outside the profile
```

## Replay semantics

Request and message correlation IDs are deterministic evidence IDs derived from `reference_sha256`.

The local peer keeps two in-memory replay sets:

```text
seen JSON-RPC request ids
seen A2A messageIds
```

Re-use is rejected.

This is intentionally narrow:

```text
transport success != exactly-once execution
```

Gate 15.2 makes no general distributed idempotency claim.

## Official SDK inspection and placement

Before any pin, the official Python `a2a-sdk` `1.1.4` package surface was inspected.

Observed core dependencies include HTTP, Pydantic, protobuf, Google API/common-proto, JSON-RPC, and packaging libraries.

Gate 15.2 therefore keeps:

```text
a2a-sdk runtime dependency: 0
a2a-sdk dev dependency:     0
new runtime dependencies:   0
```

The adapter uses the current A2A 1.0 specification as the wire-contract source and the Python standard library for the bounded JSON-RPC profile.

This avoids repeating the Phase 13 dependency-placement mistake where a protocol SDK in runtime dependencies enlarged unrelated Lambda packages.

It does **not** prove independent SDK compatibility. That becomes the next bounded question.

## First CI attempt

Initial head:

```text
025d032c0d5cf26fd03188f103c5a710fc631784
```

A2A CI run:

```text
run: 34403479455 / #1
job: 102640742076
```

The protocol fixture and bounded offline experiment passed. Ruff then failed only:

```text
RUF022 — __all__ is not sorted
```

No protocol or runtime failure occurred.

Remediation commit:

```text
c27a2362df4971a7b619be33dcaacd2bfe2a2369
```

The remediation changed export ordering only.

## Successful exact implementation validation

```text
workflow: A2A CI
run:      34405966213 / #2
job:      102648874518
head:     c27a2362df4971a7b619be33dcaacd2bfe2a2369
result:   SUCCESS
```

Quality gates:

```text
uv lock --check:                 PASS
uv sync --frozen:                PASS
protocol fixture JSON:           PASS
offline reference experiment:    PASS
Ruff:                             PASS
Pyright strict:                  PASS — 0 errors / 0 warnings
pytest A2A slice:                 PASS — 25 tests
```

## Measured local evidence

### Agent Card

```text
bytes: 582
```

### Direct Message response path

```text
request bytes:                 654
response bytes:                564
client elapsed:                0.210263 ms
peer handler elapsed:          0.144480 ms
reference admission:           ADMITTED
retry count:                   0
failure class:                 none
```

### Terminal Task response path

```text
request bytes:                 654
response bytes:                425
client elapsed:                0.142776 ms
peer handler elapsed:          0.094917 ms
reference admission:           ADMITTED
retry count:                   0
failure class:                 none
```

### Aggregate

```text
protocol requests:             2
peer handler attempts:         2
request bytes:                 1308
response bytes:                989
client elapsed sum:            0.353039 ms
handler elapsed sum:           0.239397 ms
retries:                       0
model invocations:             0
capability executions:         0
new AWS resources:             0
new IAM roles/policies:        0
incremental AWS cost:          USD 0.00
```

These timings are local process measurements. They must not be extrapolated to HTTP, Internet, cross-region, or production latency.

## Identity evidence

The measured fixture produced:

```text
handoff_id:
multi-agent-handoff:v1:handoff:c6a876d61a927a1f900d892819e0a43d54d64b281d970191cefdc86b15c31778

specialist_task_id:
single-agent-authority:v1:task:87ec895bc0a21460fad3e46ca679c132d6733fcab892dabb78a5d5c9f9a3055f

reference_sha256:
6ceba04c03f107c67ec599270b699d5231138f4acf05ab0a63b5ebaf7687a254
```

Protocol request/context/response IDs are deterministic correlation evidence only.

## Authority invariants

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

## Result

Gate 15.2 succeeds for the bounded hypothesis:

```text
reference projection:                 PASS
raw fail-closed protocol admission:   PASS
Message metadata path:                PASS
terminal Task metadata path:          PASS
model invocation count:               0
capability execution count:           0
AWS/IAM mutation:                      0
network deployment:                    0
new runtime dependencies:              0
```

The result is **not** sufficient to claim cross-implementation interoperability because both protocol sides are currently OpsLens-owned code.

## Retention decision

Retain:

```text
content-addressed A2AReference contract
raw duplicate/unknown-field validation
local reference registry for lab tests
strict JSON-RPC projection/admission
Message/terminal-Task metadata admission
A2A-specific CI slice and fixtures
measured evidence
```

Do not retain or create:

```text
public/network A2A runtime
standing cloud resources
new IAM
A2A capability authorization
business-result transport
AgentCore hosting
SDK runtime dependency
```

## Next authorized gate

Gate 15.3 only:

> Run one bounded offline conformance check using the official Python A2A SDK as an independent protocol oracle for the already-frozen happy-path Agent Card and `SendMessage` profile.

The purpose is to answer one remaining evidence gap:

```text
OpsLens-owned profile works locally
!=
independent official implementation accepts the same profile
```

Gate 15.3 must preserve:

```text
OpsLens raw validation:             authority
SDK parsing/acceptance:             protocol oracle only
model invocations:                  0
capability executions:              0
network deployment:                 0
AWS/IAM changes:                    0
business-result transport:          0
```

A real peer/network experiment remains deferred until a concrete consumer exists.

## Evidence files

```text
docs/adr/0057-bounded-offline-a2a-reference-adapter.md
labs/evidence/phase-15-gate-15-2-bounded-offline-a2a-reference-adapter-v1.json
```

## PR #89

The Governed LLM Gateway work remains outside Phase 15 scope and untouched:

```text
PR:     #89
branch: feat/governed-gateway-semantic-planner
```
