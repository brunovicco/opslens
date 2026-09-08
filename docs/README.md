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
  Gate 12.4 Measured retention decision         COMPLETE / MERGED
  Gate 12.5 Multi-agent phase closeout          NEXT
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

No public/deployed agent runtime, AgentCore runtime, MCP, A2A, or runtime-exposure authority is claimed by Phase 12.

## Phase 12 architecture records

- [`adr/0042-bounded-multi-agent-specialization-handoff.md`](adr/0042-bounded-multi-agent-specialization-handoff.md) — freeze deterministic bounded specialization/handoff authority.
- [`adr/0043-freeze-multi-agent-comparison-before-second-model-call.md`](adr/0043-freeze-multi-agent-comparison-before-second-model-call.md) — freeze comparative metrics before adding the second model call.
- [`adr/0044-first-bounded-real-two-model-comparison.md`](adr/0044-first-bounded-real-two-model-comparison.md) — run the first bounded real triage-to-specialist experiment without moving authority into models.
- [`adr/0045-do-not-retain-two-model-topology-without-measured-lift.md`](adr/0045-do-not-retain-two-model-topology-without-measured-lift.md) — retain the simpler measured reference when the two-model topology adds material overhead without measured lift.

Frozen Phase 12 contracts:

```text
multi-agent-handoff:v1
multi-agent-comparison:v1
multi-agent-triage-reasoning:v1
multi-agent-two-model-reasoning:v1
multi-agent-real-comparison:v1
```

## Gate 12.1 — deterministic specialization boundary

Code-owned partition:

```text
EVIDENCE_ANALYSIS
 -> public_repository_analysis
 -> structured_security_query

GUIDANCE_SYNTHESIS
 -> hybrid_security_answer
 -> knowledge_guidance
```

The handoff contract can deterministically narrow the reasoning surface from four source capabilities to at most two specialist capabilities. This is reasoning-surface narrowing, not runtime privilege reduction.

Gate 12.1 merged through PR #166 as `eceed76a6cfc5d7e28e88dfdc503b4863b526ba0`.

## Gate 12.2 — frozen comparison contract

```text
Phase 11 corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
Phase 11 report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
Gate 12.2 dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
Gate 12.2 report_sha256: 0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
```

The synthetic `6/6` result is evaluator/contract conformance, not model quality.

Gate 12.2 merged through PR #169 as `865ba70c813711cb88da9ac7308c8966ff983fd0`.

## Gate 12.3 — first authenticated two-model experiment

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

Gate 12.3 merged through PR #172 as `f51cb70ad070716e774419b8d2c62918d3e65210`.

## Gate 12.4 — measured retention decision

Decision evidence:

```text
../labs/evidence/phase-12-gate-12-4-retention-decision-v1.json
```

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
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
new rescue/tuning experiment:                   NOT AUTHORIZED WITHOUT NEW HYPOTHESIS
```

Gate 12.4 made no model invocation and incurred no new inference cost.

Exact merge reference:

```text
issue #174:             CLOSED / COMPLETED
PR #175 final head:     c2accab5c7a353f4c2a721cf6912d498e53b76f1
PR merge test commit:   7a57c16f55c4a432874eea2b07bf7a104e75ace2
Multi-Agent CI:         34219145838 / run #33 / PASS
pytest:                 33 passed in 0.34s
merge SHA:              fabe8128d1d6077e8de92225991b5e26c1b72ab3
```

### Phase 12 laboratories

- [`../labs/phase-12-gate-12-1-bounded-specialization-handoff.md`](../labs/phase-12-gate-12-1-bounded-specialization-handoff.md)
- [`../labs/phase-12-gate-12-2-comparative-multi-agent-evaluation.md`](../labs/phase-12-gate-12-2-comparative-multi-agent-evaluation.md)
- [`../labs/phase-12-gate-12-3-first-bounded-real-two-model-comparison.md`](../labs/phase-12-gate-12-3-first-bounded-real-two-model-comparison.md)
- [`../labs/phase-12-gate-12-4-measured-multi-agent-retention-decision.md`](../labs/phase-12-gate-12-4-measured-multi-agent-retention-decision.md)

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

## Next authorized gate

```text
Phase 12 — Gate 12.5: Multi-Agent Phase Closeout
```

Gate 12.5 should close Phase 12 around the measured result: retain the simpler single-agent runtime reference, retain the deterministic specialization/handoff mechanism, preserve the non-retained real two-model experiment historically, and make no claims about capabilities or runtimes that Phase 12 did not prove.

AgentCore, MCP, and A2A remain separate future decisions. Deferred PR #89 remains out-of-scope cross-project integration work.

## Documentation update rule

Every material gate should leave behind architecture rationale, implementation/evaluation evidence, IAM/trust impact, cost reasoning, CI evidence, and the next authorized action. Historical detail stays in labs and ADRs rather than being rewritten into a more favorable story after later measurements.
