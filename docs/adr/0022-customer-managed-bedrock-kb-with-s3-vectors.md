# ADR 0022 — Use a customer-managed Bedrock Knowledge Base with S3 Vectors

Status: Accepted for Phase 7 Gate 7.3

Date: 2026-09-05

## Context

Phase 7 separates explanatory/remediation retrieval from the deterministic structured
facts implemented through Phases 2–6.

Gate 7.1 froze provider-independent retrieval contracts and a golden evaluation set.
Gate 7.2 then materialized a reproducible corpus with exactly:

```text
6 canonical documents
9 canonical chunks
manifest sha256: 98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

The next gate must add vector infrastructure without weakening those identities.
In particular, infrastructure must not silently re-chunk the six canonical documents
into provider-defined pieces that no longer correspond to the nine frozen chunk IDs.

AWS documentation was revalidated on 2026-09-05 because Bedrock Knowledge Bases,
S3 Vectors, and OpenSearch Serverless have changed materially since the original
OpsLens proposal.

## Decision

Use an Amazon Bedrock **customer-managed vector Knowledge Base** backed by a
customer-created **Amazon S3 Vectors** vector bucket and index.

The initial Gate 7.3 configuration is:

```text
knowledge base:        customer-managed Bedrock vector Knowledge Base
source data:           existing OpsLens dev general-purpose S3 data bucket
source prefix:         knowledge/corpus/v1/bedrock/
vector store:          Amazon S3 Vectors
embedding model:       amazon.titan-embed-text-v2:0
embedding dimensions:  1024
data type:             float32
distance metric:       cosine
chunking strategy:     NONE
reranking:             deferred
hybrid search:         deferred
KMS CMK:               not introduced for the public v1 corpus
```

A dedicated S3 vector bucket/index is used for this knowledge base. The existing
OpsLens data-lake bucket remains the S3 **document source** and is not replaced by
the S3 Vectors resource.

## Why customer-managed instead of Bedrock Managed Knowledge Base

Current AWS guidance recommends Managed Knowledge Base for the general case because
Bedrock manages ingestion, storage, indexing, retrieval optimization, embeddings,
and managed reranking.

OpsLens intentionally chooses the customer-managed variant for this gate because
the product has stricter engineering requirements than the general default:

1. retrieval must remain independently testable before synthesis;
2. the vector-store choice, dimension, metric, storage cost, and IAM boundary must
   remain visible as portfolio and AIP-C01 evidence;
3. the nine Gate 7.1 chunk identities must remain directly traceable through
   ingestion and retrieval;
4. Gate 7.5 must measure the raw retrieval baseline before any managed reranking
   can obscure that baseline;
5. Phase 8 may later compare semantic-only retrieval with hybrid retrieval.

This is not a claim that Managed Knowledge Base is inferior. It is a deliberate
trade-off for transparency, reproducibility, and separately measurable retrieval.

## Why S3 Vectors

The v1 corpus has only nine chunks and is expected to have low query frequency while
Phase 7 is evaluated.

AWS describes S3 Vectors as a cost-effective vector store suitable for workloads
where sub-second semantic retrieval is acceptable and no vector infrastructure
provisioning is desired. With Bedrock Knowledge Bases it supports semantic search,
up to 1 KB of custom metadata and 35 custom metadata keys per vector, and
floating-point vectors.

That fits the current requirement without adding a search service whose advanced
capabilities are not yet used.

### OpenSearch Serverless alternative

OpenSearch Serverless remains a valid future alternative. NextGen collection groups
can now use minimum search/indexing capacity of zero and scale to zero after ten
minutes idle, so the old blanket argument that Serverless always requires a large
idle OCU baseline is no longer correct.

It is still not selected for Gate 7.3 because OpsLens does not yet require:

```text
hybrid keyword + vector search
higher sustained query throughput
advanced search/index behavior
OpenSearch-specific aggregations
```

The first request after a NextGen component has scaled to zero can also incur a
10–30 second wake-up delay. Phase 8 or measured Gate 7.5 results may justify a
revisit.

## Embedding configuration

Use Amazon Titan Text Embeddings V2:

```text
model ID:    amazon.titan-embed-text-v2:0
dimensions:  1024
```

AWS documents 1024 as the default output dimension and also supports 512 and 256.
The model is optimized for text retrieval and supports up to 8,192 input tokens or
50,000 characters.

OpsLens chooses 1024 as the v1 baseline because the corpus is tiny, so reducing
vector dimensions has negligible storage benefit while changing dimension later
requires replacing the S3 vector index.

Use `float32`, which is the S3 Vectors index data type and is required for the
Bedrock Knowledge Bases integration.

Use `cosine` distance. S3 Vectors supports cosine and Euclidean, and AWS's current
Bedrock/S3 Vectors tutorial uses Titan Text Embeddings V2 at 1024 dimensions with
cosine. This is an OpsLens v1 design choice, not a general claim that cosine is
always superior.

The S3 vector index configuration is immutable for name, dimensions, distance
metric, and non-filterable metadata keys. Any later model/dimension/metric migration
therefore requires a new index rather than an in-place mutation.

## Preserve canonical chunks: pre-split files + NONE

Gate 7.2 already owns chunk construction. Bedrock must not become a second chunking
authority.

Before ingestion, OpsLens will deterministically project the verified Gate 7.2
corpus into exactly nine S3 text objects:

```text
verified immutable source replay
 -> verify checked manifest
 -> 9 canonical chunks
 -> 9 deterministic S3 content objects
 -> 9 metadata sidecars
```

The Bedrock data source uses:

```text
chunkingStrategy = NONE
```

AWS explicitly documents `NONE` for pre-processed/pre-split documents, with each
file treated as one chunk. This preserves the invariant:

```text
1 published S3 content object == 1 Gate 7.2 canonical chunk
```

The publication process must fail closed unless the fresh replay exactly matches
the checked `knowledge/corpus/v1/manifest.json` before any object is uploaded.

Third-party source text remains absent from Git. The nine text objects are generated
only from the verified immutable sources in the single real dev environment.

## Metadata and provenance

Each content object receives a same-folder `.metadata.json` sidecar.

Only the already frozen provider-independent canonical metadata vocabulary may be
projected into Bedrock custom metadata:

```text
source_id
source_type
canonical_uri
document_id
content_sha256
title
published_at
updated_at
vulnerability_ids
ecosystem
package_name
section_path
```

Null/empty optional values do not need to consume metadata space. The publication
contract must prove that each final metadata payload remains below the stricter
Bedrock + S3 Vectors limit of 1 KB and 35 custom keys per vector.

Metadata is stored for filtering/provenance but excluded from embedding influence
(`includeForEmbedding = false`). Retrieval similarity should be driven by canonical
chunk text rather than IDs, hashes, URLs, or classification labels.

`chunk_id` and `chunk_content_sha256` are not invented as new provider metadata
fields. The later adapter must resolve the returned S3 object location against the
allowlisted publication plan and independently hash the returned chunk text before
constructing `RetrievedChunk`.

For an S3 Vectors index used by Bedrock, configure Bedrock's required non-filterable
keys:

```text
AMAZON_BEDROCK_TEXT
AMAZON_BEDROCK_METADATA
```

## S3 source location

Reuse the existing encrypted, versioned, private OpsLens dev data bucket and scope
the Bedrock data source to:

```text
knowledge/corpus/v1/bedrock/
```

Creating another general-purpose S3 source bucket would add policy, lifecycle,
observability, and cost surface without solving a current requirement.

The existing bucket uses SSE-S3 and blocks public access. The v1 corpus contains
public official documentation/advisories, so a customer-managed KMS key is not
justified in this gate. A later private/proprietary corpus would require a new
security decision.

## IAM and trust boundaries

Create a dedicated Bedrock Knowledge Bases service role rather than reusing the
human bootstrap/admin identity.

The role trust policy uses `bedrock.amazonaws.com` and scopes source account / source
ARN conditions as supported by AWS. The permissions are limited to the resources
needed for ingestion:

```text
bedrock:InvokeModel
  -> selected Titan Text Embeddings V2 model

s3:GetObject / s3:ListBucket as required
  -> existing data bucket + exact knowledge prefix

s3vectors:PutVectors
s3vectors:GetVectors
s3vectors:DeleteVectors
s3vectors:QueryVectors
s3vectors:GetIndex
  -> exact S3 vector index ARN
```

The future application retrieval identity is a different responsibility. Gate 7.4
will grant only the Bedrock retrieval authority it needs; it will not inherit vector
write or source-ingestion permissions.

## Ingestion ownership

Terraform will own durable infrastructure:

```text
S3 vector bucket/index
Bedrock KB service role and policies
Bedrock vector Knowledge Base
S3 data source configuration
```

Terraform will **not** own third-party chunk text and will not run source replay.

Starting/synchronizing an ingestion job is an explicit operational step after the
verified publication has completed. This prevents Terraform state from becoming an
implicit corpus-authoring mechanism.

## Reranking and hybrid retrieval

Neither feature is enabled in Gate 7.3.

Gate 7.5 must first establish the semantic retrieval baseline with Recall@K and MRR.
A reranker may be added only if measured retrieval quality justifies its additional
latency, model cost, and evaluation complexity.

S3 Vectors supports semantic search but not hybrid search. Hybrid retrieval is
already a later OpsLens concern and should not be pulled forward solely to exercise
a feature.

## Cost model

The current S3 Vectors US East pricing example documents:

```text
vector storage:  $0.06 / GB-month
vector writes:   $0.20 / GB
query request:   $2.50 / million queries
plus data processed / returned charges
```

For nine 1024-dimension vectors, vector storage and write costs are effectively
negligible at portfolio scale.

Titan Text Embeddings V2 is currently priced at approximately `$0.02 / million`
input tokens in AWS examples. The exact measured Gate 7.3 ingestion cost will be
recorded after the first real ingestion rather than guessed from source file size.

No synthesis cost belongs to Gate 7.3.

## Observability

Gate 7.3 must capture enough evidence to diagnose at least:

```text
publication object count and byte count
ingestion job id / status / timestamps
ingestion statistics when returned
knowledge base id / data source id / vector index ARN
embedding model id and dimensions
intentional ingestion failure reason
```

Application retrieval latency and retrieved ranks/scores belong to Gate 7.4/7.5.

## Failure modes to test

At minimum:

1. canonical replay no longer matches the checked Gate 7.2 manifest — publication
   must stop before S3 writes;
2. metadata exceeds the Bedrock/S3 Vectors budget — publication must fail locally;
3. one expected chunk/object is missing — ingestion or pre-ingestion verification
   must fail;
4. Bedrock service role lacks one exact required permission — real ingestion must
   fail and be diagnosable without broadening to administrator access;
5. embedding/vector dimension mismatch — infrastructure/ingestion must reject the
   mismatch rather than silently changing the model/index.

## AIP-C01 relevance

This gate directly exercises the exam guide's vector-store and retrieval topics:

```text
Task 1.4  vector store architecture + metadata + maintenance
Task 1.5  document segmentation + embeddings + vector search
```

The certification is a learning benefit, not the reason for selecting a service.
Every selected component solves an explicit OpsLens requirement.

## Alternatives rejected for v1

### Bedrock Managed Knowledge Base

Excellent general default, but rejected for this gate because OpsLens explicitly
needs direct vector-store configuration and separately measurable raw retrieval.

### OpenSearch Serverless

Deferred until hybrid search, higher sustained throughput, or advanced search
features are demonstrated requirements.

### Aurora PostgreSQL / pgvector

Adds database lifecycle, capacity, schema, and operational concerns that the
nine-chunk semantic-only corpus does not need.

### Bedrock default/fixed/semantic/hierarchical chunking

Rejected because Gate 7.2 already owns canonical chunk boundaries. Provider
re-chunking would break the frozen evaluation identity.

### Reranking now

Rejected until baseline retrieval is measured.

## Consequences

Positive:

- Gate 7.1/7.2 chunk identity survives infrastructure ingestion;
- vector infrastructure remains explicit and independently reviewable;
- retrieval can be evaluated without synthesis or managed reranking;
- v1 idle/storage cost remains extremely small;
- infrastructure does not vendor or execute third-party source code.

Trade-offs:

- OpsLens owns more infrastructure than a Managed Knowledge Base;
- S3 Vectors is semantic-only, so hybrid search requires a later change;
- vector-index configuration is immutable and migration requires replacement;
- a deterministic publication step is required before ingestion.

## Official references revalidated on 2026-09-05

- Amazon Bedrock — Build a managed knowledge base:
  https://docs.aws.amazon.com/bedrock/latest/userguide/kb-build-managed.html
- Amazon S3 — Using S3 Vectors with Amazon Bedrock Knowledge Bases:
  https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-bedrock-kb.html
- Amazon Bedrock — Prerequisites for a customer-created vector store:
  https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-setup.html
- Amazon Bedrock — Titan Text Embeddings models:
  https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html
- Amazon Bedrock — Knowledge Base chunking:
  https://docs.aws.amazon.com/bedrock/latest/userguide/kb-chunking.html
- Amazon Bedrock — S3 data-source connector and metadata:
  https://docs.aws.amazon.com/bedrock/latest/userguide/s3-data-source-connector.html
- Amazon Bedrock — Knowledge Base service-role permissions:
  https://docs.aws.amazon.com/bedrock/latest/userguide/kb-permissions.html
- Amazon S3 pricing:
  https://aws.amazon.com/s3/pricing/
- Amazon OpenSearch Serverless — scale to zero:
  https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-scale-to-zero.html
