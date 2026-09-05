# Phase 7 — Gate 7.3: Knowledge Base + Vector Infrastructure

_Date: 2026-09-05_

## Status

**COMPLETE — REAL AWS EVIDENCE RECORDED / PR MERGE PENDING.**

Gate 7.2 was squash-merged through PR #94. The frozen corpus identity used by this gate is:

```text
manifest sha256: 98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
canonical documents: 6
canonical chunks: 9
```

Gate 7.3 created the minimum vector infrastructure required for a separately measurable Bedrock Knowledge Base retrieval baseline while preserving the deterministic chunk/provenance authority established in Gates 7.1 and 7.2.

This gate does **not** implement answer synthesis, hybrid retrieval, reranking, agents, or `RetrieveAndGenerate`.

## Implemented architecture

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
  9 text objects + 9 metadata sidecars
        |
        v
opslens-dev-data-487757851499-us-east-1
knowledge/corpus/v1/bedrock/
        |
        v
Bedrock S3 data source
chunking = NONE
        |
        v
Titan Text Embeddings V2
1024 dimensions / FLOAT32
        |
        v
Amazon S3 Vectors
cosine distance
        |
        v
customer-managed Bedrock vector Knowledge Base
        |
        v
Gate 7.4 bounded Retrieve adapter
```

Permanent authority rule:

> Bedrock may embed and retrieve canonical chunks. It does not redefine canonical
> chunk boundaries, source identity, document hashes, vulnerability truth, or risk
> policy truth.

## Frozen AWS configuration

ADR 0022 freezes the baseline:

```text
KB mode:              customer-managed vector Knowledge Base
vector store:         Amazon S3 Vectors
embedding:            amazon.titan-embed-text-v2:0
embedding dimension:  1024
vector type:          FLOAT32
distance:             cosine
Bedrock chunking:     NONE
source S3 bucket:     opslens-dev-data-487757851499-us-east-1
source prefix:        knowledge/corpus/v1/bedrock/
reranking:            deferred
hybrid search:        deferred
customer KMS key:     deferred / not justified for public v1 corpus
```

Real resources:

```text
knowledge base id:     BTVJ2PBR2A
data source id:        IEL1LBE026
knowledge base ARN:    arn:aws:bedrock:us-east-1:487757851499:knowledge-base/BTVJ2PBR2A
service role ARN:      arn:aws:iam::487757851499:role/OpsLensDevBedrockKnowledgeBaseRole
vector bucket ARN:     arn:aws:s3vectors:us-east-1:487757851499:bucket/opslens-dev-knowledge-487757851499-us-east-1
vector index ARN:      arn:aws:s3vectors:us-east-1:487757851499:bucket/opslens-dev-knowledge-487757851499-us-east-1/index/opslens-dev-remediation-v1
```

A fresh post-apply Terraform plan returned **No changes**.

## Why S3 Vectors

OpsLens currently needs semantic-only retrieval for nine canonical chunks. It does not yet require OpenSearch-specific hybrid search, high sustained throughput, advanced indexing, or aggregations.

OpenSearch Serverless NextGen was explicitly re-evaluated because it can now scale to zero. It remains deferred because no current requirement justifies the additional search surface. Aurora/pgvector is also deferred because the nine-chunk corpus does not justify database lifecycle/capacity/schema concerns.

## Embedding and chunking

The v1 baseline is:

```text
Amazon Titan Text Embeddings V2
model id: amazon.titan-embed-text-v2:0
dimensions: 1024
data type: FLOAT32
distance metric: cosine
```

Bedrock chunking is `NONE`. Each published text object is already one Gate 7.2 canonical chunk, so provider re-chunking is not authorized.

## Deterministic publication

Publication starts from a fresh replay of the six immutable pins and requires byte-for-byte equality with the checked manifest before any S3 write.

Real successful publication evidence:

```text
source manifest sha256:
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418

payload count:      18
content objects:     9
metadata sidecars:   9
total bytes:         14,928
```

The nine content objects remain content-addressed by their canonical chunk SHA-256 values. The successful compact sidecars were independently verified by S3 checksum/size/type evidence and were:

```text
minimum sidecar bytes: 394
maximum sidecar bytes: 493
Bedrock/S3 Vectors limit: 1024 bytes
```

The projection retains only the frozen canonical metadata vocabulary. It uses Bedrock's simplified metadata representation, equivalent to metadata excluded from embedding influence, so identifiers/hashes/URLs do not drive similarity.

## Real metadata failure and fix

The first real ingestion job was:

```text
ingestion job id: 4S4OLDKNCZ
status: COMPLETE
documents scanned: 9
new documents indexed: 0
vectors materialized: 0
```

`GetIngestionJob` exposed the actual failure reason:

```text
Ignored 9 files as the associated metadata was larger than service limit of
MaximumFileSizeSupported: 1024 bytes
```

The original projection validated logical metadata below 1 KB but serialized a verbose typed sidecar whose final files were about 1.3–1.4 KB. The fix moved to the supported compact metadata representation and added an explicit fail-closed check on the **final serialized sidecar bytes** at the deterministic publication boundary.

This is retained as a production-relevant lesson:

> Validate the provider-consumed serialization, not only the logical object that precedes serialization.

No Knowledge Base, data source, vector bucket, or vector index was recreated.

## Real successful ingestion

After deterministic republication, the second ingestion job succeeded:

```text
ingestion job id: WZRUGOFZPI
status: COMPLETE
startedAt: 2026-09-05T20:41:46.010046+00:00
updatedAt: 2026-09-05T20:41:57.155598+00:00
observed ingestion duration: 11.145552 seconds

numberOfDocumentsScanned:          9
numberOfMetadataDocumentsScanned:  9
numberOfNewDocumentsIndexed:       9
numberOfModifiedDocumentsIndexed:  0
numberOfMetadataDocumentsModified: 0
numberOfDocumentsDeleted:          0
numberOfDocumentsFailed:           0
numberOfDocumentsSkipped:          0
failure reasons:                   none
```

A strongly consistent S3 Vectors listing immediately returned exactly **9 vector keys**.

This proves the real path:

```text
verified canonical corpus
 -> bounded S3 publication
 -> Bedrock ingestion
 -> Titan Text Embeddings V2
 -> S3 Vectors materialization
```

## IAM and trust-boundary evidence

The dedicated Knowledge Bases service role has only the required source/model/vector responsibilities. The future Gate 7.4 retrieval runtime identity remains separate and must not inherit source-ingestion/vector-write authority.

A real negative control attempted to assume the service role from the human IAM Identity Center bootstrap session:

```text
operation: sts:AssumeRole
caller: AWSReservedSSO_OpsLensBootstrapAdmin_.../brunovicco
target: OpsLensDevBedrockKnowledgeBaseRole
result: AccessDenied
```

The denial is expected and confirms that the Bedrock service role is not directly assumable by the human bootstrap identity. No trust policy was broadened to make the test pass.

## Credential-chain failure evidence

During republication, AWS CLI commands could still use the IAM Identity Center session while the botocore process inside `uv run` failed with:

```text
provider_type=TokenRetrievalError
```

The publisher's adapter was improved to retain only bounded provider error categories (`provider_code` or safe exception type) without exposing response bodies or corpus content.

The local lab recovered by exporting temporary already-resolved credentials from AWS CLI into the shell process. No persistent access key was created or stored.

## Cost discipline

The Gate 7.3 corpus is intentionally tiny: nine 1024-dimensional FLOAT32 vectors plus compact metadata. Vector storage is therefore negligible at portfolio scale.

S3 Vectors pricing is usage based, and small PUTs have service billing granularity that dominates the logical payload size. Titan Text Embeddings V2 charges by input token usage. The ingestion API does not return exact embedding token counts, so this gate records the measured workload shape and published pricing assumptions rather than fabricating an exact bill from source byte count.

No synthesis model cost belongs to Gate 7.3.

The cost conclusion for this nine-chunk dev validation is therefore:

```text
bounded one-time embedding work: very small
vector storage: negligible
query cost: none in Gate 7.3
synthesis cost: none
```

Gate 7.4/7.5 will measure real retrieval calls separately.

## Observability evidence

Recorded real evidence includes:

```text
publication object count + total bytes
manifest identity
knowledge base id / ARN
data source id
vector bucket/index ARN
embedding model + dimension
ingestion job id + status + timestamps
ingestion statistics
vector count after ingestion
real provider failure reason for oversized metadata
real credential-chain failure category
real service-role trust-boundary AccessDenied
```

Retrieval ranks, relevance scores, Recall@K, MRR, and query latency belong to Gates 7.4 and 7.5.

## Security boundaries

### Indirect prompt injection

The source files are public third-party text. Pinning and hashing establish identity, not instruction trust. Later synthesis must treat retrieved text as evidence, never as system/tool/policy authority.

### Corpus substitution

Publishing begins from immutable pins and exact manifest verification. Mutable pages or manually edited local text cannot become corpus authority.

### Provider re-chunking

`chunkingStrategy = NONE` prevents Bedrock from becoming a second chunk-construction authority.

### Privilege broadening during troubleshooting

Real failures were diagnosed without attaching administrator/wildcard Bedrock/S3/S3Vectors permissions to the service role and without weakening its trust relationship.

## AIP-C01 mapping

This gate directly exercises the exam guide's vector-store and retrieval architecture concerns:

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

The certification is a learning benefit, not the reason the services were selected.

## CI evidence

Latest validated functional head before documentation closeout:

```text
head: efe5d782c373ff0a40a99473e8ec744538c8638d
Python CI #199:    SUCCESS
Terraform CI #206: SUCCESS
```

The closeout documentation commit must also pass the same PR quality gates before merge.

## Exit criteria

- [x] Gate 7.2 post-merge checkpoint corrected for this gate;
- [x] current official AWS documentation revalidated;
- [x] Managed vs customer-managed Knowledge Base decision recorded;
- [x] S3 Vectors vs OpenSearch Serverless decision recorded;
- [x] embedding model/dimension/distance decision recorded;
- [x] `NONE` pre-split chunking decision recorded;
- [x] deterministic publication contract implemented and tested offline;
- [x] final serialized metadata schema/size limits tested;
- [x] Terraform resources and least-privilege KB service role implemented;
- [x] Terraform CI/security gates green;
- [x] canonical Terraform plans reviewed before apply;
- [x] nine canonical chunks published from a verified real replay;
- [x] real AWS resources applied and reconciled in `dev`;
- [x] ingestion job succeeds and is inspected;
- [x] exactly nine vectors materialized;
- [x] meaningful real failure paths diagnosed;
- [x] IAM trust-boundary negative control demonstrated;
- [x] bounded cost rationale recorded;
- [x] Gate 7.3 closeout evidence documented;
- [ ] final documentation commit green;
- [ ] PR #95 ready for review and squash-merged.

## Increment record

```text
7.3a  architecture freeze + ADR                         COMPLETE
7.3b  deterministic Bedrock publication projection     COMPLETE
7.3c  bounded S3 publication + verification            COMPLETE
7.3d  Terraform S3 Vectors + KB + IAM + data source    COMPLETE
7.3e  canonical plan review + real apply               COMPLETE
7.3f  real publication + ingestion + vector proof      COMPLETE
7.3g  failure + IAM + cost/observability closeout      COMPLETE
```

## Next authorized implementation step

After PR #95 is green and squash-merged, begin **Gate 7.4 — Real bounded Retrieve adapter**.

Gate 7.4 must use Bedrock Knowledge Base `Retrieve` directly, not `RetrieveAndGenerate`, so retrieval can be measured independently before synthesis. The runtime identity must be separate from the ingestion service role and receive only the retrieval authority it requires.

## Official AWS references revalidated

See ADR 0022 for the frozen reference list and decision rationale.
