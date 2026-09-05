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
| 6 | Semantic Query Layer | ✅ Complete — PR #91 / `95db66e` |
| 7 | Knowledge Retrieval with Bedrock | 🚧 Gate 7.1 complete; Gate 7.2 complete / PR #94 merge pending |
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

Established the real `dev` environment, Terraform remote state, IAM Identity Center human access, GitHub Actions OIDC deployment identity, budget/cost controls, CloudWatch, X-Ray, and intentional failure-path validation.

### Phase 1 — EPSS Vertical Slice

Implemented the first complete threat-intelligence path:

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

Completed deterministic PyPI v1 applicability:

```text
package/version/purl
 + GHSA range evidence
 -> PEP 440 applicability
 -> affected | not_affected | unsupported
 -> CVE/GHSA/NVD reconciliation
 -> content-addressed correlation record
```

Permanent rule:

> No LLM decides vulnerability applicability.

### Phase 4 — Repository Intelligence

Completed the read-only public GitHub repository slice:

```text
public GitHub repository
 -> immutable commit snapshot
 -> bounded GET-only acquisition
 -> exact inert uv.lock
 -> deterministic parser
 -> Phase 3 correlation
 -> NVD/CVSS + KEV + EPSS evidence
 -> RepositoryAnalysisResult
```

Repository code is never executed, and repository risk is not claimed as runtime exposure.

### Phase 5 — Risk Prioritization Engine

Completed deterministic Risk Policy v1:

```text
KEV present                         +40
EPSS >= 0.70 / 0.30 / 0.10          +30 / +20 / +10
max supported CVSS >= 9 / 7 / 4     +20 / +10 / +5
known fixed version                 +10
```

Priority tiers:

```text
P0 >= 80
P1 >= 60
P2 >= 30
P3 < 30
```

Missing evidence remains `partial` / `review_required`; it does not silently become a confident low-risk result.

## Phase 6 — Semantic Query Layer — COMPLETE

### Goal

Convert bounded natural-language factual questions into a typed semantic query and deterministic Athena SQL without giving a model unrestricted SQL authority.

Target flow:

```text
User question
 -> bounded Bedrock planner
 -> structured planner proposal
 -> deterministic planner-output parser
 -> typed SemanticQuery
 -> deterministic validator
 -> deterministic SQL compiler
 -> exact compiler-shape admission
 -> bounded read-only Athena workgroup
 -> structured result evidence
```

Permanent guardrail:

> **No unrestricted text-to-SQL.**

### Gate 6.1 — Typed semantic-query contract + deterministic compiler — COMPLETE

First supported slice:

> Which CVEs have EPSS of at least 0.7 on an explicit snapshot date?

Contract:

```text
metric:          epss_score
dimension:       cve
snapshot_date:   required explicit date
minimum_score:   optional 0.0..1.0
order:           epss_score ASC|DESC + cve ASC tie break
limit:           1..100, default 20
```

Only deterministic application code owns database/table/columns/predicates/order/LIMIT.

ADR: [`adr/0020-no-unrestricted-text-to-sql.md`](adr/0020-no-unrestricted-text-to-sql.md).

### Gate 6.2 — Bounded read-only Athena execution — COMPLETE

Real dev boundary:

```text
database:    opslens_dev
workgroup:   opslens-dev
relation:    "opslens_dev"."epss_scores"
scan cutoff: 10 MiB enforced by workgroup
```

Real success evidence:

```text
query_execution_id:         958fb573-1a69-4ce6-8a36-d9be45e71c79
row_count:                  20
data_scanned_bytes:         3,785,003 (~3.61 MiB)
engine_execution_time_ms:   973
total_execution_time_ms:    1,128
```

Intentional `limit=101` fails before Athena.

Closeout: [`../labs/phase-6-gate-6-2-athena-readonly-execution.md`](../labs/phase-6-gate-6-2-athena-readonly-execution.md).

### Gate 6.3 — Bounded planner contract + offline evaluation — COMPLETE

Frozen planner authority:

```text
input length:      <= 1,000 chars
decisions:         semantic_query | unsupported
metric:            epss_score
dimensions:        exactly [cve]
snapshot_date:     explicit YYYY-MM-DD
minimum_score:     null or inclusive >= threshold
order:             epss_score asc|desc
limit:             1..100
SQL field:         none
```

The deterministic parser rejects malformed/extra/missing fields, unsupported semantics, invalid values, relative/missing dates, and SQL injection attempts before rebuilding `SemanticQuery`.

Golden offline evaluation:

```text
18 total cases
  8 supported
 10 fail-closed unsupported
```

ADR: [`adr/0021-bounded-bedrock-semantic-query-planner.md`](adr/0021-bounded-bedrock-semantic-query-planner.md).

Closeout: [`../labs/phase-6-gate-6-3-planner-contract-evaluation.md`](../labs/phase-6-gate-6-3-planner-contract-evaluation.md).

### Gate 6.4 — Real Bedrock planner invocation — COMPLETE

Selected runtime boundary:

```text
model_id:       us.anthropic.claude-haiku-4-5-20251001-v1:0
client Region:  us-east-1
inference mode: US Geographic system-defined inference profile
streaming:      disabled
tools:          disabled
temperature:    0.0
maxTokens:      256
```

Implemented code:

```text
BedrockPlannerInvocationEvidence
BedrockPlannerResult
BedrockConverseClient Protocol
BedrockSemanticPlanner
ExecuteNaturalLanguageSemanticQuery
scripts/run_natural_language_semantic_query.py
```

Real supported versioned E2E evidence on 2026-09-04:

```text
question:                       Which CVEs have EPSS of at least 0.7 on 2026-09-03?
decision:                       semantic_query
input/output/total:             942 / 79 / 1021 tokens
Bedrock latency:                1,632 ms
client elapsed:                 2,894 ms
retries:                        0
estimated planner cost:         ~$0.00147
Athena query_execution_id:      09a32501-a06c-4437-809c-ebcaf350cd1d
Athena rows:                    20
Athena data scanned:            3,785,003 bytes (~3.61 MiB)
Athena engine/total:            994 / 1,192 ms
```

Real fail-closed evidence also proved a missing explicit snapshot date stops before Athena. A local IAM Identity Center token-expiry failure was separately diagnosed before service invocation.

Closeout: [`../labs/phase-6-gate-6-4-real-bedrock-planner.md`](../labs/phase-6-gate-6-4-real-bedrock-planner.md).

### Phase 6 exit state

- [x] typed `SemanticQuery` contract;
- [x] explicit metric/dimension/filter allowlists;
- [x] invalid/unknown semantics fail closed;
- [x] deterministic SQL only;
- [x] bounded read-only Athena for the supported slice;
- [x] planner evaluation set with field-level metrics;
- [x] real bounded Bedrock invocation;
- [x] typed runtime invocation evidence;
- [x] real model/API/token/latency/cost evidence;
- [x] versioned natural-language question through model + parser + compiler + Athena;
- [x] versioned intentional semantic failure with `athena_invoked=false`;
- [x] diagnosable local authentication failure;
- [x] ADR rejecting unrestricted text-to-SQL;
- [x] ADR defining bounded planner authority;
- [x] final validation + green CI + PR #91 + squash merge;
- [deferred] final deployed runtime IAM least privilege until a runtime identity exists.

The local bootstrap/admin Identity Center profile is lab validation only and does not satisfy the future deployed-runtime IAM criterion.

## Phase 7 — Knowledge Retrieval with Bedrock — IN PROGRESS

### Goal

Create a separately testable RAG path for explanatory/remediation knowledge without replacing the structured Phase 6 path.

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

Structured NVD, CISA KEV, FIRST EPSS, CVSS, GHSA applicability, repository-version, and Risk Policy evidence remain outside the RAG authority boundary.

### Gate 7.1 — Corpus + retrieval contract — COMPLETE

Gate 7.1 remained offline-first and froze provider-independent contracts and evaluation fixtures before any AWS retrieval resource exists.

Frozen contract:

```text
KnowledgeDocument
RetrievalRequest
RetrievedChunk
RetrievalEvidence
Citation
```

Frozen v1 bounds:

```text
query:         <= 1,000 chars
top_k:         1..10
default top_k: 5
provider DSL:  none
```

Canonical metadata is allowlisted independently of any future AWS projection. Exact document/chunk SHA-256 identities and HTTPS provenance are validated. Retrieval ranks must be contiguous, chunk IDs unique, and returned chunks cannot exceed `request.top_k`.

Citation provenance is projected from admitted chunks rather than authored by a model.

Golden fixture:

```text
10 cases
  8 positive remediation/documentation cases
  2 negative/out-of-scope cases
prepared metrics: Recall@K + MRR
corpus status at Gate 7.1 freeze: planned_for_gate_7_2
```

Final functional validation:

```text
workflow: Python CI
run:      33931113097
commit:   f882f5df12f20f68b2601bf525a625fe72a36b7b

Knowledge Retrieval Ruff:     PASS
Knowledge Retrieval Pyright:  0 errors / 0 warnings
Knowledge Retrieval pytest:   14 passed in 0.08s

Correlation regression:              PASS
Repository Intelligence regression:  PASS
Risk Policy regression:              PASS
Semantic Query regression:           PASS
```

No Knowledge Base, vector store/index, embedding job, IAM role, retrieval call, synthesis call, or other paid AWS resource/call was introduced.

Closeout: [`../labs/phase-7-gate-7-1-retrieval-contract.md`](../labs/phase-7-gate-7-1-retrieval-contract.md).

Gate 7.1 was squash-merged through PR #93 at `f2e3b72c31d0713707857bc0867a7f59e667b9dd`.

### Gate 7.2 — Reproducible canonical corpus — COMPLETE / MERGE PENDING

Gate 7.2 converts the frozen document/chunk identities into a real reproducible corpus before any vector service exists.

Implemented scope:

- six explicitly authorized official documentation/security/advisory source files;
- full immutable upstream Git commit pins;
- separate human-facing provenance and acquisition authority;
- bounded GET-only acquisition from derived `raw.githubusercontent.com` paths;
- strict UTF-8 and deterministic LF normalization;
- exact line-aligned section selection with ambiguity/drift fail-closed semantics;
- provider-independent canonical document/chunk identities;
- deterministic source/document/chunk SHA-256 evidence;
- hash-only manifest with no vendored third-party text;
- serial bounded replay pipeline;
- explicit `--write` and exact `--check` modes;
- scoped offline tests and real local replay evidence.

Real corpus shape:

```text
documents: 6
chunks:    9
manifest:  knowledge/corpus/v1/manifest.json
sha256:    98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

The first real replay detected an ambiguous PyPA `Version specifiers` selector and failed closed. Inspection of the exact pinned source showed two headings with that name. The selector was made more specific; uniqueness validation was preserved rather than relaxed.

Final manifest CI:

```text
workflow: Python CI
run:      33965739749
commit:   bb61f6766f9c52c167ac7d1a3a8bc734cd1a6307

Knowledge Retrieval Ruff:     PASS
Knowledge Retrieval Pyright:  0 errors / 0 warnings / 0 informations
Knowledge Retrieval pytest:   44 passed in 0.25s

Correlation regression:              PASS
Repository Intelligence regression:  PASS
Risk Policy regression:              PASS
Semantic Query regression:           PASS
```

No AWS resource, Knowledge Base, vector index, embedding job, IAM role, retrieval call, synthesis call, or paid AWS call was introduced by Gate 7.2.

Closeout: [`../labs/phase-7-gate-7-2-canonical-corpus.md`](../labs/phase-7-gate-7-2-canonical-corpus.md).

### Gate 7.3 — Knowledge Base + vector infrastructure — NEXT AFTER PR #94 MERGE

Gate 7.3 must begin with fresh architecture research against current official AWS documentation before any resource is selected or created.

Decide using current official AWS documentation and measured needs:

- Bedrock Managed Knowledge Base vs customer-managed configuration;
- embedding model and dimensions;
- vector store such as S3 Vectors or OpenSearch Serverless;
- chunking strategy and compatibility with the deterministic canonical chunks;
- metadata projection and provenance limits;
- Knowledge Base service role vs OpsLens retrieval runtime identity;
- IAM/trust boundaries and least privilege;
- pricing, idle cost, ingestion cost, retrieval cost, and operational complexity;
- observability, throttling, quotas, failure behavior, backup/rebuild implications.

Do not select an AWS service merely because it appears in AIP-C01.

Do not create Gate 7.3 resources until Gate 7.2 is squash-merged and the architecture decision is documented.

### Gate 7.4 — Real bounded Retrieve adapter — PLANNED

Implement `Retrieve` first, independently from generation, with:

- bounded `top_k`;
- typed Bedrock adapter boundary;
- explicit provenance admission;
- stable provider-error wrapping;
- intentional failure evidence;
- no `RetrieveAndGenerate` shortcut for the v1 evaluation path.

### Gate 7.5 — Retrieval evaluation — PLANNED

Measure retrieval separately from synthesis using the frozen golden dataset:

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

Only admitted retrieved chunks may enter model context. Freeze context/token limits, model authority, output contract, runtime evidence, and denial-of-wallet controls before real synthesis is treated as complete.

### Gate 7.7 — Citations + groundedness — PLANNED

Require explicit citations mapped deterministically to admitted evidence and measure citation correctness/coverage plus unsupported claims/groundedness.

### Gate 7.8 — Closeout — PLANNED

Require:

- retrieval + synthesis failure diagnosis;
- IAM least-privilege review;
- retrieval/embedding/vector/synthesis cost split;
- observability evidence;
- ADRs for material architecture decisions;
- targeted and regression tests;
- documentation;
- PR + green CI + logical merge.

## Future phases

### Phase 8 — Hybrid Retrieval

Combine deterministic structured threat intelligence with semantic retrieval, preferably using validated CVE/GHSA/package evidence to scope knowledge retrieval first.

### Phase 9 — Public Analyze Your Repository

Expose a bounded public demo only after repository intelligence, risk policy, structured query, and retrieval boundaries are stable.

### Phase 10 — Observability & Operational Excellence

Make the end-to-end system diagnosable through stage latency, errors, throttling, queue/DLQ state, Athena bytes, model tokens/latency, retrieval latency, and estimated investigation cost.

### Phase 11 — Single-Agent Baseline

Build one bounded agent over existing deterministic tools before introducing multi-agent complexity. Measure quality, latency, cost, tool calls, and failure modes.

### Phase 12 — Multi-Agent Architecture

Introduce specialization only where it demonstrably improves the single-agent baseline.

### Phase 13 — MCP

Expose controlled OpsLens capabilities through typed, authorized, observable MCP tools with allowlists and prompt/tool-injection tests.

### Phase 14 — Amazon Bedrock AgentCore

Evaluate/adopt AgentCore only after a working bounded agent baseline exists and there is a concrete need for runtime, gateway, identity, memory, or observability capabilities.

### Phase 15 — A2A

Introduce agent-to-agent interoperability only after internal agent contracts and authority boundaries are stable.

### Phase 16 — Runtime Exposure with Amazon Inspector

Add deployed-runtime/package evidence so OpsLens can distinguish repository risk from real runtime exposure rather than infer one from the other.

### Phase 17 — Security Hardening

Expand identity, authorization, abuse-case, data-handling, supply-chain, prompt/tool-injection, red-team, and denial-of-wallet controls.

### Phase 18 — Evaluation, Cost & Portfolio Readiness

Close the program with reproducible evaluation, measured cost, architecture/runbooks, portfolio documentation, and explicit evidence for deterministic, retrieval, and agentic trade-offs.
