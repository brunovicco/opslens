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
| 10 | Observability & Operational Excellence | ▶️ In progress |
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

H8.5-01 was executed once and rejected because semantic groundedness and citation correctness did not improve. The runtime default remains `hybrid-synthesis-prompt:v1`.

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

Public v1 remains fixed to `analyze_public_repository`. Deterministic code requires exactly:

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

Phase 9 closeout decision from ADR 0031:

```text
application boundary validated != public runtime deployed
```

At closeout:

```text
public HTTP compute:      NOT DEPLOYED
public endpoint:          NOT DEPLOYED
public runtime principal: DOES NOT EXIST
new Gate 9.4 AWS:         NONE
new Gate 9.4 IAM:         NONE
```

Closeout merge:

```text
PR #132
f27c278db1039d31bd8410a2e51d14b77f6c1f0b
issue #131: CLOSED / COMPLETED
```

Public-launch prerequisites remain explicit: concrete compute/endpoint, runtime IAM, timeout/concurrency/rate/abuse/quota controls, kill switch, cost attribution, production telemetry, rollback/incident procedures, and workload-derived SLOs/alerts.

## Phase 10 — Observability & Operational Excellence — IN PROGRESS

Phase 10 starts from the frozen Phase 9 contracts and makes operational evidence explicit without weakening application authority.

Primary goal:

```text
make governed execution diagnosable
without weakening deterministic authority,
provenance, content minimization, or least privilege
```

Frozen Phase 10 rule:

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
```

Mandatory sequence begins as follows:

```text
Gate 10.1 — Content-Minimized Operational Telemetry Contract   COMPLETE / MERGED
Gate 10.2 — Governed Orchestration Instrumentation             NEXT
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

The event contract has no arbitrary attribute bag. It can carry only bounded operational semantics and already-authorized Phase 9 content-addressed identity references. It cannot carry raw repository/source/model/SQL/credential content.

Low-cardinality metrics are fixed to:

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
exact-head CI run:            34135197989 / PASS
Ruff:                         PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
pytest:                       14 passed
merge SHA:                    665b86f6e527a0096d7c3db522f4bd2c95b177aa
issue #134:                   CLOSED / COMPLETED
```

Gate 10.1 introduced no public runtime, new AWS resources, new IAM permissions, Bedrock/model calls, Athena calls, telemetry exporter calls, production dashboards, alarms, or SLO claims.

### Gate 10.2 — Governed Orchestration Instrumentation — NEXT

Goal: wire `operational-telemetry:v1` into the already-governed public-analysis orchestration through injected provider-neutral boundaries before choosing or deploying a telemetry backend.

Expected boundary:

```text
existing public-analysis stage
 -> deterministic stage outcome/failure classification
 -> OperationalEvent
 -> injected OperationalEventSink
 -> optional provider adapter later
```

Gate 10.2 must freeze, test, and document:

```text
exact stage emission order
success/rejection/failure mapping
no downstream stage telemetry after fail-closed application stop
content-minimized identities only
clock/duration accounting through an injected boundary
telemetry sink failure semantics
no telemetry-based business/route authorization
no high-cardinality metric dimensions
```

The sink-failure decision must be explicit. A telemetry failure must never convert an application rejection/failure into success or authorize downstream work. Whether telemetry delivery itself is required for one future runtime is a separate operational policy decision and must not be hidden inside the application authority contract.

Gate 10.2 remains offline/provider-neutral unless real deployment is separately justified. No public HTTP runtime, runtime IAM, production SLO, or production telemetry delivery may be claimed from unit/CI evidence.

Phase 10 entry criteria remain frozen:

```text
1. Phase 9 contracts remain versioned boundaries
2. public input never gains arbitrary fetch/SQL/tool/model/execution authority
3. third-party repository code is never executed
4. Repository Risk != Runtime Exposure
5. Phase 8 remains hybrid route/evidence authority
6. semantic planning remains proposal-only and content-minimized
7. failed admission prevents downstream execution
8. IAM exists only for a concrete runtime identity
9. production SLO/alert claims require deployed workload evidence
10. observability cannot weaken privacy/provenance/content-minimization boundaries
11. runtime/provider/retrieval changes require separately versioned hypotheses
12. PR #89 remains deferred until separately re-evaluated
```

## Future phases

### Phase 11 — Single-Agent Baseline

Build one bounded agent over existing deterministic tools before multi-agent complexity.

### Phase 12 — Multi-Agent Architecture

Introduce specialization only where measured evidence improves the single-agent baseline.

### Phase 13 — MCP

Expose bounded internal tools through explicit MCP contracts after deterministic authorities are stable.

### Phase 14 — Amazon Bedrock AgentCore

Evaluate managed runtime capabilities against measured OpsLens needs rather than adopting them for certification coverage alone.

### Phase 15 — A2A

Add agent-to-agent interoperability only after stable agent boundaries exist.

### Phase 16 — Runtime Exposure with Amazon Inspector

Add independent runtime evidence without conflating repository risk with runtime exposure.

### Phase 17 — Security Hardening

Perform cross-cutting IAM, data protection, abuse, threat-model, dependency, and operational hardening.

### Phase 18 — Evaluation, Cost & Portfolio Readiness

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 remains the deferred consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and must be re-evaluated against the then-current architecture before any integration merge.
