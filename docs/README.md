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
Phase 13 MCP                                    COMPLETE
  Gate 13.1 Bounded MCP capability exposure     COMPLETE / MERGED
  Gate 13.2 Bounded MCP protocol adapter         COMPLETE / MERGED
  Gate 13.3 Bounded MCP execution bridge         COMPLETE / MERGED
  Gate 13.4 Bounded MCP result projection        COMPLETE / MERGED
  Gate 13.5 MCP phase closeout                   COMPLETE / MERGED
Phase 14 Amazon Bedrock AgentCore               NEXT
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
MCP capability execution != business result transport
MCP result admission != result projection authority
MCP result projection != public runtime exposure
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

## Phase 13 — MCP — complete

Phase 13 demonstrates official MCP interoperability while preserving existing deterministic authority. It closes at a bounded offline/in-process boundary instead of introducing a public runtime without a concrete consumer requirement.

Retained contracts:

```text
mcp-capability-exposure:v1
mcp-capability-execution:v1
mcp-result-projection:v1
```

Retained path:

```text
existing typed Phase 11 capability authority
 -> closed MCP tool identity
 -> official MCP SDK reference-only protocol adapter
 -> raw exact-key-set argument refusal
 -> deterministic invocation resolution + admission
 -> exactly one existing typed executor attempt
 -> content-addressed MCP execution bridge
 -> explicit result projection for structured_security_query only
 -> bounded CVE + EPSS rows
 -> STOP before public/network runtime
```

### Gate 13.1 — capability exposure

Architecture/lab:

- [`adr/0047-bounded-mcp-capability-exposure.md`](adr/0047-bounded-mcp-capability-exposure.md)
- [`../labs/phase-13-gate-13-1-bounded-mcp-capability-exposure.md`](../labs/phase-13-gate-13-1-bounded-mcp-capability-exposure.md)

The closed tool identity remains separate from capability authorization and executable-input authority.

### Gate 13.2 — official SDK offline interoperability

Architecture/lab:

- [`adr/0048-bounded-offline-mcp-protocol-adapter.md`](adr/0048-bounded-offline-mcp-protocol-adapter.md)
- [`../labs/phase-13-gate-13-2-bounded-mcp-protocol-adapter.md`](../labs/phase-13-gate-13-2-bounded-mcp-protocol-adapter.md)

The official MCP Python SDK is pinned as `mcp==2.2.0` in development dependencies only. Real testing showed that raw argument-shape validation must occur before permissive framework coercion. A separate dependency-placement experiment showed that putting MCP in runtime dependencies enlarged unrelated Lambda packages and tripped an existing package-size guard, so deployment limits were not weakened.

### Gate 13.3 — capability execution bridge

Architecture/lab:

- [`adr/0049-bounded-mcp-capability-execution-bridge.md`](adr/0049-bounded-mcp-capability-execution-bridge.md)
- [`../labs/phase-13-gate-13-3-bounded-mcp-capability-execution-bridge.md`](../labs/phase-13-gate-13-3-bounded-mcp-capability-execution-bridge.md)

An accepted MCP invocation reference reaches exactly one existing typed capability-executor attempt after deterministic admission. MCP adds no generic args/kwargs dispatch, adaptive retry, or alternate-capability fallback.

### Gate 13.4 — structured business-result projection

Architecture/lab:

- [`adr/0050-bounded-mcp-structured-result-projection.md`](adr/0050-bounded-mcp-structured-result-projection.md)
- [`../labs/phase-13-gate-13-4-bounded-mcp-structured-result-projection.md`](../labs/phase-13-gate-13-4-bounded-mcp-structured-result-projection.md)

Business-result disclosure is explicit and capability-specific. Only `structured_security_query` transports business rows in Phase 13, mapped to bounded `cve` + `epss_score` fields after existing typed result admission. Knowledge, hybrid, and public-repository result families remain unsupported for business-result transport.

### Gate 13.5 — MCP phase closeout

Architecture/lab/evidence:

- [`adr/0051-phase13-mcp-closeout.md`](adr/0051-phase13-mcp-closeout.md)
- [`../labs/phase-13-gate-13-5-mcp-closeout.md`](../labs/phase-13-gate-13-5-mcp-closeout.md)
- [`../labs/evidence/phase-13-closeout-v1.json`](../labs/evidence/phase-13-closeout-v1.json)

Final closeout merge evidence:

```text
issue #192
PR #193 final head:      99dd3d979a5205e38f2c1a4dfc84dc9f82d0e0c7
PR merge test commit:    7ec68aa12bc0a08b698ed0ddf76434e7bd97fe85
MCP CI:                  34250265151 / run #52 / PASS
job:                     102142600531
uv lock --check:         PASS
MCP SDK pin:             PASS
MCP import smoke:        PASS
Ruff:                    PASS
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest MCP slice:        29 passed in 0.90s
review threads:          0
PR comments:             0
new model invocations:   0
new AWS/IAM:             0
public MCP endpoint:     0
MCP deployed runtime:    0
merge SHA:               c449cfc8e18dfd240ceedbe6e8e4d143601f0254
```

Phase 13 explicitly does not claim a public/Streamable HTTP MCP endpoint, transport authentication/authorization, persistent invocation/result registries, broader result-family serialization, production network SLOs, AgentCore behavior, A2A interoperability, or runtime exposure.

## Permanent engineering boundaries

> **Agents reason. Code verifies evidence.**

> **MCP is an interoperability boundary, not new business authority.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

## Next authorized phase

```text
Phase 14 — Amazon Bedrock AgentCore
```

Phase 14 must begin with a concrete OpsLens runtime/workload need and an evidence-backed evaluation of AgentCore. Managed runtime adoption is not automatic and does not retroactively turn the Phase 13 offline MCP proof into a public runtime.

The first gate must define workload, identity/IAM, failure/retry behavior, observability, lifecycle, cost, and security requirements before provisioning runtime resources. Phase 11 deterministic capability authority, the Phase 12 measured topology decision, and all retained Phase 13 MCP boundaries remain upstream constraints.

Deferred PR #89 remains separate cross-project Governed LLM Gateway work and is not authorized by the OpsLens Phase 14 transition.

## Documentation update rule

Every material gate should leave behind architecture rationale, implementation/evaluation evidence, IAM/trust impact, cost reasoning, CI evidence, and the next authorized action. Historical detail stays in labs and ADRs rather than being rewritten into a more favorable story after later measurements.
