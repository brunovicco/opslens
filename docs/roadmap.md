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
| 12 | Multi-Agent Architecture | ▶️ Next |
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
agent action proposal != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
structured model output != trusted proposal
evaluation evidence != operational telemetry
model selection != capability authority
agent reasoning may select an already-permitted capability
agent reasoning does not acquire deterministic truth or execution authority
```

## Completed foundation — Phases 0–6

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

## Phase 7 — Knowledge Retrieval with Bedrock — COMPLETE

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

## Phase 8 — Hybrid Retrieval — COMPLETE

Frozen contracts:

```text
hybrid-routing:v1
hybrid-evidence:v1
hybrid-synthesis:v1
hybrid-evaluation-golden:v1
```

First complete baseline:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

`H8.5-01` was tested once and rejected because it did not improve semantic groundedness/citation correctness. Runtime default remains `hybrid-synthesis-prompt:v1`.

## Phase 9 — Public Analyze Your Repository — COMPLETE

Frozen contracts:

```text
public-analysis-request:v1
public-repository-evidence:v1
public-semantic-planning:v1
public-analysis-handoff:v1
```

Governed boundary:

```text
untrusted public JSON
 -> deterministic request admission
 -> immutable public GitHub evidence
 -> deterministic repository analysis
 -> metadata-only semantic planning proposal
 -> deterministic public-v1 scope admission
 -> existing Phase 8 hybrid authority
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

Phase 9 closes at `application boundary validated != public runtime deployed`.

## Phase 10 — Observability & Operational Excellence — COMPLETE

Frozen contracts:

```text
operational-telemetry:v1
cloudwatch-emf:v1
```

Phase 10 proves deterministic operational evidence and an AWS-native EMF representation boundary. It does not prove public runtime, CloudWatch ingestion, production latency/error distributions, runtime IAM, production cost/request, dashboards/alarms, or SLO compliance.

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

Reasoning boundary:

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

The initial capability surface remains closed:

```text
structured_security_query
knowledge_guidance
hybrid_security_answer
public_repository_analysis
```

The model receives no arbitrary args/kwargs, SQL, URL, shell, credentials, provider/model selection, retry/fallback policy, or result-authority surface.

First real frozen six-case reasoning baseline:

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

Gate 11.5 made an evidence-driven decision:

```text
optimization decision: NO-CHANGE / NO-EXPERIMENT
```

No prompt tuning, model switch, caching, retry/fallback expansion, or capability expansion was retained because the measured baseline did not expose a material target that justified additional complexity or risk.

Gate 11.6 closeout:

```text
issue #162
PR #163 final head: a17f7adc334473b3047ed3e37962b6a5881f7934
Single-Agent CI:    34171804704 / run #44 / PASS
pytest:             56 passed in 0.44s
merge SHA:          a075c9a8ec3f0998e990d0b854bfd9ed22cabd07
```

Phase 11 does not prove multi-agent quality, deployed/public agent runtime, production SLOs, AgentCore behavior, MCP/A2A interoperability, runtime exposure, universal model correctness, or production billing/cost distributions.

## Phase 12 — Multi-Agent Architecture — NEXT

Phase 12 begins only from a concrete specialization hypothesis. The roadmap does not authorize adding agents merely for architectural novelty.

Entry rules:

```text
1. each agent/specialization has one explicit bounded responsibility
2. deterministic authorities frozen through Phase 11 remain code-owned
3. generic tool registries and arbitrary executable argument surfaces remain prohibited
4. handoff identity, failure, stopping, and loop bounds are explicit before execution
5. comparative evaluation uses the Phase 11 single-agent baseline as the reference
6. specialization is retained only when measured evidence demonstrates material value
7. AgentCore, MCP, and A2A remain separate future decisions
8. Repository Risk != Runtime Exposure remains frozen
9. PR #89 remains deferred cross-project work
```

The first Phase 12 gate should therefore define a bounded multi-agent hypothesis and comparison protocol before implementation.

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
