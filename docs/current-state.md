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
Phase 11   Single-Agent Baseline                               COMPLETE
  Gate 11.1 Bounded capability authorization contract          COMPLETE / MERGED
  Gate 11.2 Typed capability bindings + offline executor       COMPLETE / MERGED
  Gate 11.3 Frozen single-agent evaluation fixture             COMPLETE / MERGED
  Gate 11.4 First bounded model reasoning baseline             COMPLETE / MERGED
  Gate 11.5 Measured optimization decision                     COMPLETE / MERGED — NO-CHANGE
  Gate 11.6 Phase 11 closeout                                  COMPLETE / MERGED
Phase 12   Multi-Agent Architecture                            IN PROGRESS
  Gate 12.1 Bounded specialization handoff contract            COMPLETE / MERGED
  Gate 12.2 Comparative multi-agent evaluation contract        NEXT
Phase 13   MCP                                                 PLANNED
Phase 14   Amazon Bedrock AgentCore                            PLANNED
Phase 15   A2A                                                 PLANNED
Phase 16   Runtime Exposure with Amazon Inspector              PLANNED
Phase 17   Security Hardening                                  PLANNED
Phase 18   Evaluation, Cost & Portfolio Readiness              PLANNED
```

Latest merged checkpoint:

```text
Phase 12 Gate 12.1 / PR #166
eceed76a6cfc5d7e28e88dfdc503b4863b526ba0
```

Gate 12.1 exact validation and merge:

```text
issue #165:               OPEN until this state synchronization completes
PR #166 final head:       567cdbde81f058d9545328ca78b718c24d79c9fb
PR merge test commit:     b1e40ea858726c0672601db8c51c353ffbcc03ae
Multi-Agent CI:           34172909750 / run #3 / PASS
job:                      101896544229
uv lock --check:          PASS
Ruff:                     PASS
Pyright strict:           0 errors / 0 warnings / 0 informations
pytest:                   10 passed in 0.39s
Single-Agent CI:          34172909748 / run #48 / PASS
single-agent pytest:      56 passed in 0.44s
PR #166 merge SHA:        eceed76a6cfc5d7e28e88dfdc503b4863b526ba0
real model calls:         0
capability executions:    0
new AWS resources:        0
new IAM roles/policies:   0
```

## Permanent architecture boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

Agentic authority remains explicitly separated:

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
structured model output != trusted proposal
model selection != capability authority
```

Deterministic code continues to own package/version semantics, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS/Risk Policy facts, `SemanticQuery` validation and SQL compilation, retrieval/evidence admission, hybrid routing/completeness, canonical evidence/citation identity, output admission, public request admission, immutable repository evidence binding, capability allowlists, capability authorization, typed capability invocation/result binding, handoff admission, specialization mapping, evaluation metrics, content-addressed evidence/report identity, provider/model selection, retry/fallback policy, and runtime-exposure authority.

LLMs may classify, plan, propose, synthesize, explain, select already-admitted citation IDs, propose one already-permitted capability, and in a future measured Phase 12 experiment propose one closed specialization. They do not own structured truth, SQL authority, evidence completeness, capability authorization, executable arguments, provider/model selection, retry/fallback policy, arbitrary tool execution, evaluation metric computation, handoff admission, or runtime-exposure truth.

## Phase 11 frozen reference

Frozen contracts:

```text
single-agent-authority:v1
single-agent-execution:v1
single-agent-evaluation:v1
single-agent-reasoning:v1
single-agent-reasoning-evaluation:v1
```

Permanent bounded reasoning path:

```text
SingleAgentTask
 -> code-owned AgentCapability allowlist
 -> one bounded model reasoning invocation
 -> transient untrusted {decision, capability}
 -> deterministic parser
 -> AgentActionProposal
 -> deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
```

The Gate 11.4 model-quality baseline deliberately stops before capability execution. Gate 11.2 remains the independent typed execution/result-admission authority.

First real frozen six-case reference:

```text
provider:                     Amazon Bedrock Converse
region:                       us-east-1
model/profile:                us.anthropic.claude-haiku-4-5-20251001-v1:0
quality:                      6/6
bounds compliance:            6/6
SDK retries:                  0
capability executions:        0
input/output/total tokens:    3291 / 104 / 3395
provider latency median:      809.5 ms
client elapsed median:        977.5 ms
derived six-case cost:        USD 0.0041921
```

Historical evidence:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Gate 11.5 remains:

```text
optimization decision: NO-CHANGE / NO-EXPERIMENT
```

No later phase may reinterpret the 6/6 acceptance-corpus result as a hidden quality gap without new measured evidence.

## Phase 12 Gate 12.1 frozen handoff boundary

New contract:

```text
multi-agent-handoff:v1
```

Code-owned specialization partition:

```text
EVIDENCE_ANALYSIS
 -> public_repository_analysis
 -> structured_security_query

GUIDANCE_SYNTHESIS
 -> hybrid_security_answer
 -> knowledge_guidance
```

Deterministic handoff path:

```text
SingleAgentTask
 -> TriageAgentTask
 -> untrusted MultiAgentHandoffProposal
 -> deterministic source-task identity check
 -> code-owned specialization scope
 -> deterministic intersection with source allowed_capabilities
 -> empty intersection? FAIL CLOSED
 -> AuthorizedMultiAgentHandoff | MultiAgentHandoffAbstention
 -> narrowed SpecialistAgentTask
 -> STOP
```

Hard bounds:

```text
maximum handoffs per source task:       1
maximum specialist capability surface:  2
real model calls in Gate 12.1:           0
capability executions in Gate 12.1:      0
adaptive retry/fallback:                 0
```

The handoff proposal contains no arbitrary message/context payload, capability selection, args/kwargs, SQL, URL, shell command, credential, provider/model selection, retry/fallback policy, or execution result.

The one-way `TriageAgentTask -> SpecialistAgentTask` API prevents recursive delegation/cycles in v1. A specialist task is not an admitted handoff source.

Gate 12.1 proves deterministic reasoning-surface narrowing from at most four Phase 11 capabilities to at most two specialist capabilities. It does **not** prove runtime privilege reduction because models still have no capability execution authority.

## What Gate 12.1 does not prove

```text
multi-agent quality improvement
triage-model routing accuracy
specialist-model reasoning quality
multi-agent latency
multi-agent token usage
multi-agent inference cost
multi-agent reliability
runtime privilege reduction
capability execution through a multi-agent flow
AgentCore behavior
MCP interoperability
A2A interoperability
public/deployed agent runtime
runtime exposure / Amazon Inspector evidence
```

## AWS / IAM / runtime boundary

Gate 12.1 introduced no AWS resources, IAM roles/policies, provider adapters, real model calls, capability executions, AgentCore runtime, MCP, A2A, public runtime, or runtime-exposure authority.

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It remains deferred and must be re-evaluated against the current OpsLens architecture before any merge.

Current preserved head:

```text
3781831795d500b05fa4bc602d50f376b4b1539f
```

## Next authorized gate

```text
Phase 12 — Gate 12.2: Comparative Multi-Agent Evaluation Contract
```

Gate 12.2 must freeze the comparison protocol before any second real model invocation is allowed. At minimum the comparison must include routing/proposal quality, bounds compliance, specialist capability-surface width, model invocation count, token usage, provider/client latency, retries, inference cost, and capability executions.

A two-model topology is not presumed beneficial. It must be rejected if measured specialization value does not justify the additional model call, latency, cost, complexity, or failure surface.

AgentCore, MCP, and A2A remain separate future architecture decisions.
