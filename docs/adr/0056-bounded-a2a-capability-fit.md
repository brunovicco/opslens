# ADR 0056 — Bound A2A to One Offline Reference-Only Interoperability Experiment

- Status: Accepted
- Date: 2026-09-09
- Phase: 15 — A2A
- Gate: 15.1 — A2A Capability Fit and Authority Boundary

## Context

Phase 14 closed on `main` at:

```text
b4854fd6aeef4b3f041cd89b3fe45d63c8b72be5
```

The retained OpsLens reasoning architecture remains the measured Phase 11 direct Bedrock single-agent path. Phase 12 retained deterministic specialization/handoff semantics but rejected its two-model triage-to-specialist topology as the default because the measured experiment added cost, latency, tokens, and model calls without quality lift.

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

`SpecialistAgentTask` is content-bound to an `AuthorizedMultiAgentHandoff`, but both remain in-process domain/application contracts today. There is no retained independently deployed OpsLens agent peer.

The official Agent2Agent Protocol specification published version `0.3.0` as the latest stable version assessed by this gate on 2026-09-09:

```text
https://a2a-protocol.org/v0.3.0/specification/
```

The relevant stable protocol model includes Agent Cards, HTTP(S), JSON-RPC 2.0, `message/send`, Tasks, Messages, Parts, Artifacts, task/context identifiers, and declared security schemes. The specification treats production transport security and request authentication as protocol concerns, while credential acquisition remains outside the A2A protocol.

Those protocol identities and transport/authentication mechanisms are not OpsLens business authority.

## Problem

OpsLens needs to evaluate A2A as an interoperability mechanism without inventing a permanent network topology or reintroducing the rejected Phase 12 two-model architecture simply because A2A is next on the roadmap.

Two facts must be reconciled:

1. there is no current retained independent agent service that requires A2A;
2. the project has a reusable deterministic handoff contract that provides a meaningful authority boundary to test against an opaque peer protocol.

A network deployment would therefore be premature. A small offline protocol experiment can still produce reusable evidence if it answers a narrower falsifiable question:

> Can an A2A adapter transport only an already-admitted specialist-task reference across a peer boundary and re-bind the result to existing OpsLens identities without allowing A2A input, peer metadata, task state, or artifacts to create capability or business authority?

## Decision

Authorize exactly one bounded **offline / in-process or loopback-only reference interoperability experiment** before any A2A network deployment, model topology change, or capability execution is considered.

Decision class:

```text
GO TO ONE BOUNDED OFFLINE/IN-PROCESS INTEROPERABILITY EXPERIMENT
```

This is an experiment authorization, not A2A retention as product architecture.

The first experiment must remain narrower than a full A2A agent deployment.

### Required protocol surface

Start with only the smallest useful stable `0.3.0` surface:

```text
AgentCard discovery/representation
JSON-RPC 2.0 binding
message/send
one bounded Message or terminal Task response
DataPart / structured data only when required for reference projection
```

Explicitly defer:

```text
streaming / SSE
push notifications
secondary in-task authentication
file payloads
arbitrary URLs
multi-turn context
remote capability execution
public Internet exposure
cloud hosting
```

A later gate may add one of these only after a concrete requirement and failure model are frozen.

### Reference-only protocol input

The A2A request must not author a `SingleAgentTask`, `SpecialistAgentTask`, capability allowlist, provider/model choice, executable arguments, SQL, URL, credential, or business result.

Prefer a reference-only projection conceptually equivalent to:

```text
already-admitted SpecialistAgentTask
 -> code-owned local reference registration
 -> protocol reference envelope
      handoff_id
      specialist_task_id
      reference_sha256
 -> A2A message/send
 -> bounded peer resolution/admission
```

The exact contract is Gate 15.2 work and must be frozen before SDK/framework coercion.

If an in-memory registry is used for the experiment, it is test/lab infrastructure only. A persistent registry is not implied.

### Result boundary

The first experiment must stop before capability execution.

A protocol success may return only enough structured metadata to prove identity binding and task-state handling. Any future business-content or specialist-model result transport requires a separate projector/admission decision.

```text
A2A transport response
 -> raw protocol validation
 -> task/message terminal-state validation
 -> exact reference identity binding
 -> deterministic OpsLens admission
 -> metadata-only evidence
 -> STOP
```

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
```

Existing code-owned authority remains unchanged:

- source task identity and content identity;
- specialization mapping;
- source/specialist capability intersection;
- handoff proposal admission;
- specialist-task construction;
- capability authorization;
- executable-input binding;
- execution result admission;
- provider/model selection;
- retry/fallback policy;
- evidence provenance and result projection.

## Identity and provenance requirements for Gate 15.2

The next gate must freeze deterministic bindings among, at minimum:

```text
OpsLens source_task_id
OpsLens handoff proposal_id
OpsLens handoff_id
OpsLens specialist_task_id
A2A JSON-RPC request id
A2A messageId
A2A task id if a Task is produced
A2A contextId if present
A2A artifact id if an Artifact is used
peer AgentCard identity/version
protocol reference_sha256
```

A2A-generated identifiers are correlation/runtime evidence only. They never replace OpsLens content-addressed identifiers.

## Replay and failure requirements

Before the first adapter executes, Gate 15.2 must define stable behavior for:

```text
duplicate request id
duplicate messageId
unknown reference
reference hash mismatch
source/handoff/specialist identity mismatch
unknown or extra protocol fields
malformed structured part
non-terminal response when terminal is required
rejected / failed / canceled task
timeout / transport failure
contradictory task / artifact identity
```

Transport success must never imply exactly-once execution.

No automatic retry is authorized until retry semantics and duplicate effects are explicitly frozen.

## Authentication and transport consequence

Gate 15.1 authorizes no production transport.

For the first offline experiment:

```text
public Internet endpoint:       0
AWS runtime:                    0
new IAM role/policy:            0
feature-branch cloud identity:  0
standing credential:            0
```

If Gate 15.2 uses loopback HTTP to exercise the official SDK, that is local test transport and does not create a production HTTPS/authentication claim.

A future network experiment must separately decide TLS, Agent Card exposure, peer authentication, secret ownership, request bounds, and hosting/IAM. It must not inherit the Gate 14.2 AgentCore `PUBLIC` exception.

## SDK/dependency consequence

Gate 15.1 does not select or pin an A2A SDK.

Gate 15.2 must inspect the official implementation/package compatible with the stable `0.3.0` protocol and decide exact placement before adding a dependency.

Default preference:

```text
reference/dev dependency first
```

A runtime dependency is justified only by measured implementation need and package impact.

This follows the Phase 13 lesson that protocol SDK placement can affect unrelated deploy artifacts.

## MCP and AgentCore separation

A2A is a peer-agent interoperability protocol, not an MCP transport replacement and not new business authority.

Phase 13 MCP remains bounded offline interoperability over typed capability authority.

Phase 14 AgentCore remains an optional disabled-by-default lab target. A2A must not assume AgentCore as hosting substrate, and Gate 15.1 creates no AgentCore or AWS resources.

## Benefit hypothesis for the first experiment

The bounded experiment is successful only if it demonstrates all of the following without widening authority:

```text
1. official A2A protocol conformance for the selected minimal surface;
2. exact binding from protocol reference to one pre-admitted SpecialistAgentTask;
3. protocol-generated identifiers remain evidence-only;
4. unknown/tampered references fail closed;
5. capability executions remain 0;
6. model invocations remain 0 for the protocol-contract experiment;
7. no AWS/IAM/network deployment is introduced;
8. protocol overhead and failure evidence are observable.
```

If the experiment cannot preserve those properties, A2A does not proceed to a real peer/model experiment.

## Observability and cost contract for the first experiment

Gate 15.2 must record independent dimensions, not a composite score:

```text
protocol request count
peer handler count
protocol request bytes
protocol response bytes
client elapsed time
handler elapsed time
retry count
failure class
reference identity outcome
A2A task/message outcome
model invocation count
capability execution count
incremental cost
```

For an offline local adapter, infrastructure cost is expected to be `USD 0.00`; that is a scope fact, not a production cost estimate.

## Alternatives rejected

### Deploy an A2A service immediately

Rejected because no retained independent OpsLens peer currently requires a network service. Hosting, TLS, auth, lifecycle, IAM, and operations would precede evidence of protocol value.

### Re-activate the Phase 12 two-model topology as the A2A use case

Rejected because Gate 12.4 already measured and rejected that topology as default. Protocol adoption cannot erase a negative topology-retention decision.

### Treat the current in-process handoff as already requiring A2A

Rejected because a typed function boundary does not become a distributed-systems problem merely because a standard exists.

### Defer A2A entirely without any experiment

Rejected for this phase because the content-addressed Gate 12.1 handoff creates a narrow, falsifiable interoperability boundary that can be tested offline without production/runtime cost or authority expansion.

### Use MCP instead

Rejected as a false equivalence. MCP exposes bounded tools/capabilities; A2A models interaction between agent peers. Their authority and lifecycle semantics differ.

## Consequences

Positive:

- A2A learning is tied to an existing OpsLens authority contract;
- no public runtime is invented;
- no rejected multi-agent topology is silently revived;
- protocol identity remains separate from business authority;
- the next implementation can be strict, reference-only, and fail closed;
- AWS/IAM/cost impact remains zero for Gate 15.1.

Costs:

- the first experiment is intentionally less feature-rich than the full A2A protocol;
- a local/in-process result does not prove production interoperability, authentication, or SLOs;
- a later real peer experiment still requires an independent value hypothesis and retention decision.

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

> Freeze and implement the smallest official A2A `0.3.0` reference-only adapter contract offline, including raw protocol validation, identity binding, failure/replay fixtures, SDK/dependency placement evidence, and zero model/capability execution.

No network deployment or model invocation is authorized by this ADR.

## Production engineering / AIP-C01 learning connection

Although A2A itself is not an AWS-specific authority mechanism, this decision exercises production GenAI engineering skills that remain relevant to AWS workloads: separate protocol authentication from application authorization, keep model/agent output untrusted until deterministic admission, minimize IAM and runtime surface, freeze evaluation before execution, preserve observability and cost dimensions independently, and introduce distributed-system complexity only behind a measurable hypothesis.
