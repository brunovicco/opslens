# OpsLens — Current State

_Last updated: 2026-09-06_

This document is the implementation checkpoint for the OpsLens repository. Detailed gate history remains in the ADRs, labs, immutable evidence artifacts, merged PRs, and Git history.

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
  Gate 8.4 First bounded hybrid synthesis                      COMPLETE / MERGED
  Gate 8.5 Measured optimization decision                      COMPLETE / MERGED — H8.5-01 REJECTED
  Gate 8.6 Phase 8 closeout                                    NEXT
```

Latest merged executable checkpoint:

```text
Phase 8 Gate 8.5 / PR #118
ff7aedaf6c5ef987efee0f7e6bb9e169eeb2f538
```

Gate 8.5 tracking issue #117 is closed as completed. A rejected optimization hypothesis is a completed experiment result, not an execution failure.

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
- canonical citation authority and output admission;
- evaluation metric computation;
- execution limits;
- hybrid route authorization;
- hybrid evidence admission/completeness;
- canonical evidence identity.

LLMs may classify, plan, propose routes, synthesize, explain, and select among already-admitted citation IDs. They do not own structured truth, evidence completeness, query authority, SQL authority, risk/applicability decisions, or evaluation metric computation.

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
 -> deterministic groundedness metrics

Typed EvidenceNeed proposal
 -> deterministic hybrid route decision
 -> deterministic typed evidence composition
 -> need-level ALL_REQUIRED admission
 -> HybridEvidenceEnvelope
 -> bounded route-aware synthesis
 -> deterministic structured fact projection
 -> allowlisted semantic citation projection
 -> independent route/structured/groundedness/citation/abstention/latency/cost metrics
 -> measured versioned optimization experiments
```

Structured vulnerability/risk facts remain outside RAG authority. Semantic retrieval provides explanatory/remediation evidence only. Runtime exposure remains unsupported until a later runtime authority is implemented.

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

## Frozen Phase 7 baselines

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

Preserved distinction:

```text
retrieval success != citation attribution success != semantic groundedness
non-empty retrieval != sufficient evidence != authority to answer
```

## Phase 8 authority contracts

### Gate 8.1 — deterministic route authority

Contract:

```text
hybrid-routing:v1
```

Policy:

```text
vulnerability_facts and/or risk_priority -> STRUCTURED
remediation_guidance                      -> SEMANTIC
structured + remediation                 -> HYBRID
runtime_exposure, alone or mixed         -> UNSUPPORTED
```

Runtime exposure is valid-but-unavailable rather than silently mapped to repository risk.

### Gate 8.2 — deterministic typed evidence

Contract:

```text
hybrid-evidence:v1
```

Structured and semantic evidence remain separate typed collections. Successful envelopes require exact need-level completeness and reject extra/unrequested evidence. Similarity score and rank are provenance/measurement metadata only; they are not truth or authority.

### Gate 8.3 — frozen evaluation contract

Frozen dataset:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Exactly six case types:

```text
structured_only_factual
semantic_only_remediation
true_hybrid
unsupported_out_of_authority
partial_structured_evidence
semantic_retrieval_noise
```

Frozen metric dimensions remain independent:

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

## Phase 8 Gate 8.4 — first bounded hybrid synthesis

Contract:

```text
hybrid-synthesis:v1
```

Route-aware execution:

```text
STRUCTURED -> deterministic facts, 0 model calls
SEMANTIC   -> admitted semantic evidence, <=1 bounded model call
HYBRID     -> deterministic facts + admitted semantic evidence, <=1 bounded model call
UNSUPPORTED -> abstain, 0 model calls
incomplete evidence -> reject_before_synthesis, 0 model calls
```

The model does not author canonical structured facts. Every admitted explanatory claim requires at least one admitted semantic citation ID. Unknown IDs, malformed/extra output, provider failure, non-`end_turn`, or other contract violations fail closed.

First complete real Bedrock baseline evidence:

```text
labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json
```

Measured baseline:

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
```

The semantic-noise case produced the measured quality weakness: the model cited the expected rank-two support chunk and also introduced a separate claim citing the admitted rank-one clean-environment neighbor.

This preserves:

```text
admission != semantic support
retrieval rank != groundedness
allowlisted citation != correct citation target
```

## Phase 8 Gate 8.5 — measured optimization decision

Gate 8.5 tested one predeclared prompt-only hypothesis against the immutable Gate 8.4 baseline.

Hypothesis:

```text
H8.5-01
hybrid-optimization:h8.5-01-v1
hybrid-synthesis-prompt:h8.5-01-v1
```

Controlled variable: trusted instructions required the smallest sufficient answer, direct question relevance for every claim, and omission of ancillary guidance.

The experiment did **not** change the frozen fixture/support targets, routing, evidence admission, structured facts, semantic evidence/order/scores, output schema, model, Region, temperature, maxTokens, call budget, unsupported behavior, IAM, or AWS infrastructure.

The runtime default remained:

```text
HybridSynthesisPromptPolicy.GATE_8_4_V1
hybrid-synthesis-prompt:v1
```

### Single real H8.5-01 run

Pre-run exact-head validation:

```text
8ac47d0d45e58a0d12e15e6214e4f820614ee19f
Python CI #341 / run 34065316124: PASS
Hybrid: Ruff PASS / Pyright 0 errors, 0 warnings / pytest 73 passed
```

STS preflight passed and exactly one real candidate execution was performed.

Immutable evidence:

```text
labs/evidence/phase-8-gate-8-5-h85-01-first-run-v1.json
```

Execution guardrails:

```text
complete:                             true
planned_case_count:                   6
synthesis_invocation_attempt_count:   3
admitted_model_execution_count:       3
all stop reasons:                     end_turn
all SDK retry attempts:               0
route_accuracy:                       1.0
structured_fact_correctness:          1.0
abstention:                           1.0
cost:                                 UNMEASURED / null
```

Candidate quality:

```text
semantic_groundedness:  0.6666666666666666
citation_correctness:   0.6666666666666666
latency_ms:             2997.0
```

Token comparison versus Gate 8.4:

```text
input tokens:   4456   delta +306
output tokens:   263   delta  -26
total tokens:   4719   delta +280
latency_ms:     2997.0 delta +37.666666666666515
```

The semantic-noise case still emitted both the correct S2 transitive-lock-review claim and the ancillary S1 clean-environment claim. The exact measured weakness therefore persisted.

Decision:

```text
H8.5-01 = REJECT
semantic_groundedness_target_not_met
citation_correctness_target_not_met
```

The negative result is preserved rather than tuned away. No second H8.5-01 execution or post-result prompt edit is authorized. A materially different intervention requires a new versioned hypothesis.

### Gate 8.5 merge checkpoint

Final PR #118 evidence/docs head:

```text
791a96811157b04a692608a4a4a2f540c626a389
```

Python CI #343 / run `34077652670` passed all six repository slice jobs.

Protected squash merge:

```text
PR #118
expected_head_sha: 791a96811157b04a692608a4a4a2f540c626a389
main merge SHA:    ff7aedaf6c5ef987efee0f7e6bb9e169eeb2f538
issue #117:        CLOSED / COMPLETED
```

No separate post-merge workflow run was emitted for the merge commit; the protected merge used the exact CI-green head recorded above.

## Credential-precedence lesson retained from Gate 8.4

Stale AWS credential environment variables can take precedence over an intended SSO profile. The clean path is to ensure stale `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_SECURITY_TOKEN`, and `AWS_CREDENTIAL_EXPIRATION` values do not shadow `AWS_PROFILE=opslens-bootstrap`.

This was an environment/credential-chain issue, not a model, prompt, retrieval, or authority-contract failure.

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for the future Phase 14 Case 3 integration with `brunovicco/governed-llm-gateway`. It is not part of Phase 8 and must not be merged merely because Gate 8.5 completed.

The integration must be re-evaluated against the then-current OpsLens architecture and roadmap.

## Next authorized step

```text
Phase 8 Gate 8.6 — Phase 8 closeout
```

Gate 8.6 must reconcile architecture, evaluation evidence, cost-accounting boundaries, IAM posture, observability gaps, README/docs consistency, and Phase 9 entry criteria. It must preserve the rejected H8.5-01 result rather than reopening prompt tuning inside closeout.
