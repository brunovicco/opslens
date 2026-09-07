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
| 9 | Public Analyze Your Repository | ▶️ In progress — Gate 9.4 next |
| 10 | Observability & Operational Excellence | ⏳ Planned |
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

Deterministic PyPI v1 applicability with canonical package identity, PEP 440 vulnerable-range evaluation, GHSA/CVE/NVD reconciliation, and content-addressed evidence.

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

Permanent rule:

> **No unrestricted text-to-SQL.**

## Phase 7 — Knowledge Retrieval with Bedrock — COMPLETE

Goal: create a separately measurable explanatory/remediation RAG path without replacing the structured Phase 6 authority boundary.

Permanent rules:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **Retrieval output is evidence, not deterministic truth.**

> **A valid citation ID is not proof that a claim is supported.**

Final path:

```text
knowledge/remediation question
 -> bounded RetrievalRequest
 -> Bedrock Knowledge Base Retrieve
 -> checked-corpus admission
 -> bounded deterministic context assembly
 -> deterministic pre-model authority decision
 -> bounded Bedrock synthesis
 -> deterministic citation catalog
 -> grounded claim/citation proposal
 -> explicit support judgments
 -> deterministic groundedness metrics
```

### Gate 7.1 — Corpus + retrieval contract — COMPLETE

Provider-independent retrieval contracts with bounded query/top-k/provenance semantics.

### Gate 7.2 — Reproducible canonical corpus — COMPLETE

```text
6 immutable official source pins
9 canonical chunks
manifest sha256:
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

### Gate 7.3 — Knowledge Base + vector infrastructure — COMPLETE

```text
KB id:                BTVJ2PBR2A
data source id:       IEL1LBE026
vector store:         Amazon S3 Vectors
embedding model:      amazon.titan-embed-text-v2:0
dimensions:           1024
vector type:          FLOAT32
distance:             cosine
chunking:              NONE
vectors materialized: 9
```

### Gate 7.4 — Real bounded Retrieve adapter — COMPLETE

Direct `Retrieve`, not `RetrieveAndGenerate`, keeps retrieval independently testable and measurable.

### Gate 7.5 — Retrieval evaluation — COMPLETE

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

### Gate 7.6 — Context assembly + bounded synthesis — COMPLETE

Deterministic whole-chunk context assembly, pre-model authority, one bounded non-streaming Claude Haiku 4.5 Converse call maximum, and strict provider/output admission.

### Gate 7.7 — Citations + groundedness — COMPLETE

Frozen result:

```text
decision accuracy:          1.0
citation target precision:  0.2857142857142857
citation target recall:     0.5
claim supportedness:        0.8461538461538461
unsupported claim rate:     0.15384615384615385
citation correctness:       0.8461538461538461
abstention precision:       1.0
abstention recall:          1.0
```

The isolation case preserved a useful attribution/groundedness failure while the TLS-cipher case correctly abstained despite non-empty retrieval.

### Gate 7.8 — Phase 7 closeout — COMPLETE

Frozen failure taxonomy, runtime IAM strategy, cost/observability boundaries, documentation consistency, Phase 8 entry criteria, and deferred optimization backlog.

## Phase 8 — Hybrid Retrieval — COMPLETE

Goal: combine structured evidence and semantic evidence without weakening their different authority semantics.

Hybrid Retrieval in OpsLens means **hybrid evidence routing**, not automatically “hybrid keyword + vector search.”

Permanent Phase 8 rule:

```text
structured vulnerability/risk facts
 -> deterministic structured authority

explanatory/remediation guidance
 -> bounded semantic evidence

combined response
 -> explicit evidence-class provenance
 -> no authority laundering
```

### Gate 8.1 — Offline routing and authority contract — COMPLETE

Contract:

```text
hybrid-routing:v1
```

```text
vulnerability_facts / risk_priority -> STRUCTURED
remediation_guidance                -> SEMANTIC
structured + remediation           -> HYBRID
runtime_exposure, alone or mixed   -> UNSUPPORTED
```

Intent/evidence-need classification is not execution authority. Supported routes require `ALL_REQUIRED` evidence.

### Gate 8.2 — Deterministic hybrid evidence envelope — COMPLETE

Contract:

```text
hybrid-evidence:v1
```

Structured and semantic evidence remain separate typed collections. Need-level completeness, provenance, rank integrity, duplicate detection, and content-addressed identity fail closed.

### Gate 8.3 — Frozen hybrid evaluation fixture — COMPLETE

Dataset:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Six cases:

```text
structured_only_factual
semantic_only_remediation
true_hybrid
unsupported_out_of_authority
partial_structured_evidence
semantic_retrieval_noise
```

Independent metrics:

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

### Gate 8.4 — First bounded hybrid synthesis — COMPLETE

Contract:

```text
hybrid-synthesis:v1
```

Route-aware model budget:

```text
STRUCTURED  -> 0 calls
SEMANTIC    -> <=1 call
HYBRID      -> <=1 call
UNSUPPORTED -> 0 calls
incomplete  -> reject before synthesis / 0 calls
```

The model cannot author canonical structured facts or provenance. Explanatory claims require admitted semantic citation IDs.

First complete real Bedrock baseline:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

The semantic-noise failure is intentionally preserved.

### Gate 8.5 — Measured optimization decision — COMPLETE

H8.5-01 tested one predeclared prompt-only candidate exactly once.

```text
candidate: hybrid-synthesis-prompt:h8.5-01-v1
quality target:
  semantic_groundedness == 1.0
  citation_correctness  == 1.0
```

Measured result:

```text
semantic_groundedness: 0.6666666666666666
citation_correctness:  0.6666666666666666
input-token delta:     +306
output-token delta:     -26
total-token delta:     +280
```

Decision:

```text
H8.5-01 = REJECT
```

The runtime default remains `hybrid-synthesis-prompt:v1`. No second H8.5-01 run or post-result prompt mutation is authorized.

### Gate 8.6 — Phase 8 closeout — COMPLETE

Gate 8.6 freezes:

```text
Phase 8 authority/failure taxonomy
immutable Gate 8.4 baseline
measured Gate 8.5 rejection
future runtime IAM boundary
cost-accounting boundary
observability boundary
README / docs / architecture consistency
Phase 9 public-demo entry criteria
deferred optimization backlog
```

Gate 8.6 makes no AWS, IAM, provider, prompt, retrieval, or model changes.

## Phase 9 — Public Analyze Your Repository — IN PROGRESS

Goal: expose the already-governed evidence system as a bounded public demo without allowing the public boundary or model output to become execution authority.

Mandatory gate sequence:

```text
Gate 9.1 — Public Request Admission                         COMPLETE
Gate 9.2 — Immutable Repository Evidence Orchestration     COMPLETE
Gate 9.3 — Bounded Semantic Planning + Admission Handoff   COMPLETE
Gate 9.4 — Phase 9 Closeout                                NEXT
```

The order is mandatory. Gate 9.4 begins only from the merged Gate 9.3 checkpoint.

### Gate 9.1 — Public Request Admission — COMPLETE

Contract:

```text
public-analysis-request:v1
```

The public operation is fixed to one GitHub repository. Untrusted JSON is bounded and reduced to validated owner/name/ref coordinates before any external capability is available. The original URL is never acquisition authority.

### Gate 9.2 — Immutable Repository Evidence Orchestration — COMPLETE

Contract:

```text
public-repository-evidence:v1
```

Merged execution path:

```text
PublicAnalysisRequest
 -> validated owner/name/ref coordinates only
 -> source-confirmed public repository metadata
 -> exact commit/tree snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic uv.lock parsing
 -> deterministic Phase 3 PyPI normalization
 -> content-addressed PublicRepositoryEvidenceExecution
```

The source-confirmed repository identity owns canonical coordinates after the initial lookup. Null refs use source-declared default-branch evidence. Explicit refs are frozen to immutable commit/tree identity before file acquisition. Cross-request, cross-snapshot, cross-file, parser, or normalization drift fails closed.

Validation checkpoint:

```text
PR #126 head:                     0fdc6c435c0f2891b6730f61bd73ad7f32ca8213
Python CI #349 / run 34080376506: PASS
Public Analysis Pyright strict:   0 errors / 0 warnings / 0 informations
Public Analysis pytest:           41 passed
merge SHA:                        b152a21bf9d0807ac40083c609ea434f32ccb671
issue #125:                       CLOSED / COMPLETED
```

No deployed public HTTP compute, AWS resource, IAM permission, Athena call, Bedrock call, or model call was introduced by Gate 9.2.

### Gate 9.3 — Bounded Semantic Planning + Admission Handoff — COMPLETE

Contracts:

```text
public-semantic-planning:v1
public-analysis-handoff:v1
```

The public operation remains fixed to `analyze_public_repository`; the planner does not own product semantics. Deterministic v1 policy requires exactly:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

The planner receives only a bounded metadata projection of verified Gate 9.2 evidence. Raw repository URL, lockfile bytes, dependency names/versions, arbitrary repository text/instructions, SQL, provider/model/tool selection, and executable repository content are excluded from the planner control plane.

The planner proposal is untrusted until deterministic admission. The existing Phase 8 route authority must resolve the admitted need set to:

```text
HYBRID
ALL_REQUIRED
STRUCTURED + SEMANTIC
```

Any malformed, under-scoped, out-of-authority, replayed, duplicated, oversized, source-rebound, or route-inconsistent proposal fails closed. Application orchestration performs no adaptive retry.

Validation checkpoint:

```text
PR #129 head:                     34cea42a0ce37cbfa06b33d57f081403edba2552
Python CI #358 / run 34082791753: PASS
Public Analysis Pyright strict:   0 errors / 0 warnings / 0 informations
Public Analysis pytest:           57 passed
merge SHA:                        6f53537c227cade688091187eac1074645e11bf0
issue #128:                       CLOSED / COMPLETED
```

Gate 9.3 used injected fake repository/planner ports only. It added no deployed public HTTP compute, AWS resource, IAM permission, real runtime GitHub call, Athena call, Bedrock call, model call, retrieval, synthesis, vulnerability enrichment, or risk execution.

ADR: `docs/adr/0030-public-semantic-planning-authority.md`.
Lab: `labs/phase-9-gate-9-3-bounded-semantic-planning.md`.

### Gate 9.4 — Phase 9 Closeout — NEXT

Gate 9.4 will close Phase 9 by freezing the public-boundary architecture that actually exists, not by inventing a deployment that has not yet been built.

Required closeout dimensions:

```text
Gate 9.1 request-admission contract
Gate 9.2 immutable repository-evidence contract
Gate 9.3 proposal/admission handoff contract
Phase 9 authority + failure taxonomy
runtime/deployment/IAM decision
request/planner/execution budgets
cost-accounting boundary
observability boundary
security/abuse controls still required before launch
documentation consistency
exact Phase 10 entry criteria
```

Gate 9.4 must explicitly preserve the difference between the validated **application boundary** and a future **public runtime**. There is still no deployed public HTTP compute principal, endpoint, public runtime IAM policy, rate limiter, abuse-protection layer, production concurrency control, or production SLO evidence.

A closeout decision may defer public deployment/runtime work to a later measured gate, but it must state that explicitly. It must not claim production readiness from fake-port CI evidence.

Phase 9 does not require agents, AgentCore, MCP, A2A, reranking, new vector infrastructure, or runtime exposure by default.

## Future phases

### Phase 10 — Observability & Operational Excellence

Make the deployed public system diagnosable through stage latency, errors, throttling, Athena bytes, model tokens/latency, retrieval latency, route decisions, groundedness signals, traces, and cost evidence.

### Phase 11 — Single-Agent Baseline

Build one bounded agent over existing deterministic tools before introducing multi-agent complexity.

### Phase 12 — Multi-Agent Architecture

Introduce specialization only where it demonstrably improves the single-agent baseline.

### Phase 13 — MCP

Expose bounded internal tools through explicit MCP contracts only after deterministic authorities are stable.

### Phase 14 — Amazon Bedrock AgentCore

Evaluate managed runtime capabilities against measured OpsLens needs; do not adopt for certification coverage alone.

### Phase 15 — A2A

Introduce agent-to-agent interoperability only after stable single/multi-agent boundaries exist.

### Phase 16 — Runtime Exposure with Amazon Inspector

Add independent deployed-runtime evidence so repository risk can be compared with actual runtime exposure without conflation.

### Phase 17 — Security Hardening

Perform cross-cutting IAM, data protection, abuse, threat-model, guardrail, dependency, and operational hardening.

### Phase 18 — Evaluation, Cost & Portfolio Readiness

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence across the completed system.

## Deferred cross-project integration

The long-lived OpsLens PR #89 is the deferred consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**.

It is not the same thing as OpsLens Phase 14. It remains open/draft and must be re-evaluated against the then-current OpsLens architecture before any integration merge.
