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
| 14 | Amazon Bedrock AgentCore | 🚧 In progress — Gates 14.1 and 14.2 complete; retention decision pending formalization |
| 15 | A2A | ⏳ Planned |
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
```

## Completed foundation — Phases 0–10

Phases 0–10 are complete. Detailed architecture, evidence, AWS/IAM decisions, and failure-path records remain in ADRs, labs, and Git history.

The retained platform includes AWS foundation, threat-intelligence ingestion, deterministic vulnerability correlation, repository intelligence over immutable inert evidence, deterministic risk prioritization, bounded semantic planning and SQL compilation, Bedrock Knowledge Base retrieval with Amazon S3 Vectors, hybrid evidence composition, governed public-analysis admission, and operational telemetry contracts.

## Phase 11 — Single-Agent Baseline — COMPLETE

Completed sequence:

```text
Gate 11.1 — Capability Authorization Contract                  COMPLETE / MERGED
Gate 11.2 — Typed Capability Bindings + Offline Executor       COMPLETE / MERGED
Gate 11.3 — Frozen Single-Agent Evaluation Fixture             COMPLETE / MERGED
Gate 11.4 — First Bounded Model Reasoning Baseline             COMPLETE / MERGED
Gate 11.5 — Measured Optimization Decision                     COMPLETE / MERGED — NO-CHANGE
Gate 11.6 — Phase 11 Closeout                                  COMPLETE / MERGED
```

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

Phase 12 tested specialization rather than assuming that more agents are better.

Retained outcome:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
```

The real two-model experiment produced no quality lift and increased invocations, tokens, latency, and cost. No rescue/tuning experiment is authorized without a new hypothesis.

Closeout:

```text
labs/evidence/phase-12-closeout-v1.json
docs/adr/0046-phase12-multi-agent-closeout.md
```

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

Closeout:

```text
labs/evidence/phase-13-closeout-v1.json
docs/adr/0051-phase13-mcp-closeout.md
```

## Phase 14 — Amazon Bedrock AgentCore — IN PROGRESS

Phase 14 evaluates managed runtime value against measured OpsLens needs. AgentCore adoption is not automatic.

### Gate 14.1 — AgentCore Runtime Capability-Fit and Authority Boundary — COMPLETE / MERGED

Gate 14.1 authorized only one bounded experiment:

```text
AgentCore Runtime:        GO TO ONE BOUNDED EXPERIMENT ONLY
first hosted boundary:    retained Phase 11 bounded reasoning
protocol:                 HTTP
authentication:           IAM SigV4
direct-code artifact:     preferred from measured packaging evidence
capability executions:    0
adaptive retries:         0
adaptive fallbacks:       0
MCP runtime promotion:    not authorized
A2A:                      deferred
runtime-exposure truth:   not created
```

References:

```text
docs/adr/0052-agentcore-runtime-capability-fit.md
labs/phase-14-gate-14-1-agentcore-runtime-capability-fit.md
```

### Gate 14.2 — First Bounded AgentCore HTTP/SigV4 Runtime Experiment — COMPLETE / MEASURED

Frozen contract:

```text
agentcore-runtime-invocation:v1
```

Bounded path:

```text
AgentCore Runtime HTTP invocation
 -> exact request admission
 -> retained SingleAgentTask authority
 -> fixed provider/model selection owned by code
 -> exactly one bounded Bedrock reasoning call
 -> transient untrusted model output
 -> deterministic parser
 -> existing AgentActionProposal
 -> existing authorize_agent_action(...)
 -> content-addressed metadata-only projection
 -> STOP before capability execution
```

Terminal successful run:

```text
source main:                e5072ec68b421677359cebb1eb449578ef7d5b49
workflow run:               34378942784 / run #11 / SUCCESS
job:                        102558703872
runtime:                    opslens_dev_bounded_runtime-Cl8aNBDGzh
network:                    PUBLIC — dev-only exception
artifact SHA256:            a846034ad646c4f6383ac08e47d9ed065b4a9f3349c14104db49a2d510b3ec88
Phase 11 corpus SHA256:     3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
replay:                     6 / 6 PASS
input/output/total tokens:  3291 / 104 / 3395
SDK retries:                0
capability executions:      0
transport elapsed sum:      19981 ms
deploy-role invocation:     AccessDeniedException / HTTP 403
cleanup:                    0 add / 0 change / 3 destroy
cleanup verifier:           RESOURCE_NOT_FOUND
```

Measured cost:

```text
AgentCore Runtime:  USD 0.002380345136128484
Bedrock inference:  USD 0.004192100000000000
TOTAL:              USD 0.006572445136128483
```

No monthly extrapolation is part of the gate.

#### Measured IAM/lifecycle lessons

Attempts #1–#10 are retained as first-class evidence. They measured dependencies and lifecycle behavior around:

```text
GitHub Actions src-layout execution
CreateAgentRuntimeEndpoint
runtime create-time TagResource
Runtime Identity service-linked-role bootstrap
managed workload-identity TagResource
CreateWorkloadIdentity
workload-identity directory authorization
DeleteWorkloadIdentity
GetAgentRuntime through DELETING
```

Final deployment authority remains:

```text
main-only GitHub OIDC
NO deployment-role InvokeAgentRuntime
NO deployment-role iam:CreateServiceLinkedRole
NO deployment-role GetWorkloadIdentity
NO feature-branch OIDC widening
```

`GetAgentRuntime` is an exact-family lifecycle read without runtime ResourceTag conditions. Mutation remains resource-tag-gated.

Evidence:

```text
labs/phase-14-gate-14-2-bounded-agentcore-runtime.md
labs/evidence/phase-14-gate-14-2-final-runtime-experiment-v1.json
docs/adr/0053-bounded-agentcore-direct-code-public-network-experiment.md
```

#### Gate 14.2 non-claims

Gate 14.2 does not prove or authorize:

```text
AgentCore as the default/production runtime
PUBLIC networking for production
production SLOs
production security approval
runtime deployment == runtime exposure
runtime telemetry == business truth
AgentCore hosting == business authorization
MCP runtime hosting
A2A
Gateway/Policy
Memory
Browser
Code Interpreter
capability execution
```

### Phase 14 next decision — NOT YET NUMBERED

Gate 14.2 is complete. The roadmap deliberately does **not** invent `Gate 14.3` merely because another step is expected.

After the final Gate 14.2 state sync is merged, a separate issue should formalize the next gate only if the evidence leaves a concrete decision gap.

The current architectural question is:

> Does the measured AgentCore hosting/session/operational value justify its IAM, lifecycle, network, latency, cost, and operational surface for the retained OpsLens reasoning architecture?

The decision may legitimately retain, modify, or reject AgentCore Runtime as a default. No outcome is preselected.

## Phase 15 — A2A — PLANNED

Introduce agent-to-agent interoperability only when agents have real service/lifecycle boundaries and a concrete interoperability problem exists.

## Phase 16 — Runtime Exposure with Amazon Inspector — PLANNED

Add independent runtime evidence while preserving:

> **Repository Risk != Runtime Exposure.**

## Phase 17 — Security Hardening — PLANNED

Perform cross-cutting IAM, data protection, abuse, threat-model, dependency, and operational hardening.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 remains separate consumer-side work for the Governed LLM Gateway project. It must not be modified or merged as a side effect of Phase 14 state synchronization.
