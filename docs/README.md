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
Phase 12 Multi-Agent Architecture               IN PROGRESS
  Gate 12.1 Bounded specialization handoff      COMPLETE / MERGED
  Gate 12.2 Comparative evaluation contract     COMPLETE / MERGED
  Gate 12.3 First real two-model comparison     COMPLETE / MERGED
  Gate 12.4 Measured retention decision         NEXT
```

The project preserves:

```text
application boundary validated != public runtime deployed
telemetry evidence != business truth
EMF document created != CloudWatch ingestion proven
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
AuthorizedAgentAction != capability invocation
structured model output != trusted proposal
synthetic fixture conformance != model quality
Repository Risk != Runtime Exposure
```

No public/deployed agent runtime, AgentCore runtime, MCP, A2A, or runtime-exposure authority is claimed by Phase 12 Gate 12.3.

## Phase 12 architecture records

- [`adr/0042-bounded-multi-agent-specialization-handoff.md`](adr/0042-bounded-multi-agent-specialization-handoff.md) — freeze a deterministic one-way specialization handoff before any second reasoning model exists.
- [`adr/0043-freeze-multi-agent-comparison-before-second-model-call.md`](adr/0043-freeze-multi-agent-comparison-before-second-model-call.md) — freeze deterministic comparison criteria and exact Phase 11 evidence binding before the first real two-model experiment.
- [`adr/0044-first-bounded-real-two-model-comparison.md`](adr/0044-first-bounded-real-two-model-comparison.md) — authorize the first bounded real triage-to-specialist experiment while preserving deterministic handoff and capability authorization.

Frozen Phase 12 contracts now include:

```text
multi-agent-handoff:v1
multi-agent-comparison:v1
multi-agent-triage-reasoning:v1
multi-agent-two-model-reasoning:v1
multi-agent-real-comparison:v1
```

Code-owned specialization partition:

```text
EVIDENCE_ANALYSIS
 -> public_repository_analysis
 -> structured_security_query

GUIDANCE_SYNTHESIS
 -> hybrid_security_answer
 -> knowledge_guidance
```

### Gate 12.1 — bounded handoff

```text
SingleAgentTask
 -> TriageAgentTask
 -> untrusted MultiAgentHandoffProposal
 -> deterministic source-task identity check
 -> code-owned specialization scope
 -> deterministic intersection with source allowed_capabilities
 -> empty intersection? FAIL CLOSED
 -> AuthorizedMultiAgentHandoff | MultiAgentHandoffAbstention
 -> narrowed SpecialistAgentTask
 -> STOP
```

Gate 12.1 merged through PR #166 as `eceed76a6cfc5d7e28e88dfdc503b4863b526ba0`.

### Gate 12.2 — frozen comparison contract

Gate 12.2 evaluates synthetic, explicitly untrusted proposals before a second real model invocation:

```text
frozen comparison fixture
 -> admitted SingleAgentTask
 -> synthetic MultiAgentHandoffProposal
 -> Gate 12.1 deterministic admission
 -> HANDOFF | ABSTAINED | REJECTED
 -> deterministic decomposed scoring
 -> content-addressed report
 -> runtime measurements remain null
 -> STOP
```

Frozen identities:

```text
Phase 11 corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
Phase 11 report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
Gate 12.2 dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
Gate 12.2 report_sha256: 0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
```

The synthetic `6/6` result is evaluator/contract conformance, not model quality.

Gate 12.2 merged through PR #169 as `865ba70c813711cb88da9ac7308c8966ff983fd0`.

### Gate 12.3 — first authenticated two-model comparison

Bounded real path:

```text
SingleAgentTask
 -> one triage model invocation
 -> transient {decision, target_specialization}
 -> deterministic parser
 -> Gate 12.1 deterministic handoff admission
 -> ABSTAIN / rejected? STOP
 -> narrowed SpecialistAgentTask
 -> one specialist reasoning invocation
 -> transient {decision, capability}
 -> deterministic parser
 -> deterministic capability authorization
 -> STOP before capability execution
```

Historical provider evidence is preserved at:

```text
../labs/evidence/phase-12-gate-12-3-first-real-two-model-comparison-v1.json
```

Observed result:

```text
quality:                           6/6
runtime-bounds compliant:          6/6
model invocations:                 10
input/output/total tokens:          5788 / 194 / 5982
provider latency median per task:  1694.0 ms
client elapsed median per task:    2135.0 ms
SDK retries:                       0
capability executions:             0
derived six-case cost:             USD 0.0074338
```

Experiment identities:

```text
dataset_sha256: 0439ebaa6215b2de7eaa82624188576743b5a50cc847137e04dc97ee7a199be7
report_sha256: 45edf58ac911ec14e872a00464dad5d5311d82165d6b8ac4321da4a0dc5ad09b
```

Compared with the frozen Phase 11 single-agent reference, Gate 12.3 retained `6/6` quality but increased model calls by 66.67%, total token use by 76.20%, provider-latency median by 109.26%, client-latency median by 118.41%, and derived inference cost by 77.33%.

This is evidence that the bounded topology is feasible, not evidence that the extra model call should be retained.

Gate 12.3 merged through PR #172 as `f51cb70ad070716e774419b8d2c62918d3e65210` after Multi-Agent CI run `34218039083` passed with strict Pyright and `33 passed` tests.

### Phase 12 laboratories

- [`../labs/phase-12-gate-12-1-bounded-specialization-handoff.md`](../labs/phase-12-gate-12-1-bounded-specialization-handoff.md)
- [`../labs/phase-12-gate-12-2-comparative-multi-agent-evaluation.md`](../labs/phase-12-gate-12-2-comparative-multi-agent-evaluation.md)
- [`../labs/phase-12-gate-12-3-first-bounded-real-two-model-comparison.md`](../labs/phase-12-gate-12-3-first-bounded-real-two-model-comparison.md)

## Phase 11 architecture records

- [`adr/0036-bounded-single-agent-capability-authorization.md`](adr/0036-bounded-single-agent-capability-authorization.md)
- [`adr/0037-typed-single-agent-capability-execution.md`](adr/0037-typed-single-agent-capability-execution.md)
- [`adr/0038-offline-single-agent-evaluation-before-runtime.md`](adr/0038-offline-single-agent-evaluation-before-runtime.md)
- [`adr/0039-bounded-single-agent-model-reasoning.md`](adr/0039-bounded-single-agent-model-reasoning.md)
- [`adr/0040-preserve-measured-reasoning-baseline-without-premature-optimization.md`](adr/0040-preserve-measured-reasoning-baseline-without-premature-optimization.md)
- [`adr/0041-phase11-single-agent-baseline-closeout.md`](adr/0041-phase11-single-agent-baseline-closeout.md)

Frozen Phase 11 reference:

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
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Gate 11.5 remains `NO-CHANGE / NO-EXPERIMENT`.

## Earlier architecture records

Phase 10: ADRs 0032–0035.

Phase 9: ADRs 0029–0031.

Phase 8: ADRs 0025–0028.

Phase 7: ADRs 0022–0024.

Detailed earlier evidence remains in phase-specific labs and is not rewritten by later closeouts.

## Permanent engineering boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

## Next authorized gate

```text
Phase 12 — Gate 12.4: Measured Multi-Agent Retention Decision
```

Gate 12.4 is a decision gate. The frozen Phase 11 single-agent reference and Gate 12.3 real two-model evidence must be compared without assuming that more agents are better.

The default next action is **NO NEW MODEL EXPERIMENT** unless a concrete falsifiable benefit hypothesis exists beyond the already-measured Gate 12.3 dimensions.

A two-model topology is retained only if measured specialization value materially justifies added model calls, latency, token usage, cost, failure surface, and architectural complexity. Current evidence shows equal frozen-corpus quality with material overhead, so the two-model experiment must not silently become the default architecture.

AgentCore, MCP, and A2A remain separate future decisions. PR #89 remains deferred cross-project integration work.

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
