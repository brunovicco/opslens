# OpsLens Architecture

_Last updated: 2026-09-06_

This document is the accumulated architecture baseline through **Phase 7 — Gate 7.7b: deterministic citation authority + grounded claim contract**.

The next architecture boundary is **Gate 7.7c: frozen groundedness/citation evaluation semantics**.

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
- package identity normalization, vulnerable-range matching, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS evidence, and Risk Policy remain deterministic;
- semantic-query validation and SQL compilation remain deterministic;
- canonical corpus normalization, selection, hashing, and checked manifest identity remain deterministic;
- retrieval evidence admission, evaluation, context assembly, synthesis admission, citation authority, output admission, and metric computation remain deterministic;
- model outputs are evidence/proposals, not authority over structured truth;
- a model may later select among allowlisted citation IDs but may not author canonical source identity;
- a syntactically valid citation does not prove semantic support;
- retrieved/source content remains untrusted data even after provenance admission;
- provenance admission proves source/content identity, not trusted-instruction status;
- schema, provenance, authority, exact-evidence, or content-addressed identity mismatches fail closed;
- IAM uses least privilege and responsibility separation;
- AWS services are introduced only for concrete requirements;
- cost and observability are architecture requirements;
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

### Explanatory/remediation knowledge path through Gate 7.7b

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
 -> one bounded Bedrock Converse synthesis call
 -> deterministic synthesis output admission
 -> SynthesisResult
 -> deterministic C1..Cn citation catalog
 -> GroundedSynthesisRequest
 -> structured claim + citation-ID proposal contract
 -> GroundedSynthesisResult
 -> next: explicit support judgments + deterministic metrics
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

The checked manifest stores provenance/hashes, not third-party source text. Authorized source text is still untrusted instruction content.

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

The Knowledge Base service role is an ingestion/storage integration identity, not a human or application runtime identity.

## 8. Direct retrieval — Gates 7.4–7.5

Gate 7.4 uses direct Knowledge Base `Retrieve` so retrieval quality, latency, provenance, and failure behavior remain independently measurable.

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

Frozen Gate 7.5 real baseline:

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

Both negative cases returned non-empty nearest-neighbor results with rank-1 scores near `0.689`, overlapping legitimate evidence.

Therefore vector retrieval existence and similarity score are not routing/answerability authority.

## 9. Context assembly — Gate 7.6a

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
 -> never skip/backfill lower ranks
 -> AssembledContext
```

Provider relevance score is intentionally absent from `ContextEvidenceBlock`.

## 10. Synthesis authority — Gates 7.6b–7.6d

Pre-model authority is deterministic:

```text
SUPPORTED
UNSUPPORTED
```

`UNSUPPORTED` cannot form a `SynthesisRequest` or make a model call.

Allowed model decisions after admission:

```text
ANSWER
INSUFFICIENT_EVIDENCE
```

Application bounds:

```text
question:            <= 1,000 characters
model calls:         exactly 1 maximum
answer:              <= 4,000 characters
raw response parser: <= 65,536 characters
```

Prompt trust classes remain structurally separate:

```text
trusted system instructions
untrusted user question
untrusted but source-verified retrieved evidence
```

ADR 0023 freezes the first synthesis provider boundary:

```text
Region:                   us-east-1
endpoint:                 bedrock-runtime
API:                      Converse
streaming:                no
provider/model:           Anthropic Claude Haiku 4.5
US Geo inference profile: us.anthropic.claude-haiku-4-5-20251001-v1:0
temperature:              0.0
provider maxTokens:       2,048
tools:                    none
application calls:        1 maximum
structured output:        JSON Schema
```

`BedrockKnowledgeSynthesizer` requires `stopReason=end_turn`, exactly one assistant text block, consistent token/latency/retry evidence, and deterministic output parsing.

Automatic model-invocation body logging remains disabled because prompts contain user/source text. Content-free metadata/hashes are recorded instead.

No deployed application runtime principal exists yet; least-privilege application IAM attachment remains deferred until actual compute exists.

## 11. First real bounded synthesis — Gates 7.6e–7.6f

Gate 7.6 was squash-merged through PR #99 at:

```text
cc8097b3e2e9b048ca069e961736788de0a79f0d
```

Exactly one supported first run completed successfully without replay.

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

A manual one-answer comparison to the exact frozen PyPA `Hash-checking Mode` source found its seven substantive guidance items supported. That review is not treated as a groundedness benchmark.

Directly computable first-run cost components total `$0.0056411`; unexposed Titan query-embedding and S3 Vectors processed/returned units remain uncomputed rather than fabricated.

## 12. Deterministic citation authority — Gate 7.7a

Gate 7.7 begins from merged Gate 7.6 and initially makes zero AWS/model calls.

```text
AssembledContext
 -> selected ContextEvidenceBlock[] only
 -> deterministic C1..Cn
 -> ProjectedCitation[]
 -> CitationCatalog
```

`ProjectedCitation` binds:

```text
citation_id
retrieval_rank
canonical_uri
source_id
document_id
chunk_id
document_content_sha256
chunk_content_sha256
title
section_path
citation_sha256
```

`CitationCatalog` binds the exact citation sequence to `context_sha256` and `catalog_sha256`.

Security/authority consequences:

- retrieval suffixes excluded from context cannot be cited;
- a model cannot redefine `C1` to another URL or chunk;
- provider similarity score is absent from citation authority;
- source text is not duplicated into citation operational identity;
- canonical provenance comes from admitted context, not model output.

## 13. Grounded claim/citation contract — Gate 7.7b

A citation-aware request binds:

```text
SynthesisRequest
 + exact CitationCatalog
 -> GroundedSynthesisRequest
```

The catalog must reference the exact synthesis `context_sha256`.

Frozen provider-independent proposal:

```json
{
  "decision": "answer",
  "claims": [
    {"text": "...", "citation_ids": ["C1", "C2"]}
  ]
}
```

or:

```json
{"decision": "insufficient_evidence", "claims": []}
```

Ownership rules:

- claim indices are deterministic and not model-authored;
- URLs/source IDs/document IDs/chunk IDs/hashes are never accepted from model output;
- every answer claim requires at least one catalog citation;
- unknown/duplicate citation IDs fail closed;
- citation order canonicalizes to deterministic catalog order;
- extra provenance fields fail closed;
- abstention contains zero claims;
- deterministic rendering permits no prose outside the admitted cited claims;
- Gate 7.6 output bounds remain authoritative.

Grounded bounds:

```text
max claims:            16
max chars/claim:      1,000
rendered answer:      <= admitted synthesis max_output_chars (hard <= 4,000)
raw provider response: <= 65,536 chars
```

Content-addressed identities:

```text
CitationCatalog.catalog_sha256
GroundedSynthesisRequest.grounded_request_sha256
GroundedClaim.claim_sha256
GroundedSynthesisResult.result_sha256
```

This contract guarantees that every admitted answer claim references at least one real catalog citation. It does **not** prove semantic support.

## 14. Groundedness evaluation boundary — Gate 7.7c NEXT

RAG evaluation must keep separate dimensions separate:

```text
retrieval relevance
citation target precision/recall
claim supportedness
citation correctness
unsupported claim rate
abstention behavior
```

A correct citation identifier can still be attached to a claim the source does not support.

Before any citation-aware provider call or prompt/schema change, Gate 7.7c must freeze:

- evaluation questions and expected evidence targets;
- support-judgment provenance;
- typed observations;
- deterministic metric formulas;
- explicit handling for unsupported/abstention cases.

Human-reviewed labels may be deterministic golden truth. A future evaluator model may provide a bounded evaluation signal, but model judgment must not silently become truth authority.

## 15. Cost discipline

Deliberate non-adoption remains part of the architecture:

- no Bedrock model for deterministic applicability or Risk Policy;
- no OpenSearch Serverless before a measured hybrid-search requirement;
- no runtime cache before measured reuse/invalidation requirements;
- no invented runtime IAM role before actual compute exists;
- no `RetrieveAndGenerate` when direct retrieval and synthesis need independent observability;
- no extra model calls merely to improve a benchmark number;
- no citation-aware Bedrock call before Gate 7.7 evaluation semantics are frozen.

Gate 7.7a/7.7b add:

```text
AWS calls:       0
model calls:     0
AWS resources:   0
IAM permissions: 0
provider cost:   $0
```

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

Citation authority
 -> only selected context blocks
 -> deterministic C1..Cn
 -> canonical provenance/hashes from code
 -> no model-authored source identity

Grounded output admission
 -> every answer claim must cite catalog IDs
 -> no uncited prose outside claims
 -> valid citation syntax != semantic support
```

Runtime Exposure remains a later independent evidence domain and cannot be inferred from repository risk or vector similarity.

## 17. ADR index

```text
0020 No unrestricted text-to-SQL
0021 Bounded Bedrock semantic-query planner
0022 Customer-managed Bedrock Knowledge Base with S3 Vectors
0023 Bounded Bedrock knowledge synthesis
```

No new ADR is required for 7.7a/7.7b yet because these are provider-independent deterministic contracts extending the already-documented synthesis boundary. A new ADR should be added only if Gate 7.7d changes model/API/IAM or introduces a new evaluation authority.

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

Gate 7.7 checkpoint evidence:

```text
Python CI #266: SUCCESS — citation catalog
Python CI #267: FAIL — Ruff export ordering only
Python CI #268: SUCCESS — grounded claim/citation contract
```

Real AWS evidence complements but does not replace offline tests, strict typing, linting, deterministic regressions, and IaC security validation.

## 19. Next architecture decision — Gate 7.7c

Freeze groundedness evaluation before changing the provider prompt:

```text
frozen evaluation case
 + expected evidence target
 + GroundedSynthesisResult
 + explicit support judgments
 -> deterministic citation metrics
 -> deterministic claim groundedness metrics
```

Do not optimize the prompt against observed provider output before this fixture and metric contract is versioned and CI-green.
