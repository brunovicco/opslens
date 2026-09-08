# OpsLens — Incremental Roadmap

_Last updated: 2026-09-08_

OpsLens advances in small, demonstrable, observable, reversible gates.

Default engineering loop:

```text
concept
 -> architecture decision
 -> IAM / trust boundary when applicable
 -> implementation
 -> success test
 -> failure test
 -> observability
 -> cost
 -> documentation / ADR
 -> logical merge
```

## Current roadmap status

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | AWS Foundation | ✅ Complete |
| 1 | EPSS Vertical Slice | ✅ Complete |
| 2 | Threat Intelligence Data Lake | ✅ Complete |
| 3 | Vulnerability Correlation Engine | ✅ Complete |
| 4 | Repository Intelligence | ✅ Complete |
| 5 | Risk Prioritization Engine | ✅ Complete |
| 6 | Semantic Query Layer | ✅ Complete |
| 7 | Knowledge Retrieval with Bedrock | ✅ Complete |
| 8 | Hybrid Retrieval | ✅ Complete |
| 9 | Public Analyze Your Repository | ✅ Complete |
| 10 | Observability & Operational Excellence | ✅ Complete |
| 11 | Single-Agent Baseline | ✅ Complete |
| 12 | Multi-Agent Architecture | 🚧 In progress — Gate 12.5 closeout next |
| 13 | MCP | ⏳ Planned |
| 14 | Amazon Bedrock AgentCore | ⏳ Planned |
| 15 | A2A | ⏳ Planned |
| 16 | Runtime Exposure with Amazon Inspector | ⏳ Planned |
| 17 | Security Hardening | ⏳ Planned |
| 18 | Evaluation, Cost & Portfolio Readiness | ⏳ Planned |

## Permanent engineering boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

Agentic phases preserve:

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
structured model output != trusted proposal
synthetic fixture conformance != model quality
model selection != capability authority
```

## Completed foundation — Phases 0–10

Phases 0–10 are complete. Their detailed architecture and evidence remain in phase ADRs, labs, state documents, and Git history.

## Phase 11 — Single-Agent Baseline — COMPLETE

Completed sequence:

```text
Gate 11.1 — Capability Authorization Contract                  COMPLETE / MERGED
Gate 11.2 — Typed Capability Bindings + Offline Executor       COMPLETE / MERGED
Gate 11.3 — Frozen Single-Agent Evaluation Fixture             COMPLETE / MERGED
Gate 11.4 — First Bounded Model Reasoning Baseline             COMPLETE / MERGED
Gate 11.5 — Measured Optimization Decision                     COMPLETE / MERGED — NO-CHANGE
Gate 11.6 — Phase 11 Closeout                                  COMPLETE / MERGED
```

Retained real reference:

```text
quality:                    6/6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
SDK retries:                0
capability executions:      0
derived inference cost:     USD 0.0041921
corpus_sha256:              3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256:              724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

## Phase 12 — Multi-Agent Architecture — IN PROGRESS

Phase 12 is evidence-driven. Adding agents is never itself a success criterion.

### Gate 12.1 — Bounded Specialization Handoff Contract — COMPLETE / MERGED

Frozen code-owned partition:

```text
EVIDENCE_ANALYSIS
 -> public_repository_analysis
 -> structured_security_query

GUIDANCE_SYNTHESIS
 -> hybrid_security_answer
 -> knowledge_guidance
```

The deterministic handoff boundary narrows a source task's reasoning surface to at most two specialist capabilities without giving a model handoff-admission or execution authority.

```text
PR #166
merge SHA: eceed76a6cfc5d7e28e88dfdc503b4863b526ba0
ADR: docs/adr/0042-bounded-multi-agent-specialization-handoff.md
```

### Gate 12.2 — Comparative Multi-Agent Evaluation Contract — COMPLETE / MERGED

Gate 12.2 froze comparison criteria before a second model call existed.

```text
dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
report_sha256:  0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
synthetic conformance: 6/6
```

Synthetic fixture conformance is not model quality.

```text
PR #169
merge SHA: 865ba70c813711cb88da9ac7308c8966ff983fd0
ADR: docs/adr/0043-freeze-multi-agent-comparison-before-second-model-call.md
```

### Gate 12.3 — First Bounded Real Two-Model Comparison — COMPLETE / MERGED

The first authenticated bounded two-model experiment preserved deterministic authority and achieved the frozen quality target:

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

Historical evidence:

```text
labs/evidence/phase-12-gate-12-3-first-real-two-model-comparison-v1.json
dataset_sha256: 0439ebaa6215b2de7eaa82624188576743b5a50cc847137e04dc97ee7a199be7
report_sha256:  45edf58ac911ec14e872a00464dad5d5311d82165d6b8ac4321da4a0dc5ad09b
```

```text
PR #172
merge SHA: f51cb70ad070716e774419b8d2c62918d3e65210
ADR: docs/adr/0044-first-bounded-real-two-model-comparison.md
```

### Gate 12.4 — Measured Multi-Agent Retention Decision — COMPLETE / MERGED

Gate 12.4 ran no new model experiment. It compared the frozen Phase 11 reference with Gate 12.3 and made the retention decision before any rescue tuning.

Measured deltas:

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

Decision evidence:

```text
labs/evidence/phase-12-gate-12-4-retention-decision-v1.json
```

Exact merge evidence:

```text
issue #174:             CLOSED / COMPLETED
PR #175 final head:     c2accab5c7a353f4c2a721cf6912d498e53b76f1
PR merge test commit:   7a57c16f55c4a432874eea2b07bf7a104e75ace2
Multi-Agent CI:         34219145838 / run #33 / PASS
job:                    102037888575
pytest:                 33 passed in 0.34s
new model calls:        0
new inference cost:     USD 0.00
merge SHA:              fabe8128d1d6077e8de92225991b5e26c1b72ab3
```

Architecture record:

```text
docs/adr/0045-do-not-retain-two-model-topology-without-measured-lift.md
```

### Gate 12.5 — Multi-Agent Phase Closeout — NEXT

Gate 12.5 should close Phase 12 without inventing additional runtime capability.

Required closeout conclusion:

```text
retained runtime reasoning reference: Phase 11 single-agent
retained Phase 12 mechanism:          deterministic specialization/handoff
non-retained default topology:        Gate 12.3 two-model triage + specialist
historical experiment evidence:       preserved
```

Closeout must explicitly state what Phase 12 did **not** prove:

```text
capability execution through multi-agent flow
public/deployed agent runtime
production SLOs
AgentCore runtime behavior
MCP interoperability
A2A interoperability
runtime exposure / Amazon Inspector evidence
universal multi-agent superiority
```

No new model experiment is required for closeout.

### Phase 12 continuation rules

```text
1. deterministic authority stays code-owned
2. specialization is a bounded authority mechanism, not a reason to add model calls
3. experiment success is not architecture-retention success
4. historical non-retained experiments remain preserved
5. new model experiments require a predeclared falsifiable benefit hypothesis
6. generic executable tool surfaces remain prohibited
7. AgentCore, MCP, and A2A remain separate decisions
8. Repository Risk != Runtime Exposure remains frozen
9. PR #89 remains deferred cross-project work
```

## Phase 13 — MCP — PLANNED

Expose bounded internal capabilities through explicit MCP contracts only after Phase 12 closes stable agent authority boundaries.

## Phase 14 — Amazon Bedrock AgentCore — PLANNED

Evaluate managed runtime capabilities against measured OpsLens needs rather than adopting them for certification coverage alone.

## Phase 15 — A2A — PLANNED

Add agent-to-agent interoperability only after stable boundaries exist and a concrete interoperability need is demonstrated.

## Phase 16 — Runtime Exposure with Amazon Inspector — PLANNED

Add independent runtime evidence without conflating repository risk with runtime exposure.

## Phase 17 — Security Hardening — PLANNED

Perform cross-cutting IAM, data protection, abuse, threat-model, dependency, and operational hardening.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 remains deferred consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and must be re-evaluated against the current architecture before any integration merge.
