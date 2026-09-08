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
  Gate 12.3 First real two-model comparison     NEXT
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

No public/deployed agent runtime, AgentCore runtime, MCP, A2A, or runtime-exposure authority is claimed by Phase 12 Gate 12.2.

## Phase 12 architecture records

- [`adr/0042-bounded-multi-agent-specialization-handoff.md`](adr/0042-bounded-multi-agent-specialization-handoff.md) — freeze a deterministic one-way specialization handoff before any second reasoning model exists.
- [`adr/0043-freeze-multi-agent-comparison-before-second-model-call.md`](adr/0043-freeze-multi-agent-comparison-before-second-model-call.md) — freeze deterministic comparison criteria and exact Phase 11 evidence binding before the first real two-model experiment.

Frozen Phase 12 contracts:

```text
multi-agent-handoff:v1
multi-agent-comparison:v1
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

Handoff authority:

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

Hard Gate 12.1 bounds:

```text
maximum handoffs per task:       1
maximum specialist capabilities: 2
real model calls:                0
capability executions:           0
```

Gate 12.1 exact merge reference:

```text
issue:                  #165
PR:                     #166
final head:             567cdbde81f058d9545328ca78b718c24d79c9fb
Multi-Agent CI:         34172909750 / run #3 / PASS
pytest:                 10 passed in 0.39s
Single-Agent CI:        34172909748 / run #48 / PASS
single-agent pytest:    56 passed in 0.44s
merge SHA:              eceed76a6cfc5d7e28e88dfdc503b4863b526ba0
```

### Gate 12.2 comparison contract

Gate 12.2 evaluates the frozen handoff boundary with synthetic, explicitly untrusted proposals before any second real model invocation exists:

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

Exact Phase 11 reference binding:

```text
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Frozen Gate 12.2 identities and conformance evidence:

```text
dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
report_sha256:  0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
total / passed: 6 / 6
handoff / abstention: 4 / 2
source capability slots for handoffs: 16
specialist capability slots: 8
capability slots removed: 8
offline capability executions: 0
```

The `6/6` result is synthetic evaluator/contract conformance. It is not triage-model quality, specialist-model quality, or a real multi-agent baseline.

Because no model is invoked, the report deliberately keeps these values `null` rather than manufacturing runtime zeros:

```text
model invocation count
input/output/total tokens
provider/client latency
SDK retries
inference cost
```

Gate 12.2 exact merge reference:

```text
issue:                  #168
PR:                     #169
final head:             953467df99ddeaedd6e19471bd2dce6c5bb8de7c
PR merge test commit:   bab183ee1dbcca0eb6a0bb76b5130180f9f2f7c2
Multi-Agent CI:         34174680219 / run #7 / PASS
pytest:                 18 passed in 0.27s
merge SHA:              865ba70c813711cb88da9ac7308c8966ff983fd0
```

### Phase 12 laboratories

- [`../labs/phase-12-gate-12-1-bounded-specialization-handoff.md`](../labs/phase-12-gate-12-1-bounded-specialization-handoff.md)
- [`../labs/phase-12-gate-12-2-comparative-multi-agent-evaluation.md`](../labs/phase-12-gate-12-2-comparative-multi-agent-evaluation.md)

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

Gate 11.5 remains:

```text
NO-CHANGE / NO-EXPERIMENT
```

### Phase 11 laboratories

- [`../labs/phase-11-gate-11-1-single-agent-authority-contract.md`](../labs/phase-11-gate-11-1-single-agent-authority-contract.md)
- [`../labs/phase-11-gate-11-2-typed-capability-bindings-offline-executor.md`](../labs/phase-11-gate-11-2-typed-capability-bindings-offline-executor.md)
- [`../labs/phase-11-gate-11-3-offline-agent-evaluation.md`](../labs/phase-11-gate-11-3-offline-agent-evaluation.md)
- [`../labs/phase-11-gate-11-4-bounded-model-reasoning-baseline.md`](../labs/phase-11-gate-11-4-bounded-model-reasoning-baseline.md)
- [`../labs/phase-11-gate-11-5-measured-optimization-decision.md`](../labs/phase-11-gate-11-5-measured-optimization-decision.md)
- [`../labs/phase-11-gate-11-6-closeout.md`](../labs/phase-11-gate-11-6-closeout.md)

## Earlier architecture records

### Phase 10

- [`adr/0032-content-minimized-operational-telemetry-contract.md`](adr/0032-content-minimized-operational-telemetry-contract.md)
- [`adr/0033-governed-operational-orchestration-instrumentation.md`](adr/0033-governed-operational-orchestration-instrumentation.md)
- [`adr/0034-bounded-cloudwatch-emf-telemetry-adapter.md`](adr/0034-bounded-cloudwatch-emf-telemetry-adapter.md)
- [`adr/0035-phase10-observability-closeout.md`](adr/0035-phase10-observability-closeout.md)

### Phase 9

- [`adr/0029-public-repository-request-admission.md`](adr/0029-public-repository-request-admission.md)
- [`adr/0030-public-semantic-planning-authority.md`](adr/0030-public-semantic-planning-authority.md)
- [`adr/0031-phase9-public-analysis-closeout.md`](adr/0031-phase9-public-analysis-closeout.md)

### Phase 8

- [`adr/0025-deterministic-hybrid-routing-authority.md`](adr/0025-deterministic-hybrid-routing-authority.md)
- [`adr/0026-deterministic-hybrid-evidence-envelope.md`](adr/0026-deterministic-hybrid-evidence-envelope.md)
- [`adr/0027-frozen-hybrid-evaluation-contract.md`](adr/0027-frozen-hybrid-evaluation-contract.md)
- [`adr/0028-bounded-route-aware-hybrid-synthesis.md`](adr/0028-bounded-route-aware-hybrid-synthesis.md)

### Phase 7

- [`adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md`](adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md)
- [`adr/0023-bounded-bedrock-knowledge-synthesis.md`](adr/0023-bounded-bedrock-knowledge-synthesis.md)
- [`adr/0024-phase7-runtime-iam-boundary.md`](adr/0024-phase7-runtime-iam-boundary.md)

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
Phase 12 — Gate 12.3: First Bounded Real Two-Model Comparison
```

Gate 12.3 may now add at most two bounded model reasoning calls per task: a triage call that proposes one closed specialization, followed by deterministic handoff admission and a specialist reasoning call that proposes one already-permitted capability. Deterministic capability authorization remains mandatory and the first experiment stops before capability execution.

Initial bounds are two model invocations, one handoff, zero adaptive application retries, zero fallbacks, and zero capability executions. Real tokens, latency, SDK retries, and cost must come only from observed provider evidence. The first real observations must be preserved before any prompt/model/topology tuning.

A two-model topology is retained only if measured specialization value justifies the added model call, latency, token usage, cost, failure surface, and architectural complexity relative to the frozen Phase 11 reference.

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
