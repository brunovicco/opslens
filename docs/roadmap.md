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
| 10 | Observability & Operational Excellence | ▶️ In progress — Gate 10.4 next |
| 11 | Single-Agent Baseline | ⏳ Planned |
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

Phase 8 freezes hybrid **evidence routing and composition**, not automatically keyword + vector search.

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

Supported routes require `ALL_REQUIRED` evidence. Structured and semantic evidence remain separate authority classes.

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

Phase 9 established a governed public-analysis **application boundary**. It did not deploy a public HTTP runtime.

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

Governed path:

```text
untrusted public JSON
 -> strict bounded request admission
 -> validated GitHub owner/name/ref coordinates
 -> source-confirmed public repository identity
 -> immutable commit/tree snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic parser + PyPI normalization
 -> PublicRepositoryEvidenceExecution
 -> bounded metadata-only semantic planning proposal
 -> deterministic exact public-v1 scope admission
 -> existing Phase 8 hybrid route authority
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

Phase 9 closeout decision from ADR 0031:

```text
application boundary validated != public runtime deployed
```

At closeout:

```text
public HTTP compute:      NOT DEPLOYED
public endpoint:          NOT DEPLOYED
public runtime principal: DOES NOT EXIST
```

Public-launch prerequisites remain explicit: concrete compute/endpoint, runtime IAM, timeout/concurrency/rate/abuse/quota controls, kill switch, cost attribution, production telemetry, rollback/incident procedures, and workload-derived SLOs/alerts.

## Phase 10 — Observability & Operational Excellence — IN PROGRESS

Phase 10 makes the governed application path diagnosable without weakening deterministic authority, provenance, content minimization, or least privilege.

Frozen Phase 10 rules:

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
telemetry delivery accounting != permission to invent evidence identities
provider serialization != execution authority
EMF document created != CloudWatch ingestion proven
```

Current sequence:

```text
Gate 10.1 — Content-Minimized Operational Telemetry Contract   COMPLETE / MERGED
Gate 10.2 — Governed Orchestration Instrumentation             COMPLETE / MERGED
Gate 10.3 — CloudWatch EMF Telemetry Adapter Boundary          COMPLETE / MERGED
Gate 10.4 — Phase 10 Closeout                                  NEXT
```

### Gate 10.1 — Content-Minimized Operational Telemetry Contract — COMPLETE

Frozen contract:

```text
operational-telemetry:v1
operation: analyze_public_repository
```

Bounded stages:

```text
public_request_admission
repository_evidence
semantic_planning
hybrid_route_admission
public_handoff
```

Low-cardinality metrics:

```text
OperationalStageCount
OperationalStageLatency
```

with only these dimensions:

```text
ContractVersion
Operation
Stage
Outcome
```

Validation:

```text
PR #135 final head:           7742ae003fc8e1ad1d1a6a4f71542875b6d6462c
exact-head CI:                34135197989 / PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
pytest:                       14 passed
merge SHA:                    665b86f6e527a0096d7c3db522f4bd2c95b177aa
issue #134:                   CLOSED / COMPLETED
```

### Gate 10.2 — Governed Orchestration Instrumentation — COMPLETE

Gate 10.2 wired the frozen telemetry contract into the already-governed public-analysis path through injected provider-neutral boundaries:

```text
MonotonicClock
OperationalEventSink
```

Successful execution emits exactly five events in stage order. Failed/rejected stages are terminal. Sink delivery is best effort only after mandatory in-process event construction, and undelivered-event accounting accepts only already-admitted event identities.

Validation:

```text
PR #138 final head:           24b2affdf464e2548d94273e41007bb3256b561e
Python CI:                    34141496326 / PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
Public Analysis pytest:       70 passed
merge SHA:                    346b223d9566a5d04d84e279f30793ad52a35b67
issue #137:                   CLOSED / COMPLETED
```

### Gate 10.3 — CloudWatch EMF Telemetry Adapter Boundary — COMPLETE

Gate 10.3 introduced an offline AWS-native representation without deploying runtime authority.

Frozen adapter contract:

```text
cloudwatch-emf:v1
namespace: OpsLens/Operational
storage resolution: 60 seconds
maximum document: 16 KiB
```

Boundary:

```text
OperationalEvent
 -> existing project_operational_metrics(...)
 -> deterministic canonical EMF JSON
 -> content-addressed CloudWatchEmfDocument
 -> injected EpochMillisecondsClock
 -> injected EmfLineWriter
 -> STOP
```

Exact dimensions remain:

```text
ContractVersion
Operation
Stage
Outcome
```

High-cardinality correlation IDs remain metadata only and never become metric dimensions.

Adapter failure taxonomy:

```text
clock_contract
document_contract
writer_delivery
```

There are zero adapter retries and at most one writer attempt per `emit(...)`.

Validation:

```text
PR #141 final head:           632e778d36ada833505342708379603a1080d390
Operational Observability CI: 34143908297 / run #9 / PASS
Ruff:                         PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
pytest:                       26 passed
merge SHA:                    0c5bf6bab39a3980c063fcb44f657c412111fefa
issue #140:                   CLOSED / COMPLETED
```

Gate 10.3 made zero CloudWatch API calls, created zero AWS/IAM resources, and did not prove telemetry ingestion.

### Gate 10.4 — Phase 10 Closeout — NEXT

Gate 10.4 is a closeout gate, not a deployment gate.

It must consolidate and freeze:

```text
operational-telemetry:v1 provider-neutral contract
five-stage deterministic instrumentation
content-minimized provenance identities
low-cardinality metric projection
best-effort sink semantics
cloudwatch-emf:v1 provider representation
separate monotonic vs wall-clock semantics
zero adapter retries
content-addressed operational/EMF evidence
failure taxonomy
privacy/cardinality boundaries
IAM and cost non-claims
```

It must explicitly preserve:

```text
application boundary validated != public runtime deployed
EMF document created != CloudWatch ingestion proven
production SLO/cost/alert claims require deployed workload evidence
IAM exists only for a concrete runtime identity
```

Gate 10.4 should produce the Phase 10 closeout ADR/lab and synchronize the public documentation. It must not create Lambda/API Gateway/ECS, runtime IAM, CloudWatch delivery, dashboards, alarms, or SLOs merely to complete the phase.

After the closeout is merged and postmerge state is synchronized, **Phase 11 — Single-Agent Baseline** becomes the next authorized project phase.

## Phase 11 — Single-Agent Baseline — PLANNED

Build one bounded agent over existing deterministic tools before multi-agent complexity.

Entry rule:

```text
agent reasoning may select/use already-governed capabilities
agent reasoning does not acquire deterministic truth or execution authority
```

Phase 11 must define an explicit tool/authority surface and a measurable baseline before Phase 12 adds specialization.

## Phase 12 — Multi-Agent Architecture — PLANNED

Introduce specialization only where measured evidence improves the single-agent baseline.

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

OpsLens PR #89 remains the deferred consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and must be re-evaluated against the then-current architecture before any integration merge.
