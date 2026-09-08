# ADR 0049 — Bound MCP Capability Execution to Existing Typed Authority

- Status: Accepted
- Date: 2026-09-08
- Phase: 13 — MCP
- Gate: 13.3 — Bounded MCP Capability Execution Bridge

## Context

Gate 13.1 froze the closed MCP tool/capability exposure and admission contract:

```text
mcp-capability-exposure:v1
```

Gate 13.2 then proved real official MCP Python SDK v2.2.0 interoperability with reference-only protocol input:

```text
{invocation_id, invocation_sha256}
```

and deliberately stopped before `execute_authorized_capability(...)`.

Phase 11 already owns the executable-input and execution-result authority through:

```text
single-agent-execution:v1
```

The architectural question for Gate 13.3 is therefore not how MCP should execute arbitrary tool arguments. The question is whether an already-admitted MCP reference can reach the existing typed executor without creating a second business-authority surface.

## Decision

Introduce a separate content-addressed bridge contract:

```text
mcp-capability-execution:v1
```

The accepted path is:

```text
MCP protocol call
 -> closed MCP tool identity
 -> Gate 13.2 raw argument-shape refusal
 -> exact invocation ID + digest
 -> deterministic resolver
 -> existing typed AgentCapabilityInvocation
 -> Gate 13.1 admit_mcp_tool_call(...)
 -> existing execute_authorized_capability(...)
 -> existing AgentCapabilityExecution
 -> McpCapabilityExecutionBridge
 -> identity/digest-only MCP structured output
 -> STOP before business result transport
```

MCP does not construct `AuthorizedAgentAction`, does not create or reinterpret `AgentCapabilityInvocation`, and does not select or replace capability executors. The existing Phase 11 executor remains the execution authority.

## Execution cardinality

For one accepted MCP execution call:

```text
MCP admission attempts:          1
capability executor calls:       exactly 1
adaptive MCP retries:            0
alternate capability fallback:   0
new model invocations:           0
```

Gate 13.3 adds no retry/fallback loop around the existing executor.

## Bridge evidence

`McpCapabilityExecutionBridge` binds only deterministic identity/evidence fields:

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

The bridge validates that:

- tool and capability remain the code-owned Gate 13.1 mapping;
- admission action identity matches the typed invocation authorization;
- admission invocation ID and digest match the exact resolved invocation;
- execution action/capability/invocation identity matches that same invocation;
- all content-addressed IDs and digests are internally consistent.

A mismatch fails closed.

## Protocol-output boundary

Gate 13.3 does **not** transport business result content through MCP.

The protocol may expose deterministic identity and digest evidence needed to prove the execution binding, but it does not newly expose:

```text
Athena rows or query text
knowledge synthesis answer text
hybrid synthesis claims
repository evidence/content
SQL
provider/model messages
credentials
arbitrary downstream exception content
```

Business-result projection/transport is a separate later decision.

## Failure boundary

The official SDK adapter returns stable, content-minimized failures for:

```text
reference/admission rejection
executor failure
executor result-contract failure
unexpected bridge/application failure
```

The existing `AgentCapabilityExecutionError` categories remain authoritative for executor/result admission. Raw downstream exception messages are not promoted into MCP evidence.

Gate 13.2 raw `tools/call` key validation remains in front of execution, so extra fields such as `sql` are rejected before resolver lookup or executor invocation.

## Separate admission-only and execution adapters

Retain the Gate 13.2 admission-only server and introduce a separate offline execution server.

This prevents the meaning of the existing admission-only adapter from silently changing after Gate 13.2. Callers and tests can distinguish:

```text
admission-only interoperability
!=
capability execution interoperability
```

## Alternatives rejected

### Let MCP tool arguments become the executable business input

Rejected. This would bypass `single-agent-execution:v1` and create a second executable-input authority.

### Reimplement capability dispatch inside the MCP adapter

Rejected. Dispatch, result-family checks, one-attempt cardinality, and stable execution failures are already owned by `execute_authorized_capability(...)`.

### Return the full downstream business result from Gate 13.3

Rejected. Execution binding and result transport have different data-exposure and evidence-admission risks and should be evaluated separately.

### Replace the admission-only Gate 13.2 server with the executing server

Rejected. It would mutate the semantics of an already-frozen interoperability proof instead of making the new execution authority transition explicit.

## Consequences

Positive:

- MCP gains real capability execution without gaining generic business-input authority;
- Gate 13.1 admission remains mandatory;
- Phase 11 typed execution and result admission remain reused rather than duplicated;
- exactly-once application-level execution is testable with deterministic doubles;
- protocol output remains content-minimized;
- Gate 13.2 admission-only semantics remain preserved.

Costs:

- the adapter now requires an `AgentCapabilityExecutors` dependency;
- a second explicit MCP server builder exists for the execution proof;
- business result transport remains intentionally incomplete.

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

The first proof remains offline/in-process and uses deterministic executor fixtures.

## AIP-C01 learning connection

This gate demonstrates a key production AI-platform pattern: protocol/tool interoperability does not imply execution authority. A model or protocol may select or reference a capability, but code-owned authorization, typed executable input, deterministic dispatch, result admission, and failure semantics remain separate control planes.
