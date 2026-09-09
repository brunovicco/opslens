# ADR 0056 — Bound A2A to One Offline Reference-Only Interoperability Experiment

- Status: Accepted
- Date: 2026-09-09
- Phase: 15 — A2A
- Gate: 15.1 — A2A Capability Fit and Authority Boundary

## Correction note

The first revision of this ADR used the historical versioned A2A `0.3.0` documentation page and incorrectly described it as the current latest stable protocol.

Current official A2A documentation identifies **protocol `1.0.0`** as the latest released stable protocol. A2A v1.0 was announced on 2026-03-12 as the first stable, production-ready major version.

The Gate 15.1 architecture decision does **not** change. The protocol baseline does.

Immutable correction evidence:

```text
labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v2.json
```

The original v1 evidence remains preserved historically and is superseded for protocol-version claims.

## Context

Phase 14 closed before Phase 15 began. The retained OpsLens reasoning architecture remains the measured Phase 11 direct Bedrock single-agent path.

Phase 12 retained deterministic specialization/handoff semantics but rejected its measured two-model triage-to-specialist topology as the default because it added material model calls, tokens, latency, and cost without quality lift.

The reusable Gate 12.1 boundary is:

```text
TriageAgentTask
 -> untrusted MultiAgentHandoffProposal
 -> deterministic source-task binding
 -> code-owned specialization mapping
 -> deterministic intersection with source allowed_capabilities
 -> AuthorizedMultiAgentHandoff | MultiAgentHandoffAbstention | fail closed
 -> SpecialistAgentTask
```

`SpecialistAgentTask` is content-bound to an `AuthorizedMultiAgentHandoff`, but both are currently in-process OpsLens contracts. There is no retained independently deployed OpsLens agent peer.

## Current official A2A baseline

Gate 15.1 is now bound to:

```text
A2A protocol:            1.0.0
release date:            2026-03-12
current specification:  https://a2a-protocol.org/dev/specification/
previous protocol:      0.3.0
```

A2A v1.0 defines one semantic model across multiple standard protocol bindings. The core standard bindings include:

```text
JSONRPC
GRPC
HTTP+JSON
```

The first OpsLens experiment will deliberately choose **JSON-RPC** as one bounded binding because it is sufficient for local protocol-conformance evidence and keeps the experiment small.

Therefore:

```text
A2A v1.0 supports multiple bindings
!=
OpsLens Gate 15.2 chooses one JSON-RPC binding
```

In v1.0, an Agent Card exposes `supportedInterfaces`; each `AgentInterface` declares its own URL, protocol binding, and protocol version. The protocol version is therefore an interface property, not a top-level Agent Card authority field.

## Problem

OpsLens needs to evaluate A2A as an interoperability mechanism without inventing a permanent distributed topology or reintroducing the rejected Phase 12 two-model architecture merely because A2A is next on the roadmap.

Two facts must be reconciled:

1. no retained independent agent service currently requires A2A;
2. OpsLens has a reusable, content-addressed handoff boundary that can support a narrow protocol-fit experiment.

The falsifiable question is:

> Can an A2A adapter transport only an already-admitted specialist-task reference across a bounded peer boundary and re-bind the result to existing OpsLens identities without allowing A2A input, peer metadata, task state, protocol binding, or artifacts to create capability or business authority?

## Decision

Authorize exactly one bounded **offline / in-process or loopback-only reference interoperability experiment** before any A2A network deployment, model topology change, or capability execution is considered.

Decision class:

```text
GO TO ONE BOUNDED OFFLINE/IN-PROCESS INTEROPERABILITY EXPERIMENT
```

This authorizes an experiment, not A2A retention as production architecture.

## Gate 15.2 protocol surface

Use the smallest useful A2A v1.0 surface:

```text
AgentCard
supportedInterfaces
one AgentInterface
  protocolBinding = JSONRPC
  protocolVersion = 1.0
JSON-RPC request/response binding
SendMessage core operation
one bounded Message or terminal Task response
structured data Part only if required for reference projection
```

The exact JSON-RPC wire representation and SDK coercion must be inspected against the official implementation before code is accepted.

Explicitly defer:

```text
GRPC binding
HTTP+JSON binding
streaming / SSE
push notifications
extended Agent Card authentication flow
file payloads
arbitrary URLs
multi-turn context
remote capability execution
public Internet exposure
cloud hosting
```

## Reference-only protocol input

An A2A request must not author a `SingleAgentTask`, `SpecialistAgentTask`, capability allowlist, provider/model choice, executable arguments, SQL, URL, credential, or business result.

Preferred conceptual path:

```text
already-admitted SpecialistAgentTask
 -> code-owned local reference registration
 -> protocol reference envelope
      handoff_id
      specialist_task_id
      reference_sha256
 -> A2A v1.0 SendMessage over selected JSON-RPC binding
 -> bounded peer reference resolution/admission
 -> terminal protocol metadata
 -> deterministic OpsLens admission
 -> STOP before model/capability execution
```

If an in-memory registry is used, it is lab-only infrastructure. A persistent registry is not implied.

## Result boundary

The first experiment must stop before model or capability execution.

```text
A2A transport response
 -> raw protocol validation
 -> allowed Message/Task shape validation
 -> terminal-state validation when a Task is returned
 -> exact reference identity binding
 -> deterministic OpsLens admission
 -> metadata-only evidence
 -> STOP
```

Any future business-content or specialist-model result transport requires a separate admission/projection decision.

## Permanent authority mapping

Freeze:

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

Existing code-owned authority remains unchanged:

- source task identity and content identity;
- specialization mapping;
- source/specialist capability intersection;
- handoff proposal admission;
- specialist-task construction;
- capability authorization;
- executable-input binding;
- execution-result admission;
- provider/model selection;
- retry/fallback policy;
- evidence provenance and result projection.

## Identity and provenance requirements for Gate 15.2

Freeze deterministic relationships among at least:

```text
OpsLens source_task_id
OpsLens handoff proposal_id
OpsLens handoff_id
OpsLens specialist_task_id
reference_sha256
A2A JSON-RPC request id
A2A messageId
A2A task id if returned
A2A contextId if returned
A2A artifact id if used
Agent Card identity/version
AgentInterface protocolBinding
AgentInterface protocolVersion
```

A2A-generated identifiers are correlation/runtime evidence only. They never replace OpsLens content-addressed identifiers.

## Replay and failure requirements

Before the first adapter executes, Gate 15.2 must define stable behavior for:

```text
duplicate JSON-RPC request id
duplicate messageId
unknown reference
reference hash mismatch
source/handoff/specialist identity mismatch
unsupported protocolVersion
unsupported protocolBinding
unknown or extra protocol fields
malformed structured Part
non-terminal Task where terminal is required
rejected / failed / canceled Task
timeout / transport failure
contradictory Task / Artifact identity
```

Transport success must never imply exactly-once execution.

No automatic retry is authorized until duplicate effects are explicitly bounded.

## Authentication and transport consequence

Gate 15.1 authorizes no production transport.

For the first experiment:

```text
public Internet endpoint:       0
AWS runtime:                    0
new IAM role/policy:            0
feature-branch cloud identity:  0
standing credential:            0
```

If Gate 15.2 uses loopback HTTP to exercise the official SDK, that proves only local protocol behavior. It does not establish production HTTPS, peer authentication, or credential posture.

A future network experiment must separately decide TLS, Agent Card exposure, authentication, secret ownership, request bounds, and hosting/IAM. It must not inherit the Gate 14.2 AgentCore `PUBLIC` exception.

## SDK/dependency consequence

Gate 15.1 does not pin an SDK.

Fresh official Python SDK evidence on 2026-09-09 shows:

```text
repository:       a2aproject/a2a-python
latest release:   1.1.4
release date:     2026-09-07
```

Gate 15.2 must inspect the exact SDK `1.1.4` package/dependency surface and confirm compatibility with the A2A v1.0 semantic contract before any pin is added.

Default preference:

```text
reference/dev dependency first
```

A runtime dependency is justified only by measured implementation need and package impact.

## MCP and AgentCore separation

A2A is an agent-peer interoperability protocol, not an MCP replacement and not new business authority.

Phase 13 MCP remains a bounded offline tool/capability interoperability boundary.

Phase 14 AgentCore remains an optional disabled-by-default lab target. A2A must not assume AgentCore as hosting substrate.

## Benefit hypothesis

The first experiment is successful only if it proves all of the following without widening authority:

```text
1. conformance to the selected minimal A2A v1.0 JSON-RPC surface;
2. exact binding from protocol reference to one pre-admitted SpecialistAgentTask;
3. protocol-generated identifiers remain evidence-only;
4. unknown/tampered references fail closed;
5. unsupported binding/version fails closed;
6. capability executions remain 0;
7. model invocations remain 0;
8. AWS/IAM/network deployment remains 0;
9. protocol overhead and failure evidence are observable.
```

If these properties cannot be maintained, A2A does not proceed to a real peer/model experiment.

## Observability and cost contract

Gate 15.2 must record independent dimensions:

```text
protocol request count
peer handler count
request bytes
response bytes
client elapsed time
handler elapsed time
retry count
failure class
reference admission outcome
Task/Message outcome
protocol binding/version
model invocation count
capability execution count
incremental cost
```

No composite quality score.

For an offline local adapter, AWS infrastructure cost remains `USD 0.00`; this is a scope fact, not a production cost estimate.

## Alternatives rejected

### Deploy an A2A service immediately

Rejected because no retained independent OpsLens peer currently requires a network service.

### Re-activate the Phase 12 two-model topology as the A2A use case

Rejected because Gate 12.4 already measured and rejected that topology as default.

### Treat the current in-process handoff as already requiring A2A

Rejected because a typed function boundary does not become a distributed-systems problem merely because a standard exists.

### Defer A2A entirely

Rejected because the content-addressed Gate 12.1 handoff provides a narrow, falsifiable offline interoperability hypothesis with zero cloud/runtime authority expansion.

### Use MCP instead

Rejected as a false equivalence. MCP exposes bounded tools/capabilities; A2A models agent-peer interaction. Neither creates business authority.

## Consequences

Positive:

- A2A learning is tied to an existing OpsLens authority contract;
- the experiment targets the current stable protocol rather than a historical version;
- JSON-RPC is an explicit bounded experiment choice rather than a false protocol-wide assumption;
- no public runtime is invented;
- no rejected multi-agent topology is silently revived;
- protocol identity remains separate from business authority;
- AWS/IAM/cost impact remains zero for Gate 15.1.

Costs:

- the first experiment is intentionally much smaller than the full A2A v1.0 surface;
- local interoperability does not prove production authentication, SLOs, or cross-vendor deployment;
- a later real-peer experiment still requires a separate value hypothesis and retention decision.

## Non-claims

Gate 15.1 does not establish:

```text
A2A as retained production architecture
A2A public/network runtime
production authentication or TLS posture
exactly-once A2A execution
A2A business-result authority
A2A capability authorization
A2A streaming or push-notification support
A2A multi-turn memory/session semantics
JSON-RPC as the only A2A v1.0 binding
AgentCore hosting for A2A
MCP promotion to public runtime
runtime exposure truth
```

## AWS / IAM / runtime impact

```text
A2A SDK dependencies:       0
A2A endpoints:              0
model invocations:          0
capability executions:      0
new AWS resources:          0
new IAM roles/policies:     0
AgentCore resources:        0
MCP runtime changes:        0
runtime-exposure authority: 0
incremental AWS cost:       USD 0.00
PR #89 changes:             0
```

## Next authorized gate

Authorize Gate 15.2 only:

> Freeze and implement the smallest official A2A `1.0` reference-only adapter contract offline using one explicitly selected JSON-RPC binding, including raw protocol validation, AgentInterface version/binding admission, identity binding, replay/failure fixtures, SDK `1.1.4` dependency-placement evidence, observability, and zero model/capability execution.

No network deployment or model invocation is authorized by this ADR.

## Production engineering / AIP-C01 learning connection

This decision exercises production GenAI engineering discipline: distinguish protocol authentication from application authorization, keep protocol/model/agent data untrusted until deterministic admission, minimize runtime and IAM surface, pin evaluation to current official contracts, preserve failed or superseded evidence rather than rewriting history, and introduce distributed-system complexity only behind a measurable hypothesis.
