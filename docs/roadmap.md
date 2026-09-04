# OpsLens — Incremental Roadmap

_Last updated: 2026-09-04_

OpsLens advances in small, demonstrable, observable, and reversible gates.

Default loop:

```text
concept
 -> architecture decision
 -> IAM/trust boundary when applicable
 -> implementation
 -> success test
 -> meaningful failure test
 -> observability
 -> cost
 -> documentation/ADR
 -> logical commit
```

## Phase status

| Phase | Scope | Status |
|---|---|---|
| 0 | AWS Foundation | ✅ Complete |
| 1 | EPSS Vertical Slice | ✅ Complete |
| 2 | Threat Intelligence Data Lake | ✅ Complete |
| 3 | Vulnerability Correlation Engine | ✅ Complete |
| 4 | Repository Intelligence | ✅ Complete |
| 5 | Risk Prioritization Engine | ✅ Complete |
| 6 | Semantic Query Layer | ✅ Complete — PR #91 / `95db66e...` |
| 7 | Knowledge Retrieval with Bedrock | ▶️ Next |
| 8 | Hybrid Retrieval | ⏳ Planned |
| 9 | Public Analyze Your Repository | ⏳ Planned |
| 10 | Observability & Operational Excellence | ⏳ Planned |
| 11 | Single-Agent Baseline | ⏳ Planned |
| 12 | Multi-Agent Architecture | ⏳ Planned |
| 13 | MCP | ⏳ Planned |
| 14 | AgentCore / governed model-runtime integration | ⏳ Planned |
| 15 | A2A | ⏳ Planned |
| 16 | Runtime Exposure with Amazon Inspector | ⏳ Planned |
| 17 | Security Hardening | ⏳ Planned |
| 18 | Evaluation, Cost & Portfolio Readiness | ⏳ Planned |

## Phase 6 — Semantic Query Layer — COMPLETE

Permanent guardrail:

> **No unrestricted text-to-SQL.**

Completed flow:

```text
User question
 -> bounded Bedrock planner
 -> deterministic planner-output parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded Athena executor
```

Phase 6 proved both a real supported E2E call and a real fail-closed path with `athena_invoked=false`. Final deployed-runtime IAM is deferred until a deployed runtime identity exists.

## Phase 7 — Knowledge Retrieval with Bedrock

### Goal

Add a controlled RAG/knowledge path for remediation and explanatory questions while keeping structured factual questions on the Phase 6 Athena path.

Permanent Phase 7 rule:

> **Not every question is RAG. Structured facts remain structured.**

### Target flow

```text
knowledge/remediation question
 -> bounded retrieval request
 -> Bedrock Knowledge Base Retrieve
 -> typed RetrievedChunk[] + provenance
 -> deterministic admission/context assembly
 -> bounded Bedrock synthesis
 -> answer + explicit citations
```

### Gate 7.1 — Corpus + retrieval contract — OFFLINE FIRST

Freeze typed contracts before AWS infrastructure:

```text
KnowledgeDocument
RetrievalRequest
RetrievedChunk
RetrievalEvidence
Citation
```

Create a small golden dataset of remediation/documentation questions with expected source documents/chunks.

Exit criteria:

- corpus purpose and authority boundary documented;
- required metadata allowlist frozen;
- retrieval request/result types frozen;
- malformed/missing provenance fails closed;
- golden retrieval fixture exists;
- no AWS resources or paid calls required.

### Gate 7.2 — Reproducible canonical corpus

- source documents acquired through bounded, trusted paths;
- exact source text preserved;
- canonical normalized document representation;
- `content_sha256` and stable source identity;
- deterministic corpus manifest;
- no third-party code execution.

### Gate 7.3 — Knowledge Base + vector infrastructure

After revalidating current AWS documentation:

- select embedding model;
- select vector store/index strategy;
- select chunking strategy;
- provision least-privilege Knowledge Base service role;
- provision only required storage/index resources;
- document pricing drivers and limits.

A current candidate is Bedrock Knowledge Bases with S3-backed corpus and S3 Vectors, but this is not frozen until current official AWS support, limits, IAM, and pricing are verified.

### Gate 7.4 — Real bounded Retrieve adapter

- use `Retrieve` so retrieval remains separately testable;
- typed retrieval evidence;
- bounded `top_k`/result count;
- metadata/source validation;
- no generation yet;
- intentional failure path.

### Gate 7.5 — Retrieval evaluation

Measure at minimum:

- Recall@K;
- MRR or equivalent;
- source/metadata correctness;
- retrieval latency;
- query/index cost evidence.

Compare chunking/retrieval alternatives only from measured results.

### Gate 7.6 — Context assembly + Bedrock synthesis

- deterministic context selection/formatting;
- bounded context size and output tokens;
- no unsupported source injection;
- synthesis cannot mutate deterministic facts;
- token, latency, model, and request evidence recorded.

### Gate 7.7 — Citations + groundedness evaluation

- explicit citations to retrieved evidence;
- citation coverage/correctness;
- groundedness evaluation;
- unsupported-claim detection;
- failure when citations/evidence are insufficient.

### Gate 7.8 — Failure, cost, observability, closeout

- at least one meaningful real failure diagnosed;
- retrieval and generation costs measured separately;
- logs/metrics/traces sufficient to localize failures;
- IAM reviewed for least privilege;
- ADR for `Retrieve` + custom synthesis if this remains the selected design;
- current state/architecture/roadmap updated;
- targeted and regression CI green;
- logical PR + squash merge.

### Phase 7 exit criteria

- reproducible content-addressed corpus;
- retrieval independently testable;
- real Bedrock retrieval evidence;
- objective retrieval quality metrics;
- bounded generation over admitted context;
- explicit citations;
- groundedness/citation evaluation;
- intentional failure diagnosed;
- cost and observability evidence;
- no competing RAG authority for structured facts.

Do not add hybrid search, agents, MCP, AgentCore, A2A, Inspector, or broad public API work to Phase 7 unless a concrete dependency requires an explicit architectural decision.
