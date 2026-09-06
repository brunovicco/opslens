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
Phase 7    Knowledge Retrieval with Bedrock                    COMPLETE
  Gate 7.1 Corpus + retrieval contract                         COMPLETE / MERGED
  Gate 7.2 Reproducible canonical corpus                       COMPLETE / MERGED
  Gate 7.3 Knowledge Base + vector infrastructure              COMPLETE / MERGED
  Gate 7.4 Real bounded Retrieve adapter                       COMPLETE / MERGED
  Gate 7.5 Retrieval evaluation                                COMPLETE / MERGED
  Gate 7.6 Context assembly + synthesis                        COMPLETE / MERGED
  Gate 7.7 Citations + groundedness                            COMPLETE / MERGED
  Gate 7.8 Phase 7 closeout                                    COMPLETE / MERGED
Phase 8    Hybrid Retrieval                                    NEXT
```

Latest merged checkpoint:

```text
Phase 7 Gate 7.8 / PR #102
16dcb98ac16e692e3eec647dcd44592497533d88
```

Gate 7.8 tracking issue #101 is closed as completed.

## Permanent boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

Deterministic authorities own package normalization, version/range matching, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS evidence, Risk Policy, semantic-query validation and SQL compilation, canonical corpus construction, retrieval evidence admission, context assembly, citation authority, output admission, and evaluation metric computation.

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
 -> deterministic bounded context assembly
 -> deterministic pre-model authority decision
 -> bounded non-streaming Bedrock Converse synthesis
 -> deterministic citation catalog
 -> grounded claim/citation output contract
 -> explicit human support judgments
 -> deterministic groundedness metrics
```

The structured and semantic paths are complementary. Structured vulnerability/risk facts remain outside RAG authority.

## Phase 7 AWS baseline

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
synthesis profile:     us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Canonical corpus manifest:

```text
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

Successful ingestion materialized exactly nine vectors.

## Retrieval baseline — Gate 7.5

Frozen `knowledge-retrieval-golden:v1`:

```text
10 cases: 8 positive + 2 negative/out-of-authority
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0

latency min:   532 ms
latency mean:  720.0 ms
latency p50:   616 ms
latency p95:   1728 ms
latency max:   1728 ms
SDK retries:   0
```

Both negative cases returned non-empty nearest-neighbor results with rank-1 scores around `0.689`. Retrieval existence or score does not establish answerability.

## Synthesis baseline — Gate 7.6

```text
default max context chunks: 5
hard max chunks:            10
max context bytes:          16,384 UTF-8 bytes
selection:                  contiguous whole-chunk rank prefix
question:                   <= 1,000 characters
model calls/application:    1 maximum
answer:                     <= 4,000 characters
API:                        bedrock-runtime / Converse
streaming:                  no
temperature:                0.0
provider maxTokens:         2,048
tools:                      none
structured output:          JSON Schema
```

First supported real synthesis was executed once without replay:

```text
Retrieve request id:     4835c5d0-4a4e-4f47-9610-482ab6ec1103
Retrieve elapsed:        1463 ms
selected chunks:         5
context bytes:           5828

Converse request id:     eee2a118-f806-40d5-8f53-57c88da8ad16
decision:                answer
input/output tokens:     2671 / 491
Bedrock latency:         7217 ms
client elapsed:          7983 ms
SDK retries:             0
```

Directly computable cost components total `$0.0056411`; unexposed query-embedding and S3 Vectors processed/returned units were not fabricated.

## Groundedness baseline — Gate 7.7

Frozen `knowledge-grounding-golden:v1`:

```text
4 cases
3 expected answers
1 expected abstention
```

The first real four-case run was executed exactly once from validated pre-run head:

```text
507fe04f963c7eeb49748eb950101ea2fc55e14f
```

Runtime totals:

```text
cases completed:                   4 / 4
real Retrieve calls:               4
real grounded Converse calls:      4
SDK retries:                       0
all Converse stop reasons:         end_turn
input tokens:                      11,734
output tokens:                     645
total tokens:                      12,379
retrieval latency mean:            790.0 ms
Bedrock latency mean:              3396.5 ms
client synthesis mean:             3743.25 ms
```

Human-reviewed support evidence:

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

The key preserved weakness is the isolation case: the expected isolation chunk was retrieved at rank 1, but both claims cited the adjacent post-change chunk. This is a citation-attribution/groundedness failure, not retrieval unavailability.

The exact TLS-cipher case correctly abstained despite five retrieved neighbors.

Directly computable four-case cost:

```text
model input:              $0.0129074
model output:             $0.0035475
model subtotal:           $0.0164549
4 S3 Vectors requests:    $0.0000100
computable total:         $0.0164649
```

## Phase 7 closeout decisions — Gate 7.8

### Failure taxonomy

```text
1. route / authority failure
2. provider retrieval failure
3. retrieval evidence-admission failure
4. retrieval relevance / coverage failure
5. context-assembly failure
6. synthesis transport failure
7. synthesis output-admission failure
8. answerability / decision failure
9. citation-authority failure
10. citation-attribution failure
11. semantic groundedness failure
```

### Future application runtime IAM

No application compute principal exists yet and Gate 7.8 created no IAM role.

The future runtime entitlement is documented in ADR 0024:

```text
bedrock:Retrieve
 -> exact Knowledge Base ARN

bedrock:InvokeModel
 -> exact US Geographic inference profile
 -> exact Claude Haiku 4.5 foundation-model ARNs required in
    us-east-1, us-east-2, us-west-2
 -> foundation-model access conditioned on exact inference profile ARN
```

The proven runtime path does not justify `RetrieveAndGenerate`, streaming inference, Knowledge Base administration, data-source management, or direct S3 Vectors application access.

### Cost and observability

Phase 7 keeps ingestion embedding/vector costs, query embedding/vector query costs, and synthesis token costs separate. Only runtime-supported values are reported as computed costs.

Current lab evidence includes provider request IDs, retrieval ranks/scores, provenance hashes, context/catalog/request/result hashes, model/profile identity, token counts, latencies, retries, stop reason, decisions, citation mappings, and human support-judgment hashes.

Phase 7 does not claim production SLOs, high-volume percentiles, end-user trace correlation, production alerts, or full per-request bill attribution without a deployed workload.

## Phase 8 entry criteria

Phase 8 starts from these frozen assumptions:

```text
1. structured vulnerability/risk truth remains deterministic authority
2. semantic retrieval remains explanatory/remediation evidence
3. routing between evidence classes is explicit and typed
4. combined answers preserve provenance by evidence class
5. Gate 7.7 baseline remains immutable
6. prompt/reranker/retrieval changes are separately versioned and reevaluated
7. no new AWS service is added without a measured requirement
8. quality, cost, failure, and observability remain separately measurable
```

## Validation note

PR #102 changed documentation/ADR files only. The repository `Python CI` pull-request workflow intentionally filters to executable Python/tests/fixtures/corpus/build paths, so the documentation-only closeout did not schedule a new Python run. The executable Gate 7.7 baseline immediately preceding the closeout passed **Python CI #295** successfully.

## Next action

Begin **Phase 8 — Gate 8.1: Offline Hybrid Routing + Authority Contract** from the merged Gate 7.8 main checkpoint. Do not add AWS resources or make model calls in Gate 8.1.
