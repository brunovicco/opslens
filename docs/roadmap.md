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
| 12 | Multi-Agent Architecture | 🚧 In progress |
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

Agentic phases additionally preserve:

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
structured model output != trusted proposal
synthetic fixture conformance != model quality
model selection != capability authority
agent reasoning may select an already-permitted capability
agent reasoning does not acquire deterministic truth or execution authority
```

## Completed foundation — Phases 0–10

Phases 0–10 are complete. Their detailed architecture and evidence remain in the phase ADRs, labs, current-state history, and Git history.

The retained system includes AWS foundation, threat-intelligence ingestion, deterministic vulnerability correlation, repository intelligence over inert immutable evidence, deterministic risk prioritization, bounded semantic planning and SQL compilation, Bedrock Knowledge Base retrieval with Amazon S3 Vectors, hybrid evidence composition, governed public-analysis admission, and operational telemetry contracts.

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

Frozen contracts:

```text
single-agent-authority:v1
single-agent-execution:v1
single-agent-evaluation:v1
single-agent-reasoning:v1
single-agent-reasoning-evaluation:v1
```

Frozen real reference:

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

Historical evidence:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
```

Gate 11.5 intentionally retained `NO-CHANGE / NO-EXPERIMENT` because no material optimization target justified additional complexity or risk.

## Phase 12 — Multi-Agent Architecture — IN PROGRESS

Phase 12 is evidence-driven. Adding agents is never itself a success criterion.

### Gate 12.1 — Bounded Specialization Handoff Contract — COMPLETE / MERGED

Frozen contract:

```text
multi-agent-handoff:v1
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

The deterministic handoff boundary narrows the reasoning surface from four source capabilities to at most two specialist capabilities. This is not a runtime privilege-reduction claim and models still have no execution authority.

Merge reference:

```text
PR #166
merge SHA: eceed76a6cfc5d7e28e88dfdc503b4863b526ba0
```

Architecture record:

```text
docs/adr/0042-bounded-multi-agent-specialization-handoff.md
```

### Gate 12.2 — Comparative Multi-Agent Evaluation Contract — COMPLETE / MERGED

Frozen contract:

```text
multi-agent-comparison:v1
```

Gate 12.2 froze comparison criteria before a second real model call existed. Its synthetic six-case fixture is evaluator/contract conformance only.

Frozen evidence:

```text
dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
report_sha256:  0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
synthetic conformance: 6/6
capability slots for four handoffs: 16 -> 8
```

Merge reference:

```text
PR #169
merge SHA: 865ba70c813711cb88da9ac7308c8966ff983fd0
```

Architecture record:

```text
docs/adr/0043-freeze-multi-agent-comparison-before-second-model-call.md
```

### Gate 12.3 — First Bounded Real Two-Model Comparison — COMPLETE / MERGED

Gate 12.3 introduced the first real bounded triage-to-specialist experiment without transferring handoff, capability-authorization, execution, provider/model-selection, retry/fallback, evidence, or evaluation authority into a model.

Runtime path:

```text
SingleAgentTask
 -> one bounded triage model invocation
 -> transient {decision, target_specialization}
 -> deterministic parser
 -> Gate 12.1 deterministic handoff admission
 -> ABSTAIN / rejected? STOP
 -> narrowed SpecialistAgentTask
 -> one bounded specialist reasoning invocation
 -> transient {decision, capability}
 -> deterministic parser
 -> deterministic capability authorization
 -> STOP before capability execution
```

Frozen bounds:

```text
maximum model invocations per task: 2
maximum handoffs:                   1
maximum specialist capabilities:    2
adaptive application retries:       0
adaptive fallbacks:                 0
capability executions:              0
```

The first authenticated Bedrock replay was preserved before any prompt/model/topology tuning:

```text
labs/evidence/phase-12-gate-12-3-first-real-two-model-comparison-v1.json
```

Measured result:

```text
quality:                           6/6
triage decision matches:           6/6
specialization matches:            6/6
admission matches:                 6/6
target-scope matches:              6/6
non-broadening cases:              6/6
specialist decision matches:       6/6
specialist capability matches:     6/6
specialist authorization matches:  6/6
runtime-bounds compliant:          6/6
model invocations:                 10
input/output/total tokens:          5788 / 194 / 5982
provider latency median per task:  1694.0 ms
client elapsed median per task:    2135.0 ms
SDK retries:                       0
capability executions:             0
derived six-case cost:             USD 0.0074338
```

Content-addressed experiment identity:

```text
dataset_sha256: 0439ebaa6215b2de7eaa82624188576743b5a50cc847137e04dc97ee7a199be7
report_sha256:  45edf58ac911ec14e872a00464dad5d5311d82165d6b8ac4321da4a0dc5ad09b
```

Direct comparison with the frozen Phase 11 reference:

```text
metric                     Phase 11       Gate 12.3        delta
quality                    6/6            6/6              no lift
model invocations          6              10               +66.67%
input tokens               3291           5788             +75.87%
output tokens              104            194              +86.54%
total tokens               3395           5982             +76.20%
provider latency median    809.5 ms       1694.0 ms        +109.26%
client elapsed median      977.5 ms       2135.0 ms        +118.41%
SDK retries                0              0                 unchanged
capability executions      0              0                 unchanged
derived cost               USD 0.0041921  USD 0.0074338    +77.33%
```

The triage stage alone cost USD `0.0046002`, approximately 9.73% more than the complete Phase 11 six-case single-agent reference.

Gate 12.3 therefore proves feasibility and authority preservation, but no measured quality benefit. It is historical experiment evidence, not an automatic retained architecture decision.

Exact merge evidence:

```text
issue #171:             CLOSED / COMPLETED
PR #172 final head:     cf6001f374e3b14bb8048465e36210adc596b3ce
PR merge test commit:   ddd275e44d8c2122b947bc9241a321c46fef9148
Multi-Agent CI:         34218039083 / run #32 / PASS
job:                    102034353535
pytest:                 33 passed in 0.33s
merge SHA:              f51cb70ad070716e774419b8d2c62918d3e65210
```

Architecture and experiment records:

```text
docs/adr/0044-first-bounded-real-two-model-comparison.md
labs/phase-12-gate-12-3-first-bounded-real-two-model-comparison.md
```

### Gate 12.4 — Measured Multi-Agent Retention Decision — NEXT

Gate 12.4 is a decision gate. It must not begin from the assumption that the two-model topology should survive merely because the experiment passed.

Inputs are frozen:

```text
Phase 11 single-agent reference
Gate 12.1 deterministic specialization boundary
Gate 12.2 comparison contract
Gate 12.3 first authenticated two-model evidence
```

Current evidence shows:

```text
quality improvement:      none on the frozen six-case corpus
coordination surface:     larger
total model calls:        +66.67%
total token use:          +76.20%
provider latency median:  +109.26%
client latency median:    +118.41%
inference cost:           +77.33%
SDK retries:              unchanged at 0
execution authority:      unchanged at 0 capability executions
```

Decision rule:

```text
retain only if a measured specialization benefit materially justifies
added calls + tokens + latency + cost + failure surface + complexity
```

The default authorized action is **NO NEW MODEL EXPERIMENT**. A new experiment is allowed only if a concrete falsifiable hypothesis identifies a benefit that Gate 12.3 did not already measure.

Without such evidence, Gate 12.4 should reject or defer the two-model topology as the retained/default reasoning architecture while preserving its implementation and runtime artifacts as historical evidence. The Phase 11 single-agent baseline remains the reference until a superior measured topology exists.

### Phase 12 continuation rules

```text
1. each specialization has one explicit bounded responsibility
2. deterministic authorities frozen through Phase 11 remain code-owned
3. generic tool registries and arbitrary executable argument surfaces remain prohibited
4. handoff identity, failure, stopping, and loop bounds remain explicit
5. comparative evaluation uses the Phase 11 single-agent baseline as the reference
6. specialization is retained only when measured evidence demonstrates material value
7. synthetic fixture conformance is never relabeled as model quality
8. real experiment success is not automatically architecture-retention success
9. AgentCore, MCP, and A2A remain separate future decisions
10. Repository Risk != Runtime Exposure remains frozen
11. PR #89 remains deferred cross-project work
```

## Phase 13 — MCP — PLANNED

Expose bounded internal capabilities through explicit MCP contracts only after stable agent boundaries exist.

## Phase 14 — Amazon Bedrock AgentCore — PLANNED

Evaluate managed runtime capabilities against measured OpsLens needs rather than adopting them for certification coverage alone.

## Phase 15 — A2A — PLANNED

Add agent-to-agent interoperability only after stable multi-agent boundaries and handoff semantics exist.

## Phase 16 — Runtime Exposure with Amazon Inspector — PLANNED

Add independent runtime evidence without conflating repository risk with runtime exposure.

## Phase 17 — Security Hardening — PLANNED

Perform cross-cutting IAM, data protection, abuse, threat-model, dependency, and operational hardening.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 remains deferred consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and must be re-evaluated against the current architecture before any integration merge.
