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
Phase 14 Amazon Bedrock AgentCore               IN PROGRESS
  Gate 14.1 Runtime capability-fit              COMPLETE / MERGED
  Gate 14.2 bounded HTTP/SigV4 runtime          COMPLETE / MEASURED
  Gate 14.3 Runtime retention decision          COMPLETE / RETAIN WITH CHANGES
  next      standing experiment-IAM cleanup     PENDING SEPARATE ISSUE
Phase 15 A2A                                    PLANNED
```

Permanent separations include:

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
MCP tool name != capability authorization
MCP call admission != capability execution
MCP capability execution != business-result transport
MCP result projection != public runtime exposure
AgentCore hosting != business authorization
runtime authentication != capability authorization
runtime execution role != model/tool authority
runtime telemetry != business truth
runtime deployment != runtime-exposure truth
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

Phase 12 retained deterministic specialization/handoff and comparison discipline, but did not retain the measured two-model topology as the default reasoning path because it produced no quality lift and increased invocation count, tokens, latency, and cost.

References:

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

References:

- [`adr/0047-bounded-mcp-capability-exposure.md`](adr/0047-bounded-mcp-capability-exposure.md)
- [`adr/0048-bounded-offline-mcp-protocol-adapter.md`](adr/0048-bounded-offline-mcp-protocol-adapter.md)
- [`adr/0049-bounded-mcp-capability-execution-bridge.md`](adr/0049-bounded-mcp-capability-execution-bridge.md)
- [`adr/0050-bounded-mcp-structured-result-projection.md`](adr/0050-bounded-mcp-structured-result-projection.md)
- [`adr/0051-phase13-mcp-closeout.md`](adr/0051-phase13-mcp-closeout.md)
- [`../labs/phase-13-gate-13-5-mcp-closeout.md`](../labs/phase-13-gate-13-5-mcp-closeout.md)
- [`../labs/evidence/phase-13-closeout-v1.json`](../labs/evidence/phase-13-closeout-v1.json)

## Phase 14 — AgentCore measured checkpoint

### Gate 14.1 — capability fit

Gate 14.1 authorized one bounded runtime experiment only; it did not pre-approve broad AgentCore adoption.

References:

- [`adr/0052-agentcore-runtime-capability-fit.md`](adr/0052-agentcore-runtime-capability-fit.md)
- [`../labs/phase-14-gate-14-1-agentcore-runtime-capability-fit.md`](../labs/phase-14-gate-14-1-agentcore-runtime-capability-fit.md)

### Gate 14.2 — bounded HTTP/SigV4 runtime experiment

Terminal measured run:

```text
source main:                e5072ec68b421677359cebb1eb449578ef7d5b49
workflow run:               34378942784 / run #11 / SUCCESS
runtime:                    opslens_dev_bounded_runtime-Cl8aNBDGzh
network:                    PUBLIC — dev-only experiment exception
replay:                     6 / 6 PASS
input/output/total tokens:  3291 / 104 / 3395
SDK retries:                0
capability executions:      0
deployment-role invocation: AccessDeniedException / HTTP 403
cleanup:                    RESOURCE_NOT_FOUND
AgentCore Runtime cost:     USD 0.002380345136128484
Bedrock inference cost:     USD 0.0041921
total observed cost:        USD 0.006572445136128483
```

Attempts #1–#10 remain preserved as measured IAM/lifecycle remediation history. Gate 14.2 does not approve AgentCore or PUBLIC networking for production and does not create runtime-exposure truth.

References:

- [`adr/0053-bounded-agentcore-direct-code-public-network-experiment.md`](adr/0053-bounded-agentcore-direct-code-public-network-experiment.md)
- [`../labs/phase-14-gate-14-2-bounded-agentcore-runtime.md`](../labs/phase-14-gate-14-2-bounded-agentcore-runtime.md)
- [`../labs/evidence/phase-14-gate-14-2-final-runtime-experiment-v1.json`](../labs/evidence/phase-14-gate-14-2-final-runtime-experiment-v1.json)

### Gate 14.3 — AgentCore Runtime retention decision

Gate 14.3 records an evidence-backed split decision:

```text
overall decision:                     RETAIN WITH CHANGES
default OpsLens reasoning runtime:    DO NOT RETAIN AgentCore
Phase 11 direct Bedrock reference:    RETAIN
AgentCore implementation/evidence:   RETAIN
AgentCore deployment role:           OPTIONAL LAB / FUTURE CONSUMER TARGET ONLY
PUBLIC network mode:                 DO NOT RETAIN
standing experiment-specific IAM:    CLEANUP REQUIRED
```

The comparable six-case quality, model count, and token evidence is unchanged between Phase 11 and the AgentCore-hosted replay. AgentCore added USD 0.002380345136128484 of measured Runtime cost to the unchanged USD 0.0041921 Bedrock inference component, or 56.78168784448091% incremental runtime cost relative to inference for the experiment.

Raw latency evidence is preserved, but no normalized percentage comparison is claimed because the measurement boundaries are not sufficiently controlled.

References:

- [`adr/0054-retain-agentcore-only-as-optional-lab-target.md`](adr/0054-retain-agentcore-only-as-optional-lab-target.md)
- [`../labs/phase-14-gate-14-3-agentcore-retention-decision.md`](../labs/phase-14-gate-14-3-agentcore-retention-decision.md)
- [`../labs/evidence/phase-14-gate-14-3-agentcore-retention-decision-v1.json`](../labs/evidence/phase-14-gate-14-3-agentcore-retention-decision-v1.json)

## Next authorized action

The Runtime resource itself is already deleted. Gate 14.3 concludes that ambient experiment-only AgentCore deployment/replay IAM is no longer justified without an active experiment.

The next work must be a separate bounded cleanup issue. It should remove standing experiment authority where safe while preserving the disabled-by-default AgentCore lab implementation and historical evidence. The Runtime Identity service-linked role should be removed only if no remaining account dependency requires it.

After that cleanup, Phase 14 can close and Phase 15 A2A may proceed without inheriting AgentCore as a hosting assumption.

PR #89 remains separate cross-project Governed LLM Gateway work and is not part of this decision.

## Documentation update rule

Every material gate should leave behind architecture rationale, implementation/evaluation evidence, IAM/trust impact, cost reasoning, CI evidence, and the next authorized action. Historical detail stays in labs and ADRs rather than being rewritten into a more favorable story after later measurements.
