# OpsLens — Incremental Roadmap

_Last updated: 2026-09-06_

OpsLens advances in small, demonstrable, observable, and reversible gates.

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
| 6 | Semantic Query Layer | ✅ Complete — PR #91 |
| 7 | Knowledge Retrieval with Bedrock | 🚧 Gates 7.1–7.6 merged; Gate 7.7 active on PR #100 |
| 8 | Hybrid Retrieval | ⏳ Planned |
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

## Phase 7 — Knowledge Retrieval with Bedrock — IN PROGRESS

Goal: create a separately measurable explanatory/remediation RAG path without replacing the structured Phase 6 authority boundary.

Permanent rules:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **Retrieval output is evidence, not deterministic truth.**

> **A valid citation ID is not proof that a claim is supported.**

Target path through the active gate:

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
 -> deterministic metric computation over explicit support judgments
```

Structured NVD, KEV, EPSS, CVSS, GHSA applicability, repository-version, runtime-exposure, and Risk Policy evidence remain outside the RAG authority boundary.

### Gate 7.1 — Corpus + retrieval contract — COMPLETE / MERGED

Provider-independent `KnowledgeDocument`, `RetrievalRequest`, `RetrievedChunk`, `RetrievalEvidence`, and `Citation` contracts with explicit query/top-k/provenance bounds.

### Gate 7.2 — Reproducible canonical corpus — COMPLETE / MERGED

```text
6 immutable official source pins
9 canonical chunks
manifest sha256:
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

### Gate 7.3 — Knowledge Base + vector infrastructure — COMPLETE / MERGED

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

### Gate 7.4 — Real bounded Retrieve adapter — COMPLETE / MERGED

Direct `Retrieve`, not `RetrieveAndGenerate`, keeps retrieval independently testable and measurable.

### Gate 7.5 — Retrieval evaluation — COMPLETE / MERGED

Frozen 10-case real baseline:

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Negative/out-of-authority results proved that vector similarity score cannot silently become answerability or routing authority.

### Gate 7.6 — Deterministic context assembly + synthesis — COMPLETE / MERGED

Squash merge through PR #99:

```text
cc8097b3e2e9b048ca069e961736788de0a79f0d
```

Gate 7.6 established whole contiguous rank-prefix context assembly, deterministic `SUPPORTED | UNSUPPORTED` pre-model authority, bounded `ANSWER | INSUFFICIENT_EVIDENCE` synthesis, one non-streaming Claude Haiku 4.5 US Geo Converse call maximum, strict provider/output admission, and content-addressed runtime evidence.

First preserved real run:

```text
retrieval request id: 4835c5d0-4a4e-4f47-9610-482ab6ec1103
retrieval elapsed:    1463 ms
retrieval retries:    0
retrieved/selected:   5 / 5
context bytes:        5828

synthesis request id: eee2a118-f806-40d5-8f53-57c88da8ad16
model decision:       answer
answer chars:         1751
input tokens:         2671
output tokens:        491
total tokens:         3162
Bedrock latency:      7217 ms
client elapsed:       7983 ms
synthesis retries:    0
```

Directly computable first-run cost components total `$0.0056411`; unexposed Titan/S3 Vectors billable units are not fabricated.

### Gate 7.7 — Deterministic Citations + Groundedness — IN PROGRESS / PR #100

Gate 7.7 begins only after Gate 7.6 merge and remains offline-first before changing provider prompts.

#### 7.7a — Deterministic citation catalog — COMPLETE

```text
AssembledContext
 -> selected blocks only
 -> C1..Cn in exact retrieval-rank order
 -> ProjectedCitation[]
 -> CitationCatalog
```

Canonical URL/source/document/chunk identity and document/chunk hashes come from admitted evidence. Provider score is absent. Retrieval suffixes excluded from context cannot be cited.

A model may later reference `C1`; it cannot decide what `C1` means.

#### 7.7b — Structured grounded claim contract — COMPLETE

Frozen provider-independent answer proposal:

```json
{
  "decision": "answer",
  "claims": [
    {"text": "...", "citation_ids": ["C1"]}
  ]
}
```

or:

```json
{"decision": "insufficient_evidence", "claims": []}
```

Rules:

- every answer claim must contain at least one citation ID;
- model-authored claim IDs are rejected;
- model-authored URLs/source IDs/document IDs/chunk IDs/hashes are rejected;
- unknown citation IDs fail closed;
- citation references canonicalize to catalog order;
- deterministic code assigns claim indices and renders the final answer;
- the original Gate 7.6 output entitlement remains the hard answer bound.

```text
max claims:            16
max chars/claim:      1,000
rendered answer:      <= 4,000 chars hard bound
raw response parser:  <= 65,536 chars
```

This structurally provides citation presence for every admitted claim but does not prove that a citation semantically supports that claim.

CI:

```text
#266 SUCCESS — citation catalog
#267 FAIL — Ruff export ordering only
#268 SUCCESS — grounded claim contract
```

No Gate 7.7 AWS/model call has occurred.

#### 7.7c — Frozen groundedness fixture + metrics — NEXT

Before modifying the Bedrock prompt/schema:

```text
freeze evaluation questions/evidence targets
 -> define citation target precision/recall
 -> define explicit claim-support judgment provenance
 -> deterministically compute claim supportedness
 -> deterministically compute citation correctness
 -> track unsupported claim rate
 -> track abstention separately
```

A model evaluator, if introduced later, may be a bounded evaluation signal but cannot silently become truth authority.

#### 7.7d — Bedrock grounded-output integration — PENDING

Only after 7.7c is frozen should the existing Converse structured-output schema be versioned for claims + allowlisted citation IDs.

#### 7.7e — Real groundedness evaluation — PENDING

Execute a versioned bounded evaluation once, preserving first-run evidence instead of repeatedly sampling until the result looks good.

#### 7.7f — Closeout + merge — PENDING

Synchronize docs/evidence, final CI, ready transition, and protected squash merge by validated head SHA.

### Gate 7.8 — Phase 7 closeout — PLANNED

Review retrieval/synthesis/citation failure diagnosis, least-privilege runtime IAM strategy, retrieval/embedding/vector/synthesis cost split, observability evidence, ADRs, regressions, and phase documentation.

## Future phases

### Phase 8 — Hybrid Retrieval

Combine deterministic structured threat intelligence with semantic retrieval only where evaluation demonstrates value.

### Phase 9 — Public Analyze Your Repository

Expose a bounded public demo only after repository intelligence, risk policy, structured query, retrieval, synthesis, and groundedness boundaries are stable.

### Phase 10 — Observability & Operational Excellence

Make the system diagnosable through stage latency, errors, throttling, Athena bytes, model tokens/latency, retrieval latency, and estimated investigation cost.

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
