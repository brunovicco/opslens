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
| 12 | Multi-Agent Architecture | ✅ Complete |
| 13 | MCP | ▶️ Next |
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
```

## Completed foundation — Phases 0–10

Phases 0–10 are complete. Their detailed architecture, evidence, AWS/IAM decisions, and failure-path records remain in ADRs, labs, and Git history.

The retained platform includes AWS foundation, threat-intelligence ingestion, deterministic vulnerability correlation, repository intelligence over immutable inert evidence, deterministic risk prioritization, bounded semantic planning and SQL compilation, Bedrock Knowledge Base retrieval with Amazon S3 Vectors, hybrid evidence composition, governed public-analysis admission, and operational telemetry contracts.

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

Retained measured reference:

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

This remains the default/reference measured reasoning architecture until a superior topology is demonstrated against a frozen benchmark.

## Phase 12 — Multi-Agent Architecture — COMPLETE

Phase 12 tested specialization as an evidence-backed architecture hypothesis rather than assuming that more agents are better.

Completed sequence:

```text
Gate 12.1 — Bounded Specialization Handoff Contract            COMPLETE / MERGED
Gate 12.2 — Comparative Multi-Agent Evaluation Contract        COMPLETE / MERGED
Gate 12.3 — First Bounded Real Two-Model Comparison            COMPLETE / MERGED
Gate 12.4 — Measured Multi-Agent Retention Decision            COMPLETE / MERGED
Gate 12.5 — Multi-Agent Phase Closeout                         COMPLETE / MERGED
```

### Retained Phase 12 mechanism

Gate 12.1 freezes deterministic specialization/handoff authority:

```text
source task
 -> code-owned specialization mapping
 -> deterministic intersection with source allowed_capabilities
 -> narrowed specialist task
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

This narrows reasoning surface without granting model-owned handoff admission or execution authority.

```text
PR #166
merge SHA: eceed76a6cfc5d7e28e88dfdc503b4863b526ba0
ADR: docs/adr/0042-bounded-multi-agent-specialization-handoff.md
```

### Frozen comparison discipline

Gate 12.2 freezes deterministic comparison semantics before a second real model call exists:

```text
dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
report_sha256:  0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
synthetic conformance: 6/6
```

Synthetic fixture conformance is evaluator/contract evidence only.

```text
PR #169
merge SHA: 865ba70c813711cb88da9ac7308c8966ff983fd0
ADR: docs/adr/0043-freeze-multi-agent-comparison-before-second-model-call.md
```

### Historical Gate 12.3 real experiment

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

### Gate 12.4 retention decision

Measured Phase 11 versus Gate 12.3 deltas:

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

Frozen retention decision:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
new rescue/tuning experiment:                   NOT AUTHORIZED WITHOUT NEW HYPOTHESIS
```

```text
PR #175
merge SHA: fabe8128d1d6077e8de92225991b5e26c1b72ab3
ADR: docs/adr/0045-do-not-retain-two-model-topology-without-measured-lift.md
```

### Gate 12.5 closeout

Phase 12 closes around the measured retained architecture:

```text
retained runtime reasoning reference: Phase 11 single-agent
retained Phase 12 mechanism:          deterministic specialization/handoff
retained comparison discipline:       deterministic decomposed evaluation
non-retained default topology:        Gate 12.3 two-model triage + specialist
historical experiment evidence:       preserved
```

Closeout evidence:

```text
labs/evidence/phase-12-closeout-v1.json
labs/phase-12-gate-12-5-multi-agent-closeout.md
docs/adr/0046-phase12-multi-agent-closeout.md
```

Exact closeout merge evidence:

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

### Phase 12 proof boundary

Phase 12 does not claim:

```text
multi-agent capability execution in a deployed runtime
public/deployed agent runtime
production agent SLOs
Amazon Bedrock AgentCore runtime behavior
MCP interoperability
A2A interoperability
runtime exposure / Amazon Inspector evidence
universal superiority of multi-agent architecture
```

## Phase 13 — MCP — NEXT

Phase 13 may expose already-bounded OpsLens capabilities through explicit MCP contracts.

The initial architecture rule is:

> **MCP is an interoperability boundary, not new business authority.**

Entry constraints:

```text
1. expose only already-bounded capabilities
2. preserve deterministic capability authorization
3. preserve typed invocation/result admission
4. prohibit arbitrary executable args/kwargs, SQL, URLs, shell, credentials, or hidden provider selection
5. preserve evidence provenance and content-addressed identity
6. fail closed on unknown tools, schemas, capability IDs, or result bindings
7. keep IAM least privilege tied to concrete MCP runtime needs
8. do not conflate MCP transport success with business/evidence truth
9. Repository Risk != Runtime Exposure remains frozen
10. deferred PR #89 remains separate cross-project work
```

The first Phase 13 gate should freeze the MCP capability exposure contract and threat boundary before introducing a network/public MCP runtime.

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
