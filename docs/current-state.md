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
Phase 8    Hybrid Retrieval                                    COMPLETE
Phase 9    Public Analyze Your Repository                      COMPLETE after Gate 9.4 merge
  Gate 9.1 Public repository request admission                 COMPLETE / MERGED
  Gate 9.2 Immutable repository evidence orchestration         COMPLETE / MERGED
  Gate 9.3 Bounded semantic planning + admission handoff       COMPLETE / MERGED
  Gate 9.4 Phase 9 closeout                                    CLOSEOUT IN REVIEW
Phase 10   Observability & Operational Excellence              NEXT after Gate 9.4 merge
```

Latest merged executable checkpoint:

```text
Phase 9 Gate 9.3 / PR #129
6f53537c227cade688091187eac1074645e11bf0
```

Latest merged documentation checkpoint before Gate 9.4:

```text
Gate 9.3 postmerge state sync / PR #130
6e0c595d5d2437dabd94365e1eeb88800a5bcab4
```

## Permanent architecture boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

Deterministic authorities own package/version semantics, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS/Risk Policy facts, SemanticQuery validation and SQL compilation, retrieval/evidence admission, hybrid route/completeness, structured fact projection, canonical evidence/citation identity, output admission, evaluation metrics, execution limits, public request admission, immutable repository evidence binding, public-v1 product scope, semantic-plan admission, and public handoff identity.

LLMs may classify, plan, propose, synthesize, explain, and select already-admitted citation IDs. They do not own structured truth, public product scope, repository truth, runtime exposure, SQL authority, route authority, evidence completeness, canonical provenance, provider/model selection, or execution authority.

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

EvidenceNeed[]
 -> deterministic hybrid route authority
 -> authority-separated evidence composition
 -> ALL_REQUIRED completeness
 -> HybridEvidenceEnvelope
 -> deterministic F* / S* projections
 -> bounded route-aware synthesis
 -> deterministic output admission
 -> independent quality/runtime metrics

Untrusted public repository JSON
 -> strict bounded request admission
 -> validated GitHub owner/name/ref coordinates
 -> source-confirmed public repository identity
 -> immutable commit/tree snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic uv.lock parsing
 -> deterministic Phase 3 PyPI normalization
 -> PublicRepositoryEvidenceExecution
 -> bounded metadata-only semantic planning proposal
 -> deterministic exact public-v1 scope admission
 -> existing Phase 8 hybrid route authority
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

The last `STOP` is material: Phase 9 validates the governed application boundary. It does not yet provide a deployed public HTTP runtime or downstream public analysis execution pipeline.

## Frozen Phase 7 / 8 quality

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

Gate 8.4 first complete hybrid baseline:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

Gate 8.5 H8.5-01 did not improve semantic groundedness/citation correctness and was rejected. Runtime default remains `hybrid-synthesis-prompt:v1`.

Preserved distinctions:

```text
retrieval success != citation attribution success != semantic groundedness
non-empty retrieval != sufficient evidence != authority to answer
admission != semantic support
```

## Phase 9 contracts

```text
public-analysis-request:v1
public-repository-evidence:v1
public-semantic-planning:v1
public-analysis-handoff:v1
```

### Gate 9.1 — request admission

Untrusted public JSON is bounded and reduced to validated GitHub owner/name/ref coordinates. The raw user URL never becomes fetch authority.

```text
public request admitted
 != repository proven public
 != repository snapshot resolved
 != repository analyzed
```

Validation:

```text
PR #123 head:                    26f0d2b5275284d891ee99a7f8276d41cc4f0753
Python CI #346 / run 34079446683: PASS
Public Analysis pytest:          33 passed
merge SHA:                       5540d7b508c71aa65d826786618690b7ddc9d433
issue #122:                      CLOSED / COMPLETED
```

### Gate 9.2 — immutable repository evidence

Source-confirmed public repository metadata resolves an immutable commit/tree; exact-commit inert `uv.lock` evidence is parsed and normalized deterministically. Repository code is never executed.

Validation:

```text
PR #126 head:                    0fdc6c435c0f2891b6730f61bd73ad7f32ca8213
Python CI #349 / run 34080376506: PASS
Public Analysis pytest:          41 passed
merge SHA:                       b152a21bf9d0807ac40083c609ea434f32ccb671
issue #125:                      CLOSED / COMPLETED
```

### Gate 9.3 — bounded semantic planning + admission handoff

The fixed public operation is `analyze_public_repository`. Deterministic policy requires exactly:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

Planner bounds:

```text
planning request:       <= 2048 UTF-8 bytes
planner response:       <= 1024 bytes
planner invocations:    <= 1 per orchestration
adaptive app retries:   0
```

The planner receives metadata-only verified identities/accounting, not repository content. Successful deterministic admission must agree with Phase 8 route authority:

```text
HYBRID
ALL_REQUIRED
STRUCTURED + SEMANTIC
```

Validation:

```text
PR #129 head:                    34cea42a0ce37cbfa06b33d57f081403edba2552
Python CI #358 / run 34082791753: PASS
Public Analysis Ruff:            PASS
Public Analysis Pyright strict:  0 errors / 0 warnings / 0 informations
Public Analysis pytest:          57 passed
merge SHA:                       6f53537c227cade688091187eac1074645e11bf0
issue #128:                      CLOSED / COMPLETED
```

Gate 9.3 used injected fake repository/planner ports and made zero real provider/model calls.

## Phase 9 closeout decision

ADR 0031 freezes the core closeout distinction:

```text
application boundary validated != public runtime deployed
```

At Gate 9.4 closeout:

```text
public HTTP compute:      NOT DEPLOYED
public endpoint:          NOT DEPLOYED
public runtime principal: DOES NOT EXIST
new Gate 9.4 AWS:         NONE
new Gate 9.4 IAM:         NONE
```

This is intentional least privilege. No runtime role is created before a concrete compute principal and responsibilities exist.

## Phase 9 fail-closed taxonomy

Failure classes include request bytes/UTF-8/JSON/field grammar, repository URL admission, metadata/visibility/ref resolution, immutable commit/tree/file evidence, parser/normalization provenance, planning request binding, planner invocation/output contract, unknown/duplicate/out-of-authority evidence needs, under-scoped plans, `runtime_exposure`, replay, source-execution rebinding, Phase 8 route/completeness/class mismatch, and handoff identity mismatch.

Any failed stage creates no later authority object.

## Cost and observability boundary

Phase 9 does not invent a public request price. Existing cost evidence remains stage-specific and only becomes valid when that stage actually runs. Gate 9.3 made zero real provider/model calls.

Current evidence supports IDs, hashes, provenance, admission decisions, bounded failure categories, exact-head CI, and real provider token/latency metadata only for previously executed provider stages.

Phase 9 does not claim:

```text
public request volume
public distributed traces
production p95/p99
production error/throttle rates
production cost/request
production SLO/alert compliance
```

Those require a deployed runtime and measured workload.

## Public-launch prerequisites still required

```text
concrete HTTP compute + endpoint
runtime identity + least-privilege IAM
timeout budget
concurrency limits
rate limiting
abuse protection
quota enforcement
cache policy only if justified
kill switch / disable path
cost guardrails + attribution
request-level telemetry
production error/latency distributions
workload-derived SLOs + alerts
rollback / incident procedures
```

Phase 9 completion does not waive these requirements.

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and is not part of Phase 9. It must be re-evaluated against the then-current architecture before any merge.

## Next authorized step

After the Gate 9.4 closeout PR is merged:

```text
Phase 10 — Observability & Operational Excellence
```

Phase 10 must start from the frozen Phase 9 contracts and preserve deterministic authority, provenance, content minimization, least privilege, and fail-closed admission. If real observability requires a small deployed runtime slice, that runtime must be introduced explicitly with concrete compute/IAM, request/abuse/cost limits, rollback, and measured operational evidence. Production SLOs and alerts must come from deployed workload evidence, not laboratory CI.
