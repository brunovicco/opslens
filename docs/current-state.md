# OpsLens — Current State

_Last updated: 2026-09-06_

This document is the public implementation checkpoint for the OpsLens repository.

## Status

```text
Phase 0    AWS Foundation                                      COMPLETE
Phase 1    EPSS Vertical Slice                                 COMPLETE
Phase 2    Threat Intelligence Data Lake                       COMPLETE
Phase 3    Vulnerability Correlation Engine                    COMPLETE
Phase 4    Repository Intelligence                             COMPLETE
Phase 5    Risk Prioritization Engine                          COMPLETE
Phase 6    Semantic Query Layer                                COMPLETE
  Gate 6.1 Typed contract + deterministic SQL compiler         COMPLETE
  Gate 6.2 Bounded read-only Athena execution                  COMPLETE
  Gate 6.3 Bounded planner contract + offline evaluation       COMPLETE
  Gate 6.4 Real Bedrock planner invocation                     COMPLETE
Phase 7    Knowledge Retrieval with Bedrock                    IN PROGRESS
  Gate 7.1 Corpus + retrieval contract                         COMPLETE
  Gate 7.2 Reproducible canonical corpus                       COMPLETE
  Gate 7.3 Knowledge Base + vector infrastructure              COMPLETE / MERGED
  Gate 7.4 Real bounded Retrieve adapter                       COMPLETE / MERGE PENDING
  Gate 7.5 Retrieval evaluation                                NEXT
```

Recent logical merges:

```text
Phase 6 / PR #91
95db66e278059629ce6572b2950e9cca705c6498

Gate 7.1 / PR #93
f2e3b72c31d0713707857bc0867a7f59e667b9dd

Gate 7.2 / PR #94
manifest sha256: 98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418

Gate 7.3 / PR #95
1337950ddb5948943bf361dba4c3cdc40dafaf2b
```

Gate 7.4 is complete on PR #97 and awaits final green closeout + squash merge.

## Permanent boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

Deterministic authorities own package normalization, vulnerable-range matching, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS evidence, Risk Policy, canonical corpus construction, semantic-query validation/SQL compilation, retrieval evidence admission, citation projection, and execution/tool/cost enforcement.

LLMs may classify, plan, synthesize, explain, and route over validated evidence. They do not replace deterministic structured truth.

## Implemented stack

```text
1. Threat Intelligence Data Lake
   NVD / CISA KEV / FIRST EPSS / GitHub Security Advisories

2. Vulnerability Correlation Engine
   PyPI identity / PEP 440 applicability / GHSA / CVE-NVD evidence

3. Repository Intelligence
   immutable public GitHub snapshot / inert uv.lock / no code execution

4. Risk Prioritization Engine
   deterministic Risk Policy v1 / factor explanations / ranking

5. Semantic Query Layer
   bounded Bedrock planner / typed SemanticQuery / deterministic SQL /
   bounded read-only Athena

6. Canonical Knowledge Corpus
   immutable official pins / bounded inert-text acquisition /
   deterministic normalization + selection / hash-only manifest

7. Bedrock Knowledge Base Vector Baseline
   deterministic S3 publication / Titan Text Embeddings V2 /
   S3 Vectors / bounded ingestion / nine real vectors

8. Real Bounded Retrieval
   direct Bedrock Knowledge Base Retrieve / strict provider parser /
   checked-corpus reconciliation / content/hash admission /
   content-free operational evidence
```

## Phase 6 — Semantic Query Layer — COMPLETE

Target path:

```text
natural-language factual question
 -> bounded Bedrock planner
 -> structured planner proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured result evidence
```

The planner has no unrestricted SQL authority.

Real Gate 6.4 supported evidence:

```text
question:                     Which CVEs have EPSS of at least 0.7 on 2026-09-03?
planner decision:             semantic_query
model input/output/total:     942 / 79 / 1021 tokens
Bedrock latency:              1,632 ms
client elapsed:               2,894 ms
estimated planner cost:       ~$0.00147
Athena rows:                  20
Athena data scanned:          3,785,003 bytes (~3.61 MiB)
Athena total time:            1,192 ms
```

A missing explicit snapshot date returns `unsupported` and never invokes Athena.

## Phase 7 — Knowledge Retrieval with Bedrock — IN PROGRESS

Phase 7 is a separate explanatory/remediation path. It does not duplicate or replace NVD, KEV, EPSS, CVSS, GHSA applicability, repository-version, or Risk Policy authority.

Target path:

```text
knowledge/remediation question
 -> bounded RetrievalRequest
 -> Bedrock Knowledge Base Retrieve
 -> typed RetrievedChunk[] + provenance
 -> deterministic validation/context admission
 -> bounded Bedrock synthesis
 -> answer + deterministic citations
```

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

Citations are projected deterministically from admitted evidence rather than model-authored URLs/source IDs.

### Gate 7.2 — Reproducible canonical corpus — COMPLETE

```text
6 official immutable source pins
9 canonical chunks
manifest sha256:
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

Acquisition is bounded GET-only inert text. Third-party source/chunk text is not vendored into Git and no third-party code is executed.

### Gate 7.3 — Knowledge Base + vector infrastructure — COMPLETE / MERGED

Merged through PR #95:

```text
commit: 1337950ddb5948943bf361dba4c3cdc40dafaf2b
```

Validated real configuration:

```text
knowledge base id:     BTVJ2PBR2A
data source id:        IEL1LBE026
source prefix:         knowledge/corpus/v1/bedrock/
chunking:              NONE
embedding model:       amazon.titan-embed-text-v2:0
embedding dimensions:  1024
embedding data type:   FLOAT32
vector store:          Amazon S3 Vectors
distance:              cosine
```

Real publication:

```text
18 verified S3 objects
9 canonical text objects
9 metadata sidecars
14,928 total bytes
394..493 bytes per compact sidecar
```

The first ingestion exposed the Bedrock/S3 Vectors 1024-byte associated-metadata limit. The deterministic publisher was fixed to validate final serialized sidecar bytes; no KB/vector resource or IAM role was broadened.

Successful ingestion:

```text
job:                           WZRUGOFZPI
status:                        COMPLETE
observed duration:             11.145552 s
documents scanned:             9
new documents indexed:         9
documents failed:              0
documents skipped:             0
vectors materialized:          9
```

A strongly consistent S3 Vectors listing returned exactly nine vectors.

Real failure evidence retained:

```text
oversized metadata sidecars -> all nine ignored, zero vectors
botocore SSO path           -> TokenRetrievalError categorized safely
human AssumeRole on KB role -> AccessDenied as expected
```

Closeout: [`../labs/phase-7-gate-7-3-kb-vector-infrastructure.md`](../labs/phase-7-gate-7-3-kb-vector-infrastructure.md).

ADR: [`adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md`](adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md).

### Gate 7.4 — Real bounded Retrieve adapter — COMPLETE / MERGE PENDING

Gate 7.4 uses direct `bedrock-agent-runtime:Retrieve`, not `RetrieveAndGenerate`, so retrieval remains independently measurable before synthesis.

Runtime authority:

```text
RetrievalRequest
 -> exact configured KB
 -> direct semantic Retrieve
 -> strict provider response parser
 -> exact S3 content-addressed key reconciliation
 -> independent text SHA-256 + byte-count validation
 -> canonical metadata comparison
 -> RetrievedChunk[]
 -> RetrievalEvidence
```

Provider metadata does not define canonical chunk/source identity. The checked Gate 7.2 manifest remains authoritative.

The first real provider response exposed `section_path` values as JSON-quoted strings inside a list. The adapter initially failed closed, a metadata-only diagnostic proved the exact shape, and normalization was added only for valid JSON-quoted string elements that decode to the exact checked manifest values. Malformed or mismatching values remain rejected.

Real admitted retrieval:

```text
knowledge base:         BTVJ2PBR2A
query sha256:           5b398fe871d0cb51eaacb4f42a11b2ec402b5fdb4c523d2b7bca85e84dff3d0d
requested top_k:        5
returned/admitted:      5
provider request id:    e92d67f1-18fa-4537-8ff4-c2e02ab813e0
client elapsed:         1257 ms
SDK retries:            0
rank 1:                 knowledge-chunk:pypa-secure-installs:hashes:v1
rank 1 score:           0.8649594783782959
```

All five returned chunks passed deterministic location, hash, byte-count, metadata, and provenance admission.

Intentional real negative control:

```text
nonexistent KB id: ZZZZZZZZZZ
result: ERROR: Bedrock Retrieve failed provider_code=ResourceNotFoundException
```

The failure was read-only and emitted only a safe provider code.

Retrieval runtime IAM is deliberately separate from ingestion/vector-write authority. No deployed application runtime principal exists yet, so final least-privilege role attachment is deferred until a real compute principal exists rather than creating dead IAM surface.

Observed populated-index calls for this gate:

```text
3 real searches against the populated KB
```

At current S3 Vectors request pricing of $2.50 per million queries, the request-fee component for those three searches is approximately `$0.0000075`, plus negligible data-processed cost for the nine-vector lab index and query-embedding model usage. An exact bill is not fabricated from incomplete provider telemetry.

Closeout: [`../labs/phase-7-gate-7-4-bounded-retrieve.md`](../labs/phase-7-gate-7-4-bounded-retrieve.md).

## AWS foundation

```text
environment:             dev
primary workload Region: us-east-1
IaC:                     Terraform
human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
```

Persistent AWS access keys are not stored in GitHub.

## Current quality boundary

Dedicated CI slices cover:

```text
Correlation
Repository Intelligence
Risk Policy
Semantic Query
Knowledge Retrieval
Terraform static/security checks
```

Knowledge Retrieval CI also watches `knowledge/corpus/**` so corpus authority changes cannot bypass its gate.

## Next action

Close PR #97 as the logical Gate 7.4 increment:

```text
1. require final documentation closeout checks to pass
2. confirm PR mergeability
3. mark PR #97 ready for review
4. squash-merge into main
5. confirm resulting main commit
6. begin Gate 7.5 on a new branch/PR
```

Gate 7.5 must measure the raw semantic retrieval baseline before synthesis, reranking, hybrid search, or arbitrary provider filters:

```text
Recall@1
Recall@3
Recall@5
Recall@10
MRR
provenance/source correctness
latency distribution
retrieval-call count / bounded cost assumptions
```
