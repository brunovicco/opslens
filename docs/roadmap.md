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
| 15 | A2A | 🚧 In progress — Gate 15.2 measured offline adapter complete; official-SDK conformance next |
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
A2A generated id != OpsLens content identity
A2A SDK acceptance != OpsLens admission authority
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

The original Gate 15.1 revision incorrectly treated the historical versioned `0.3.0` page as the latest stable A2A baseline. The architecture decision remains valid, but the authoritative protocol evidence is corrected to A2A `1.0.0`.

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

Current architecture finding:

```text
retained independent OpsLens agent peer:    NO
current in-process handoff needs A2A:        NO
bounded reference-interoperability test:    YES
```

Decision:

```text
GO TO ONE BOUNDED OFFLINE/IN-PROCESS INTEROPERABILITY EXPERIMENT
```

Gate 15.1 records:

```text
docs/adr/0056-bounded-a2a-capability-fit.md
labs/phase-15-gate-15-1-a2a-capability-fit.md
labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v1.json  # historical protocol claim superseded
labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v2.json  # authoritative correction
```

### Gate 15.2 — bounded offline reference-only adapter — COMPLETE / MEASURED

Gate 15.2 froze and proved:

```text
a2a-reference-interoperability:v1
```

Retained path:

```text
pre-admitted SpecialistAgentTask
 -> content-addressed A2AReference
 -> lab-only code-owned registry
 -> strict A2A 1.0 JSON-RPC SendMessage projection
 -> raw duplicate-key / exact-key-set validation
 -> code-owned reference resolution
 -> bounded Message or terminal completed Task metadata
 -> deterministic OpsLens result admission
 -> STOP before model/capability execution
```

Protected merge:

```text
PR:               #231
main SHA:         3a9adfdcfdd206d1c932a2d90bcb312377596b70
measurement head: c27a2362df4971a7b619be33dcaacd2bfe2a2369
```

SDK/dependency outcome:

```text
official Python SDK inspected: 1.1.4
a2a-sdk pinned:                NO
new runtime dependencies:      0
```

The selected wire profile can be verified with deterministic stdlib code, so Gate 15.2 does not widen deployed dependencies. The official SDK remains a potential independent conformance oracle, never OpsLens admission authority.

Measured local result:

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

Exact implementation validation before protected merge:

```text
A2A CI:        34406512226 / #7  SUCCESS
Multi-Agent:   34406512227 / #42 SUCCESS
AgentCore CI:  34406512228 / #70 SUCCESS
```

Gate 15.2 proves OpsLens-owned offline protocol projection/admission. It does **not** yet prove that an independent official implementation accepts the same frozen profile.

Records:

```text
docs/adr/0057-bounded-offline-a2a-reference-adapter.md
labs/phase-15-gate-15-2-bounded-offline-a2a-reference-adapter.md
labs/evidence/phase-15-gate-15-2-bounded-offline-a2a-reference-adapter-v1.json
```

### Gate 15.3 — bounded offline official-SDK conformance — NEXT / AUTHORIZED

Use the official Python A2A SDK only as an independent protocol-conformance oracle for the already-frozen Gate 15.2 happy path.

Required boundary:

```text
OpsLens A2AReference + raw validation:    AUTHORITATIVE
OpsLens content identity/admission:       AUTHORITATIVE
official SDK parsing/acceptance:          CONFORMANCE ORACLE ONLY
SDK-created business/capability authority: 0
```

Required evidence:

```text
pin exact SDK version in development scope only if needed
record lockfile/package impact
prove runtime dependency surface remains unchanged
validate frozen AgentCard through official SDK types/parser
validate frozen SendMessage happy-path through official SDK representation
compare canonical protocol semantics, not incidental serializer ordering
record any optional-field/default coercion differences
keep OpsLens negative/fail-closed parser authoritative
keep model calls = 0
keep capability executions = 0
keep network deployment = 0
keep AWS/IAM changes = 0
keep business-result transport = 0
```

A real peer/network experiment remains deferred. Passing official-SDK conformance alone does not create a reason to deploy another agent service.

## Phase 16 — Runtime Exposure with Amazon Inspector — PLANNED

Add independent runtime evidence while preserving:

> **Repository Risk != Runtime Exposure.**

## Phase 17 — Security Hardening — PLANNED

Perform cross-cutting IAM, data protection, abuse, threat-model, dependency, and operational hardening.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 remains separate consumer-side work for the Governed LLM Gateway project. It must not be modified or merged as a side effect of Phase 15 work.
