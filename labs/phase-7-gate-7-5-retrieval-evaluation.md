# Phase 7 — Gate 7.5: Retrieval Evaluation

_Date: 2026-09-06_

## Status

**IN PROGRESS — EVALUATION CONTRACT FROZEN / METRIC IMPLEMENTATION NEXT.**

Gate 7.4 was squash-merged to `main` at:

```text
7c25877e0ae9541a4f20b8537e4f77c88ee776a5
```

The evaluation reuses the real direct-Retrieve runtime proven in Gate 7.4.

## Goal

Measure the raw semantic retrieval baseline independently from synthesis, reranking, hybrid search, and agentic behavior.

Permanent rule:

> Retrieval output is evidence, not deterministic truth.

Gate 7.5 answers:

> Given the frozen canonical corpus and frozen golden questions, how often does the correct explanatory/remediation evidence appear near the top of the real Bedrock Knowledge Base ranking?

## Frozen evaluation dataset

Fixture:

```text
tests/fixtures/knowledge_retrieval/golden_retrieval_v1.json
```

Dataset ID:

```text
knowledge-retrieval-golden:v1
```

Shape:

```text
10 total cases
 8 positive cases with one or more relevant canonical chunk IDs
 2 negative/out-of-authority cases with no relevant canonical chunk IDs
```

The fixture authority remains explanatory/remediation knowledge only. Structured NVD, KEV, EPSS, CVSS, GHSA applicability, repository versions, risk scores, and runtime exposure remain outside the corpus authority.

Do not relabel cases after observing real retrieval results. Any future label change requires an explicit versioned dataset change.

## Real runtime under evaluation

```text
knowledge base id: BTVJ2PBR2A
data source id:    IEL1LBE026
vector count:      9
vector store:      Amazon S3 Vectors
embedding model:   amazon.titan-embed-text-v2:0
dimensions:        1024
search baseline:   semantic only
reranking:         disabled
synthesis:         absent
```

The evaluation uses the Gate 7.4 checked-corpus admission path. Provider-returned results count only after deterministic location/hash/byte-count/metadata/provenance validation succeeds.

## Bounded query strategy

Run exactly one real Retrieve request per fixture case with:

```text
top_k = 10
```

Why one call per case:

- `Recall@1`, `@3`, `@5`, and `@10` can be derived from the same ranking;
- avoids 4x provider calls merely to change the cutoff;
- preserves one ranking per question;
- keeps query cost and rate pressure bounded;
- corpus contains only nine vectors, so a `top_k=10` request may validly return nine results.

Expected real-call budget for the full fixture:

```text
10 Retrieve calls total
```

Do not retry evaluation cases automatically in v1. A provider/runtime failure is recorded as a failed case with its safe failure category; rerunning requires an explicit operator decision so transient failures are not silently erased from evidence.

## Positive-case metrics

Positive cases are those with:

```text
should_have_relevant_evidence = true
```

### Recall@K

For one positive case and cutoff `K`:

```text
Recall@K(case) = 1
  if at least one fixture relevant_chunk_id appears in ranks 1..K
else 0
```

Aggregate:

```text
Recall@K = sum(case hits) / number of positive cases
```

Frozen cutoffs:

```text
K = 1, 3, 5, 10
```

Because the current corpus contains nine vectors, `Recall@10` means “relevant evidence appears anywhere in the provider ranking returned for the bounded top_k=10 request.”

### Reciprocal rank / MRR

For one positive case:

```text
RR(case) = 1 / rank_of_first_relevant_chunk
```

If no relevant chunk is returned:

```text
RR(case) = 0
```

Aggregate:

```text
MRR = mean(RR over all positive cases)
```

For cases with multiple relevant chunk IDs, the first relevant result defines reciprocal rank.

## Provenance/source correctness

The Gate 7.4 admission boundary already guarantees that admitted chunk provenance comes from the checked manifest rather than provider-invented identity.

Gate 7.5 additionally compares relevant hits with the fixture labels:

```text
chunk_id in relevant_chunk_ids
canonical document_id in relevant_document_ids
source_type in expected_source_types
```

Record:

```text
relevant_hit_count
relevant_hit_provenance_correct_count
relevant_hit_provenance_correct_rate
```

A provider score does not override a fixture/provenance mismatch.

## Negative-case evidence

Negative cases have:

```text
should_have_relevant_evidence = false
relevant_chunk_ids = []
```

A nearest-neighbor vector search is not expected to abstain automatically. Therefore Gate 7.5 does **not** invent a score threshold or treat an empty fixture label as proof that Bedrock should return zero candidates.

For each negative case record observational evidence:

```text
returned_result_count
rank-1 chunk identity
rank-1 relevance score when present
maximum relevance score when present
minimum relevance score when present
```

Aggregate:

```text
negative_nonempty_retrieval_rate
negative_rank1_score distribution
```

This evidence informs later routing/abstention/context-admission decisions. Provider relevance scores remain uncalibrated evidence and are not interpreted as probabilities.

## Latency metrics

Use Gate 7.4 `client_elapsed_ms` per real Retrieve call.

Record:

```text
count
min
max
mean
p50
p95
```

Percentiles use the deterministic nearest-rank definition over the sorted observed values:

```text
rank = ceil(p * N)
value = sorted_values[rank - 1]
```

With only ten cases, latency percentiles are laboratory evidence, not a production SLO claim.

## Cost evidence

Count actual real Retrieve attempts and successful populated-index searches.

For the planned ten-case run, use current published pricing assumptions and report components separately:

```text
S3 Vectors query request component
S3 Vectors processed-data component when estimable
query embedding model usage when provider telemetry supports it
```

Do not fabricate exact query-embedding token counts or billable vector bytes when the response does not expose them.

At the current S3 Vectors request fee of `$2.50 / 1,000,000 queries`, ten populated-index searches have a request-fee component of approximately:

```text
10 / 1,000,000 * $2.50 = $0.000025
```

This excludes data-processed and embedding-model components.

## Output evidence contract

The evaluation runner must emit deterministic JSON/Markdown evidence without retrieved source text.

Per-case evidence:

```text
case_id
question_sha256
should_have_relevant_evidence
relevant_chunk_ids from frozen fixture
returned canonical chunk IDs by rank
provider scores by rank when present
client_elapsed_ms
provider_request_id
retry_attempts
success/failure category
positive hit cutoffs / reciprocal rank when applicable
negative observational fields when applicable
```

Aggregate evidence:

```text
dataset_id
knowledge_base_id
case count / positive count / negative count
Recall@1 / Recall@3 / Recall@5 / Recall@10
MRR
provenance correctness
latency summary
provider retry/failure counts
real call count
bounded cost assumptions
```

Raw query text may remain in the checked fixture but should not be duplicated into runtime operational output; use `question_sha256` in emitted evidence.

Retrieved source text must not be emitted by the evaluation artifact.

## Failure behavior

Fail closed before or during aggregation on:

```text
unknown fixture schema fields
missing/duplicate case IDs
invalid should_have_relevant_evidence values
positive case with no relevant chunk IDs
negative case with any relevant chunk/document/source labels
fixture chunk ID not present in checked canonical catalog
returned chunk identity not admitted by Gate 7.4
more returned results than request top_k
non-finite provider score
provider/runtime failure without safe categorization
case-count mismatch
attempt to aggregate two records for one case
```

Provider/runtime failures are recorded as case failures and must not be silently converted into retrieval misses.

## Increment plan

```text
7.5a  freeze metric + evidence contract                         COMPLETE
7.5b  strict golden-fixture loader                              NEXT
7.5c  deterministic offline metric aggregation                  PENDING
7.5d  bounded real evaluation runner                            PENDING
7.5e  execute exactly one top_k=10 run per fixture case         PENDING
7.5f  analyze metrics/latency/cost + negative evidence          PENDING
7.5g  docs/state closeout + final CI + squash merge             PENDING
```

## Exit criteria

- [x] Gate 7.4 squash-merged before evaluation work;
- [x] frozen ten-case fixture reused without outcome-driven relabeling;
- [x] one-call-per-case `top_k=10` strategy frozen;
- [x] Recall@1/@3/@5/@10 definitions frozen;
- [x] MRR definition frozen;
- [x] provenance/source correctness definition frozen;
- [x] negative-case evidence explicitly observational, not an invented confidence threshold;
- [x] latency percentile definition frozen;
- [x] cost accounting boundaries frozen;
- [ ] strict fixture loader implemented;
- [ ] deterministic metric aggregator implemented and unit-tested;
- [ ] bounded real runner implemented and CI green;
- [ ] ten real fixture cases executed once each;
- [ ] aggregate retrieval metrics recorded;
- [ ] failure/retry/latency/cost evidence recorded;
- [ ] docs/current state/roadmap/architecture synchronized;
- [ ] PR squash-merged.

## Next authorized implementation step

Implement **7.5b + 7.5c offline only**:

1. strict loader for `golden_retrieval_v1.json`;
2. validate every positive fixture chunk against the checked Gate 7.2 catalog;
3. deterministic per-case Recall/RR and aggregate Recall@K/MRR/provenance metrics;
4. negative-case observational aggregation;
5. unit tests with no AWS calls.

Do not run the ten-case real evaluation until the evaluator is deterministic and CI-green.

## Official pricing references

- Amazon S3 pricing — S3 Vectors:
  https://aws.amazon.com/s3/pricing/
- Amazon Bedrock pricing:
  https://aws.amazon.com/bedrock/pricing/
