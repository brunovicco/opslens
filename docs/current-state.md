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
  Gate 8.5 Measured optimization decision                      NEXT
```

Latest merged executable checkpoint:

```text
Phase 8 Gate 8.4 / PR #115
bce7d4ea596c37e55f14f2e02df58b8d40ed8c2d
```

Gate 8.4 tracking issue #114 is closed as completed.

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

## Retrieval baseline — Gate 7.5

Frozen `knowledge-retrieval-golden:v1`:

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Key preserved distinction:

```text
retrieval success != citation attribution success != semantic groundedness
non-empty retrieval != sufficient evidence != authority to answer
```

## Groundedness baseline — Gate 7.7

Frozen `knowledge-grounding-golden:v1` aggregate metrics:

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

The isolation case remains the important measured weakness: retrieval returned the expected isolation evidence, while the model cited adjacent post-change evidence. That is an attribution/groundedness weakness rather than retrieval unavailability.

## Phase 8 Gate 8.1 — deterministic route authority

Contract:

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
vulnerability_facts and/or risk_priority -> STRUCTURED
remediation_guidance                      -> SEMANTIC
structured + remediation                 -> HYBRID
runtime_exposure, alone or mixed         -> UNSUPPORTED
```

Supported routes require `ALL_REQUIRED` evidence. Runtime exposure is valid-but-unavailable rather than silently mapped to repository risk.

## Phase 8 Gate 8.2 — deterministic typed evidence

Contract:

```text
hybrid-evidence:v1
```

Structured and semantic evidence remain separate typed collections. Successful envelopes require exact need-level completeness and reject extra/unrequested evidence. Similarity score and rank are provenance/measurement metadata only; they are not truth or authority.

## Phase 8 Gate 8.3 — frozen evaluation contract

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

Frozen metric dimensions:

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

The semantic-noise case freezes the critical distinction that rank-one/admitted evidence can be non-supporting while a lower-ranked admitted chunk is the actual support target.

## Phase 8 Gate 8.4 — first bounded hybrid synthesis

Contract:

```text
hybrid-synthesis:v1
```

Route-aware execution:

```text
STRUCTURED
 -> deterministic F1/F2/... structured facts
 -> 0 model calls

SEMANTIC
 -> admitted S1/S2/... evidence
 -> <=1 bounded Bedrock Converse call

HYBRID
 -> deterministic F projections + admitted S projections
 -> <=1 bounded Bedrock Converse call

UNSUPPORTED
 -> abstain
 -> 0 model calls

incomplete evidence
 -> reject_before_synthesis
 -> 0 model calls
```

The model does not author canonical structured facts. Every admitted explanatory claim requires at least one admitted semantic citation ID. Unknown IDs, malformed/extra output, provider failure, non-`end_turn`, or other contract violations fail closed.

### First complete real Bedrock baseline

Input branch head:

```text
7d06bdb87830f32bb1fc848c9580f8575e52895c
```

Operator-observed execution:

```text
complete:                            true
planned_case_count:                  6
synthesis_invocation_attempt_count:  3
admitted_model_execution_count:      3
model:                               us.anthropic.claude-haiku-4-5-20251001-v1:0
region:                              us-east-1
all stop reasons:                    end_turn
all SDK retry attempts:              0
```

Immutable evidence:

```text
labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json
```

Measured metrics:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

The semantic-noise case produced the measured quality weakness: the model cited the expected rank-two support chunk and also introduced a separate claim citing the admitted rank-one clean-environment neighbor. Output admission accepted both allowlisted IDs, while groundedness and citation correctness correctly degraded to `2/3`.

This preserves the intended distinction:

```text
admission != semantic support
retrieval rank != groundedness
allowlisted citation != correct citation target
```

Gate 8.4 intentionally records this baseline without tuning it.

### Credential-precedence incident discovered during Gate 8.4

Two incomplete pre-baseline attempts were traced to stale AWS credential environment variables taking precedence over the requested SSO profile. Botocore resolved `credential_method=env` and raised `credentials_refreshed_still_expired` before a Bedrock response existed.

A clean subshell proved the intended chain:

```text
credential_method=sso
credential_resolution=ok
sts_signed_request=ok
local_converse_output_config=supported
```

No model, prompt, fixture, retrieval, evidence-authority, or output-policy tuning was required to obtain the complete baseline.

## CI / merge checkpoint

Final PR #115 head:

```text
b37865c59cd32dd7a50a7b44de0dcc86a54da1b1
```

Python CI #336 / run `34064224132` passed all six repository slice jobs.

Hybrid retrieval quality gate:

```text
uv lock --check     PASS
Ruff                PASS
Pyright strict      PASS — 0 errors, 0 warnings
pytest              PASS — 66 passed
```

Protected squash merge:

```text
PR #115
expected_head_sha: b37865c59cd32dd7a50a7b44de0dcc86a54da1b1
main merge SHA:    bce7d4ea596c37e55f14f2e02df58b8d40ed8c2d
issue #114:        CLOSED / COMPLETED
```

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for the future Phase 14 Case 3 integration with `brunovicco/governed-llm-gateway`. It is not part of Phase 8 and must not be merged merely because Gate 8.4 completed.

The integration should be re-evaluated only against the then-current OpsLens architecture and roadmap.

## Next authorized step

```text
Phase 8 Gate 8.5 — Measured optimization decision
```

Gate 8.5 must start from the frozen Gate 8.4 real baseline. It may decide that no optimization is justified. If an experiment is proposed, it must state the target metric, preserve authority boundaries, avoid composite scoring, and compare against the immutable Gate 8.4 baseline rather than silently replacing it.
