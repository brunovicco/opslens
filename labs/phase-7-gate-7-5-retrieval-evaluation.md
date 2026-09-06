# Phase 7 — Gate 7.5: Retrieval Evaluation

_Date: 2026-09-06_

## Status

**COMPLETE — REAL EVALUATION RECORDED / FINAL CI + SQUASH MERGE PENDING.**

Gate 7.4 was squash-merged to `main` at:

```text
7c25877e0ae9541a4f20b8537e4f77c88ee776a5
```

Gate 7.5 measures the real direct-Retrieve runtime from Gate 7.4 before synthesis, reranking, hybrid search, or agentic behavior.

Permanent rule:

> Retrieval output is evidence, not deterministic truth.

## Frozen evaluation dataset

```text
fixture:    tests/fixtures/knowledge_retrieval/golden_retrieval_v1.json
dataset id: knowledge-retrieval-golden:v1
cases:      10 total / 8 positive / 2 negative-out-of-authority
```

The fixture authority remains explanatory/remediation knowledge only. Structured NVD, KEV, EPSS, CVSS, GHSA applicability, repository versions, risk scores, and runtime exposure remain outside the corpus authority.

No labels were changed after observing provider outcomes.

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

Provider results count only after Gate 7.4 deterministic location/hash/byte-count/metadata/provenance admission succeeds.

## Bounded query strategy

Exactly one real request was executed per fixture case:

```text
top_k = 10
real attempts = 10
application-level replay = 0
```

`Recall@1`, `@3`, `@5`, and `@10` are derived from the same ranking. The corpus contains nine vectors, so Bedrock validly returned nine results for each `top_k=10` request.

This keeps evaluation cost bounded and avoids comparing different provider rankings merely because K changed.

## Real execution

The first shell attempt never reached application code because the repository uses a `src/` layout without installing the project package into the `uv run` environment. The failure was:

```text
ModuleNotFoundError: No module named 'opslens'
```

No AWS retrieval call occurred in that attempt.

The operational invocation was corrected without changing project packaging:

```bash
PYTHONPATH=src uv run python -m opslens.knowledge_retrieval.cli.run_bedrock_retrieval_evaluation \
  --knowledge-base-id BTVJ2PBR2A \
  --data-source-id IEL1LBE026 \
  --source-bucket opslens-dev-data-487757851499-us-east-1 \
  --region us-east-1
```

Changing packaging/build metadata solely for this gate would be unrelated scope. The lab therefore documents the explicit `PYTHONPATH=src` requirement.

Real execution result:

```text
exit code:          0
complete:           true
real attempts:      10
successful cases:   10
provider failures:  0
admission failures: 0
SDK retries:        0
results per case:   9
```

The emitted evidence contained no raw question text and no retrieved source text.

## Aggregate retrieval quality

```text
Recall@1:   0.375  (3 / 8 positive cases)
Recall@3:   0.750  (6 / 8)
Recall@5:   0.875  (7 / 8)
Recall@10:  1.000  (8 / 8)
MRR:        0.5699404761904762
```

Relevant-hit provenance:

```text
relevant hits:       9
provenance correct:  9
correctness rate:    1.0
```

All relevant hits used canonical checked-corpus document/source identities rather than provider-owned identity.

### Positive-case ranks

| Case | First relevant rank | RR | Latency ms |
| --- | ---: | ---: | ---: |
| `remediation-python-upgrade-01` | 3 | 0.333333 | 1728 |
| `remediation-lock-refresh-01` | 1 | 1.000000 | 627 |
| `remediation-hash-verification-01` | 1 | 1.000000 | 566 |
| `remediation-advisory-guidance-01` | 7 | 0.142857 | 700 |
| `remediation-transitive-review-01` | 3 | 0.333333 | 617 |
| `remediation-validation-01` | 2 | 0.500000 | 559 |
| `documentation-version-constraints-01` | 4 | 0.250000 | 665 |
| `documentation-isolation-01` | 1 | 1.000000 | 532 |

The weakest positive case is `remediation-advisory-guidance-01`: the expected vendor-advisory remediation chunk appeared only at rank 7. This is preserved as baseline evidence rather than relabeled after observation.

`Recall@10 = 1.0` must not be overinterpreted. With only nine vectors and `top_k=10`, it mainly proves that every positive target exists somewhere in the full returned corpus ranking. `Recall@3`, `Recall@5`, and MRR are more useful baseline ranking signals.

The current runtime default remains `top_k=5`. The evaluation shows that this would contain relevant evidence for seven of eight positive cases, while the vendor-advisory case would be missed. Gate 7.5 records the weakness; it does not tune retrieval after seeing the test set.

## Negative/out-of-authority evidence

Both negative cases returned nine nearest-neighbor candidates:

```text
negative_nonempty_retrieval_rate = 1.0
```

| Case | Rank-1 chunk | Rank-1 score | Latency ms |
| --- | --- | ---: | ---: |
| `negative-runtime-exposure-01` | `knowledge-chunk:dependency-remediation-validation:post-change:v1` | 0.6890382468700409 | 590 |
| `negative-uncovered-ecosystem-01` | `knowledge-chunk:dependency-remediation-validation:post-change:v1` | 0.6880056560039520 | 616 |

This is expected behavior for nearest-neighbor search and is architecturally important:

- non-empty retrieval does not prove the corpus has authority to answer the question;
- provider relevance scores are not calibrated probabilities;
- the negative rank-1 scores overlap scores observed for valid positive evidence;
- an arbitrary global score threshold would therefore be unsupported by this fixture;
- routing/authority checks must happen before synthesis rather than relying on vector score as an abstention oracle.

This reinforces the OpsLens rule:

> Not every question is a RAG problem.

The runtime-exposure negative case especially reinforces:

> Repository Risk != Runtime Exposure.

## Latency and retry evidence

```text
count:    10
min:      532 ms
max:      1728 ms
mean:     720.0 ms
p50:      616 ms
p95:      1728 ms
total SDK retries: 0
```

Percentiles use the frozen nearest-rank definition.

The first request was the 1728 ms maximum while the remaining requests were 532–700 ms. The fixture is too small to claim warm-up causality or a production SLO, so this remains observational lab evidence only.

## Provider request IDs

```text
remediation-python-upgrade-01:         481b1c21-a362-4314-a187-ea0f7ed527e2
remediation-lock-refresh-01:           50e8f5c8-7cdb-4efb-9b4b-3b58c896f4c7
remediation-hash-verification-01:      6a16159f-fd08-44c9-b594-f8d0940f437b
remediation-advisory-guidance-01:      d16dcec5-a5ea-4882-982d-090e4a21ac7a
remediation-transitive-review-01:      fd91b242-6b9d-44d8-9e5e-8804ca8a2b1b
remediation-validation-01:             a967e17d-654f-4250-b35a-a3955df37d5e
documentation-version-constraints-01:  9914d48e-92b5-4b3f-a6e7-26a9269ea913
documentation-isolation-01:            734bc5e9-c41c-43b7-a21b-03ef51d2a06c
negative-runtime-exposure-01:          cd2f7eb0-2115-4fab-a3ff-2f41d85d7d7a
negative-uncovered-ecosystem-01:       84617a01-f1b7-4f67-b97a-26a068f88c67
```

## Cost evidence

OpsLens uses a **customer-managed Bedrock Knowledge Base** with S3 Vectors, not the newer Bedrock Managed Knowledge Base product. The two architectures have different pricing surfaces and must not be conflated.

For S3 Vectors, current AWS pricing separates query cost into request, data-processed, and data-returned components.

Observed populated-index searches:

```text
10
```

Published S3 Vectors query-request rate used by this lab:

```text
$2.50 / 1,000,000 queries
```

Request-fee component:

```text
10 / 1,000,000 * $2.50 = $0.000025
```

Do not treat `$0.000025` as the full retrieval bill. Exact S3 Vectors processed/returned bytes and Titan query-embedding token counts are not exposed by the Bedrock `Retrieve` response, so the lab does not fabricate those components. For this nine-vector fixture they are expected to be small, but only the request-fee component is calculated exactly from observed call count.

Official references:

- Amazon S3 pricing — S3 Vectors: https://aws.amazon.com/s3/pricing/
- Amazon Bedrock pricing: https://aws.amazon.com/bedrock/pricing/
- Bedrock Knowledge Bases types: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html

## Security / authority conclusions

Gate 7.5 did not widen IAM or provider authority.

The evaluation proves:

```text
provider ranking
 -> deterministic checked-corpus admission
 -> deterministic evaluation
```

It does not prove:

```text
provider score -> truth
provider score -> confidence probability
non-empty retrieval -> question is in corpus authority
Recall@10 -> production-quality ranking
```

No synthesis, reranking, hybrid search, arbitrary provider filter, or runtime IAM expansion was introduced.

## AIP-C01 learning conclusions

Reusable rules from this gate:

1. Evaluate retrieval independently from generation when diagnosing RAG quality.
2. Derive multiple Recall@K cutoffs from one ranking when possible to reduce calls and variance.
3. MRR exposes ranking weakness that Recall@large-K can hide.
4. Vector similarity scores require calibration before they can support thresholds or abstention.
5. Negative/out-of-domain examples are necessary even when a vector store always returns nearest neighbors.
6. Retrieval provenance correctness is separate from retrieval relevance.
7. Small-sample latency percentiles are troubleshooting evidence, not production SLOs.
8. Customer-managed and managed Knowledge Bases have different infrastructure and cost responsibilities.

## Increment plan

```text
7.5a  freeze metric + evidence contract                         COMPLETE
7.5b  strict golden-fixture loader                              COMPLETE
7.5c  deterministic offline metric aggregation                  COMPLETE
7.5d  bounded real evaluation runner                            COMPLETE
7.5e  execute exactly one top_k=10 run per fixture case         COMPLETE
7.5f  analyze metrics/latency/cost + negative evidence          COMPLETE
7.5g  docs/state closeout + final CI + squash merge             IN PROGRESS
```

## Exit criteria

- [x] Gate 7.4 squash-merged before evaluation work;
- [x] frozen ten-case fixture reused without outcome-driven relabeling;
- [x] one-call-per-case `top_k=10` strategy frozen;
- [x] strict fixture loader implemented;
- [x] deterministic Recall/MRR/provenance/latency metric core implemented and unit-tested;
- [x] bounded real runner implemented;
- [x] ten real fixture cases executed exactly once each;
- [x] aggregate retrieval metrics recorded;
- [x] negative/out-of-authority evidence recorded;
- [x] provider request IDs, latency, retries, and bounded cost evidence recorded;
- [x] relevance scores kept non-authoritative and uncalibrated;
- [x] current-state/roadmap/architecture closeout prepared;
- [ ] final CI green after closeout docs;
- [ ] PR #98 ready for review;
- [ ] PR #98 squash-merged.

## Next authorized step

Run final CI on the closeout commit. If green, confirm mergeability, mark PR #98 ready for review, and squash-merge Gate 7.5.

Do not start Gate 7.6 inside PR #98.
