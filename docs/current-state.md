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

Gate 11.4 final validation and merge:

```text
issue #156:               CLOSED / COMPLETED
PR #157 final head:       2ec5b3804fa8c6454e1ea7d824b82d2db9113f91
Single-Agent CI:          34170308179 / run #37 / PASS
job:                      101889202476
PR merge test commit:     bd3802bf4003e5a447e5e104caad0a86cf8388ec
uv lock --check:          PASS
entrypoint smoke:         PASS
Ruff:                     PASS
Pyright strict:           0 errors / 0 warnings / 0 informations
pytest:                   56 passed in 0.43s
PR #157 merge SHA:        8b41025facf4451490bf96223d69fbed19b4a00f
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
agent reasoning may select an already-permitted capability
agent reasoning does not acquire deterministic truth or execution authority
```

Deterministic code continues to own package/version semantics, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS/Risk Policy facts, `SemanticQuery` validation and SQL compilation, retrieval/evidence admission, hybrid routing/completeness, canonical evidence/citation identity, output admission, public request admission, immutable repository evidence binding, capability allowlists, capability authorization, typed capability invocation/result binding, evaluation metrics, content-addressed report identity, and runtime-exposure authority.

LLMs may classify, plan, propose, synthesize, explain, select already-admitted citation IDs, and propose one already-permitted capability. They do not own structured truth, SQL authority, evidence completeness, capability authorization, executable argument authority, provider/model selection, retry/fallback policy, arbitrary tool execution, or evaluation metric computation.

## Phase 11 frozen contracts

```text
Gate 11.1  single-agent-authority:v1
Gate 11.2  single-agent-execution:v1
Gate 11.3  single-agent-evaluation:v1
Gate 11.4  single-agent-reasoning:v1
           single-agent-reasoning-evaluation:v1
```

Current bounded reasoning path:

```text
SingleAgentTask
 -> one model invocation
 -> transient untrusted {decision, capability}
 -> deterministic parser
 -> AgentActionProposal
 -> deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
 -> STOP
```

Gate 11.4 deliberately stops before capability execution. Gate 11.2 remains the execution/result-admission authority.

Reasoning limits:

```text
model invocations per task: 1
application retries:        0
adaptive fallbacks:         0
capability executions:      0
raw model output persisted: no
```

## Gate 11.4 real Bedrock baseline

Fixed provider boundary:

```text
provider:        Amazon Bedrock Converse
region:          us-east-1
model/profile:   us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:       disabled
tools:           disabled
temperature:     0.0
maxTokens:       96
```

The first authenticated runtime attempt exposed that Bedrock structured outputs reject JSON Schema `oneOf`. The provider schema was therefore reduced to a flat closed object with `decision` and `capability`; ACT/non-null and ABSTAIN/null consistency remains deterministically enforced by application code. The provider-valid response is still an untrusted proposal.

Preserved first real baseline:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
```

Content identities:

```text
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Measured quality and bounds:

```text
total cases:             6
passed cases:            6
decision matches:        6
capability matches:      6
authorization matches:   6
bounds-compliant cases:  6
SDK retries:             0
capability executions:   0
stop reason:             end_turn for all 6 calls
```

Measured usage, latency, and experiment-time cost:

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

The cost is a token-price derivation from observed usage using the contemporaneously verified US geographic cross-Region Claude Haiku 4.5 rates. It is not an AWS invoice reconciliation. The first client call has a materially larger client-minus-provider interval than the remaining calls; no cold-start or connection-setup cause is asserted without separate evidence.

## AWS / IAM / runtime boundary

Gate 11.4 introduced no new AWS resources, IAM roles/policies, AgentCore runtime, MCP, A2A, public agent runtime, or runtime-exposure authority. The real replay used the already-authorized `opslens-bootstrap` IAM Identity Center profile. No credentials are stored in the repository.

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It remains deferred and must be re-evaluated against the current OpsLens architecture before any merge.

## Next authorized step

```text
Phase 11 Gate 11.5 — Measured Optimization Decision
```

Gate 11.5 must start from the observed Gate 11.4 baseline rather than assume an optimization is required. The current evidence already shows `6/6` proposal quality, `6/6` bounds compliance, zero retries, zero capability executions, sub-second median provider latency, and a six-case derived inference cost of USD 0.0041921.

The next gate should first decide whether a bounded optimization experiment has a measurable objective and material expected benefit. If no concrete quality, latency, or cost gap justifies a change, the correct engineering decision may be to preserve the Gate 11.4 baseline unchanged and proceed to Phase 11 closeout. No AgentCore, MCP, A2A, public runtime, or Governed LLM Gateway integration is authorized by this checkpoint.
