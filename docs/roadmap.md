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
| 7 | Knowledge Retrieval with Bedrock | 🚧 Gates 7.1–7.5 merged; Gate 7.6 complete through 7.6f on PR #99 |
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

Target path:

```text
knowledge/remediation question
 -> bounded RetrievalRequest
 -> Bedrock Knowledge Base Retrieve
 -> deterministic checked-corpus admission
 -> bounded deterministic context assembly
 -> deterministic pre-model authority decision
 -> bounded Bedrock synthesis
 -> deterministic citations + groundedness evaluation
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

Acquisition is bounded GET-only inert text; normalization, exact selection, and hashing are deterministic.

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

Direct `Retrieve`, not `RetrieveAndGenerate`, so retrieval remains independently testable.

Real success:

```text
requested top_k:     5
returned/admitted:   5
client elapsed:      1257 ms
SDK retries:         0
rank 1:              knowledge-chunk:pypa-secure-installs:hashes:v1
rank 1 score:        0.8649594783782959
```

A nonexistent KB is safely categorized as provider failure without leaking response bodies.

### Gate 7.5 — Retrieval evaluation — COMPLETE / MERGED

Frozen fixture:

```text
knowledge-retrieval-golden:v1
10 cases
8 positive
2 negative/out-of-authority
one real top_k=10 call per case
```

Measured baseline:

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

Both negative cases returned non-empty nearest-neighbor results with rank-1 scores near `0.689`, overlapping legitimate positive evidence. No global relevance-score threshold is invented.

### Gate 7.6 — Deterministic context assembly + synthesis — COMPLETE THROUGH 7.6f / PR #99

Gate 7.6 separates evidence selection, model authority, provider transport, and output validation.

#### 7.6a — Deterministic context assembly — COMPLETE

```text
RetrievalEvidence
 -> whole contiguous rank prefix
 -> ContextEvidenceBlock[]
 -> AssembledContext
```

Bounds:

```text
default max chunks:      5
hard max chunks:         10
max admitted text bytes: 16,384 UTF-8 bytes
```

No truncation, no backfill, no score-derived authority.

#### 7.6b — Synthesis request/output + abstention — COMPLETE

Deterministic pre-model authority:

```text
SUPPORTED
UNSUPPORTED
```

Allowed model decisions only after admission:

```text
ANSWER
INSUFFICIENT_EVIDENCE
```

Prompt trust classes remain distinct: trusted system instructions, untrusted user question, untrusted but source-verified retrieved evidence.

#### 7.6c — Bedrock model/API/IAM/cost selection — COMPLETE

ADR 0023 freezes:

```text
Region:             us-east-1
endpoint/API:       bedrock-runtime / Converse
model/profile:      us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:          no
temperature:        0.0
maxTokens:          2048
model calls:        1 maximum
tools:              none
structured output:  JSON Schema
```

No deployed runtime principal exists yet, so no synthetic application IAM role is created.

#### 7.6d — Offline provider adapter — COMPLETE

Exactly one non-streaming `converse()` invocation, strict `end_turn`/assistant-text/usage/latency evidence admission, deterministic model-output parsing, and explicit provider/response/stop/output/timing failure categories.

#### 7.6e — First bounded real synthesis — COMPLETE

Exactly one supported real run completed successfully:

```text
retrieval request id: 4835c5d0-4a4e-4f47-9610-482ab6ec1103
retrieval latency:    1463 ms
retrieval retries:    0
retrieved/selected:   5 / 5
context bytes:        5828
context stop:         exhausted_retrieval

synthesis request id: eee2a118-f806-40d5-8f53-57c88da8ad16
model decision:       answer
answer chars:         1751
input tokens:         2671
output tokens:        491
total tokens:         3162
Bedrock latency:      7217 ms
client elapsed:       7983 ms
synthesis retries:    0
stop reason:          end_turn
```

No replay was performed.

#### 7.6f — Quality / latency / token / cost analysis — COMPLETE

Manual comparison against the exact frozen PyPA `Hash-checking Mode` source slice found the seven substantive answer items supported by admitted evidence. This is a single-answer manual supportedness review, not a groundedness benchmark.

The source-supported pip 26.2+ `--no-require-hashes` escape hatch is retained as a quality nuance: it weakens global enforcement and should be treated as an explicit compatibility exception, not the default secure posture.

Observed model cost:

```text
input:        $0.0029381
output:       $0.0027005
model total:  $0.0056386
```

One S3 Vectors query-request component:

```text
$0.0000025
```

Directly computable total:

```text
$0.0056411
```

Titan query embedding and S3 Vectors data-processed/data-returned components remain uncomputed because Bedrock `Retrieve` does not expose the required billable units.

The first structured-output synthesis is not treated as warmed steady-state latency because first-use grammar compilation may contribute to the observed `7217 ms` Bedrock latency.

#### 7.6g — Closeout + merge — IN PROGRESS

Required:

```text
[x] synchronize Gate 7.6 lab/current-state/roadmap/architecture
[ ] final CI green on exact closeout head
[ ] mark PR #99 ready
[ ] squash merge against validated head SHA
```

### Gate 7.7 — Citations + groundedness — NEXT AFTER 7.6 MERGE

Add deterministic citation projection from admitted evidence and measure:

```text
citation correctness
citation coverage
unsupported claims / groundedness
answer supportedness
abstention behavior
```

Model-authored URLs or source IDs must never become citation authority.

### Gate 7.8 — Phase 7 closeout — PLANNED

Review retrieval/synthesis failure diagnosis, least-privilege runtime IAM strategy, retrieval/embedding/vector/synthesis cost split, observability evidence, ADRs, regressions, and phase documentation.

## Future phases

### Phase 8 — Hybrid Retrieval

Combine deterministic structured threat intelligence with semantic retrieval only where evaluation demonstrates value.

### Phase 9 — Public Analyze Your Repository

Expose a bounded public demo only after repository intelligence, risk policy, structured query, and retrieval boundaries are stable.

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
