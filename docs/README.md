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
  Gate 12.1 Bounded specialization handoff      COMPLETE / MERGED
  Gate 12.2 Comparative evaluation contract     COMPLETE / MERGED
  Gate 12.3 First real two-model comparison     COMPLETE / MERGED
  Gate 12.4 Measured retention decision         COMPLETE / MERGED
  Gate 12.5 Multi-agent phase closeout          COMPLETE / MERGED
Phase 13 MCP                                    NEXT
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
Repository Risk != Runtime Exposure
```

No public/deployed agent runtime, AgentCore runtime, MCP interoperability, A2A interoperability, or runtime-exposure authority is claimed by Phase 12.

## Phase 12 architecture records

- [`adr/0042-bounded-multi-agent-specialization-handoff.md`](adr/0042-bounded-multi-agent-specialization-handoff.md) — freeze deterministic bounded specialization/handoff authority.
- [`adr/0043-freeze-multi-agent-comparison-before-second-model-call.md`](adr/0043-freeze-multi-agent-comparison-before-second-model-call.md) — freeze comparative metrics before adding the second model call.
- [`adr/0044-first-bounded-real-two-model-comparison.md`](adr/0044-first-bounded-real-two-model-comparison.md) — run the first bounded real triage-to-specialist experiment without moving authority into models.
- [`adr/0045-do-not-retain-two-model-topology-without-measured-lift.md`](adr/0045-do-not-retain-two-model-topology-without-measured-lift.md) — retain the simpler measured reference when the two-model topology adds material overhead without measured lift.
- [`adr/0046-phase12-multi-agent-closeout.md`](adr/0046-phase12-multi-agent-closeout.md) — close Phase 12 around the architecture that survived measurement.

Frozen Phase 12 contracts:

```text
multi-agent-handoff:v1
multi-agent-comparison:v1
multi-agent-triage-reasoning:v1
multi-agent-two-model-reasoning:v1
multi-agent-real-comparison:v1
```

## Retained Phase 12 mechanism

Code-owned specialization partition:

```text
EVIDENCE_ANALYSIS
 -> public_repository_analysis
 -> structured_security_query

GUIDANCE_SYNTHESIS
 -> hybrid_security_answer
 -> knowledge_guidance
```

The Gate 12.1 handoff contract can deterministically narrow the reasoning surface from four source capabilities to at most two specialist capabilities. This is reasoning-surface narrowing, not runtime privilege reduction.

Gate 12.1 merged through PR #166 as `eceed76a6cfc5d7e28e88dfdc503b4863b526ba0`.

## Frozen comparison discipline

Gate 12.2 exact identities:

```text
Phase 11 corpus_sha256:   3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
Phase 11 report_sha256:   724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
Gate 12.2 dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
Gate 12.2 report_sha256:  0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
```

The synthetic `6/6` result is evaluator/contract conformance, not model quality.

## Historical Gate 12.3 real two-model experiment

Historical provider evidence:

```text
../labs/evidence/phase-12-gate-12-3-first-real-two-model-comparison-v1.json
```

Observed result:

```text
quality:                           6/6
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
report_sha256:  45edf58ac911ec14e872a00464dad5d5311d82165d6b8ac4321da4a0dc5ad09b
```

## Frozen Phase 12 retention decision

Measured Phase 11 versus Gate 12.3 comparison:

```text
quality:                    6/6 -> 6/6      no lift
model invocations:          6 -> 10         +66.67%
total tokens:               3395 -> 5982    +76.20%
provider latency median:    809.5 -> 1694   +109.26%
client elapsed median:      977.5 -> 2135   +118.41%
derived cost:               0.0041921 -> 0.0074338 USD  +77.33%
SDK retries:                0 -> 0
capability executions:      0 -> 0
```

Retention decision:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
new rescue/tuning experiment:                   NOT AUTHORIZED WITHOUT NEW HYPOTHESIS
```

Decision evidence:

```text
../labs/evidence/phase-12-gate-12-4-retention-decision-v1.json
```

## Phase 12 closeout

Closeout evidence:

```text
../labs/evidence/phase-12-closeout-v1.json
../labs/phase-12-gate-12-5-multi-agent-closeout.md
```

Exact closeout merge:

```text
issue #177
PR #178 final head:     3d9ad6a6d302299fb8209b40c7232bc18555c2dd
PR merge test commit:   f2de18db9a2b23413be4977e3f4b21a5846ed837
Multi-Agent CI:         34220492021 / run #34 / PASS
job:                    102042205489
Pyright strict:         0 errors / 0 warnings / 0 informations
pytest:                 33 passed in 0.35s
new model calls:        0
new inference cost:     USD 0.00
merge SHA:              aca4264e9c98f81c239b44b55c8772ef02debc4c
```

Phase 12 closes around the measured retained architecture, not around the most complex experiment implemented during the phase.

### Phase 12 laboratories

- [`../labs/phase-12-gate-12-1-bounded-specialization-handoff.md`](../labs/phase-12-gate-12-1-bounded-specialization-handoff.md)
- [`../labs/phase-12-gate-12-2-comparative-multi-agent-evaluation.md`](../labs/phase-12-gate-12-2-comparative-multi-agent-evaluation.md)
- [`../labs/phase-12-gate-12-3-first-bounded-real-two-model-comparison.md`](../labs/phase-12-gate-12-3-first-bounded-real-two-model-comparison.md)
- [`../labs/phase-12-gate-12-4-measured-multi-agent-retention-decision.md`](../labs/phase-12-gate-12-4-measured-multi-agent-retention-decision.md)
- [`../labs/phase-12-gate-12-5-multi-agent-closeout.md`](../labs/phase-12-gate-12-5-multi-agent-closeout.md)

## Retained Phase 11 reference

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

The single-agent path remains the default/reference measured reasoning architecture until a superior topology is demonstrated against a frozen benchmark.

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
Phase 13 — MCP
```

The initial Phase 13 rule is:

> **MCP is an interoperability boundary, not new business authority.**

Phase 13 may expose only already-bounded capabilities and must preserve deterministic authorization, typed invocation/result admission, evidence provenance, fail-closed schema/tool handling, and least privilege.

AgentCore and A2A remain separate later decisions. Deferred PR #89 remains out-of-scope cross-project integration work.

## Documentation update rule

Every material gate should leave behind architecture rationale, implementation/evaluation evidence, IAM/trust impact, cost reasoning, CI evidence, and the next authorized action. Historical detail stays in labs and ADRs rather than being rewritten into a more favorable story after later measurements.
