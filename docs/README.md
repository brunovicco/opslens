# OpsLens Documentation

OpsLens documentation is organized around current architecture, implementation state, incremental roadmap, ADRs, and measured laboratory evidence.

## Primary documents

- [`architecture.md`](architecture.md) — accumulated architecture baseline through **Phase 8 — Hybrid Retrieval**.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture baseline synchronized with the English version.
- [`current-state.md`](current-state.md) — exact implementation checkpoint and next authorized action.
- [`roadmap.md`](roadmap.md) — incremental phase/gate plan and completion status.
- [`adr/`](adr/) — accepted architecture decisions.
- [`../labs/`](../labs/) — gate laboratories and immutable evidence references.

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
Phase 8  Hybrid Retrieval                       COMPLETE
Phase 9  Public Analyze Your Repository         NEXT
```

Phase 8 adds deterministic evidence-class routing and completeness without weakening the structured/semantic authority split.

## Frozen Phase 8 evaluation

```text
hybrid-evaluation-golden:v1
sha256: 68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Independent dimensions:

```text
route_accuracy
structured_fact_correctness
semantic_groundedness
citation_correctness
abstention
latency
cost
```

No composite score exists.

Gate 8.4 first complete real Bedrock baseline:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

Gate 8.5 measured `H8.5-01` exactly once. The prompt-only candidate preserved deterministic guardrails but left semantic groundedness and citation correctness at `2/3`, so the predeclared decision was `REJECT`. The Gate 8.4 prompt remains the runtime default.

## Phase 8 architecture records

- [`adr/0025-deterministic-hybrid-routing-authority.md`](adr/0025-deterministic-hybrid-routing-authority.md) — deterministic `STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED` route authority.
- [`adr/0026-deterministic-hybrid-evidence-envelope.md`](adr/0026-deterministic-hybrid-evidence-envelope.md) — authority-separated structured/semantic evidence envelope and completeness.
- [`adr/0027-frozen-hybrid-evaluation-contract.md`](adr/0027-frozen-hybrid-evaluation-contract.md) — six-case evaluation fixture and independent metrics frozen before synthesis.
- [`adr/0028-bounded-route-aware-hybrid-synthesis.md`](adr/0028-bounded-route-aware-hybrid-synthesis.md) — bounded synthesis behind deterministic hybrid route/evidence authority.

## Phase 8 evidence

- [`../labs/phase-8-gate-8-4-bounded-hybrid-synthesis.md`](../labs/phase-8-gate-8-4-bounded-hybrid-synthesis.md) — first route-aware synthesis and real baseline history.
- [`../labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json`](../labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json) — immutable Gate 8.4 real Bedrock baseline.
- [`../labs/phase-8-gate-8-5-measured-optimization.md`](../labs/phase-8-gate-8-5-measured-optimization.md) — H8.5-01 hypothesis, single-run rule, and measured REJECT decision.
- [`../labs/evidence/phase-8-gate-8-5-h85-01-first-run-v1.json`](../labs/evidence/phase-8-gate-8-5-h85-01-first-run-v1.json) — immutable H8.5-01 runtime evidence.
- [`../labs/phase-8-gate-8-6-closeout.md`](../labs/phase-8-gate-8-6-closeout.md) — Phase 8 architecture/evaluation/IAM/cost/observability closeout and Phase 9 entry boundary.

## Phase 7 architecture records

- [`adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md`](adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md) — customer-managed vector Knowledge Base and S3 Vectors.
- [`adr/0023-bounded-bedrock-knowledge-synthesis.md`](adr/0023-bounded-bedrock-knowledge-synthesis.md) — bounded non-streaming Bedrock knowledge synthesis after deterministic context admission.
- [`adr/0024-phase7-runtime-iam-boundary.md`](adr/0024-phase7-runtime-iam-boundary.md) — future least-privilege application runtime entitlement, intentionally documented before compute exists.

Phase 7 detailed evidence remains available in `../labs/phase-7-gate-7-*` and is not rewritten by the Phase 8 closeout.

## Permanent engineering boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

The model may plan and synthesize inside typed, bounded contracts. Deterministic code owns structured truth, route authority, required-evidence completeness, evidence admission, canonical citations, output admission, and evaluation metric computation.

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
