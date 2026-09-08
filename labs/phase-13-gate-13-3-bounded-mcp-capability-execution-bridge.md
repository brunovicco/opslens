# Phase 13 — Gate 13.3: Bounded MCP Capability Execution Bridge

_Date: 2026-09-08_

## Status

**IMPLEMENTED / VALIDATION PENDING.**

Starting checkpoint:

```text
main:   e8f986c3f681c5c189ec7a42f58f7b49c12384dd
issue:  #186
branch: feat/phase13-mcp-capability-execution-bridge
PR:     #187
```

## Objective

Connect the already-proven MCP reference/admission path to the existing Phase 11 typed capability executor without giving MCP any new business-input, authorization, retry/fallback, provider/model, result-projection, or runtime-exposure authority.

Permanent rule:

> **MCP is an interoperability boundary, not new business authority.**

## Frozen upstream authority

Gate 13.3 reuses instead of replacing:

```text
Gate 13.1: mcp-capability-exposure:v1
Phase 11:  single-agent-execution:v1
Gate 13.2: reference-only official MCP SDK adapter
```

The protocol still receives exactly:

```text
invocation_id
invocation_sha256
```

It cannot author the business input carried by the resolved typed invocation.

## Bounded execution path

```text
MCP Client
 -> exact closed Gate 13.1 tool
 -> Gate 13.2 raw argument-shape refusal
 -> {invocation_id, invocation_sha256}
 -> deterministic McpInvocationResolver
 -> exact existing AgentCapabilityInvocation
 -> Gate 13.1 admit_mcp_tool_call(...)
 -> existing execute_authorized_capability(...)
 -> exact AgentCapabilityExecution
 -> McpCapabilityExecutionBridge
 -> identity/digest-only structured MCP output
 -> STOP
```

There is no generic MCP dispatch registry and no new executor implementation in the MCP boundary.

## New deterministic evidence contract

Gate 13.3 freezes:

```text
mcp-capability-execution:v1
```

`McpCapabilityExecutionBridge` content-addresses the exact relationship between:

```text
closed MCP tool
existing capability
upstream AuthorizedAgentAction identity
existing typed invocation identity + digest
Gate 13.1 admission identity + digest
Phase 11 execution identity + digest
downstream admitted result digest
```

A standalone forged bridge fails validation if any identifier/digest pair is inconsistent.

## Execution authority

`execute_mcp_invocation_reference(...)` performs the following deterministic sequence:

```text
1. resolve exact invocation reference
2. revalidate resolver-returned ID + digest
3. run Gate 13.1 MCP admission
4. call existing execute_authorized_capability(...) once
5. bind admitted execution to MCP admission
6. return content-minimized projection
```

The Phase 11 executor already owns:

```text
closed typed invocation dispatch
exactly one executor attempt
no adaptive retry
no alternate capability fallback
result-family admission
result/request identity admission
stable content-free execution failure categories
```

Gate 13.3 does not duplicate or loosen those rules.

## Separate MCP servers

Gate 13.2 admission-only semantics remain intact:

```text
build_offline_mcp_server(...)
 -> admission only
 -> STOP before execution
```

Gate 13.3 introduces a separate execution proof:

```text
build_offline_mcp_execution_server(...)
 -> admission
 -> existing typed execution
 -> execution bridge evidence
```

This prevents a previously frozen admission-only adapter from silently changing meaning.

## Protocol output boundary

Successful Gate 13.3 calls expose only:

```text
contract_version
tool_name
capability
action_id
invocation_id
invocation_sha256
admission_id
admission_sha256
execution_id
execution_sha256
downstream_result_sha256
bridge_id
bridge_sha256
```

The test explicitly proves the output does not include sample structured-query business data such as:

```text
CVE-2026-0001
offline-mcp-execution-1
0.91
```

Business result projection and transport remain deferred.

## Failure-path proof

The deterministic offline test slice covers:

```text
content-addressed bridge identity
forged execution ID/digest pair rejected
exact resolved invocation object reaches executor
one successful MCP call -> exactly one executor call
tool/capability mismatch -> zero executor calls
executor exception -> stable MCP failure without downstream detail leak
wrong executor result family -> fail closed
result bound to a different invocation -> fail closed
extra `sql` argument -> INVALID_PARAMS before executor
```

The existing Gate 13.2 raw-argument middleware remains before the execution bridge.

## First CI feedback

The first PR validation reached Ruff successfully but strict Pyright rejected an untyped dataclass `default_factory=list` in the new test recorder:

```text
Type of "calls" is partially unknown
Type of "calls" is "list[Unknown]"
```

This was corrected by replacing the generic factory with a typed helper returning:

```python
list[StructuredSecurityQueryInvocation]
```

No `type: ignore` was added and no runtime behavior changed.

## Cardinality and cost boundary

```text
new model invocations:                  0
new inference cost:                     USD 0.00
capability executions per accepted call: exactly 1
MCP adaptive retries:                   0
MCP alternate-capability fallback:      0
```

The successful offline proof uses deterministic executor fixtures; it does not call AWS merely to prove protocol-to-executor wiring.

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

OpsLens PR #89 remains separate long-lived consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. Gate 13.3 does not modify, rebase, merge, close, or reuse it.

## What Gate 13.3 proves

```text
an admitted MCP invocation reference can reach the existing typed executor
MCP admission can remain mandatory before execution
the exact resolved invocation can be preserved into execution
one protocol call can be bounded to one executor attempt
existing Phase 11 result admission can remain authoritative
MCP execution evidence can be content-addressed without exposing business result content
protocol failure can remain stable/content-minimized
```

## What Gate 13.3 does not prove

```text
business result transport through MCP
persistent invocation registry
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
docs/adr/0049-bounded-mcp-capability-execution-bridge.md
```

## Exit checklist

```text
[x] Gate 13.2 merged and state synchronized before entry
[x] issue #186 created
[x] branch created from exact main
[x] mcp-capability-execution:v1 defined
[x] bridge evidence binds admission + invocation + execution identities
[x] Gate 13.1 admission remains mandatory
[x] existing execute_authorized_capability(...) remains execution authority
[x] separate execution server preserves Gate 13.2 admission-only semantics
[x] official SDK in-process execution tests added
[x] one accepted call executes exactly once
[x] extra MCP executable arguments remain rejected before execution
[x] result mismatch and executor failures fail closed
[x] business result content is not transported
[x] no model/AWS/IAM/public runtime expansion
[x] ADR 0049 added and indexed
[x] Gate 13.3 lab added
[x] draft PR #187 opened
[ ] final exact-head MCP CI PASS
[ ] PR scope/review threads clean
[ ] protected squash merge
[ ] state synchronization
[ ] issue #186 CLOSED / COMPLETED after state synchronization
```
