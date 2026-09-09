# OpsLens — Current State

_Last updated: 2026-09-09_

This document is the authoritative implementation checkpoint for OpsLens. Detailed historical evidence remains in ADRs, gate labs, immutable evidence artifacts, merged PRs, workflow runs, and Git history.

## Status

```text
Phase 0    AWS Foundation                                      COMPLETE
Phase 1    EPSS Vertical Slice                                 COMPLETE
Phase 2    Threat Intelligence Data Lake                       COMPLETE
Phase 3    Vulnerability Correlation Engine                    COMPLETE
Phase 4    Repository Intelligence                             COMPLETE
Phase 5    Risk Prioritization Engine                          COMPLETE
Phase 6    Semantic Query Layer                                COMPLETE
Phase 7    Knowledge Retrieval with Bedrock                    COMPLETE
Phase 8    Hybrid Retrieval                                    COMPLETE
Phase 9    Public Analyze Your Repository                      COMPLETE
Phase 10   Observability & Operational Excellence              COMPLETE
Phase 11   Single-Agent Baseline                               COMPLETE
Phase 12   Multi-Agent Architecture                            COMPLETE
Phase 13   MCP                                                 COMPLETE
Phase 14   Amazon Bedrock AgentCore                            IN PROGRESS
  Gate 14.1 AgentCore Runtime capability-fit / authority       COMPLETE / MERGED
  Gate 14.2 First bounded HTTP/SigV4 runtime experiment        COMPLETE / MEASURED
Phase 15   A2A                                                 PLANNED
Phase 16   Runtime Exposure with Amazon Inspector              PLANNED
Phase 17   Security Hardening                                  PLANNED
Phase 18   Evaluation, Cost & Portfolio Readiness              PLANNED
```

## Latest measured checkpoint — Phase 14 Gate 14.2

Terminal successful experiment:

```text
source main:                e5072ec68b421677359cebb1eb449578ef7d5b49
merge:                      fix(phase14): preserve runtime delete waiter read authority (#220)
workflow:                   AgentCore Runtime Experiment
run:                        34378942784 / run #11 / SUCCESS
job:                        102558703872
runtime:                    opslens_dev_bounded_runtime-Cl8aNBDGzh
runtime version:            1
protocol:                   HTTP
network:                    PUBLIC — dev-only experiment exception
artifact SHA256:            a846034ad646c4f6383ac08e47d9ed065b4a9f3349c14104db49a2d510b3ec88
Phase 11 corpus SHA256:     3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
```

Authenticated replay:

```text
cases:                      6 / 6 PASS
HTTP responses:             200
capability executions:      0
SDK retries:                0
input/output/total tokens:  3291 / 104 / 3395
transport elapsed sum:      19981 ms
```

Negative authorization proof:

```text
OpsLensGitHubDeployRole
 -> bedrock-agentcore:InvokeAgentRuntime
 -> AccessDeniedException / HTTP 403
```

Cleanup proof:

```text
Terraform:                  0 add / 0 change / 3 destroy
independent verifier:       RESOURCE_NOT_FOUND
```

Preserved workflow artifact:

```text
artifact ID: 10115123076
digest:      sha256:7006a7c2bfda1658a9e66fcfe38f61b06dc64e6f54705ffbf6b02574870ef65c
```

Immutable repository closeout evidence:

```text
labs/evidence/phase-14-gate-14-2-final-runtime-experiment-v1.json
```

## Observed Gate 14.2 cost

Delayed AgentCore Runtime CloudWatch telemetry arrived after the successful run.

Observed resource usage:

```text
CPUUsed-vCPUHours:   0.005455525277778
MemoryUsed-GBHours:  0.200219642726704
```

Recorded cost checkpoint:

```text
AgentCore CPU:       USD 0.000488269512361131
AgentCore memory:    USD 0.001892075623767353
AgentCore Runtime:   USD 0.002380345136128484
Bedrock inference:   USD 0.004192100000000000
------------------------------------------------
TOTAL:               USD 0.006572445136128483
```

This is the observed cost of the successful six-case experiment. No monthly extrapolation is authorized.

## Permanent architecture boundaries

> **Agents reason. Code verifies evidence.**

> **MCP is an interoperability boundary, not new business authority.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

Agentic/runtime authority remains explicitly separated:

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

Deterministic code continues to own package/version semantics, vulnerability applicability, source evidence, KEV/EPSS/CVSS facts, Risk Policy v1, semantic-query validation, SQL compilation, retrieval/evidence admission, hybrid completeness, citation/evidence identity, public request admission, immutable repository evidence binding, capability allowlists, capability authorization, executable-input bindings, result admission, handoff admission, MCP mapping/admission/projection authority, provider/model selection, retry/fallback policy, application session ownership, cost/execution bounds, and runtime-exposure truth.

## Retained reasoning architecture

Phase 11 remains the default/reference measured reasoning path:

```text
SingleAgentTask
 -> code-owned AgentCapability allowlist
 -> one bounded model reasoning invocation
 -> transient untrusted {decision, capability}
 -> deterministic parser
 -> AgentActionProposal
 -> deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
```

Frozen six-case reference:

```text
provider:                     Amazon Bedrock Converse
region:                       us-east-1
model/profile:                us.anthropic.claude-haiku-4-5-20251001-v1:0
quality:                      6/6
model invocations:            6
input/output/total tokens:    3291 / 104 / 3395
provider latency median:      809.5 ms
client elapsed median:        977.5 ms
SDK retries:                  0
capability executions:        0
derived six-case cost:        USD 0.0041921
```

Historical reference:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
```

## Retained Phase 12 decision

Phase 12 retained deterministic specialization/handoff and comparison discipline, but did not retain the two-model topology as the default:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
```

The measured two-model topology produced no quality lift while increasing invocations, tokens, latency, and cost.

## Retained Phase 13 MCP boundary

Phase 13 is complete and retains a bounded offline MCP interoperability layer over existing capability authority:

```text
Phase 11 typed capability authority
 -> mcp-capability-exposure:v1
 -> official MCP SDK reference-only adapter
 -> raw exact-key-set argument refusal
 -> deterministic invocation resolution + admission
 -> mcp-capability-execution:v1
 -> exactly one existing typed executor attempt
 -> existing typed result admission
 -> mcp-result-projection:v1 for structured_security_query only
 -> bounded CVE + EPSS rows
 -> STOP before public/network runtime
```

MCP remains development-only in the current retained implementation. It does not create capability authorization or generic business-result authority.

Closeout evidence:

```text
labs/evidence/phase-13-closeout-v1.json
docs/adr/0051-phase13-mcp-closeout.md
```

## Phase 14 Gate 14.1 — capability-fit decision

Gate 14.1 authorized only one bounded experiment:

```text
AgentCore Runtime:       GO TO ONE BOUNDED EXPERIMENT ONLY
hosted boundary:         retained Phase 11 reasoning path
protocol:                HTTP
authentication:          IAM SigV4
capability executions:   0
adaptive retries:        0
adaptive fallbacks:      0
MCP runtime promotion:   not authorized
A2A:                     deferred
runtime-exposure truth:  not created
```

References:

```text
docs/adr/0052-agentcore-runtime-capability-fit.md
labs/phase-14-gate-14-1-agentcore-runtime-capability-fit.md
```

## Phase 14 Gate 14.2 — final measured outcome

Frozen contract:

```text
agentcore-runtime-invocation:v1
```

Path:

```text
raw JSON
 -> exact admission
 -> SingleAgentTask
 -> exactly one fixed-model reasoning proposal
 -> deterministic authorize_agent_action(...)
 -> content-addressed projection
 -> metadata-only response
 -> STOP before capability execution
```

### Measured attempt history

Attempts #1–#10 remain preserved as remediation evidence rather than being hidden by the successful run. They exposed, in sequence, source-layout execution, `CreateAgentRuntimeEndpoint`, runtime create-time tagging, service-linked-role bootstrap, workload-identity tagging/creation/directory scopes, cleanup `DeleteWorkloadIdentity`, and late-delete `GetAgentRuntime` lifecycle-read requirements.

Detailed evidence remains under:

```text
labs/evidence/phase-14-gate-14-2-*.json
```

### Final IAM boundary

The deployment principal remains main-only GitHub OIDC and still does **not** have:

```text
bedrock-agentcore:InvokeAgentRuntime
iam:CreateServiceLinkedRole
bedrock-agentcore:GetWorkloadIdentity
feature-branch OIDC trust
```

Deletion lifecycle reads are separated from mutation authority:

```text
ReadExactBoundedAgentCoreRuntimeLifecycle
 -> GetAgentRuntime
 -> exact OpsLens runtime family
 -> no runtime ResourceTag condition
```

Mutation remains resource-tag-gated for:

```text
DeleteAgentRuntime
ListTagsForResource
TagResource
UntagResource
UpdateAgentRuntime
```

This is required because a delete waiter must be able to observe the exact resource even after lifecycle transitions make resource tags unavailable.

### Gate 14.2 non-claims

Gate 14.2 does not establish:

```text
AgentCore as the default/production runtime
PUBLIC as a production network decision
production SLOs
production security approval
runtime deployment == runtime exposure
runtime telemetry == business truth
runtime authentication == capability authorization
AgentCore hosting == business authorization
```

No MCP runtime, A2A, Gateway/Policy, Memory, Browser, Code Interpreter, or capability execution was exercised.

## Deferred Governed LLM Gateway integration

PR #89 remains open/draft and is separate cross-project work for the Governed LLM Gateway. It remains untouched by Gate 14.2 and must be re-evaluated independently before any merge.

Preserved branch/head:

```text
feat/governed-gateway-semantic-planner
3781831795d500b05fa4bc602d50f376b4b1539f
```

## Next architecture decision

Gate 14.2 is complete, but **AgentCore retention is not yet decided**.

No Gate 14.3 number or implementation scope is authorized by this document yet. After the final Gate 14.2 state synchronization is merged, inspect the roadmap and formalize a separate issue only if a concrete decision gap remains.

The evidence-based question is:

> Does the measured AgentCore hosting/session/operational value justify its IAM, lifecycle, network, latency, cost, and operational surface for the retained OpsLens reasoning architecture?

The answer is deliberately not pre-committed.
