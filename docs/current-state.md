# OpsLens — Current State

_Last updated: 2026-09-06_

This document is the implementation checkpoint for the OpsLens repository.

## Status

```text
Phase 0    AWS Foundation                                      COMPLETE
Phase 1    EPSS Vertical Slice                                 COMPLETE
Phase 2    Threat Intelligence Data Lake                       COMPLETE
Phase 3    Vulnerability Correlation Engine                    COMPLETE
Phase 4    Repository Intelligence                             COMPLETE
Phase 5    Risk Prioritization Engine                          COMPLETE
Phase 6    Semantic Query Layer                                COMPLETE
Phase 7    Knowledge Retrieval with Bedrock                    COMPLETE
  Gate 7.1 Corpus + retrieval contract                         COMPLETE / MERGED
  Gate 7.2 Reproducible canonical corpus                       COMPLETE / MERGED
  Gate 7.3 Knowledge Base + vector infrastructure              COMPLETE / MERGED
  Gate 7.4 Real bounded Retrieve adapter                       COMPLETE / MERGED
  Gate 7.5 Retrieval evaluation                                COMPLETE / MERGED
  Gate 7.6 Context assembly + synthesis                        COMPLETE / MERGED
  Gate 7.7 Citations + groundedness                            COMPLETE / MERGED
  Gate 7.8 Phase 7 closeout                                    COMPLETE / MERGED
Phase 8    Hybrid Retrieval                                    IN PROGRESS
  Gate 8.1 Offline hybrid routing + authority contract         COMPLETE / MERGED
  Gate 8.2 Deterministic hybrid evidence envelope              COMPLETE / MERGED
  Gate 8.3 Frozen hybrid evaluation fixture                    COMPLETE / MERGED
  Gate 8.4 First bounded hybrid synthesis                      NEXT
```

Latest merged executable checkpoint:

```text
Phase 8 Gate 8.3 / PR #112
5c2e3b1caf4b56657ae0e840a35db46df44feaa5
```

Gate 8.3 tracking issue #111 is closed as completed.

## Permanent boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

> **Intent classification != execution authority.**

Deterministic authorities own package normalization, version/range matching, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS evidence, Risk Policy, semantic-query validation and SQL compilation, canonical corpus construction, retrieval evidence admission, context assembly, citation authority, output admission, evaluation metric computation, hybrid route authorization, hybrid evidence admission/completeness, canonical evidence identity, and execution limits.

LLMs may classify, plan, synthesize, explain, propose routes, and select among already-admitted citation IDs. They do not replace structured truth, invent source authority, directly authorize structured/semantic execution, manufacture hybrid evidence completeness, or own evaluation metric computation.

## Implemented system

```text
Threat Intelligence Data Lake
 -> deterministic vulnerability correlation
 -> immutable Repository Intelligence
 -> deterministic Risk Policy v1
 -> bounded Semantic Query Layer

Controlled Knowledge Corpus
 -> customer-managed Bedrock Knowledge Base
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> direct bounded Retrieve
 -> deterministic checked-corpus admission
 -> deterministic bounded context assembly
 -> deterministic pre-model authority decision
 -> bounded non-streaming Bedrock Converse synthesis
 -> deterministic citation catalog
 -> grounded claim/citation output contract
 -> explicit human support judgments
 -> deterministic groundedness metrics

Typed EvidenceNeed proposal
 -> HybridRoutingRequest admission
 -> deterministic route_evidence_request
 -> HybridRouteDecision
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> deterministic evidence projection/admission
 -> need-level + class-level ALL_REQUIRED verification
 -> HybridEvidenceEnvelope
 -> frozen hybrid evaluation fixture
 -> offline route + evidence-admission baseline
```

The structured and semantic paths are complementary. Structured vulnerability/risk facts remain outside RAG authority. Phase 8 now has deterministic routing, deterministic evidence composition, and a frozen pre-synthesis hybrid evaluation contract. It has not yet introduced hybrid model synthesis.

## Phase 7 AWS baseline

```text
knowledge base id:     BTVJ2PBR2A
data source id:        IEL1LBE026
source bucket:         opslens-dev-data-487757851499-us-east-1
Region:                us-east-1
vector store:          Amazon S3 Vectors
embedding model:       amazon.titan-embed-text-v2:0
dimensions:            1024
vector type:           FLOAT32
distance:              cosine
chunking:              NONE
canonical chunks:      9
synthesis profile:     us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Canonical corpus manifest:

```text
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

Successful ingestion materialized exactly nine vectors.

## Retrieval baseline — Gate 7.5

Frozen `knowledge-retrieval-golden:v1`:

```text
10 cases: 8 positive + 2 negative/out-of-authority
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0

latency min:   532 ms
latency mean:  720.0 ms
latency p50:   616 ms
latency p95:   1728 ms
latency max:   1728 ms
SDK retries:   0
```

Both negative cases returned non-empty nearest-neighbor results with rank-1 scores around `0.689`. Retrieval existence or score does not establish answerability.

## Synthesis baseline — Gate 7.6

```text
default max context chunks: 5
hard max chunks:            10
max context bytes:          16,384 UTF-8 bytes
selection:                  contiguous whole-chunk rank prefix
question:                   <= 1,000 characters
model calls/application:    1 maximum
answer:                     <= 4,000 characters
API:                        bedrock-runtime / Converse
streaming:                  no
temperature:                0.0
provider maxTokens:         2,048
tools:                      none
structured output:          JSON Schema
```

First supported real synthesis was executed once without replay:

```text
Retrieve request id:     4835c5d0-4a4e-4f47-9610-482ab6ec1103
Retrieve elapsed:        1463 ms
selected chunks:         5
context bytes:           5828

Converse request id:     eee2a118-f806-40d5-8f53-57c88da8ad16
decision:                answer
input/output tokens:     2671 / 491
Bedrock latency:         7217 ms
client elapsed:          7983 ms
SDK retries:             0
```

Directly computable cost components total `$0.0056411`; unexposed query-embedding and S3 Vectors processed/returned units were not fabricated.

## Groundedness baseline — Gate 7.7

Frozen `knowledge-grounding-golden:v1`:

```text
4 cases
3 expected answers
1 expected abstention
```

The first real four-case run was executed exactly once from validated pre-run head:

```text
507fe04f963c7eeb49748eb950101ea2fc55e14f
```

Runtime totals:

```text
cases completed:                   4 / 4
real Retrieve calls:               4
real grounded Converse calls:      4
SDK retries:                       0
all Converse stop reasons:         end_turn
input tokens:                      11,734
output tokens:                     645
total tokens:                      12,379
retrieval latency mean:            790.0 ms
Bedrock latency mean:              3396.5 ms
client synthesis mean:             3743.25 ms
```

Human-reviewed support evidence:

```text
labs/evidence/phase-7-gate-7-7-first-run-review-v1.json
```

Frozen aggregate metrics:

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

The key preserved weakness is the isolation case: the expected isolation chunk was retrieved at rank 1, but both claims cited the adjacent post-change chunk. This is a citation-attribution/groundedness failure, not retrieval unavailability.

The exact TLS-cipher case correctly abstained despite five retrieved neighbors.

Directly computable four-case cost:

```text
model input:              $0.0129074
model output:             $0.0035475
model subtotal:           $0.0164549
4 S3 Vectors requests:    $0.0000100
computable total:         $0.0164649
```

## Phase 7 closeout decisions — Gate 7.8

### Failure taxonomy

```text
1. route / authority failure
2. provider retrieval failure
3. retrieval evidence-admission failure
4. retrieval relevance / coverage failure
5. context-assembly failure
6. synthesis transport failure
7. synthesis output-admission failure
8. answerability / decision failure
9. citation-authority failure
10. citation-attribution failure
11. semantic groundedness failure
```

### Future application runtime IAM

No application compute principal exists yet and Gate 7.8 created no IAM role.

The future runtime entitlement is documented in ADR 0024:

```text
bedrock:Retrieve
 -> exact Knowledge Base ARN

bedrock:InvokeModel
 -> exact US Geographic inference profile
 -> exact Claude Haiku 4.5 foundation-model ARNs required in
    us-east-1, us-east-2, us-west-2
 -> foundation-model access conditioned on exact inference profile ARN
```

The proven runtime path does not justify `RetrieveAndGenerate`, streaming inference, Knowledge Base administration, data-source management, or direct S3 Vectors application access.

### Cost and observability

Phase 7 keeps ingestion embedding/vector costs, query embedding/vector query costs, and synthesis token costs separate. Only runtime-supported values are reported as computed costs.

Current lab evidence includes provider request IDs, retrieval ranks/scores, provenance hashes, context/catalog/request/result hashes, model/profile identity, token counts, latencies, retries, stop reason, decisions, citation mappings, and human support-judgment hashes.

Phase 7 does not claim production SLOs, high-volume percentiles, end-user trace correlation, production alerts, or full per-request bill attribution without a deployed workload.

## Phase 8 Gate 8.1 — Offline hybrid routing + authority contract

Gate 8.1 froze the provider-independent contract before any new provider integration.

Contract version:

```text
hybrid-routing:v1
```

Recognized evidence needs:

```text
vulnerability_facts
risk_priority
remediation_guidance
runtime_exposure
```

Deterministic v1 policy:

```text
vulnerability_facts and/or risk_priority
 -> STRUCTURED
 -> required evidence: STRUCTURED
 -> completeness: ALL_REQUIRED

remediation_guidance
 -> SEMANTIC
 -> required evidence: SEMANTIC
 -> completeness: ALL_REQUIRED

structured need + remediation_guidance
 -> HYBRID
 -> required evidence: STRUCTURED + SEMANTIC
 -> completeness: ALL_REQUIRED

runtime_exposure, alone or mixed
 -> UNSUPPORTED
 -> required evidence: none
 -> completeness: NOT_APPLICABLE
```

A true hybrid route is intentionally `ALL_REQUIRED`: semantic retrieval cannot substitute structured truth, and structured evidence cannot pretend to contain explanatory/remediation guidance.

`runtime_exposure` is recognized but unavailable until actual runtime authority is implemented in the later Amazon Inspector phase. Repository risk is not promoted into runtime exposure.

Route decisions carry stable reason codes, canonical evidence-need ordering, required evidence classes, completeness semantics, and a versioned content-addressed SHA-256 identity.

ADR:

```text
docs/adr/0025-deterministic-hybrid-routing-authority.md
```

Lab record:

```text
labs/phase-8-gate-8-1-hybrid-routing-contract.md
```

### Gate 8.1 validation

Final executable PR head:

```text
2d73b03030b3a2b0334fbd15dcfba798661f49c4
```

Python CI #298 / run `34047512871` passed all six jobs, including the explicit `Hybrid retrieval quality gates` slice.

An earlier run failed strict Pyright because direct runtime `isinstance` checks on statically typed parameters triggered `reportUnnecessaryIsInstance`. The fix preserved runtime validation behind `object`-typed admission helpers; no `type: ignore` or weakened type-checking rule was introduced.

## Phase 8 Gate 8.2 — Deterministic hybrid evidence envelope

Gate 8.2 froze deterministic composition after routing and before any future hybrid synthesis.

Contract version:

```text
hybrid-evidence:v1
```

Core composition:

```text
HybridRouteDecision
 + StructuredEvidenceRow[]
 + SemanticEvidenceChunk[]
 -> HybridEvidenceEnvelope
```

The envelope deliberately keeps structured and semantic evidence in separate collections. It is a composition artifact, not a new undifferentiated source of truth.

### Structured authority

The deliberately small v1 authority map is:

```text
vulnerability_facts
 -> repository_analysis
 -> semantic_query

risk_priority
 -> risk_policy
```

`semantic_query` here is the existing Phase 6 bounded structured-query subsystem. Its admitted factual output remains structured evidence because deterministic query validation and SQL compilation own the authority boundary; the name does not make it vector/RAG evidence.

Structured evidence binds:

```text
evidence need
authority
source artifact ID
source artifact SHA-256
row key
canonical scalar fields
content-addressed evidence ID
```

Risk Policy evidence cannot be relabeled as vulnerability applicability, repository-analysis evidence cannot be relabeled as `risk_priority`, and structured evidence cannot satisfy `remediation_guidance`.

### Semantic evidence

Gate 8.2 projects already-admitted Phase 7 retrieval evidence without promoting similarity into factual authority. The projection preserves retrieval ID, rank, chunk/document/source IDs, source type, canonical URI, exact content hashes/text, optional relevance score, title, and section path.

For v1, one envelope semantic set must come from exactly one admitted retrieval operation and keep contiguous ranks from 1.

A provider relevance score remains provenance/measurement evidence only. It does not establish applicability, risk, answerability, or authority.

### Need-level completeness

Class-level presence is necessary but insufficient.

For example:

```text
requested needs:
  vulnerability_facts
  risk_priority

required class:
  STRUCTURED
```

One arbitrary structured row does not satisfy both needs. A successful v1 envelope requires:

```text
satisfied_evidence_needs
 ==
authority_decision.evidence_needs
```

Evidence for an unrequested class or need is also rejected. Successful envelopes are therefore complete by construction under `ALL_REQUIRED`; partial/best-effort envelopes are not a normal success state in v1.

### Deterministic identity and provenance

Canonical ordering applies to structured fields, structured evidence rows, semantic chunks, and class provenance memberships. Structured rows, semantic chunks, and the final envelope all receive content-addressed identities.

The envelope identity binds:

```text
hybrid-evidence contract version
exact Gate 8.1 authority decision ID
ALL_REQUIRED completeness
exact satisfied evidence needs
exact structured evidence IDs
exact semantic evidence IDs
```

This supports reproducible evaluation/audit without converting a hash into semantic truth or confidence.

ADR:

```text
docs/adr/0026-deterministic-hybrid-evidence-envelope.md
```

Lab record:

```text
labs/phase-8-gate-8-2-hybrid-evidence-envelope.md
```

### Gate 8.2 validation

Final executable PR head:

```text
70ef54a0a56844b6429c0b8a739352b31d076580
```

Python CI #302 / run `34048762536` passed all six jobs. The dedicated hybrid slice passed:

```text
uv lock --check        PASS
Ruff                   PASS
Pyright strict         PASS — 0 errors, 0 warnings
pytest hybrid slice    PASS — 39 passed
```

The initial PR run exposed lint-only defects: import ordering and Python 3.13's preferred PEP 695 `type` alias syntax. They were corrected directly. No lint suppression, `type: ignore`, weakened strictness, or semantic workaround was introduced.

PR #109 was then squash-merged using exact validated expected head `70ef54a0a56844b6429c0b8a739352b31d076580`, producing:

```text
aea3b66b83bee5d06bc4efab06538dc094df51e6
```

Gate 8.2 created/executed:

```text
AWS resources:     0
IAM changes:       0
Athena calls:      0
Bedrock calls:     0
S3 Vectors calls:  0
model calls:       0
```

The Phase 7 Gate 7.5/Gate 7.7 baselines and Gate 8.1 routing semantics remain unchanged.

## Phase 8 Gate 8.3 — Frozen hybrid evaluation fixture

Gate 8.3 froze the hybrid benchmark before any hybrid model synthesis or tuning.

Frozen dataset:

```text
dataset_id: hybrid-evaluation-golden:v1
sha256:     68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

The dataset requires exactly six scenario classes:

```text
structured_only_factual
semantic_only_remediation
true_hybrid
unsupported_out_of_authority
partial_structured_evidence
semantic_retrieval_noise
```

The semantic-noise case deliberately admits a non-supporting rank-1 neighbor while freezing a rank-2 chunk as the expected support/citation target. This preserves the distinction:

```text
retrieved
!= admitted
!= semantically supporting
!= correctly cited
```

### Frozen metric dimensions

```text
route_accuracy
structured_fact_correctness
semantic_groundedness
citation_correctness
abstention
latency
cost
```

There is no aggregate hybrid-quality score that may hide authority-specific failure.

At Gate 8.3 only `route_accuracy` is a legitimately measured member of the seven frozen response/runtime dimensions. Envelope outcome agreement is recorded separately as deterministic `evidence_admission_accuracy`.

Frozen offline baseline:

```text
route_accuracy:              1.0
evidence_admission_accuracy: 1.0
```

All synthesis/runtime dimensions that do not yet exist remain explicitly `UNMEASURED` with `null` values. Missing model/provider execution is not fabricated as zero latency, zero cost, or perfect correctness.

### Gate 8.3 evaluation path

```text
HybridEvaluationCase
 -> HybridRoutingRequest
 -> route_evidence_request
 -> HybridRouteDecision
 -> assemble_hybrid_evidence when supported
 -> HybridOfflineCaseResult
 -> HybridOfflineBaseline
```

The fixture loader validates exact keys, Gate 8.2 evidence contracts, six-case coverage, seven-metric coverage, metric stage/unit semantics, expected structured facts, semantic support/citation targets, and canonical dataset identity fail-closed.

ADR:

```text
docs/adr/0027-frozen-hybrid-evaluation-contract.md
```

Lab record:

```text
labs/phase-8-gate-8-3-hybrid-evaluation-fixture.md
```

### Gate 8.3 validation

Exact executable PR head:

```text
356b0ccf4d5205d4abd8dab52179423bb2b139e6
```

Python CI #306 / run `34050330182` passed all six jobs. Dedicated hybrid slice:

```text
uv lock --check     PASS
Ruff                PASS
Pyright strict      PASS — 0 errors, 0 warnings
pytest hybrid slice PASS — 49 passed
```

The correction cycle exposed Ruff style/import findings and one strict Pyright redundant integer cast. They were fixed directly without `noqa`, `type: ignore`, lint suppression, or weakened strictness.

PR #112 was promoted from draft only after the exact head above was green, then squash-merged with expected-head protection, producing:

```text
5c2e3b1caf4b56657ae0e840a35db46df44feaa5
```

Issue #111 closed automatically as completed.

Gate 8.3 created/executed:

```text
AWS resources:     0
IAM changes:       0
Athena calls:      0
Bedrock calls:     0
S3 Vectors calls:  0
model calls:       0
```

The Phase 7 Gate 7.5/Gate 7.7 baselines and Gate 8.1/Gate 8.2 authority semantics remain unchanged.

## Gate 8.4 entry criteria

Gate 8.4 starts from these frozen assumptions:

```text
1. Gate 8.1 owns deterministic evidence-class routing authority
2. Gate 8.2 owns deterministic admitted evidence composition
3. Gate 8.3 owns the frozen evaluation fixture and metric dimensions
4. structured and semantic provenance remain distinguishable end to end
5. hybrid v1 remains ALL_REQUIRED by class and exact evidence need
6. successful retrieval/relevance scores do not establish structured truth
7. runtime_exposure remains unsupported without runtime authority
8. missing required evidence must fail before synthesis
9. hybrid-evaluation-golden:v1 is immutable input to the first synthesis baseline
10. observed model behavior may populate metrics but may not rewrite the fixture
11. structured fact correctness, semantic groundedness, citation correctness, and abstention remain independent
12. no new AWS service is added without a measured requirement
```

The first bounded hybrid synthesis may let a model reason over an already-admitted typed envelope. It must not rewrite structured facts into a new truth source, convert vector similarity into applicability/risk truth, author canonical provenance, broaden SQL/tool authority, or silently answer with incomplete evidence.

## Validation note

PR #112 changed executable hybrid-retrieval code and was squash-merged only after Python CI #306 passed against exact executable head `356b0ccf4d5205d4abd8dab52179423bb2b139e6`.

This post-merge state synchronization changes documentation only. The repository `Python CI` pull-request workflow intentionally filters away documentation-only changes, so no new executable validation is expected for this state-only update.

## Next action

Begin **Phase 8 — Gate 8.4: First Bounded Hybrid Synthesis** from merged Gate 8.3 main. Consume the frozen `hybrid-evaluation-golden:v1` fixture unchanged, add the smallest bounded synthesis surface, and measure the synthesis-specific dimensions without weakening deterministic authority boundaries.