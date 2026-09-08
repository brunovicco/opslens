# Phase 13 — Gate 13.1: Bounded MCP Capability Exposure Contract

_Date: 2026-09-08_

## Status

**COMPLETE / MERGED — final state synchronization pending.**

Starting checkpoint:

```text
main:   913a3302534098b429d3955c770d025480289a3f
issue:  #180
branch: feat/phase13-bounded-mcp-capability-exposure
PR:     #181
```

Final Gate 13.1 merge checkpoint:

```text
PR final head: 340f2d7beee3640bd14455de635fe3ee4b6cc5cc
merge SHA:     322922aed4abec3b2266a18d15d8145df974a7d1
```

Gate 13.1 freezes MCP authority and identity semantics before any MCP SDK, server process, network transport, authentication layer, or capability execution is introduced.

## Gate objective

Phase 13 starts from the rule:

> **MCP is an interoperability boundary, not new business authority.**

The first gate therefore does not ask an MCP framework to define OpsLens tool authority. It exposes only the four capabilities already frozen by Phase 11 and binds MCP admission to an already-authorized typed invocation.

## Frozen contract

```text
mcp-capability-exposure:v1
```

Closed tool identities:

```text
opslens.structured_security_query
 -> structured_security_query

opslens.knowledge_guidance
 -> knowledge_guidance

opslens.hybrid_security_answer
 -> hybrid_security_answer

opslens.public_repository_analysis
 -> public_repository_analysis
```

The mapping is code-owned and one-to-one. There is no dynamic tool registry.

## Authority boundary

```text
existing AuthorizedAgentAction
 + existing typed AgentCapabilityInvocation
 -> closed McpToolName
 -> deterministic tool/capability match
 -> McpToolCallAdmission
 -> STOP
```

The MCP boundary does not create the authorization and does not create the typed invocation.

Existing authority remains:

```text
single-agent-authority:v1
single-agent-execution:v1
```

The exact upstream typed invocation remains authoritative for executable input semantics.

## Invocation-reference rule

Gate 13.1 deliberately does not give MCP arbitrary executable `args` / `kwargs` authority.

The underlying invocation is already one of:

```text
StructuredSecurityQueryInvocation
KnowledgeGuidanceInvocation
HybridSecurityAnswerInvocation
PublicRepositoryAnalysisInvocation
```

MCP admission binds only:

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

It does not author or reinterpret:

```text
SemanticQuery
SQL
knowledge synthesis request
hybrid synthesis request
repository coordinates
URLs
shell commands
credentials
provider/model selection
retry/fallback policy
execution result
```

## Deterministic exposure evidence

`McpCapabilityExposure` content-addresses the exact one-to-one tool/capability mapping.

Equivalent exposure semantics produce the same identity. Cross-capability binding fails closed.

`list_mcp_capability_exposures()` returns the complete fixed v1 catalog in canonical tool-name order.

## Deterministic call admission

`admit_mcp_tool_call(...)`:

```text
1. requires an exact McpToolName enum
2. resolves capability from the existing typed invocation type
3. obtains the exact AuthorizedAgentAction already embedded in that invocation
4. compares the code-owned MCP tool capability with invocation capability
5. rejects mismatches before execution
6. emits content-addressed McpToolCallAdmission evidence
7. performs zero capability execution
```

Unknown runtime objects cannot become dynamically registered tools.

## Raw transport-name boundary

`parse_mcp_tool_name(...)` is the raw-string-to-tool parser in this gate.

```text
exact known tool string -> McpToolName
unknown string          -> FAIL CLOSED
non-string input        -> FAIL CLOSED
```

A transport-visible name remains an identifier only. It is not authorization.

## Security invariants

```text
MCP tool name != capability authorization
MCP tool exposure != executable argument authority
MCP call admission != capability execution
MCP transport success != business/evidence truth
MCP result != runtime exposure truth
Repository Risk != Runtime Exposure
```

Models still cannot gain capability authority through MCP.

## Failure behavior

Gate 13.1 fails closed for:

```text
unknown tool name
tool/capability mismatch
unknown typed invocation type
forged MCP exposure identity
forged MCP admission identity
invalid upstream action identity
invalid upstream invocation identity
```

No arbitrary downstream/provider/model message becomes canonical MCP evidence.

## Tests

The bounded test slice covers:

```text
closed four-tool / four-capability one-to-one mapping
raw tool-name parser success and rejection
deterministic exposure identity
cross-capability exposure rejection
admission binding to existing AuthorizedAgentAction
typed invocation identity preservation
tool/invocation capability mismatch rejection
unknown invocation type rejection
forged admission identity rejection
zero capability execution in the admission path
```

## CI boundary

Dedicated workflow:

```text
.github/workflows/mcp-ci.yml
```

It runs:

```text
uv lock --check
uv sync --frozen
MCP boundary import smoke
Ruff MCP slice
Pyright strict MCP slice
pytest MCP slice
```

No AWS credentials, MCP runtime, model invocation, or external network service is required by Gate 13.1 CI.

## Validation history

The first PR run reached the new boundary and failed only Ruff import ordering. That deterministic style failure was corrected without changing the authority contract.

Intermediate validated implementation head:

```text
head:                dd0b5be955dd76cefc66a432f841a45951a5d13e
PR merge test SHA:   da6069349dadfbd5593e4eadaab1ad242f485bb0
MCP CI:              34223209211 / run #2 / PASS
job:                 102050984804
pytest MCP slice:    7 passed in 0.21s
```

Final exact-head validation after the documentation checkpoint:

```text
PR #181 final head:     340f2d7beee3640bd14455de635fe3ee4b6cc5cc
PR merge test commit:   166e5626f52bdbabfd306b0e3152b02c1620ee5f
MCP CI:                 34223369166 / run #3 / PASS
job:                    102051514632
uv lock --check:        PASS
MCP import smoke:       PASS
Ruff:                   PASS
Pyright strict:         0 errors / 0 warnings / 0 informations
pytest MCP slice:       7 passed in 0.19s
unresolved review threads: 0
merge SHA:              322922aed4abec3b2266a18d15d8145df974a7d1
```

## Framework / dependency decision

No external MCP SDK is added in Gate 13.1.

This is intentional. Framework/runtime behavior should not define tool authority before the core contract is frozen.

A later gate may introduce a real MCP transport adapter against this contract.

## AWS / IAM / runtime impact

```text
new AWS resources:          0
new IAM roles/policies:     0
new model invocations:      0
capability executions:      0
MCP SDK dependency:         0
MCP server runtime:         0
network MCP transport:      0
AgentCore runtime:          0
A2A runtime:                0
public runtime:             0
runtime-exposure authority: 0
```

## Deferred Governed LLM Gateway integration

OpsLens PR #89 remains separate long-lived cross-project work for **Phase 14 — Case 3 of `brunovicco/governed-llm-gateway`**. Gate 13.1 does not modify, rebase, merge, close, or reuse it.

## What Gate 13.1 proves

```text
MCP-visible tool identity can remain a closed code-owned surface
MCP can reference existing typed capability authority without recreating it
protocol naming can be separated from authorization
content-addressed MCP admission can preserve upstream action/invocation identity
unknown/mismatched tool paths can fail closed before execution
MCP authority semantics can be tested without adopting a runtime framework
```

## What Gate 13.1 does not prove

```text
real MCP protocol interoperability
MCP client/server serialization
MCP authentication or authorization transport
session lifecycle
network reliability
capability execution through MCP
MCP result transport
public/deployed MCP runtime
production SLOs
AgentCore behavior
A2A interoperability
runtime exposure evidence
```

## Next gate boundary

After the final state synchronization merge, the next authorized gate is:

```text
Phase 13 — Gate 13.2: Bounded MCP Protocol Adapter / Offline Interoperability
```

Gate 13.2 must preserve Gate 13.1 as authority. A real SDK/transport may adapt protocol calls to already-admitted invocation references, but it must not become a second executable-input or authorization surface.

## AIP-C01 learning checkpoint

The practical lesson is that an interoperability protocol must remain subordinate to the application authority model. A tool name is not permission, transport input is not trusted executable authority, and protocol success is not evidence truth. Freezing the contract first makes later MCP SDK/server adoption testable against explicit security invariants rather than allowing framework defaults to define them implicitly.

## Architecture record

```text
docs/adr/0047-bounded-mcp-capability-exposure.md
```

## Exit checklist

```text
[x] Phase 12 state-synchronized before Phase 13 entry
[x] issue #180 created
[x] dedicated Gate 13.1 branch created from exact main
[x] mcp-capability-exposure:v1 contract implemented
[x] four closed MCP tool names defined
[x] one-to-one tool/capability mapping implemented
[x] deterministic raw tool-name parser implemented
[x] existing typed invocation remains executable-input authority
[x] deterministic MCP admission implemented
[x] content-addressed exposure/admission identities implemented
[x] no dynamic tool registry
[x] no arbitrary MCP args/kwargs authority
[x] no capability execution
[x] no MCP SDK/runtime dependency
[x] no AWS/IAM/runtime expansion
[x] bounded unit tests added
[x] dedicated MCP CI added
[x] ADR 0047 added and indexed
[x] Gate 13.1 lab added
[x] draft PR #181 opened
[x] final exact-head MCP CI PASS
[x] PR scope/review threads clean
[x] protected squash merge
[ ] public/current state synchronized in follow-up PR
[ ] issue #180 CLOSED / COMPLETED after state synchronization
```
