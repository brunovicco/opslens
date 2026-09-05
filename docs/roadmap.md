# OpsLens — Incremental Roadmap

_Last updated: 2026-09-05_

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
| 7 | Knowledge Retrieval with Bedrock | 🚧 Gates 7.1–7.3 complete; PR #95 merge pending |
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

Implemented:

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

Completed NVD/CVE, CISA KEV, FIRST EPSS current/historical, and GitHub Security Advisory source-local deterministic evidence while preserving explicit provenance and time coordinates.

### Phase 3 — Vulnerability Correlation Engine

Completed deterministic PyPI v1 applicability with canonical package identity, PEP 440 range evaluation, GHSA/CVE/NVD reconciliation, and content-addressed correlation evidence.

Permanent rule:

> No LLM decides vulnerability applicability.

### Phase 4 — Repository Intelligence

Completed the read-only public GitHub repository slice using immutable repository snapshots and inert `uv.lock` evidence. Third-party repository code is never executed.

### Phase 5 — Risk Prioritization Engine

Completed deterministic Risk Policy v1 over Phase 4 evidence with explicit factor contributions, priority tiers, completeness semantics, and content-addressed results.

## Phase 6 — Semantic Query Layer — COMPLETE

Goal:

> Convert bounded natural-language factual questions into typed semantic queries and deterministic Athena SQL without giving a model unrestricted SQL authority.

Target flow:

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

Real Phase 6 evidence includes bounded planner tokens/latency/cost, Athena bytes/latency, supported E2E execution, unsupported fail-closed behavior, and diagnosed IAM Identity Center credential failure.

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

Frozen provider-independent contracts:

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

Citations are projected from admitted retrieval evidence rather than model-authored URLs/source IDs.

### Gate 7.2 — Reproducible canonical corpus — COMPLETE

Corpus shape:

```text
6 official immutable source pins
9 canonical chunks
manifest sha256:
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

Acquisition is bounded GET-only inert text. Canonical normalization/selection/hashing is deterministic. Third-party text is not vendored into Git.

### Gate 7.3 — Knowledge Base + vector infrastructure — COMPLETE / PR #95 MERGE PENDING

Validated architecture:

```text
KB mode:              customer-managed Bedrock vector Knowledge Base
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

Real publication evidence:

```text
18 verified S3 objects
9 canonical text objects
9 compact metadata sidecars
14,928 total bytes
394..493 sidecar bytes
```

Real successful ingestion:

```text
job:                           WZRUGOFZPI
status:                        COMPLETE
observed duration:             11.145552 seconds
documents scanned:             9
new documents indexed:         9
documents failed:              0
documents skipped:             0
vectors materialized:          9
```

Real failure evidence retained:

- first ingestion ignored all nine files because verbose metadata sidecars exceeded the 1024-byte Bedrock/S3 Vectors limit;
- local botocore SSO credential resolution produced a safely categorized `TokenRetrievalError` while AWS CLI credentials remained usable;
- direct human `sts:AssumeRole` on the Bedrock KB service role returned expected `AccessDenied`.

No failure was fixed by broadening the KB service role or OIDC trust.

ADR: [`adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md`](adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md).
Closeout: [`../labs/phase-7-gate-7-3-kb-vector-infrastructure.md`](../labs/phase-7-gate-7-3-kb-vector-infrastructure.md).

### Gate 7.4 — Real bounded Retrieve adapter — NEXT

Implement Amazon Bedrock Knowledge Base `Retrieve` directly, independently from generation.

Required properties:

- consume the frozen `RetrievalRequest` contract;
- bounded `top_k` only;
- exact Knowledge Base ID configured outside model authority;
- provider-neutral adapter Protocol;
- typed Bedrock response parsing;
- reject malformed/extra/untrusted provider evidence;
- map returned S3 location/content/metadata back to the frozen publication/corpus identity;
- independently validate returned chunk text/hash before admitting `RetrievedChunk`;
- preserve deterministic rank and provenance;
- bounded provider errors and retry behavior;
- separate least-privilege retrieval runtime IAM identity;
- intentional real failure evidence;
- no `RetrieveAndGenerate` shortcut.

Exit evidence should include a first real retrieval request, returned ranks/scores/provenance, latency, request bounds, IAM/failure evidence, and query-cost rationale.

### Gate 7.5 — Retrieval evaluation — PLANNED

Use the frozen golden dataset to measure retrieval separately from synthesis:

```text
Recall@1
Recall@3
Recall@5
Recall@10
MRR
provenance/source correctness
latency
retrieval cost
```

### Gate 7.6 — Deterministic context assembly + synthesis — PLANNED

Only admitted retrieved chunks may enter model context. Freeze context/token limits, synthesis model authority, output contract, runtime evidence, and denial-of-wallet controls before treating synthesis as complete.

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

Expose bounded internal tools through explicit MCP contracts only after their deterministic authorities are stable.

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
