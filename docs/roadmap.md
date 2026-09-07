# OpsLens — Incremental Roadmap

_Last updated: 2026-09-07_

OpsLens advances in small, demonstrable, observable, reversible gates.

Default engineering loop:

```text
concept
 -> architecture decision
 -> IAM / trust boundary when applicable
 -> implementation
 -> success test
 -> failure test
 -> observability
 -> cost
 -> documentation / ADR
 -> logical merge
```

## Current roadmap status

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | AWS Foundation | ✅ Complete |
| 1 | EPSS Vertical Slice | ✅ Complete |
| 2 | Threat Intelligence Data Lake | ✅ Complete |
| 3 | Vulnerability Correlation Engine | ✅ Complete |
| 4 | Repository Intelligence | ✅ Complete |
| 5 | Risk Prioritization Engine | ✅ Complete |
| 6 | Semantic Query Layer | ✅ Complete |
| 7 | Knowledge Retrieval with Bedrock | ✅ Complete |
| 8 | Hybrid Retrieval | ✅ Complete |
| 9 | Public Analyze Your Repository | ✅ Complete |
| 10 | Observability & Operational Excellence | ✅ Complete |
| 11 | Single-Agent Baseline | ▶️ Next |
| 12 | Multi-Agent Architecture | ⏳ Planned |
| 13 | MCP | ⏳ Planned |
| 14 | Amazon Bedrock AgentCore | ⏳ Planned |
| 15 | A2A | ⏳ Planned |
| 16 | Runtime Exposure with Amazon Inspector | ⏳ Planned |
| 17 | Security Hardening | ⏳ Planned |
| 18 | Evaluation, Cost & Portfolio Readiness | ⏳ Planned |

## Permanent engineering boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

## Completed foundation — Phases 0–6

### Phase 0 — AWS Foundation

Real `dev`, Terraform remote state, IAM Identity Center human access, GitHub Actions OIDC deployment identity, cost controls, CloudWatch, X-Ray, and intentional failure-path validation.

### Phase 1 — EPSS Vertical Slice

FIRST EPSS ingestion through EventBridge Scheduler, Lambda, S3 Bronze/Silver, Glue, and Athena.

### Phase 2 — Threat Intelligence Data Lake

NVD/CVE, CISA KEV, FIRST EPSS current/historical, and GitHub Security Advisory source-local deterministic evidence with provenance and explicit time coordinates.

### Phase 3 — Vulnerability Correlation Engine

Deterministic PyPI applicability with canonical package identity, PEP 440 vulnerable-range evaluation, GHSA/CVE/NVD reconciliation, and content-addressed evidence.

### Phase 4 — Repository Intelligence

Read-only public GitHub repository analysis over immutable snapshots and inert `uv.lock` evidence. Third-party repository code is never executed.

### Phase 5 — Risk Prioritization Engine

Deterministic Risk Policy v1 with explicit factor contributions, priority tiers, completeness semantics, and content-addressed results.

### Phase 6 — Semantic Query Layer

```text
natural-language factual question
 -> bounded Bedrock planner
 -> structured proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured evidence
```

The planner never receives unrestricted SQL authority.

## Phase 7 — Knowledge Retrieval with Bedrock — COMPLETE

Phase 7 introduced a separately measurable explanatory/remediation path without replacing structured authority.

Frozen infrastructure:

```text
knowledge base:          BTVJ2PBR2A
data source:             IEL1LBE026
embedding model:         amazon.titan-embed-text-v2:0
vector store:            Amazon S3 Vectors
canonical chunks:        9
```

Frozen retrieval baseline:

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Preserved distinction:

```text
retrieval success != citation attribution success != semantic groundedness
non-empty retrieval != sufficient evidence != authority to answer
```

## Phase 8 — Hybrid Retrieval — COMPLETE

Contracts:

```text
hybrid-routing:v1
hybrid-evidence:v1
hybrid-synthesis:v1
hybrid-evaluation-golden:v1
```

Route authority:

```text
vulnerability_facts / risk_priority -> STRUCTURED
remediation_guidance                -> SEMANTIC
structured + remediation           -> HYBRID
runtime_exposure                    -> UNSUPPORTED
```

First real hybrid baseline:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

`H8.5-01` was executed once and rejected because semantic groundedness and citation correctness did not improve. Runtime default remains `hybrid-synthesis-prompt:v1`.

## Phase 9 — Public Analyze Your Repository — COMPLETE

Merged sequence:

```text
Gate 9.1 — Public Request Admission                         COMPLETE / MERGED
Gate 9.2 — Immutable Repository Evidence Orchestration     COMPLETE / MERGED
Gate 9.3 — Bounded Semantic Planning + Admission Handoff   COMPLETE / MERGED
Gate 9.4 — Phase 9 Closeout                                COMPLETE / MERGED
```

Frozen contracts:

```text
public-analysis-request:v1
public-repository-evidence:v1
public-semantic-planning:v1
public-analysis-handoff:v1
```

Governed boundary:

```text
untrusted public JSON
 -> strict bounded request admission
 -> source-confirmed public repository identity
 -> immutable commit/tree snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic parsing/normalization
 -> PublicRepositoryEvidenceExecution
 -> metadata-only semantic planning proposal
 -> deterministic public-v1 scope admission
 -> existing Phase 8 hybrid route authority
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

Phase 9 closes at:

```text
application boundary validated != public runtime deployed
```

## Phase 10 — Observability & Operational Excellence — COMPLETE

Phase 10 made the governed application path diagnosable without weakening deterministic authority, provenance, content minimization, cardinality discipline, or least privilege.

Frozen rules:

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
telemetry delivery accounting != permission to invent evidence identities
provider serialization != execution authority
EMF document created != CloudWatch ingestion proven
```

Completed sequence:

```text
Gate 10.1 — Content-Minimized Operational Telemetry Contract   COMPLETE / MERGED
Gate 10.2 — Governed Orchestration Instrumentation             COMPLETE / MERGED
Gate 10.3 — CloudWatch EMF Telemetry Adapter Boundary          COMPLETE / MERGED
Gate 10.4 — Phase 10 Closeout                                  COMPLETE / MERGED
```

### Gate 10.1 — provider-neutral operational evidence

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

Metrics:

```text
OperationalStageCount
OperationalStageLatency
```

with dimensions:

```text
ContractVersion
Operation
Stage
Outcome
```

Validation:

```text
PR #135 final head:           7742ae003fc8e1ad1d1a6a4f71542875b6d6462c
CI:                           34135197989 / PASS
pytest:                       14 passed
merge SHA:                    665b86f6e527a0096d7c3db522f4bd2c95b177aa
```

### Gate 10.2 — governed instrumentation

Provider-neutral ports:

```text
MonotonicClock
OperationalEventSink
```

Successful execution emits exactly five ordered success events. Failed/rejected stages are terminal. Event construction is mandatory; external sink delivery is best effort. Undelivered accounting accepts only already-admitted event identities.

Validation:

```text
PR #138 final head:           24b2affdf464e2548d94273e41007bb3256b561e
Python CI:                    34141496326 / PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
Public Analysis pytest:       70 passed
merge SHA:                    346b223d9566a5d04d84e279f30793ad52a35b67
```

### Gate 10.3 — bounded CloudWatch EMF representation

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
 -> canonical EMF JSON
 -> content-addressed CloudWatchEmfDocument
 -> injected EpochMillisecondsClock
 -> injected EmfLineWriter
 -> STOP
```

High-cardinality correlation IDs remain metadata-only and never become metric dimensions.

Validation:

```text
PR #141 final head:           632e778d36ada833505342708379603a1080d390
Operational Observability CI: 34143908297 / run #9 / PASS
Ruff:                         PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
pytest:                       26 passed
merge SHA:                    0c5bf6bab39a3980c063fcb44f657c412111fefa
```

Gate 10.3 made zero CloudWatch API calls, created zero AWS/IAM resources, and did not prove telemetry ingestion.

### Gate 10.4 — Phase 10 closeout

ADR 0035 closes Phase 10 at the proven boundary.

Closeout validation:

```text
issue #143:                 CLOSED / COMPLETED
PR #144 final head:         2fa375f04948792816b72d67c2d1ce9c1043026e
PR #144 merge SHA:          6669638c8a72e250c6ebb3329ebb2c49e6a97898
application/runtime code:   unchanged
new AWS resources/IAM:      0
new provider/runtime calls: 0
```

Gate 10.4 was documentation-only; Gate 10.3 remains the latest executable quality evidence.

Phase 10 proves:

```text
provider-neutral operational event contract
bounded deterministic stage instrumentation
content-minimized correlation/provenance identities
fixed low-cardinality metric projection
best-effort sink semantics after mandatory in-process evidence
bounded content-free failure taxonomy
cloudwatch-emf:v1 deterministic serialization
separate monotonic-duration and epoch-millisecond clock semantics
zero adapter retries
content-addressed operational/EMF evidence
```

Phase 10 does not prove:

```text
public HTTP runtime
CloudWatch ingestion
runtime principal / runtime IAM
public traffic volume
production distributed traces
production p95/p99/error rates
production cost/request
production dashboards/alarms
production SLO compliance
```

## Phase 11 — Single-Agent Baseline — NEXT

Phase 11 must build **one bounded agent** over already-governed capabilities before multi-agent complexity.

Entry boundary:

```text
agent reasoning may select/use already-authorized capabilities
agent reasoning does not acquire deterministic truth or execution authority
```

The first Phase 11 gate should freeze the single-agent contract before choosing a managed runtime.

Required topics:

```text
explicit allowlisted tool/capability surface
deterministic authority preservation
bounded execution budget
bounded retries / no hidden fallback
failure and abstention semantics
evidence/provenance handoff
Phase 10 operational evidence reuse
offline deterministic evaluation fixture
baseline before optimization or multi-agent expansion
```

Do not introduce arbitrary shell/network/tool authority merely because an agent framework supports it.

## Phase 12 — Multi-Agent Architecture — PLANNED

Introduce specialization only where measured evidence improves the Phase 11 single-agent baseline.

## Phase 13 — MCP — PLANNED

Expose bounded internal tools through explicit MCP contracts after deterministic authorities are stable.

## Phase 14 — Amazon Bedrock AgentCore — PLANNED

Evaluate managed runtime capabilities against measured OpsLens needs rather than adopting them for certification coverage alone.

## Phase 15 — A2A — PLANNED

Add agent-to-agent interoperability only after stable agent boundaries exist.

## Phase 16 — Runtime Exposure with Amazon Inspector — PLANNED

Add independent runtime evidence without conflating repository risk with runtime exposure.

## Phase 17 — Security Hardening — PLANNED

Perform cross-cutting IAM, data protection, abuse, threat-model, dependency, and operational hardening.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 remains deferred consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and must be re-evaluated against the then-current architecture before any integration merge.
