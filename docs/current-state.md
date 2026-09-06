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
  Gate 7.1 Corpus + retrieval contract                         COMPLETE / MERGED
  Gate 7.2 Reproducible canonical corpus                       COMPLETE / MERGED
  Gate 7.3 Knowledge Base + vector infrastructure              COMPLETE / MERGED
  Gate 7.4 Real bounded Retrieve adapter                       COMPLETE / MERGED
  Gate 7.5 Retrieval evaluation                                COMPLETE / MERGED
  Gate 7.6 Context assembly + synthesis                        COMPLETE / MERGED
  Gate 7.7 Citations + groundedness                            IN PROGRESS / PR #100
    7.7a deterministic citation catalog                        COMPLETE
    7.7b grounded claim-to-citation contract                   COMPLETE
    7.7c frozen evaluation fixture + metrics                   NEXT
```

Recent logical merges:

```text
Phase 6 / PR #91
95db66e278059629ce6572b2950e9cca705c6498

Gate 7.1 / PR #93
f2e3b72c31d0713707857bc0867a7f59e667b9dd

Gate 7.2 / PR #94
manifest sha256:
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418

Gate 7.3 / PR #95
1337950ddb5948943bf361dba4c3cdc40dafaf2b

Gate 7.4 / PR #97
7c25877e0ae9541a4f20b8537e4f77c88ee776a5

Gate 7.5 / PR #98
b30af10a568cefa7175c253120499939f9ca18d8

Gate 7.6 / PR #99
cc8097b3e2e9b048ca069e961736788de0a79f0d
```

Gate 7.7 is active on draft PR #100 from the exact Gate 7.6 merge.

## Permanent boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

Deterministic authorities own package normalization, vulnerable-range matching, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS evidence, Risk Policy, canonical corpus construction, semantic-query validation/SQL compilation, retrieval evidence admission, context assembly, synthesis admission, citation authority, output admission, and metric computation.

LLMs may classify, plan, synthesize, explain, route, and later propose citation references from an allowlisted deterministic catalog. They do not replace structured truth or invent source authority.

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
 -> deterministic synthesis admission
 -> bounded Bedrock Converse synthesis
 -> typed SynthesisResult + runtime evidence
 -> deterministic citation catalog
 -> grounded claim/citation output contract
```

## Phase 7 runtime baseline

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

## Gate 7.4 — Direct bounded retrieval — COMPLETE / MERGED

Direct `bedrock-agent-runtime:Retrieve` stays separately observable from generation.

Real admitted baseline:

```text
requested top_k:        5
returned/admitted:      5
provider request id:    e92d67f1-18fa-4537-8ff4-c2e02ab813e0
client elapsed:         1257 ms
SDK retries:            0
rank 1:                 knowledge-chunk:pypa-secure-installs:hashes:v1
rank 1 score:           0.8649594783782959
```

## Gate 7.5 — Retrieval evaluation — COMPLETE / MERGED

Frozen dataset:

```text
knowledge-retrieval-golden:v1
10 cases
8 positive
2 negative/out-of-authority
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

```text
latency min:  532 ms
latency mean: 720.0 ms
latency p50:  616 ms
latency p95:  1728 ms
latency max:  1728 ms
SDK retries:  0
```

Both negative/out-of-authority cases returned non-empty nearest-neighbor results with rank-1 scores near `0.689`, overlapping legitimate evidence. Provider similarity therefore remains evidence, not probability, answerability, or routing authority.

## Gate 7.6 — Deterministic context assembly + synthesis — COMPLETE / MERGED

Gate 7.6 established:

```text
RetrievalEvidence
 -> contiguous whole-chunk rank-prefix context assembly
 -> AssembledContext
 -> deterministic SUPPORTED / UNSUPPORTED authority
 -> bounded SynthesisRequest
 -> trusted/untrusted prompt envelope
 -> one non-streaming Bedrock Converse call maximum
 -> strict provider evidence admission
 -> deterministic ANSWER / INSUFFICIENT_EVIDENCE parsing
 -> SynthesisResult
```

Context bounds:

```text
default max chunks:      5
hard max chunks:         10
max admitted text bytes: 16,384 UTF-8 bytes
```

Synthesis bounds:

```text
question:            <= 1,000 characters
model calls:         exactly 1 maximum
answer:              <= 4,000 characters
raw response parser: <= 65,536 characters
```

Bedrock provider boundary:

```text
Region:                  us-east-1
endpoint/API:            bedrock-runtime / Converse
streaming:               no
model/profile:           us.anthropic.claude-haiku-4-5-20251001-v1:0
temperature:             0.0
provider maxTokens:      2,048
tools:                   none
structured output:       JSON Schema
```

First supported real run completed once without replay.

Retrieval:

```text
provider request id:    4835c5d0-4a4e-4f47-9610-482ab6ec1103
requested/returned:     5 / 5
client elapsed:         1463 ms
SDK retries:            0
rank 1:                 knowledge-chunk:pypa-secure-installs:hashes:v1
rank 1 score:           0.8649594783782959
```

Context:

```text
selected chunks:        5
selected UTF-8 bytes:   5828
stop reason:            exhausted_retrieval
context sha256:         bba245b46a1f8cbb2c42010b61e1ef397b2cde9c92fc0439ee0dc03197788445
```

Synthesis:

```text
decision:               answer
answer characters:      1751
input tokens:           2671
output tokens:          491
total tokens:           3162
Bedrock latency:        7217 ms
client elapsed:         7983 ms
SDK retries:            0
stop reason:            end_turn
provider request id:    eee2a118-f806-40d5-8f53-57c88da8ad16
```

Manual review against the exact frozen PyPA `Hash-checking Mode` slice found the seven substantive answer items supported by admitted evidence. This is a one-answer supportedness review, not a groundedness benchmark.

Directly computable cost components:

```text
model input:            $0.0029381
model output:           $0.0027005
model total:            $0.0056386
S3 Vectors request:     $0.0000025
computable total:       $0.0056411
```

Titan query-embedding and S3 Vectors data-processed/data-returned units are not exposed by `Retrieve` and are not fabricated.

Final Gate 7.6 CI:

```text
Python CI #265: SUCCESS
validated PR head: 60c2384e9e902326a1cb7fa6c1ca8028132ecfa9
squash merge:      cc8097b3e2e9b048ca069e961736788de0a79f0d
```

## Gate 7.7 — Deterministic citations + groundedness — IN PROGRESS

### 7.7a — Citation catalog — COMPLETE

```text
AssembledContext
 -> exact selected blocks only
 -> deterministic C1..Cn
 -> ProjectedCitation[]
 -> CitationCatalog
```

Rules:

- retrieval chunks excluded from `AssembledContext` cannot become citation authority;
- citation IDs follow selected retrieval rank deterministically;
- canonical URI/source/document/chunk identity is projected from admitted evidence;
- document/chunk content hashes remain bound to each citation;
- provider relevance score is absent;
- each citation and the catalog are content-addressed;
- source text is not duplicated into citation operational identity.

A future model may reference `C1`, but cannot redefine what `C1` means.

### 7.7b — Grounded claim/citation contract — COMPLETE

Citation-aware provider-independent output is frozen as:

```json
{
  "decision": "answer",
  "claims": [
    {"text": "...", "citation_ids": ["C1"]}
  ]
}
```

or:

```json
{"decision": "insufficient_evidence", "claims": []}
```

The model cannot author claim IDs, URLs, source IDs, document IDs, chunk IDs, or hashes. Deterministic code assigns claim indices, validates every citation ID against the exact catalog, canonicalizes citation order, rejects extra provenance fields, and renders the final answer only from cited claims.

Grounded bounds:

```text
max claims:             16
max characters/claim:  1,000
rendered answer:        <= original Gate 7.6 max_output_chars
raw response:           <= 65,536 characters
```

Every answer claim must contain at least one valid citation ID. This proves syntactic citation coverage only; it does not prove semantic support.

CI:

```text
Python CI #266: SUCCESS — citation catalog
Python CI #267: FAIL — Ruff __all__ ordering only
Python CI #268: SUCCESS — grounded claim/citation contract
```

No AWS/model call has occurred in Gate 7.7.

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

## Next action

Continue Gate 7.7c **offline before any citation-aware Bedrock call**:

```text
1. freeze evaluation questions/expected evidence before prompt tuning
2. define citation target precision/recall separately from claim groundedness
3. define explicit support-judgment provenance
4. compute all metrics deterministically from typed observations
5. preserve unsupported-claim and abstention metrics separately
6. require CI green before modifying Bedrock grounded-output request/schema
```

A valid citation ID is not itself proof that the cited evidence supports the claim.
