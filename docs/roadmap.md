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
| 7 | Knowledge Retrieval with Bedrock | 🚧 Gates 7.1–7.4 merged; Gate 7.5 closeout pending |
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

Established the real `dev` environment, Terraform remote state, IAM Identity Center human access, GitHub Actions OIDC deployment identity, cost controls, CloudWatch, X-Ray, and intentional failure-path validation.

### Phase 1 — EPSS Vertical Slice

Built the first real path:

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

> No LLM decides vulnerability applicability.

### Phase 4 — Repository Intelligence

Completed read-only public GitHub repository analysis using immutable snapshots and inert `uv.lock` evidence. Third-party repository code is never executed.

### Phase 5 — Risk Prioritization Engine

Completed deterministic Risk Policy v1 with explicit factor contributions, priority tiers, completeness semantics, and content-addressed results.

### Phase 6 — Semantic Query Layer

Completed:

```text
User question
 -> bounded Bedrock planner
 -> structured proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured result evidence
```

Permanent guardrail:

> **No unrestricted text-to-SQL.**

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

Frozen provider-independent contracts and bounds for `KnowledgeDocument`, `RetrievalRequest`, `RetrievedChunk`, `RetrievalEvidence`, and `Citation`.

### Gate 7.2 — Reproducible canonical corpus — COMPLETE

```text
6 official immutable source pins
9 canonical chunks
manifest sha256:
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

Acquisition is bounded GET-only inert text. Canonical normalization, selection, and hashing are deterministic.

### Gate 7.3 — Knowledge Base + vector infrastructure — COMPLETE / MERGED

Merged through PR #95 at:

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
```

Successful real ingestion materialized exactly nine vectors.

### Gate 7.4 — Real bounded Retrieve adapter — COMPLETE / MERGED

Squash-merged through PR #97 at:

```text
7c25877e0ae9541a4f20b8537e4f77c88ee776a5
```

Implemented direct Bedrock Knowledge Base `Retrieve`, independently from generation:

```text
RetrievalRequest
 -> exact configured KB
 -> semantic Retrieve
 -> strict provider parser
 -> checked S3 content-addressed key resolution
 -> returned-text hash + byte-count validation
 -> canonical metadata reconciliation
 -> RetrievedChunk[]
 -> RetrievalEvidence
```

A real provider representation mismatch for `section_path` failed closed and was normalized only after metadata-only diagnosis proved the exact JSON-quoted representation.

Real admitted retrieval returned the expected pip hash-checking chunk at rank 1. A nonexistent KB produced a safely categorized `ResourceNotFoundException` negative control.

### Gate 7.5 — Retrieval evaluation — COMPLETE / CLOSEOUT PENDING

Frozen evaluation:

```text
knowledge-retrieval-golden:v1
10 cases
8 positive
2 negative/out-of-authority
one top_k=10 real call per case
```

Real aggregate baseline:

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Latency:

```text
min: 532 ms
max: 1728 ms
mean: 720.0 ms
p50: 616 ms
p95: 1728 ms
SDK retries: 0
```

Both negative cases returned non-empty nearest-neighbor results and rank-1 scores near `0.689`. These scores overlap positive evidence, so Gate 7.5 explicitly rejects inventing a global relevance-score threshold from this fixture.

Important interpretation:

- `Recall@10=1.0` is weak evidence by itself because the index contains only nine vectors;
- `Recall@3`, `Recall@5`, and MRR expose ranking quality more meaningfully;
- the weakest positive target appeared at rank 7;
- runtime default `top_k=5` would capture seven of eight positive targets in the frozen fixture;
- no labels or retrieval behavior are tuned after observing this test set.

Observed real calls:

```text
10
```

S3 Vectors request-fee component at `$2.50 / 1,000,000 queries`:

```text
$0.000025
```

Processed-data, returned-data, and query-embedding components are not fabricated because Bedrock `Retrieve` does not expose the exact billable units needed to compute them.

Closeout: [`../labs/phase-7-gate-7-5-retrieval-evaluation.md`](../labs/phase-7-gate-7-5-retrieval-evaluation.md).

Remaining Gate 7.5 work:

```text
final closeout CI
confirm mergeability
ready for review
squash merge PR #98
```

### Gate 7.6 — Deterministic context assembly + synthesis — NEXT AFTER 7.5 MERGE

Only admitted retrieved chunks may enter model context.

Before implementation, freeze:

- retrieval candidate/context limits;
- deterministic context ordering and formatting;
- handling when relevant evidence is missing or authority is unsupported;
- synthesis model and invocation API;
- max input/output/token/call budgets;
- model output contract;
- runtime token/latency/request evidence;
- prompt-injection boundary for retrieved text;
- failure/abstention semantics.

Gate 7.5 evidence must inform the design, but the golden test set must not be used for ad-hoc outcome-driven tuning.

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

Make the end-to-end system diagnosable through stage latency, errors, throttling, Athena bytes, model tokens/latency, retrieval latency, and estimated investigation cost.

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
