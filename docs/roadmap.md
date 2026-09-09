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
 -> branch hygiene
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
| 13 | MCP | ✅ Complete — bounded offline MCP retained |
| 14 | Amazon Bedrock AgentCore | ✅ Complete — optional lab target retained; standing experiment IAM removed |
| 15 | A2A | 🚧 In progress — Gate 15.1 complete/corrected to A2A 1.0; bounded offline reference adapter next |
| 16 | Runtime Exposure with Amazon Inspector | ⏳ Planned |
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

Agentic/interoperability/runtime phases preserve:

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
structured model output != trusted proposal
model selection != capability authority
MCP tool name != capability authorization
MCP tool exposure != executable argument authority
MCP call admission != capability execution
MCP capability execution != business-result transport
MCP result admission != result-projection authority
MCP result projection != public runtime exposure
MCP transport success != business/evidence truth
AgentCore hosting != business authorization
runtime authentication != capability authorization
runtime session != identity authority
runtime execution role != model/tool authority
runtime transport success != business/evidence truth
runtime telemetry != business truth
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
```

## Completed foundation — Phases 0–10

Phases 0–10 are complete. Detailed architecture, evidence, AWS/IAM decisions, and failure-path records remain in ADRs, labs, and Git history.

The retained platform includes AWS foundation, threat-intelligence ingestion, deterministic vulnerability correlation, repository intelligence over immutable inert evidence, deterministic risk prioritization, bounded semantic planning and SQL compilation, Bedrock Knowledge Base retrieval with Amazon S3 Vectors, hybrid evidence composition, governed public-analysis admission, and operational telemetry contracts.

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
corpus_sha256:              3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
```

This remains the default/reference reasoning architecture until a superior topology is demonstrated against frozen evidence.

## Phase 12 — Multi-Agent Architecture — COMPLETE

Retained outcome:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
```

The real two-model experiment produced no quality lift and increased invocations, tokens, latency, and cost. Gate 12.1 remains reusable as a deterministic content-addressed specialization/handoff authority boundary.

## Phase 13 — MCP — COMPLETE

MCP is retained as an interoperability boundary over existing governed capability authority.

Retained contracts:

```text
mcp-capability-exposure:v1
mcp-capability-execution:v1
mcp-result-projection:v1
```

Retained path:

```text
Phase 11 typed capability authority
 -> closed MCP tool identity
 -> official MCP SDK reference-only adapter
 -> raw exact-key-set argument refusal
 -> deterministic invocation resolution + admission
 -> exactly one existing typed executor attempt
 -> existing typed result admission
 -> structured result projection for structured_security_query only
 -> bounded CVE + EPSS rows
 -> STOP before public/network runtime
```

Public/network MCP hosting remains an explicit non-claim. The MCP SDK stays development-only in the retained architecture.

## Phase 14 — Amazon Bedrock AgentCore — COMPLETE

Phase 14 evaluated managed runtime value against measured OpsLens needs instead of preselecting adoption.

### Gate 14.1 — Runtime capability fit — COMPLETE

Authorized only one bounded experiment:

```text
AgentCore Runtime:        GO TO ONE BOUNDED EXPERIMENT ONLY
first hosted boundary:    retained Phase 11 bounded reasoning
protocol:                 HTTP
authentication:           IAM SigV4
capability executions:    0
MCP runtime promotion:    not authorized
A2A:                      deferred
runtime-exposure truth:   not created
```

### Gate 14.2 — bounded Runtime experiment — COMPLETE / MEASURED

Terminal measured result:

```text
workflow run:               34378942784 / run #11 / SUCCESS
replay:                     6 / 6 PASS
input/output/total tokens:  3291 / 104 / 3395
SDK retries:                0
capability executions:      0
transport elapsed sum:      19981 ms
deploy-role invocation:     AccessDeniedException / HTTP 403
runtime cleanup:            RESOURCE_NOT_FOUND
AgentCore Runtime cost:     USD 0.002380345136128484
Bedrock inference cost:     USD 0.0041921
total observed cost:        USD 0.006572445136128483
```

The `PUBLIC` network mode was a dev-only experiment exception and is not a retained production decision.

### Gate 14.3 — Runtime retention decision — COMPLETE / RETAIN WITH CHANGES

```text
default OpsLens reasoning runtime:            DO NOT RETAIN AgentCore
Phase 11 direct Bedrock reasoning reference: RETAIN
AgentCore implementation/evidence:           RETAIN
PUBLIC network mode:                         DO NOT RETAIN
standing AgentCore Runtime resources:        DO NOT RETAIN
standing experiment-specific IAM:            DO NOT RETAIN without an active experiment
```

The six-case quality/model/token evidence was unchanged relative to Phase 11. AgentCore added USD 0.002380345136128484 of measured Runtime cost, or 56.78168784448091% relative to the unchanged USD 0.0041921 inference component. Raw latency boundaries were not normalized into a percentage comparison.

### Gate 14.4 — standing experiment IAM cleanup — COMPLETE / VERIFIED

```text
implementation merge: 9913c3cbf5f2239d6445042a139a9cca890590c8
plan:                 0 add / 0 change / 4 destroy
apply:                0 add / 0 change / 4 destroy
post-apply plan:      NO CHANGES
```

Independent verification:

```text
OpsLensAgentCoreReplayRole:                 ABSENT
OpsLensAgentCoreDeployDevAccess:            ABSENT
AgentCore deploy policy attachment:         []
OpsLensGitHubDeployRole:                    PRESENT
AWSServiceRoleForBedrockAgentCoreRuntimeIdentity:
                                            PRESENT / intentionally retained
```

Final retained Phase 14 architecture:

```text
Phase 11 direct Bedrock reasoning:           DEFAULT / RETAIN
AgentCore implementation/evidence:           RETAIN AS OPTIONAL LAB TARGET
AgentCore managed Runtime as default:         DO NOT RETAIN
standing AgentCore Runtime resources:         NONE
standing experiment-specific GitHub IAM:     REMOVED
Gate 14.2 PUBLIC exception:                   NOT RETAINED
Runtime Identity service-linked role:         RETAIN pending separate safety proof
```

## Phase 15 — A2A — IN PROGRESS

Phase 15 evaluates A2A as an agent-peer interoperability boundary without presuming a distributed runtime.

### Gate 15.1 — capability fit / authority boundary — COMPLETE / CORRECTED

The original Gate 15.1 revision incorrectly treated the historical versioned `0.3.0` page as the latest stable A2A baseline. The architecture decision remains valid, but the authoritative protocol evidence is now corrected.

Current official baseline verified on 2026-09-09:

```text
Agent2Agent Protocol:          1.0.0
release date:                  2026-03-12
previous protocol:             0.3.0
standard protocol bindings:    JSONRPC / GRPC / HTTP+JSON
first OpsLens binding choice:  JSONRPC
Python SDK latest observed:    1.1.4
Gate 15.1 SDK pin:             NONE
```

A2A v1.0 Agent Cards advertise `supportedInterfaces`; each `AgentInterface` declares its own `url`, `protocolBinding`, and `protocolVersion`. OpsLens choosing JSON-RPC for Gate 15.2 is therefore an explicit experiment scope decision, not a protocol-wide claim.

Current architecture finding:

```text
retained independent OpsLens agent peer:    NO
current in-process handoff needs A2A:        NO
bounded reference-interoperability test:    YES
```

The retained Gate 12.1 handoff is a meaningful protocol boundary because it already creates one content-addressed `SpecialistAgentTask` after deterministic source binding and capability narrowing. That does not mean the existing in-process path should become distributed.

Gate 15.1 hypothesis:

> A minimal A2A adapter can carry only a reference to one already-admitted specialist task across a bounded peer boundary and re-bind the protocol response to existing OpsLens identities without allowing protocol data, peer metadata, task state, artifacts, or protocol binding to create capability or business authority.

Decision:

```text
GO TO ONE BOUNDED OFFLINE/IN-PROCESS INTEROPERABILITY EXPERIMENT
```

First experiment bounds:

```text
AgentCard:                  minimal required surface
supportedInterfaces:       one interface only
protocolBinding:           JSONRPC
protocolVersion:           1.0
core operation:            SendMessage
terminal Message/Task:     exactly bounded
reference-only input:      yes
streaming:                 no
push notifications:        no
extended auth flow:        no
multi-turn:                no
model invocations:         0
capability executions:     0
AWS resources:             0
new IAM:                   0
public endpoint:           0
```

Preferred reference path:

```text
pre-admitted SpecialistAgentTask
 -> local code-owned reference registry
 -> {handoff_id, specialist_task_id, reference_sha256}
 -> A2A 1.0 SendMessage over selected JSONRPC binding
 -> bounded peer reference resolution
 -> terminal protocol metadata
 -> deterministic OpsLens admission
 -> STOP before model/capability execution
```

Gate 15.1 records:

```text
docs/adr/0056-bounded-a2a-capability-fit.md
labs/phase-15-gate-15-1-a2a-capability-fit.md
labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v1.json  # historical protocol claim superseded
labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v2.json  # authoritative correction
```

### Gate 15.2 — bounded offline reference-only adapter — NEXT / AUTHORIZED

Gate 15.2 must freeze the contract before implementation/framework coercion and then prove the smallest selected A2A `1.0` JSON-RPC slice offline.

Required work:

```text
inspect official Python SDK 1.1.4 package/framework surface
freeze exact dependency placement before pinning
freeze reference-only request contract
freeze AgentCard supportedInterfaces projection
freeze raw protocol validation before domain admission
admit protocolBinding = JSONRPC and protocolVersion = 1.0 explicitly
bind request/message/task/context IDs as evidence only
freeze duplicate/replay/failure semantics
cover unsupported binding/version fail-closed behavior
cover unknown/tampered reference fail-closed behavior
measure request/response bytes and local latency
keep model calls = 0
keep capability executions = 0
keep AWS/IAM/runtime deployment = 0
```

No network service, model call, capability execution, AgentCore hosting, or MCP public runtime is authorized by Gate 15.2.

A later A2A peer/model experiment requires a new gate and a separate measurable value hypothesis.

## Phase 16 — Runtime Exposure with Amazon Inspector — PLANNED

Add independent runtime evidence while preserving:

> **Repository Risk != Runtime Exposure.**

## Phase 17 — Security Hardening — PLANNED

Perform cross-cutting IAM, data protection, abuse, threat-model, dependency, and operational hardening.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 remains separate consumer-side work for the Governed LLM Gateway project. It must not be modified or merged as a side effect of Phase 15 work.
