# OpsLens — Incremental Roadmap

_Last updated: 2026-09-06_

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
| 8 | Hybrid Retrieval | ⏳ Next |
| 9 | Public Analyze Your Repository | ⏳ Planned |
| 10 | Observability & Operational Excellence | ⏳ Planned |
| 11 | Single-Agent Baseline | ⏳ Planned |
| 12 | Multi-Agent Architecture | ⏳ Planned |
| 13 | MCP | ⏳ Planned |
| 14 | Amazon Bedrock AgentCore | ⏳ Planned |
| 15 | A2A | ⏳ Planned |
| 16 | Runtime Exposure with Amazon Inspector | ⏳ Planned |
| 17 | Security Hardening | ⏳ Planned |
| 18 | Evaluation, Cost & Portfolio Readiness | ⏳ Planned |

## Completed foundation — Phases 0–6

### Phase 0 — AWS Foundation

Real `dev`, Terraform remote state, IAM Identity Center human access, GitHub Actions OIDC deployment identity, cost controls, CloudWatch, X-Ray, and intentional failure-path validation.

### Phase 1 — EPSS Vertical Slice

```text
FIRST EPSS
 -> EventBridge Scheduler
 -> Lambda ingestion
 -> S3 Bronze
 -> deterministic Silver / Parquet
 -> Glue Data Catalog
 -> Athena
```

### Phase 2 — Threat Intelligence Data Lake

NVD/CVE, CISA KEV, FIRST EPSS current/historical, and GitHub Security Advisory source-local deterministic evidence with provenance and explicit time coordinates.

### Phase 3 — Vulnerability Correlation Engine

Deterministic PyPI v1 applicability with canonical package identity, PEP 440 vulnerable-range evaluation, GHSA/CVE/NVD reconciliation, and content-addressed evidence.

> **No LLM decides vulnerability applicability.**

### Phase 4 — Repository Intelligence

Read-only public GitHub repository analysis over immutable snapshots and inert `uv.lock` evidence. Third-party repository code is never executed.

### Phase 5 — Risk Prioritization Engine

Deterministic Risk Policy v1 with explicit factor contributions, priority tiers, completeness semantics, and content-addressed results.

### Phase 6 — Semantic Query Layer

```text
natural-language factual question
 -> bounded Bedrock planner
 -> structured proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured evidence
```

Permanent rule:

> **No unrestricted text-to-SQL.**

## Phase 7 — Knowledge Retrieval with Bedrock — COMPLETE

Goal: create a separately measurable explanatory/remediation RAG path without replacing the structured Phase 6 authority boundary.

Permanent rules:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **Retrieval output is evidence, not deterministic truth.**

> **A valid citation ID is not proof that a claim is supported.**

Final path:

```text
knowledge/remediation question
 -> bounded RetrievalRequest
 -> Bedrock Knowledge Base Retrieve
 -> deterministic checked-corpus admission
 -> bounded deterministic context assembly
 -> deterministic pre-model authority decision
 -> bounded Bedrock synthesis
 -> deterministic citation catalog
 -> grounded claim/citation proposal
 -> explicit support judgments
 -> deterministic groundedness metrics
```

Structured NVD, KEV, EPSS, CVSS, GHSA applicability, repository-version, runtime-exposure, and Risk Policy evidence remain outside the RAG authority boundary.

### Gate 7.1 — Corpus + retrieval contract — COMPLETE

Provider-independent retrieval contracts with bounded query/top-k/provenance semantics.

### Gate 7.2 — Reproducible canonical corpus — COMPLETE

```text
6 immutable official source pins
9 canonical chunks
manifest sha256:
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

### Gate 7.3 — Knowledge Base + vector infrastructure — COMPLETE

```text
KB id:                BTVJ2PBR2A
data source id:       IEL1LBE026
vector store:         Amazon S3 Vectors
embedding model:      amazon.titan-embed-text-v2:0
dimensions:           1024
vector type:          FLOAT32
distance:             cosine
chunking:             NONE
vectors materialized: 9
```

ADR 0022 records the customer-managed Bedrock Knowledge Base + S3 Vectors decision.

### Gate 7.4 — Real bounded Retrieve adapter — COMPLETE

Direct `Retrieve`, not `RetrieveAndGenerate`, keeps retrieval independently testable and measurable.

### Gate 7.5 — Retrieval evaluation — COMPLETE

Frozen baseline:

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Negative/out-of-authority cases proved that vector similarity cannot silently become answerability or routing authority.

### Gate 7.6 — Deterministic context assembly + synthesis — COMPLETE

Established contiguous whole-chunk context assembly, deterministic pre-model authority, bounded `ANSWER | INSUFFICIENT_EVIDENCE` synthesis, one non-streaming Claude Haiku 4.5 US Geo Converse call maximum, strict provider/output admission, and content-addressed runtime evidence.

First preserved real run:

```text
retrieval request id: 4835c5d0-4a4e-4f47-9610-482ab6ec1103
retrieval elapsed:    1463 ms
retrieved/selected:   5 / 5
context bytes:        5828

synthesis request id: eee2a118-f806-40d5-8f53-57c88da8ad16
model decision:       answer
input tokens:         2671
output tokens:        491
Bedrock latency:      7217 ms
client elapsed:       7983 ms
```

### Gate 7.7 — Deterministic citations + groundedness — COMPLETE

```text
AssembledContext
 -> C1..Cn catalog
 -> structured claims + citation IDs
 -> explicit human support labels
 -> deterministic groundedness metrics
```

Frozen evaluation:

```text
knowledge-grounding-golden:v1
4 cases
3 expected answers
1 expected insufficient-evidence
```

Measured baseline:

```text
decision accuracy:          1.0
citation target precision:  0.2857142857142857
citation target recall:     0.5
claim supportedness:        0.8461538461538461
unsupported claim rate:     0.15384615384615385
citation correctness:       0.8461538461538461
abstention precision:       1.0
abstention recall:          1.0
```

The isolation case preserved a useful failure: correct evidence retrieved at rank 1, but the model cited the adjacent chunk. The TLS-cipher case correctly abstained despite non-empty retrieval.

### Gate 7.8 — Phase 7 closeout — COMPLETE

Gate 7.8 intentionally does not optimize the measured Gate 7.7 result.

It freezes:

```text
failure taxonomy across the complete RAG path
future least-privilege application runtime IAM strategy
cost-accounting boundaries
current versus missing production observability
README / docs / ADR consistency
quality and regression evidence inventory
Phase 8 entry criteria
future optimization backlog
```

Future application runtime IAM is documented in ADR 0024 but no runtime principal is created until real compute exists.

## Phase 8 — Hybrid Retrieval — NEXT

### Goal

Combine structured evidence and semantic evidence without weakening their different authority semantics.

Hybrid Retrieval in OpsLens means **hybrid evidence routing**, not automatically “hybrid keyword + vector search.” Keyword/vector hybrid search, reranking, or another vector technology may be evaluated later, but none is assumed at Phase 8 entry.

### Permanent Phase 8 authority rule

```text
structured vulnerability/risk facts
 -> deterministic structured authority

explanatory/remediation guidance
 -> bounded semantic retrieval evidence

combined response
 -> explicit evidence-class provenance
 -> no authority laundering between the two paths
```

### Gate 8.1 — Offline routing and authority contract

Before any new AWS API call:

```text
user request
 -> typed question intent / evidence need
 -> deterministic route eligibility
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> typed evidence plan
```

The first contract must define:

- which question classes require structured evidence;
- which question classes allow semantic evidence;
- when both evidence classes are allowed;
- what happens when one path is unavailable or incomplete;
- how provenance remains separated in a combined result;
- what the model may propose versus what deterministic code must verify.

### Gate 8.2 — Deterministic hybrid evidence envelope

Build a provider-independent envelope that can carry already-validated structured rows and already-admitted semantic chunks without flattening them into a single authority class.

Expected conceptual shape:

```text
HybridEvidence
  structured_evidence[]
  semantic_evidence[]
  authority_decision
  provenance_by_class
  completeness
```

No model call is required for this gate.

### Gate 8.3 — Frozen hybrid evaluation fixture

Freeze evaluation cases before tuning. Include at minimum:

```text
structured-only factual case
semantic-only remediation case
true hybrid case requiring both evidence classes
unsupported/out-of-authority case
partial structured evidence case
semantic retrieval noise case
```

Metrics should keep route accuracy, structured fact correctness, semantic groundedness, citation correctness, abstention, latency, and cost separate.

### Gate 8.4 — First bounded hybrid synthesis

Only after Gates 8.1–8.3 are CI-green should a model receive the typed hybrid evidence envelope.

The model must not:

- rewrite structured facts into a new truth source;
- convert vector similarity into applicability or risk truth;
- author canonical provenance;
- broaden tool/SQL authority;
- silently answer when required evidence is missing.

### Gate 8.5 — Measured optimization decision

Use the frozen hybrid baseline to decide whether any of the following is actually justified:

```text
larger retrieval candidate budget
reranking
keyword + vector hybrid search
metadata filtering changes
prompt/schema revision
alternative embedding or vector technology
```

Any accepted change requires a versioned hypothesis, before/after evaluation, cost impact, failure impact, and rollback path.

### Gate 8.6 — Phase 8 closeout

Reconcile architecture, cost, IAM, observability, evaluation, README/docs, and the next public-demo entry boundary before Phase 9.

## Future phases

### Phase 9 — Public Analyze Your Repository

Expose a bounded public demo only after structured query, retrieval, synthesis, groundedness, and hybrid authority boundaries are stable.

### Phase 10 — Observability & Operational Excellence

Make the deployed system diagnosable through stage latency, errors, throttling, Athena bytes, model tokens/latency, retrieval latency, route decisions, groundedness signals, and estimated investigation cost.

### Phase 11 — Single-Agent Baseline

Build one bounded agent over existing deterministic tools before introducing multi-agent complexity.

### Phase 12 — Multi-Agent Architecture

Introduce specialization only where it demonstrably improves the single-agent baseline.

### Phase 13 — MCP

Expose bounded internal tools through explicit MCP contracts only after deterministic authorities are stable.

### Phase 14 — Amazon Bedrock AgentCore

Evaluate managed runtime capabilities against measured OpsLens needs; do not adopt for certification coverage alone.

### Phase 15 — A2A

Introduce agent-to-agent interoperability only after stable single/multi-agent boundaries exist.

### Phase 16 — Runtime Exposure with Amazon Inspector

Add independent deployed-runtime evidence so repository risk can be compared with actual runtime exposure without conflation.

### Phase 17 — Security Hardening

Perform cross-cutting IAM, data protection, abuse, threat-model, guardrail, dependency, and operational hardening.

### Phase 18 — Evaluation, Cost & Portfolio Readiness

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence across the completed system.
