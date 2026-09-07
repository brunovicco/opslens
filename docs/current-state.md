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
Phase 9    Public Analyze Your Repository                      COMPLETE
  Gate 9.1 Public repository request admission                 COMPLETE / MERGED
  Gate 9.2 Immutable repository evidence orchestration         COMPLETE / MERGED
  Gate 9.3 Bounded semantic planning + admission handoff       COMPLETE / MERGED
  Gate 9.4 Phase 9 closeout                                    COMPLETE / MERGED
Phase 10   Observability & Operational Excellence              IN PROGRESS
  Gate 10.1 Content-minimized operational telemetry contract   COMPLETE / MERGED
  Gate 10.2 Governed orchestration instrumentation             COMPLETE / MERGED
  Gate 10.3 CloudWatch EMF telemetry adapter boundary          NEXT
```

Latest merged executable/project checkpoint:

```text
Phase 10 Gate 10.2 / PR #138
346b223d9566a5d04d84e279f30793ad52a35b67
```

Tracking:

```text
Gate 10.2 issue #137:             CLOSED / COMPLETED
Gate 10.2 final PR head:          24b2affdf464e2548d94273e41007bb3256b561e
Gate 10.2 exact-head Python CI:   run 34141496326 / PASS
Public Analysis Ruff:             PASS
Public Analysis Pyright strict:   0 errors / 0 warnings / 0 informations
Public Analysis pytest:           70 passed
Gate 10.2 merge SHA:              346b223d9566a5d04d84e279f30793ad52a35b67
```

## Permanent architecture boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

Deterministic authorities own package/version semantics, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS/Risk Policy facts, SemanticQuery validation and SQL compilation, retrieval/evidence admission, hybrid route/completeness, structured fact projection, canonical evidence/citation identity, output admission, evaluation metrics, execution limits, public request admission, immutable repository evidence binding, public-v1 product scope, semantic-plan admission, public handoff identity, and operational telemetry admission/projection semantics.

LLMs may classify, plan, propose, synthesize, explain, and select already-admitted citation IDs. They do not own structured truth, public product scope, repository truth, runtime exposure, SQL authority, route authority, evidence completeness, canonical provenance, provider/model selection, execution authority, or telemetry authority.

Phase 10 adds the explicit distinctions:

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
telemetry delivery accounting != permission to invent evidence identities
```

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

Governed operational instrumentation
 -> operational-telemetry:v1
 -> request admission event
 -> repository evidence event
 -> semantic planning event
 -> deterministic hybrid route event
 -> public handoff event
 -> injected best-effort OperationalEventSink
 -> bounded undelivered-event identity accounting
```

The application `STOP` remains material. Gate 10.2 instrumented the governed application boundary; it did not deploy a public HTTP runtime or downstream public analysis execution pipeline.

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

Successful deterministic admission must agree with Phase 8 route authority:

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

### Gate 9.4 — closeout

ADR 0031 freezes:

```text
application boundary validated != public runtime deployed
```

```text
PR #132:                         MERGED
merge SHA:                       f27c278db1039d31bd8410a2e51d14b77f6c1f0b
issue #131:                      CLOSED / COMPLETED
```

## Phase 10 Gate 10.1 — operational telemetry contract

Frozen contract:

```text
operational-telemetry:v1
operation: analyze_public_repository
```

Stages:

```text
public_request_admission
repository_evidence
semantic_planning
hybrid_route_admission
public_handoff
```

Outcomes:

```text
succeeded
rejected
failed
```

Only content-addressed Phase 9 identity references are available:

```text
public_request_id
source_execution_id
handoff_id
```

There is no arbitrary telemetry attribute bag and no event field for raw repository URL/owner/name, dependency names/versions, `uv.lock` bytes, prompt/retrieved/model text, SQL, credentials/secrets, or provider/model selection.

Metric projection is fixed to:

```text
OperationalStageCount      Count
OperationalStageLatency    Milliseconds
```

with only these dimensions:

```text
ContractVersion
Operation
Stage
Outcome
```

High-cardinality request/source/handoff identities never become metric dimensions.

Validation:

```text
PR #135 final head:               7742ae003fc8e1ad1d1a6a4f71542875b6d6462c
Operational Observability CI:     run 34135197989 / PASS
uv lock --check:                  PASS
Ruff:                             PASS
Pyright strict:                   0 errors / 0 warnings / 0 informations
pytest:                           14 passed
merge SHA:                        665b86f6e527a0096d7c3db522f4bd2c95b177aa
issue #134:                       CLOSED / COMPLETED
```

## Phase 10 Gate 10.2 — governed orchestration instrumentation

Gate 10.2 wires `operational-telemetry:v1` into the existing Phase 9 path without moving any application authority into telemetry.

Provider-neutral ports:

```text
MonotonicClock
OperationalEventSink
```

Successful execution emits exactly five events in order:

```text
public_request_admission
repository_evidence
semantic_planning
hybrid_route_admission
public_handoff
```

Failure semantics are deterministic and terminal. Source transport vs evidence rejection, planner invocation vs planner-output rejection, route rejection, handoff rejection, and unexpected internal failures remain separately diagnosable without copying arbitrary provider/exception text into events.

Sink delivery remains best effort:

```text
valid OperationalEvent construction failure -> fail closed
external sink failure                       -> never changes business/route authority
```

Delivery accounting accepts only IDs of already-admitted events and rejects forged or duplicate undelivered identities.

Validation:

```text
PR #138 final head:               24b2affdf464e2548d94273e41007bb3256b561e
Python CI run:                    34141496326 / PASS
uv lock --check:                  PASS
Ruff:                             PASS
Pyright strict:                   0 errors / 0 warnings / 0 informations
Public Analysis pytest:           70 passed
merge SHA:                        346b223d9566a5d04d84e279f30793ad52a35b67
issue #137:                       CLOSED / COMPLETED
```

Gate 10.2 created no public runtime, AWS resource, IAM role/policy, Athena call, Bedrock/model call, CloudWatch/OpenTelemetry exporter call, dashboard, alarm, or production SLO claim.

## Cost and observability boundary

OpsLens does not invent a public-request price, production latency distribution, SLO, or alert compliance before a deployed workload exists.

Current Phase 10 evidence proves the telemetry contract, deterministic instrumentation, failure taxonomy, content-minimization/cardinality boundaries, and CI quality. It does not yet prove production telemetry delivery.

Still not claimed:

```text
public request volume
public distributed traces
production p95/p99
production error/throttle rates
production cost/request
production SLO/alert compliance
```

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

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and must be re-evaluated against the then-current architecture before any merge.

## Next authorized step

```text
Phase 10 Gate 10.3 — CloudWatch EMF Telemetry Adapter Boundary
```

Gate 10.3 may adapt the frozen provider-neutral `OperationalEvent`/metric projection to Amazon CloudWatch Embedded Metric Format through an injected writer boundary, but it must remain offline/fake-writer first. It must preserve the existing low-cardinality dimensions, keep content-addressed IDs out of metric dimensions, perform zero implicit retries, and make no claim of CloudWatch delivery until a concrete runtime transports the serialized records. A real AWS call, runtime IAM policy, dashboard, alarm, or SLO requires separate explicit evidence.
