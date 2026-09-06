# OpsLens — Current State

_Last updated: 2026-09-06_

This document is the implementation checkpoint for the OpsLens repository.

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
  Gate 7.7 Citations + groundedness                            COMPLETE / PR #100
  Gate 7.8 Phase 7 closeout                                    NEXT
```

Recent logical merges:

```text
Phase 6 / PR #91
95db66e278059629ce6572b2950e9cca705c6498

Gate 7.3 / PR #95
1337950ddb5948943bf361dba4c3cdc40dafaf2b

Gate 7.4 / PR #97
7c25877e0ae9541a4f20b8537e4f77c88ee776a5

Gate 7.5 / PR #98
b30af10a568cefa7175c253120499939f9ca18d8

Gate 7.6 / PR #99
cc8097b3e2e9b048ca069e961736788de0a79f0d
```

Gate 7.7 is complete on PR #100 and awaits the protected squash-merge closeout after final CI.

## Permanent boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

Deterministic authorities own package normalization, vulnerable-range matching, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS evidence, Risk Policy, canonical corpus construction, semantic-query validation/SQL compilation, retrieval evidence admission, context assembly, synthesis admission, citation authority, output admission, and evaluation metric computation.

LLMs may classify, plan, synthesize, explain, route, and select among already-admitted citation IDs. They do not replace structured truth or invent source authority.

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
 -> deterministic citation catalog
 -> grounded claim/citation output contract
 -> explicit support judgments
 -> deterministic groundedness metrics
```

## Phase 7 infrastructure baseline

```text
knowledge base id:     BTVJ2PBR2A
data source id:        IEL1LBE026
source bucket:         opslens-dev-data-487757851499-us-east-1
Region:                us-east-1
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

## Gate 7.4 — Direct bounded retrieval

Direct `bedrock-agent-runtime:Retrieve` stays separately observable from generation.

Initial real admitted baseline:

```text
requested top_k:        5
returned/admitted:      5
provider request id:    e92d67f1-18fa-4537-8ff4-c2e02ab813e0
client elapsed:         1257 ms
SDK retries:            0
rank 1:                 knowledge-chunk:pypa-secure-installs:hashes:v1
rank 1 score:           0.8649594783782959
```

Provider similarity is retained as evidence, never silently converted to confidence or authority.

## Gate 7.5 — Retrieval evaluation

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

Both negative/out-of-authority cases returned non-empty nearest-neighbor results with rank-1 scores near `0.689`, overlapping legitimate evidence. Retrieval existence or score therefore does not establish answerability.

## Gate 7.6 — Deterministic context assembly + synthesis

Merged through PR #99 at:

```text
cc8097b3e2e9b048ca069e961736788de0a79f0d
```

Context bounds:

```text
default max chunks:      5
hard max chunks:         10
max admitted text bytes: 16,384 UTF-8 bytes
selection:               contiguous whole-chunk rank prefix
truncation/backfill:     forbidden
```

Synthesis boundary:

```text
question:                 <= 1,000 characters
model calls/application:  1 maximum
answer:                   <= 4,000 characters
raw response parser:      <= 65,536 characters
Region:                   us-east-1
API:                      bedrock-runtime / Converse
model/profile:            us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:                no
temperature:              0.0
provider maxTokens:       2,048
tools:                    none
structured output:        JSON Schema
```

First supported real run completed once without replay:

```text
Retrieve request id:     4835c5d0-4a4e-4f47-9610-482ab6ec1103
Retrieve elapsed:        1463 ms
selected chunks:         5
context bytes:           5828

Converse request id:     eee2a118-f806-40d5-8f53-57c88da8ad16
decision:                answer
answer characters:       1751
input/output tokens:     2671 / 491
Bedrock latency:         7217 ms
client elapsed:          7983 ms
SDK retries:             0
```

Directly computable first-run cost components total `$0.0056411`; unexposed Titan/S3 Vectors billable units were not fabricated.

## Gate 7.7 — Deterministic citations + groundedness — COMPLETE

### Citation authority

```text
AssembledContext
 -> selected blocks only
 -> deterministic C1..Cn
 -> ProjectedCitation[]
 -> CitationCatalog
```

A model may reference `C1`; it cannot redefine the URL/source/document/chunk/hash behind `C1`.

### Grounded output

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

Every admitted answer claim contains at least one valid citation ID. This gives syntactic citation coverage, not semantic proof.

### Frozen evaluation

Dataset:

```text
knowledge-grounding-golden:v1
4 cases
3 expected answers
1 expected abstention
```

The first real four-case run was executed exactly once from validated head:

```text
507fe04f963c7eeb49748eb950101ea2fc55e14f
```

Runtime outcome:

```text
application complete:              true
cases completed:                   4 / 4
real Retrieve calls:               4
real grounded Converse calls:      4
retries:                           0
all Converse stop reasons:         end_turn
```

Tokens and latency:

```text
input tokens:                       11,734
output tokens:                      645
total tokens:                       12,379
retrieval latency mean:             790.0 ms
Bedrock latency mean:               3396.5 ms
client synthesis mean:              3743.25 ms
```

Human-reviewed support evidence is preserved without model/source text duplication at:

```text
labs/evidence/phase-7-gate-7-7-first-run-review-v1.json
```

Frozen aggregate metrics:

```text
decision accuracy:                 1.0
citation target precision:         0.2857142857142857
citation target recall:            0.5
claim supportedness rate:          0.8461538461538461
unsupported claim rate:            0.15384615384615385
citation correctness rate:         0.8461538461538461
abstention precision:              1.0
abstention recall:                 1.0
```

The key failure signal is the isolation case: the correct isolation chunk was retrieved at rank 1, but both claims cited the adjacent post-change chunk instead. Under strict exact-chunk review both claim/citation pairs were unsupported. This is an attribution/grounding failure, not a retrieval-availability failure.

The exact TLS-cipher case correctly abstained even though vector retrieval returned five neighbors, reinforcing that non-empty retrieval does not equal answerability.

Directly computable Gate 7.7 first-run cost:

```text
model input:              $0.0129074
model output:             $0.0035475
model subtotal:           $0.0164549
4 S3 Vectors requests:    $0.0000100
computable total:         $0.0164649
```

This is not represented as the complete AWS bill because exact Titan query-embedding and S3 Vectors processed/returned units are not exposed by the runtime evidence.

Relevant CI:

```text
Python CI #279: SUCCESS — real-evaluation harness
Python CI #280: SUCCESS — validated pre-run head
Python CI #283: FAIL    — strict typing diagnostics in reviewed projection only
Python CI #284: SUCCESS — reviewed evidence + deterministic metrics
```

Gate 7.7 introduced no AWS resource and no IAM permission.

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

Proceed to **Gate 7.8 — Phase 7 closeout** only after PR #100 final CI and squash merge.

Gate 7.8 should consolidate:

```text
retrieval / synthesis / citation failure diagnosis
least-privilege application runtime IAM strategy
retrieval / vector / embedding / model cost accounting boundaries
observability evidence and missing production telemetry
Phase 7 ADR and architecture consistency
regression and evaluation evidence
explicit Phase 8 entry criteria
```

Do not optimize the Gate 7.7 prompt against the preserved four-case output inside the same baseline gate. Any citation-attribution improvement must be separately versioned and reevaluated.
