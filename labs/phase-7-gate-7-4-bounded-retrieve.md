# Phase 7 — Gate 7.4: Real Bounded Retrieve Adapter

_Date: 2026-09-05_

## Status

**IN PROGRESS — 7.4a–7.4d IMPLEMENTED AND QUALITY-GATED / REAL RETRIEVE PENDING.**

Gate 7.3 was squash-merged to `main` at:

```text
1337950ddb5948943bf361dba4c3cdc40dafaf2b
```

The real dev Knowledge Base remains populated with exactly nine canonical chunks:

```text
knowledge base id: BTVJ2PBR2A
data source id:    IEL1LBE026
vector count:      9
embedding model:   amazon.titan-embed-text-v2:0
vector store:      Amazon S3 Vectors
chunking:          NONE
```

## Goal

Implement and validate the first real retrieval-only runtime for Phase 7.

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

The OpsLens v1 request surface is intentionally smaller than the provider API:

```text
knowledgeBaseId: fixed configured KB
retrievalQuery.text: validated request.query
retrievalConfiguration.vectorSearchConfiguration.numberOfResults: request.top_k
```

No provider DSL is accepted from the caller. No search-type override, reranking,
implicit pagination, or generation configuration is sent.

## Search behavior

OpsLens uses Amazon S3 Vectors, so the v1 baseline is semantic retrieval only.
AWS documents hybrid search only for vector-store configurations that support it;
the current S3 Vectors path remains semantic-only.

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

The AWS API allows a broader `numberOfResults` range. OpsLens intentionally retains
the stricter `1..10` product boundary already frozen in Gate 7.1.

The first real vertical slice is unfiltered. If a caller supplies any typed Gate 7.1
scope (`source_types`, vulnerability IDs, ecosystem, or package name) before a
reviewed deterministic Bedrock-filter translation exists, the application fails
**before** the provider call rather than silently discarding that scope.

## Implemented deterministic checked-corpus catalog — 7.4b

`application/retrieval_catalog.py` derives runtime lookup authority only from the
checked Gate 7.2 manifest.

Published content keys remain content-addressed:

```text
knowledge/corpus/v1/bedrock/chunks/<chunk_content_sha256>.txt
```

The catalog resolves:

```text
returned S3 object key
 -> expected chunk_content_sha256
 -> checked manifest chunk
 -> canonical chunk_id
 -> canonical document_id/source_id/source_type/canonical_uri
 -> canonical document hash/title/section path
```

The catalog requires globally unique content keys, chunk digests, and chunk IDs and
fails closed on malformed, unknown, out-of-prefix, or ambiguous keys.

## Implemented provider response admission — 7.4c

The application and adapter now admit a Bedrock retrieval result only when all of
the following hold:

1. result count does not exceed `request.top_k`;
2. content type is `TEXT` and content is non-empty/bounded;
3. relevance score is absent or finite numeric evidence;
4. location is an exact S3 URI in the expected source bucket;
5. the S3 key has the frozen content-addressed chunk shape;
6. the key resolves to exactly one checked manifest chunk;
7. returned UTF-8 text SHA-256 equals the expected canonical chunk hash;
8. returned UTF-8 byte count equals checked manifest evidence;
9. required canonical metadata matches checked corpus authority exactly;
10. unknown non-provider metadata is rejected;
11. Bedrock-reserved `x-amz-bedrock-kb-*` metadata remains non-authoritative and is
    cross-checked when it restates source URI or data-source identity;
12. ranks are assigned deterministically from provider response order.

Bedrock `documentId` and provider-owned chunk identifiers are not canonical OpsLens
identity.

The provider does not get authority to invent `chunk_id`, `document_id`, source URL,
source type, document hash, title, or section path.

### Pagination and guardrail behavior

A v1 request is exactly one bounded `Retrieve` operation. `nextToken` is rejected
until an explicit pagination budget/contract is introduced.

A response reporting `guardrailAction=INTERVENED` is not silently admitted as
ordinary retrieval evidence.

## Implemented runtime adapter

`adapters/bedrock_retrieval.py` sends exactly one direct semantic request:

```text
knowledgeBaseId=<validated configured id>
retrievalQuery={"text": <validated query>}
retrievalConfiguration={
  "vectorSearchConfiguration": {
    "numberOfResults": <validated top_k>
  }
}
```

It captures bounded provider-neutral runtime evidence:

```text
provider request id
SDK retry attempts
client elapsed milliseconds
returned result count
rank + provider relevance score
```

Provider/transport errors expose only a safe provider code when available, otherwise
the exception class. Provider response bodies/messages and retrieved content are not
copied into operational error messages.

## Checked manifest loading for the hot path — 7.4d

The real retrieval CLI does **not** replay six external source repositories before
every query.

`load_corpus_manifest()` strictly parses the checked hash-only
`knowledge/corpus/v1/manifest.json` into existing typed manifest contracts. Unknown
schema fields, invalid types, malformed hashes/identities, and impossible byte counts
fail closed through the existing domain validation.

This preserves the separation:

```text
corpus acquisition/replay time
 -> external immutable pins + deterministic manifest verification

retrieval request time
 -> checked local manifest + catalog
 -> one bounded Bedrock Retrieve call
```

## Real Retrieve CLI

`cli/run_bedrock_retrieve.py` is ready for the first real call.

Required explicit authority:

```text
query
knowledge base id
data source id
source bucket
```

The region is frozen to `us-east-1`; the manifest defaults to the checked v1 file;
`top_k` defaults to 5 and remains bounded to 1..10.

The CLI output intentionally contains **no retrieved chunk text**. It serializes:

```text
backend
knowledge base id
query SHA-256 (not raw query text)
requested top_k
provider request id
retry count
client elapsed ms
returned count
ranked canonical chunk/document/source IDs
canonical URLs/title/section path
content hashes
provider relevance scores
```

## Runtime IAM boundary

The retrieval caller is a separate responsibility from the Gate 7.3 Knowledge Base
service role.

Current AWS IAM documentation allows `bedrock:Retrieve` to be scoped to the exact
Knowledge Base ARN. A future deployed OpsLens retrieval runtime therefore needs only
that retrieval authority for this KB; it must not inherit ingestion/vector-write or
provisioning authority.

It must not receive merely for retrieval:

```text
s3:PutObject
s3:GetObject for source corpus unless separately justified
s3vectors:PutVectors
s3vectors:DeleteVectors
bedrock:StartIngestionJob
iam:PassRole
infrastructure provisioning authority
```

No deployed application runtime principal exists yet. Creating an unattached role or
policy solely to satisfy a checklist would add dead IAM surface. Therefore the first
real call uses temporary human/bootstrap Identity Center credentials strictly as lab
validation authority; this does **not** become the future production runtime
identity. The exact least-privilege deployed attachment remains deferred until a
real compute/runtime principal exists.

## Error behavior proven offline

Tests cover fail-closed behavior for:

```text
unimplemented typed filters
nextToken/pagination
more results than top_k
non-TEXT result content
unexpected S3 bucket
unknown content-addressed key
content SHA-256 mismatch
content byte-count mismatch
canonical metadata mismatch
unknown non-provider metadata
reserved source URI / data-source contradiction
non-finite relevance score
guardrail intervention
unknown provider response field
provider AccessDenied-style error diagnostics
non-service exception diagnostics
```

## Quality evidence before the first real call

Functional head before this documentation update:

```text
9dc5e2d3d6915623dbe2efa992d52719c92765e4
Python CI #220: SUCCESS

Knowledge Retrieval Ruff:     PASS
Knowledge Retrieval Pyright:  0 errors / 0 warnings / 0 informations
Knowledge Retrieval pytest:   91 passed in 0.76s

Correlation regression:              PASS
Repository Intelligence regression:  PASS
Risk Policy regression:              PASS
Semantic Query regression:           PASS
```

No real `Retrieve` call was made by these tests.

## Observability

Gate 7.4 records provider-neutral runtime evidence sufficient to evaluate retrieval
before synthesis:

```text
knowledge base reference
requested top_k
returned chunk count
ranked checked chunk identities
provider relevance scores when present
client elapsed time
provider request id
SDK retry count
failure category
```

Do not interpret Bedrock relevance scores as calibrated confidence.

## Cost

Gate 7.4 adds retrieval-query cost only. No synthesis-model cost belongs here.

The closeout will record the exact number of real `Retrieve` calls and current
published S3 Vectors/Knowledge Base pricing assumptions. An exact per-query bill must
not be fabricated when the provider response does not expose one.

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
7.4a  freeze direct-Retrieve request/response authority boundary       COMPLETE
7.4b  deterministic checked-corpus S3-key lookup                      COMPLETE
7.4c  Bedrock Retrieve adapter + fake-client admission tests          COMPLETE
7.4d  bounded real CLI/runtime evidence                               COMPLETE
7.4e  least-privilege retrieval IAM boundary review                   COMPLETE / ATTACHMENT DEFERRED
7.4f  real Retrieve success + intentional real failure                NEXT
7.4g  observability/cost/docs closeout + logical merge                PENDING
```

## Exit criteria

- [x] Gate 7.3 squash-merged before implementation;
- [x] current official AWS Retrieve documentation revalidated;
- [x] direct `Retrieve`, not `RetrieveAndGenerate`, retained for the baseline;
- [x] semantic-only behavior for S3 Vectors recorded;
- [x] Gate 7.1 `top_k <= 10` retained despite broader provider limits;
- [x] checked-corpus lookup maps returned content keys to canonical chunk identity;
- [x] Bedrock adapter implemented with no arbitrary provider DSL;
- [x] response provenance/content admission is deterministic and fail-closed;
- [x] pagination behavior explicitly bounded;
- [x] checked manifest loader avoids external replay in the retrieval hot path;
- [x] bounded real CLI emits content-free operational evidence;
- [x] retrieval-only IAM boundary reviewed;
- [x] targeted + regression CI green before real invocation;
- [ ] real Retrieve call succeeds against `BTVJ2PBR2A`;
- [ ] one intentional real provider failure is diagnosed;
- [ ] real latency/request/cost evidence recorded;
- [ ] documentation synchronized with real evidence;
- [ ] final PR CI green;
- [ ] PR squash-merged.

## Next authorized step

Run exactly one real unfiltered semantic `Retrieve` against the existing dev KB with
`top_k=5` through the versioned CLI. Inspect the provider response through the
strict admission boundary before changing any response-shape assumption.

If real AWS evidence differs from the documented provider shape, fail closed,
inspect the exact non-sensitive discrepancy, update the contract deliberately, and
re-run CI before another real request.

Do not start synthesis or Gate 7.5 evaluation yet.

## Official AWS references revalidated

- Amazon Bedrock — Retrieve data and generate AI responses with knowledge bases:
  https://docs.aws.amazon.com/bedrock/latest/userguide/kb-how-retrieval.html
- Amazon Bedrock — Test a knowledge base with Retrieve:
  https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-retrieve.html
- Amazon Bedrock — Configure and customize queries:
  https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-config.html
- Amazon Bedrock API — KnowledgeBaseRetrievalResult:
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_KnowledgeBaseRetrievalResult.html
- Amazon Bedrock API — RetrievalResultLocation:
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_RetrievalResultLocation.html
- Amazon Bedrock API — RetrievalResultS3Location:
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_RetrievalResultS3Location.html
- Amazon Bedrock API — RetrievalResultContent:
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_RetrievalResultContent.html
- Botocore — `bedrock-agent-runtime.retrieve`:
  https://docs.aws.amazon.com/botocore/latest/reference/services/bedrock-agent-runtime/client/retrieve.html
- Amazon Bedrock — Knowledge Base runtime permissions:
  https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-prereq-permissions-general.html
