# OpsLens — Current State

_Last updated: 2026-09-07_

This document is the authoritative implementation checkpoint for OpsLens. Detailed history remains in ADRs, gate labs, immutable evidence artifacts, merged PRs, and Git history.

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
Phase 11   Single-Agent Baseline                               IN PROGRESS
  Gate 11.1 Bounded capability authorization contract          COMPLETE / MERGED
  Gate 11.2 Typed capability bindings + offline executor       COMPLETE / MERGED
  Gate 11.3 Frozen single-agent evaluation fixture             NEXT
Phase 12   Multi-Agent Architecture                            PLANNED
Phase 13   MCP                                                 PLANNED
Phase 14   Amazon Bedrock AgentCore                            PLANNED
Phase 15   A2A                                                 PLANNED
Phase 16   Runtime Exposure with Amazon Inspector              PLANNED
Phase 17   Security Hardening                                  PLANNED
Phase 18   Evaluation, Cost & Portfolio Readiness              PLANNED
```

Latest merged project checkpoint:

```text
Phase 11 Gate 11.2 / PR #150
0fb70ace5bd544c6ef5f17f1030bdbcbeb8063b7
```

Gate 11.2 exact validation:

```text
issue #149:              CLOSED / COMPLETED
PR #150 final head:      1f2dae3ece3b4a2dc9280575fd5a1a3c315751f4
Single-Agent CI:         34155862646 / run #11 / PASS
PR merge test commit:    0262b66b97323bda5ecd397c0b292fd961e88f8a
uv lock --check:         PASS
Ruff:                    PASS
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest:                  31 passed in 0.44s
PR #150 merge SHA:       0fb70ace5bd544c6ef5f17f1030bdbcbeb8063b7
```

## Permanent architecture boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

Phase 11 permanently adds:

```text
agent action proposal != capability authorization != execution result
AuthorizedAgentAction != capability invocation
capability invocation != execution result
agent reasoning may select/use already-authorized capabilities
agent reasoning does not acquire deterministic truth or execution authority
```

Deterministic code continues to own package/version semantics, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS/Risk Policy facts, `SemanticQuery` validation and SQL compilation, retrieval/evidence admission, hybrid route/completeness, canonical evidence/citation identity, output admission, evaluation metrics, execution limits, public request admission, immutable repository evidence binding, public-v1 scope admission, public handoff identity, operational telemetry admission/projection semantics, provider-specific telemetry document admission, agent task admission, capability allowlists, capability authorization, typed capability invocation admission, downstream result binding, and agent execution identity.

LLMs may classify, plan, propose, synthesize, explain, select already-admitted citation IDs, and later propose one capability selection. They do not own structured truth, repository truth, runtime exposure, SQL authority, hybrid route authority, evidence completeness, canonical provenance, capability allowlists, capability authorization, executable argument authority, provider/model selection, retry/fallback policy, arbitrary tool execution, or telemetry authority.

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

Untrusted public repository request
 -> deterministic request admission
 -> immutable public GitHub evidence
 -> deterministic repository analysis
 -> proposal-only semantic planning
 -> deterministic public-v1 scope admission
 -> existing Phase 8 hybrid authority
 -> PublicAnalysisAdmissionHandoff
 -> STOP

Operational evidence
 -> operational-telemetry:v1
 -> deterministic five-stage instrumentation
 -> content-addressed OperationalEvent
 -> low-cardinality metric projection
 -> cloudwatch-emf:v1 representation
 -> STOP

Single-agent authority + execution
 -> bounded SingleAgentTask
 -> code-owned AgentCapability allowlist
 -> untrusted AgentActionProposal
 -> deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention
 -> exact typed capability invocation
 -> capability-specific executor port
 -> one-attempt typed result admission
 -> content-addressed AgentCapabilityExecution
 -> STOP
```

The final `STOP` is material. OpsLens now has a validated offline single-agent authorization and execution boundary, but it still has no reasoning-model loop, deployed agent runtime, public agent endpoint, AgentCore runtime, MCP, or A2A execution.

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

Gate 8.5 `H8.5-01` was rejected because it did not improve semantic groundedness/citation correctness. Runtime default remains `hybrid-synthesis-prompt:v1`.

Preserved distinctions:

```text
retrieval success != citation attribution success != semantic groundedness
non-empty retrieval != sufficient evidence != authority to answer
admission != semantic support
```

## Phase 10 observability boundary

Phase 10 remains complete and frozen at:

```text
operational-telemetry:v1
cloudwatch-emf:v1
```

Permanent Phase 10 rules:

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
telemetry delivery accounting != permission to invent evidence identities
provider serialization != execution authority
EMF document created != CloudWatch ingestion proven
```

Phase 10 does not prove a public HTTP runtime, CloudWatch ingestion, runtime IAM, production p95/p99, production cost/request, dashboards/alarms, or production SLO compliance.

## Gate 11.1 — Bounded Single-Agent Capability Authority

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

Limits:

```text
max task UTF-8 bytes:       2048
max allowed capabilities:   4
proposals per task:         1
authorization steps:        1
capability executions:      0
adaptive retries:           0
```

The proposal surface contains only task identity, decision, optional typed capability, and content-addressed proposal identity. It contains no generic tool name, arbitrary args/kwargs, URL, SQL, shell command, provider/model choice, credentials, or retry/fallback policy.

Authorization semantics:

```text
allowlisted ACT
 -> deterministic AuthorizedAgentAction

out-of-allowlist ACT
 -> fail closed

ABSTAIN
 -> deterministic AgentAbstention
 -> no capability authority
```

A valid proposal is not itself execution authority.

Gate 11.1 exact validation remains:

```text
issue #146:              CLOSED / COMPLETED
PR #147 final head:      12f63c54add74498478f2e48bc3835485fc3f5f5
Single-Agent CI:         34149074387 / run #5 / PASS
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest:                  16 passed in 0.09s
PR #147 merge SHA:       641fc20d29cf1148d63b460948a08362158be113
```

## Gate 11.2 — Typed Capability Bindings + Offline Executor

Frozen contract:

```text
single-agent-execution:v1
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

The execution layer accepts only closed typed invocation classes. It has no generic tool registry or arbitrary argument envelope. Each invocation embeds the exact `AuthorizedAgentAction` and fails before execution if the action capability does not match the invocation type.

Execution limits:

```text
max executions per call: 1
execution retries:        0
adaptive fallbacks:       0
```

Result admission is explicit:

```text
structured -> result bound to exact invocation_sha256
knowledge  -> exact SynthesisResult.request_sha256 match
hybrid     -> exact HybridSynthesisResult.request_sha256 match
public     -> exact public request_id + request_sha256 match
```

Successful execution creates content-addressed `AgentCapabilityExecution` evidence over the authorized action, typed invocation, capability, and admitted downstream result hash.

Failure categories remain content-free:

```text
executor_failure
result_contract
```

A downstream failure is attempted once and does not trigger another capability, retry, fallback provider, or hidden agent step.

## Gate 11.2 AWS / IAM / cost boundary

```text
real reasoning model calls:   0
real AWS calls:               0
new AWS resources:            0
new IAM roles/policies:       0
public runtime:               0
AgentCore runtime:            0
MCP:                          0
A2A:                          0
runtime-exposure authority:   0
```

Gate 11.2 tests use injected fakes and frozen local fixtures. Existing capability contracts may have AWS-backed adapters elsewhere in OpsLens, but no AWS execution is claimed for this gate.

No runtime cost is measured because no real runtime/provider execution occurs.

Gate 11.2 also does not mutate `operational-telemetry:v1`; future agent execution telemetry requires a separately versioned contract.

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It remains deferred and must be re-evaluated against the current OpsLens architecture before any merge.

## Next authorized step

```text
Phase 11 Gate 11.3 — Frozen Single-Agent Evaluation Fixture
```

Gate 11.3 must remain offline and deterministic. It must freeze evaluation cases and independent metrics over the already-merged `single-agent-authority:v1` and `single-agent-execution:v1` contracts before a reasoning model is allowed into Gate 11.4.

Required rules:

```text
1. evaluate proposal/authorization/execution as separate stages.
2. include allowlisted ACT, ABSTAIN, denied capability, malformed/tampered identity, and result-binding failure cases.
3. freeze expected capability selection separately from execution/result correctness.
4. keep deterministic authority/admission metrics separate from future model quality metrics.
5. record execution-attempt budget and abstention/denial behavior explicitly.
6. do not fabricate latency/cost/model-quality values before a real model baseline exists.
7. no real model, AWS, AgentCore, MCP, or A2A calls in Gate 11.3.
8. existing Phase 10 telemetry contract remains unchanged.
9. Repository Risk != Runtime Exposure remains frozen.
10. PR #89 remains deferred.
```
