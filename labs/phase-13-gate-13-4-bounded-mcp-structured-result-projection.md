# Phase 13 — Gate 13.4: Bounded MCP Structured Result Projection and Offline Transport

_Date: 2026-09-08_

## Status

**IMPLEMENTED / FINAL VALIDATION PENDING.**

Starting checkpoint:

```text
main:   a7ded96a326bfa0dbecad8764b10af16507599be
issue:  #189
branch: feat/phase13-mcp-structured-result-projection
PR:     #190
```

## Objective

Expose the first explicit business-result slice through MCP without turning protocol/framework serialization into a new disclosure or executable-input authority.

Permanent rules:

> **MCP is an interoperability boundary, not new business authority.**

> **Execution success != result transport authority.**

Gate 13.4 is deliberately limited to the already-bounded `structured_security_query` capability.

## Frozen upstream authority

The gate reuses:

```text
mcp-capability-exposure:v1
mcp-capability-execution:v1
single-agent-execution:v1
```

The MCP request still carries only:

```text
invocation_id
invocation_sha256
```

The protocol does not author `SemanticQuery`, SQL, rows, result fields, provider/model selection, credentials, retry policy, or fallback policy.

## Why an additive execution outcome was required

Before this gate, the Phase 11 executor intentionally returned only:

```text
AgentCapabilityExecution
```

The exact admitted downstream result object was checked and then discarded from the return value. Re-executing or duplicating capability dispatch inside MCP to recover that object would violate the one-attempt authority boundary.

Gate 13.4 therefore adds:

```text
execute_authorized_capability_outcome(...)
 -> AgentCapabilityExecutionOutcome(
      execution=existing AgentCapabilityExecution,
      result=exact already-admitted typed result,
    )
```

while preserving the old API:

```text
execute_authorized_capability(...)
 -> execute_authorized_capability_outcome(...)
 -> .execution
```

A regression test verifies the legacy and additive APIs produce the same `execution_id`, `execution_sha256`, and downstream result digest for the same typed invocation/result.

## Bounded result path

```text
MCP Client
 -> exact structured-security tool
 -> Gate 13.2 raw argument-shape refusal
 -> {invocation_id, invocation_sha256}
 -> deterministic resolver
 -> exact StructuredSecurityQueryInvocation
 -> Gate 13.1 admission
 -> existing typed executor exactly once
 -> StructuredSecurityQueryResultBinding admission
 -> AgentCapabilityExecution
 -> Gate 13.3 McpCapabilityExecutionBridge
 -> explicit structured EPSS projector
 -> mcp-result-projection:v1
 -> MCP Client
 -> STOP
```

No generic object serializer or result plugin registry is introduced.

## New contract

Gate 13.4 freezes:

```text
mcp-result-projection:v1
```

The projection is content-addressed and binds:

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

The business rows participate in the projection digest.

## Source and protocol shapes

The existing Gate 6 compiler owns the actual query projection:

```text
SELECT "cve", "epss"
```

Therefore the admitted Athena result must expose exactly:

```text
("cve", "epss")
```

Gate 13.4 maps that internal source shape to the protocol semantic shape:

```text
columns = ["cve", "epss_score"]
rows = [
  {"cve": "CVE-...", "epss_score": "0..1"}
]
```

The mapper is explicit. It does not iterate arbitrary result fields.

## Data minimization

Successful result transport deliberately excludes:

```text
query_execution_id
data_scanned_bytes
engine_execution_time_ms
total_execution_time_ms
SQL
execution parameters
provider/model messages
credentials
adapter internals
arbitrary downstream exception content
```

The official SDK test asserts representative internal values do not appear in structured protocol output.

## Result bounds

The projector independently revalidates:

```text
row_count <= invocation.query.limit
invocation.query.limit <= 100
row_count <= 100
row width == 2
source columns == ("cve", "epss")
CVE identity shape is explicit
EPSS is bounded decimal text in 0..1
```

This matters because a downstream object being admitted as one typed result family does not automatically authorize every possible field/value shape for external transport.

## Capability scope

Business-result transport in this gate exists only for:

```text
structured_security_query
```

These remain intentionally unsupported:

```text
knowledge_guidance
hybrid_security_answer
public_repository_analysis
```

The result server registers only the structured-security tool. The application projector also rejects a non-structured tool before capability execution, so there is no generic result fallback.

## Server semantics remain additive

The prior servers keep their meanings:

```text
build_offline_mcp_server(...)
 -> admission only

build_offline_mcp_execution_server(...)
 -> admission + execution
 -> identity/digest-only result
```

Gate 13.4 adds:

```text
build_offline_mcp_structured_result_server(...)
 -> admission + exactly one execution + structured business projection
```

Existing Gate 13.2/13.3 callers do not silently gain business-content disclosure.

## Failure-path proof

The Gate 13.4 tests cover:

```text
content-addressed projection identity
forged projection digest rejection
same exact invocation reaches executor once
row count above SemanticQuery.limit rejected
unexpected Athena columns rejected
invalid EPSS value rejected
non-structured result projection rejected before execution
extra `sql` input rejected by Gate 13.2 middleware before execution
executor failure returned through stable content-minimized MCP error
successful MCP output excludes engine/query metadata and SQL
```

The existing MCP test suite remains the regression surface for Gates 13.1–13.3.

## CI feedback during implementation

Two non-authority defects were found before the merge candidate:

1. MCP Ruff reported one line-length issue in the new projection validator; it was formatting-only and corrected without behavior changes.
2. Single-Agent Ruff reported `I001` around the new PEP 695 type alias. A temporary branch-only diagnostic ran the exact Ruff `--fix --diff` behavior and proved Ruff required one fewer blank line between the import block and the `type` alias. The temporary workflow was removed immediately after diagnosis.

No `type: ignore`, rule suppression, or quality-gate weakening was introduced.

A later implementation checkpoint already demonstrated the expanded MCP slice as:

```text
MCP CI run:        34244617484 / run #40
Ruff MCP slice:    PASS
Pyright strict:    0 errors / 0 warnings / 0 informations
pytest MCP slice:  29 passed in 1.21s
```

This is intermediate evidence only. Final Gate 13.4 completion still requires exact-head MCP and Single-Agent CI after all code/docs changes.

## Cost and execution boundary

```text
new model invocations:        0
new inference cost:           USD 0.00
accepted MCP result call:     exactly 1 capability execution
adaptive MCP retries:         0
alternate capability fallback: 0
```

The executor proof is deterministic/offline and does not call AWS merely to demonstrate result projection.

## AWS / IAM / runtime impact

```text
new AWS resources:          0
new IAM roles/policies:     0
GitHub OIDC trust changes:  0
public MCP endpoint:        0
MCP deployed runtime:       0
AgentCore runtime:          0
A2A runtime:                0
runtime-exposure authority: 0
```

## Deferred Governed LLM Gateway integration

OpsLens PR #89 remains separate long-lived consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. Gate 13.4 does not modify, rebase, merge, close, or reuse it.

## What Gate 13.4 proves

```text
an already-admitted typed business result can be preserved without duplicate execution
result disclosure can be a separate deterministic authority from execution
only one explicit capability result family can be transported while others remain closed
business rows can remain bound to invocation/execution/bridge/result provenance
SemanticQuery row authority can remain effective at protocol egress
framework serialization can remain subordinate to a code-owned projection schema
```

## What Gate 13.4 does not prove

```text
knowledge synthesis result transport
hybrid result transport
public-analysis result transport
persistent result registry
stdio or Streamable HTTP interoperability
public MCP endpoint
MCP authentication/authorization transport
network reliability or production SLOs
AgentCore runtime behavior
A2A interoperability
runtime exposure evidence
```

## Architecture record

```text
docs/adr/0050-bounded-mcp-structured-result-projection.md
```

## Exit checklist

```text
[x] Gate 13.3 merged and state synchronized before entry
[x] issue #189 created
[x] branch created from exact main
[x] draft PR #190 opened
[x] additive admitted-result execution outcome implemented
[x] legacy execute_authorized_capability(...) behavior preserved
[x] mcp-result-projection:v1 defined
[x] structured_security_query is the only business-result family exposed
[x] explicit CVE/EPSS projection added; no generic serializer
[x] SemanticQuery row limit reapplied at result egress
[x] Gate 13.2 raw argument refusal remains ahead of execution
[x] separate result server preserves Gate 13.2/13.3 server meanings
[x] official SDK success + failure tests added
[x] no model/AWS/IAM/public runtime expansion
[x] ADR 0050 added
[x] Gate 13.4 lab added
[ ] ADR 0050 indexed
[ ] final exact-head MCP CI PASS
[ ] final exact-head Single-Agent CI PASS
[ ] PR scope/review threads clean
[ ] protected squash merge
[ ] state synchronization
[ ] issue #189 CLOSED / COMPLETED after state synchronization
```
