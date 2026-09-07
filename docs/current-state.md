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
  Gate 11.3 Frozen single-agent evaluation fixture             COMPLETE / MERGED
  Gate 11.4 First bounded model reasoning baseline             COMPLETE / MERGED
  Gate 11.5 Measured optimization decision                     NEXT
  Gate 11.6 Phase 11 closeout                                  BLOCKED
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
Phase 11 Gate 11.4 / PR #157
8b41025facf4451490bf96223d69fbed19b4a00f
```

Gate 11.4 exact validation:

```text
issue #156:              CLOSED / COMPLETED
PR #157 final head:      2ec5b3804fa8c6454e1ea7d824b82d2db9113f91
Single-Agent CI:         34170308179 / run #37 / PASS
job:                     101889202476
PR merge test commit:    bd3802bf4003e5a447e5e104caad0a86cf8388ec
uv lock --check:         PASS
entrypoint smoke:        PASS
Ruff:                    PASS
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest:                  56 passed in 0.43s
PR #157 merge SHA:       8b41025facf4451490bf96223d69fbed19b4a00f
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
agent action proposal != capability authorization != execution result != evaluation score
AuthorizedAgentAction != capability invocation
capability invocation != execution result
evaluation evidence != operational telemetry
structured model output != trusted proposal
model selection != capability authority
agent reasoning may select/use already-authorized capabilities
agent reasoning does not acquire deterministic truth or execution authority
```

Deterministic code continues to own package/version semantics, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS/Risk Policy facts, `SemanticQuery` validation and SQL compilation, retrieval/evidence admission, hybrid route/completeness, canonical evidence/citation identity, output admission, evaluation metrics, execution limits, public request admission, immutable repository evidence binding, public-v1 scope admission, public handoff identity, operational telemetry admission/projection semantics, provider-specific telemetry document admission, agent task admission, capability allowlists, capability authorization, typed capability invocation admission, downstream result binding, agent execution identity, evaluation-fixture admission, evaluation expectation semantics, execution-bound scoring, content-addressed evaluation report identity, reasoning-output admission, reasoning invocation evidence admission, and reasoning-evaluation report identity.

LLMs may classify, plan, propose, synthesize, explain, select already-admitted citation IDs, and propose one capability selection. They do not own structured truth, repository truth, runtime exposure, SQL authority, hybrid route authority, evidence completeness, canonical provenance, capability allowlists, capability authorization, executable argument authority, provider/model selection, retry/fallback policy, arbitrary tool execution, evaluation metric computation, or telemetry authority.

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

Single-agent authority + execution + evaluation + reasoning
 -> bounded SingleAgentTask
 -> code-owned AgentCapability allowlist
 -> one provider-neutral model reasoning invocation
 -> transient untrusted structured decision
 -> deterministic reasoning-output parser
 -> AgentActionProposal
 -> deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
 -> STOP for Gate 11.4 model-quality baseline

Existing execution/evaluation boundary remains independently frozen:
 -> exact typed capability invocation
 -> capability-specific executor port
 -> one-attempt typed result admission
 -> content-addressed AgentCapabilityExecution
 -> strict golden AgentEvaluationDataset
 -> deterministic decomposed evaluation metrics
 -> content-addressed AgentEvaluationReport
 -> STOP
```

The final Gate 11.4 `STOP` is material. OpsLens now has a real single-agent reasoning baseline without granting the model capability-execution authority. It still has no deployed agent runtime, public agent endpoint, AgentCore runtime, MCP, or A2A execution.

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

## Gate 11.3 — Frozen Single-Agent Evaluation Fixture

Frozen contract:

```text
single-agent-evaluation:v1
```

The strict golden corpus contains six deterministic cases covering:

```text
authorized capability without execution
explicit abstention
unauthorized capability rejection
admitted typed execution
executor failure
result-contract failure
```

The evaluator replays the already-frozen Gate 11.1 authorization boundary and, where explicitly requested by the case, the Gate 11.2 typed execution boundary. It does not grant capability authority, repair result bindings, retry failed execution, or use an LLM as judge.

Decomposed deterministic metrics:

```text
total_cases
passed_cases
authorization_matches
capability_matches
execution_matches
failure_category_matches
bounds_compliant_cases
```

Case results and the complete report are content-addressed. Executor exception text is discarded before evaluation evidence admission. Report serialization excludes raw task text and arbitrary provider/executor messages.

Gate 11.3 runtime boundary:

```text
real reasoning model calls:   0
real AWS calls:               0
new AWS resources:            0
new IAM roles/policies:       0
AgentCore runtime:            0
MCP:                          0
A2A:                          0
gateway integration:          0
```

No inference cost, latency, token use, or model quality is claimed for Gate 11.3. Absence of a call is not a measured zero-cost observation.

## Gate 11.4 — First Bounded Model Reasoning Baseline

Frozen contracts:

```text
single-agent-reasoning:v1
single-agent-reasoning-evaluation:v1
```

Authority boundary:

```text
SingleAgentTask
 -> one fixed provider-neutral reasoning invocation
 -> transient untrusted {decision, capability}
 -> deterministic parser
 -> existing AgentActionProposal
 -> existing authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
 -> STOP
```

The model cannot emit executable args/kwargs, SQL, URLs, shell commands, credentials, provider/model selection, retry/fallback policy, or result data. Raw model output is transient and excluded from admitted reasoning/report evidence.

Fixed first provider:

```text
Amazon Bedrock Converse
region:          us-east-1
model/profile:   us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:       disabled
tools:           disabled
temperature:     0.0
maxTokens:       96
```

The first authenticated runtime attempt exposed a concrete provider compatibility boundary: Bedrock structured outputs rejected JSON Schema `oneOf`. The adapter was corrected to a flat closed schema over `decision` and `capability`, while ACT/non-null and ABSTAIN/null consistency remains deterministic application authority. A regression test freezes that provider-compatible schema shape.

First real frozen corpus result:

```text
total cases:             6
passed cases:            6
decision matches:        6
capability matches:      6
authorization matches:   6
bounds-compliant cases:  6
SDK retries:             0
capability executions:   0
```

Preserved evidence:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Measured runtime observations:

```text
input tokens:             3291
output tokens:             104
total tokens:             3395
cache read/write tokens:  0 / 0
provider latency mean:    843.833333 ms
provider latency median:  809.5 ms
provider latency max:     1053 ms
client elapsed mean:      1379.833333 ms
client elapsed median:    977.5 ms
client elapsed max:       3418 ms
derived inference cost:   USD 0.0041921
```

The derived inference cost uses observed token counts and contemporaneously verified US geographic cross-Region Claude Haiku 4.5 rates. It is not an AWS invoice reconciliation. The first client call had a much larger client-minus-provider interval than the remaining calls; no cause is asserted without separate evidence.

Gate 11.4 AWS/runtime boundary:

```text
new AWS resources:              0
new IAM roles/policies:         0
AgentCore runtime:              0
MCP:                            0
A2A:                            0
public agent runtime:           0
runtime-exposure authority:     0
Governed LLM Gateway changes:   0
```

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It remains deferred and must be re-evaluated against the current OpsLens architecture before any merge.

## Next authorized step

```text
Phase 11 Gate 11.5 — Measured Optimization Decision
```

Gate 11.5 must start from the measured Gate 11.4 baseline rather than assume that an optimization is required. Current evidence already shows `6/6` proposal quality, `6/6` bounds compliance, zero retries, zero capability executions, sub-second median provider latency, and a six-case derived inference cost of USD 0.0041921.

The next gate must first identify a concrete, measurable quality, latency, token, or cost gap before authorizing any optimization experiment. If no material gap is justified by evidence, preserving the Gate 11.4 baseline unchanged is a valid engineering outcome and Gate 11.6 closeout should become next. PR #89 remains deferred and `operational-telemetry:v1` remains unchanged unless a separately versioned agent-specific telemetry contract is justified.
