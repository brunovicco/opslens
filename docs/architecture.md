# OpsLens Architecture

_Last updated: 2026-09-06_

This document is the accumulated architecture baseline through **Phase 7 — Knowledge Retrieval with Bedrock: COMPLETE**.

The next architecture boundary is **Phase 8 — Hybrid Retrieval**.

## 1. Purpose

OpsLens is an open-source software supply-chain and threat-intelligence platform on AWS.

Product goal:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, which findings should I prioritize, and what verified guidance can help me act on them?

Core invariant:

> **Agents reason. Code verifies evidence.**

Additional permanent boundaries:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

## 2. Permanent architectural principles

Unless changed by explicit ADR:

- raw third-party evidence is preserved before enrichment or interpretation;
- exact source versions and content hashes participate in provenance;
- package identity normalization, vulnerable-range matching, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS evidence, and Risk Policy remain deterministic;
- semantic-query validation and SQL compilation remain deterministic;
- canonical corpus normalization, selection, hashing, and checked-manifest identity remain deterministic;
- retrieval admission, context assembly, citation authority, synthesis output admission, support-evidence validation, and metric computation remain deterministic;
- model outputs are proposals/evidence, not authority over structured truth;
- a model may select among allowlisted citation IDs but may not author canonical source identity;
- syntactically valid citation coverage does not prove semantic support;
- retrieved/source content remains untrusted instruction content after provenance admission;
- schema, provenance, authority, exact-evidence, or content-addressed identity mismatches fail closed;
- IAM uses least privilege and responsibility separation;
- AWS services are introduced only for concrete measured requirements;
- cost and observability are architecture requirements;
- one real `dev` environment is preferred over fictional portfolio environments;
- first-run evaluation evidence is preserved before optimization.

## 3. System shape

### Structured vulnerability/risk path

```text
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
 -> deterministic correlation
 -> immutable Repository Intelligence
 -> RepositoryAnalysisResult
 -> deterministic Risk Policy v1
 -> RiskPrioritizationResult
```

### Structured natural-language query path

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

### Explanatory/remediation knowledge path

```text
explicitly authorized official sources
 -> immutable repository/commit/path pins
 -> bounded GET-only inert-text acquisition
 -> deterministic normalization + exact section selection
 -> content-addressed canonical chunks
 -> checked hash/provenance manifest
 -> deterministic S3 publication
 -> customer-managed Bedrock Knowledge Base ingestion
 -> Titan Text Embeddings V2 / 1024 / FLOAT32
 -> Amazon S3 Vectors / cosine
 -> direct bounded Retrieve
 -> checked-corpus S3/hash/metadata reconciliation
 -> RetrievedChunk[]
 -> deterministic contiguous rank-prefix context assembly
 -> deterministic pre-model authority decision
 -> one bounded non-streaming Bedrock Converse call
 -> deterministic synthesis output admission
 -> deterministic C1..Cn citation catalog
 -> structured claim + citation-ID proposal
 -> human-reviewed pair-level support evidence
 -> deterministic groundedness/citation metrics
```

Retrieval and synthesis remain separately observable. `RetrieveAndGenerate` remains deliberately unused.

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

Human administration uses temporary IAM Identity Center credentials. GitHub Actions uses OIDC; persistent AWS access keys are not stored in GitHub.

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

## 5. Structured deterministic authorities — Phases 2–6

### Threat Intelligence Data Lake

NVD, KEV, EPSS, and GHSA remain source-local evidence with explicit provenance and time semantics.

### Vulnerability Correlation

```text
package/version/purl
 + exact vulnerable-range evidence
 -> deterministic PEP 440 evaluation
 -> affected | not_affected | unsupported
 -> CVE/GHSA/NVD reconciliation
 -> content-addressed evidence
```

> **No LLM decides vulnerability applicability.**

### Repository Intelligence

```text
public repository
 -> immutable repository/commit/tree identity
 -> bounded GitHub read-only acquisition
 -> inert uv.lock bytes
 -> deterministic TOML parsing
 -> canonical dependencies
 -> deterministic vulnerability applicability
 -> RepositoryAnalysisResult
```

Repository findings do not prove runtime presence or exploitability.

### Risk Prioritization

```text
RepositoryAnalysisResult
 -> deterministic Risk Policy v1
 -> factor contributions
 -> priority score + tier
 -> completeness / review_required
```

The priority value is an OpsLens policy score, not exploit probability, CVSS, EPSS, or runtime exposure.

### Semantic Query

```text
question
 -> bounded Bedrock planner
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded Athena execution
```

ADRs 0020 and 0021 preserve the no-unrestricted-text-to-SQL boundary.

## 6. Phase 7 controlled corpus and vector Knowledge Base

Gate 7.1 froze provider-independent retrieval contracts.

Gate 7.2 authorized six official source files through immutable repository/commit/path pins and deterministically materialized nine chunks.

Frozen corpus:

```text
manifest id: knowledge-corpus-manifest:v1
documents:   6
chunks:      9
sha256:      98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

Gate 7.3 selected a customer-managed Bedrock vector Knowledge Base backed by S3 Vectors:

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

Successful ingestion materialized exactly nine vectors.

The Knowledge Base service role is an ingestion/vector integration identity, not a human or application runtime identity.

## 7. Direct retrieval and deterministic admission

Gate 7.4 uses direct Knowledge Base `Retrieve`.

Admission path:

```text
provider result
 -> exact expected S3 location
 -> checked manifest lookup
 -> returned-text SHA-256 + byte-count validation
 -> canonical metadata reconciliation
 -> deterministic rank
 -> RetrievedChunk
```

Provider-owned IDs do not become canonical OpsLens identity.

Frozen Gate 7.5 baseline:

```text
10 cases
8 positive
2 negative/out-of-authority
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Both negative cases returned nearest-neighbor results. Vector similarity and non-empty retrieval are therefore evidence, not routing/answerability authority.

## 8. Context assembly and synthesis

Provider-independent context bounds:

```text
default max chunks:      5
hard max chunks:         10
max admitted text bytes: 16,384 UTF-8 bytes
```

Algorithm:

```text
RetrievalEvidence
 -> preserve rank order
 -> admit whole next chunk if it fits
 -> stop at max chunks or first non-fitting whole chunk
 -> never truncate
 -> never skip/backfill lower ranks
 -> AssembledContext
```

Pre-model authority is deterministic:

```text
SUPPORTED
UNSUPPORTED
```

`UNSUPPORTED` cannot form a synthesis request.

Synthesis boundary from ADR 0023:

```text
question:                 <= 1,000 characters
model calls/application:  1 maximum
answer:                   <= 4,000 characters
raw response parser:      <= 65,536 characters
Region:                   us-east-1
API:                      bedrock-runtime / Converse
model/profile:            us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:                no
temperature:              0.0
provider maxTokens:       2,048
tools:                    none
structured output:        JSON Schema
```

Prompt trust classes remain separated:

```text
trusted system instructions
untrusted user question
untrusted but source-verified retrieved evidence
```

Automatic model-invocation body logging remains disabled because prompts contain user/source text. Content-free metadata and hashes are recorded instead.

## 9. Deterministic citation authority and groundedness

```text
AssembledContext
 -> selected ContextEvidenceBlock[] only
 -> deterministic C1..Cn
 -> CitationCatalog
 -> GroundedSynthesisRequest
 -> structured claims + citation IDs
 -> deterministic output admission
```

Canonical URI/source/document/chunk/hash identity is projected from admitted evidence, never accepted from model output.

A valid citation ID guarantees syntactic citation coverage only.

Frozen `knowledge-grounding-golden:v1` baseline:

```text
decision accuracy:                 1.0
citation target precision:         0.2857142857142857
citation target recall:            0.5
claim supportedness rate:          0.8461538461538461
unsupported claim rate:            0.15384615384615385
citation correctness rate:         0.8461538461538461
abstention precision:              1.0
abstention recall:                 1.0
```

Human-reviewed support evidence is preserved as content-addressed metadata:

```text
labs/evidence/phase-7-gate-7-7-first-run-review-v1.json
```

### Architecture lesson: retrieval success != groundedness

The isolation target was retrieved at rank 1 and became `C1`, yet the model cited `C2` for both claims. Strict exact-chunk review marked both pairs unsupported.

```text
retrieval success
 != citation attribution success
 != claim groundedness
```

### Architecture lesson: retrieval existence != answerability

The TLS-cipher case returned five vector neighbors but correctly produced `insufficient_evidence`.

```text
non-empty vector retrieval
 != sufficient evidence
 != authority to answer
```

The Gate 7.7 weakness remains frozen. Any prompt or citation-selection change requires a new version and a new evaluation.

## 10. Phase 7 failure taxonomy

Gate 7.8 freezes failure diagnosis by stage:

```text
1. route / authority failure
   wrong evidence path or unsupported request admitted

2. provider retrieval failure
   Bedrock Retrieve timeout/throttle/provider error

3. retrieval evidence-admission failure
   wrong S3 key/bucket, hash/byte mismatch, invalid metadata/provenance

4. retrieval relevance / coverage failure
   provider call succeeds but required evidence is outside admitted results

5. context-assembly failure
   deterministic bounds prevent sufficient whole-chunk context

6. synthesis transport failure
   Converse timeout/throttle/provider error

7. synthesis output-admission failure
   invalid schema, unexpected block/stop reason, invalid counts/bounds

8. answerability / decision failure
   incorrect ANSWER vs INSUFFICIENT_EVIDENCE decision

9. citation-authority failure
   unknown/duplicate/out-of-catalog citation identity

10. citation-attribution failure
    selected valid citation points to the wrong evidence chunk

11. semantic groundedness failure
    cited evidence does not support the emitted claim
```

These categories are intentionally separate. A citation-attribution failure must not be mislabeled as a retrieval miss, and provider success must not hide semantic failure.

## 11. Future application runtime IAM boundary

No application compute principal exists yet. Gate 7.8 documents the future entitlement before a role is created.

### Retrieval runtime entitlement

The proven runtime requires only:

```text
Action:   bedrock:Retrieve
Resource: arn:aws:bedrock:us-east-1:487757851499:knowledge-base/BTVJ2PBR2A
```

The application does not need `RetrieveAndGenerate`, data-source management, Knowledge Base administration, or direct S3 Vectors access for the proven path.

### Synthesis runtime entitlement

The application calls non-streaming `Converse`. Bedrock authorizes this through `bedrock:InvokeModel`.

The selected US Geographic inference profile is:

```text
us.anthropic.claude-haiku-4-5-20251001-v1:0
```

For requests sourced from `us-east-1`, AWS documents destination Regions:

```text
us-east-1
us-east-2
us-west-2
```

The future role therefore needs `bedrock:InvokeModel` on:

```text
exact inference-profile ARN in us-east-1
exact Claude Haiku 4.5 foundation-model ARN in us-east-1
exact Claude Haiku 4.5 foundation-model ARN in us-east-2
exact Claude Haiku 4.5 foundation-model ARN in us-west-2
```

Foundation-model permissions should be conditioned on the exact `bedrock:InferenceProfileArn`.

Streaming permission (`bedrock:InvokeModelWithResponseStream`) is intentionally absent because the Phase 7 contract is non-streaming.

See ADR 0024 for the policy shape and rationale.

## 12. Cost-accounting boundary

Phase 7 separates cost drivers instead of reporting a fabricated single number:

```text
ingestion-time model embedding
S3 Vectors storage
S3 Vectors writes
query-time embedding
S3 Vectors query request fee
S3 Vectors data processed
S3 Vectors data returned
synthesis input tokens
synthesis output tokens
```

The first four-case grounded run directly computed:

```text
model input:             $0.0129074
model output:            $0.0035475
model subtotal:          $0.0164549
4 S3 Vectors requests:   $0.0000100
computable total:        $0.0164649
```

This is not represented as the complete AWS bill because exact query-embedding consumption and S3 Vectors processed/returned units are not exposed by the runtime evidence.

Cost Explorer/billing remains the source for bill-level reconciliation.

## 13. Observability boundary

Current lab/runtime evidence captures:

```text
provider request IDs
retrieval result counts/ranks/scores
canonical provenance hashes
context/catalog/request/result hashes
model/profile identity
input/output/total/cache tokens
Bedrock latency
client elapsed time
SDK retry count
stop reason
answer/abstention decision
claim/citation mappings
human support-judgment hashes
```

Phase 7 does not claim:

```text
production SLOs
continuous deployed application metrics for the RAG path
end-user trace correlation across a deployed runtime
production alert thresholds
high-volume cost or latency distributions
```

Those require a real deployed runtime and measured workload.

## 14. Phase 8 entry boundary

Hybrid Retrieval must not simply concatenate Athena rows and vector chunks.

Phase 8 begins from an explicit evidence-class routing contract:

```text
structured vulnerability/risk facts
 -> deterministic structured authority

explanatory/remediation guidance
 -> bounded semantic retrieval evidence

combined response
 -> provenance remains explicit by evidence class
 -> no authority laundering
```

Entry criteria:

```text
1. Gate 7.7 baseline remains immutable
2. route eligibility is explicit and typed
3. structured truth remains authoritative for vulnerability/risk facts
4. semantic evidence remains bounded explanatory/remediation evidence
5. combined evidence preserves provenance by class
6. missing required evidence causes explicit partial/unsupported behavior
7. quality, cost, failures, and observability remain independently measurable
8. new AWS services/rerankers/search modes require measured justification
```

Phase 8 starts offline-first with the routing and authority contract before introducing any new AWS resource or model call.

## 15. Deliberate non-adoption at Phase 7 closeout

- no OpenSearch Serverless before a measured requirement;
- no reranker before a measured relevance/groundedness hypothesis;
- no keyword/vector hybrid mode merely because it exists;
- no runtime cache before reuse/invalidation requirements are measured;
- no application IAM role before actual compute exists;
- no provider-generated canonical citations;
- no post-hoc similarity threshold derived from the small fixture;
- no prompt tuning inside the frozen Gate 7.7 baseline.

## 16. Architecture records

Relevant current ADRs:

```text
0020 No unrestricted text-to-SQL
0021 Bounded Bedrock semantic-query planner
0022 Customer-managed Bedrock KB with S3 Vectors
0023 Bounded Bedrock knowledge synthesis
0024 Phase 7 future application runtime IAM boundary
```

Phase 7 closeout evidence is recorded in:

```text
labs/phase-7-gate-7-8-closeout.md
```
