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
  Gate 7.8 Phase 7 closeout                                    COMPLETE / CLOSEOUT PR
Phase 8    Hybrid Retrieval                                    NEXT
```

Latest merged implementation checkpoint before Gate 7.8 documentation closeout:

```text
Phase 7 Gate 7.7 / PR #100
928f9b6173fba67778c3ee9f104aa250d108cf50
```

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
 -> retrieval evaluation
 -> deterministic bounded context assembly
 -> deterministic pre-model authority decision
 -> bounded Bedrock Converse synthesis
 -> deterministic citation catalog
 -> grounded claim/citation output contract
 -> explicit human support judgments
 -> deterministic groundedness metrics
```

The structured and semantic paths are complementary. Structured vulnerability/risk facts remain outside RAG authority.

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

## Gate 7.5 retrieval baseline

Frozen dataset:

```text
knowledge-retrieval-golden:v1
10 cases
8 positive
2 negative/out-of-authority
```

Measured result:

```text
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

Both negative/out-of-authority cases returned non-empty nearest-neighbor results with rank-1 scores around `0.689`, overlapping legitimate evidence. Retrieval existence or score does not establish answerability.

## Gate 7.6 synthesis baseline

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

Directly computable cost components total `$0.0056411`; unexposed query-embedding and S3 Vectors processed/returned units were not fabricated.

## Gate 7.7 groundedness baseline

Frozen dataset:

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
SDK retries:                       0
all Converse stop reasons:         end_turn

input tokens:                      11,734
output tokens:                     645
total tokens:                      12,379
retrieval latency mean:            790.0 ms
Bedrock latency mean:              3396.5 ms
client synthesis mean:             3743.25 ms
```

Human-reviewed support evidence is preserved at:

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

The key preserved weakness is the isolation case: the expected isolation chunk was retrieved at rank 1, but both generated claims cited the adjacent post-change chunk. Under strict exact-chunk review both claim/citation pairs were unsupported. This is a citation-attribution/grounding failure, not retrieval unavailability.

The exact TLS-cipher case correctly abstained despite five retrieved neighbors.

Directly computable four-case cost:

```text
model input:              $0.0129074
model output:             $0.0035475
model subtotal:           $0.0164549
4 S3 Vectors requests:    $0.0000100
computable total:         $0.0164649
```

## Gate 7.8 closeout decisions

Gate 7.8 consolidates architecture rather than optimizing the measured baseline.

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

These classes must remain diagnosable separately. A downstream failure must not be rewritten as a retrieval miss or model hallucination when the evidence indicates a different stage.

### Future application runtime IAM

No application compute principal exists yet and no role is created in Gate 7.8.

The future deployed runtime entitlement is frozen conceptually as:

```text
bedrock:Retrieve
 -> exact Knowledge Base ARN only

bedrock:InvokeModel
 -> exact US Geographic inference profile
 -> exact Claude Haiku 4.5 foundation-model ARNs required in
    us-east-1, us-east-2, us-west-2
 -> foundation-model access conditioned on the exact inference profile ARN
```

Not required by the proven runtime path:

```text
bedrock:RetrieveAndGenerate
bedrock:InvokeModelWithResponseStream
Knowledge Base administration/data-source management
S3 Vectors direct application access
broad Bedrock wildcard administration
```

See ADR 0024.

### Cost-accounting boundary

Phase 7 separates:

```text
ingestion-time embedding / vector-write costs
vector storage costs
query-time embedding costs
S3 Vectors query request / processed / returned costs
model input/output token costs
```

Only values directly supported by runtime/provider evidence are reported as computed cost. Cost Explorer remains the bill-level reconciliation source.

### Observability boundary

Current lab evidence includes provider request IDs, ranks/scores, result counts, context/catalog/request/result hashes, model/profile ID, token counts, provider/client latency, retries, stop reason, decisions, claim/citation mappings, and human judgment hashes.

Phase 7 does **not** claim production SLOs, high-volume latency distributions, end-user trace correlation, or production alert thresholds. Those require deployed runtime telemetry.

## Phase 8 entry criteria

Phase 8 may begin only from these frozen assumptions:

```text
1. structured vulnerability/risk truth remains deterministic authority
2. semantic retrieval remains explanatory/remediation evidence
3. routing between evidence classes is explicit and typed
4. combined answers preserve provenance by evidence class
5. Gate 7.7 baseline remains immutable
6. any prompt/reranker/retrieval change is separately versioned and reevaluated
7. no new AWS service is added without a measured requirement
8. quality, cost, failure, and observability dimensions remain separately measurable
```

Phase 8 must not begin by blindly concatenating Athena rows and vector chunks.

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

After Gate 7.8 closeout CI and merge, begin **Phase 8 — Hybrid Retrieval** with an offline-first routing/authority contract before any new AWS resource, reranker, hybrid search mode, or model call is introduced.
