# OpsLens — Phase 7 Handoff

_Phase: 7 — Knowledge Retrieval with Bedrock_
_Date: 2026-09-04_

## Starting point

Phase 6 is complete and merged to `main` through PR #91 at commit:

```text
95db66e278059629ce6572b2950e9cca705c6498
```

Phase 6 created a safe structured-question path with no unrestricted text-to-SQL. Phase 7 must add a separate knowledge/remediation path without weakening that boundary.

## Phase objective

Build a controlled retrieval-augmented generation path for questions whose answers live in explanatory/remediation documentation rather than deterministic structured analytics.

Example target class:

> What remediation guidance does the advisory provide for this vulnerability?

Not a Phase 7 target:

> Which CVEs have EPSS >= 0.7 on a specific date?

That remains a Phase 6 structured query.

## Target architecture

```text
knowledge/remediation question
 -> retrieval request
 -> Bedrock Knowledge Base Retrieve
 -> RetrievedChunk[] + source metadata
 -> deterministic validation/context assembly
 -> Bedrock synthesis
 -> answer + explicit Citation[]
```

## Required permanent decisions

- Not every question is RAG.
- Structured facts remain structured authorities.
- RAG must not become a second truth source for KEV/EPSS/CVSS/applicability.
- Retrieval evidence needs stable provenance and content identity.
- Retrieved content is untrusted input for generation and can contain indirect prompt injection.
- Context, top-k, output tokens, retries, and spend are bounded.
- Final runtime IAM is least privilege and separate from bootstrap/admin access.

## Gates

### Gate 7.1 — Corpus + retrieval contract

Offline only. Freeze:

```text
KnowledgeDocument
RetrievalRequest
RetrievedChunk
RetrievalEvidence
Citation
```

Create a golden dataset of remediation/documentation questions and expected source documents/chunks.

Do not create AWS resources or make paid calls.

### Gate 7.2 — Reproducible canonical corpus

Content-addressed document normalization and manifest, with exact source text and provenance.

### Gate 7.3 — Knowledge Base + vector infrastructure

Revalidate current official AWS docs first. Select embedding model, vector store, chunking, metadata strategy, IAM, and cost model. S3 Vectors is a candidate, not a pre-approved conclusion.

### Gate 7.4 — Real bounded Retrieve adapter

Use retrieval independently of generation, typed evidence, bounded results, and fail-closed validation.

### Gate 7.5 — Retrieval evaluation

Measure Recall@K, MRR/equivalent, provenance correctness, latency, and cost.

### Gate 7.6 — Context assembly + synthesis

Deterministic admitted context plus bounded Bedrock synthesis.

### Gate 7.7 — Citations + groundedness

Explicit citations, citation correctness/coverage, groundedness, and unsupported-claim evaluation.

### Gate 7.8 — Closeout

Meaningful real failure, observability, cost, IAM review, docs/ADR, regression CI, PR, squash merge.

## First implementation step

Gate 7.1 only:

1. inspect existing repository architecture and naming conventions;
2. define typed offline retrieval/domain contracts;
3. define canonical metadata allowlist and validation rules;
4. build a small golden retrieval fixture;
5. test success and malformed-provenance failure paths;
6. no AWS resource creation yet.

## Security threats to address during Phase 7

- indirect prompt injection in retrieved documents;
- poisoned or wrong-source corpus entries;
- metadata spoofing;
- context overflow;
- retrieval of stale/incorrect versions;
- citation laundering;
- unsupported model claims;
- excessive top-k or repeated model calls;
- credential exposure;
- denial-of-wallet.

## AIP-C01 focus

RAG, embeddings, Knowledge Bases, vector retrieval, chunking, metadata filters, Retrieve vs RetrieveAndGenerate, citations, IAM service roles, retrieval metrics, groundedness, troubleshooting, token/cost optimization.

## Exit criteria

Phase 7 is complete only when retrieval is independently measurable, generation is bounded and grounded in admitted evidence, citations are explicit/evaluated, failures are diagnosable, costs are measured, and the structured-fact authority boundary remains intact.
