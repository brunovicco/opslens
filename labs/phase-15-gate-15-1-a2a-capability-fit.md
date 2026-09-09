# Phase 15 — Gate 15.1: A2A Capability Fit and Authority Boundary

_Date: 2026-09-09_

## Status

**COMPLETE — ONE BOUNDED OFFLINE REFERENCE-ONLY A2A INTEROPERABILITY EXPERIMENT AUTHORIZED.**

```text
source main: b4854fd6aeef4b3f041cd89b3fe45d63c8b72be5
issue:       #227
protocol:    A2A stable 0.3.0 assessed
AWS/IAM:     no change
```

## Why this gate exists

Phase 15 does not start by installing an A2A SDK or deploying another service.

OpsLens already has a deterministic Gate 12.1 specialization/handoff contract, but the retained runtime architecture does not contain an independently deployed peer. The Phase 12 two-model topology was measured and rejected as the default.

Therefore:

```text
existing typed handoff
!=
existing distributed-agent requirement
```

A2A must solve an interoperability problem rather than manufacture one.

## Current retained handoff

The real current boundary is:

```text
SingleAgentTask
 -> TriageAgentTask
 -> untrusted MultiAgentHandoffProposal
 -> deterministic source-task binding
 -> code-owned specialization mapping
 -> deterministic intersection with source allowed_capabilities
 -> empty intersection? FAIL CLOSED
 -> AuthorizedMultiAgentHandoff | MultiAgentHandoffAbstention
 -> narrowed SpecialistAgentTask
```

Current implementation references:

```text
src/opslens/multi_agent/domain/handoff.py
src/opslens/multi_agent/application/handoff.py
```

Measured Phase 12 evidence already established that deterministic specialization narrowing is useful independently from a second model call. The two-model topology itself is not the retained default.

## Official A2A baseline assessed

Official stable specification assessed on 2026-09-09:

```text
Agent2Agent Protocol 0.3.0
https://a2a-protocol.org/v0.3.0/specification/
```

Relevant concepts for OpsLens:

```text
AgentCard
security schemes
HTTP(S)
JSON-RPC 2.0
message/send
Task
Message
Part
Artifact
TaskState
task/context correlation identity
```

The full protocol is intentionally not the first experiment surface.

## Capability-fit finding

### Finding 1 — no retained independent peer exists today

The retained architecture does not currently have a separately hosted specialist agent whose operation requires A2A.

The historical Phase 12 second model is not treated as that peer because:

```text
Gate 12.3 two-model topology as default: DO NOT RETAIN
```

Reactivating it solely to justify A2A would violate the measured architecture decision.

### Finding 2 — a narrow interoperability hypothesis still exists

The Gate 12.1 content-addressed handoff provides a useful protocol-boundary experiment:

> Can an A2A adapter carry only a reference to one already-admitted `SpecialistAgentTask`, then re-bind the protocol response to existing OpsLens identities, without allowing A2A input or peer-generated metadata to create authority?

This is falsifiable and does not require production hosting.

## Decision

```text
GO TO ONE BOUNDED OFFLINE/IN-PROCESS INTEROPERABILITY EXPERIMENT
```

Not authorized:

```text
production/network A2A deployment
new AWS runtime
new IAM
model call
capability execution
streaming
push notifications
secondary auth
business-result transport
AgentCore hosting
MCP public promotion
```

## First experiment shape

Preferred conceptual path:

```text
already-admitted SpecialistAgentTask
 -> code-owned local reference registry
 -> reference-only A2A projection
      handoff_id
      specialist_task_id
      reference_sha256
 -> minimal A2A message/send
 -> bounded peer-side reference resolution
 -> terminal Message or Task metadata
 -> deterministic OpsLens result admission
 -> metadata-only evidence
 -> STOP before capability execution
```

The registry, if used, is lab-only in-memory state. Gate 15.1 does not create or imply a persistent invocation/task registry.

## Why reference-only input

A protocol request must not create executable or business authority.

The request therefore must not author:

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

Reference-only input lets deterministic code resolve already-admitted state and reject tampering before any downstream work.

This follows the same general authority discipline learned in Phase 13 MCP without conflating the two protocols.

## Protocol surface limit

Gate 15.2 should start with the smallest official stable surface that can prove interoperability:

```text
AgentCard
JSON-RPC 2.0
message/send
structured data part if needed
one terminal Message or Task
```

Defer until justified:

```text
SSE streaming
push notifications
secondary authentication
file payloads
arbitrary URLs
multi-turn context
remote business execution
```

## Identity map to freeze next

Gate 15.2 must define deterministic relationships among:

```text
source_task_id
proposal_id
handoff_id
specialist_task_id
reference_sha256
JSON-RPC request id
messageId
task id
contextId
artifact id, if used
AgentCard identity/version
```

Protocol-generated IDs are correlation evidence, never replacements for OpsLens content identities.

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
```

Existing authority remains code-owned:

```text
source-task binding
specialization mapping
capability intersection
handoff admission
capability authorization
executable-input binding
execution-result admission
provider/model selection
retry/fallback policy
business-result projection
```

## Replay / idempotency / failure scope

Gate 15.2 must freeze fixtures for:

```text
duplicate JSON-RPC request id
duplicate messageId
unknown specialist reference
reference hash mismatch
source/handoff/specialist mismatch
unknown or extra protocol fields
malformed structured part
non-terminal response where terminal required
rejected task
failed task
canceled task
timeout / transport failure
contradictory task/artifact identity
```

Important:

```text
transport success != exactly-once execution
```

No automatic retry is authorized until duplicate effects are bounded.

## Authentication scope

The official protocol supports declared security schemes and authenticates at the HTTP transport boundary. Production deployments require appropriate HTTPS/security posture.

Gate 15.1 does not make a production authentication claim because the next experiment is offline/in-process or loopback-only.

```text
A2A authentication != capability authorization
```

Any later network experiment must separately decide TLS, peer authentication, credentials, AgentCard exposure, secret ownership, request bounds, and hosting.

## SDK/dependency rule

No SDK is selected in Gate 15.1.

Gate 15.2 must inspect the official A2A implementation compatible with stable protocol `0.3.0`, then freeze:

```text
exact package/version
exact dependency scope
framework coercion behavior
raw request validation boundary
package-size/runtime impact
```

Default preference is a development/reference dependency unless a runtime requirement is proven.

## Experiment success criteria

The next experiment is useful only if it proves:

```text
official minimal protocol interoperability: PASS
reference -> pre-admitted SpecialistAgentTask binding: exact
unknown/tampered reference: fail closed
A2A-generated identity authority: 0
model invocations: 0
capability executions: 0
AWS resources: 0
new IAM: 0
public endpoint: 0
protocol overhead: measured
failure classes: observable
```

If those properties cannot be maintained, A2A does not progress to a real peer/model experiment.

## Observability dimensions

Freeze independent measures:

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
task/message outcome
model invocation count
capability execution count
incremental cost
```

No composite score.

## Cost / AWS boundary

Gate 15.1 itself:

```text
model invocations:        0
capability executions:    0
AWS API calls:            0
new AWS resources:        0
new IAM roles/policies:   0
AgentCore resources:      0
public endpoints:         0
incremental AWS cost:     USD 0.00
```

## Non-claims

This gate does not prove or authorize:

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
AgentCore hosting
MCP public runtime
runtime exposure truth
```

## Phase 13 / Phase 14 separation

```text
MCP  -> tool/capability interoperability boundary
A2A  -> agent-peer interaction boundary
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
labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v1.json
```

## Next authorized gate

Gate 15.2 only:

> Freeze and implement the smallest official A2A `0.3.0` reference-only adapter contract offline, including raw protocol validation, exact identity binding, replay/failure fixtures, SDK/dependency placement evidence, observability, and zero model/capability execution.

No network deployment and no model invocation are authorized yet.
