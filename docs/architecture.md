# OpsLens Architecture

_Last updated: 2026-09-06_

This document is the accumulated architecture baseline through **Phase 7 — Gate 7.6a: Deterministic context assembly**.

The next architecture boundary is **Phase 7 — Gate 7.6b: Synthesis request/output + abstention contract**.

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
- retrieval evidence admission, evaluation, context admission, and citation projection remain deterministic;
- provider/model outputs are evidence or proposals, not authority over structured truth;
- LLMs may classify, plan, route, synthesize, and explain only over validated evidence;
- retrieved explanatory text never becomes a second authority for structured threat facts;
- third-party repository/source content is untrusted data to inspect, never code to execute;
- admission proves source/content identity, not trusted-instruction status;
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

### Phase 7 explanatory/remediation path through Gate 7.6a

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
 -> deterministic retrieval evaluation
 -> deterministic whole-chunk context assembly
 -> AssembledContext
 -> future bounded synthesis
```

Retrieval is real and independently measured. Context assembly is deterministic and offline. Bedrock synthesis is not implemented yet.

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

## 10. Knowledge Retrieval — Phase 7 through Gate 7.6a

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

### 10.3 Gate 7.3 vector baseline — COMPLETE / MERGED

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

The first ingestion revealed that final serialized associated metadata must fit Bedrock/S3 Vectors' effective 1024-byte limit. The publisher validates final serialized sidecar bytes.

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

### 10.4 Gate 7.4 direct retrieval baseline — COMPLETE / MERGED

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

The first real call exposed `section_path` elements represented as JSON-quoted scalars. The adapter normalizes only that empirically proven representation and still requires exact equality with checked manifest evidence.

Real admitted retrieval:

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

Intentional read-only provider failure:

```text
nonexistent KB: ZZZZZZZZZZ
provider_code: ResourceNotFoundException
```

Gate 7.4 was squash-merged through PR #97 at:

```text
7c25877e0ae9541a4f20b8537e4f77c88ee776a5
```

### 10.5 IAM separation

The Knowledge Base service role owns ingestion/storage integration and is trusted by `bedrock.amazonaws.com`, not humans.

Retrieval is a separate runtime responsibility. A future deployed retrieval principal should be scoped to the exact KB retrieval action and must not inherit source writes, vector writes/deletes, ingestion, PassRole, or Terraform provisioning authority merely to retrieve.

No application runtime principal exists yet, so final retrieval-role attachment is deferred until there is an actual compute principal.

### 10.6 Retrieval-content trust boundary

Authorized/pinned text remains untrusted instruction content.

Retrieved text may become explanatory evidence only after deterministic admission. It cannot change system prompts, IAM, tool policies, vulnerability applicability, structured source facts, or Risk Policy.

### 10.7 Gate 7.5 evaluation contract

Gate 7.5 freezes evaluation over `knowledge-retrieval-golden:v1`:

```text
10 cases
8 positive
2 negative/out-of-authority
one real top_k=10 ranking per case
```

Metrics are deterministic over admitted results:

```text
Recall@1
Recall@3
Recall@5
Recall@10
MRR
relevant-hit provenance correctness
negative non-empty retrieval evidence
latency distribution
retry counts
```

Provider/runtime failures are not converted into retrieval misses. Aggregate quality is withheld if the run is incomplete.

### 10.8 Gate 7.5 real baseline — COMPLETE / MERGED

All ten real calls completed successfully with zero SDK retries.

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Latency:

```text
min:   532 ms
max:   1728 ms
mean:  720.0 ms
p50:   616 ms
p95:   1728 ms
```

The expected vendor-advisory remediation chunk was the weakest positive target at rank 7. This is retained as baseline evidence and is not fixed by relabeling or post-hoc test-set tuning.

`Recall@10=1.0` is intentionally not treated as a strong production claim because the corpus contains only nine vectors. `Recall@3`, `Recall@5`, and MRR better expose ranking behavior.

Gate 7.5 was squash-merged through PR #98 at:

```text
b30af10a568cefa7175c253120499939f9ca18d8
```

### 10.9 Negative retrieval conclusion

Both out-of-authority cases returned nine nearest-neighbor results:

```text
negative_nonempty_retrieval_rate = 1.0
rank-1 scores ~= 0.689
```

The negative scores overlap scores from legitimate positive retrieval evidence. Therefore:

- non-empty vector retrieval is not an authority decision;
- Bedrock relevance score is not a calibrated probability;
- Gate 7.5 provides no evidence for a global score threshold;
- route/authority validation must precede synthesis;
- runtime exposure cannot be answered merely because remediation text is semantically nearby.

This measurement reinforces both `Not every question is a RAG problem` and `Repository Risk != Runtime Exposure`.

### 10.10 Gate 7.6 design consequence

Gate 7.6 must not blindly pass every retrieved candidate into synthesis.

The synthesis path must separate:

```text
admitted retrieval candidates
 -> deterministic context authority
 -> explicitly bounded synthesis authority
```

Gate 7.5's frozen golden set is evidence for architectural decisions, not a dataset for ad-hoc tuning.

### 10.11 Gate 7.6a deterministic context assembly — COMPLETE / PR #99

Provider-independent context contracts:

```text
ContextAssemblyLimits
ContextEvidenceBlock
AssembledContext
ContextAssemblyStopReason
```

Frozen v1 limits:

```text
default max chunks:      5
hard max chunks:         10
max admitted text bytes: 16,384 UTF-8 bytes
```

The byte ceiling is deliberately application-level. It bounds admitted source text before a provider request but is not described as a token estimate, model input limit, or context-window size.

Assembly algorithm:

```text
RetrievalEvidence
 -> read admitted chunks in existing rank order
 -> project next whole chunk
 -> stop if max_chunks reached
 -> stop if adding next whole chunk exceeds max_utf8_bytes
 -> never truncate
 -> never skip a non-fitting higher rank to backfill a lower rank
 -> AssembledContext
```

The no-backfill rule avoids creating a second ranking heuristic that Gate 7.5 did not evaluate.

Empty retrieval fails closed. If rank 1 alone exceeds the byte budget, assembly also fails closed rather than truncating source evidence.

`ContextEvidenceBlock` preserves:

```text
retrieval rank
canonical chunk/document/source identity
source type
canonical URI
document/chunk content SHA-256
exact admitted text
exact UTF-8 byte count
title
section path
```

Provider `relevance_score` is intentionally **not** projected into synthesis context. Gate 7.5 proved that score is uncalibrated and overlaps between legitimate and out-of-authority retrievals.

Operational `AssembledContext` evidence includes:

```text
retrieval_id
query_sha256
limits
selected block evidence
retrieved_chunk_count
total_utf8_bytes
stop_reason
context_sha256
```

The raw query is not duplicated into operational context identity. The deterministic context fingerprint covers query identity, limits, selected rank/provenance/content hashes, retrieved count, and stop reason. Exact source text is bound through each block's verified content hash.

Retrieved text remains untrusted evidence after admission. Future synthesis serialization must keep trusted instructions, user input, and retrieved source content logically distinct.

7.6a is pure deterministic local code:

```text
AWS calls:           0
new AWS resources:   0
new IAM permissions: 0
model tokens:        0
provider cost:       $0
```

Quality evidence:

```text
Python CI #245: SUCCESS
Ruff:             PASS
Pyright strict:   PASS
pytest:            PASS
regressions:      PASS
```

The initial CI exposed style and strict-typing issues only. Runtime validation was retained rather than removed: direct `isinstance` checks on strongly typed public fields were routed through an `object`-typed helper, consistent with the existing domain fail-closed pattern.

## 11. Evidence and cache boundary

Threat-intelligence identities include temporal/source evidence; a repository commit alone is not a safe cache key.

Knowledge identity depends on exact pinned source bytes, deterministic section selection, canonical content hashes, and admitted provider projection.

Synthesis-context identity now additionally depends on the exact admitted retrieval operation, deterministic context limits, selected rank prefix, canonical content hashes, and stop reason.

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

Retrieval evaluation
 -> checked admitted chunks only
 -> deterministic metrics
 -> provider scores remain non-authoritative
 -> no synthesis/model authority

Context assembly
 -> admitted RetrievalEvidence only
 -> whole contiguous rank prefix
 -> deterministic chunk/byte bounds
 -> no score-derived authority
 -> no model/network/IAM authority
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
- no synthesis model before retrieval is independently evaluated and context authority is frozen;
- Athena dev workgroup enforces a 10 MiB scan cutoff.

Gate 7.3 uses only nine vectors.

Gate 7.4 observed three populated-index searches.

Gate 7.5 observed ten populated-index searches. At the published S3 Vectors request price of `$2.50 / 1,000,000 queries`, the exact request-fee component is:

```text
$0.000025
```

The S3 Vectors pricing model also includes data processed and data returned. The customer-managed KB also uses Titan Text Embeddings V2 for query embeddings. Bedrock `Retrieve` does not expose the exact billable vector bytes or query-embedding token count required to reconstruct those components, so OpsLens does not fabricate a full bill from incomplete telemetry.

AWS documents both Managed and Customer-managed Knowledge Bases. OpsLens uses the customer-managed form with S3 Vectors and a selected embedding model; pricing for a fully managed KB must not be applied blindly to this architecture.

Gate 7.6a adds zero provider cost because context assembly is local deterministic code.

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

Gate 7.6a does not need a new AWS-service ADR because it adds no provider/service selection. A synthesis ADR should be added only if 7.6c makes a durable provider/runtime architecture decision not already covered by existing ADRs.

## 16. Next architecture decision — Gate 7.6b

Freeze the synthesis contract **offline before selecting or invoking a model**.

Required decisions:

```text
synthesis request type
synthesis output type
unsupported / insufficient-evidence behavior
trusted instruction vs untrusted context serialization
application-level output and call bounds
model-output validation
safe failure categories
runtime evidence required from a future provider adapter
```

Only after that contract is deterministic and CI-green should Gate 7.6c select a Bedrock runtime API/model from current official AWS documentation and freeze provider-specific token, timeout, retry, IAM, observability, and cost boundaries.

Generation must consume only admitted `AssembledContext`. Retrieval relevance scores remain observational signals and do not become authority or confidence probabilities.
