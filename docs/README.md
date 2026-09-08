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
Phase 12 Multi-Agent Architecture               NEXT
```

The project still preserves:

```text
application boundary validated != public runtime deployed
telemetry evidence != business truth
EMF document created != CloudWatch ingestion proven
agent action proposal != capability authorization
AuthorizedAgentAction != capability invocation
structured model output != trusted proposal
Repository Risk != Runtime Exposure
```

No public/deployed agent runtime, AgentCore runtime, MCP, A2A, or runtime-exposure authority is claimed by the Phase 11 closeout.

## Phase 11 architecture records

- [`adr/0036-bounded-single-agent-capability-authorization.md`](adr/0036-bounded-single-agent-capability-authorization.md) — separate agent proposal from deterministic capability authorization.
- [`adr/0037-typed-single-agent-capability-execution.md`](adr/0037-typed-single-agent-capability-execution.md) — bind authorized actions to exact typed invocation and result admission.
- [`adr/0038-offline-single-agent-evaluation-before-runtime.md`](adr/0038-offline-single-agent-evaluation-before-runtime.md) — freeze deterministic evaluation before real model reasoning.
- [`adr/0039-bounded-single-agent-model-reasoning.md`](adr/0039-bounded-single-agent-model-reasoning.md) — add one bounded provider-neutral reasoning step behind deterministic authorization.
- [`adr/0040-preserve-measured-reasoning-baseline-without-premature-optimization.md`](adr/0040-preserve-measured-reasoning-baseline-without-premature-optimization.md) — preserve the measured baseline when no material optimization target exists.
- [`adr/0041-phase11-single-agent-baseline-closeout.md`](adr/0041-phase11-single-agent-baseline-closeout.md) — close Phase 11 at the bounded single-agent reference before multi-agent complexity.

Frozen Phase 11 contracts:

```text
single-agent-authority:v1
single-agent-execution:v1
single-agent-evaluation:v1
single-agent-reasoning:v1
single-agent-reasoning-evaluation:v1
```

Permanent reasoning boundary:

```text
SingleAgentTask
 -> code-owned AgentCapability allowlist
 -> one bounded model reasoning invocation
 -> transient untrusted {decision, capability}
 -> deterministic parser
 -> AgentActionProposal
 -> deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
```

The real Gate 11.4 quality baseline deliberately stops before capability execution. Gate 11.2 remains the independent typed execution/result-admission authority.

### Real reasoning baseline

Preserved evidence:

```text
../labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Measured result:

```text
proposal quality:             6/6
bounds compliance:            6/6
SDK retries:                  0
capability executions:        0
input/output/total tokens:    3291 / 104 / 3395
provider latency median:      809.5 ms
client elapsed median:        977.5 ms
derived six-case cost:        USD 0.0041921
```

Gate 11.5 then merged an evidence-driven:

```text
NO-CHANGE / NO-EXPERIMENT
```

No prompt/model/cache/retry/fallback/capability change was justified by a material measured target.

### Phase 11 laboratories

- [`../labs/phase-11-gate-11-1-single-agent-authority-contract.md`](../labs/phase-11-gate-11-1-single-agent-authority-contract.md)
- [`../labs/phase-11-gate-11-2-typed-capability-bindings-offline-executor.md`](../labs/phase-11-gate-11-2-typed-capability-bindings-offline-executor.md)
- [`../labs/phase-11-gate-11-3-offline-agent-evaluation.md`](../labs/phase-11-gate-11-3-offline-agent-evaluation.md)
- [`../labs/phase-11-gate-11-4-bounded-model-reasoning-baseline.md`](../labs/phase-11-gate-11-4-bounded-model-reasoning-baseline.md)
- [`../labs/phase-11-gate-11-5-measured-optimization-decision.md`](../labs/phase-11-gate-11-5-measured-optimization-decision.md)
- [`../labs/phase-11-gate-11-6-closeout.md`](../labs/phase-11-gate-11-6-closeout.md)

## Phase 10 architecture records

- [`adr/0032-content-minimized-operational-telemetry-contract.md`](adr/0032-content-minimized-operational-telemetry-contract.md)
- [`adr/0033-governed-operational-orchestration-instrumentation.md`](adr/0033-governed-operational-orchestration-instrumentation.md)
- [`adr/0034-bounded-cloudwatch-emf-telemetry-adapter.md`](adr/0034-bounded-cloudwatch-emf-telemetry-adapter.md)
- [`adr/0035-phase10-observability-closeout.md`](adr/0035-phase10-observability-closeout.md)

Frozen Phase 10 contracts:

```text
operational-telemetry:v1
cloudwatch-emf:v1
```

Phase 10 proves deterministic operational evidence and an AWS-native EMF representation boundary, not public runtime or CloudWatch ingestion.

## Phase 9 architecture records

- [`adr/0029-public-repository-request-admission.md`](adr/0029-public-repository-request-admission.md)
- [`adr/0030-public-semantic-planning-authority.md`](adr/0030-public-semantic-planning-authority.md)
- [`adr/0031-phase9-public-analysis-closeout.md`](adr/0031-phase9-public-analysis-closeout.md)

Frozen Phase 9 contracts:

```text
public-analysis-request:v1
public-repository-evidence:v1
public-semantic-planning:v1
public-analysis-handoff:v1
```

## Phase 8 architecture records

- [`adr/0025-deterministic-hybrid-routing-authority.md`](adr/0025-deterministic-hybrid-routing-authority.md)
- [`adr/0026-deterministic-hybrid-evidence-envelope.md`](adr/0026-deterministic-hybrid-evidence-envelope.md)
- [`adr/0027-frozen-hybrid-evaluation-contract.md`](adr/0027-frozen-hybrid-evaluation-contract.md)
- [`adr/0028-bounded-route-aware-hybrid-synthesis.md`](adr/0028-bounded-route-aware-hybrid-synthesis.md)

Frozen hybrid dataset:

```text
hybrid-evaluation-golden:v1
sha256: 68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

## Phase 7 architecture records

- [`adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md`](adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md)
- [`adr/0023-bounded-bedrock-knowledge-synthesis.md`](adr/0023-bounded-bedrock-knowledge-synthesis.md)
- [`adr/0024-phase7-runtime-iam-boundary.md`](adr/0024-phase7-runtime-iam-boundary.md)

Detailed Phase 7 evidence remains in `../labs/phase-7-gate-7-*` and is not rewritten by later closeouts.

## Permanent engineering boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

## Next authorized phase

```text
Phase 12 — Multi-Agent Architecture
```

Phase 12 must start from a concrete bounded specialization hypothesis. Multi-agent complexity is retained only if comparative evaluation demonstrates material value over the frozen Phase 11 single-agent reference.

Required entry properties:

```text
bounded responsibility per specialization
explicit handoff identity and stopping semantics
fail-closed handoff/result admission
no generic arbitrary tool authority
comparative evaluation against Phase 11
AgentCore/MCP/A2A remain separate future decisions
```

PR #89 remains deferred cross-project integration work and is not made mergeable by Phase 11 closeout.

## Documentation update rule

Every material gate should leave behind:

```text
architecture decision / rationale
implementation evidence
success evidence
failure evidence
IAM / trust boundary
observability evidence
cost reasoning
CI evidence
next authorized gate/phase
```

Top-level documents describe the current baseline. Historical detail stays in labs and ADRs so stale gate status does not leak into the project overview.
