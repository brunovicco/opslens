# Phase 7 — Gate 7.3: Knowledge Base + Vector Infrastructure

_Date: 2026-09-05_

## Status

**IN PROGRESS — ARCHITECTURE FROZEN / NO AWS RESOURCES CREATED YET.**

Gate 7.2 was squash-merged through PR #94:

```text
main commit: cbe3af9f418feade9ae76815d5ef096a6c956f12
manifest sha256: 98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
canonical documents: 6
canonical chunks: 9
```

Gate 7.3 is the first Phase 7 increment allowed to create vector infrastructure.
It must preserve the deterministic chunk/provenance authority established in
Gates 7.1 and 7.2.

## Goal

Create the minimum AWS infrastructure needed to index and later retrieve the nine
canonical remediation/documentation chunks through Amazon Bedrock Knowledge Bases,
while keeping retrieval independently testable from generation.

This gate does **not** implement answer synthesis, hybrid retrieval, reranking,
agents, or `RetrieveAndGenerate`.

## Target architecture

```text
6 immutable official source files
        |
        v
Gate 7.2 replay + checked manifest verification
        |
        v
9 canonical chunks
        |
        v
DETERMINISTIC PUBLICATION BOUNDARY
  9 text objects + metadata sidecars
        |
        v
existing OpsLens dev S3 data bucket
knowledge/corpus/v1/bedrock/
        |
        v
Bedrock S3 data source
chunking = NONE
        |
        v
Titan Text Embeddings V2
1024 dimensions / float32
        |
        v
customer-created S3 Vectors index
cosine distance
        |
        v
Bedrock customer-managed vector Knowledge Base
        |
        v
Gate 7.4 Retrieve adapter
```

Permanent authority rule:

> Bedrock may embed and retrieve canonical chunks. It does not redefine canonical
> chunk boundaries, source identity, document hashes, vulnerability truth, or risk
> policy truth.

## AWS concepts to learn in this gate

### Bedrock Managed vs customer-managed Knowledge Bases

AWS now recommends Bedrock Managed Knowledge Base as the general default for a
managed combination of ingestion, storage, indexing, embeddings, reranking, and
retrieval optimization.

OpsLens intentionally chooses the customer-managed vector Knowledge Base because
we need direct vector-store configuration and separately measurable raw retrieval
for the frozen evaluation path.

This is a workload-specific decision, not a general recommendation against the
managed offering.

### S3 Vectors

S3 Vectors provides a separate vector-bucket/index resource model. It is not the
same object namespace as the existing general-purpose S3 data bucket.

The existing data bucket remains the document source. A dedicated vector bucket and
index will store Bedrock-managed vector data.

Current Bedrock integration constraints relevant to OpsLens:

```text
search:             semantic only
vector data type:   float32
custom metadata:    <= 1 KB per vector
custom key count:   <= 35 per vector
required Bedrock non-filterable keys:
  AMAZON_BEDROCK_TEXT
  AMAZON_BEDROCK_METADATA
```

### Embeddings

The v1 embedding baseline is:

```text
Amazon Titan Text Embeddings V2
model id: amazon.titan-embed-text-v2:0
dimensions: 1024
```

The model is optimized for text retrieval. The vector index dimension is immutable
after creation, so this choice must be reviewed before the first apply.

### Chunking

Bedrock default chunking is approximately 300 tokens. That default is **not**
authorized for OpsLens because Gate 7.2 already established the canonical chunk
boundaries.

Use `NONE`, where AWS treats each source file as one chunk. OpsLens will publish
exactly nine pre-split content files.

### Metadata

Bedrock supports same-folder `<source-file>.metadata.json` sidecars. Metadata can be
available for filtering without being concatenated into the text that is embedded.

OpsLens will set provenance metadata to `includeForEmbedding = false` so similarity
is driven by source content rather than identifiers, hashes, URLs, or labels.

## Architecture decisions

ADR 0022 freezes the initial configuration:

```text
KB mode:              customer-managed vector Knowledge Base
vector store:         S3 Vectors
embedding:            Titan Text Embeddings V2
embedding dimension:  1024
vector type:          float32
distance:             cosine
Bedrock chunking:     NONE
source S3 bucket:     reuse existing OpsLens dev data bucket
source prefix:        knowledge/corpus/v1/bedrock/
reranking:            deferred
hybrid search:        deferred
customer KMS key:     deferred / not justified for public v1 corpus
```

## Why OpenSearch Serverless is not selected now

The decision was re-evaluated rather than inherited from the original proposal.
OpenSearch Serverless NextGen can now scale search and indexing to zero after ten
minutes idle when configured with zero minimum capacity. The first request after
wake-up can take 10–30 seconds.

Therefore, `OpenSearch is too expensive while idle` is no longer a sufficient
architecture argument by itself.

OpsLens still chooses S3 Vectors because the current workload is nine chunks,
semantic-only retrieval, low query frequency, and no OpenSearch-specific feature.
OpenSearch should be reconsidered if Phase 8 needs hybrid retrieval or Gate 7.5
shows a concrete search limitation.

## Cost drivers

Current AWS examples for US East document S3 Vectors pricing around:

```text
storage:         $0.06 / GB-month
PUT data:        $0.20 / GB
query requests:  $2.50 / million queries
+ query data processed / returned
```

At nine 1024-dimension vectors, storage is negligible.

Titan Text Embeddings V2 examples currently use approximately:

```text
$0.02 / million input tokens
```

The real ingestion token/cost evidence must be measured after ingestion. No
synthesis model cost belongs to this gate.

## IAM boundary

A dedicated Knowledge Bases service role will be created.

Required authority is expected to be limited to:

```text
Bedrock embedding invocation
 -> selected Titan embedding model

S3 source read
 -> existing data bucket
 -> exact knowledge/corpus/v1/bedrock/ prefix

S3 Vectors read/write/query
 -> exact knowledge vector index
```

The role must not inherit the human `opslens-bootstrap` administrative authority.

The future Gate 7.4 retrieval runtime identity is separate and must not receive
vector-write/source-ingestion permissions.

## Security risks

### Indirect prompt injection

The source files are public third-party text. Pinning and hashing them establishes
identity, not instruction trust.

Later synthesis must treat retrieved text as evidence, never as system/tool policy.

### Corpus substitution

Publishing from mutable pages or manually edited local text would break Gate 7.2
reproducibility. Publication must begin from a fresh replay of the immutable pins
and exact manifest verification.

### Provider re-chunking

Default/fixed/semantic/hierarchical Bedrock chunking could produce content pieces
that do not match the frozen chunk IDs. `NONE` prevents a second chunking authority.

### Metadata drift or overflow

S3 Vectors has stricter Bedrock metadata limits. The publication projection must
validate exact keys and encoded byte size locally before any S3 write.

### Privilege broadening during troubleshooting

An intentional IAM failure must be diagnosed from the denied action/resource. It
must not be fixed by attaching administrator or wildcard Bedrock/S3/S3Vectors
permissions.

## Failure modes to demonstrate

```text
1. fresh source replay != checked manifest
   -> publication stops before S3 write

2. metadata > 1 KB or unauthorized metadata key
   -> publication fails locally

3. missing one of nine publication objects
   -> pre-ingestion verification fails

4. missing exact KB service-role permission
   -> ingestion fails and denied action is diagnosed

5. embedding/index dimension mismatch
   -> infrastructure/ingestion fails rather than mutating the index
```

## Observability evidence to record

Gate 7.3 should record:

```text
publication object count
publication total bytes
publication manifest identity
knowledge base id
source data-source id
vector bucket/index ARN
embedding model id + dimension
ingestion job id + state
ingestion start/end timestamps
ingestion statistics returned by AWS
intentional failure action/resource/error
estimated embedding + vector cost
```

Retrieval result ranks, relevance scores, Recall@K, MRR, and query latency belong to
Gates 7.4 and 7.5.

## AIP-C01 mapping

The attached AIP-C01 exam guide specifically covers:

```text
Task 1.4
  vector store architecture
  metadata frameworks
  vector-store maintenance

Task 1.5
  document segmentation
  embedding selection
  vector search
  retrieval architecture
```

Gate 7.3 exercises these topics through an OpsLens requirement rather than adding
services only for exam coverage.

## Exit criteria

Gate 7.3 is complete only when all of the following are demonstrated:

- [ ] Gate 7.2 post-merge checkpoint corrected in repository docs;
- [x] current official AWS documentation revalidated;
- [x] Managed vs customer-managed Knowledge Base decision recorded;
- [x] S3 Vectors vs OpenSearch Serverless decision recorded;
- [x] embedding model/dimension/distance decision recorded;
- [x] `NONE` pre-split chunking decision recorded;
- [ ] deterministic nine-object publication contract implemented and tested offline;
- [ ] publication metadata schema/size limits tested;
- [ ] Terraform resources and least-privilege KB service role implemented;
- [ ] Terraform CI/security gates green;
- [ ] canonical `terraform plan` reviewed before apply;
- [ ] nine canonical chunks published from a verified real replay;
- [ ] real AWS resources applied in `dev`;
- [ ] ingestion job succeeds and is inspected;
- [ ] one meaningful intentional real failure is diagnosed;
- [ ] real embedding/vector cost evidence recorded;
- [ ] documentation/ADR/current-state/roadmap closeout complete;
- [ ] PR green and squash-merged.

## Increment plan

```text
7.3a  architecture freeze + ADR
7.3b  deterministic Bedrock publication projection (offline)
7.3c  bounded S3 publication + pre-ingestion verification
7.3d  Terraform S3 Vectors + KB + IAM + data source
7.3e  canonical plan review
7.3f  real publication + apply + ingestion
7.3g  intentional failure + cost/observability + closeout
```

## Next authorized implementation step

Implement **7.3b only**:

> Build a deterministic provider projection that takes freshly materialized Gate 7.2
> evidence, requires exact equality with the checked manifest, and produces an
> in-memory plan for exactly nine Bedrock S3 content objects plus metadata sidecars.

The first implementation must be offline and perform no S3, Bedrock, embedding, or
S3 Vectors call.

Do not create Terraform vector/Knowledge Base resources until that projection is
proven deterministic and fail-closed.

## Official AWS references revalidated

See ADR 0022 for the frozen reference list and decision rationale.
