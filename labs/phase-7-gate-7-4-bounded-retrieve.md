# Phase 7 — Gate 7.4: Real Bounded Retrieve Adapter

_Date: 2026-09-05_

## Status

**IN PROGRESS — ARCHITECTURE FROZEN / IMPLEMENTATION NOT STARTED.**

Gate 7.3 was squash-merged to `main` at:

```text
1337950ddb5948943bf361dba4c3cdc40dafaf2b
```

The real dev Knowledge Base is populated with exactly nine canonical chunks.

```text
knowledge base id: BTVJ2PBR2A
data source id:    IEL1LBE026
vector count:      9
embedding model:   amazon.titan-embed-text-v2:0
vector store:      Amazon S3 Vectors
chunking:          NONE
```

## Goal

Implement the first real retrieval-only runtime for Phase 7.

```text
RetrievalRequest
 -> bounded Bedrock Knowledge Base Retrieve
 -> raw provider response
 -> deterministic provenance/content admission
 -> RetrievedChunk[]
 -> RetrievalEvidence
```

This gate does **not** generate answers and does **not** use `RetrieveAndGenerate`.

Permanent rule:

> Retrieval output is evidence, not deterministic truth.

## Why Retrieve directly

AWS provides a direct Knowledge Base `Retrieve` operation through the
`bedrock-agent-runtime` client. This keeps retrieval independently measurable from
synthesis, preserves the Gate 7.5 Recall@K/MRR baseline, and prevents generation
quality from hiding retrieval defects.

The request surface for OpsLens v1 is intentionally smaller than the provider API:

```text
knowledgeBaseId: fixed configured KB
retrievalQuery.text: request.query
retrievalConfiguration.vectorSearchConfiguration.numberOfResults: request.top_k
```

No provider DSL is accepted from the caller.

## Search behavior

OpsLens uses Amazon S3 Vectors, so the v1 baseline is semantic retrieval only.
AWS documents hybrid search only for specific vector-store configurations with a
filterable text field; it is not available for the current S3 Vectors path.

Do not send `overrideSearchType=HYBRID`.

Do not add reranking in Gate 7.4. Gate 7.5 must measure the raw semantic baseline
first.

## Boundaries inherited from Gate 7.1

```text
query:         non-blank, <= 1,000 chars
top_k:         1..10
default top_k: 5
source_types:  typed allowlist only
provider DSL:  none
```

The AWS API itself allows a larger `numberOfResults` range. OpsLens intentionally
retains the stricter `1..10` product boundary already frozen in Gate 7.1.

## Provider response admission

A Bedrock retrieval result may carry:

```text
content
location
metadata
score
```

OpsLens must not trust those fields independently.

Admission requires all of the following:

1. result count does not exceed `request.top_k`;
2. content is text and non-empty;
3. score is absent or finite numeric evidence;
4. location is the expected S3 source shape for the frozen dev corpus;
5. S3 object key belongs to the exact `knowledge/corpus/v1/bedrock/chunks/` prefix;
6. the object key's content-addressed SHA-256 matches the returned text;
7. that SHA-256 resolves to exactly one checked Gate 7.2 manifest chunk;
8. provider metadata contains only admitted canonical fields needed for provenance;
9. provider metadata values match the checked source registry/spec/manifest authority;
10. ranks are assigned deterministically from provider response order.

The provider does not get authority to invent `chunk_id`, `document_id`, source URL,
source type, or document hash.

## Chunk identity resolution

Gate 7.3 deliberately did not invent `chunk_id` as Bedrock metadata.

Published content object keys are content-addressed:

```text
knowledge/corpus/v1/bedrock/chunks/<chunk_content_sha256>.txt
```

Therefore the retrieval adapter must resolve:

```text
returned S3 object key
 -> expected chunk_content_sha256
 -> checked manifest chunk
 -> checked corpus selection
 -> canonical chunk_id/document_id/source provenance
```

The returned text is independently hashed and must equal the expected chunk hash.

This makes the checked corpus artifacts — not Bedrock metadata — the final authority
for chunk identity.

## Filters

Gate 7.1 already contains typed optional scope fields such as source type,
vulnerability id, ecosystem, and package name.

Gate 7.4 will implement provider filters only after each typed scope can be mapped to
a deterministic Bedrock filter expression without exposing arbitrary caller DSL.

The first real vertical slice may use an unfiltered `RetrievalRequest` to prove the
core response-admission path. Typed filters can then be added incrementally inside
the same gate with explicit unit tests.

## Runtime IAM

The retrieval caller is a separate responsibility from the Gate 7.3 Knowledge Base
service role.

The future deployed retrieval identity should require only the Knowledge Base
runtime action for the exact Knowledge Base. It must not inherit:

```text
s3:PutObject
s3:GetObject for source corpus unless separately justified
s3vectors:PutVectors
s3vectors:DeleteVectors
bedrock:StartIngestionJob
IAM PassRole / provisioning authority
```

For the first local real call, the existing bootstrap Identity Center profile may be
used only as lab authority. That does not satisfy the final deployed-runtime IAM
criterion.

## Error behavior

Provider/transport failures must be wrapped with bounded, content-free diagnostics.

The adapter must fail closed on at least:

```text
unknown response fields where the contract requires exactness
non-text content
unsupported location type
unexpected S3 bucket/prefix/key
content hash mismatch
metadata/provenance mismatch
duplicate canonical chunk identity
more results than request.top_k
non-finite relevance score
pagination/nextToken unless explicitly implemented and bounded
```

For v1, one request must produce one bounded page. If Bedrock returns a `nextToken`
for a request already bounded to `top_k <= 10`, treat it as unsupported until an
explicit pagination contract exists.

## Observability

Record provider-neutral runtime evidence sufficient to evaluate retrieval before
synthesis:

```text
knowledge base reference
requested top_k
returned chunk count
ranked chunk identities
provider relevance scores when present
client elapsed time
provider request id when safely available
retry count if exposed by the SDK boundary
failure category
```

Do not interpret Bedrock relevance scores as calibrated confidence.

## Cost

Gate 7.4 adds query cost only. No synthesis-model cost belongs here.

Record the number of real Retrieve calls and use current published S3 Vectors /
Knowledge Base pricing assumptions for an estimated bounded retrieval cost. Do not
fabricate an exact per-query bill when AWS does not expose one in the response.

## Evaluation handoff

Gate 7.4 proves that a real request can be admitted into typed evidence.

Gate 7.5 owns aggregate quality measurement over the frozen fixture:

```text
Recall@1
Recall@3
Recall@5
Recall@10
MRR
provenance/source correctness
latency distribution
retrieval cost
```

## Increment plan

```text
7.4a  freeze direct-Retrieve request/response authority boundary
7.4b  build deterministic checked-corpus lookup for returned S3 keys
7.4c  implement Bedrock Retrieve adapter with fake-client tests
7.4d  implement bounded real CLI/runtime evidence
7.4e  add least-privilege retrieval IAM boundary
7.4f  perform real Retrieve success + intentional failure
7.4g  observability/cost/docs closeout + logical merge
```

## Exit criteria

- [x] Gate 7.3 squash-merged before implementation;
- [x] current official AWS Retrieve documentation revalidated;
- [x] direct `Retrieve`, not `RetrieveAndGenerate`, retained for the baseline;
- [x] semantic-only behavior for S3 Vectors recorded;
- [x] Gate 7.1 `top_k <= 10` retained despite broader provider limits;
- [ ] checked-corpus lookup maps returned content keys to canonical chunk identity;
- [ ] Bedrock adapter implemented with no arbitrary provider DSL;
- [ ] response provenance/content admission is deterministic and fail-closed;
- [ ] pagination behavior explicitly bounded;
- [ ] real Retrieve call succeeds against `BTVJ2PBR2A`;
- [ ] one intentional real failure is diagnosed;
- [ ] retrieval-only IAM boundary reviewed;
- [ ] latency/request/cost evidence recorded;
- [ ] targeted + regression CI green;
- [ ] documentation synchronized;
- [ ] PR squash-merged.

## Next authorized implementation step

Implement **7.4b only** first:

> Build an offline deterministic lookup from the checked Gate 7.2 registry/spec/
> manifest that can resolve a returned content-addressed S3 key to exactly one
> canonical chunk identity and provenance record.

Do not make a real Retrieve call until that admission lookup and fake response tests
exist.

## Official AWS references revalidated

- Amazon Bedrock — Configure and customize queries and response generation:
  https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-config.html
- Amazon Bedrock API — KnowledgeBaseRetrievalConfiguration:
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_KnowledgeBaseRetrievalConfiguration.html
- Amazon Bedrock API — KnowledgeBaseVectorSearchConfiguration:
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_KnowledgeBaseVectorSearchConfiguration.html
- Botocore — `bedrock-agent-runtime.retrieve`:
  https://docs.aws.amazon.com/botocore/latest/reference/services/bedrock-agent-runtime/client/retrieve.html
