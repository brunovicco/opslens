# OpsLens Architecture

_Last updated: 2026-09-05_

This document is the accumulated architecture baseline through **Phase 7 — Gate 7.3: Knowledge Base + Vector Infrastructure**.

The next roadmap boundary is **Phase 7 — Gate 7.4: Real bounded Retrieve adapter**.

## 1. Purpose

OpsLens is an open-source software supply chain and threat-intelligence platform on AWS.

Product goal:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, and which findings should I prioritize?

The architecture establishes trustworthy deterministic evidence and policy enforcement before adding semantic, generative, retrieval, or agentic reasoning.

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
- deterministic facts remain authoritative;
- exact source versions and content hashes participate in provenance;
- package identity normalization remains deterministic;
- version parsing and vulnerable-range matching remain deterministic;
- vulnerability applicability remains deterministic;
- CVE/GHSA/NVD reconciliation remains deterministic;
- KEV/EPSS/CVSS evidence remains deterministic and source-preserving;
- risk policy evaluation remains deterministic;
- semantic-query validation and SQL compilation remain deterministic;
- canonical corpus normalization, selection, and hashing remain deterministic;
- retrieval evidence validation and context admission remain deterministic;
- citation projection remains deterministic from admitted evidence;
- execution/tool/cost enforcement remains deterministic;
- LLMs may classify, plan, route, synthesize, and explain over validated evidence;
- LLMs do not replace package applicability, structured source evidence, or risk-policy enforcement;
- natural-language planning never receives unrestricted SQL authority;
- retrieved explanatory text never becomes a second authority for structured threat facts;
- third-party repository/source content is untrusted data to inspect, never code to execute;
- missing evidence is not silently converted into benign evidence;
- schema, provenance, authority, or exact-evidence mismatches fail closed;
- IAM uses least privilege and responsibility separation;
- AWS services are introduced only for concrete requirements;
- cost and observability are architectural requirements;
- one real `dev` environment is preferred over fictional portfolio environments.

## 3. Current system shape

### Structured vulnerability/risk path

```text
THREAT INTELLIGENCE DATA
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
        |
        v
DETERMINISTIC CORRELATION
PyPI identity + PEP 440 + GHSA applicability + CVE/NVD evidence
        |
        v
REPOSITORY INTELLIGENCE
immutable public GitHub snapshot + inert uv.lock + deterministic findings
        |
        v
RepositoryAnalysisResult
        |
        v
RISK PRIORITIZATION
versioned Risk Policy v1 + factor evidence + deterministic ranking
        |
        v
RiskPrioritizationResult
```

### Phase 6 semantic structured-query path

```text
natural-language factual question
 -> bounded Bedrock planner
 -> structured proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic validation + SQL compiler
 -> bounded read-only Athena
 -> structured result evidence
```

The planner has no arbitrary SQL authority.

### Phase 7 explanatory/remediation path through Gate 7.3

```text
explicitly authorized official sources
 -> immutable repository/commit/path pins
 -> bounded GET-only inert-text acquisition
 -> deterministic normalization + exact section selection
 -> 9 content-addressed canonical chunks
 -> checked hash-only manifest
 -> deterministic 9 text + 9 metadata S3 publication
 -> Bedrock S3 data source / chunking NONE
 -> Titan Text Embeddings V2 / 1024 / FLOAT32
 -> Amazon S3 Vectors / cosine
 -> customer-managed Bedrock Knowledge Base
 -> Gate 7.4 bounded Retrieve
```

The vector layer is now real and validated. Retrieval and synthesis are still separate future authorities.

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

Human administration uses temporary IAM Identity Center credentials. GitHub Actions assumes AWS roles through OIDC; persistent AWS access keys are not stored in GitHub.

Terraform layout:

```text
infra/
  bootstrap/
  environments/
    dev/
```

Primary general-purpose storage:

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

Phase 7 now also owns a dedicated S3 Vectors bucket/index for the Knowledge Base. It is separate from the general-purpose S3 data bucket that stores source objects.

## 5. Threat Intelligence Data Lake — Phase 2

Phase 2 preserves source-local authority. NVD, KEV, EPSS, and GHSA are not flattened into one lossy universal vulnerability record.

Key properties:

- FIRST EPSS current/historical evidence with explicit snapshot dates;
- CISA KEV complete-catalog semantics;
- NVD bootstrap/incremental evidence with authoritative watermarking;
- GitHub Security Advisory exact source-version evidence;
- Glue/Athena analytics projections downstream of source truth.

## 6. Vulnerability Correlation Engine — Phase 3

Phase 3 is complete for the supported PyPI v1 scope.

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

Phase 4 analyzes a supported public GitHub repository without executing its code.

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

A repository finding proves repository-risk evidence for an immutable dependency snapshot. It does not prove runtime presence or exploitability.

## 8. Risk Prioritization Engine — Phase 5

Phase 5 introduces a separate downstream policy authority over Phase 4 facts.

```text
RepositoryAnalysisResult
 -> RiskFindingInput
 -> pure deterministic Risk Policy v1
 -> factor contributions
 -> priority score + tier
 -> completeness / review_required
 -> deterministic aggregate ranking
```

The priority value is an **OpsLens priority score**, not exploit probability, CVSS, EPSS, or runtime exposure.

## 9. Semantic Query Layer — Phase 6

Phase 6 adds bounded natural-language planning without unrestricted SQL authority.

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

Permanent guardrail:

> **No unrestricted text-to-SQL.**

## 10. Knowledge Retrieval — Phase 7 through Gate 7.3

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

Canonical metadata and citation provenance remain provider-independent. Citations are projected from admitted chunks rather than accepted from model-authored URLs/source IDs.

### 10.2 Canonical corpus authority

Gate 7.2 authorizes six official explanatory/remediation source files through immutable repository/commit/path pins.

Frozen normalization:

```text
UTF-8:          strict
BOM:            reject
NUL:            reject
newlines:       CRLF/CR -> LF
Unicode:        preserve
selection:      exact line-aligned markers
document join:  two LF
```

The checked-in manifest stores only provenance and hashes, not third-party source/chunk text.

```text
manifest id: knowledge-corpus-manifest:v1
documents:   6
chunks:      9
sha256:      98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

### 10.3 Gate 7.3 vector baseline

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

### 10.4 Deterministic publication boundary

Publication is authorized only after fresh Gate 7.2 replay exactly matches the checked manifest.

```text
verified replay
 -> 9 canonical text objects
 -> 9 metadata sidecars
 -> checksummed S3 writes
 -> exact prefix membership verification
 -> HeadObject checksum/size/type verification
```

Real successful publication:

```text
objects:             18
content:              9
metadata:             9
total bytes:          14,928
metadata sidecars:    394..493 bytes
```

The first real ingestion exposed a subtle provider boundary: logical metadata was below 1 KB, but the verbose serialized sidecar exceeded the Bedrock/S3 Vectors 1024-byte service limit. All nine files were ignored and zero vectors were created.

The deterministic publisher now validates the **final serialized sidecar bytes** and uses the supported compact metadata representation. This preserves the frozen metadata vocabulary while preventing metadata identifiers from influencing embeddings.

### 10.5 Real ingestion and vector materialization

Successful ingestion job:

```text
job id:                           WZRUGOFZPI
status:                           COMPLETE
startedAt:                        2026-09-05T20:41:46.010046+00:00
updatedAt:                        2026-09-05T20:41:57.155598+00:00
observed duration:                11.145552 s
documents scanned:                9
new documents indexed:            9
documents failed:                 0
documents skipped:                0
vectors materialized:             9
```

A strongly consistent S3 Vectors listing returned exactly nine vector keys immediately after completion.

### 10.6 IAM separation

The Bedrock Knowledge Base service role is dedicated to ingestion/storage integration:

```text
bedrock:InvokeModel
 -> exact Titan embedding model

s3:GetObject / s3:ListBucket
 -> exact source bucket/prefix

s3vectors Put/Get/Delete/Query/GetIndex
 -> exact vector index
```

The role trust is for `bedrock.amazonaws.com`, not the human bootstrap identity. A real human `sts:AssumeRole` attempt returned expected `AccessDenied`.

Gate 7.4 must introduce a separate retrieval runtime identity. It must not inherit source-ingestion or vector-write authority.

### 10.7 Retrieval-content trust boundary

Authorized/pinned text is still untrusted instruction content.

Retrieved text may become explanatory evidence only after deterministic admission. It cannot change system prompts, tool policies, IAM authority, vulnerability applicability, structured source facts, or risk policy.

### 10.8 Gate 7.4 boundary

Next architecture increment:

```text
RetrievalRequest
 -> dedicated retrieval runtime identity
 -> Bedrock Knowledge Base Retrieve
 -> strict provider response parser
 -> S3 location/content/metadata reconciliation
 -> independent content/hash validation
 -> RetrievedChunk[]
 -> RetrievalEvidence
```

No `RetrieveAndGenerate` shortcut is allowed for the v1 baseline because retrieval quality must be measured separately from generation.

## 11. Evidence and cache boundary

Threat-intelligence analysis identities include selected temporal/source evidence. A repository commit alone is not a safe cache key.

Likewise, canonical knowledge identity is not just a human-facing URL. It depends on exact pinned source bytes, deterministic section selection, canonical content hashes, and admitted provider projection.

No runtime cache backend exists yet because a measured workload has not justified storage cost, invalidation semantics, IAM, observability, failure recovery, and retention policy.

## 12. Security boundaries

```text
Human administration
 -> AWS IAM Identity Center

GitHub Actions
 -> OIDC
 -> deployment role
 -> Terraform-managed AWS changes

Threat-intelligence runtimes
 -> source-specific least-privilege roles

Repository Intelligence
 -> bounded public GitHub read-only authority
 -> inert repository evidence only
 -> no third-party code execution

Risk Policy
 -> pure deterministic Phase 4 evidence input
 -> no network/model authority

Semantic Query planner
 -> bounded Bedrock planning authority only
 -> deterministic parser/compiler owns query truth
 -> bounded read-only Athena execution

Canonical Knowledge Corpus
 -> immutable allowlisted official source pins
 -> bounded GET-only raw-source acquisition
 -> inert untrusted text
 -> deterministic normalization/selection/hashing

Knowledge Base ingestion
 -> dedicated Bedrock service role
 -> exact source prefix + embedding model + vector index

Future retrieval runtime
 -> separate least-privilege Bedrock Retrieve authority
 -> no ingestion/vector-write authority
```

A deterministic repository priority remains a **repository-risk policy result**. Runtime Exposure remains a later independent evidence domain.

## 13. Cost discipline

Examples of deliberate non-adoption:

- no Glue crawler where explicit schemas suffice;
- no DynamoDB repository cache before measured reuse;
- no Step Functions unless workflow semantics justify it;
- no Iceberg requirement yet;
- no OpenSearch Serverless before hybrid/search requirements justify it;
- no Bedrock call for deterministic applicability or risk prioritization;
- no synthesis model in Gate 7.3;
- Athena dev workgroup enforces a 10 MiB scan cutoff.

Gate 7.3 storage/write/embedding workload is deliberately tiny: nine vectors. Exact embedding tokens are not returned by the ingestion API, so the gate records measured workload shape and published pricing assumptions instead of fabricating an exact bill.

Gate 7.4/7.5 will separately measure retrieval latency, quality, and cost.

## 14. Quality gates

Dedicated deterministic CI slices exist for:

```text
Correlation
Repository Intelligence
Risk Policy
Semantic Query
Knowledge Retrieval
Terraform static/security checks
```

Knowledge Retrieval CI watches source, tests, and `knowledge/corpus/**` so corpus authority changes cannot bypass the gate.

Real AWS evidence complements but does not replace offline tests, strict typing, linting, Terraform validation, TFLint, and Checkov.

## 15. ADR index for current architecture

Key ADRs include:

```text
0020 No unrestricted text-to-SQL
0021 Bounded Bedrock semantic-query planner
0022 Customer-managed Bedrock Knowledge Base with S3 Vectors
```

## 16. Next architecture decision

Gate 7.4 must freeze the real retrieval runtime boundary before synthesis exists:

- exact Bedrock `Retrieve` API surface;
- least-privilege runtime IAM;
- request/response bounds;
- provider-error categorization;
- provenance/location reconciliation;
- returned content/hash validation;
- relevance-score semantics;
- latency/cost evidence;
- intentional real failure;
- no `RetrieveAndGenerate`.
