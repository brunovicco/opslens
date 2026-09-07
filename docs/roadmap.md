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
| 9 | Public Analyze Your Repository | ✅ Complete after Gate 9.4 merge |
| 10 | Observability & Operational Excellence | ▶️ Next |
| 11 | Single-Agent Baseline | ⏳ Planned |
| 12 | Multi-Agent Architecture | ⏳ Planned |
| 13 | MCP | ⏳ Planned |
| 14 | Amazon Bedrock AgentCore | ⏳ Planned |
| 15 | A2A | ⏳ Planned |
| 16 | Runtime Exposure with Amazon Inspector | ⏳ Planned |
| 17 | Security Hardening | ⏳ Planned |
| 18 | Evaluation, Cost & Portfolio Readiness | ⏳ Planned |

## Completed foundation — Phases 0–6

### Phase 0 — AWS Foundation

Real `dev`, Terraform remote state, IAM Identity Center human access, GitHub Actions OIDC deployment identity, cost controls, CloudWatch, X-Ray, and intentional failure-path validation.

### Phase 1 — EPSS Vertical Slice

FIRST EPSS ingestion through EventBridge Scheduler, Lambda, S3 Bronze/Silver, Glue, and Athena.

### Phase 2 — Threat Intelligence Data Lake

NVD/CVE, CISA KEV, FIRST EPSS current/historical, and GitHub Security Advisory source-local deterministic evidence with provenance and explicit time coordinates.

### Phase 3 — Vulnerability Correlation Engine

Deterministic PyPI applicability with canonical package identity, PEP 440 vulnerable-range evaluation, GHSA/CVE/NVD reconciliation, and content-addressed evidence.

> **No LLM decides vulnerability applicability.**

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

> **No unrestricted text-to-SQL.**

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

Frozen groundedness baseline preserves the distinction:

```text
retrieval success != citation attribution success != semantic groundedness
```

## Phase 8 — Hybrid Retrieval — COMPLETE

Phase 8 freezes hybrid **evidence routing and composition**, not automatically keyword + vector search.

### Gate 8.1 — deterministic route authority

```text
hybrid-routing:v1
vulnerability_facts / risk_priority -> STRUCTURED
remediation_guidance                -> SEMANTIC
structured + remediation           -> HYBRID
runtime_exposure                    -> UNSUPPORTED
```

### Gate 8.2 — deterministic hybrid evidence

```text
hybrid-evidence:v1
```

Structured and semantic evidence remain separate authority classes and supported routes require `ALL_REQUIRED` evidence.

### Gate 8.3 — frozen evaluation

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

No composite score exists.

### Gate 8.4 — bounded synthesis

```text
hybrid-synthesis:v1
STRUCTURED  -> 0 model calls
SEMANTIC    -> <=1
HYBRID      -> <=1
UNSUPPORTED -> 0
incomplete  -> 0 / reject before synthesis
```

First real baseline:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

### Gate 8.5 — measured optimization

H8.5-01 was tested once and rejected because the target quality metrics did not improve. The runtime default remains `hybrid-synthesis-prompt:v1`.

### Gate 8.6 — closeout

Phase 8 authority/failure taxonomy, IAM/cost/observability boundaries, negative experiment evidence, and Phase 9 entry criteria are frozen.

## Phase 9 — Public Analyze Your Repository — COMPLETE after Gate 9.4 merge

Goal: establish a governed public-analysis application boundary without allowing public input or model proposals to become execution authority.

Mandatory sequence:

```text
Gate 9.1 — Public Request Admission                         COMPLETE / MERGED
Gate 9.2 — Immutable Repository Evidence Orchestration     COMPLETE / MERGED
Gate 9.3 — Bounded Semantic Planning + Admission Handoff   COMPLETE / MERGED
Gate 9.4 — Phase 9 Closeout                                CLOSEOUT IN REVIEW
```

### Gate 9.1 — Public Request Admission

Contract:

```text
public-analysis-request:v1
```

Untrusted JSON is bounded and reduced to validated GitHub owner/name/ref coordinates. The raw URL never becomes arbitrary fetch authority.

### Gate 9.2 — Immutable Repository Evidence Orchestration

Contract:

```text
public-repository-evidence:v1
```

```text
PublicAnalysisRequest
 -> source-confirmed public repository identity
 -> immutable commit/tree snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic parser
 -> deterministic Phase 3 PyPI normalization
 -> PublicRepositoryEvidenceExecution
```

Third-party repository code is never executed.

### Gate 9.3 — Bounded Semantic Planning + Admission Handoff

Contracts:

```text
public-semantic-planning:v1
public-analysis-handoff:v1
```

The fixed operation is:

```text
analyze_public_repository
```

Deterministic public policy requires exactly:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

The planner receives only bounded metadata and cannot redefine product scope. Successful admission must agree with the Phase 8 router:

```text
HYBRID
ALL_REQUIRED
STRUCTURED + SEMANTIC
```

Exact-head validation:

```text
PR #129 head:                    34cea42a0ce37cbfa06b33d57f081403edba2552
Python CI #358 / run 34082791753: PASS
Public Analysis Pyright strict:  0 errors / 0 warnings / 0 informations
Public Analysis pytest:          57 passed
merge SHA:                       6f53537c227cade688091187eac1074645e11bf0
```

### Gate 9.4 — Phase 9 Closeout

ADR 0031 freezes the closeout boundary:

```text
application boundary validated != public runtime deployed
```

Gate 9.4 introduces no public endpoint, runtime compute, AWS resource, IAM permission, runtime provider call, or downstream public evidence execution.

At closeout:

```text
public HTTP compute:      NOT DEPLOYED
public endpoint:          NOT DEPLOYED
public runtime principal: DOES NOT EXIST
new Gate 9.4 AWS:         NONE
new Gate 9.4 IAM:         NONE
```

This deliberately preserves least privilege rather than creating a speculative broad runtime role.

Public-launch prerequisites remain explicit: concrete compute/endpoint, runtime IAM, timeout/concurrency/rate/abuse/quota controls, kill switch, cost attribution, request telemetry, rollback/incident procedures, and workload-derived SLOs/alerts.

## Phase 10 — Observability & Operational Excellence — NEXT

Phase 10 starts from the frozen Phase 9 application contracts.

Primary goal:

```text
make a concrete runtime diagnosable
without weakening deterministic authority,
provenance, content minimization, or least privilege
```

Entry criteria:

```text
1. Phase 9 contracts remain versioned boundaries
2. public input never gains arbitrary fetch/SQL/tool/model/execution authority
3. repository code is never executed
4. Repository Risk != Runtime Exposure
5. Phase 8 remains hybrid route/evidence authority
6. semantic planning remains proposal-only and content-minimized
7. failed admission prevents downstream execution
8. IAM exists only for a concrete runtime identity
9. production SLO/alert claims require deployed workload evidence
10. observability cannot weaken privacy/provenance boundaries
11. runtime/provider/retrieval changes require measured versioned hypotheses
12. PR #89 remains separately deferred until reevaluated
```

If useful telemetry requires a small deployed runtime slice, that slice must explicitly define compute, IAM, request/time/concurrency/abuse/cost limits, rollback, and measurement before production claims are made.

## Future phases

### Phase 11 — Single-Agent Baseline

Build one bounded agent over existing deterministic tools before multi-agent complexity.

### Phase 12 — Multi-Agent Architecture

Introduce specialization only where measured evidence improves the single-agent baseline.

### Phase 13 — MCP

Expose bounded internal tools through explicit MCP contracts after deterministic authorities are stable.

### Phase 14 — Amazon Bedrock AgentCore

Evaluate managed runtime capabilities against measured OpsLens needs.

### Phase 15 — A2A

Add agent-to-agent interoperability only after stable agent boundaries exist.

### Phase 16 — Runtime Exposure with Amazon Inspector

Add independent runtime evidence without conflating repository risk with runtime exposure.

### Phase 17 — Security Hardening

Perform cross-cutting IAM, data protection, abuse, threat-model, dependency, and operational hardening.

### Phase 18 — Evaluation, Cost & Portfolio Readiness

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 is the deferred consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and must be re-evaluated against the then-current architecture before any integration merge.
