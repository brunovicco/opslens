# OpsLens Documentation

OpsLens documentation is organized around current architecture, implementation state, incremental roadmap, ADRs, gate laboratories, and immutable evaluation/runtime evidence.

## Primary documents

- [`architecture.md`](architecture.md) — accumulated architecture baseline; later phases are additionally frozen through ADRs and gate labs.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture baseline synchronized with the English version.
- [`current-state.md`](current-state.md) — exact implementation checkpoint and next authorized action.
- [`roadmap.md`](roadmap.md) — incremental phase/gate plan and completion status.
- [`adr/`](adr/) — accepted architecture decisions.
- [`../labs/`](../labs/) — gate laboratories and immutable evidence references.

## Current implementation checkpoint

```text
Phase 0  AWS Foundation                         COMPLETE
Phase 1  EPSS Vertical Slice                    COMPLETE
Phase 2  Threat Intelligence Data Lake          COMPLETE
Phase 3  Vulnerability Correlation Engine       COMPLETE
Phase 4  Repository Intelligence                COMPLETE
Phase 5  Risk Prioritization Engine             COMPLETE
Phase 6  Semantic Query Layer                   COMPLETE
Phase 7  Knowledge Retrieval with Bedrock       COMPLETE
Phase 8  Hybrid Retrieval                       COMPLETE
Phase 9  Public Analyze Your Repository         COMPLETE
Phase 10 Observability & Operational Excellence COMPLETE
Phase 11 Single-Agent Baseline                  COMPLETE
Phase 12 Multi-Agent Architecture               COMPLETE
Phase 13 MCP                                    IN PROGRESS
  Gate 13.1 Bounded MCP capability exposure     COMPLETE / MERGED
  Gate 13.2 Bounded MCP protocol adapter         NEXT
```

Permanent separations include:

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
structured model output != trusted proposal
synthetic fixture conformance != model quality
MCP tool name != capability authorization
MCP tool exposure != executable argument authority
MCP call admission != capability execution
MCP transport success != business/evidence truth
Repository Risk != Runtime Exposure
```

## Retained reasoning reference

Phase 11 remains the default/reference measured reasoning architecture:

```text
quality:                    6/6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
SDK retries:                0
capability executions:      0
derived six-case cost:      USD 0.0041921
```

Historical evidence:

```text
../labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
```

## Phase 12 closeout

Phase 12 retained the Gate 12.1 deterministic specialization/handoff mechanism and Gate 12.2 comparison discipline, but did not retain the Gate 12.3 two-model topology as the default reasoning path.

Measured Phase 11 versus Gate 12.3 result:

```text
quality:                    6/6 -> 6/6      no lift
model invocations:          6 -> 10         +66.67%
total tokens:               3395 -> 5982    +76.20%
provider latency median:    809.5 -> 1694   +109.26%
client elapsed median:      977.5 -> 2135   +118.41%
derived cost:               0.0041921 -> 0.0074338 USD  +77.33%
```

Closeout references:

- [`adr/0042-bounded-multi-agent-specialization-handoff.md`](adr/0042-bounded-multi-agent-specialization-handoff.md)
- [`adr/0043-freeze-multi-agent-comparison-before-second-model-call.md`](adr/0043-freeze-multi-agent-comparison-before-second-model-call.md)
- [`adr/0044-first-bounded-real-two-model-comparison.md`](adr/0044-first-bounded-real-two-model-comparison.md)
- [`adr/0045-do-not-retain-two-model-topology-without-measured-lift.md`](adr/0045-do-not-retain-two-model-topology-without-measured-lift.md)
- [`adr/0046-phase12-multi-agent-closeout.md`](adr/0046-phase12-multi-agent-closeout.md)
- [`../labs/phase-12-gate-12-5-multi-agent-closeout.md`](../labs/phase-12-gate-12-5-multi-agent-closeout.md)

## Phase 13 Gate 13.1 — bounded MCP capability exposure

Architecture record:

- [`adr/0047-bounded-mcp-capability-exposure.md`](adr/0047-bounded-mcp-capability-exposure.md)

Gate lab:

- [`../labs/phase-13-gate-13-1-bounded-mcp-capability-exposure.md`](../labs/phase-13-gate-13-1-bounded-mcp-capability-exposure.md)

Frozen contract:

```text
mcp-capability-exposure:v1
```

Closed MCP tool identities:

```text
opslens.structured_security_query   -> structured_security_query
opslens.knowledge_guidance          -> knowledge_guidance
opslens.hybrid_security_answer      -> hybrid_security_answer
opslens.public_repository_analysis  -> public_repository_analysis
```

Gate 13.1 authority path:

```text
existing AuthorizedAgentAction
 + existing typed AgentCapabilityInvocation
 -> closed McpToolName
 -> deterministic tool/capability match
 -> content-addressed McpToolCallAdmission
 -> STOP
```

The MCP boundary does not create the authorization, does not create the typed invocation, does not execute a capability, and does not gain arbitrary executable argument authority.

Exact Gate 13.1 merge evidence:

```text
issue #180
PR #181 final head:      340f2d7beee3640bd14455de635fe3ee4b6cc5cc
PR merge test commit:    166e5626f52bdbabfd306b0e3152b02c1620ee5f
MCP CI:                  34223369166 / run #3 / PASS
job:                     102051514632
uv lock --check:         PASS
MCP import smoke:        PASS
Ruff:                    PASS
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest MCP slice:        7 passed in 0.19s
review threads:          0
model invocations:       0
capability executions:   0
MCP SDK/runtime:         0
new AWS/IAM:             0
merge SHA:               322922aed4abec3b2266a18d15d8145df974a7d1
```

Gate 13.1 proves the authority contract only. It does not prove real MCP client/server interoperability, authentication, network reliability, capability execution through MCP, result transport, a deployed MCP runtime, AgentCore, A2A, or runtime exposure.

## Permanent engineering boundaries

> **Agents reason. Code verifies evidence.**

> **MCP is an interoperability boundary, not new business authority.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

## Next authorized gate

```text
Phase 13 — Gate 13.2: Bounded MCP Protocol Adapter / Offline Interoperability
```

Gate 13.2 may introduce a real MCP protocol adapter only against the frozen Gate 13.1 contract. Before adding an SDK dependency, the current official MCP Python SDK/API must be verified and the selected dependency pinned deliberately.

The initial protocol path must reference an already-created typed invocation, resolve it deterministically server-side, pass through Gate 13.1 admission, and stop before capability execution. The first interoperability proof should remain offline/in-process or stdio rather than a public network deployment.

AgentCore and A2A remain separate later decisions. Deferred PR #89 remains out-of-scope cross-project integration work.

## Documentation update rule

Every material gate should leave behind architecture rationale, implementation/evaluation evidence, IAM/trust impact, cost reasoning, CI evidence, and the next authorized action. Historical detail stays in labs and ADRs rather than being rewritten into a more favorable story after later measurements.
