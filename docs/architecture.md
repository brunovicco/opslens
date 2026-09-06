# OpsLens Architecture

_Last updated: 2026-09-06_

This document is the accumulated architecture baseline through **Phase 7 — Gate 7.7: deterministic citations + measured groundedness**.

The next architecture boundary is **Gate 7.8: Phase 7 closeout**.

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
- canonical corpus normalization, selection, hashing, and checked-manifest identity remain deterministic;
- retrieval admission, context assembly, synthesis admission, citation authority, output admission, support-evidence validation, and metric computation remain deterministic;
- model outputs are evidence/proposals, not authority over structured truth;
- a model may select among allowlisted citation IDs but may not author canonical source identity;
- a syntactically valid citation does not prove semantic support;
- retrieved/source content remains untrusted data after provenance admission;
- provenance admission proves source/content identity, not trusted-instruction status;
- schema, provenance, authority, exact-evidence, or content-addressed identity mismatches fail closed;
- IAM uses least privilege and responsibility separation;
- AWS services are introduced only for concrete requirements;
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

### Explanatory/remediation knowledge path through Gate 7.7

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
 -> deterministic contiguous rank-prefix context assembly
 -> AssembledContext
 -> deterministic pre-model authority decision
 -> SynthesisRequest
 -> trusted/untrusted prompt envelope
 -> one bounded Bedrock Converse synthesis call
 -> deterministic synthesis output admission
 -> deterministic C1..Cn citation catalog
 -> GroundedSynthesisRequest
 -> structured claim + citation-ID proposal
 -> GroundedSynthesisResult
 -> explicit human-reviewed claim/citation support judgments
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

Therefore vector retrieval existence and similarity score are not routing or answerability authority.

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

## 10. Synthesis authority — Gate 7.6

Pre-model authority is deterministic:

```text
SUPPORTED
UNSUPPORTED
```

`UNSUPPORTED` cannot form a synthesis request or make a model call.

Allowed model decisions after admission:

```text
ANSWER
INSUFFICIENT_EVIDENCE
```

Application bounds:

```text
question:            <= 1,000 characters
model calls:         1 maximum per application attempt
answer:              <= 4,000 characters
raw response parser: <= 65,536 characters
```

Prompt trust classes remain structurally separate:

```text
trusted system instructions
untrusted user question
untrusted but source-verified retrieved evidence
```

ADR 0023 freezes the synthesis provider boundary:

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
structured output:        JSON Schema
```

`BedrockKnowledgeSynthesizer` requires `stopReason=end_turn`, exactly one assistant text block, consistent token/latency/retry evidence, and deterministic output parsing.

Automatic model-invocation body logging remains disabled because prompts contain user/source text. Content-free metadata/hashes are recorded instead.

No deployed application runtime principal exists yet; least-privilege application IAM attachment remains deferred until actual compute exists.

## 11. First real bounded synthesis — Gate 7.6

Gate 7.6 was squash-merged through PR #99 at:

```text
cc8097b3e2e9b048ca069e961736788de0a79f0d
```

Exactly one supported first run completed successfully without replay.

```text
Retrieve request id:   4835c5d0-4a4e-4f47-9610-482ab6ec1103
retrieval elapsed:     1463 ms
selected chunks:       5
context bytes:         5828

Converse request id:   eee2a118-f806-40d5-8f53-57c88da8ad16
decision:              answer
input/output tokens:   2671 / 491
Bedrock latency:       7217 ms
client elapsed:        7983 ms
SDK retries:           0
```

A manual one-answer comparison to the exact frozen PyPA `Hash-checking Mode` source found its substantive guidance supported. That review is not treated as a groundedness benchmark.

Directly computable first-run cost components total `$0.0056411`; unexposed Titan query-embedding and S3 Vectors processed/returned units remain uncomputed rather than fabricated.

## 12. Deterministic citation authority — Gate 7.7a

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
- deterministic rendering permits no prose outside admitted cited claims;
- Gate 7.6 output bounds remain authoritative.

This contract guarantees citation presence for every admitted answer claim. It does not guarantee semantic support.

## 14. Groundedness evaluation — Gates 7.7c–7.7e

Frozen dataset before provider execution:

```text
knowledge-grounding-golden:v1
3 expected answer cases
1 expected insufficient-evidence case
judgment authority: human_reviewed_claim_citation_pairs_v1
```

The evaluator keeps distinct:

```text
citation target precision / recall
claim supportedness
unsupported claim rate
claim/citation pair correctness
answer/abstention decision behavior
```

The first real four-case run was executed once from pre-run CI-green head:

```text
507fe04f963c7eeb49748eb950101ea2fc55e14f
```

No provider replay or prompt tuning occurred after observing the baseline.

Runtime totals:

```text
application complete:              true
real Retrieve calls:               4
real grounded Converse calls:      4
input tokens:                      11,734
output tokens:                     645
total tokens:                      12,379
retrieval latency mean:            790.0 ms
Bedrock latency mean:              3396.5 ms
client synthesis mean:             3743.25 ms
SDK retries:                       0
```

Human-reviewed semantic support is preserved as metadata-only, content-addressed evidence:

```text
labs/evidence/phase-7-gate-7-7-first-run-review-v1.json
```

The evidence artifact stores exact claim hashes, selected citation IDs/chunk identities, result/request/catalog hashes, and human-reviewed judgment hashes. It does not duplicate source bodies or copied model claim text.

Measured baseline:

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

### Architecture lesson from the isolation case

The frozen isolation evidence target was successfully retrieved at rank 1 and became `C1`. The model nevertheless cited `C2`, an adjacent post-change testing-outcomes chunk, for both generated claims.

Strict exact-chunk review marked both claim/citation pairs unsupported because the claims included the testing/isolated-environment premise while their only citation did not establish that premise.

Therefore:

```text
retrieval success
 != citation attribution success
 != claim groundedness
```

This failure is intentionally retained in the baseline. Correcting the prompt or citation-selection policy requires a new version and a fresh evaluation, not post-hoc modification of the Gate 7.7 fixture.

### Architecture lesson from abstention

The exact pip TLS-cipher case still returned five nearest-neighbor chunks, but the grounded model returned `insufficient_evidence` with zero claims.

Therefore:

```text
non-empty vector retrieval
 != sufficient evidence
 != authority to answer
```

This aligns with the Gate 7.5 negative-control result and reinforces the need for an independent answerability boundary.

## 15. Cost discipline

Gate 7.7 directly computable four-case cost:

```text
model input:             $0.0129074
model output:            $0.0035475
model subtotal:          $0.0164549
4 S3 Vectors requests:   $0.0000100
computable total:        $0.0164649
```

This is not called the complete AWS bill. Exact Titan query-embedding consumption and S3 Vectors data-processed/data-returned units are not available in the runtime evidence.

Deliberate non-adoption remains part of the architecture:

- no LLM for deterministic applicability or Risk Policy;
- no OpenSearch Serverless before a measured hybrid-search need;
- no reranker before evaluation demonstrates a requirement;
- no runtime cache before measured reuse/invalidation requirements;
- no invented application IAM role before actual compute exists;
- no provider-generated canonical citations;
- no post-hoc score threshold derived from the small retrieval fixture.

## 16. IAM boundary

Current identities remain separate:

```text
human operator
 -> IAM Identity Center temporary session

GitHub Actions
 -> OIDC / STS deployment identity

Bedrock Knowledge Base service role
 -> ingestion/vector-store integration only

future deployed application runtime
 -> NOT YET CREATED
```

The absence of a deployed runtime principal is intentional. Gate 7.8 must document the minimal future permissions before any compute principal is introduced. The expected capability shape is bounded to the already-proven runtime APIs rather than broad Bedrock administration.

## 17. Observability boundary

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

What this does not yet constitute:

```text
production SLOs
continuous CloudWatch application metrics for the RAG path
end-user trace correlation across a deployed runtime
production alert thresholds
high-volume cost distribution
```

Those are not fabricated from small lab samples.

## 18. Phase 7 closeout boundary — Gate 7.8 NEXT

Gate 7.8 must consolidate, not optimize:

```text
failure taxonomy
IAM least-privilege plan
cost attribution map
observability map
ADR/document consistency
quality/regression inventory
explicit Phase 8 entry criteria
versioned future optimization backlog
```

The closeout must explicitly preserve the distinction between:

```text
structured truth authority
semantic retrieval evidence
context admission
model answerability
citation authority
citation target alignment
claim supportedness
runtime exposure evidence
```

Only after those boundaries are reconciled should OpsLens enter Phase 8 Hybrid Retrieval.

## 19. Phase 8 entry principle

Hybrid retrieval must not simply concatenate SQL rows and vector chunks.

The future design needs an explicit router/authority contract in which deterministic structured evidence remains authoritative for vulnerability/risk facts, while semantic evidence contributes explanatory/remediation context only where the request is authorized and evaluation demonstrates value.

Phase 8 must therefore start from the Phase 7 measured baseline rather than replacing it.
