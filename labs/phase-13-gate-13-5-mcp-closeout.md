# Phase 13 — Gate 13.5: MCP Phase Closeout

_Date: 2026-09-08_

## Status

**IMPLEMENTED / DRAFT PR — FINAL EXACT-HEAD VALIDATION PENDING.**

Starting checkpoint:

```text
main:   915ec9920c3b501631e70a78121fe76fd93be80c
issue:  #192
branch: docs/phase13-mcp-closeout
PR:     #193
```

## Objective

Close Phase 13 around the MCP architecture actually proven by evidence, rather than adding a public/deployed transport solely to make the phase appear more complete.

Permanent rule:

> **MCP is an interoperability boundary, not new business authority.**

Gate 13.5 adds no new protocol behavior. It records the retention decision, exact evidence trail, explicit non-claims, and next-phase boundary.

## Completed Phase 13 sequence

```text
Gate 13.1 — Bounded MCP Capability Exposure Contract           COMPLETE / MERGED
Gate 13.2 — Bounded MCP Protocol Adapter / Offline Interop      COMPLETE / MERGED
Gate 13.3 — Bounded MCP Capability Execution Bridge            COMPLETE / MERGED
Gate 13.4 — Bounded MCP Business Result Projection             COMPLETE / MERGED
Gate 13.5 — MCP Phase Closeout                                  THIS GATE
```

Exact implementation merge trail:

```text
Gate 13.1 / issue #180 / PR #181
merge: 322922aed4abec3b2266a18d15d8145df974a7d1
contract: mcp-capability-exposure:v1

Gate 13.2 / issue #183 / PR #184
merge: 131c086ff85564dbd777cebd6454d70e53ca8332
SDK: mcp==2.2.0, development dependency only

Gate 13.3 / issue #186 / PR #187
merge: 170429c894456adc1e1c38ca93b49f12e310fb94
contract: mcp-capability-execution:v1

Gate 13.4 / issue #189 / PR #190
merge: 87772b1604d4ede0f88f72d4d338ddf553953304
contract: mcp-result-projection:v1
```

Gate 13.4 authoritative state synchronization is on `main` at:

```text
915ec9920c3b501631e70a78121fe76fd93be80c
```

## Retained architecture

Phase 13 closes around this bounded path:

```text
Phase 11 typed AgentCapabilityInvocation/result authority
 -> mcp-capability-exposure:v1
 -> official MCP SDK reference-only protocol adapter
 -> raw tools/call exact key-set refusal
 -> deterministic invocation resolution + revalidation
 -> deterministic MCP admission
 -> mcp-capability-execution:v1
 -> exactly one existing typed executor attempt
 -> existing typed result-family/result-identity admission
 -> mcp-result-projection:v1 for structured_security_query only
 -> allowlisted CVE + EPSS business rows
 -> STOP before public/network runtime
```

The retained design demonstrates interoperability by composing existing deterministic authorities rather than creating a second business-authority plane inside MCP.

## Gate 13.1 retained boundary

Frozen tool surface:

```text
opslens.structured_security_query   -> structured_security_query
opslens.knowledge_guidance          -> knowledge_guidance
opslens.hybrid_security_answer      -> hybrid_security_answer
opslens.public_repository_analysis  -> public_repository_analysis
```

MCP tool naming and exposure remain protocol identity only. They do not create `AuthorizedAgentAction`, business inputs, provider/model authority, SQL, URLs, shell commands, credentials, or execution authority.

## Gate 13.2 retained boundary

Protocol input remains exactly:

```text
invocation_id
invocation_sha256
```

A real SDK interoperability finding showed that generated SDK/Pydantic argument coercion may ignore unexpected fields. OpsLens therefore retains raw exact-key-set validation before framework coercion.

The official MCP Python SDK remains:

```text
mcp==2.2.0
scope: development dependency only
```

This placement is evidence-driven. Moving the SDK into runtime dependencies previously enlarged unrelated Lambda packages and tripped an existing package-size guard. Phase 13 deploys no MCP runtime, so widening deployed dependencies has no justified benefit.

## Gate 13.3 retained boundary

One accepted MCP execution call is bound to exactly one existing typed executor attempt:

```text
McpToolCallAdmission
 + exact AgentCapabilityInvocation
 + exact AgentCapabilityExecution
 -> McpCapabilityExecutionBridge
```

MCP adds no adaptive retry, alternate-capability fallback, dynamic executable argument registry, provider/model selection, or new result-family admission authority.

## Gate 13.4 retained boundary

Business-result disclosure is intentionally narrower than capability execution.

Only:

```text
structured_security_query
```

has a Phase 13 business-result transport policy.

The explicit projector maps the already-admitted structured result to:

```text
columns = ["cve", "epss_score"]
rows = [
  {"cve": "CVE-...", "epss_score": "0..1"}
]
```

It reapplies the semantic-query row limit, keeps the protocol surface bounded to at most 100 rows, validates CVE/EPSS shape, and excludes SQL, Athena query identifiers, scan bytes, engine timing, provider messages, credentials, and arbitrary exception content.

Knowledge, hybrid, and public-repository business-result transport remain unsupported and fail closed.

## Closeout decision

**Close Phase 13 at the bounded offline MCP boundary.**

There is no concrete current consumer/runtime requirement that justifies adding any of these before closeout:

```text
public or Streamable HTTP MCP endpoint
transport authentication/authorization
session lifecycle
persistent invocation/result registry
broader business-result serializers
runtime hosting
new workload identity or IAM
network retry/timeout policy
rate limiting / abuse controls
production MCP SLOs
```

Those concerns are real, but introducing them without a concrete runtime requirement would conflate protocol interoperability with production runtime architecture.

## Why this is not an incomplete MCP phase

The phase question was not “can OpsLens expose an MCP server on the Internet?” It was “can OpsLens add official MCP interoperability without authority drift?”

Gates 13.1–13.4 already prove:

```text
closed protocol-facing tool identity
real official MCP client/server interoperability
fail-closed raw argument validation ahead of framework coercion
deterministic invocation reference resolution and revalidation
mandatory deterministic admission before execution
one accepted call -> one existing typed executor attempt
content-addressed admission/execution provenance
separate execution and business-result disclosure authorities
explicit structured-security result projection
row bounds retained at protocol egress
stable content-minimized failure behavior
```

Adding a deployed transport would answer a different question and requires its own evidence.

## Explicit non-claims

Phase 13 does **not** prove or implement:

```text
generic business-result serialization
knowledge-guidance business-result transport
hybrid-security-answer business-result transport
public-repository-analysis business-result transport
persistent invocation/result registry
stdio subprocess deployment interoperability
Streamable HTTP production interoperability
public MCP endpoint
MCP transport authentication or authorization
network reliability or production SLOs
Amazon Bedrock AgentCore runtime behavior
A2A interoperability
runtime exposure / Amazon Inspector evidence
```

These are deliberate non-claims, not missing evidence to be silently inferred later.

## Frozen authority separations

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

## Closeout evidence

The deterministic closeout artifact is preserved at:

```text
labs/evidence/phase-13-closeout-v1.json
```

It binds:

```text
source main SHA
Gate 13.1–13.4 issues / PRs / merge SHAs
retained contracts
retained protocol/tool surface
result-disclosure scope
authority boundaries
explicit non-claims
MCP SDK dependency disposition
zero runtime/AWS/IAM/model expansion
deferred PR #89 state
next phase
```

## Cost, AWS, IAM, and runtime impact

Gate 13.5 is documentation/evidence closeout only:

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

A real Bedrock or AWS deployment run would not strengthen this closeout because no new cloud/model behavior is being introduced.

## Deferred Governed LLM Gateway integration

OpsLens PR #89 remains separate long-lived consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**.

Preserved head:

```text
3781831795d500b05fa4bc602d50f376b4b1539f
```

Gate 13.5 does not modify, rebase, merge, close, or reuse it. The external project phase numbering must not be confused with OpsLens Phase 14.

## Architecture record

```text
docs/adr/0051-phase13-mcp-closeout.md
```

## AIP-C01 learning connection

The important platform lesson is that tool interoperability does not imply authorization, executable-input authority, result-disclosure authority, or runtime readiness.

A production-quality GenAI platform keeps those authorities separable and measurable. It also avoids adding a managed/network runtime merely for certification coverage: runtime adoption should follow a concrete workload need, least-privilege design, failure-mode analysis, observability, and cost evidence.

## Exit checklist

```text
[x] Gate 13.4 merged and state synchronized before closeout
[x] issue #192 created
[x] branch created from exact main
[x] Gate 13.1–13.4 merge/evidence trail recorded
[x] retained MCP architecture explicitly stated
[x] public/network runtime non-claims preserved
[x] MCP SDK remains dev-only for an evidence-backed reason
[x] deterministic closeout evidence artifact added
[x] ADR 0051 added
[x] Gate 13.5 lab added
[x] ADR 0051 indexed
[x] draft PR #193 opened
[ ] exact-head MCP CI PASS
[ ] PR scope/review threads clean
[ ] protected squash merge
[ ] final Phase 13 state synchronization
[ ] issue #192 CLOSED / COMPLETED after final state synchronization
```

## Next phase boundary

After Gate 13.5 merge and final state synchronization:

```text
Phase 14 — Amazon Bedrock AgentCore
```

Phase 14 must start by evaluating AgentCore against a concrete OpsLens runtime need. It does not inherit authorization to deploy the Phase 13 offline MCP proof unchanged as a public runtime.
