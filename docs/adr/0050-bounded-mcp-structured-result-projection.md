# ADR 0050 — Project Only Explicit Structured Security Results Through MCP

- Status: Accepted
- Date: 2026-09-08
- Phase: 13 — MCP
- Gate: 13.4 — Bounded MCP Structured Result Projection and Offline Transport

## Context

Gate 13.3 proved that one exact MCP invocation reference can pass deterministic admission, execute through the existing typed Phase 11 executor exactly once, and return content-minimized execution evidence:

```text
mcp-capability-execution:v1
```

It deliberately stops before business-result transport.

The existing Phase 11 executor already validates downstream result families and binds them to the exact typed invocation, but `execute_authorized_capability(...)` historically returns only `AgentCapabilityExecution`. The admitted typed downstream object exists transiently inside that function.

Gate 13.4 therefore has two distinct questions:

1. how to retain an already-admitted typed result without duplicating execution dispatch; and
2. which business fields, if any, MCP may expose.

A generic serializer would make every field present on a downstream object implicitly protocol-visible. Re-executing or redispatching a capability inside the MCP layer merely to recover its result would create duplicate execution authority. Both are rejected.

## Decision

Introduce a separate bounded result-projection contract:

```text
mcp-result-projection:v1
```

and initially support business-result transport only for:

```text
structured_security_query
```

The accepted path is:

```text
MCP protocol call
 -> Gate 13.2 raw argument-shape refusal
 -> exact invocation ID + digest resolution
 -> Gate 13.1 deterministic admission
 -> existing typed StructuredSecurityQueryInvocation
 -> existing typed capability executor exactly once
 -> existing StructuredSecurityQueryResultBinding admission
 -> existing AgentCapabilityExecution
 -> Gate 13.3 McpCapabilityExecutionBridge
 -> explicit structured EPSS result projector
 -> mcp-result-projection:v1
 -> allowlisted CVE + EPSS rows
 -> MCP structured output
 -> STOP before public/network runtime
```

MCP still does not create or reinterpret executable business input.

## Additive execution outcome

Add an application-only wrapper:

```text
AgentCapabilityExecutionOutcome
 = existing AgentCapabilityExecution
 + exact already-admitted typed downstream result
```

and an additive function:

```text
execute_authorized_capability_outcome(...)
```

The existing public behavior remains:

```text
execute_authorized_capability(...)
 -> execute_authorized_capability_outcome(...)
 -> outcome.execution
```

This preserves existing `single-agent-execution:v1` identities and caller behavior while allowing a later projector to consume the exact result that already passed the original execution/result-admission boundary.

No second capability dispatch is introduced.

## Initial business-result surface

The first projector accepts only the actual frozen structured-query result shape produced by the Gate 6 compiler/executor:

```text
Athena columns: ("cve", "epss")
```

The MCP-visible semantic projection is:

```text
columns: ["cve", "epss_score"]
rows:
  - cve
  - epss_score
```

The projector does not expose arbitrary `AthenaQueryResult` fields merely because they exist.

Specifically deferred from successful MCP output:

```text
query_execution_id
data_scanned_bytes
engine_execution_time_ms
total_execution_time_ms
SQL
execution parameters
provider/downstream messages
credentials
hidden adapter metadata
```

## Data bounds and validation

The projector is explicit and fail closed.

Before transport it requires:

```text
bridge tool == opslens.structured_security_query
bridge capability == structured_security_query
bridge invocation identity == exact typed invocation
structured result invocation digest == exact typed invocation digest
bridge downstream result digest == admitted structured result digest
Athena columns == ("cve", "epss")
row_count <= invocation.query.limit
row_count <= 100
row width == 2
CVE matches the explicit CVE identity shape
EPSS is bounded decimal text from 0 to 1
```

`SemanticQuery.limit` remains the upstream row authority and is already restricted to `1..100`. The MCP projector reapplies that bound rather than assuming downstream compliance.

EPSS text is canonicalized before projection identity is calculated, so equivalent bounded decimal representations produce stable protocol semantics.

## Content-addressed projection evidence

`McpStructuredSecurityResultProjection` binds only:

```text
contract_version
tool_name
capability
invocation_id
execution_id
bridge_id
result_sha256
columns
allowlisted rows
projection_sha256
projection_id
```

The business rows are part of the projection digest. A forged digest or identifier fails validation.

## Separate result-transport server

Retain both previously frozen servers unchanged in meaning:

```text
build_offline_mcp_server(...)
 -> admission only

build_offline_mcp_execution_server(...)
 -> admission + execution
 -> identity/digest-only output
```

and add a third explicit proof:

```text
build_offline_mcp_structured_result_server(...)
 -> structured-security admission
 -> exactly one typed execution
 -> explicit bounded result projection
```

The result server registers only the structured-security tool. Other capability result families are not silently serialized or exposed.

## Failure boundary

Fail closed for:

```text
unsupported capability projection
unknown/malformed invocation reference
tool/capability mismatch
executor failure
wrong or mismatched admitted result family
bridge/result identity drift
unexpected Athena columns
rows beyond SemanticQuery.limit
malformed CVE or EPSS business content
extra/missing MCP arguments
forged projection identity
```

Protocol errors remain stable and do not copy arbitrary downstream exception content.

## Alternatives rejected

### Generic dataclass / model serialization

Rejected. Object shape is not a protocol authority boundary. Adding a field to an internal result type must not silently publish it through MCP.

### Re-execute the capability to recover business content

Rejected. One MCP request must not execute the same capability twice merely because the earlier execution API returned identity evidence only.

### Duplicate capability dispatch inside the MCP boundary

Rejected. Phase 11 already owns typed dispatch, one-attempt execution, result-family validation, and result identity admission.

### Return raw `AthenaQueryResult`

Rejected. It contains operational engine metadata that is not required for the first business-result contract.

### Enable all four capability result families at once

Rejected. Knowledge, hybrid, and public-analysis outputs have different provenance, content, citation, and disclosure semantics. They require separate evidence before protocol exposure.

### Change the Gate 13.3 execution server in place

Rejected. The identity-only Gate 13.3 proof remains useful and should not silently gain business-content disclosure semantics.

## Consequences

Positive:

- business-result exposure becomes an explicit code-owned policy;
- existing execution authority is reused, not duplicated;
- legacy `execute_authorized_capability(...)` behavior remains compatible;
- structured results are bounded twice: by semantic query authority and by MCP projection admission;
- internal Athena operational metadata stays private by default;
- future result families require deliberate independent decisions.

Costs:

- one additive execution-outcome type/function is required;
- a third explicit offline MCP server builder exists;
- result projection is intentionally capability-specific rather than generic;
- knowledge/hybrid/public result transport remains incomplete.

## AWS / IAM impact

```text
new AWS resources:          0
new IAM roles/policies:     0
new model invocations:      0
public MCP endpoint:        0
MCP deployed runtime:       0
AgentCore runtime:          0
A2A runtime:                0
runtime-exposure authority: 0
```

The Gate 13.4 proof remains in-process and uses deterministic executor fixtures.

## AIP-C01 learning connection

This gate reinforces an important production GenAI pattern: tool execution success does not imply that every downstream object is safe to expose. Execution authority, result admission, result projection, and transport disclosure are distinct control planes. Explicit schemas and deterministic provenance binding are preferable to framework-driven generic serialization when business evidence crosses an interoperability boundary.
