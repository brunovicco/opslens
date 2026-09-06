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
| 7 | Knowledge Retrieval with Bedrock | 🚧 Gates 7.1–7.4 complete; PR #97 merge pending |
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

## Completed foundation

### Phase 0 — AWS Foundation

Established the real `dev` environment, Terraform remote state, IAM Identity Center human access, GitHub Actions OIDC deployment identity, cost controls, CloudWatch, X-Ray, and intentional failure-path validation.

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

Completed NVD/CVE, CISA KEV, FIRST EPSS current/historical, and GitHub Security Advisory source-local deterministic evidence while preserving provenance and time coordinates.

### Phase 3 — Vulnerability Correlation Engine

Completed deterministic PyPI v1 applicability with canonical package identity, PEP 440 range evaluation, GHSA/CVE/NVD reconciliation, and content-addressed evidence.

Permanent rule:

> No LLM decides vulnerability applicability.

### Phase 4 — Repository Intelligence

Completed read-only public GitHub repository analysis using immutable snapshots and inert `uv.lock` evidence. Third-party repository code is never executed.

### Phase 5 — Risk Prioritization Engine

Completed deterministic Risk Policy v1 with explicit factor contributions, priority tiers, completeness semantics, and content-addressed results.

## Phase 6 — Semantic Query Layer — COMPLETE

Goal:

> Convert bounded natural-language factual questions into typed semantic queries and deterministic Athena SQL without giving a model unrestricted SQL authority.

```text
User question
 -> bounded Bedrock planner
 -> structured proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic validator + SQL compiler
 -> bounded read-only Athena
 -> structured result evidence
```

Permanent guardrail:

> **No unrestricted text-to-SQL.**

Completed gates:

```text
6.1 Typed semantic-query contract + deterministic compiler    COMPLETE
6.2 Bounded read-only Athena execution                       COMPLETE
6.3 Bounded planner contract + offline evaluation            COMPLETE
6.4 Real Bedrock planner invocation                          COMPLETE
```

## Phase 7 — Knowledge Retrieval with Bedrock — IN PROGRESS

### Goal

Create a separately testable explanatory/remediation retrieval path without replacing the structured Phase 6 path.

Permanent rules:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **Retrieval output is evidence, not deterministic truth.**

Target architecture:

```text
knowledge/remediation question
 -> bounded RetrievalRequest
 -> Bedrock Knowledge Base Retrieve
 -> typed RetrievedChunk[] + provenance
 -> deterministic validation/context admission
 -> bounded Bedrock synthesis
 -> answer + deterministic citations
```

Structured NVD, KEV, EPSS, CVSS, GHSA applicability, repository-version, and Risk Policy evidence remain outside the RAG authority boundary.

### Gate 7.1 — Corpus + retrieval contract — COMPLETE

Frozen contracts:

```text
KnowledgeDocument
RetrievalRequest
RetrievedChunk
RetrievalEvidence
Citation
```

Bounds:

```text
query:         non-blank, <= 1,000 chars
top_k:         1..10
default top_k: 5
provider DSL:  none
```

Citations are projected from admitted evidence rather than model-authored source IDs or URLs.

### Gate 7.2 — Reproducible canonical corpus — COMPLETE

```text
6 official immutable source pins
9 canonical chunks
manifest sha256:
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

Acquisition is bounded GET-only inert text. Canonical normalization, selection, and hashing are deterministic.

### Gate 7.3 — Knowledge Base + vector infrastructure — COMPLETE / MERGED

Merged through PR #95:

```text
1337950ddb5948943bf361dba4c3cdc40dafaf2b
```

Validated baseline:

```text
KB id:                BTVJ2PBR2A
data source id:       IEL1LBE026
vector store:         Amazon S3 Vectors
embedding model:      amazon.titan-embed-text-v2:0
dimensions:           1024
vector type:          FLOAT32
distance:             cosine
chunking:             NONE
source prefix:        knowledge/corpus/v1/bedrock/
```

Real successful ingestion:

```text
job:                    WZRUGOFZPI
status:                 COMPLETE
duration:               11.145552 s
documents scanned:      9
new documents indexed:  9
failed:                 0
skipped:                0
vectors materialized:   9
```

Real failure evidence included oversized metadata sidecars, a safely categorized botocore SSO credential failure, and an expected human `AssumeRole` denial on the Bedrock service role. None was fixed by broadening IAM.

ADR: [`adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md`](adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md).

Closeout: [`../labs/phase-7-gate-7-3-kb-vector-infrastructure.md`](../labs/phase-7-gate-7-3-kb-vector-infrastructure.md).

### Gate 7.4 — Real bounded Retrieve adapter — COMPLETE / PR #97 MERGE PENDING

Implemented direct Amazon Bedrock Knowledge Base `Retrieve`, independently from generation.

Frozen runtime path:

```text
RetrievalRequest
 -> exact configured KB
 -> direct semantic Retrieve
 -> strict provider parser
 -> checked S3 content-addressed key resolution
 -> independent returned-text hash + byte-count validation
 -> canonical metadata reconciliation
 -> RetrievedChunk[]
 -> RetrievalEvidence
```

Provider authority is deliberately smaller than the product contract:

- no arbitrary provider DSL;
- no hybrid override;
- no reranking;
- no synthesis;
- no implicit pagination;
- typed filters fail before the provider call until deterministic translation exists.

The first real call correctly failed closed because Bedrock represented `section_path` elements as JSON-quoted strings. A metadata-only diagnostic proved the exact provider shape; the adapter now decodes only valid JSON-quoted string scalars and still requires exact equality with the checked manifest. Regression CI is green.

Real admitted Retrieve:

```text
query sha256:         5b398fe871d0cb51eaacb4f42a11b2ec402b5fdb4c523d2b7bca85e84dff3d0d
knowledge base:       BTVJ2PBR2A
requested top_k:      5
returned/admitted:    5
provider request id:  e92d67f1-18fa-4537-8ff4-c2e02ab813e0
client elapsed:       1257 ms
SDK retries:          0
rank 1:               knowledge-chunk:pypa-secure-installs:hashes:v1
rank 1 score:         0.8649594783782959
```

Intentional real provider failure:

```text
nonexistent KB: ZZZZZZZZZZ
provider_code: ResourceNotFoundException
```

The failure was read-only and exposed only a safe provider code.

IAM review concluded that retrieval must remain separate from ingestion/vector-write authority. Final role attachment is deferred until a real application runtime principal exists rather than creating unused IAM surface.

Observed populated-index search count for this gate: `3`.

At current S3 Vectors request pricing of `$2.50 / 1,000,000 queries`, the request-fee component for those three searches is approximately `$0.0000075`, plus negligible processed-data cost for the nine-vector laboratory index and query-embedding model usage. Exact provider billing is not inferred from incomplete telemetry.

Closeout: [`../labs/phase-7-gate-7-4-bounded-retrieve.md`](../labs/phase-7-gate-7-4-bounded-retrieve.md).

### Gate 7.5 — Retrieval evaluation — NEXT

Measure the frozen raw semantic baseline before adding synthesis, reranking, hybrid search, or arbitrary provider filters.

Required metrics:

```text
Recall@1
Recall@3
Recall@5
Recall@10
MRR
provenance/source correctness
latency distribution
retrieval-call count
bounded retrieval cost assumptions
```

Evaluation must use the frozen Gate 7.1/7.2 fixture and the Gate 7.4 direct-Retrieve runtime. Provider relevance scores are evidence only, not calibrated confidence.

### Gate 7.6 — Deterministic context assembly + synthesis — PLANNED

Only admitted retrieved chunks may enter model context. Freeze token/context limits, synthesis model authority, output contract, runtime evidence, and denial-of-wallet controls before treating synthesis as complete.

### Gate 7.7 — Citations + groundedness — PLANNED

Require citations mapped deterministically to admitted evidence and measure citation correctness/coverage plus unsupported claims/groundedness.

### Gate 7.8 — Phase 7 closeout — PLANNED

Require retrieval + synthesis failure diagnosis, IAM least-privilege review, retrieval/embedding/vector/synthesis cost split, observability evidence, ADRs, targeted/regression tests, documentation, and logical merge.

## Future phases

### Phase 8 — Hybrid Retrieval

Combine deterministic structured threat intelligence with semantic retrieval only where evaluation demonstrates value.

### Phase 9 — Public Analyze Your Repository

Expose a bounded public demo only after repository intelligence, risk policy, structured query, and retrieval boundaries are stable.

### Phase 10 — Observability & Operational Excellence

Make the end-to-end system diagnosable through stage latency, errors, throttling, queue/DLQ state, Athena bytes, model tokens/latency, retrieval latency, and estimated investigation cost.

### Phase 11 — Single-Agent Baseline

Build one bounded agent over existing deterministic tools before introducing multi-agent complexity.

### Phase 12 — Multi-Agent Architecture

Introduce specialization only where it demonstrably improves the single-agent baseline.

### Phase 13 — MCP

Expose bounded internal tools through explicit MCP contracts only after deterministic authorities are stable.

### Phase 14 — Amazon Bedrock AgentCore

Evaluate managed agent runtime capabilities against measured OpsLens needs; do not adopt for certification coverage alone.

### Phase 15 — A2A

Introduce agent-to-agent interoperability only after stable single/multi-agent boundaries exist.

### Phase 16 — Runtime Exposure with Amazon Inspector

Add independent deployed-runtime evidence so repository risk can be compared with actual runtime exposure without conflating the two.

### Phase 17 — Security Hardening

Perform cross-cutting IAM, data protection, abuse, threat-model, guardrail, dependency, and operational hardening.

### Phase 18 — Evaluation, Cost & Portfolio Readiness

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence across the completed system.
