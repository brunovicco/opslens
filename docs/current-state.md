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
  Gate 10.3 CloudWatch EMF telemetry adapter boundary          COMPLETE / MERGED
  Gate 10.4 Phase 10 closeout                                  NEXT
```

Latest merged executable/project checkpoint:

```text
Phase 10 Gate 10.3 / PR #141
0c5bf6bab39a3980c063fcb44f657c412111fefa
```

Gate 10.3 validation:

```text
issue #140:                         CLOSED / COMPLETED
final PR head:                      632e778d36ada833505342708379603a1080d390
Operational Observability CI:       34143908297 / run #9 / PASS
uv lock --check:                    PASS
Ruff:                               PASS
Pyright strict:                     0 errors / 0 warnings / 0 informations
pytest:                             26 passed
merge SHA:                          0c5bf6bab39a3980c063fcb44f657c412111fefa
```

## Permanent architecture boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

Deterministic authorities own package/version semantics, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS/Risk Policy facts, `SemanticQuery` validation and SQL compilation, retrieval/evidence admission, hybrid route/completeness, structured fact projection, canonical evidence/citation identity, output admission, evaluation metrics, execution limits, public request admission, immutable repository evidence binding, public-v1 product scope, semantic-plan admission, public handoff identity, operational telemetry admission/projection semantics, and provider-specific telemetry document admission.

LLMs may classify, plan, propose, synthesize, explain, and select already-admitted citation IDs. They do not own structured truth, public product scope, repository truth, runtime exposure, SQL authority, route authority, evidence completeness, canonical provenance, provider/model selection, execution authority, or telemetry authority.

Phase 10 freezes these distinctions:

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
telemetry delivery accounting != permission to invent evidence identities
provider serialization != execution authority
EMF document created != CloudWatch ingestion proven
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
 -> exact five-stage event sequence
 -> deterministic failure taxonomy
 -> content-addressed OperationalEvent
 -> fixed low-cardinality metric projection
 -> injected best-effort OperationalEventSink
 -> bounded undelivered-event identity accounting

CloudWatch representation boundary
 -> admitted OperationalEvent
 -> existing project_operational_metrics(...)
 -> deterministic cloudwatch-emf:v1 payload
 -> exact four-dimension metric set
 -> content-addressed CloudWatchEmfDocument
 -> injected EpochMillisecondsClock
 -> injected EmfLineWriter
 -> STOP
```

The application `STOP` remains material. Phase 10 has made the governed application boundary observable and added an offline AWS-native representation boundary; it has not deployed a public HTTP runtime or proven CloudWatch ingestion.

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

Gate 8.5 `H8.5-01` did not improve semantic groundedness/citation correctness and was rejected. Runtime default remains `hybrid-synthesis-prompt:v1`.

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

## Phase 10 Gate 10.3 — CloudWatch EMF telemetry adapter boundary

Gate 10.3 adapts admitted operational evidence into an AWS-native representation without changing provider-neutral telemetry authority.

Frozen contract:

```text
cloudwatch-emf:v1
namespace: OpsLens/Operational
storage resolution: 60 seconds
maximum canonical document: 16 KiB
```

Boundary:

```text
OperationalEvent
 -> project_operational_metrics(...)
 -> canonical CloudWatch EMF JSON
 -> CloudWatchEmfDocument
 -> injected EpochMillisecondsClock
 -> injected EmfLineWriter
 -> STOP
```

Exact metric dimension set remains:

```text
ContractVersion
Operation
Stage
Outcome
```

High-cardinality identities remain log metadata only:

```text
EventId
PublicRequestId
SourceExecutionId
HandoffId
```

They never become metric dimensions.

Adapter failure categories are content-free and bounded:

```text
clock_contract
document_contract
writer_delivery
```

Each `emit(...)` has zero adapter retries and at most one writer attempt. The canonical EMF document is SHA-256 content-addressed. The timestamp clock is intentionally distinct from the Gate 10.2 monotonic duration clock.

Validation:

```text
PR #141 final head:               632e778d36ada833505342708379603a1080d390
Operational Observability CI:     34143908297 / run #9 / PASS
uv lock --check:                  PASS
Ruff:                             PASS
Pyright strict:                   0 errors / 0 warnings / 0 informations
pytest:                           26 passed
merge SHA:                        0c5bf6bab39a3980c063fcb44f657c412111fefa
issue #140:                       CLOSED / COMPLETED
```

The initial PR run `34143614259` preserved one test-only strict-Pyright failure (`RecordingWriter.lines -> list[Unknown]`); it was corrected without changing adapter behavior before the exact-head green run.

Gate 10.3 introduced no AWS resource, IAM policy, public runtime, `logs:PutLogEvents`, `cloudwatch:PutMetricData`, OpenTelemetry call, dashboard, alarm, production SLO, or CloudWatch ingestion claim.

## Cost and observability boundary

OpsLens does not invent a public-request price, CloudWatch cost, production latency distribution, SLO, or alert compliance before a deployed workload exists.

Current Phase 10 evidence proves:

```text
provider-neutral telemetry contract
content-minimized operational events
deterministic stage instrumentation
bounded failure taxonomy
low-cardinality metric projection
provider-specific EMF serialization
content-addressed EMF documents
clock/writer failure boundaries
```

It does **not** prove:

```text
public request volume
CloudWatch ingestion
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

None of these prerequisites is silently satisfied by the Phase 10 offline application/telemetry work.

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and must be re-evaluated against the then-current architecture before any merge.

## Next authorized step

```text
Phase 10 Gate 10.4 — Phase 10 Closeout
```

Gate 10.4 must freeze the completed observability boundary and close Phase 10 without inventing a production runtime. It should consolidate contracts, authority/failure/cardinality/privacy/IAM/cost boundaries, exact merge evidence, and the entry criteria for Phase 11 — Single-Agent Baseline.

The closeout must preserve:

```text
application boundary validated != public runtime deployed
EMF document created != CloudWatch ingestion proven
production SLO/cost/alert claims require deployed workload evidence
IAM exists only for a concrete runtime identity
```

A public runtime, CloudWatch delivery backend, runtime IAM policy, dashboard, alarm, or SLO is not required merely to declare the current Phase 10 observability architecture complete.
