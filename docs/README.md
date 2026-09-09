# OpsLens Documentation

OpsLens documentation is organized around current architecture, implementation state, incremental roadmap, ADRs, gate laboratories, and immutable evaluation/runtime evidence.

## Primary documents

- [`architecture.md`](architecture.md) — accumulated architecture baseline.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture baseline.
- [`current-state.md`](current-state.md) — authoritative implementation checkpoint.
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
Phase 14 Amazon Bedrock AgentCore               COMPLETE
Phase 15 A2A                                    COMPLETE
  Gate 15.1 capability fit / authority          COMPLETE / GO OFFLINE ONLY
  Gate 15.1 protocol-baseline correction        COMPLETE / A2A 1.0.0
  Gate 15.2 reference-only offline adapter      COMPLETE / MEASURED
  Gate 15.3 official SDK conformance            COMPLETE / PASS
  Gate 15.4 retention / closeout                COMPLETE / RETAIN BOUNDED OFFLINE
Phase 16 Runtime Exposure with Inspector        NEXT / PLANNED
Phase 17 Security Hardening                     PLANNED
Phase 18 Evaluation, Cost & Portfolio           PLANNED
```

## Permanent authority separations

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
MCP tool name != capability authorization
MCP call admission != capability execution
MCP result projection != public runtime exposure
AgentCore hosting != business authorization
runtime authentication != capability authorization
runtime deployment != runtime-exposure truth
A2A message != capability authorization
A2A peer identity != business authority
A2A AgentCard skill != OpsLens capability authorization
A2A task state != business/evidence truth
A2A transport success != business/evidence truth
A2A artifact != admitted OpsLens evidence
A2A authentication != capability authorization
A2A protocol binding != business authority
A2A generated id != OpsLens content identity
A2A SDK acceptance != OpsLens admission authority
Repository Risk != Runtime Exposure
```

## Retained measured reasoning reference

Phase 11 remains the default/reference reasoning architecture:

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

Reference:

- [`../labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json`](../labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json)

## Phase 13 — MCP — complete

MCP is retained as a bounded offline interoperability boundary over existing typed capability authority. It does not create capability authorization or a public runtime.

References:

- [`adr/0047-bounded-mcp-capability-exposure.md`](adr/0047-bounded-mcp-capability-exposure.md)
- [`adr/0048-bounded-offline-mcp-protocol-adapter.md`](adr/0048-bounded-offline-mcp-protocol-adapter.md)
- [`adr/0049-bounded-mcp-capability-execution-bridge.md`](adr/0049-bounded-mcp-capability-execution-bridge.md)
- [`adr/0050-bounded-mcp-structured-result-projection.md`](adr/0050-bounded-mcp-structured-result-projection.md)
- [`adr/0051-phase13-mcp-closeout.md`](adr/0051-phase13-mcp-closeout.md)

## Phase 14 — AgentCore — complete

Phase 14 measured a bounded HTTP/SigV4 Runtime experiment, rejected AgentCore as the default reasoning runtime, retained it as an optional lab target, and removed standing experiment-specific GitHub IAM.

Final state:

```text
Phase 11 direct Bedrock reasoning:          RETAIN / DEFAULT
AgentCore implementation/evidence:          RETAIN AS OPTIONAL LAB TARGET
AgentCore managed Runtime as default:        DO NOT RETAIN
standing AgentCore Runtime resources:        NONE
standing experiment-specific GitHub IAM:    REMOVED
Gate 14.2 PUBLIC exception:                  NOT RETAINED
```

References:

- [`adr/0052-agentcore-runtime-capability-fit.md`](adr/0052-agentcore-runtime-capability-fit.md)
- [`adr/0053-bounded-agentcore-direct-code-public-network-experiment.md`](adr/0053-bounded-agentcore-direct-code-public-network-experiment.md)
- [`adr/0054-retain-agentcore-only-as-optional-lab-target.md`](adr/0054-retain-agentcore-only-as-optional-lab-target.md)
- [`adr/0055-remove-standing-agentcore-experiment-iam.md`](adr/0055-remove-standing-agentcore-experiment-iam.md)

## Phase 15 — A2A — complete

### Gate 15.1 — capability fit

```text
A2A protocol:                  1.0.0
standard bindings:             JSONRPC / GRPC / HTTP+JSON
first OpsLens binding choice:  JSONRPC
retained independent peer:     NO
network A2A required today:    NO
decision:                      GO OFFLINE ONLY
```

### Gate 15.2 — bounded offline adapter

Retained contract:

```text
a2a-reference-interoperability:v1
```

Measured result:

```text
Agent Card bytes:          582
protocol requests:         2
request bytes total:       1308
response bytes total:      989
client elapsed sum:        0.353039 ms
handler elapsed sum:       0.239397 ms
retries:                   0
model invocations:         0
capability executions:     0
AWS/IAM changes:           0
incremental AWS cost:      USD 0.00
```

### Gate 15.3 — official SDK conformance

```text
a2a-sdk:                       1.1.4
source commit:                 2d4d3048b245d2af854bad804f0e722ea9febc08
AgentCard semantic conformance: PASS
SendMessage request:           PASS
JSON-RPC construction:         PASS
Message response:              PASS
Task response:                 PASS
project/runtime dependency:    0
protocol network requests:     0
```

The official SDK is retained only as an exact-source CI conformance oracle. OpsLens raw validation, content identity, replay checks, and result admission remain authoritative.

### Final Phase 15 retention

```text
content-addressed A2AReference:                 RETAIN
strict raw JSON admission:                      RETAIN
A2A 1.0 JSONRPC SendMessage profile:            RETAIN
Message / terminal Task metadata admission:     RETAIN
A2A fixtures / CI:                              RETAIN
official exact-source SDK oracle:               RETAIN FOR CI
public/network A2A runtime:                      DO NOT CREATE
standing A2A cloud resources / IAM:             NONE
A2A capability/business-result authority:        DO NOT CREATE
a2a-sdk project/runtime dependency:              DO NOT ADD
```

Canonical records:

- [`adr/0056-bounded-a2a-capability-fit.md`](adr/0056-bounded-a2a-capability-fit.md)
- [`adr/0057-bounded-offline-a2a-reference-adapter.md`](adr/0057-bounded-offline-a2a-reference-adapter.md)
- [`adr/0058-official-a2a-sdk-as-ci-conformance-oracle.md`](adr/0058-official-a2a-sdk-as-ci-conformance-oracle.md)
- [`adr/0059-phase15-a2a-closeout.md`](adr/0059-phase15-a2a-closeout.md)
- [`../labs/phase-15-closeout.md`](../labs/phase-15-closeout.md)
- [`../labs/evidence/phase-15-closeout-v1.json`](../labs/evidence/phase-15-closeout-v1.json)

## Next planned phase

Phase 16 — Runtime Exposure with Amazon Inspector — is next in the existing roadmap. It must start with its own evidence/authority gate and preserve:

> **Repository Risk != Runtime Exposure.**

Phase 15 does not authorize Phase 16 AWS changes by itself.
