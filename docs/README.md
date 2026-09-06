# OpsLens Documentation

OpsLens documentation is organized around current architecture, implementation state, incremental roadmap, ADRs, and measured laboratory evidence.

## Primary documents

- [`architecture.md`](architecture.md) — current accumulated architecture baseline through **Phase 7 complete**.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture baseline synchronized with the English version.
- [`current-state.md`](current-state.md) — exact implementation checkpoint and next authorized action.
- [`roadmap.md`](roadmap.md) — incremental phase/gate plan and completion status.
- [`adr/`](adr/) — accepted architecture decisions.
- [`labs/`](labs/) — historical implementation/operational evidence for earlier phases.
- [`../labs/`](../labs/) — current Phase 7 gate evidence and content-addressed review artifacts.

## Current implementation checkpoint

```text
Phase 0  AWS Foundation                         COMPLETE
Phase 1  EPSS Vertical Slice                    COMPLETE
Phase 2  Threat Intelligence Data Lake          COMPLETE
Phase 3  Vulnerability Correlation Engine       COMPLETE
Phase 4  Repository Intelligence                COMPLETE
Phase 5  Risk Prioritization Engine             COMPLETE
Phase 6  Semantic Query Layer                   COMPLETE
Phase 7  Knowledge Retrieval with Bedrock       COMPLETE
Phase 8  Hybrid Retrieval                       NEXT
```

Phase 7 closes with two independently measured baselines:

```text
retrieval quality
 -> knowledge-retrieval-golden:v1
 -> Recall@5 0.875 / MRR 0.5699404761904762

groundedness + citation quality
 -> knowledge-grounding-golden:v1
 -> claim supportedness 0.8461538461538461
 -> citation correctness 0.8461538461538461
 -> abstention precision/recall 1.0 / 1.0
```

The weaker citation-target metrics are preserved intentionally. Gate 7.8 is a closeout and consistency gate, not a prompt-tuning gate.

## Phase 7 architecture records

- [`adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md`](adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md) — customer-managed vector Knowledge Base and S3 Vectors.
- [`adr/0023-bounded-bedrock-knowledge-synthesis.md`](adr/0023-bounded-bedrock-knowledge-synthesis.md) — bounded non-streaming Bedrock knowledge synthesis after deterministic context admission.
- [`adr/0024-phase7-runtime-iam-boundary.md`](adr/0024-phase7-runtime-iam-boundary.md) — future least-privilege application runtime entitlement, intentionally documented before compute exists.

## Phase 7 evidence

- [`../labs/phase-7-gate-7-1-retrieval-contract.md`](../labs/phase-7-gate-7-1-retrieval-contract.md)
- [`../labs/phase-7-gate-7-2-canonical-corpus.md`](../labs/phase-7-gate-7-2-canonical-corpus.md)
- [`../labs/phase-7-gate-7-3-kb-vector-infrastructure.md`](../labs/phase-7-gate-7-3-kb-vector-infrastructure.md)
- [`../labs/phase-7-gate-7-5-retrieval-evaluation.md`](../labs/phase-7-gate-7-5-retrieval-evaluation.md)
- [`../labs/phase-7-gate-7-6-context-synthesis.md`](../labs/phase-7-gate-7-6-context-synthesis.md)
- [`../labs/phase-7-gate-7-7-citations-groundedness.md`](../labs/phase-7-gate-7-7-citations-groundedness.md)
- [`../labs/phase-7-gate-7-8-closeout.md`](../labs/phase-7-gate-7-8-closeout.md)
- [`../labs/evidence/phase-7-gate-7-7-first-run-review-v1.json`](../labs/evidence/phase-7-gate-7-7-first-run-review-v1.json)

## Permanent engineering boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

The model may plan and synthesize within typed, bounded contracts. Deterministic code owns structured truth, evidence admission, authority checks, canonical citations, and evaluation metric computation.

## Documentation update rule

Every material gate should leave behind:

```text
architecture decision / rationale
implementation evidence
success evidence
failure evidence
IAM / trust boundary
observability evidence
cost reasoning
CI evidence
next authorized gate
```

Top-level documents describe the current baseline. Historical detail stays in labs and ADRs so stale gate status does not leak into the current project overview.
