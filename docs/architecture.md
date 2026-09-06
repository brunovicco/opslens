# OpsLens Architecture

_Last updated: 2026-09-06_

This document is the accumulated architecture baseline through **Phase 7 — Gate 7.4: Real bounded Retrieve adapter**.

The next architecture boundary is **Phase 7 — Gate 7.5: Retrieval evaluation**.

## 1. Purpose

OpsLens is an open-source software supply-chain and threat-intelligence platform on AWS.

Product goal:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, and which findings should I prioritize?

Core invariant:

> **Agents reason. Code verifies evidence.**

Additional permanent boundaries:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

## 2. Permanent architectural principles

Unless changed by an explicit ADR:

- raw third-party evidence is preserved before enrichment or interpretation;
- exact source versions and content hashes participate in provenance;
- package identity normalization, version/range matching, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS evidence, and Risk Policy remain deterministic;
- semantic-query validation and SQL compilation remain deterministic;
- canonical corpus normalization, selection, hashing, and checked manifest identity remain deterministic;
- retrieval evidence admission and citation projection remain deterministic;
- provider/model outputs are evidence or proposals, not authority over structured truth;
- LLMs may classify, plan, route, synthesize, and explain only over validated evidence;
- retrieved explanatory text never becomes a second authority for structured threat facts;
- third-party repository/source content is untrusted data to inspect, never code to execute;
- schema, provenance, authority, or exact-evidence mismatches fail closed;
- IAM uses least privilege and responsibility separation;
- AWS services are introduced only for concrete requirements;
- cost and observability are architectural requirements;
- one real `dev` environment is preferred over fictional portfolio environments.

## 3. Current system shape

### Structured vulnerability/risk path

```text
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
 -> deterministic correlation
 -> immutable Repository Intelligence
 -> RepositoryAnalysisResult
 -> deterministic Risk Policy v1
 -> RiskPrioritizationResult
```

### Phase 6 structured semantic-query path

```text
natural-language factual question
 -> bounded Bedrock planner
 -> structured proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured result evidence
```

The planner has no arbitrary SQL authority.

### Phase 7 explanatory/remediation path through Gate 7.4

```text
explicitly authorized official sources
 -> immutable repository/commit/path pins
 -> bounded GET-only inert-text acquisition
 -> deterministic normalization + exact section selection
 -> 9 content-addressed canonical chunks
 -> checked hash-only manifest
 -> deterministic S3 publication
 -> Bedrock S3 data source / chunking NONE
 -> Titan Text Embeddings V2 / 1024 / FLOAT32
 -> Amazon S3 Vectors / cosine
 -> customer-managed Bedrock Knowledge Base
 -> bounded direct Retrieve
 -> strict provider parser
 -> checked-corpus S3/hash/metadata reconciliation
 -> RetrievedChunk[]
 -> RetrievalEvidence
```

Retrieval is now real and independently measurable. Synthesis remains a later authority.

## 4. AWS foundation

```text
environment:             dev
primary workload Region: us-east-1
AWS account:             487757851499
IaC:                     Terraform
human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
```

Only one real environment exists: `dev`.

Human administration uses temporary IAM Identity Center credentials. GitHub Actions assumes deployment roles through OIDC; persistent AWS access keys are not stored in GitHub.

Primary storage:

```text
Data:       opslens-dev-data-487757851499-us-east-1
Artifacts:  opslens-dev-artifacts-487757851499-us-east-1
TF state:   opslens-dev-tfstate-487757851499-us-east-1
```

Analytics:

```text
Glue database:    opslens_dev
Athena workgroup: opslens-dev
scan cutoff:      10,485,760 bytes
```

Phase 7 owns a dedicated S3 Vectors bucket/index separate from the general-purpose S3 source-data bucket.

## 5. Threat Intelligence Data Lake — Phase 2

Phase 2 preserves source-local authority rather than flattening NVD, KEV, EPSS, and GHSA into one lossy universal record.

Key properties include explicit EPSS snapshot dates, CISA KEV complete-catalog semantics, NVD source provenance/watermarking, and exact GHSA source evidence.

## 6. Vulnerability Correlation Engine — Phase 3

```text
package/version/purl
 + exact GHSA vulnerable-range evidence
 -> deterministic PEP 440 evaluation
 -> affected | not_affected | unsupported
 -> CVE/GHSA/NVD reconciliation
 -> content-addressed correlation evidence
```

Permanent rule:

> **No LLM decides vulnerability applicability.**

## 7. Repository Intelligence — Phase 4

```text
public repository
 -> immutable repository/commit/tree identity
 -> bounded GET-only GitHub acquisition
 -> exact inert root uv.lock bytes
 -> deterministic TOML parsing
 -> canonical PyPI dependencies
 -> deterministic vulnerability applicability
 -> NVD/CVSS + KEV + EPSS evidence
 -> RepositoryAnalysisResult
```

Repository findings prove repository-risk evidence for an immutable snapshot. They do not prove runtime presence or exploitability.

## 8. Risk Prioritization Engine — Phase 5

```text
RepositoryAnalysisResult
 -> pure deterministic Risk Policy v1
 -> factor contributions
 -> priority score + tier
 -> completeness / review_required
 -> deterministic aggregate ranking
```

The priority value is an OpsLens policy score, not exploit probability, CVSS, EPSS, or runtime exposure.

## 9. Semantic Query Layer — Phase 6

```text
question
 -> bounded Bedrock planner
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded Athena execution
 -> structured evidence
```

ADRs:

```text
0020 No unrestricted text-to-SQL
0021 Bounded Bedrock semantic-query planner
```

## 10. Knowledge Retrieval — Phase 7 through Gate 7.4

### 10.1 Provider-independent retrieval contract

Gate 7.1 froze:

```text
KnowledgeDocument
RetrievalRequest
RetrievedChunk
RetrievalEvidence
Citation
```

Bounds:

```text
query:         non-blank, <= 1,000 chars
top_k:         1..10
default top_k: 5
provider DSL:  none
```

Citation provenance is projected from admitted chunks, never trusted from model-authored URLs/source IDs.

### 10.2 Canonical corpus authority

Gate 7.2 authorizes six official source files through immutable repository/commit/path pins.

Frozen corpus identity:

```text
manifest id: knowledge-corpus-manifest:v1
documents:   6
chunks:      9
sha256:      98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

The checked manifest stores provenance/hashes, not third-party source/chunk text.

### 10.3 Gate 7.3 vector baseline — COMPLETE

ADR 0022 selects a customer-managed Bedrock vector Knowledge Base backed by S3 Vectors.

Validated configuration:

```text
knowledge base id:     BTVJ2PBR2A
data source id:        IEL1LBE026
source prefix:         knowledge/corpus/v1/bedrock/
chunking:              NONE
embedding model:       amazon.titan-embed-text-v2:0
embedding dimensions:  1024
embedding data type:   FLOAT32
vector store:          Amazon S3 Vectors
distance:              cosine
reranking:             deferred
hybrid search:         deferred
```

Real resource ARNs:

```text
KB:
arn:aws:bedrock:us-east-1:487757851499:knowledge-base/BTVJ2PBR2A

service role:
arn:aws:iam::487757851499:role/OpsLensDevBedrockKnowledgeBaseRole

vector bucket:
arn:aws:s3vectors:us-east-1:487757851499:bucket/opslens-dev-knowledge-487757851499-us-east-1

vector index:
arn:aws:s3vectors:us-east-1:487757851499:bucket/opslens-dev-knowledge-487757851499-us-east-1/index/opslens-dev-remediation-v1
```

Deterministic publication is authorized only after fresh corpus replay exactly matches the checked manifest.

Real publication:

```text
objects:             18
content:              9
metadata:             9
total bytes:          14,928
metadata sidecars:    394..493 bytes
```

The first ingestion revealed that the final serialized associated metadata, not merely logical custom metadata, must fit Bedrock/S3 Vectors' effective 1024-byte limit. The publisher now validates the final serialized sidecar bytes.

Successful ingestion:

```text
job id:                           WZRUGOFZPI
status:                           COMPLETE
observed duration:                11.145552 s
documents scanned:                9
new documents indexed:            9
documents failed:                 0
documents skipped:                0
vectors materialized:             9
```

A strongly consistent S3 Vectors listing returned exactly nine vector keys.

### 10.4 Gate 7.4 direct retrieval baseline — COMPLETE

Gate 7.4 deliberately uses direct `Retrieve`, not `RetrieveAndGenerate`, so raw retrieval quality/latency/provenance/cost remain independently measurable.

Runtime request authority is limited to:

```text
knowledgeBaseId
retrievalQuery.text
retrievalConfiguration.vectorSearchConfiguration.numberOfResults
```

No arbitrary provider DSL, hybrid override, reranking, generation, or implicit pagination is accepted.

Runtime path:

```text
RetrievalRequest
 -> exact configured KB
 -> Bedrock Knowledge Base Retrieve
 -> strict provider response parser
 -> expected S3 bucket + content-addressed key
 -> checked manifest lookup
 -> independent returned-text SHA-256 + UTF-8 byte-count validation
 -> canonical metadata reconciliation
 -> deterministic rank assignment
 -> RetrievedChunk[]
 -> RetrievalEvidence
```

Provider-owned `documentId`/chunk IDs do not become OpsLens canonical identity.

Typed Gate 7.1 filters fail before the provider call until a reviewed deterministic provider-filter translation exists.

`nextToken` and guardrail intervention fail closed in v1.

### 10.5 Real provider compatibility evidence

The first real call reached Bedrock but admission rejected `section_path` because Bedrock returned each path element as a JSON-quoted scalar inside the list.

Observed shape:

```text
["\"Secure installs\"", "\"Hash-checking Mode\""]
```

Canonical manifest shape:

```text
["Secure installs", "Hash-checking Mode"]
```

The adapter normalizes only this empirically observed case: quoted elements must parse as exactly one JSON string and the decoded value must equal checked manifest evidence. Plain canonical strings remain valid; malformed or mismatching values fail closed.

### 10.6 Real admitted retrieval evidence

```text
knowledge base:         BTVJ2PBR2A
query sha256:           5b398fe871d0cb51eaacb4f42a11b2ec402b5fdb4c523d2b7bca85e84dff3d0d
requested top_k:        5
returned/admitted:      5
provider request id:    e92d67f1-18fa-4537-8ff4-c2e02ab813e0
client elapsed:         1257 ms
SDK retries:            0
rank 1 chunk:           knowledge-chunk:pypa-secure-installs:hashes:v1
rank 1 score:           0.8649594783782959
```

All five results passed deterministic S3 location, content hash, byte-count, metadata, and checked-corpus provenance admission.

The CLI emits no retrieved source text and no raw query; operational evidence is hash/identity/rank/score/latency/request metadata only.

### 10.7 Real failure evidence

One intentional read-only request used a nonexistent syntactically valid KB ID:

```text
ZZZZZZZZZZ
```

Observed safe diagnostic:

```text
provider_code=ResourceNotFoundException
```

No provider response body, corpus text, or credential material was copied into the operational error.

### 10.8 IAM separation

The Knowledge Base service role owns ingestion/storage integration and is trusted by `bedrock.amazonaws.com`, not humans.

Retrieval is a separate runtime responsibility. A future deployed retrieval principal should be scoped to the exact KB retrieval action and must not inherit source writes, vector writes/deletes, ingestion, PassRole, or Terraform provisioning authority merely to retrieve.

No application runtime principal exists yet, so final retrieval-role attachment is deferred until there is an actual compute principal. Creating an unattached role would add dead IAM surface.

### 10.9 Retrieval-content trust boundary

Authorized/pinned text remains untrusted instruction content.

Retrieved text may become explanatory evidence only after deterministic admission. It cannot change system prompts, IAM, tool policies, vulnerability applicability, structured source facts, or Risk Policy.

## 11. Evidence and cache boundary

Threat-intelligence identities include temporal/source evidence; a repository commit alone is not a safe cache key.

Likewise, knowledge identity depends on exact pinned source bytes, deterministic section selection, canonical content hashes, and admitted provider projection.

No runtime cache backend exists yet because a measured workload has not justified storage cost, invalidation semantics, IAM, observability, failure recovery, or retention policy.

## 12. Security boundaries

```text
Human administration
 -> AWS IAM Identity Center

GitHub Actions
 -> OIDC
 -> deployment role
 -> Terraform-managed AWS changes

Repository Intelligence
 -> bounded public GitHub read-only authority
 -> inert evidence only
 -> no third-party code execution

Risk Policy
 -> pure deterministic evidence input
 -> no network/model authority

Semantic Query planner
 -> bounded Bedrock planning authority
 -> deterministic parser/compiler owns query truth
 -> bounded read-only Athena

Canonical Knowledge Corpus
 -> immutable allowlisted official source pins
 -> bounded GET-only raw-source acquisition
 -> inert untrusted text
 -> deterministic normalization/selection/hashing

Knowledge Base ingestion
 -> dedicated Bedrock service role
 -> exact source prefix + embedding model + vector index

Retrieval runtime
 -> direct bounded Bedrock Retrieve
 -> checked-corpus admission
 -> no ingestion/vector-write authority
 -> final deployed principal deferred until actual runtime exists
```

Runtime Exposure remains a later independent evidence domain and is not inferred from repository risk.

## 13. Cost discipline

Examples of deliberate non-adoption:

- no Glue crawler where explicit schemas suffice;
- no DynamoDB repository cache before measured reuse;
- no Step Functions unless workflow semantics justify it;
- no Iceberg requirement yet;
- no OpenSearch Serverless before hybrid/search requirements justify it;
- no Bedrock call for deterministic applicability or Risk Policy;
- no synthesis model before retrieval is independently evaluated;
- Athena dev workgroup enforces a 10 MiB scan cutoff.

Gate 7.3 uses only nine vectors.

Gate 7.4 observed three searches against the populated index. At current S3 Vectors request pricing of `$2.50 / 1,000,000 queries`, the request-fee component is approximately `$0.0000075`, plus negligible processed-data cost for this tiny index and query-embedding model usage. Exact query billing is not inferred from provider telemetry that does not expose billable vector bytes or embedding token usage.

Gate 7.5 will measure full-fixture query count, latency distribution, quality, and bounded cost assumptions.

## 14. Quality gates

Dedicated CI slices exist for:

```text
Correlation
Repository Intelligence
Risk Policy
Semantic Query
Knowledge Retrieval
Terraform static/security checks
```

Knowledge Retrieval CI also watches `knowledge/corpus/**`, so corpus authority changes cannot bypass the gate.

Real AWS evidence complements but does not replace offline tests, strict typing, linting, Terraform validation, TFLint, and Checkov.

## 15. ADR index

```text
0020 No unrestricted text-to-SQL
0021 Bounded Bedrock semantic-query planner
0022 Customer-managed Bedrock Knowledge Base with S3 Vectors
```

## 16. Next architecture decision — Gate 7.5

Gate 7.5 must evaluate the raw semantic retrieval baseline before synthesis, reranking, hybrid search, or additional filter behavior changes.

Required evaluation dimensions:

```text
Recall@1
Recall@3
Recall@5
Recall@10
MRR
provenance/source correctness
latency distribution
retrieval-call count
bounded retrieval cost assumptions
```

The evaluation must use the frozen Gate 7.1/7.2 fixture and Gate 7.4 direct-Retrieve runtime. Provider relevance scores remain uncalibrated evidence, not confidence probabilities.
