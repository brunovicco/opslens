# ADR 0048 — Bounded Offline MCP Protocol Adapter

- Status: Accepted
- Date: 2026-09-08
- Phase: 13 — MCP
- Gate: 13.2 — Bounded MCP Protocol Adapter and Offline Interoperability

## Context

Gate 13.1 froze `mcp-capability-exposure:v1`: four closed MCP-visible tool identities map one-to-one to four existing `AgentCapability` values, and deterministic MCP admission accepts only an already-authorized typed `AgentCapabilityInvocation`.

Gate 13.1 deliberately stopped before adopting an MCP framework. Gate 13.2 must now prove interoperability with the official MCP protocol implementation without allowing protocol JSON to become a second authorization or executable-input authority.

The official `modelcontextprotocol/python-sdk` documentation identifies v2 as the current stable line. The latest verified non-prerelease release at this gate is `v2.2.0`, published 2026-09-07. It supports Python 3.10+ and the in-process `MCPServer` / `Client(server)` path required for an offline interoperability proof.

## Decision

Pin the official SDK exactly for this gate:

```text
mcp==2.2.0
```

and keep it in the OpsLens **development dependency group**, not project runtime dependencies.

Introduce a provider-neutral invocation resolver and an official-SDK adapter around the existing Gate 13.1 admission contract.

The bounded path is:

```text
MCP Client
 -> exact closed Gate 13.1 tool
 -> raw tools/call argument-shape refusal
 -> {invocation_id, invocation_sha256}
 -> McpInvocationReference validation
 -> McpInvocationResolver
 -> exact existing AgentCapabilityInvocation
 -> Gate 13.1 admit_mcp_tool_call(...)
 -> content-minimized McpAdmissionProjection
 -> MCP Client
 -> STOP
```

`execute_authorized_capability(...)` is not part of this gate.

## Protocol input authority

Each MCP tool accepts exactly:

```text
invocation_id: str
invocation_sha256: str
```

The protocol does not author or reinterpret:

```text
SemanticQuery
SQL
knowledge synthesis content
hybrid synthesis content
repository coordinates or URLs
arbitrary args / kwargs
shell commands
credentials
provider/model selection
retry/fallback policy
capability execution result
```

The already-created typed `AgentCapabilityInvocation` remains executable-input authority.

## Raw protocol argument refusal

Real interoperability testing against MCP Python SDK v2.2.0 showed that the high-level generated function argument model does not, by itself, provide the required fail-closed behavior for unknown fields. A `tools/call` request containing the two expected reference fields plus an additional `sql` field was accepted by SDK/Pydantic coercion after the unknown field was ignored.

OpsLens therefore does not equate framework-generated schema validation with executable-input authority.

For the four closed Gate 13.1 tool names, the adapter installs a narrow server middleware that observes raw `tools/call` params before function-model validation and requires the argument key set to be exactly:

```text
{invocation_id, invocation_sha256}
```

Extra or missing keys are refused with stable `INVALID_PARAMS` before resolver lookup or Gate 13.1 admission.

The middleware is intentionally not an authorization engine and does not rewrite requests. Its sole responsibility is fail-closed protocol-edge refusal. Existing deterministic OpsLens application/domain code remains authoritative for reference validation, resolver identity checks, tool/capability matching, authorization identity, and admission evidence.

This preserves the invariant:

> Framework coercion may parse protocol values; it does not decide which executable-input surface OpsLens admits.

## Invocation resolution boundary

The application-owned port is:

```text
McpInvocationResolver.resolve(invocation_id, invocation_sha256)
 -> AgentCapabilityInvocation
```

A resolver lookup is not trusted merely because an object was returned. Application code independently verifies that the returned invocation carries the exact requested `invocation_id` and `invocation_sha256` before Gate 13.1 admission runs.

The first implementation is `InMemoryMcpInvocationResolver`, used only for the offline interoperability proof. Persistent registry/storage remains out of scope.

## MCP server adapter

The official SDK adapter constructs `MCPServer[None]` and registers exactly the four Gate 13.1 names with `add_tool(...)`:

```text
opslens.structured_security_query
opslens.knowledge_guidance
opslens.hybrid_security_answer
opslens.public_repository_analysis
```

Each handler accepts only the two invocation-reference fields and delegates to the same deterministic application service. There is no dynamic registration path and no capability executor dependency.

## Protocol output authority

Successful calls return only a content-minimized deterministic projection:

```text
contract_version
tool_name
capability
action_id
invocation_id
invocation_sha256
admission_id
admission_sha256
```

Business request content, SQL, repository content, provider/model responses, credentials, and execution results are not returned by the Gate 13.2 protocol adapter.

The SDK structured-output boundary uses a transport `TypedDict` rather than exposing the internal slots dataclass directly, because v2.2.0 rejected the internal dataclass as a serializable structured-output schema. This conversion changes only transport representation; the internal deterministic `McpAdmissionProjection` remains the admitted evidence contract.

## Failure behavior

The adapter fails closed for malformed references, unknown invocations, resolver identity substitution, tool/capability mismatch, invalid upstream typed identities, and protocol argument-shape violations.

Extra or missing raw arguments for one of the four closed tools are refused before SDK function-model coercion with stable `INVALID_PARAMS`. Known deterministic boundary rejections become a stable MCP `ToolError` message. Unexpected resolver exceptions are also translated to a different stable error message. Arbitrary downstream exception text is not copied into canonical admission evidence or protocol-visible structured output.

## Dependency placement decision

The first implementation attempt placed `mcp==2.2.0` in `[project].dependencies`.

That was rejected by real CI evidence. Existing Lambda packaging exports project runtime dependencies, so the MCP SDK and its transitive HTTP/ASGI/OAuth/schema dependencies were pulled into Lambda packages unrelated to MCP. Terraform CI then failed the NVD incremental Lambda direct-upload size gate with a package size of `57,899,088` bytes, above the 50 MiB direct-upload limit.

The remediation is architectural rather than a packaging-limit workaround:

```text
mcp==2.2.0 -> development dependency only
```

Gate 13.2 is an offline/in-process interoperability gate and introduces no deployed MCP runtime. Therefore deployed OpsLens Lambda requirements must remain unchanged by the SDK experiment.

This preserves a useful dependency-boundary rule:

> A protocol test dependency is not automatically an application runtime dependency.

## Interoperability proof

Use the official SDK directly in tests:

```text
MCPServer(...)
Client(server)
client.list_tools()
client.call_tool(...)
```

The bounded test suite must prove:

```text
exact four-tool discovery
successful real protocol admission for an existing typed invocation
content-minimized structured output
resolver identity-substitution rejection
tool/capability mismatch rejection
unknown-invocation rejection
extra executable argument rejection before tool handling
zero capability execution
```

No public TCP listener, HTTP endpoint, stdio subprocess, or external network service is required.

## Alternatives rejected

### Keep MCP as a project runtime dependency

Rejected because CI demonstrated that it changes unrelated Lambda deployment artifacts despite Gate 13.2 having no deployed MCP runtime.

### Trust generated MCP/Pydantic argument validation to reject unknown fields

Rejected because the real v2.2.0 protocol test demonstrated that an unexpected `sql` key was silently ignored. The OpsLens contract requires fail-closed rejection, not permissive coercion.

### Expose typed business inputs directly as MCP tool arguments

Rejected because this would create a second executable-input authority parallel to `single-agent-execution:v1`.

### Resolve by invocation ID only

Rejected because the digest is part of the content-addressed identity and must be checked independently.

### Trust any object returned by the resolver

Rejected because a resolver is an adapter boundary. Application code rechecks exact ID and digest before deterministic admission.

### Execute capabilities after protocol admission

Rejected because execution/result transport introduces a separate authority and evidence problem. Gate 13.2 isolates protocol interoperability.

### Deploy Streamable HTTP immediately

Rejected because authentication, network exposure, session lifecycle, rate limits, deployment, IAM, and observability are separate decisions that should not be conflated with the first protocol proof.

## Consequences

Positive:

- real official MCP interoperability is exercised without moving business authority into MCP;
- the protocol-visible input remains only a content-addressed reference;
- unexpected raw argument keys fail closed before permissive framework coercion;
- Gate 13.1 remains the deterministic admission authority;
- resolver substitution and mismatched identities fail closed;
- the SDK cannot silently expand Lambda runtime dependencies;
- protocol failures are content-minimized;
- future transport/runtime decisions can build on a tested adapter boundary.

Trade-offs:

- clients cannot create arbitrary new OpsLens invocations through MCP;
- the adapter carries a narrow middleware guard because SDK defaults are more permissive than the OpsLens contract;
- the in-memory resolver is not a production registry;
- no capability execution is exposed yet;
- no deployed/public MCP interoperability is claimed.

## AWS / IAM / runtime impact

```text
new AWS resources:          0
new IAM roles/policies:     0
model invocations:          0
capability executions:      0
public MCP endpoint:        0
MCP deployed runtime:       0
AgentCore runtime:          0
A2A runtime:                0
runtime-exposure authority: 0
```

Deferred OpsLens PR #89 remains separate Governed LLM Gateway cross-project work and is not modified by this decision.

## AIP-C01 learning connection

This gate demonstrates three practical production lessons. Interoperability protocols remain subordinate to deterministic authorization and execution boundaries: protocol shape is not business authority. Framework-generated validation must be adversarially verified rather than assumed to be fail closed. Dependency scope is also runtime architecture: a development-only SDK experiment should not silently enter unrelated Lambda artifacts; CI package-size evidence is a valid signal that the dependency boundary is wrong, not a reason to weaken deployment limits.
