# OpsLens — Current State

_Last updated: 2026-09-05_

This document is the public implementation checkpoint for the OpsLens repository.

## Status

```text
Phase 0    AWS Foundation                                      COMPLETE
Phase 1    EPSS Vertical Slice                                 COMPLETE
Phase 2    Threat Intelligence Data Lake                       COMPLETE
Phase 3    Vulnerability Correlation Engine                    COMPLETE
Phase 4    Repository Intelligence                             COMPLETE
Phase 5    Risk Prioritization Engine                          COMPLETE
Phase 6    Semantic Query Layer                                COMPLETE
  Gate 6.1 Typed contract + deterministic SQL compiler         COMPLETE
  Gate 6.2 Bounded read-only Athena execution                  COMPLETE
  Gate 6.3 Bounded planner contract + offline evaluation       COMPLETE
  Gate 6.4 Real Bedrock planner invocation                     COMPLETE
Phase 7    Knowledge Retrieval with Bedrock                    IN PROGRESS
  Gate 7.1 Corpus + retrieval contract                         COMPLETE
  Gate 7.2 Reproducible canonical corpus                       COMPLETE
  Gate 7.3 Knowledge Base + vector infrastructure              COMPLETE / MERGE PENDING
  Gate 7.4 Real bounded Retrieve adapter                       NEXT
```

Phase 6 was squash-merged through PR #91:

```text
commit: 95db66e278059629ce6572b2950e9cca705c6498
PR:     #91 — feat(semantic-query): close Gate 6.4 with real Bedrock runtime evidence
```

Gate 7.1 was squash-merged through PR #93:

```text
commit: f2e3b72c31d0713707857bc0867a7f59e667b9dd
PR:     #93 — feat(knowledge-retrieval): start Phase 7 Gate 7.1 contracts
```

Gate 7.2 was squash-merged through PR #94. Its frozen corpus identity is:

```text
manifest sha256: 98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
documents: 6
chunks: 9
```

Gate 7.3 is complete on PR #95 and awaits final green closeout + logical merge.

## Permanent boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

Deterministic authorities remain responsible for:

- package identity normalization;
- version parsing and vulnerable-range matching;
- vulnerability applicability;
- CVE/GHSA/NVD alias reconciliation;
- KEV, EPSS, and CVSS evidence;
- risk policy evaluation;
- canonical evidence serialization and content addressing;
- planner-output parsing and validation;
- semantic-query validation and SQL compilation;
- Athena admission, execution bounds, and result validation;
- retrieval evidence validation and context admission;
- citation projection from admitted evidence;
- execution/tool/cost enforcement.

LLMs may classify, plan, synthesize, explain, and route over validated evidence. They do not decide vulnerability applicability, receive arbitrary SQL authority, or turn RAG text into a second authority for structured threat facts.

## Implemented deterministic stack

```text
1. Threat Intelligence Data Lake
   NVD / CISA KEV / FIRST EPSS / GitHub Security Advisories

2. Vulnerability Correlation Engine
   PyPI identity / PEP 440 applicability / GHSA / CVE-NVD evidence

3. Repository Intelligence
   immutable public GitHub snapshot / inert uv.lock / repository findings

4. Risk Prioritization Engine
   deterministic Risk Policy v1 / factor explanations / ranking

5. Semantic Query deterministic boundary
   typed SemanticQuery / allowlists / deterministic SQL / bounded Athena

6. Bounded Bedrock planner
   natural-language request / structured planner proposal /
   deterministic parser / typed runtime evidence / fail-closed composition

7. Knowledge retrieval contract foundation
   typed knowledge documents / bounded retrieval requests /
   retrieved chunks + provenance / retrieval evidence / deterministic citations

8. Reproducible canonical knowledge corpus
   immutable official source pins / bounded inert-text acquisition /
   deterministic normalization + section selection / content-addressed manifest

9. Bedrock Knowledge Base vector baseline
   verified S3 publication / Titan Text Embeddings V2 /
   S3 Vectors / bounded ingestion / real vector materialization evidence
```

## Repository and risk path

```text
public GitHub repository
 -> immutable repository identity
 -> exact commit + tree SHA
 -> bounded GET-only GitHub REST acquisition
 -> exact inert uv.lock bytes
 -> deterministic TOML parsing
 -> PyPI package/version/purl normalization
 -> GHSA vulnerable-range applicability
 -> CVE/GHSA/NVD evidence reconciliation
 -> NVD/CVSS enrichment
 -> complete-snapshot CISA KEV evidence
 -> explicit-date FIRST EPSS evidence
 -> content-addressed RepositoryAnalysisResult
 -> deterministic Risk Policy v1
 -> priority score + tier + completeness
 -> content-addressed RiskPrioritizationResult
```

No third-party repository code is executed.

## Risk Policy v1

```text
KEV present                         +40
EPSS >= 0.70 / 0.30 / 0.10          +30 / +20 / +10
max supported CVSS >= 9 / 7 / 4     +20 / +10 / +5
known fixed version                 +10
maximum                              100
```

Priority tiers:

```text
P0 >= 80
P1 >= 60
P2 >= 30
P3 < 30
```

This is an OpsLens priority score, not exploit probability, source severity, or runtime exposure.

Deterministic identities:

```text
risk-policy:v1@sha256:<digest>
risk-evaluation:v1@sha256:<digest>
risk-prioritization:v1@sha256:<digest>
```

## Phase 6 — Semantic Query Layer — COMPLETE

Target architecture:

```text
User question
 -> bounded Bedrock planner
 -> structured planner proposal
 -> deterministic planner-output parser
 -> typed SemanticQuery
 -> deterministic validation
 -> deterministic SQL compiler
 -> exact compiler-shape admission
 -> bounded read-only Athena workgroup
 -> structured result evidence
```

### Gate 6.1 — COMPLETE

First supported factual slice:

> Which CVEs have EPSS of at least 0.7 on an explicit snapshot date?

Contract:

```text
metric:       epss_score
dimension:    cve
filters:      explicit snapshot_date, optional minimum_score
order:        epss_score ASC|DESC, deterministic cve ASC tie break
limit:        1..100, default 20
```

The compiler owns database/table/columns/predicates/order/limit. Filter values become validated positional Athena execution parameters.

ADR: [`adr/0020-no-unrestricted-text-to-sql.md`](adr/0020-no-unrestricted-text-to-sql.md).

### Gate 6.2 — COMPLETE

Bounded real Athena boundary:

```text
database:    opslens_dev
workgroup:   opslens-dev
relation:    "opslens_dev"."epss_scores"
scan cutoff: 10 MiB via enforced workgroup configuration
```

Real Gate 6.2 evidence:

```text
query_execution_id:         958fb573-1a69-4ce6-8a36-d9be45e71c79
row_count:                  20
data_scanned_bytes:         3,785,003 (~3.61 MiB)
engine_execution_time_ms:   973
total_execution_time_ms:    1,128
```

Intentional `limit=101` fails before Athena.

Closeout: [`../labs/phase-6-gate-6-2-athena-readonly-execution.md`](../labs/phase-6-gate-6-2-athena-readonly-execution.md).

### Gate 6.3 — COMPLETE

Frozen bounded planner contract:

```text
question length: <= 1,000 chars
planner decisions: semantic_query | unsupported
supported metric: epss_score
supported dimension: exactly [cve]
required time: explicit YYYY-MM-DD
threshold semantics: inclusive >= only
order: epss_score asc|desc
limit: 1..100
SQL authority: none
```

The deterministic parser rejects extra/missing fields, invalid/relative dates, unsupported values, invalid score/limit values, and injected SQL before reconstructing the existing `SemanticQuery`.

Golden offline fixture:

```text
18 total cases
  8 supported
 10 fail-closed unsupported
```

ADR: [`adr/0021-bounded-bedrock-semantic-query-planner.md`](adr/0021-bounded-bedrock-semantic-query-planner.md).

Closeout: [`../labs/phase-6-gate-6-3-planner-contract-evaluation.md`](../labs/phase-6-gate-6-3-planner-contract-evaluation.md).

### Gate 6.4 — COMPLETE

Real model boundary:

```text
model_id:       us.anthropic.claude-haiku-4-5-20251001-v1:0
client Region:  us-east-1
inference mode: US Geographic system-defined inference profile
streaming:      disabled
tools:          disabled
temperature:    0.0
maxTokens:      256
```

Real supported E2E evidence:

```text
question:                       Which CVEs have EPSS of at least 0.7 on 2026-09-03?
planner decision:               semantic_query
model input/output/total:       942 / 79 / 1021 tokens
Bedrock latency:                1,632 ms
client elapsed:                 2,894 ms
estimated planner cost:         ~$0.00147
Athena rows:                    20
Athena data scanned:            3,785,003 bytes (~3.61 MiB)
Athena total time:              1,192 ms
```

Real fail-closed evidence proved a missing explicit snapshot date returns `unsupported` and never invokes Athena.

Closeout evidence: [`../labs/phase-6-gate-6-4-real-bedrock-planner.md`](../labs/phase-6-gate-6-4-real-bedrock-planner.md).

## Phase 7 — Knowledge Retrieval with Bedrock — IN PROGRESS

Phase 7 creates a separate path for explanatory/remediation questions. It does not replace the Phase 6 structured path and does not duplicate NVD, KEV, EPSS, CVSS, GHSA applicability, repository-version, or risk-policy authority through RAG.

Target flow:

```text
knowledge/remediation question
 -> bounded RetrievalRequest
 -> Bedrock Knowledge Base Retrieve
 -> typed RetrievedChunk[] + provenance
 -> deterministic validation/context admission
 -> bounded Bedrock synthesis
 -> answer + deterministic citations
```

### Gate 7.1 — Corpus + retrieval contract — COMPLETE

The offline-first contract freezes:

```text
KnowledgeDocument
RetrievalRequest
RetrievedChunk
RetrievalEvidence
Citation
```

Frozen v1 retrieval bounds:

```text
query:         non-blank, <= 1,000 characters
top_k:         1..10
default top_k: 5
provider DSL:  none
```

Citations are projected deterministically from admitted `RetrievedChunk` evidence rather than accepting model-authored provenance.

### Gate 7.2 — Reproducible canonical corpus — COMPLETE

Versioned product inputs:

```text
knowledge/corpus/v1/source_registry.json
knowledge/corpus/v1/corpus_spec.json
knowledge/corpus/v1/manifest.json
```

Real corpus shape:

```text
6 official pinned source files
9 canonical chunks
manifest sha256: 98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

No third-party source code is executed and source/chunk text is not vendored into Git.

Closeout evidence: [`../labs/phase-7-gate-7-2-canonical-corpus.md`](../labs/phase-7-gate-7-2-canonical-corpus.md).

### Gate 7.3 — Knowledge Base + vector infrastructure — COMPLETE / MERGE PENDING

Validated architecture:

```text
KB:                  customer-managed Bedrock vector Knowledge Base
KB id:               BTVJ2PBR2A
data source id:      IEL1LBE026
source prefix:       knowledge/corpus/v1/bedrock/
chunking:            NONE
embedding:           amazon.titan-embed-text-v2:0
embedding dimension: 1024
vector type:         FLOAT32
vector store:        S3 Vectors
distance:            cosine
```

Real deterministic publication:

```text
payloads:               18
content objects:         9
metadata sidecars:       9
publication bytes:       14,928
compact sidecar range:   394..493 bytes
manifest identity:       98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

The first real ingestion exposed that the original verbose sidecars exceeded Bedrock's 1024-byte S3 Vectors metadata limit. Job `4S4OLDKNCZ` completed but indexed zero vectors and returned an explicit failure reason saying all nine files were ignored because associated metadata was too large.

The deterministic projection was corrected to validate the final serialized sidecar bytes and use the supported compact metadata representation. No KB/vector resource was recreated.

Successful real ingestion:

```text
job:                              WZRUGOFZPI
status:                           COMPLETE
startedAt:                        2026-09-05T20:41:46.010046+00:00
updatedAt:                        2026-09-05T20:41:57.155598+00:00
observed duration:                11.145552 s
numberOfDocumentsScanned:         9
numberOfNewDocumentsIndexed:      9
numberOfDocumentsFailed:          0
numberOfDocumentsSkipped:         0
vectors materialized:             9
```

A strongly consistent `s3vectors list-vectors` returned exactly nine keys immediately after ingestion.

Real operational failures retained as evidence:

```text
oversized Bedrock metadata -> provider failure reason diagnosed
botocore SSO credential retrieval -> TokenRetrievalError categorized safely
human sts:AssumeRole on KB service role -> AccessDenied as expected
```

The service role was not broadened during troubleshooting. The future Gate 7.4 retrieval identity remains separate from ingestion/vector-write authority.

Closeout evidence: [`../labs/phase-7-gate-7-3-kb-vector-infrastructure.md`](../labs/phase-7-gate-7-3-kb-vector-infrastructure.md).
ADR: [`adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md`](adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md).

## AWS foundation

```text
environment:             dev
primary workload Region: us-east-1
IaC:                     Terraform
human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
```

Persistent AWS access keys are not stored in GitHub.

## Current quality boundary

Dedicated Python CI slices exist for:

```text
src/opslens/correlation
src/opslens/repository_intelligence
src/opslens/risk_policy
src/opslens/semantic_query
src/opslens/knowledge_retrieval
```

The workflow also watches `knowledge/corpus/**`, so corpus authority/spec/manifest changes cannot bypass the Knowledge Retrieval gate.

A pre-existing repo-wide Ruff backlog outside these scoped deterministic slices remains separate technical debt.

## Next action

Close PR #95 as the logical Gate 7.3 increment:

```text
1. require the documentation closeout commit to pass Python/Terraform CI
2. mark PR #95 ready for review
3. confirm mergeability and final checks
4. squash-merge PR #95 into main
5. confirm resulting main commit
6. begin Gate 7.4 on a new branch/PR
```

Gate 7.4 must implement Amazon Bedrock Knowledge Base `Retrieve` directly, not `RetrieveAndGenerate`, so raw retrieval can be measured independently before synthesis. It must use a separate least-privilege runtime identity and preserve Gate 7.1 typed evidence/citation authority.
