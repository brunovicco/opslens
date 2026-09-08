# OpsLens — Incremental Roadmap

_Last updated: 2026-09-08_

OpsLens advances in small, demonstrable, observable, reversible gates.

Default engineering loop:

```text
concept
 -> architecture decision
 -> IAM / trust boundary when applicable
 -> implementation
 -> success test
 -> failure test
 -> observability
 -> cost
 -> documentation / ADR
 -> logical merge
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
| 13 | MCP | 🚧 In progress — Gate 13.1 complete; Gate 13.2 next |
| 14 | Amazon Bedrock AgentCore | ⏳ Planned |
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

Agentic/interoperability phases additionally preserve:

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
structured model output != trusted proposal
synthetic fixture conformance != model quality
model selection != capability authority
MCP tool name != capability authorization
MCP tool exposure != executable argument authority
MCP call admission != capability execution
MCP transport success != business/evidence truth
MCP result != runtime exposure truth
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
report_sha256:              724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

This remains the default/reference measured reasoning architecture until a superior topology is demonstrated against a frozen benchmark.

## Phase 12 — Multi-Agent Architecture — COMPLETE

Phase 12 tested specialization as an evidence-backed architecture hypothesis rather than assuming that more agents are better.

Completed sequence:

```text
Gate 12.1 — Bounded Specialization Handoff Contract            COMPLETE / MERGED
Gate 12.2 — Comparative Multi-Agent Evaluation Contract        COMPLETE / MERGED
Gate 12.3 — First Bounded Real Two-Model Comparison            COMPLETE / MERGED
Gate 12.4 — Measured Multi-Agent Retention Decision            COMPLETE / MERGED
Gate 12.5 — Multi-Agent Phase Closeout                         COMPLETE / MERGED
```

Retained outcome:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
```

Measured Phase 11 versus Gate 12.3 deltas:

```text
quality:                    6/6 -> 6/6      no lift
model invocations:          6 -> 10         +66.67%
total tokens:               3395 -> 5982    +76.20%
provider latency median:    809.5 -> 1694   +109.26%
client elapsed median:      977.5 -> 2135   +118.41%
derived cost:               0.0041921 -> 0.0074338 USD  +77.33%
SDK retries:                0 -> 0
capability executions:      0 -> 0
```

Closeout evidence:

```text
labs/evidence/phase-12-closeout-v1.json
labs/phase-12-gate-12-5-multi-agent-closeout.md
docs/adr/0046-phase12-multi-agent-closeout.md
PR #178 merge: aca4264e9c98f81c239b44b55c8772ef02debc4c
final Phase 12 state sync: 913a3302534098b429d3955c770d025480289a3f
```

## Phase 13 — MCP — IN PROGRESS

MCP is introduced as an interoperability boundary over existing governed capability authority. It does not become another authorization or generic execution plane.

### Gate 13.1 — Bounded MCP Capability Exposure Contract — COMPLETE / MERGED

Frozen contract:

```text
mcp-capability-exposure:v1
```

Closed one-to-one tool surface:

```text
opslens.structured_security_query   -> structured_security_query
opslens.knowledge_guidance          -> knowledge_guidance
opslens.hybrid_security_answer      -> hybrid_security_answer
opslens.public_repository_analysis  -> public_repository_analysis
```

Authority path:

```text
existing AuthorizedAgentAction
 + existing typed AgentCapabilityInvocation
 -> closed McpToolName
 -> deterministic tool/capability match
 -> content-addressed McpToolCallAdmission
 -> STOP
```

The typed `single-agent-execution:v1` invocation remains the executable-input authority. MCP cannot author arbitrary `args`/`kwargs`, SQL, URLs, shell commands, credentials, provider/model choices, retry/fallback policy, or execution results.

Gate 13.1 deliberately adds no MCP SDK/runtime and performs no capability execution.

Exact merge evidence:

```text
issue #180
PR #181 final head:      340f2d7beee3640bd14455de635fe3ee4b6cc5cc
PR merge test commit:    166e5626f52bdbabfd306b0e3152b02c1620ee5f
MCP CI:                  34223369166 / run #3 / PASS
job:                     102051514632
uv lock --check:         PASS
MCP import smoke:        PASS
Ruff:                    PASS
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest MCP slice:        7 passed in 0.19s
review threads:          0
model invocations:       0
capability executions:   0
MCP SDK/runtime:         0
new AWS/IAM:             0
merge SHA:               322922aed4abec3b2266a18d15d8145df974a7d1
```

Architecture record and lab:

```text
docs/adr/0047-bounded-mcp-capability-exposure.md
labs/phase-13-gate-13-1-bounded-mcp-capability-exposure.md
```

### Gate 13.2 — Bounded MCP Protocol Adapter / Offline Interoperability — NEXT

Gate 13.2 may introduce a real MCP protocol adapter, but only against the already-frozen Gate 13.1 authority contract.

Proposed bounded path:

```text
MCP protocol tool call
 -> exact closed tool identity
 -> bounded invocation reference
 -> deterministic server-side resolution to existing typed AgentCapabilityInvocation
 -> Gate 13.1 admit_mcp_tool_call(...)
 -> content-minimized admission response/evidence
 -> STOP before execute_authorized_capability(...)
```

Entry constraints:

```text
1. verify the current official MCP Python SDK/API before adding a dependency
2. pin the selected SDK deliberately if adopted
3. protocol input references an already-created typed invocation; it does not author arbitrary business args
4. resolution must recover the exact invocation identity or fail closed
5. tool/capability matching remains Gate 13.1 deterministic authority
6. unknown/missing/forged invocation references fail closed
7. no dynamic tool registry
8. STOP before capability execution
9. first interoperability proof should be offline/in-process or stdio
10. no public network deployment, AWS/IAM expansion, or authentication design without concrete need
11. protocol success remains distinct from business/evidence truth
12. AgentCore, A2A, and runtime exposure remain separate later decisions
```

A real protocol adapter is retained only if it preserves the frozen authority model without creating a second executable-input surface.

### Phase 13 continuation rules

```text
1. MCP tool identity never grants capability authorization
2. MCP arguments never bypass typed invocation creation/admission
3. transport/framework code depends on the provider-neutral MCP boundary, not vice versa
4. protocol errors are admitted only through stable content-free categories
5. capability execution and result transport require separate gates
6. public/network runtime and authentication require separate evidence and least-privilege decisions
7. no framework adoption merely for certification coverage
8. Repository Risk != Runtime Exposure remains frozen
9. PR #89 remains deferred cross-project work
```

## Phase 14 — Amazon Bedrock AgentCore — PLANNED

Evaluate managed runtime capabilities against measured OpsLens needs rather than adopting them for certification coverage alone.

## Phase 15 — A2A — PLANNED

Add agent-to-agent interoperability only after stable boundaries exist and a concrete interoperability need is demonstrated.

## Phase 16 — Runtime Exposure with Amazon Inspector — PLANNED

Add independent runtime evidence without conflating repository risk with runtime exposure.

## Phase 17 — Security Hardening — PLANNED

Perform cross-cutting IAM, data protection, abuse, threat-model, dependency, and operational hardening.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 remains deferred consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and must be re-evaluated against the current architecture before any integration merge.
