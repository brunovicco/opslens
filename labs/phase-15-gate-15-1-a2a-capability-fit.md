# Phase 15 — Gate 15.1: A2A Capability Fit and Authority Boundary

_Date: 2026-09-09_

## Status

**COMPLETE — ONE BOUNDED OFFLINE REFERENCE-ONLY A2A INTEROPERABILITY EXPERIMENT AUTHORIZED.**

```text
issue:                #227
original merge:       18fe6bd4e4dac8dab81ce11ac15e204d077fabd4
current protocol:     A2A 1.0.0
first binding choice: JSONRPC
AWS/IAM:              no change
```

## Protocol-baseline correction

The first Gate 15.1 revision used the historical versioned A2A `0.3.0` documentation page and incorrectly described it as the latest stable release.

Fresh verification against the current official A2A documentation on 2026-09-09 establishes:

```text
latest released A2A protocol: 1.0.0
release date:                 2026-03-12
previous version:             0.3.0
standard bindings:            JSONRPC / GRPC / HTTP+JSON
official Python SDK latest:   1.1.4 (2026-09-07)
```

The architecture decision is unchanged. Only the protocol baseline is corrected.

Evidence policy:

```text
phase-15-gate-15-1-a2a-capability-fit-v1.json
 -> preserved historical first assessment
 -> superseded for protocol-version claims

phase-15-gate-15-1-a2a-capability-fit-v2.json
 -> authoritative corrected Gate 15.1 evidence
```

## Why this gate exists

OpsLens already has a deterministic Gate 12.1 specialization/handoff contract, but the retained architecture does not contain an independently deployed peer. The measured Phase 12 two-model topology was rejected as the default.

Therefore:

```text
existing typed handoff
!=
existing distributed-agent requirement
```

A2A must solve an interoperability problem rather than manufacture one.

## Retained handoff boundary

```text
SingleAgentTask
 -> TriageAgentTask
 -> untrusted MultiAgentHandoffProposal
 -> deterministic source-task binding
 -> code-owned specialization mapping
 -> deterministic source/specialist capability intersection
 -> empty intersection? FAIL CLOSED
 -> AuthorizedMultiAgentHandoff | MultiAgentHandoffAbstention
 -> narrowed SpecialistAgentTask
```

Implementation references:

```text
src/opslens/multi_agent/domain/handoff.py
src/opslens/multi_agent/application/handoff.py
```

The deterministic handoff remains useful independently from a second model call.

## A2A v1.0 facts relevant to OpsLens

The official A2A v1.0 semantic model supports multiple standard bindings:

```text
JSONRPC
GRPC
HTTP+JSON
```

The Agent Card declares `supportedInterfaces`; each interface carries its own:

```text
url
protocolBinding
protocolVersion
```

For Gate 15.2, OpsLens deliberately selects **one JSON-RPC binding** as the smallest local experiment surface. This is an OpsLens scope decision, not a claim that A2A v1.0 is JSON-RPC-only.

The core operation used by the experiment is `SendMessage`.

## Capability-fit findings

### Finding 1 — no retained independent peer exists

There is no separately hosted specialist agent whose current operation requires A2A.

The historical Phase 12 second model is not reclassified as a peer because:

```text
Gate 12.3 two-model topology as default: DO NOT RETAIN
```

### Finding 2 — a narrow protocol hypothesis exists

The Gate 12.1 content-addressed handoff provides a falsifiable protocol boundary:

> Can an A2A adapter carry only a reference to one already-admitted `SpecialistAgentTask` and re-bind protocol results to existing OpsLens identities without allowing protocol data to create capability or business authority?

## Decision

```text
GO TO ONE BOUNDED OFFLINE/IN-PROCESS INTEROPERABILITY EXPERIMENT
```

Not authorized:

```text
production/network A2A deployment
new AWS runtime
new IAM
model invocation
capability execution
streaming
push notifications
extended authentication flow
business-result transport
AgentCore hosting
MCP public promotion
```

## Gate 15.2 reference-only shape

```text
already-admitted SpecialistAgentTask
 -> code-owned local reference registry
 -> reference-only projection
      handoff_id
      specialist_task_id
      reference_sha256
 -> A2A 1.0 SendMessage over selected JSONRPC binding
 -> bounded peer-side reference resolution
 -> terminal Message or Task metadata
 -> deterministic OpsLens result admission
 -> metadata-only evidence
 -> STOP before model/capability execution
```

The registry, if used, is lab-only in-memory state. No persistent invocation/task registry is implied.

## Why reference-only input

Protocol input must not author:

```text
SingleAgentTask
SpecialistAgentTask
allowed_capabilities
SemanticQuery
SQL
URL
shell command
credential
provider/model choice
retry/fallback policy
capability invocation args/kwargs
business result
```

Deterministic code resolves already-admitted state and rejects tampering before downstream work.

## Minimum protocol surface

Gate 15.2 may use only:

```text
AgentCard
supportedInterfaces
one AgentInterface
  protocolBinding = JSONRPC
  protocolVersion = 1.0
SendMessage
structured Part only when needed for the reference
one terminal Message or Task
```

Deferred:

```text
GRPC
HTTP+JSON
SSE streaming
push notifications
file payloads
arbitrary URLs
multi-turn context
remote business execution
```

## Identity map to freeze

```text
source_task_id
proposal_id
handoff_id
specialist_task_id
reference_sha256
JSON-RPC request id
messageId
task id if returned
contextId if returned
artifact id if used
AgentCard identity/version
AgentInterface protocolBinding
AgentInterface protocolVersion
```

Protocol-generated identifiers are correlation evidence only.

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
```

Existing OpsLens authority remains code-owned: source binding, specialization mapping, capability intersection, handoff admission, capability authorization, executable-input binding, execution-result admission, provider/model selection, retry/fallback policy, provenance, and result projection.

## Replay / failure requirements for Gate 15.2

Freeze fixtures for:

```text
duplicate JSON-RPC request id
duplicate messageId
unknown specialist reference
reference hash mismatch
source/handoff/specialist mismatch
unsupported protocolVersion
unsupported protocolBinding
unknown/extra protocol fields
malformed structured Part
non-terminal Task where terminal is required
rejected / failed / canceled Task
timeout / transport failure
contradictory Task / Artifact identity
```

```text
transport success != exactly-once execution
```

No automatic retry is authorized until duplicate effects are bounded.

## SDK/dependency rule

Gate 15.1 pins no SDK.

Fresh official Python implementation snapshot:

```text
repository:     a2aproject/a2a-python
latest release: 1.1.4
release date:   2026-09-07
```

Gate 15.2 must inspect exact SDK `1.1.4` dependency/framework behavior and confirm A2A v1.0 compatibility before adding a pin.

Default preference:

```text
reference/dev dependency first
```

## Success criteria for the next experiment

```text
selected A2A 1.0 JSON-RPC surface: PASS
reference -> pre-admitted SpecialistAgentTask binding: exact
unknown/tampered reference: fail closed
unsupported binding/version: fail closed
A2A-generated identity authority: 0
model invocations: 0
capability executions: 0
AWS resources: 0
new IAM: 0
public endpoint: 0
protocol overhead: measured
failure classes: observable
```

## Observability dimensions

```text
protocol requests
peer handler attempts
request bytes
response bytes
client elapsed
handler elapsed
retry count
failure class
reference admission outcome
Task/Message outcome
protocol binding/version
model invocation count
capability execution count
incremental cost
```

No composite score.

## Cost / AWS boundary

```text
model invocations:        0
capability executions:    0
new AWS resources:        0
new IAM roles/policies:   0
AgentCore resources:      0
public endpoints:         0
incremental AWS cost:     USD 0.00
```

## Non-claims

```text
A2A as production architecture
A2A public endpoint
production TLS/auth posture
production SLOs
exactly-once execution
streaming
push notifications
multi-turn state
business-result authority
capability authorization via AgentCard/skill
JSON-RPC as the only A2A v1.0 binding
AgentCore hosting
MCP public runtime
runtime exposure truth
```

## Phase 13 / Phase 14 separation

```text
MCP -> tool/capability interoperability boundary
A2A -> agent-peer interaction boundary
```

Neither creates business authority.

AgentCore remains optional disabled-by-default lab infrastructure and is not selected as A2A hosting. The Gate 14.2 `PUBLIC` exception is not inherited.

## PR #89

The Governed LLM Gateway integration remains deferred and untouched:

```text
branch: feat/governed-gateway-semantic-planner
head:   3781831795d500b05fa4bc602d50f376b4b1539f
```

## Evidence

```text
docs/adr/0056-bounded-a2a-capability-fit.md
labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v1.json  # superseded version claim
labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v2.json  # authoritative correction
```

## Next authorized gate

Gate 15.2 only:

> Freeze and implement the smallest A2A `1.0` reference-only adapter contract offline using one explicitly selected JSON-RPC binding, including raw protocol validation, AgentInterface version/binding admission, exact identity binding, replay/failure fixtures, SDK `1.1.4` dependency-placement evidence, observability, and zero model/capability execution.

No network deployment and no model invocation are authorized.
