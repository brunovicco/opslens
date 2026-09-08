# ADR 0051 — Close Phase 13 at the Bounded Offline MCP Boundary

- Status: Accepted
- Date: 2026-09-08
- Phase: 13 — MCP
- Gate: 13.5 — MCP Phase Closeout

## Context

Phase 13 introduced MCP incrementally over authority boundaries that already existed in OpsLens. The phase did not begin from a requirement to expose a public MCP endpoint. Its architectural question was narrower: can official MCP interoperability be added without turning protocol/framework behavior into a second authorization, executable-input, execution, evidence, or result-disclosure plane?

Gates 13.1–13.4 answered that question with progressively stronger proofs.

Gate 13.1 froze a closed MCP tool identity and deterministic admission contract. Gate 13.2 proved real official MCP Python SDK interoperability while keeping protocol input reference-only and adding raw argument-shape refusal ahead of permissive framework coercion. Gate 13.3 connected admitted MCP references to the existing typed Phase 11 capability executor exactly once. Gate 13.4 then introduced the first business-result transport policy through an explicit capability-specific projector rather than generic object serialization.

All implementation gates currently defined for Phase 13 are complete. There is no concrete consumer/runtime requirement in the current roadmap that requires a public HTTP MCP server, transport authentication, persistent invocation/result registry, broader result-family disclosure, or deployed MCP runtime before the next planned phase.

## Decision

Close Phase 13 at the bounded offline MCP interoperability and result-projection boundary.

Retain:

```text
Phase 11 typed capability authority
 -> mcp-capability-exposure:v1
 -> official MCP SDK reference-only protocol adapter
 -> raw tools/call argument-shape refusal
 -> deterministic invocation resolution + admission
 -> mcp-capability-execution:v1
 -> exactly one existing typed executor attempt
 -> mcp-result-projection:v1 for structured_security_query only
 -> allowlisted CVE + EPSS rows
 -> STOP before public/network runtime
```

Do not add a public or deployed MCP runtime merely to make Phase 13 appear more complete.

Any future network transport, authentication, session lifecycle, registry, broader business-result transport, or runtime hosting requirement must arrive as a separately justified architecture decision with its own least-privilege, failure, observability, cost, and operational evidence.

## Retained contracts

### Gate 13.1 — capability exposure and admission

```text
contract:  mcp-capability-exposure:v1
issue:     #180
PR:        #181
merge SHA: 322922aed4abec3b2266a18d15d8145df974a7d1
```

Retained property:

```text
closed McpToolName
 + existing AuthorizedAgentAction
 + existing typed AgentCapabilityInvocation
 -> deterministic tool/capability match
 -> content-addressed McpToolCallAdmission
```

MCP tool identity does not create capability authorization.

### Gate 13.2 — official SDK offline interoperability

```text
issue:     #183
PR:        #184
merge SHA: 131c086ff85564dbd777cebd6454d70e53ca8332
SDK:       mcp==2.2.0
scope:     development dependency only
```

Retained property:

```text
MCP Client
 -> exact closed tool
 -> raw tools/call key-set refusal
 -> {invocation_id, invocation_sha256}
 -> deterministic resolver
 -> independent invocation identity revalidation
 -> Gate 13.1 admission
```

A real SDK finding remains important: generated SDK/Pydantic function-argument coercion can ignore an unexpected field. OpsLens therefore retains code-owned raw argument-shape validation before framework coercion.

The SDK also remains dev-only. A previous experiment placing it in runtime dependencies enlarged unrelated Lambda deployment packages and tripped an existing size gate. Because Phase 13 deploys no MCP runtime, widening deployment dependencies would add cost/risk without a runtime requirement.

### Gate 13.3 — capability execution bridge

```text
contract:  mcp-capability-execution:v1
issue:     #186
PR:        #187
merge SHA: 170429c894456adc1e1c38ca93b49f12e310fb94
```

Retained property:

```text
admitted MCP invocation reference
 -> exact existing typed AgentCapabilityInvocation
 -> existing execute_authorized_capability(...)
 -> AgentCapabilityExecution
 -> content-addressed McpCapabilityExecutionBridge
```

One accepted application call performs exactly one existing typed executor attempt. MCP adds no adaptive retry, alternate-capability fallback, or dynamic executable-argument registry.

### Gate 13.4 — explicit structured business-result projection

```text
contract:  mcp-result-projection:v1
issue:     #189
PR:        #190
merge SHA: 87772b1604d4ede0f88f72d4d338ddf553953304
```

Retained property:

```text
already-admitted StructuredSecurityQueryResultBinding
 -> explicit structured EPSS projector
 -> allowlisted cve + epss_score rows
 -> content-addressed MCP result projection
```

The projector reapplies `SemanticQuery.limit`, caps the transport surface to at most 100 rows, validates CVE and EPSS value shape, and excludes SQL plus Athena/provider operational metadata.

Knowledge, hybrid, and public-repository result families remain unsupported for business-result transport.

## Why Phase 13 can close without a public MCP runtime

The implemented phase objective is interoperability without authority drift, not deployment for its own sake.

The current evidence already proves:

```text
closed protocol-facing tool identity
reference-only official SDK client/server interoperability
fail-closed raw argument validation before framework coercion
deterministic invocation reference resolution and revalidation
mandatory deterministic admission before execution
exactly-one existing typed executor attempt
content-addressed admission/execution provenance
explicit capability-specific result disclosure
business-result row bounds at protocol egress
stable separation between admission-only, execution-only, and structured-result servers
```

A public endpoint would introduce new concerns that are not required to answer the Phase 13 question:

```text
network transport lifecycle
authentication and client identity
authorization transport semantics
session/state management
rate limiting and abuse protection
network retry and timeout behavior
availability/SLO targets
secrets or workload identity
runtime hosting and IAM
observability and operational cost
```

Adding those concerns now would conflate protocol interoperability with production runtime architecture and would pre-empt later planned runtime decisions.

## Retained authority model

Phase 13 preserves these separations:

```text
MCP tool name != capability authorization
MCP tool exposure != executable argument authority
MCP call admission != capability execution
MCP capability execution != business result transport
MCP result admission != result projection authority
MCP result projection != public runtime exposure
MCP transport success != business/evidence truth
MCP result != runtime exposure truth
Repository Risk != Runtime Exposure
```

The MCP framework remains subordinate to code-owned contracts. Framework convenience never becomes authority merely because a schema or object can be serialized.

## Explicit Phase 13 non-claims

Phase 13 does **not** prove or implement:

```text
generic business-result serialization
knowledge-guidance business-result transport
hybrid-security-answer business-result transport
public-repository-analysis business-result transport
persistent invocation or result registry
stdio subprocess deployment interoperability
Streamable HTTP production interoperability
public MCP endpoint
MCP transport authentication or authorization
network reliability or production SLOs
Amazon Bedrock AgentCore runtime behavior
A2A interoperability
runtime exposure / Amazon Inspector evidence
```

These non-claims are part of the closeout evidence. Later phases must not reinterpret offline MCP interoperability as proof of capabilities that were never exercised.

## Closeout evidence

The deterministic closeout record is preserved at:

```text
labs/evidence/phase-13-closeout-v1.json
```

It binds the Gate 13.1–13.4 merge identities, retained contracts, dependency disposition, explicit non-claims, runtime-impact zeros, and deferred cross-project integration state.

## Why no additional model or AWS run is required

Gate 13.5 is an architecture/evidence closeout over already-merged deterministic protocol boundaries. It does not introduce a new model path, cloud runtime, network endpoint, IAM principal, or capability implementation.

Therefore:

```text
new model invocations in closeout: 0
new inference cost in closeout:     USD 0.00
new AWS resources in closeout:      0
new IAM roles/policies:             0
live capability executions:         0
```

Running Bedrock or deploying AWS infrastructure merely to close this phase would create unrelated evidence rather than validate the closeout decision.

## Alternatives rejected

### Add Streamable HTTP before closeout

Rejected. No concrete current consumer requires a public/network MCP transport. HTTP would add authentication, session, reliability, abuse, runtime-hosting, and IAM questions that deserve an independent evidence-backed gate.

### Expose all four capability result families before closeout

Rejected. Result admission and protocol disclosure are distinct authorities. Knowledge, hybrid, and public-analysis results carry different provenance/citation/content semantics and are not required to prove the bounded MCP architecture.

### Move the MCP SDK into runtime dependencies now

Rejected. No MCP runtime is deployed, and an earlier dependency-placement experiment measurably harmed unrelated Lambda packaging. Runtime dependency expansion must follow a real runtime requirement.

### Use generic model/dataclass serialization for future convenience

Rejected. Internal object shape is not protocol disclosure authority.

### Treat successful offline interoperability as runtime readiness

Rejected. Protocol correctness and production runtime readiness are different evidence classes.

## Next phase boundary

After Gate 13.5 and final Phase 13 state synchronization, the next OpsLens roadmap phase is:

```text
Phase 14 — Amazon Bedrock AgentCore
```

Phase 14 should evaluate managed runtime capabilities against measured OpsLens needs rather than adopting AgentCore for certification coverage alone.

Phase 14 does not retroactively turn the Phase 13 offline MCP server into a public runtime. Any hosting or integration decision must preserve the frozen Phase 13 authority contracts.

## Deferred Governed LLM Gateway integration

Long-lived OpsLens PR #89 remains separate cross-project work for **Phase 14 — Case 3 of `brunovicco/governed-llm-gateway`**.

That external project phase numbering is not OpsLens Phase 14. This closeout does not authorize modifying, rebasing, merging, closing, or reusing PR #89. Reactivation requires a separate current-state re-evaluation.

## AWS / IAM / runtime impact

```text
new model invocations:       0
new inference cost:           USD 0.00
new AWS resources:            0
new IAM roles/policies:       0
GitHub OIDC trust changes:    0
live capability executions:   0
public MCP endpoints:         0
deployed MCP runtimes:        0
AgentCore runtime changes:    0
A2A runtime changes:          0
runtime-exposure changes:     0
Governed LLM Gateway changes: 0
```

## AIP-C01 learning connection

Phase 13 demonstrates a production GenAI platform lesson that is easy to miss when learning tool protocols: interoperability is not authorization, execution, evidence, or disclosure authority.

A safe tool-protocol architecture composes explicit boundaries instead of letting framework convenience collapse them. Equally important, architectural maturity includes knowing when **not** to deploy another runtime. A managed or networked transport should be introduced because a measured use case requires it, with least privilege and operational evidence, not because the framework can expose one.
