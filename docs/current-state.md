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
Phase 7    Knowledge Retrieval with Bedrock                    IN PROGRESS
  Gate 7.1 Corpus + retrieval contract                         COMPLETE
  Gate 7.2 Reproducible canonical corpus                       COMPLETE
  Gate 7.3 Knowledge Base + vector infrastructure              COMPLETE / MERGED
  Gate 7.4 Real bounded Retrieve adapter                       COMPLETE / MERGED
  Gate 7.5 Retrieval evaluation                                COMPLETE / MERGED
  Gate 7.6 Context assembly + synthesis                        IN PROGRESS
    7.6a deterministic context assembly                        COMPLETE / PR #99
    7.6b synthesis request/output + abstention contract         NEXT
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

Gate 7.4 / PR #97
7c25877e0ae9541a4f20b8537e4f77c88ee776a5

Gate 7.5 / PR #98
b30af10a568cefa7175c253120499939f9ca18d8
```

Gate 7.6 is active on draft PR #99 from the Gate 7.5 merge. The first increment is deliberately offline-only; no synthesis model call or new AWS/IAM surface exists yet.

## Permanent boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

Deterministic authorities own package normalization, vulnerable-range matching, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS evidence, Risk Policy, canonical corpus construction, semantic-query validation/SQL compilation, retrieval evidence admission, context assembly, citation projection, and execution/tool/cost enforcement.

LLMs may classify, plan, synthesize, explain, and route over validated evidence. They do not replace deterministic structured truth.

## Implemented system

```text
Threat Intelligence Data Lake
 -> deterministic vulnerability correlation
 -> immutable Repository Intelligence
 -> deterministic Risk Policy v1
 -> bounded Semantic Query Layer

Controlled Knowledge Corpus
 -> customer-managed Bedrock Knowledge Base
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> direct bounded Retrieve
 -> deterministic checked-corpus admission
 -> retrieval evaluation
 -> deterministic bounded context assembly
```

Bedrock synthesis is deliberately not implemented yet.

## Phase 7 current runtime

```text
knowledge base id:     BTVJ2PBR2A
data source id:        IEL1LBE026
source bucket:         opslens-dev-data-487757851499-us-east-1
vector store:          Amazon S3 Vectors
embedding model:       amazon.titan-embed-text-v2:0
dimensions:            1024
vector type:           FLOAT32
distance:              cosine
chunking:              NONE
canonical chunks:      9
```

Canonical corpus manifest:

```text
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

Successful ingestion:

```text
job:                    WZRUGOFZPI
status:                 COMPLETE
documents scanned:      9
new documents indexed:  9
failed:                 0
skipped:                0
vectors materialized:   9
```

## Gate 7.4 — Real bounded Retrieve adapter — COMPLETE / MERGED

Gate 7.4 uses direct `bedrock-agent-runtime:Retrieve`, not `RetrieveAndGenerate`, so retrieval remains independently measurable.

Runtime authority:

```text
RetrievalRequest
 -> exact configured KB
 -> direct semantic Retrieve
 -> strict provider parser
 -> exact S3 content-addressed key reconciliation
 -> returned-text SHA-256 + byte-count validation
 -> canonical metadata comparison
 -> RetrievedChunk[]
 -> RetrievalEvidence
```

Real admitted retrieval:

```text
query sha256:           5b398fe871d0cb51eaacb4f42a11b2ec402b5fdb4c523d2b7bca85e84dff3d0d
requested top_k:        5
returned/admitted:      5
provider request id:    e92d67f1-18fa-4537-8ff4-c2e02ab813e0
client elapsed:         1257 ms
SDK retries:            0
rank 1:                 knowledge-chunk:pypa-secure-installs:hashes:v1
rank 1 score:           0.8649594783782959
```

Intentional provider failure:

```text
nonexistent KB: ZZZZZZZZZZ
provider_code: ResourceNotFoundException
```

Gate 7.4 was squash-merged through PR #97 at `7c25877e0ae9541a4f20b8537e4f77c88ee776a5`.

## Gate 7.5 — Retrieval evaluation — COMPLETE / MERGED

Frozen dataset:

```text
knowledge-retrieval-golden:v1
10 cases
8 positive
2 negative/out-of-authority
```

Exactly one real `top_k=10` Retrieve request was executed for each case. All ten completed successfully and no SDK retry occurred.

Aggregate quality:

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
```

Provenance:

```text
relevant hits:      9
correct provenance: 9
correctness rate:   1.0
```

Latency:

```text
min:   532 ms
max:   1728 ms
mean:  720.0 ms
p50:   616 ms
p95:   1728 ms
retries: 0
```

Negative evidence:

```text
negative_nonempty_retrieval_rate: 1.0
rank-1 scores: 0.6890382468700409, 0.6880056560039520
rank-1 chunk for both negatives:
knowledge-chunk:dependency-remediation-validation:post-change:v1
```

The negative scores overlap the score range of legitimate evidence. Gate 7.5 therefore does not create an arbitrary score threshold. Vector similarity is evidence, not a calibrated confidence probability or an authority/route decision.

The weakest positive case retrieved the expected vendor-advisory remediation chunk at rank 7. `Recall@10=1.0` is not treated as a production-quality claim because the corpus contains only nine vectors. `Recall@3`, `Recall@5`, and MRR expose the ranking weakness more clearly.

Current runtime default `top_k=5` would contain expected evidence for seven of eight positive cases in this frozen fixture. Gate 7.5 records this baseline and does not tune against the test set.

Observed real calls:

```text
10 populated-index searches
```

At the published S3 Vectors request rate of `$2.50 / 1,000,000 queries`, the exact request-fee component is:

```text
$0.000025
```

This is not presented as the complete retrieval bill. Bedrock `Retrieve` does not expose exact S3 Vectors processed/returned billable bytes or Titan query-embedding token counts, so those components are not fabricated.

Gate 7.5 was squash-merged through PR #98 at `b30af10a568cefa7175c253120499939f9ca18d8`.

Closeout lab: [`../labs/phase-7-gate-7-5-retrieval-evaluation.md`](../labs/phase-7-gate-7-5-retrieval-evaluation.md).

## Gate 7.6 — Context assembly + synthesis — IN PROGRESS

### 7.6a — Deterministic context assembly — COMPLETE / PR #99

Current provider-independent path:

```text
RetrievalEvidence
 -> deterministic contiguous rank-prefix assembly
 -> whole ContextEvidenceBlock[]
 -> AssembledContext
 -> future bounded synthesis adapter
```

Frozen v1 limits:

```text
default max chunks:      5
hard max chunks:         10
max admitted text bytes: 16,384 UTF-8 bytes
```

The byte limit is an application-level denial-of-wallet/input-growth guardrail, not a token estimate or provider context-window claim.

Context selection is intentionally simple and reproducible:

- only already-admitted `RetrievedChunk` values are eligible;
- whole chunks only; no text truncation;
- preserve one contiguous retrieval-rank prefix from rank 1;
- stop at the first non-fitting chunk; do not backfill lower-ranked smaller chunks;
- empty retrieval fails closed;
- if rank 1 alone exceeds the byte budget, assembly fails closed;
- provider relevance score is not projected into synthesis context;
- raw query is represented operationally by SHA-256 rather than copied into context evidence;
- deterministic `context_sha256` covers query identity, limits, selected provenance/content hashes, counts, and stop reason.

The no-score rule follows directly from Gate 7.5: negative/out-of-authority queries produced similarity scores overlapping valid retrieval evidence, so provider score cannot silently become context authority.

7.6a adds no AWS resources, IAM permissions, network calls, or model calls.

Quality evidence:

```text
Python CI #243: FAIL — Ruff line length only; fixed without semantic change
Python CI #244: FAIL — Pyright direct-isinstance diagnostics; runtime checks retained via helper
Python CI #245: SUCCESS
  Ruff:             PASS
  Pyright strict:   PASS
  pytest:            PASS
  regressions:      PASS
```

Lab: [`../labs/phase-7-gate-7-6-context-synthesis.md`](../labs/phase-7-gate-7-6-context-synthesis.md).

## IAM boundary

The Knowledge Base service role remains an ingestion/storage integration identity trusted by Bedrock.

Retrieval is a separate runtime responsibility. No deployed application compute principal exists yet, so final least-privilege retrieval-role attachment remains deferred until a real runtime principal exists.

7.6a requires no AWS or IAM change. Synthesis permissions must not be added before a concrete runtime/model boundary is selected and justified.

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

Continue Gate 7.6 inside draft PR #99 with **7.6b offline first**:

```text
1. freeze synthesis request/output contract
2. freeze unsupported / insufficient-evidence behavior
3. define trusted-instruction vs untrusted-context serialization boundary
4. freeze application call/output bounds
5. only then select Bedrock runtime API/model from current official AWS documentation
```

Do not make a real synthesis call until the request/output/abstention contract is deterministic and CI-green.
