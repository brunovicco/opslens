# OpsLens Documentation

OpsLens documentation is organized around current architecture, implementation state, incremental roadmap, ADRs, gate laboratories, and immutable evaluation/runtime evidence.

## Primary documents

- [`architecture.md`](architecture.md) — accumulated architecture baseline; later phases are additionally frozen through ADRs and gate labs.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture baseline synchronized with the English version.
- [`current-state.md`](current-state.md) — exact implementation checkpoint and next authorized gate.
- [`roadmap.md`](roadmap.md) — incremental phase/gate plan and completion status.
- [`adr/`](adr/) — accepted architecture decisions.
- [`../labs/`](../labs/) — gate laboratories and immutable evidence references.

## Current implementation checkpoint

```text
Phase 0  AWS Foundation                         COMPLETE
Phase 1  EPSS Vertical Slice                    COMPLETE
Phase 2  Threat Intelligence Data Lake          COMPLETE
Phase 3  Vulnerability Correlation Engine       COMPLETE
Phase 4  Repository Intelligence                COMPLETE
Phase 5  Risk Prioritization Engine             COMPLETE
Phase 6  Semantic Query Layer                   COMPLETE
Phase 7  Knowledge Retrieval with Bedrock       COMPLETE
Phase 8  Hybrid Retrieval                       COMPLETE
Phase 9  Public Analyze Your Repository         COMPLETE
Phase 10 Observability & Operational Excellence COMPLETE
Phase 11 Single-Agent Baseline                  COMPLETE
Phase 12 Multi-Agent Architecture               COMPLETE
Phase 13 MCP                                    COMPLETE
Phase 14 Amazon Bedrock AgentCore               COMPLETE
Phase 15 A2A                                    IN PROGRESS
  Gate 15.1 capability fit / authority          COMPLETE / GO OFFLINE ONLY
  Gate 15.1 protocol-baseline correction        COMPLETE / A2A 1.0.0
  Gate 15.2 reference-only offline adapter      NEXT / AUTHORIZED
```

Permanent separations include:

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
A2A authentication != capability authorization
A2A protocol binding != business authority
Repository Risk != Runtime Exposure
```

## Retained reasoning reference

Phase 11 remains the default/reference measured reasoning architecture:

```text
quality:                    6/6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
SDK retries:                0
capability executions:      0
derived six-case cost:      USD 0.0041921
```

Historical evidence:

```text
../labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
```

## Phase 12 — retained specialization boundary

Phase 12 retained deterministic specialization/handoff and comparison discipline, but did not retain the measured two-model topology as the default reasoning path because it produced no quality lift and increased invocation count, tokens, latency, and cost.

The reusable boundary is:

```text
TriageAgentTask
 -> untrusted MultiAgentHandoffProposal
 -> deterministic source binding
 -> code-owned specialization mapping
 -> deterministic capability intersection
 -> AuthorizedMultiAgentHandoff | abstention | fail closed
 -> SpecialistAgentTask
```

References:

- [`adr/0042-bounded-multi-agent-specialization-handoff.md`](adr/0042-bounded-multi-agent-specialization-handoff.md)
- [`adr/0045-do-not-retain-two-model-topology-without-measured-lift.md`](adr/0045-do-not-retain-two-model-topology-without-measured-lift.md)
- [`adr/0046-phase12-multi-agent-closeout.md`](adr/0046-phase12-multi-agent-closeout.md)

## Phase 13 — MCP — complete

Phase 13 demonstrates official MCP interoperability while preserving existing deterministic authority. It closes at a bounded offline/in-process boundary instead of introducing a public runtime without a concrete consumer requirement.

Retained contracts:

```text
mcp-capability-exposure:v1
mcp-capability-execution:v1
mcp-result-projection:v1
```

References:

- [`adr/0047-bounded-mcp-capability-exposure.md`](adr/0047-bounded-mcp-capability-exposure.md)
- [`adr/0048-bounded-offline-mcp-protocol-adapter.md`](adr/0048-bounded-offline-mcp-protocol-adapter.md)
- [`adr/0049-bounded-mcp-capability-execution-bridge.md`](adr/0049-bounded-mcp-capability-execution-bridge.md)
- [`adr/0050-bounded-mcp-structured-result-projection.md`](adr/0050-bounded-mcp-structured-result-projection.md)
- [`adr/0051-phase13-mcp-closeout.md`](adr/0051-phase13-mcp-closeout.md)
- [`../labs/evidence/phase-13-closeout-v1.json`](../labs/evidence/phase-13-closeout-v1.json)

## Phase 14 — AgentCore — complete

Phase 14 measured one bounded HTTP/SigV4 Runtime experiment, retained the implementation/evidence only as an optional disabled-by-default lab target, rejected AgentCore as the default OpsLens reasoning runtime, and removed the standing experiment-specific GitHub IAM after the retention decision.

Terminal experiment/reference facts:

```text
Gate 14.2 replay:          6 / 6 PASS
AgentCore Runtime cost:    USD 0.002380345136128484
Bedrock inference cost:    USD 0.0041921
total observed cost:       USD 0.006572445136128483
Runtime cleanup:           RESOURCE_NOT_FOUND
Gate 14.4 IAM cleanup:     0 add / 0 change / 4 destroy
post-apply convergence:    NO CHANGES
```

Final retained outcome:

```text
Phase 11 direct Bedrock reasoning:          RETAIN / DEFAULT
AgentCore implementation/evidence:          RETAIN AS OPTIONAL LAB TARGET
AgentCore managed Runtime as default:        DO NOT RETAIN
standing AgentCore Runtime resources:        NONE
standing experiment-specific GitHub IAM:    REMOVED
Gate 14.2 PUBLIC exception:                  NOT RETAINED
Runtime Identity service-linked role:        RETAIN pending separate safety proof
```

References:

- [`adr/0052-agentcore-runtime-capability-fit.md`](adr/0052-agentcore-runtime-capability-fit.md)
- [`adr/0053-bounded-agentcore-direct-code-public-network-experiment.md`](adr/0053-bounded-agentcore-direct-code-public-network-experiment.md)
- [`adr/0054-retain-agentcore-only-as-optional-lab-target.md`](adr/0054-retain-agentcore-only-as-optional-lab-target.md)
- [`adr/0055-remove-standing-agentcore-experiment-iam.md`](adr/0055-remove-standing-agentcore-experiment-iam.md)
- [`../labs/evidence/phase-14-gate-14-4-agentcore-iam-cleanup-postapply-v1.json`](../labs/evidence/phase-14-gate-14-4-agentcore-iam-cleanup-postapply-v1.json)

## Phase 15 — A2A — in progress

### Gate 15.1 — capability fit / authority boundary

The first Gate 15.1 revision used a historical A2A `0.3.0` page and incorrectly described it as the current latest stable protocol. The architecture decision is unchanged, but the protocol baseline was corrected before Gate 15.2 implementation.

Authoritative baseline:

```text
A2A protocol:                   1.0.0
release date:                   2026-03-12
previous protocol:              0.3.0
standard bindings:              JSONRPC / GRPC / HTTP+JSON
first OpsLens binding choice:   JSONRPC
Python SDK latest observed:     1.1.4
SDK pinned by Gate 15.1:        NO
```

A2A v1.0 uses Agent Card `supportedInterfaces`; each interface declares `url`, `protocolBinding`, and `protocolVersion`. JSON-RPC is an explicit Gate 15.2 scope choice rather than a claim that A2A has only one binding.

Finding:

```text
retained independently deployed agent peer: NO
current in-process handoff needs A2A:        NO
bounded protocol-fit hypothesis:            YES
```

Decision:

```text
GO TO ONE BOUNDED OFFLINE/IN-PROCESS INTEROPERABILITY EXPERIMENT
```

The first experiment is reference-only:

```text
pre-admitted SpecialistAgentTask
 -> code-owned local reference
 -> {handoff_id, specialist_task_id, reference_sha256}
 -> A2A 1.0 SendMessage over selected JSONRPC binding
 -> bounded peer reference resolution
 -> terminal Message or Task metadata
 -> deterministic OpsLens admission
 -> STOP before model/capability execution
```

Gate 15.1 added no SDK dependency, endpoint, model call, capability execution, AWS resource, IAM permission, or AgentCore runtime.

References:

- [`adr/0056-bounded-a2a-capability-fit.md`](adr/0056-bounded-a2a-capability-fit.md)
- [`../labs/phase-15-gate-15-1-a2a-capability-fit.md`](../labs/phase-15-gate-15-1-a2a-capability-fit.md)
- [`../labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v1.json`](../labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v1.json) — historical first assessment; protocol-version claim superseded
- [`../labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v2.json`](../labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v2.json) — authoritative corrected evidence

### Next authorized gate — Gate 15.2

Freeze and implement the smallest selected A2A `1.0` reference-only adapter contract offline using one explicitly selected JSON-RPC binding.

Required properties:

```text
raw protocol validation before domain admission
AgentInterface protocolBinding/version admission
exact reference binding
fail-closed unsupported binding/version behavior
fail-closed tamper/unknown-reference behavior
duplicate/replay/failure fixtures
inspect Python SDK 1.1.4 before any pin
SDK/dependency placement evidence
request/response byte and local latency evidence
model invocations = 0
capability executions = 0
AWS/IAM/runtime deployment = 0
```

Gate 15.2 must not assume AgentCore hosting or promote MCP into a public runtime.
