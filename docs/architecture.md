# OpsLens Architecture

_Last updated: 2026-09-06_

This document is the accumulated architecture baseline through **Phase 7 — Gate 7.6f: measured bounded Bedrock synthesis**.

The next architecture boundary is **Phase 7 — Gate 7.7: deterministic citations + groundedness evaluation**.

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

Unless changed by explicit ADR:

- raw third-party evidence is preserved before enrichment or interpretation;
- exact source versions and content hashes participate in provenance;
- package identity normalization, version/range matching, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS evidence, and Risk Policy remain deterministic;
- semantic-query validation and SQL compilation remain deterministic;
- canonical corpus normalization, selection, hashing, and checked manifest identity remain deterministic;
- retrieval evidence admission, evaluation, context assembly, synthesis admission, citation projection, and evidence validation remain deterministic;
- provider/model outputs are evidence or proposals, not authority over structured truth;
- LLMs may classify, plan, route, synthesize, and explain only inside explicitly bounded authority;
- retrieved explanatory text never becomes a second authority for structured threat facts;
- source/repository content remains untrusted data to inspect, never code to execute;
- admission proves source/content identity, not trusted-instruction status;
- schema, provenance, authority, or exact-evidence mismatches fail closed;
- IAM uses least privilege and responsibility separation;
- AWS services are introduced only for concrete requirements;
- cost and observability are architectural requirements;
- one real `dev` environment is preferred over fictional portfolio environments.

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

### Explanatory/remediation knowledge path through Gate 7.6f

```text
explicitly authorized official sources
 -> immutable repository/commit/path pins
 -> bounded GET-only inert-text acquisition
 -> deterministic normalization + exact section selection
 -> content-addressed canonical chunks
 -> checked hash/provenance manifest
 -> deterministic S3 publication
 -> Bedrock Knowledge Base ingestion
 -> Titan Text Embeddings V2 / 1024 / FLOAT32
 -> Amazon S3 Vectors / cosine
 -> direct bounded Retrieve
 -> strict provider parser
 -> checked-corpus S3/hash/metadata reconciliation
 -> RetrievedChunk[]
 -> RetrievalEvidence
 -> deterministic rank-prefix context assembly
 -> AssembledContext
 -> deterministic pre-model authority decision
 -> SynthesisRequest
 -> trusted/untrusted prompt envelope
 -> exactly one bounded Bedrock Converse call
 -> strict provider response evidence admission
 -> deterministic synthesis output parser
 -> SynthesisResult
 -> future deterministic citation projection
```

Retrieval and synthesis remain separately observable and measurable. `RetrieveAndGenerate` is deliberately not used.

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

Phase 7 owns a dedicated S3 Vectors bucket/index separate from the general-purpose source-data bucket.

## 5. Deterministic structured authorities

### Threat Intelligence Data Lake — Phase 2

NVD, KEV, EPSS, and GHSA remain source-local deterministic evidence with explicit provenance and time semantics.

### Vulnerability Correlation — Phase 3

```text
package/version/purl
 + exact vulnerable-range evidence
 -> deterministic PEP 440 evaluation
 -> affected | not_affected | unsupported
 -> CVE/GHSA/NVD reconciliation
 -> content-addressed evidence
```

> **No LLM decides vulnerability applicability.**

### Repository Intelligence — Phase 4

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

### Risk Prioritization — Phase 5

```text
RepositoryAnalysisResult
 -> pure deterministic Risk Policy v1
 -> factor contributions
 -> priority score + tier
 -> completeness / review_required
```

The priority value is an OpsLens policy score, not exploit probability, CVSS, EPSS, or runtime exposure.

### Semantic Query — Phase 6

```text
question
 -> bounded Bedrock planner
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded Athena execution
```

ADRs:

```text
0020 No unrestricted text-to-SQL
0021 Bounded Bedrock semantic-query planner
```

## 6. Knowledge corpus authority — Phase 7

Gate 7.1 froze provider-independent retrieval contracts and bounded query/top-k semantics.

Gate 7.2 authorizes six official source files through immutable repository/commit/path pins and deterministically materializes nine chunks.

Frozen corpus:

```text
manifest id: knowledge-corpus-manifest:v1
documents:   6
chunks:      9
sha256:      98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

The checked manifest stores provenance/hashes, not third-party source text.

Authorized source text is still untrusted instruction content.

## 7. Vector Knowledge Base — Gate 7.3

ADR 0022 selects a customer-managed Bedrock vector Knowledge Base backed by S3 Vectors.

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

The dedicated Knowledge Base service role owns only the ingestion/storage integration responsibility; it is not a human or future application runtime identity.

## 8. Direct retrieval — Gates 7.4–7.5

Gate 7.4 uses direct Knowledge Base `Retrieve` so retrieval quality, latency, provenance, and failure behavior remain independently measurable.

Runtime request authority is limited to:

```text
knowledgeBaseId
retrievalQuery.text
retrievalConfiguration.vectorSearchConfiguration.numberOfResults
```

No arbitrary provider DSL, reranking, generation, or implicit pagination is accepted.

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

### Retrieval evaluation baseline

Frozen real Gate 7.5 dataset:

```text
10 cases
8 positive
2 negative/out-of-authority
one top_k=10 ranking per case
```

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Both negative cases returned non-empty nearest-neighbor results with rank-1 scores near `0.689`, overlapping legitimate evidence.

Therefore:

- vector retrieval existence is not an authority decision;
- provider relevance score is not calibrated confidence;
- no global similarity threshold is justified by this fixture;
- authority/routing must precede synthesis;
- `Repository Risk != Runtime Exposure` remains enforceable outside RAG.

## 9. Deterministic context assembly — Gate 7.6a

Provider-independent contracts:

```text
ContextAssemblyLimits
ContextEvidenceBlock
AssembledContext
ContextAssemblyStopReason
```

Bounds:

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
 -> never skip and backfill lower ranks
 -> AssembledContext
```

Provider relevance score is intentionally absent from `ContextEvidenceBlock`.

`context_sha256` binds query identity, context limits, selected canonical provenance/content hashes, ranks, counts, and stop reason.

## 10. Synthesis authority contract — Gate 7.6b

Pre-model authority is deterministic:

```text
SUPPORTED
UNSUPPORTED
```

`UNSUPPORTED` cannot form a `SynthesisRequest` and cannot create an AWS client/model call.

Allowed model decisions after admission:

```text
ANSWER
INSUFFICIENT_EVIDENCE
```

The model cannot redefine routing authority.

Application bounds:

```text
question:            <= 1,000 characters
model calls:         exactly 1 maximum
answer:              <= 4,000 characters
raw response parser: <= 65,536 characters
```

Prompt trust classes remain separate:

```text
trusted system instructions
untrusted user question
untrusted but source-verified retrieved evidence
```

The trusted instructions explicitly reject commands, role changes, policy changes, tool requests, and attempts to ignore control instructions found inside retrieved evidence.

Prompt/request/result identities use deterministic SHA-256 evidence.

## 11. Bedrock synthesis provider boundary — Gates 7.6c–7.6d

ADR 0023 freezes:

```text
Region:                  us-east-1
endpoint:                bedrock-runtime
API:                     Converse
streaming:               no
provider/model:          Anthropic Claude Haiku 4.5
US Geo inference profile: us.anthropic.claude-haiku-4-5-20251001-v1:0
temperature:             0.0
provider maxTokens:      2,048
tools:                   none
application calls:       1 maximum
structured output:       JSON Schema
```

The US Geographic profile may route from `us-east-1` to the documented US destination Regions. Global inference is intentionally not selected.

Converse requires `bedrock:InvokeModel`; the non-streaming path does not require `bedrock:InvokeModelWithResponseStream`.

No application runtime principal exists yet. Final least-privilege IAM attachment is deferred until a real compute principal exists rather than creating unused role surface.

`BedrockKnowledgeSynthesizer` performs exactly one injected `converse()` call and requires:

```text
provider request identity
stopReason=end_turn
exactly one assistant text block
usage counters
token-total consistency
provider latency
client elapsed time
retry count
valid deterministic synthesis JSON
request/prompt/context identity consistency
```

Provider/runtime failures and legitimate `insufficient_evidence` abstention remain separate typed outcomes.

Automatic Bedrock model-invocation body logging remains disabled because the prompt contains user/source text. Content-free metadata/hashes are recorded instead.

## 12. First real bounded synthesis — Gate 7.6e

Exactly one supported lab execution completed successfully.

Retrieval:

```text
provider request id:  4835c5d0-4a4e-4f47-9610-482ab6ec1103
requested/returned:   5 / 5
client elapsed:       1463 ms
SDK retries:          0
rank 1:               knowledge-chunk:pypa-secure-installs:hashes:v1
rank 1 score:         0.8649594783782959
```

Context:

```text
selected chunks:      5
selected UTF-8 bytes: 5828
stop reason:          exhausted_retrieval
context sha256:       bba245b46a1f8cbb2c42010b61e1ef397b2cde9c92fc0439ee0dc03197788445
```

Synthesis:

```text
provider request id: eee2a118-f806-40d5-8f53-57c88da8ad16
decision:            answer
answer chars:        1751
input tokens:        2671
output tokens:       491
total tokens:        3162
Bedrock latency:     7217 ms
client elapsed:      7983 ms
SDK retries:         0
stop reason:         end_turn
```

The exact answer is content-addressed through its result evidence. No replay was performed.

## 13. Gate 7.6f quality interpretation

The rank-1 evidence is the frozen PyPA `Hash-checking Mode` section pinned to:

```text
repository: pypa/pip
commit:     173eb9b290e2924f0cd42b7714645b38b4df2e81
path:       docs/html/topics/secure-installs.md
```

A manual single-answer review found the generated answer's substantive guidance supported by that admitted source slice. No structured vulnerability, runtime-exposure, or Risk Policy claim was introduced.

The source-supported pip 26.2+ `--no-require-hashes` behavior is an explicit compatibility exception because it weakens global enforcement. The answer framed it as optional/selective behavior; Gate 7.6 does not post-hoc tune the prompt from this single observation.

This is not a production groundedness metric. Gate 7.7 must evaluate unsupported claims and citation correctness/coverage systematically.

## 14. Cost discipline

Deliberate non-adoption remains part of the architecture:

- no Bedrock model for deterministic applicability or Risk Policy;
- no OpenSearch Serverless before a measured hybrid-search requirement;
- no runtime cache before measured reuse/invalidation requirements;
- no invented runtime IAM role before actual compute exists;
- no `RetrieveAndGenerate` when direct retrieval and synthesis need independent observability;
- no extra model call merely to improve a benchmark number.

Gate 7.6 first-run model usage:

```text
2671 input tokens * $1.10 / 1M = $0.0029381
491 output tokens * $5.50 / 1M = $0.0027005
model total                       = $0.0056386
```

One S3 Vectors query-request component:

```text
$0.0000025
```

Directly computable components total:

```text
$0.0056411
```

This is not a full bill. Bedrock `Retrieve` does not expose exact Titan query-embedding billable units or S3 Vectors data-processed/data-returned units, so OpsLens does not fabricate them.

## 15. Latency and observability

Measured first-run stages:

```text
retrieval client elapsed: 1463 ms
Bedrock model latency:    7217 ms
synthesis client elapsed: 7983 ms
```

The simple sequential client-stage sum is `9446 ms`, but there was no separate outer stopwatch.

AWS documents possible first-use structured-output grammar compilation latency, so the first `7217 ms` model latency is preserved as first-run evidence rather than treated as warmed steady-state SLA.

Operational evidence includes provider request IDs, retry counts, token usage, model/profile ID, stage latency, context/request/prompt/result hashes, and deterministic provenance. Raw model-invocation body logging is not enabled.

## 16. Security boundaries

```text
Human administration
 -> IAM Identity Center

GitHub Actions
 -> OIDC
 -> deployment role
 -> Terraform-managed AWS changes

Repository Intelligence
 -> bounded read-only GitHub authority
 -> inert evidence only
 -> no third-party code execution

Semantic Query
 -> bounded Bedrock planning proposal
 -> deterministic parser/compiler authority
 -> bounded read-only Athena

Canonical Knowledge Corpus
 -> immutable official source pins
 -> inert untrusted text
 -> deterministic normalization/selection/hashing

Knowledge Base ingestion
 -> dedicated service role
 -> exact source prefix + embedding model + vector index

Retrieval runtime
 -> direct bounded Retrieve
 -> checked-corpus admission
 -> provider score non-authoritative

Context assembly
 -> admitted retrieval evidence only
 -> whole contiguous rank prefix
 -> deterministic chunk/byte bounds

Synthesis admission
 -> deterministic supported/unsupported authority
 -> unsupported means zero model calls

Synthesis runtime
 -> exactly one bounded Converse call
 -> no tools / no streaming
 -> retrieved text remains untrusted data
 -> strict response/output evidence admission
```

Runtime Exposure remains a later independent evidence domain and cannot be inferred from repository risk or vector similarity.

## 17. ADR index

```text
0020 No unrestricted text-to-SQL
0021 Bounded Bedrock semantic-query planner
0022 Customer-managed Bedrock Knowledge Base with S3 Vectors
0023 Bounded Bedrock knowledge synthesis
```

## 18. Quality gates

Dedicated CI slices cover:

```text
Correlation
Repository Intelligence
Risk Policy
Semantic Query
Knowledge Retrieval
Terraform static/security checks
```

Real AWS evidence complements but does not replace offline tests, strict typing, linting, deterministic regressions, and IaC security validation.

## 19. Next architecture decision — Gate 7.7

Add deterministic citations and groundedness evaluation without granting citation authority to the model.

Required boundary:

```text
SynthesisResult
 + admitted AssembledContext
 -> deterministic citation projection
 -> answer with canonical citations
 -> citation correctness/coverage evaluation
 -> unsupported-claim / groundedness evaluation
```

Model-authored URLs, document IDs, chunk IDs, or source IDs must never become canonical citation authority.

Gate 7.7 should build a versioned evaluation fixture before any post-hoc prompt tuning and should keep answer quality, citation correctness, citation coverage, abstention, and unsupported claims separately measurable.
