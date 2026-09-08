# OpsLens — Current State

_Last updated: 2026-09-08_

This document is the authoritative implementation checkpoint for OpsLens. Detailed history remains in ADRs, gate labs, immutable evidence artifacts, merged PRs, and Git history.

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
Phase 13   MCP                                                 IN PROGRESS
  Gate 13.1 Bounded MCP capability exposure contract           COMPLETE / MERGED
  Gate 13.2 Bounded MCP protocol adapter / offline interop      NEXT
Phase 14   Amazon Bedrock AgentCore                            PLANNED
Phase 15   A2A                                                 PLANNED
Phase 16   Runtime Exposure with Amazon Inspector              PLANNED
Phase 17   Security Hardening                                  PLANNED
Phase 18   Evaluation, Cost & Portfolio Readiness              PLANNED
```

Latest merged checkpoint:

```text
Phase 13 Gate 13.1 / PR #181
322922aed4abec3b2266a18d15d8145df974a7d1
```

Gate 13.1 exact validation and merge:

```text
issue #180:               closeout tracker; closure follows final state synchronization
PR #181 final head:       340f2d7beee3640bd14455de635fe3ee4b6cc5cc
PR merge test commit:     166e5626f52bdbabfd306b0e3152b02c1620ee5f
MCP CI:                    34223369166 / run #3 / PASS
job:                       102051514632
uv lock --check:           PASS
MCP import smoke:          PASS
Ruff:                      PASS
Pyright strict:            0 errors / 0 warnings / 0 informations
pytest MCP slice:          7 passed in 0.19s
review threads:            0
new model invocations:     0
capability executions:     0
MCP SDK/runtime:           0
new AWS/IAM resources:     0
PR #181 merge SHA:         322922aed4abec3b2266a18d15d8145df974a7d1
```

## Permanent architecture boundaries

> **Agents reason. Code verifies evidence.**

> **MCP is an interoperability boundary, not new business authority.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

Agentic and interoperability authority remains explicitly separated:

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

Deterministic code continues to own package/version semantics, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS/Risk Policy facts, `SemanticQuery` validation and SQL compilation, retrieval/evidence admission, hybrid routing/completeness, canonical evidence/citation identity, output admission, public request admission, immutable repository evidence binding, capability allowlists, capability authorization, typed capability invocation/result binding, handoff admission, specialization mapping, comparison/evaluation metrics, MCP tool/capability mapping and call admission, content-addressed evidence/report identity, provider/model selection, retry/fallback policy, and runtime-exposure authority.

## Retained measured reasoning architecture

Phase 12 did **not** replace the Phase 11 single-agent reference.

Retained/default reasoning path:

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

Frozen Phase 11 six-case reference:

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
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

## Retained Phase 12 mechanism

Gate 12.1 remains the retained deterministic specialization/handoff authority primitive:

```text
source task
 -> code-owned specialization mapping
 -> deterministic intersection with source allowed_capabilities
 -> narrowed specialist task
```

Code-owned partition:

```text
EVIDENCE_ANALYSIS
 -> public_repository_analysis
 -> structured_security_query

GUIDANCE_SYNTHESIS
 -> hybrid_security_answer
 -> knowledge_guidance
```

The `4 -> <=2` capability reduction is reasoning-surface narrowing, not runtime privilege reduction. Models still have no capability execution authority.

Gate 12.2 remains the retained deterministic comparison discipline:

```text
dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
report_sha256:  0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
synthetic conformance: 6/6
```

Synthetic fixture conformance is evaluator/contract evidence only, not model quality.

## Historical Gate 12.3 two-model experiment

The first authenticated bounded two-model experiment remains preserved at:

```text
labs/evidence/phase-12-gate-12-3-first-real-two-model-comparison-v1.json

dataset_sha256: 0439ebaa6215b2de7eaa82624188576743b5a50cc847137e04dc97ee7a199be7
report_sha256:  45edf58ac911ec14e872a00464dad5d5311d82165d6b8ac4321da4a0dc5ad09b
```

Observed result:

```text
quality:                           6/6
model invocations:                 10
input/output/total tokens:          5788 / 194 / 5982
provider latency median per task:  1694.0 ms
client elapsed median per task:    2135.0 ms
SDK retries:                       0
capability executions:             0
derived six-case cost:             USD 0.0074338
```

Compared with the retained Phase 11 reference:

```text
quality                    6/6 -> 6/6       no lift
model invocations          6 -> 10          +66.67%
total tokens               3395 -> 5982     +76.20%
provider latency median    809.5 -> 1694.0  +109.26%
client elapsed median      977.5 -> 2135.0  +118.41%
derived cost               0.0041921 -> 0.0074338 USD  +77.33%
SDK retries                0 -> 0
capability executions      0 -> 0
```

## Frozen Phase 12 retention decision

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
new rescue/tuning experiment:                   NOT AUTHORIZED WITHOUT NEW HYPOTHESIS
```

Decision and closeout evidence:

```text
labs/evidence/phase-12-gate-12-4-retention-decision-v1.json
labs/evidence/phase-12-closeout-v1.json
docs/adr/0045-do-not-retain-two-model-topology-without-measured-lift.md
docs/adr/0046-phase12-multi-agent-closeout.md
labs/phase-12-gate-12-5-multi-agent-closeout.md
```

## Phase 13 Gate 13.1 — bounded MCP capability exposure

Frozen contract:

```text
mcp-capability-exposure:v1
```

Closed tool surface:

```text
opslens.structured_security_query   -> structured_security_query
opslens.knowledge_guidance          -> knowledge_guidance
opslens.hybrid_security_answer      -> hybrid_security_answer
opslens.public_repository_analysis  -> public_repository_analysis
```

Gate 13.1 freezes protocol-facing identity without granting the protocol any new execution authority:

```text
existing AuthorizedAgentAction
 + existing typed AgentCapabilityInvocation
 -> closed McpToolName
 -> deterministic tool/capability match
 -> content-addressed McpToolCallAdmission
 -> STOP
```

The MCP boundary does not create `AuthorizedAgentAction`, does not create the typed invocation, does not execute the capability, and does not accept arbitrary executable `args` / `kwargs`.

The exact typed invocation remains the executable-input authority. MCP admission binds only:

```text
contract_version
tool_name
capability
action_id
invocation_id
invocation_sha256
admission_sha256
admission_id
```

It cannot author or reinterpret `SemanticQuery`, SQL, synthesis requests, repository coordinates, URLs, shell commands, credentials, provider/model selection, retry/fallback policy, or execution results.

Failure paths are fail closed for unknown tool names, unknown typed invocation types, tool/capability mismatch, and forged exposure/admission identities.

Architecture/evidence references:

```text
docs/adr/0047-bounded-mcp-capability-exposure.md
labs/phase-13-gate-13-1-bounded-mcp-capability-exposure.md
```

## Phase 13 proof boundary so far

Gate 13.1 proves:

```text
MCP-visible tool identity can remain a closed code-owned surface
protocol naming can remain separate from capability authorization
MCP admission can preserve exact upstream action/invocation identity
unknown or mismatched paths can fail closed before execution
MCP authority semantics can be tested without adopting a runtime framework
```

Gate 13.1 does **not** prove:

```text
real MCP protocol interoperability
MCP client/server serialization
MCP authentication or session lifecycle
network reliability
capability execution through MCP
MCP result transport
public/deployed MCP runtime
production MCP SLOs
AgentCore behavior
A2A interoperability
runtime exposure / Amazon Inspector evidence
```

## AWS / IAM / runtime checkpoint

Gate 13.1 introduced no runtime expansion:

```text
new model invocations:       0
new inference cost:           USD 0.00
new AWS resources:            0
new IAM roles/policies:       0
GitHub OIDC trust changes:    0
capability executions:        0
MCP SDK dependency:           0
MCP network runtime:          0
AgentCore runtime:            0
A2A runtime:                  0
public runtime:               0
runtime-exposure authority:   0
Governed LLM Gateway changes: 0
```

## Deferred Governed LLM Gateway integration

Long-lived OpsLens PR #89 remains open/draft consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It remains deferred and must be re-evaluated against the current OpsLens architecture before any merge.

Preserved historical head:

```text
3781831795d500b05fa4bc602d50f376b4b1539f
```

## Next authorized gate

```text
Phase 13 — Gate 13.2: Bounded MCP Protocol Adapter / Offline Interoperability
```

Gate 13.2 may introduce a real MCP protocol adapter only against the already-frozen Gate 13.1 authority contract. Framework/SDK adoption must not redefine capability authority.

Initial constraints:

```text
1. protocol input references an already-created typed invocation; it does not author arbitrary business args
2. deterministic server-side resolution must recover the exact admitted invocation identity or fail closed
3. tool/capability matching still passes through Gate 13.1 admission
4. STOP before execute_authorized_capability(...)
5. first interoperability proof should be offline/in-process or stdio, not public network deployment
6. unknown/missing/forged invocation references fail closed
7. no dynamic tool registry
8. no AWS/IAM expansion without a concrete runtime need
9. protocol success remains distinct from business/evidence truth
10. AgentCore, A2A, public runtime, and runtime exposure remain later decisions
```

Before adding an MCP SDK dependency, Gate 13.2 must verify the current official SDK/API and pin the chosen dependency deliberately.
