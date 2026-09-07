# OpsLens — Current State

_Last updated: 2026-09-07_

This document is the implementation checkpoint for the OpsLens repository. Detailed gate history remains in ADRs, labs, immutable evidence artifacts, merged PRs, and Git history.

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
Phase 8    Hybrid Retrieval                                    COMPLETE
  Gate 8.1 Offline hybrid routing + authority contract         COMPLETE / MERGED
  Gate 8.2 Deterministic hybrid evidence envelope              COMPLETE / MERGED
  Gate 8.3 Frozen hybrid evaluation fixture                    COMPLETE / MERGED
  Gate 8.4 First bounded hybrid synthesis                      COMPLETE / MERGED
  Gate 8.5 Measured optimization decision                      COMPLETE / MERGED — H8.5-01 REJECTED
  Gate 8.6 Phase 8 closeout                                    COMPLETE / MERGED
Phase 9    Public Analyze Your Repository                      IN PROGRESS
  Gate 9.1 Public repository request admission                 COMPLETE / MERGED
  Gate 9.2 Deterministic public analysis orchestration         NEXT
```

Latest merged executable checkpoint:

```text
Phase 9 Gate 9.1 / PR #123
5540d7b508c71aa65d826786618690b7ddc9d433
```

Gate 9.1 issue #122 is closed as completed. The public surface still has no deployed HTTP compute, new IAM principal, or public runtime.

## Permanent architecture boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

Deterministic authorities own:

- package normalization and version/range semantics;
- vulnerability applicability and CVE/GHSA/NVD reconciliation;
- KEV, EPSS, CVSS, and Risk Policy facts;
- SemanticQuery validation and SQL compilation;
- retrieval evidence admission and context assembly;
- hybrid route authorization and required-evidence completeness;
- structured fact projection;
- canonical evidence/citation identity;
- synthesis output admission;
- evaluation metric computation;
- execution limits;
- public request admission and normalized request identity.

LLMs may classify, plan, propose, synthesize, explain, and select among already-admitted citation IDs. They do not own structured truth, evidence completeness, query/SQL authority, risk/applicability decisions, canonical provenance, public input authority, or evaluation metric computation.

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
 -> checked-corpus admission
 -> bounded context assembly
 -> bounded Bedrock Converse synthesis
 -> deterministic citation authority
 -> groundedness evaluation

Typed EvidenceNeed proposal
 -> deterministic hybrid route decision
 -> deterministic authority-separated evidence composition
 -> need-level ALL_REQUIRED admission
 -> HybridEvidenceEnvelope
 -> deterministic F* structured projection
 -> deterministic S* semantic projection
 -> bounded route-aware synthesis
 -> deterministic output admission
 -> independent quality/runtime metrics
 -> versioned measured optimization decisions

Untrusted public repository JSON
 -> strict bounded admission
 -> GitHub URL reduced to validated owner/name/ref coordinates
 -> content-addressed PublicAnalysisRequest
 -> STOP before any external call
```

Structured vulnerability/risk facts remain outside RAG authority. Semantic retrieval supplies explanatory/remediation evidence only. Runtime exposure remains unsupported until a later independent runtime authority is implemented.

## AWS / Bedrock baseline

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

No public application compute principal exists after Gate 9.1.

## Frozen Phase 7 quality

Gate 7.5 retrieval:

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Gate 7.7 groundedness:

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

Preserved distinctions:

```text
retrieval success != citation attribution success != semantic groundedness
non-empty retrieval != sufficient evidence != authority to answer
```

## Phase 8 contracts

### Gate 8.1 — route authority

```text
hybrid-routing:v1
```

```text
vulnerability_facts and/or risk_priority -> STRUCTURED
remediation_guidance                      -> SEMANTIC
structured + remediation                 -> HYBRID
runtime_exposure, alone or mixed         -> UNSUPPORTED
```

Supported routes require `ALL_REQUIRED` evidence.

### Gate 8.2 — authority-separated evidence

```text
hybrid-evidence:v1
```

Structured and semantic evidence remain separate typed collections. Extra/unrequested evidence, missing required needs, invalid ranks, duplicates, or identity drift fail closed. Similarity rank/score are evidence metadata, never truth.

### Gate 8.3 — frozen evaluation

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Six cases:

```text
structured_only_factual
semantic_only_remediation
true_hybrid
unsupported_out_of_authority
partial_structured_evidence
semantic_retrieval_noise
```

Seven independent dimensions:

```text
route_accuracy
structured_fact_correctness
semantic_groundedness
citation_correctness
abstention
latency
cost
```

No composite score exists.

### Gate 8.4 — route-aware bounded synthesis

```text
hybrid-synthesis:v1
```

```text
STRUCTURED  -> deterministic F* facts / 0 model calls
SEMANTIC    -> admitted S* evidence / <=1 model call
HYBRID      -> F* + S* evidence / <=1 model call
UNSUPPORTED -> abstain / 0 model calls
incomplete  -> reject_before_synthesis / 0 model calls
```

The model never authors canonical structured facts or provenance. Each explanatory claim requires admitted semantic citation identity. Provider/output/citation-contract violations fail closed.

## Gate 8.4 real baseline

Immutable evidence:

```text
labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json
```

```text
complete:                            true
planned_case_count:                  6
synthesis_invocation_attempt_count:  3
admitted_model_execution_count:      3
route_accuracy:                      1.0
structured_fact_correctness:         1.0
semantic_groundedness:               0.6666666666666666
citation_correctness:                0.6666666666666666
abstention:                          1.0
latency_ms:                          2959.3333333333335
cost:                                UNMEASURED / null
input tokens:                        4150
output tokens:                       289
total tokens:                        4439
```

The semantic-noise case retrieved/admitted both S1 and S2. S2/rank 2 was the frozen support target; S1/rank 1 was an admitted neighbor. The model emitted claims from both, correctly exposing the distinction:

```text
admission != semantic support
retrieval rank != groundedness
allowlisted citation != correct question-specific citation target
```

## Gate 8.5 measured optimization

H8.5-01 tested one prompt-only policy exactly once after exact-head CI:

```text
experiment: hybrid-optimization:h8.5-01-v1
candidate:  hybrid-synthesis-prompt:h8.5-01-v1
```

Real-run evidence:

```text
labs/evidence/phase-8-gate-8-5-h85-01-first-run-v1.json
```

Execution guardrails passed:

```text
complete:                            true
planned_case_count:                  6
synthesis_invocation_attempt_count:  3
admitted_model_execution_count:      3
all stop reasons:                    end_turn
all SDK retry attempts:              0
route_accuracy:                      1.0
structured_fact_correctness:         1.0
abstention:                          1.0
```

Quality did not improve:

```text
semantic_groundedness: 0.6666666666666666
citation_correctness:  0.6666666666666666
latency_ms:            2997.0
cost:                  UNMEASURED / null
```

Token deltas:

```text
input:   +306
output:   -26
total:   +280
```

Decision:

```text
H8.5-01 = REJECT
semantic_groundedness_target_not_met
citation_correctness_target_not_met
```

The runtime default remains:

```text
HybridSynthesisPromptPolicy.GATE_8_4_V1
hybrid-synthesis-prompt:v1
```

No second H8.5-01 run or post-result prompt mutation is authorized.

## Phase 8 closeout conclusions

Gate 8.6 records:

- the Phase 8 authority and failure taxonomy;
- immutable Gate 8.4 and Gate 8.5 evidence;
- no speculative IAM expansion before public compute exists;
- cost remains separated by stage and hybrid USD cost remains unmeasured;
- current runtime evidence provides request IDs, hashes, route/case behavior, failure categories, tokens, latency, retries, stop reasons, F/S projections, citations, and independent metrics;
- no production SLO/percentile/alert claims are made from laboratory runs;
- top-level EN/PT-BR README, architecture, documentation index, and roadmap are synchronized;
- Phase 9 entry criteria are frozen in `labs/phase-8-gate-8-6-closeout.md`.

Gate 8.6 intentionally performed no AWS/IAM/model changes.

## Phase 9 Gate 9.1 — public request admission

Contract:

```text
public-analysis-request:v1
```

The future public operation is deliberately narrower than internal OpsLens capabilities:

```text
analyze one GitHub repository
```

Accepted untrusted input is a bounded JSON object containing a GitHub repository web URL and optional requested ref. Gate 9.1 reduces that URL locally to validated coordinates before any external capability exists:

```text
untrusted JSON bytes
 -> <= 2048 bytes
 -> strict UTF-8 / duplicate-key / known-field admission
 -> exact HTTPS github.com repository-root URL grammar
 -> reject userinfo / port / query / fragment / controls / percent-encoded paths
 -> Phase 4 owner/name/ref validators
 -> content-addressed PublicAnalysisRequest
 -> STOP
```

Key boundary:

```text
public request admitted
 != repository proven public
 != repository snapshot resolved
 != repository analyzed
```

The original user-controlled URL never becomes fetch authority. A later gate may pass only validated owner/name/ref coordinates into the existing read-only GitHub snapshot resolver, which still owns repository metadata validation, private-repository rejection, and exact commit/tree resolution.

Normalized request identity is independent from raw transport-body provenance. Missing/null `requested_ref` remains null so later source metadata, not Phase 9, determines the repository default branch.

Exact-head validation:

```text
PR #123 head: 26f0d2b5275284d891ee99a7f8276d41cc4f0753
Python CI #346 / run 34079446683: PASS
Public Analysis Ruff:             PASS
Public Analysis Pyright strict:   PASS — 0 errors, 0 warnings
Public Analysis pytest:           PASS — 33 passed
merge SHA:                        5540d7b508c71aa65d826786618690b7ddc9d433
issue #122:                       CLOSED / COMPLETED
```

Gate 9.1 added no AWS resource, IAM permission, runtime GitHub acquisition, Athena call, or Bedrock call.

ADR: `docs/adr/0029-public-repository-request-admission.md`.
Lab: `labs/phase-9-gate-9-1-public-request-admission.md`.

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**.

It is not OpsLens Phase 14 and is not part of Phase 9. It must be re-evaluated against the then-current OpsLens architecture before any integration merge.

## Next authorized step

```text
Phase 9 Gate 9.2 — Deterministic public analysis orchestration
```

Gate 9.2 should compose the already-admitted `PublicAnalysisRequest` with existing immutable snapshot and repository-analysis contracts through dependency-injected ports. It should remain offline/fake-source first, prove that arbitrary URLs cannot re-enter acquisition authority, and freeze deterministic success/failure behavior before any public HTTP deployment.

Public compute/runtime IAM, rate limiting, abuse protection, concurrency, external-call budgets, response projection, and deployment remain later Phase 9 gates. Agents, MCP, AgentCore, A2A, reranking, new vector technology, and runtime exposure remain later phases or separately measured hypotheses rather than automatic Gate 9.2 scope.
