# ADR 0047 — Bounded MCP Capability Exposure

- Status: Accepted
- Date: 2026-09-08
- Phase: 13 — MCP
- Gate: 13.1 — Bounded MCP Capability Exposure Contract

## Context

Phase 12 is complete. Its measured architecture retains the Phase 11 single-agent reasoning reference and the Gate 12.1 deterministic specialization/handoff mechanism while preserving the Gate 12.3 two-model topology only as historical, non-default experiment evidence.

Phase 13 introduces MCP interoperability. The first design question is not which MCP server framework to run. The first question is what authority an MCP boundary is allowed to expose.

OpsLens already has four closed `AgentCapability` values and a separate typed execution contract. Each typed invocation contains one exact `AuthorizedAgentAction` and content-addressed invocation identity. Introducing MCP directly over arbitrary JSON arguments would duplicate or bypass these deterministic boundaries.

The architecture therefore needs to freeze MCP identity and admission semantics before adding an MCP SDK, network transport, authentication mechanism, or capability execution path.

## Decision

Freeze:

```text
mcp-capability-exposure:v1
```

with exactly four MCP tool identities:

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

Gate 13.1 admits only an already-authorized typed invocation reference:

```text
existing AuthorizedAgentAction
 + existing typed AgentCapabilityInvocation
 -> closed McpToolName
 -> deterministic tool/capability match
 -> content-addressed McpToolCallAdmission
 -> STOP
```

MCP does not create the `AuthorizedAgentAction` and does not create the typed invocation.

The admission evidence binds:

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

Raw model output, provider output, executor output, credentials, or arbitrary downstream messages are not part of MCP admission identity.

## Invocation-reference design

The first MCP contract deliberately does **not** expose arbitrary tool `args` or `kwargs`.

The underlying typed invocation already owns exact execution semantics:

```text
StructuredSecurityQueryInvocation
KnowledgeGuidanceInvocation
HybridSecurityAnswerInvocation
PublicRepositoryAnalysisInvocation
```

Each invocation is already bound to an exact authorization and deterministic input identity. MCP therefore references that admitted object rather than becoming another authority that can author:

```text
SemanticQuery
SQL
knowledge synthesis request
hybrid synthesis request
public repository coordinates
URLs
shell commands
credentials
provider/model choice
retry/fallback policy
execution result
```

A later transport gate may define how a protocol-level invocation reference resolves to an already-admitted server-side invocation. It must not reinterpret this decision as permission for unrestricted arguments.

## Closed raw tool-name parser

Transport-visible strings cross a deterministic parser into `McpToolName`.

Unknown or malformed names fail closed. A raw string is not itself a capability authorization.

## Existing authority remains authoritative

The MCP boundary depends inward on the existing Phase 11 contracts:

```text
single-agent-authority:v1
single-agent-execution:v1
```

`capability_for_invocation(...)` and `action_for_invocation(...)` remain the source of exact typed invocation authority.

MCP admission rejects:

```text
unknown invocation type
tool/capability mismatch
invalid upstream action identity
invalid invocation identity
forged admission identity
unknown tool name
```

## Security invariants

```text
MCP tool name != capability authorization
MCP tool exposure != executable argument authority
MCP call admission != capability execution
MCP transport success != business/evidence truth
MCP result != runtime exposure truth
```

`Repository Risk != Runtime Exposure` remains unchanged.

## No external MCP SDK in Gate 13.1

Gate 13.1 is intentionally provider-neutral and transport-neutral. It adds no MCP framework dependency.

This keeps framework behavior, network lifetime, authentication, session state, protocol serialization, and server deployment outside the first authority decision.

A later gate may evaluate the official MCP SDK or another transport adapter only after this contract is merged.

## Alternatives rejected

### Add the MCP SDK first and expose Python functions as tools

Rejected because framework decoration would define a public tool surface before deterministic authority and argument semantics were frozen.

### Expose arbitrary JSON args/kwargs directly through MCP

Rejected because it would create a second executable-input authority parallel to the existing typed invocation contract.

### Build a dynamic MCP tool registry

Rejected because OpsLens has a closed capability set. Dynamic registration would expand the trust surface without a measured requirement.

### Let MCP tool name grant authorization

Rejected because naming a capability is not authorization. Existing `AuthorizedAgentAction` remains mandatory.

### Execute the capability during Gate 13.1

Rejected because the first gate isolates exposure/admission semantics. Execution and result transport introduce additional failure, provenance, and runtime concerns.

### Deploy a public/network MCP server now

Rejected because transport authentication, session lifecycle, IAM, rate limits, observability, and deployment would confound the first contract decision.

## Consequences

Positive:

- MCP cannot broaden the existing four-capability authority surface;
- transport-visible tool identity is deterministic and fail closed;
- MCP admission is bound to exact existing authorization and invocation evidence;
- arbitrary executable argument surfaces remain excluded;
- a future MCP server adapter can be tested against a frozen core contract;
- no external MCP SDK or runtime infrastructure is required to validate Gate 13.1.

Trade-offs:

- callers cannot invoke tools from arbitrary JSON arguments in Gate 13.1;
- a later gate must define safe resolution from MCP protocol input to existing invocation identity;
- the first MCP slice proves authority semantics, not interoperability with a real MCP client.

## AWS / IAM / runtime impact

```text
new AWS resources:          0
new IAM roles/policies:     0
new model invocations:      0
capability executions:      0
MCP SDK dependency:         0
MCP network runtime:        0
AgentCore runtime:          0
A2A runtime:                0
public runtime:             0
runtime-exposure authority: 0
```

Deferred OpsLens PR #89 remains separate Governed LLM Gateway cross-project work and is not modified by this decision.

## AIP-C01 learning connection

This gate demonstrates a production principle that is easy to miss in agent interoperability designs: protocol exposure is a trust boundary. A tool protocol should not silently become a new authorization system. Freezing identity, argument authority, deterministic admission, evidence provenance, and failure semantics before adopting a framework keeps interoperability subordinate to the governed application boundary.
