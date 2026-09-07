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
| 11 | Single-Agent Baseline | 🚧 In progress — Gates 11.1–11.2 complete |
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

Phase 11 adds:

```text
agent action proposal != capability authorization != execution result
AuthorizedAgentAction != capability invocation
capability invocation != execution result
agent reasoning may select/use already-authorized capabilities
agent reasoning does not acquire deterministic truth or execution authority
```

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
 -> bounded model planner
 -> structured proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured evidence
```

The planner never receives unrestricted SQL authority.

## Phase 7 — Knowledge Retrieval with Bedrock — COMPLETE

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

## Phase 8 — Hybrid Retrieval — COMPLETE

Frozen contracts:

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

First complete baseline:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

`H8.5-01` was tested once and rejected. Runtime default remains `hybrid-synthesis-prompt:v1`.

## Phase 9 — Public Analyze Your Repository — COMPLETE

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
 -> deterministic request admission
 -> immutable public GitHub evidence
 -> deterministic repository analysis
 -> metadata-only semantic planning proposal
 -> deterministic public-v1 scope admission
 -> existing Phase 8 hybrid authority
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

Phase 9 closes at:

```text
application boundary validated != public runtime deployed
```

## Phase 10 — Observability & Operational Excellence — COMPLETE

Frozen contracts:

```text
operational-telemetry:v1
cloudwatch-emf:v1
```

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

Phase 10 proves deterministic operational evidence and an AWS-native EMF representation boundary. It does not prove public runtime, CloudWatch ingestion, production latency/error distributions, runtime IAM, production cost/request, dashboards/alarms, or SLO compliance.

## Phase 11 — Single-Agent Baseline — IN PROGRESS

Phase 11 introduces agentic reasoning only after deterministic capability authority and typed execution/result binding are frozen.

Current sequence:

```text
Gate 11.1 — Capability Authorization Contract                COMPLETE / MERGED
Gate 11.2 — Typed Capability Bindings + Offline Executor      COMPLETE / MERGED
Gate 11.3 — Frozen Single-Agent Evaluation Fixture            NEXT
Gate 11.4 — First Bounded Model Reasoning Baseline            BLOCKED
Gate 11.5 — Measured Optimization Decision                    BLOCKED
Gate 11.6 — Phase 11 Closeout                                 BLOCKED
```

### Gate 11.1 — capability authorization — COMPLETE

Frozen contract:

```text
single-agent-authority:v1
```

Initial capability classes:

```text
structured_security_query
knowledge_guidance
hybrid_security_answer
public_repository_analysis
```

Authority boundary:

```text
bounded SingleAgentTask
 -> code-owned AgentCapability allowlist
 -> untrusted AgentActionProposal
 -> deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention
 -> STOP
```

Limits:

```text
max task UTF-8 bytes:       2048
max allowed capabilities:   4
proposals per task:         1
authorization steps:        1
capability executions:      0
adaptive retries:           0
```

Exact validation:

```text
issue #146:              CLOSED / COMPLETED
PR #147 final head:      12f63c54add74498478f2e48bc3835485fc3f5f5
Single-Agent CI:         34149074387 / run #5 / PASS
Ruff:                    PASS
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest:                  16 passed in 0.09s
PR #147 merge SHA:       641fc20d29cf1148d63b460948a08362158be113
```

Gate 11.1 performed zero real model, capability, AWS, or runtime calls and added no AWS/IAM resources.

### Gate 11.2 — typed capability bindings + offline executor — COMPLETE

Frozen contract:

```text
single-agent-execution:v1
```

Boundary:

```text
AuthorizedAgentAction
 -> exact typed capability invocation
 -> deterministic action/capability match
 -> explicit capability-specific executor port
 -> one bounded execution attempt
 -> typed downstream result admission
 -> content-addressed AgentCapabilityExecution
 -> STOP
```

Exact bindings:

```text
structured_security_query
 -> SemanticQuery
 -> StructuredSecurityQueryResultBinding(AthenaQueryResult)

knowledge_guidance
 -> SynthesisRequest
 -> SynthesisResult

hybrid_security_answer
 -> HybridSynthesisRequest
 -> HybridSynthesisResult

public_repository_analysis
 -> PublicAnalysisRequest
 -> PublicAnalysisAdmissionHandoff
```

The invocation surface has no arbitrary `tool_name`, kwargs, URL, SQL, command, provider/model selector, credentials, retry policy, or fallback policy.

Execution limits:

```text
max executions per call: 1
execution retries:        0
adaptive fallbacks:       0
```

Result admission preserves exact downstream identity:

```text
structured -> invocation_sha256 binding
knowledge  -> SynthesisRequest.request_sha256
hybrid     -> HybridSynthesisRequest.request_sha256
public     -> PublicAnalysisRequest request_id + request_sha256
```

Failure categories:

```text
executor_failure
result_contract
```

Exact validation:

```text
issue #149:              CLOSED / COMPLETED
PR #150 final head:      1f2dae3ece3b4a2dc9280575fd5a1a3c315751f4
Single-Agent CI:         34155862646 / run #11 / PASS
job:                     101847434766
Ruff:                    PASS
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest:                  31 passed in 0.44s
PR #150 merge SHA:       0fb70ace5bd544c6ef5f17f1030bdbcbeb8063b7
```

Gate 11.2 performed zero real reasoning-model/AWS calls and added no AWS/IAM/runtime resources. It also left `operational-telemetry:v1` unchanged.

### Gate 11.3 — frozen single-agent evaluation fixture — NEXT

Goal:

```text
frozen deterministic agent cases
 -> proposal expectation
 -> authorization expectation
 -> execution expectation
 -> independent metric dimensions
 -> baseline-ready fixture
 -> STOP
```

Required design constraints:

```text
separate proposal selection from authorization correctness
separate authorization from execution/result correctness
include ACT, ABSTAIN, denied, malformed/tampered, and result-mismatch scenarios
freeze exact capability and outcome expectations
track execution-attempt budget explicitly
no composite metric that hides authority failures
future model-quality/latency/cost dimensions remain UNMEASURED until Gate 11.4
no real model/provider/AWS calls
no AgentCore/MCP/A2A
no runtime-exposure authority
```

Gate 11.3 must create the evaluation contract before Gate 11.4 is allowed to introduce a real reasoning model.

Observability remains explicit: do not mutate `operational-telemetry:v1` to represent agent steps. Agent-specific operational evidence requires a separately versioned contract if it becomes necessary.

## Phase 12 — Multi-Agent Architecture — PLANNED

Introduce specialization only where measured evidence improves the Phase 11 single-agent baseline.

## Phase 13 — MCP — PLANNED

Expose bounded internal capabilities through explicit MCP contracts after deterministic authorities are stable.

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

OpsLens PR #89 remains deferred consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and must be re-evaluated against the current architecture before any integration merge.
