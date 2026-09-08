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
Phase 13   MCP                                                 COMPLETE
  Gate 13.1 Bounded MCP capability exposure contract           COMPLETE / MERGED
  Gate 13.2 Bounded MCP protocol adapter / offline interop      COMPLETE / MERGED
  Gate 13.3 Bounded MCP capability execution bridge            COMPLETE / MERGED
  Gate 13.4 Bounded MCP business result projection             COMPLETE / MERGED
  Gate 13.5 MCP phase closeout                                 COMPLETE / MERGED
Phase 14   Amazon Bedrock AgentCore                            NEXT
Phase 15   A2A                                                 PLANNED
Phase 16   Runtime Exposure with Amazon Inspector              PLANNED
Phase 17   Security Hardening                                  PLANNED
Phase 18   Evaluation, Cost & Portfolio Readiness              PLANNED
```

Latest merged checkpoint:

```text
Phase 13 Gate 13.5 / PR #193
c449cfc8e18dfd240ceedbe6e8e4d143601f0254
```

Gate 13.5 exact validation and merge:

```text
issue #192:               state-sync tracker; closure follows this synchronization
PR #193 final head:       99dd3d979a5205e38f2c1a4dfc84dc9f82d0e0c7
PR merge test commit:     7ec68aa12bc0a08b698ed0ddf76434e7bd97fe85
MCP CI:                    34250265151 / run #52 / PASS
job:                       102142600531
uv lock --check:           PASS
MCP SDK pin:               PASS
MCP import smoke:          PASS
Ruff:                      PASS
Pyright strict:            0 errors / 0 warnings / 0 informations
pytest MCP slice:          29 passed in 0.90s
review threads:            0
PR conversation comments: 0
new model invocations:     0
new AWS/IAM resources:     0
public MCP endpoint:       0
MCP deployed runtime:      0
PR #193 merge SHA:         c449cfc8e18dfd240ceedbe6e8e4d143601f0254
```

Phase 13 closes at the bounded offline MCP boundary. The closeout intentionally does not add public/network MCP hosting, transport authentication, broader result-family serialization, AgentCore, A2A, runtime-exposure authority, or AWS/IAM expansion without a concrete separately justified runtime need.

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
MCP capability execution != business result transport
MCP result admission != result projection authority
MCP result projection != public runtime exposure
MCP transport success != business/evidence truth
MCP result != runtime exposure truth
```

Deterministic code continues to own package/version semantics, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS/Risk Policy facts, `SemanticQuery` validation and SQL compilation, retrieval/evidence admission, hybrid routing/completeness, canonical evidence/citation identity, output admission, public request admission, immutable repository evidence binding, capability allowlists, capability authorization, typed capability invocation/result binding, handoff admission, specialization mapping, comparison/evaluation metrics, MCP tool/capability mapping, raw MCP argument-shape refusal, invocation-reference validation, resolver identity revalidation, call admission, typed capability execution dispatch, MCP admission-to-execution identity binding, business-result projection allowlists and bounds, content-addressed MCP result-projection identity, content-addressed evidence/report identity, provider/model selection, retry/fallback policy, and runtime-exposure authority.

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

Architecture/evidence references:

```text
docs/adr/0047-bounded-mcp-capability-exposure.md
labs/phase-13-gate-13-1-bounded-mcp-capability-exposure.md
```

## Phase 13 Gate 13.2 — bounded MCP protocol adapter / offline interoperability

Pinned development-only dependency:

```text
mcp==2.2.0
```

Bounded protocol path:

```text
MCP Client
 -> exact closed Gate 13.1 tool
 -> raw tools/call argument-shape refusal
 -> {invocation_id, invocation_sha256}
 -> McpInvocationReference
 -> McpInvocationResolver
 -> exact existing AgentCapabilityInvocation
 -> independent ID + digest revalidation
 -> Gate 13.1 admit_mcp_tool_call(...)
 -> content-minimized McpAdmissionProjection
 -> MCP Client
 -> STOP
```

Real tests discovered that MCP SDK v2.2.0/Pydantic may ignore an unexpected argument field rather than fail closed. OpsLens therefore installs a narrow raw-request middleware that refuses extra or missing keys before SDK function-model coercion. Framework validation remains subordinate to OpsLens authority.

A second concrete finding came from Terraform CI: when `mcp==2.2.0` was initially placed in project runtime dependencies, its transitive graph enlarged unrelated Lambda packages and caused the NVD incremental direct-upload package to exceed the existing 50 MiB limit. The correct remediation was to keep MCP dev-only because Gate 13.2 deploys no MCP runtime; deployment limits were not weakened.

Architecture/evidence references:

```text
docs/adr/0048-bounded-offline-mcp-protocol-adapter.md
labs/phase-13-gate-13-2-bounded-mcp-protocol-adapter.md
PR #184 merge: 131c086ff85564dbd777cebd6454d70e53ca8332
```

## Phase 13 Gate 13.3 — bounded MCP capability execution bridge

Frozen contract:

```text
mcp-capability-execution:v1
```

Bounded execution path:

```text
MCP Client
 -> exact closed Gate 13.1 tool
 -> Gate 13.2 raw argument-shape refusal
 -> exact invocation ID + digest resolution
 -> Gate 13.1 deterministic MCP admission
 -> existing typed AgentCapabilityInvocation
 -> existing execute_authorized_capability(...)
 -> exact AgentCapabilityExecution
 -> content-addressed McpCapabilityExecutionBridge
 -> identity/digest-only MCP structured output
 -> STOP before business result transport
```

The successful path performs exactly one existing typed executor call. Gate 13.3 adds no MCP retry, alternate-capability fallback, generic `args`/`kwargs` dispatch, or new model/provider behavior.

Gate 13.2 admission-only semantics remain preserved through a separate server builder; Gate 13.3 introduces an explicit execution server instead of silently changing the admission-only adapter.

Protocol-visible execution output remains identity-only and excludes downstream business content such as Athena rows, query text, synthesis answers, repository content, provider messages, credentials, or arbitrary downstream exception text.

Failure-path tests prove tool/capability mismatch fails before execution, executor exceptions are content-minimized, wrong/mismatched result families fail closed, and an extra `sql` field is still rejected before execution.

Architecture/evidence references:

```text
docs/adr/0049-bounded-mcp-capability-execution-bridge.md
labs/phase-13-gate-13-3-bounded-mcp-capability-execution-bridge.md
PR #187 merge: 170429c894456adc1e1c38ca93b49f12e310fb94
```

## Phase 13 Gate 13.4 — bounded MCP structured result projection / offline transport

Frozen contract:

```text
mcp-result-projection:v1
```

Bounded result path:

```text
MCP Client
 -> exact structured-security tool
 -> Gate 13.2 raw argument-shape refusal
 -> exact invocation reference resolution
 -> Gate 13.1 deterministic admission
 -> existing typed StructuredSecurityQueryInvocation
 -> existing capability executor exactly once
 -> existing StructuredSecurityQueryResultBinding admission
 -> existing AgentCapabilityExecution
 -> Gate 13.3 McpCapabilityExecutionBridge
 -> explicit structured EPSS projector
 -> allowlisted CVE + EPSS rows
 -> content-addressed result-projection evidence
 -> MCP Client
 -> STOP before public/network runtime
```

Gate 13.4 adds an application-only `AgentCapabilityExecutionOutcome` so the exact already-admitted downstream result can be preserved beside the existing execution identity without re-executing or duplicating capability dispatch. The historical `execute_authorized_capability(...)` API delegates to the additive outcome path and preserves the same `AgentCapabilityExecution` semantics.

Business-result transport is intentionally limited to `structured_security_query`. The projector accepts only the exact internal Athena shape `("cve", "epss")`, maps it to protocol fields `cve` + `epss_score`, reapplies `SemanticQuery.limit`, enforces a maximum of 100 rows, validates CVE/EPSS value shape, and binds the allowlisted rows into a content-addressed projection identity.

Successful protocol output deliberately excludes query execution identifiers, bytes scanned, Athena timing, SQL, execution parameters, provider/model messages, credentials, hidden adapter metadata, and arbitrary downstream exception content.

The admission-only Gate 13.2 server and identity-only Gate 13.3 execution server retain their original meanings. Gate 13.4 adds a third separate offline result server rather than silently broadening either prior protocol.

Architecture/evidence references:

```text
docs/adr/0050-bounded-mcp-structured-result-projection.md
labs/phase-13-gate-13-4-bounded-mcp-structured-result-projection.md
PR #190 merge: 87772b1604d4ede0f88f72d4d338ddf553953304
```

## Phase 13 Gate 13.5 — MCP phase closeout

Closeout decision:

```text
retain the bounded offline MCP architecture
close Phase 13 without inventing a public/deployed MCP runtime
```

Retained path:

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

The MCP SDK remains development-only because Phase 13 deploys no MCP runtime and a prior runtime-dependency placement experiment measurably harmed unrelated Lambda packaging. Public/network transport, transport authentication, persistent registries, broader result-family disclosure, AgentCore, A2A, and runtime-exposure behavior remain explicit non-claims rather than being inferred from offline interoperability.

Architecture/evidence references:

```text
docs/adr/0051-phase13-mcp-closeout.md
labs/phase-13-gate-13-5-mcp-closeout.md
labs/evidence/phase-13-closeout-v1.json
PR #193 merge: c449cfc8e18dfd240ceedbe6e8e4d143601f0254
```

## Phase 13 retained proof boundary

Phase 13 now proves:

```text
MCP-visible tool identity can remain a closed code-owned surface
protocol naming can remain separate from capability authorization
MCP admission can preserve exact upstream action/invocation identity
real official MCP client/server interoperability can remain reference-only
raw protocol arguments can fail closed before permissive framework coercion
resolver results can be revalidated before deterministic admission
MCP admission can remain mandatory before typed capability execution
one accepted protocol call can be bounded to one existing executor attempt
existing Phase 11 result-family and result-identity admission can remain authoritative
MCP execution evidence can be content-addressed independently of business result transport
an already-admitted typed result can be retained without duplicate capability execution
business-result disclosure can remain an explicit capability-specific code-owned authority
structured result fields and rows can be allowlisted, bounded, normalized, and content-addressed
SemanticQuery row authority can remain effective at MCP protocol egress
prior admission-only and identity-only server semantics can remain stable while result transport is added separately
MCP SDK experimentation can remain outside unrelated deployed Lambda runtimes
```

Phase 13 explicitly does **not** prove:

```text
generic business-result serialization
knowledge-guidance result transport
hybrid-security-answer result transport
public-repository-analysis result transport
persistent invocation/result registry
stdio subprocess deployment interoperability
Streamable HTTP production interoperability
public MCP endpoint
MCP transport authentication/authorization
network reliability or production SLOs
Amazon Bedrock AgentCore runtime behavior
A2A interoperability
runtime exposure / Amazon Inspector evidence
```

## AWS / IAM / runtime checkpoint

Gate 13.5 introduced no deployed runtime expansion:

```text
new model invocations:       0
new inference cost:           USD 0.00
new AWS resources:            0
new IAM roles/policies:       0
GitHub OIDC trust changes:    0
live capability executions:   0
MCP SDK dependency:           dev-only mcp==2.2.0
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

## Next authorized phase

```text
Phase 14 — Amazon Bedrock AgentCore
```

Phase 14 must begin with a concrete OpsLens runtime requirement and an evidence-backed evaluation of AgentCore. It does not inherit authorization to deploy the Phase 13 offline MCP proof unchanged as a public runtime.

Initial constraints:

```text
1. preserve the retained Phase 11 reasoning reference and Phase 12 retention decision
2. preserve Phase 13 MCP admission/execution/result-projection authority boundaries
3. do not equate managed runtime adoption with business authorization or evidence truth
4. define workload, runtime, identity, observability, failure, and cost needs before provisioning resources
5. no AWS/IAM expansion without a concrete AgentCore capability requirement
6. no public MCP/A2A/runtime-exposure claim merely because AgentCore can host agent workloads
7. preserve Repository Risk != Runtime Exposure
8. keep the separate Governed LLM Gateway Phase 14 / Case 3 integration independently governed
9. keep PR #89 untouched until its separately governed re-evaluation
```
