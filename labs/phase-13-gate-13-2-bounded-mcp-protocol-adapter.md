# Phase 13 — Gate 13.2: Bounded MCP Protocol Adapter and Offline Interoperability

_Date: 2026-09-08_

## Status

**IMPLEMENTED / FINAL VALIDATION PENDING.**

Starting checkpoint:

```text
main:   4728685e70b7cebfcb07543a763cf82a98d97ae5
issue:  #183
branch: feat/phase13-mcp-protocol-adapter
PR:     #184
```

Gate 13.2 introduces the first real official MCP SDK adapter while keeping the Gate 13.1 deterministic authority contract unchanged.

## Gate objective

The governing rule remains:

> **MCP is an interoperability boundary, not new business authority.**

The objective is to prove real protocol interoperability with the official MCP Python SDK without granting protocol JSON new authorization or executable-input authority.

## Official SDK verification

Verified official source:

```text
repository: modelcontextprotocol/python-sdk
stable line: v2
release: v2.2.0
published: 2026-09-07
Python requirement: >=3.10
OpsLens pin: mcp==2.2.0
```

The official v2 API used by this gate is:

```python
from mcp import Client
from mcp.server import MCPServer
```

The first proof uses the official in-process path:

```text
MCPServer(...)
 -> Client(server)
 -> list_tools() / call_tool(...)
```

No public network listener is required.

## Dependency boundary

The SDK is intentionally pinned in the `dev` dependency group:

```text
[dependency-groups].dev -> mcp==2.2.0
```

It is not an OpsLens project runtime dependency.

The regenerated lock proves:

```text
package opslens runtime dependencies:
  aws-lambda-powertools
  boto3
  packaging

package opslens dev dependencies:
  boto3-stubs
  mcp
  pyright
  pytest
  ruff
```

This placement was corrected from the first implementation attempt after real Terraform CI exposed an invalid runtime dependency boundary.

## First dependency-placement failure

The initial `mcp==2.2.0` pin was placed under `[project].dependencies`.

That caused existing Lambda packaging to export the entire MCP dependency graph into unrelated deployment packages. Terraform CI then failed the NVD incremental Lambda direct-upload size check:

```text
package size: 57,899,088 bytes
limit:        50 MiB direct upload
result:       FAIL
```

This was not remediated by weakening the package limit or changing Lambda deployment strategy.

The correct fix was:

```text
MCP SDK experiment dependency -> dev-only
```

because Gate 13.2 has no deployed MCP runtime.

A one-shot branch workflow regenerated `uv.lock` and removed itself. Lock refresh run:

```text
run: 34227025760
job: 102063531236
result: PASS
final one-shot cleanup head: afdebe8232bfbe3235979c5f3fa92d8776f82b47
```

## Bounded authority path

```text
MCP Client
 -> exact closed Gate 13.1 tool name
 -> raw argument-shape fail-closed middleware
 -> {invocation_id, invocation_sha256}
 -> McpInvocationReference
 -> McpInvocationResolver
 -> exact existing AgentCapabilityInvocation
 -> independent ID + digest revalidation
 -> Gate 13.1 admit_mcp_tool_call(...)
 -> McpAdmissionProjection
 -> MCP Client
 -> STOP
```

`execute_authorized_capability(...)` is not called.

## Protocol input surface

Every exposed MCP tool accepts exactly:

```text
invocation_id
invocation_sha256
```

The protocol does not accept or author:

```text
SemanticQuery
SQL
knowledge synthesis request content
hybrid synthesis request content
repository coordinates or URLs
arbitrary args / kwargs
shell commands
credentials
provider/model selection
retry/fallback policy
capability execution result
```

The real v2.2.0 interoperability test exposed an important framework-default behavior: the high-level function argument model does not itself fail closed on unknown fields. An extra field such as `sql` was silently ignored by SDK/Pydantic argument coercion and the tool call otherwise succeeded.

OpsLens therefore does **not** treat the generated framework schema as the executable-input authority. A server middleware inspects raw `tools/call` params before SDK function-model validation and requires the exact key set:

```text
{invocation_id, invocation_sha256}
```

Extra or missing keys fail with stable `INVALID_PARAMS` before resolver lookup, Gate 13.1 admission, or any capability execution. The security property is owned by OpsLens code rather than inferred from a permissive framework default.

## Invocation reference contract

`McpInvocationReference` validates:

```text
invocation_id follows single-agent-execution:v1 identity format
invocation_sha256 is lowercase SHA-256
invocation_id suffix == invocation_sha256
```

This prevents internally contradictory protocol references from reaching resolution.

## Resolver port

Provider-neutral port:

```text
McpInvocationResolver.resolve(invocation_id, invocation_sha256)
 -> AgentCapabilityInvocation
```

Resolver output is still checked by application code. A resolver that returns a different valid invocation is rejected before Gate 13.1 admission.

The first adapter is:

```text
InMemoryMcpInvocationResolver
```

It is an offline interoperability fixture, not a production persistence mechanism.

## Official MCP server adapter

The adapter registers exactly four tools through official `MCPServer.add_tool(...)`:

```text
opslens.structured_security_query
opslens.knowledge_guidance
opslens.hybrid_security_answer
opslens.public_repository_analysis
```

The closed Gate 13.1 `McpToolName` enum remains the naming source.

There is no dynamic plugin/tool registry.

## Pyright feedback and remediation

The first adapter implementation used nested `@server.tool(...)` decorators. Ruff passed, but strict Pyright correctly reported the four nested handler function names as unused from static analysis because framework registration occurred through decoration.

The remediation changed registration to explicit:

```text
server.add_tool(handler, name=closed_tool_name, structured_output=True)
```

This preserves the protocol semantics while making registration explicit to static analysis. No authority behavior changed.

A later strict-Pyright pass also rejected a `set(raw_arguments)` comparison because the SDK middleware context exposes raw params through partially unknown mapping key types. The remediation retained strict typing without `type: ignore`: exact argument shape is checked through mapping length plus membership of both required code-owned keys.

## SDK argument-validation discovery

A real `Client.call_tool(...)` regression case included:

```text
invocation_id
invocation_sha256
sql = "DROP TABLE findings"
```

Without the OpsLens pre-validation middleware, MCP v2.2.0/Pydantic ignored the additional `sql` field and returned a successful admission result. This is unacceptable for a boundary whose contract says arbitrary executable arguments are not admitted.

The remediation uses the SDK-supported server middleware hook, which observes raw request params before handler validation. For one of the four closed tool names, the middleware refuses any argument mapping whose keys are not exactly the two reference fields.

This deliberately avoids relying on provisional middleware for business authorization or argument rewriting. The middleware only performs a narrow refusal at the protocol edge; deterministic invocation validation, resolver identity checking, capability mapping, and admission remain in existing OpsLens application/domain code.

## Content-minimized output

Successful protocol calls expose only:

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

Underlying business input content and execution output remain absent.

## Failure behavior

The protocol adapter fails closed for:

```text
malformed invocation reference
unknown invocation
resolver identity mismatch
tool/capability mismatch
invalid upstream typed identity
extra or missing protocol arguments
```

Unexpected/missing raw arguments for one of the four closed tools are refused before SDK function-model coercion with stable `INVALID_PARAMS`. Known deterministic admission-boundary rejection is translated to a stable MCP `ToolError`. Unexpected resolver failure uses a separate stable message. Arbitrary downstream exception details are not copied into deterministic admission evidence.

## Test boundary

The Gate 13.2 test slice adds real official SDK coverage for:

```text
four exact tools discovered by Client.list_tools()
real Client.call_tool(...) successful admission
content-minimized structured output
resolver substitution rejection
tool/capability mismatch failure
unknown invocation failure
extra SQL argument refused before tool handling
```

The existing Gate 13.1 tests remain in the same MCP slice.

No capability executor is constructed or invoked by the adapter path.

## CI boundary

`.github/workflows/mcp-ci.yml` now additionally verifies:

```text
installed mcp version == 2.2.0
```

then runs:

```text
MCP boundary import smoke
Ruff MCP slice
Pyright strict MCP slice
pytest MCP slice
```

Changing `pyproject.toml` / `uv.lock` also exercises existing Python and Terraform CI so dependency-placement regressions cannot be hidden inside the MCP-specific workflow.

## AWS / IAM / runtime impact

```text
new AWS resources:          0
new IAM roles/policies:     0
new model invocations:      0
capability executions:      0
public MCP endpoint:        0
MCP deployed runtime:       0
AgentCore runtime:          0
A2A runtime:                0
runtime-exposure authority: 0
```

## Deferred Governed LLM Gateway integration

OpsLens PR #89 remains separate long-lived cross-project work for **Phase 14 — Case 3 of `brunovicco/governed-llm-gateway`**. Gate 13.2 does not modify, rebase, merge, close, or reuse it.

## What Gate 13.2 proves

```text
official MCP SDK can expose the four frozen OpsLens tool identities
real MCP Client/server protocol handling can remain reference-only
protocol input can resolve an already-created typed invocation without authoring it
raw protocol argument shape can be refused before permissive SDK coercion
resolver output can be revalidated before admission
Gate 13.1 remains the deterministic admission authority
structured MCP output can be content-minimized to deterministic admission evidence
offline protocol interoperability can be tested with zero capability execution
MCP SDK dependency scope can be kept out of unrelated deployed Lambda runtimes
```

## What Gate 13.2 does not prove

```text
capability execution through MCP
business result transport through MCP
persistent invocation registry
stdio subprocess interoperability
Streamable HTTP interoperability
public MCP endpoint
MCP authentication/authorization transport
network reliability or production SLOs
AgentCore runtime behavior
A2A interoperability
runtime exposure evidence
```

## AIP-C01 learning checkpoint

Three lessons are intentionally preserved. Protocol interoperability does not imply authorization authority: the SDK handles protocol mechanics while deterministic OpsLens code still validates references and admission. Framework-generated validation is not automatically a fail-closed security boundary; real adversarial protocol tests must verify how unknown fields are treated. Dependency scope is also architecture: a development-only MCP proof must not silently enlarge unrelated Lambda runtime artifacts.

## Architecture record

```text
docs/adr/0048-bounded-offline-mcp-protocol-adapter.md
```

## Exit checklist

```text
[x] Gate 13.1 state synchronized before Gate 13.2 entry
[x] issue #183 created
[x] branch created from exact main 4728685e70b7cebfcb07543a763cf82a98d97ae5
[x] official MCP stable release verified
[x] mcp==2.2.0 pinned exactly
[x] SDK moved to dev-only after runtime packaging regression
[x] uv.lock regenerated deterministically
[x] one-shot lock workflow removed itself
[x] McpInvocationReference implemented
[x] provider-neutral McpInvocationResolver implemented
[x] resolver result ID + digest independently revalidated
[x] in-memory offline resolver implemented
[x] official MCPServer adapter implemented
[x] exactly four closed tools registered
[x] protocol input limited to invocation ID + digest
[x] raw tools/call argument shape fails closed before SDK coercion
[x] content-minimized admission output implemented
[x] stable fail-closed protocol errors implemented
[x] real in-process SDK tests added
[x] arbitrary executable argument regression added
[x] no capability execution
[x] no AWS/IAM/public runtime expansion
[x] ADR 0048 added and indexed
[x] Gate 13.2 lab added
[x] draft PR #184 opened
[ ] final exact-head MCP CI PASS
[ ] final exact-head Python CI PASS
[ ] final exact-head Terraform CI PASS
[ ] PR scope/review threads clean
[ ] protected squash merge
[ ] public/current state synchronized
[ ] issue #183 CLOSED / COMPLETED after state synchronization
```
