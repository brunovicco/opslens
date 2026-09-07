# OpsLens — Current State

_Last updated: 2026-09-07_

This document is the authoritative implementation checkpoint for OpsLens. Detailed gate history remains in ADRs, labs, immutable evidence artifacts, merged PRs, and Git history.

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
Phase 10   Observability & Operational Excellence              COMPLETE
  Gate 10.1 Content-minimized operational telemetry contract   COMPLETE / MERGED
  Gate 10.2 Governed orchestration instrumentation             COMPLETE / MERGED
  Gate 10.3 CloudWatch EMF telemetry adapter boundary          COMPLETE / MERGED
  Gate 10.4 Phase 10 closeout                                  COMPLETE / MERGED
Phase 11   Single-Agent Baseline                               NEXT
```

Latest merged project checkpoint:

```text
Phase 10 Gate 10.4 / PR #144
6669638c8a72e250c6ebb3329ebb2c49e6a97898
```

Gate 10.4 closeout evidence:

```text
issue #143:                 CLOSED / COMPLETED
PR #144 final head:         2fa375f04948792816b72d67c2d1ce9c1043026e
PR #144 merge SHA:          6669638c8a72e250c6ebb3329ebb2c49e6a97898
application/runtime code:   unchanged
new AWS resources:          0
new IAM permissions:        0
new provider/runtime calls: 0
```

Because Gate 10.4 changed documentation/architecture only, the latest executable validation remains Gate 10.3:

```text
PR #141 final head:           632e778d36ada833505342708379603a1080d390
Operational Observability CI: 34143908297 / run #9 / PASS
uv lock --check:              PASS
Ruff:                         PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
pytest:                       26 passed
merge SHA:                    0c5bf6bab39a3980c063fcb44f657c412111fefa
issue #140:                   CLOSED / COMPLETED
```

## Permanent architecture boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

Deterministic code owns package/version semantics, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS/Risk Policy facts, `SemanticQuery` validation and SQL compilation, retrieval/evidence admission, hybrid route/completeness, canonical evidence/citation identity, output admission, evaluation metrics, execution limits, public request admission, immutable repository evidence binding, public-v1 scope admission, public handoff identity, operational telemetry admission/projection semantics, and provider-specific telemetry document admission.

LLMs may classify, plan, propose, synthesize, explain, and select already-admitted citation IDs. They do not own structured truth, public product scope, repository truth, runtime exposure, SQL authority, route authority, evidence completeness, canonical provenance, provider/model selection, execution authority, or telemetry authority.

Phase 10 permanently adds:

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
telemetry delivery accounting != permission to invent evidence identities
provider serialization != execution authority
EMF document created != CloudWatch ingestion proven
```

## Implemented governed path

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
 -> bounded Retrieve
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

Untrusted public repository JSON
 -> strict bounded request admission
 -> validated GitHub owner/name/ref coordinates
 -> source-confirmed public repository identity
 -> immutable commit/tree snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic parsing + PyPI normalization
 -> PublicRepositoryEvidenceExecution
 -> bounded metadata-only semantic planning proposal
 -> deterministic public-v1 scope admission
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

CloudWatch representation boundary
 -> admitted OperationalEvent
 -> project_operational_metrics(...)
 -> deterministic cloudwatch-emf:v1 payload
 -> content-addressed CloudWatchEmfDocument
 -> injected EpochMillisecondsClock
 -> injected EmfLineWriter
 -> STOP
```

The `STOP` is material. OpsLens has a validated governed application boundary and an offline AWS-native telemetry representation boundary; it does not yet have a deployed public HTTP workload.

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

```text
retrieval success != citation attribution success != semantic groundedness
non-empty retrieval != sufficient evidence != authority to answer
admission != semantic support
```

## Phase 9 governed public-analysis boundary

Frozen contracts:

```text
public-analysis-request:v1
public-repository-evidence:v1
public-semantic-planning:v1
public-analysis-handoff:v1
```

Public v1 is fixed to `analyze_public_repository`. Deterministic code requires exactly:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

Successful admission must agree with Phase 8 authority:

```text
HYBRID
ALL_REQUIRED
STRUCTURED + SEMANTIC
```

Phase 9 remains closed at:

```text
application boundary validated != public runtime deployed
```

## Phase 10 closeout

### Gate 10.1 — operational telemetry contract

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

Metrics:

```text
OperationalStageCount      Count
OperationalStageLatency    Milliseconds
```

Dimensions:

```text
ContractVersion
Operation
Stage
Outcome
```

Validation:

```text
PR #135 final head:           7742ae003fc8e1ad1d1a6a4f71542875b6d6462c
Operational Observability CI: 34135197989 / PASS
pytest:                       14 passed
merge SHA:                    665b86f6e527a0096d7c3db522f4bd2c95b177aa
```

### Gate 10.2 — governed orchestration instrumentation

Provider-neutral ports:

```text
MonotonicClock
OperationalEventSink
```

Successful execution emits exactly five ordered success events. Failed/rejected stages are terminal. In-process event construction is mandatory; external sink delivery is best effort and cannot change business or route authority.

Validation:

```text
PR #138 final head:           24b2affdf464e2548d94273e41007bb3256b561e
Python CI:                    34141496326 / PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
Public Analysis pytest:       70 passed
merge SHA:                    346b223d9566a5d04d84e279f30793ad52a35b67
```

### Gate 10.3 — CloudWatch EMF adapter boundary

```text
cloudwatch-emf:v1
namespace: OpsLens/Operational
storage resolution: 60 seconds
maximum canonical document: 16 KiB
```

High-cardinality correlation identities remain log metadata only and never become metric dimensions.

Adapter failure categories:

```text
clock_contract
document_contract
writer_delivery
```

Adapter retries are exactly zero and writer delivery is attempted at most once per `emit(...)`.

### Gate 10.4 — closeout decision

ADR 0035 closes Phase 10 at the proven boundary. Phase 10 proves:

```text
provider-neutral operational event contract
bounded deterministic stage instrumentation
content-minimized provenance/correlation identities
fixed low-cardinality metric projection
best-effort external sink semantics after mandatory in-process evidence
bounded content-free failure taxonomy
cloudwatch-emf:v1 deterministic serialization
separate monotonic-duration and epoch-millisecond clock semantics
zero adapter retries
content-addressed OperationalEvent / CloudWatchEmfDocument evidence
```

Phase 10 does **not** prove:

```text
public HTTP runtime
CloudWatch ingestion
runtime principal / runtime IAM
public request volume
production distributed traces
production p95/p99
production error/throttle rates
production cost/request
production dashboards/alarms
production SLO compliance
```

## IAM and cost boundary

Phase 10 closes with no public runtime principal and no new runtime telemetry IAM.

Not granted:

```text
logs:PutLogEvents
cloudwatch:PutMetricData
```

Production observability cost remains unmeasured because no public workload or CloudWatch ingestion exists.

```text
unmeasured cost != zero cost
```

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and must be re-evaluated against the then-current architecture before any merge.

## Next authorized step

```text
Phase 11 — Single-Agent Baseline
```

Phase 11 starts with one bounded agent over already-governed capabilities before any multi-agent complexity.

Entry rules:

```text
1. agent reasoning may select/use already-authorized capabilities
2. deterministic truth remains code-owned
3. exact tool/capability surface must be explicit and allowlisted
4. arbitrary tool execution is not allowed
5. execution budgets and failure/abstention semantics must be bounded
6. evaluation baseline must exist before optimization or multi-agent expansion
7. Phase 10 operational evidence boundaries must be reused rather than bypassed
8. Repository Risk != Runtime Exposure remains frozen
9. PR #89 remains deferred until separately re-evaluated
```

Phase 11 should begin with an offline, provider-neutral single-agent contract before selecting managed runtime infrastructure.
