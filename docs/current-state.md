# OpsLens — Current State

_Last updated: 2026-09-08_

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
  Gate 12.3 First bounded real two-model comparison            COMPLETE / MERGED
  Gate 12.4 Measured multi-agent retention decision            NEXT
Phase 13   MCP                                                 PLANNED
Phase 14   Amazon Bedrock AgentCore                            PLANNED
Phase 15   A2A                                                 PLANNED
Phase 16   Runtime Exposure with Amazon Inspector              PLANNED
Phase 17   Security Hardening                                  PLANNED
Phase 18   Evaluation, Cost & Portfolio Readiness              PLANNED
```

Latest merged checkpoint:

```text
Phase 12 Gate 12.3 / PR #172
f51cb70ad070716e774419b8d2c62918d3e65210
```

Gate 12.3 exact validation and merge:

```text
issue #171:               CLOSED / COMPLETED
PR #172 final head:       cf6001f374e3b14bb8048465e36210adc596b3ce
PR merge test commit:     ddd275e44d8c2122b947bc9241a321c46fef9148
Multi-Agent CI:           34218039083 / run #32 / PASS
job:                      102034353535
offline fixture CLI:      PASS
real CLI --help smoke:    PASS
uv lock --check:          PASS
Ruff:                     PASS
Pyright strict:           0 errors / 0 warnings / 0 informations
pytest:                   33 passed in 0.33s
PR #172 merge SHA:        f51cb70ad070716e774419b8d2c62918d3e65210
new AWS resources:        0
new IAM roles/policies:   0
capability executions:    0
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

LLMs may classify, plan, propose, synthesize, explain, select already-admitted citation IDs, propose one already-permitted capability, and inside the bounded Gate 12.3 experiment propose one closed specialization. Models do not own structured truth, SQL authority, evidence completeness, handoff admission, capability authorization, executable arguments, provider/model selection, retry/fallback policy, arbitrary tool execution, evaluation metric computation, or runtime-exposure truth.

## Phase 11 frozen single-agent reference

Frozen contracts:

```text
single-agent-authority:v1
single-agent-execution:v1
single-agent-evaluation:v1
single-agent-reasoning:v1
single-agent-reasoning-evaluation:v1
```

Permanent reasoning path:

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
model invocations:            6
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

Gate 11.5 retained this reference with `NO-CHANGE / NO-EXPERIMENT`. No later phase may reinterpret the `6/6` acceptance-corpus result as a hidden quality gap without new measured evidence.

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

The `4 -> <=2` capability reduction is deterministic reasoning-surface narrowing, not runtime privilege reduction. Models still have no capability execution authority.

## Phase 12 Gate 12.2 frozen comparison boundary

Contract:

```text
multi-agent-comparison:v1
```

Gate 12.2 froze comparison semantics before the second real model call. The six-case synthetic fixture remains evaluator/contract conformance only, not model quality.

Frozen identities:

```text
dataset_sha256:
1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491

report_sha256:
0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
```

## Phase 12 Gate 12.3 real two-model evidence

Frozen experiment contracts:

```text
multi-agent-triage-reasoning:v1
multi-agent-two-model-reasoning:v1
multi-agent-real-comparison:v1
```

Bounded runtime path:

```text
SingleAgentTask
 -> one triage model invocation
 -> transient {decision, target_specialization}
 -> deterministic parser
 -> Gate 12.1 deterministic handoff admission
 -> ABSTAIN / rejected? STOP
 -> narrowed SpecialistAgentTask
 -> one specialist reasoning invocation
 -> transient {decision, capability}
 -> deterministic parser
 -> existing deterministic capability authorization
 -> STOP before capability execution
```

Hard bounds:

```text
maximum model invocations per task: 2
maximum handoffs per source task:    1
maximum specialist capability width: 2
adaptive application retries:       0
adaptive fallbacks:                 0
capability executions:              0
```

The first authenticated Bedrock replay is preserved at:

```text
labs/evidence/phase-12-gate-12-3-first-real-two-model-comparison-v1.json
```

Content-addressed identities:

```text
dataset_sha256:
0439ebaa6215b2de7eaa82624188576743b5a50cc847137e04dc97ee7a199be7

report_sha256:
45edf58ac911ec14e872a00464dad5d5311d82165d6b8ac4321da4a0dc5ad09b
```

Observed real result:

```text
quality:                           6/6
triage decision matches:           6/6
specialization matches:            6/6
handoff admission matches:         6/6
target-scope matches:              6/6
non-broadening cases:              6/6
specialist decision matches:       6/6
specialist capability matches:     6/6
specialist authorization matches:  6/6
runtime-bounds compliant:          6/6
model invocations:                 10
input/output/total tokens:          5788 / 194 / 5982
provider latency median per task:  1694.0 ms
client elapsed median per task:    2135.0 ms
SDK retries:                       0
capability executions:             0
derived six-case cost:             USD 0.0074338
```

The two abstention cases stopped after triage. The four admitted handoffs invoked exactly one specialist. No adaptive retry, fallback, capability executor, IAM expansion, or new AWS resource was introduced.

## Measured Phase 11 vs Gate 12.3 comparison

```text
metric                     Phase 11       Gate 12.3        delta
quality                    6/6            6/6              no lift
model invocations          6              10               +66.67%
input tokens               3291           5788             +75.87%
output tokens              104            194              +86.54%
total tokens               3395           5982             +76.20%
provider latency median    809.5 ms       1694.0 ms        +109.26%
client elapsed median      977.5 ms       2135.0 ms        +118.41%
SDK retries                0              0                 unchanged
capability executions      0              0                 unchanged
derived cost               USD 0.0041921  USD 0.0074338    +77.33%
```

Gate 12.3 proves that the bounded two-model topology can preserve the frozen quality and all deterministic authority boundaries. It does **not** demonstrate a quality improvement. The measured coordination overhead is material.

The triage stage alone cost USD `0.0046002` for the six cases, approximately 9.73% more than the complete Phase 11 six-case single-agent reference.

## AWS / IAM / runtime boundary

The Gate 12.3 experiment used the existing human IAM Identity Center path to invoke the already selected Bedrock profile. It did not justify or introduce:

```text
new AWS resources
new IAM roles or policies
GitHub OIDC trust broadening
capability execution
AgentCore runtime
MCP
A2A
public agent runtime
runtime-exposure authority
```

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It remains deferred and must be re-evaluated against the current OpsLens architecture before any merge.

Preserved historical head:

```text
3781831795d500b05fa4bc602d50f376b4b1539f
```

## Next authorized gate

```text
Phase 12 — Gate 12.4: Measured Multi-Agent Retention Decision
```

Gate 12.4 is a decision gate, not an automatic tuning gate. It must use the frozen Phase 11 reference and the preserved Gate 12.3 real evidence to decide whether the two-model topology should be retained, rejected, deferred, or redesigned.

The default next action is **no new model experiment** unless a concrete, falsifiable benefit hypothesis exists that is not already answered by Gate 12.3 evidence.

Current evidence shows equal `6/6` acceptance quality with materially higher call count, token usage, latency, cost, failure surface, and implementation complexity. Therefore the two-model path must not become the retained/default architecture merely because it is more agentic.

Gate 12.4 must preserve historical Gate 12.3 artifacts regardless of its decision. AgentCore, MCP, and A2A remain separate future architecture decisions.
