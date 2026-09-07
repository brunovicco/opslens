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
| 11 | Single-Agent Baseline | 🚧 In progress — Gates 11.1–11.4 complete |
| 12 | Multi-Agent Architecture | ⏳ Planned |
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

Phase 11 adds:

```text
agent action proposal != capability authorization != execution result != evaluation score
AuthorizedAgentAction != capability invocation
capability invocation != execution result
evaluation evidence != operational telemetry
structured model output != trusted proposal
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

`H8.5-01` was tested once and rejected. Runtime default remains `hybrid-synthesis-prompt:v1`.

### Phase 9 — Public Analyze Your Repository

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

### Phase 10 — Observability & Operational Excellence

Frozen contracts:

```text
operational-telemetry:v1
cloudwatch-emf:v1
```

Phase 10 proves deterministic operational evidence and an AWS-native EMF representation boundary. It does not prove public runtime, CloudWatch ingestion, production latency/error distributions, runtime IAM, production cost/request, dashboards/alarms, or SLO compliance.

## Phase 11 — Single-Agent Baseline — IN PROGRESS

Current sequence:

```text
Gate 11.1 — Capability Authorization Contract                 COMPLETE / MERGED
Gate 11.2 — Typed Capability Bindings + Offline Executor       COMPLETE / MERGED
Gate 11.3 — Frozen Single-Agent Evaluation Fixture             COMPLETE / MERGED
Gate 11.4 — First Bounded Model Reasoning Baseline             COMPLETE / MERGED
Gate 11.5 — Measured Optimization Decision                    NEXT
Gate 11.6 — Phase 11 Closeout                                 BLOCKED
```

### Gate 11.1 — capability authorization — COMPLETE

Frozen contract `single-agent-authority:v1` with four initial capability classes:

```text
structured_security_query
knowledge_guidance
hybrid_security_answer
public_repository_analysis
```

Authority remains code-owned: model/proposal output cannot itself authorize a capability.

### Gate 11.2 — typed capability bindings + offline executor — COMPLETE

Frozen contract `single-agent-execution:v1`. Only exact typed capability invocations are accepted; no generic tool registry, arbitrary kwargs, SQL, URL, shell command, provider/model selector, credentials, retry policy, or fallback policy exists at the invocation surface.

### Gate 11.3 — frozen single-agent evaluation fixture — COMPLETE

Frozen contract `single-agent-evaluation:v1`. Evaluation replays the deterministic Gate 11.1/11.2 boundaries with decomposed metrics and no LLM judge.

### Gate 11.4 — first bounded model reasoning baseline — COMPLETE

New contracts:

```text
single-agent-reasoning:v1
single-agent-reasoning-evaluation:v1
```

Reasoning boundary:

```text
SingleAgentTask
 -> one fixed provider-neutral model invocation
 -> transient untrusted {decision, capability}
 -> deterministic parser
 -> existing AgentActionProposal
 -> existing authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
 -> STOP
```

The baseline deliberately executes no capability.

Fixed provider:

```text
Amazon Bedrock Converse
region:          us-east-1
model/profile:   us.anthropic.claude-haiku-4-5-20251001-v1:0
temperature:     0.0
maxTokens:       96
tools:           disabled
```

The first authenticated runtime attempt exposed that Bedrock structured outputs reject JSON Schema `oneOf`. The provider schema was corrected to a flat closed object while deterministic application code retained ACT/ABSTAIN cross-field authority.

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

Preserved evidence:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Exact completion evidence:

```text
issue #156:              CLOSED / COMPLETED
PR #157 final head:      2ec5b3804fa8c6454e1ea7d824b82d2db9113f91
Single-Agent CI:         34170308179 / run #37 / PASS
job:                     101889202476
PR merge test commit:    bd3802bf4003e5a447e5e104caad0a86cf8388ec
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest:                  56 passed in 0.43s
PR #157 merge SHA:       8b41025facf4451490bf96223d69fbed19b4a00f
```

Gate 11.4 added no new AWS resources, IAM roles/policies, AgentCore, MCP, A2A, public runtime, or runtime-exposure authority.

### Gate 11.5 — measured optimization decision — NEXT

Gate 11.5 must answer a decision question before changing code:

```text
Does the measured Gate 11.4 baseline expose a material quality, latency, token, or cost gap that justifies one bounded optimization experiment?
```

Current evidence is already strong: `6/6` proposal quality, `6/6` bounds compliance, zero retries, zero capability executions, sub-second median provider latency, and a six-case derived inference cost of USD 0.0041921.

Therefore Gate 11.5 must not tune prompts, switch models, introduce caching, expand retries/fallback, add tool authority, or change provider topology merely because an optimization gate exists. If no measurable objective with material expected benefit is identified, the correct decision is to preserve the Gate 11.4 baseline and proceed to Gate 11.6 closeout.

## Phase 12 — Multi-Agent Architecture — PLANNED

Introduce specialization only where measured evidence improves the Phase 11 single-agent baseline.

## Phase 13 — MCP — PLANNED

Expose bounded internal capabilities through explicit MCP contracts after deterministic authorities are stable.

## Phase 14 — Amazon Bedrock AgentCore — PLANNED

Evaluate managed runtime capabilities against measured OpsLens needs rather than adopting them for certification coverage alone.

## Phase 15 — A2A — PLANNED

Add agent-to-agent interoperability only after stable agent boundaries exist.

## Phase 16 — Runtime Exposure with Amazon Inspector — PLANNED

Add independent runtime evidence without conflating repository risk with runtime exposure.

## Phase 17 — Security Hardening — PLANNED

Perform cross-cutting IAM, data protection, abuse, threat-model, dependency, and operational hardening.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 remains deferred consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and must be re-evaluated against the current architecture before any integration merge.
