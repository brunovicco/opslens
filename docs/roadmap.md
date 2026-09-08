# OpsLens — Incremental Roadmap

_Last updated: 2026-09-07_

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
model selection != capability authority
agent reasoning may select an already-permitted capability
agent reasoning does not acquire deterministic truth or execution authority
```

## Completed foundation — Phases 0–10

### Phase 0 — AWS Foundation

Real `dev`, Terraform remote state, IAM Identity Center human access, GitHub Actions OIDC deployment identity, cost controls, CloudWatch, X-Ray, and intentional failure-path validation.

### Phase 1 — EPSS Vertical Slice

FIRST EPSS ingestion through EventBridge Scheduler, Lambda, S3 Bronze/Silver, Glue, and Athena.

### Phase 2 — Threat Intelligence Data Lake

NVD/CVE, CISA KEV, FIRST EPSS current/historical, and GitHub Security Advisory source-local deterministic evidence with provenance and explicit time coordinates.

### Phase 3 — Vulnerability Correlation Engine

Deterministic PyPI applicability with canonical package identity, PEP 440 vulnerable-range evaluation, GHSA/CVE/NVD reconciliation, and content-addressed evidence.

### Phase 4 — Repository Intelligence

Read-only public GitHub repository analysis over immutable snapshots and inert `uv.lock` evidence. Third-party repository code is never executed.

### Phase 5 — Risk Prioritization Engine

Deterministic Risk Policy v1 with explicit factor contributions, priority tiers, completeness semantics, and content-addressed results.

### Phase 6 — Semantic Query Layer

```text
natural-language factual question
 -> bounded model planner
 -> structured proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured evidence
```

The planner never receives unrestricted SQL authority.

### Phase 7 — Knowledge Retrieval with Bedrock

Frozen infrastructure:

```text
knowledge base:          BTVJ2PBR2A
data source:             IEL1LBE026
embedding model:         amazon.titan-embed-text-v2:0
vector store:            Amazon S3 Vectors
canonical chunks:        9
```

Frozen retrieval baseline:

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

### Phase 8 — Hybrid Retrieval

Frozen contracts:

```text
hybrid-routing:v1
hybrid-evidence:v1
hybrid-synthesis:v1
hybrid-evaluation-golden:v1
```

The rejected `H8.5-01` experiment remains historical evidence that tuning is not retained without measured improvement.

### Phase 9 — Public Analyze Your Repository

Governed public-analysis boundary closes at:

```text
application boundary validated != public runtime deployed
```

### Phase 10 — Observability & Operational Excellence

Frozen contracts:

```text
operational-telemetry:v1
cloudwatch-emf:v1
```

Operational evidence is representation/evidence authority only; public runtime and CloudWatch ingestion remain separate proof obligations.

## Phase 11 — Single-Agent Baseline — COMPLETE

Completed sequence:

```text
Gate 11.1 — Capability Authorization Contract                 COMPLETE / MERGED
Gate 11.2 — Typed Capability Bindings + Offline Executor       COMPLETE / MERGED
Gate 11.3 — Frozen Single-Agent Evaluation Fixture             COMPLETE / MERGED
Gate 11.4 — First Bounded Model Reasoning Baseline             COMPLETE / MERGED
Gate 11.5 — Measured Optimization Decision                    COMPLETE / MERGED — NO-CHANGE
Gate 11.6 — Phase 11 Closeout                                 COMPLETE / MERGED
```

Frozen Phase 11 contracts:

```text
single-agent-authority:v1
single-agent-execution:v1
single-agent-evaluation:v1
single-agent-reasoning:v1
single-agent-reasoning-evaluation:v1
```

Reasoning reference:

```text
SingleAgentTask
 -> code-owned AgentCapability allowlist
 -> one fixed provider-neutral model invocation
 -> transient untrusted {decision, capability}
 -> deterministic parser
 -> AgentActionProposal
 -> deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
 -> STOP for the real reasoning-quality baseline
```

First real frozen six-case baseline:

```text
quality:                    6/6 PASS
decision matches:           6/6
capability matches:         6/6
authorization matches:      6/6
bounds compliance:          6/6
SDK retries:                0
capability executions:      0
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
derived inference cost:     USD 0.0041921
```

Historical evidence:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Gate 11.5 retained:

```text
optimization decision: NO-CHANGE / NO-EXPERIMENT
```

Phase 11 does not prove multi-agent quality, deployed/public agent runtime, production SLOs, AgentCore behavior, MCP/A2A interoperability, runtime exposure, universal model correctness, or production billing/cost distributions.

## Phase 12 — Multi-Agent Architecture — IN PROGRESS

Phase 12 is evidence-driven. The roadmap does not authorize adding agents merely for architectural novelty.

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

Deterministic handoff authority:

```text
SingleAgentTask
 -> TriageAgentTask
 -> untrusted MultiAgentHandoffProposal
 -> deterministic source-task binding
 -> code-owned specialization scope
 -> intersection with source allowed_capabilities
 -> empty intersection? FAIL CLOSED
 -> AuthorizedMultiAgentHandoff | MultiAgentHandoffAbstention
 -> narrowed SpecialistAgentTask
 -> STOP
```

Frozen Gate 12.1 bounds:

```text
maximum handoffs per task:       1
maximum specialist capabilities: 2
real model calls:                0
capability executions:           0
new AWS resources:               0
new IAM roles/policies:          0
```

The 4 -> <=2 specialist capability reduction is a deterministic reasoning-surface narrowing property, not a runtime privilege-reduction claim. Models still have no execution authority.

Gate 12.1 merged through PR #166:

```text
final head:          567cdbde81f058d9545328ca78b718c24d79c9fb
merge test commit:   b1e40ea858726c0672601db8c51c353ffbcc03ae
Multi-Agent CI:      34172909750 / run #3 / PASS
pytest:              10 passed in 0.39s
Single-Agent CI:     34172909748 / run #48 / PASS
single-agent pytest: 56 passed in 0.44s
merge SHA:           eceed76a6cfc5d7e28e88dfdc503b4863b526ba0
```

Architecture record:

```text
docs/adr/0042-bounded-multi-agent-specialization-handoff.md
```

### Gate 12.2 — Comparative Multi-Agent Evaluation Contract — NEXT

Before adding a second real model call, Gate 12.2 must freeze a deterministic comparison protocol against the Phase 11 reference.

Required dimensions:

```text
routing/proposal quality
bounds compliance
specialist capability-surface width
model invocation count
input/output/total tokens
provider/client latency
SDK retries
inference cost
capability executions
```

Gate 12.2 should first define an offline/provider-neutral evaluation dataset and report contract. It must not use an LLM judge for metric authority.

A later real experiment may be authorized only after the comparison contract is frozen. The topology must be rejected if measured specialization value does not justify additional model calls, latency, token usage, cost, failure modes, or architectural complexity.

### Phase 12 continuation rules

```text
1. each specialization has one explicit bounded responsibility
2. deterministic authorities frozen through Phase 11 remain code-owned
3. generic tool registries and arbitrary executable argument surfaces remain prohibited
4. handoff identity, failure, stopping, and loop bounds remain explicit
5. comparative evaluation uses the Phase 11 single-agent baseline as the reference
6. specialization is retained only when measured evidence demonstrates material value
7. AgentCore, MCP, and A2A remain separate future decisions
8. Repository Risk != Runtime Exposure remains frozen
9. PR #89 remains deferred cross-project work
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
