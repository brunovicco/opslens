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
Phase 12   Multi-Agent Architecture                            IN PROGRESS
  Gate 12.1 Bounded specialization handoff contract            COMPLETE / MERGED
  Gate 12.2 Comparative multi-agent evaluation contract        COMPLETE / MERGED
  Gate 12.3 First bounded real two-model comparison            NEXT
Phase 13   MCP                                                 PLANNED
Phase 14   Amazon Bedrock AgentCore                            PLANNED
Phase 15   A2A                                                 PLANNED
Phase 16   Runtime Exposure with Amazon Inspector              PLANNED
Phase 17   Security Hardening                                  PLANNED
Phase 18   Evaluation, Cost & Portfolio Readiness              PLANNED
```

Latest merged checkpoint:

```text
Phase 12 Gate 12.2 / PR #169
865ba70c813711cb88da9ac7308c8966ff983fd0
```

Gate 12.2 exact validation and merge:

```text
issue #168:               OPEN until this state synchronization completes
PR #169 final head:       953467df99ddeaedd6e19471bd2dce6c5bb8de7c
PR merge test commit:     bab183ee1dbcca0eb6a0bb76b5130180f9f2f7c2
Multi-Agent CI:           34174680219 / run #7 / PASS
job:                      101901637997
offline fixture CLI:      PASS
uv lock --check:          PASS
Ruff:                     PASS
Pyright strict:           0 errors / 0 warnings / 0 informations
pytest:                   18 passed in 0.27s
PR #169 merge SHA:        865ba70c813711cb88da9ac7308c8966ff983fd0
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
synthetic fixture conformance != model quality
model selection != capability authority
```

Deterministic code continues to own package/version semantics, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS/Risk Policy facts, `SemanticQuery` validation and SQL compilation, retrieval/evidence admission, hybrid routing/completeness, canonical evidence/citation identity, output admission, public request admission, immutable repository evidence binding, capability allowlists, capability authorization, typed capability invocation/result binding, handoff admission, specialization mapping, comparison/evaluation metrics, content-addressed evidence/report identity, provider/model selection, retry/fallback policy, and runtime-exposure authority.

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

Gate 11.5 remains `NO-CHANGE / NO-EXPERIMENT`. No later phase may reinterpret the `6/6` acceptance-corpus result as a hidden quality gap without new measured evidence.

## Phase 12 Gate 12.1 frozen handoff boundary

Contract:

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
```

The `4 -> <=2` capability reduction is deterministic reasoning-surface narrowing, not runtime privilege reduction. Models still have no capability execution authority.

## Phase 12 Gate 12.2 frozen comparison boundary

Contract:

```text
multi-agent-comparison:v1
```

Offline comparison path:

```text
frozen comparison fixture
 -> admitted SingleAgentTask
 -> synthetic untrusted MultiAgentHandoffProposal
 -> existing Gate 12.1 handoff admission
 -> HANDOFF | ABSTAINED | REJECTED
 -> deterministic decomposed case score
 -> content-addressed comparison report
 -> runtime measurements remain null
 -> STOP
```

Frozen evidence identities:

```text
dataset_sha256:
1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491

report_sha256:
0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
```

Frozen synthetic conformance metrics:

```text
total / passed:                        6 / 6
decision matches:                      6
specialization matches:                6
admission matches:                     6
target scope matches:                  6
non-broadening cases:                  6
bounds-compliant cases:                6
handoff / abstention cases:             4 / 2
source capability slots for handoffs: 16
specialist capability slots:            8
capability slots removed:               8
offline capability executions:          0
```

This `6/6` is synthetic contract/evaluator conformance only. It is **not** triage-model quality, specialist-model quality, or a multi-agent runtime baseline.

Because Gate 12.2 makes no model call, these fields are deliberately `null`, not zero:

```text
model invocation count
input/output/total tokens
provider latency
client elapsed latency
SDK retries
inference cost
```

This prevents unmeasured runtime evidence from being represented as an observed zero.

## What Gate 12.2 does not prove

```text
triage model quality
specialist model quality
multi-agent quality improvement
real multi-agent model invocation count
real multi-agent token usage
real multi-agent latency
real multi-agent retries
real multi-agent inference cost
capability execution through a multi-agent flow
production reliability
runtime privilege reduction
AgentCore / MCP / A2A behavior
```

## AWS / IAM / runtime boundary

Gate 12.2 introduced no AWS resources, IAM roles/policies, provider adapters, real model calls, capability executions, AgentCore runtime, MCP, A2A, public runtime, or runtime-exposure authority.

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It remains deferred and must be re-evaluated against the current OpsLens architecture before any merge.

Current preserved head:

```text
3781831795d500b05fa4bc602d50f376b4b1539f
```

## Next authorized gate

```text
Phase 12 — Gate 12.3: First Bounded Real Two-Model Comparison
```

The first real comparison may introduce at most two bounded reasoning invocations per task:

```text
SingleAgentTask
 -> bounded triage model proposes specialization only
 -> deterministic parser + Gate 12.1 handoff admission
 -> narrowed SpecialistAgentTask
 -> bounded specialist reasoning proposes capability only
 -> existing deterministic capability authorization
 -> STOP before capability execution
```

Required hard bounds for the first experiment:

```text
maximum model invocations per task: 2
maximum handoffs:                   1
adaptive application retries:       0
adaptive fallbacks:                 0
capability executions:              0
```

Real tokens, latency, SDK retries, and inference cost must come only from observed provider evidence. The two-model topology must be rejected if measured specialization value does not justify its additional call, latency, token usage, cost, failure surface, and architectural complexity.

AgentCore, MCP, and A2A remain separate future architecture decisions.
