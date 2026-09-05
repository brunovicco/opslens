# OpsLens Documentation

OpsLens documentation is organized around implemented architecture, current state, incremental roadmap, labs, and ADRs.

## Primary documents

- [`architecture.md`](architecture.md) — accumulated architecture baseline through Phase 7 Gate 7.3.
- [`current-state.md`](current-state.md) — current implementation checkpoint and next action.
- [`roadmap.md`](roadmap.md) — incremental phase/gate plan and completion status.
- [`adr/`](adr/) — architecture decision records.

## Current implementation checkpoint

```text
Phase 0  AWS Foundation                         COMPLETE
Phase 1  EPSS Vertical Slice                    COMPLETE
Phase 2  Threat Intelligence Data Lake          COMPLETE
Phase 3  Vulnerability Correlation Engine       COMPLETE
Phase 4  Repository Intelligence                COMPLETE
Phase 5  Risk Prioritization Engine             COMPLETE
Phase 6  Semantic Query Layer                   COMPLETE
Phase 7  Knowledge Retrieval with Bedrock       IN PROGRESS
  7.1 Corpus + retrieval contract               COMPLETE
  7.2 Reproducible canonical corpus             COMPLETE
  7.3 Knowledge Base + vector infrastructure    COMPLETE / PR #95 MERGE PENDING
  7.4 Real bounded Retrieve adapter             NEXT
```

Gate 7.3 validates a real customer-managed Amazon Bedrock vector Knowledge Base backed by Amazon S3 Vectors, Titan Text Embeddings V2, deterministic pre-split corpus publication, bounded ingestion, least-privilege service-role separation, and exactly nine materialized vectors.

## Phase 7 evidence

- [`../labs/phase-7-gate-7-1-retrieval-contract.md`](../labs/phase-7-gate-7-1-retrieval-contract.md)
- [`../labs/phase-7-gate-7-2-canonical-corpus.md`](../labs/phase-7-gate-7-2-canonical-corpus.md)
- [`../labs/phase-7-gate-7-3-kb-vector-infrastructure.md`](../labs/phase-7-gate-7-3-kb-vector-infrastructure.md)

## Current Phase 7 ADR

- [`adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md`](adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md)

## Permanent engineering boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

## Documentation update rule

Every material gate should leave behind:

```text
architecture decision / rationale
implementation evidence
success evidence
failure evidence
IAM/trust boundary
observability evidence
cost reasoning
CI evidence
next authorized gate
```

Detailed historical implementation evidence lives in `labs/` and ADRs rather than being duplicated in every top-level document.
