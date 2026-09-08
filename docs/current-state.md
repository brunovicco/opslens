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
Phase 12   Multi-Agent Architecture                            NEXT
Phase 13   MCP                                                 PLANNED
Phase 14   Amazon Bedrock AgentCore                            PLANNED
Phase 15   A2A                                                 PLANNED
Phase 16   Runtime Exposure with Amazon Inspector              PLANNED
Phase 17   Security Hardening                                  PLANNED
Phase 18   Evaluation, Cost & Portfolio Readiness              PLANNED
```

Latest merged phase checkpoint:

```text
Phase 11 Gate 11.6 / PR #163
a075c9a8ec3f0998e990d0b854bfd9ed22cabd07
```

Gate 11.6 exact validation and merge:

```text
issue #162:               CLOSED / COMPLETED after state synchronization
PR #163 final head:       a17f7adc334473b3047ed3e37962b6a5881f7934
Single-Agent CI:          34171804704 / run #44 / PASS
job:                      101893384194
PR merge test commit:     7fc884c7d2cf3de6ce2e0c09d0184da06ac5ebc9
uv lock --check:          PASS
entrypoint smoke:         PASS
Ruff:                     PASS
Pyright strict:           0 errors / 0 warnings / 0 informations
pytest:                   56 passed in 0.44s
PR #163 merge SHA:        a075c9a8ec3f0998e990d0b854bfd9ed22cabd07
new AWS resources:        0
new IAM roles/policies:   0
new model calls:          0
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
agent action proposal != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
structured model output != trusted proposal
evaluation evidence != operational telemetry
model selection != capability authority
agent reasoning may select an already-permitted capability
agent reasoning does not acquire deterministic truth or execution authority
```

Deterministic code continues to own package/version semantics, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS/Risk Policy facts, `SemanticQuery` validation and SQL compilation, retrieval/evidence admission, hybrid routing/completeness, canonical evidence/citation identity, output admission, public request admission, immutable repository evidence binding, capability allowlists, capability authorization, typed capability invocation/result binding, evaluation metrics, content-addressed evidence/report identity, provider/model selection, retry/fallback policy, and runtime-exposure authority.

LLMs may classify, plan, propose, synthesize, explain, select already-admitted citation IDs, and propose one already-permitted capability. They do not own structured truth, SQL authority, evidence completeness, capability authorization, executable argument authority, provider/model selection, retry/fallback policy, arbitrary tool execution, evaluation metric computation, or runtime-exposure truth.

## Phase 11 frozen contracts

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

Typed execution remains:

```text
AuthorizedAgentAction
 -> exact typed capability invocation
 -> deterministic action/capability match
 -> capability-specific executor port
 -> one bounded execution attempt
 -> typed downstream result admission
 -> content-addressed AgentCapabilityExecution
```

The initial capability surface is frozen as:

```text
structured_security_query
knowledge_guidance
hybrid_security_answer
public_repository_analysis
```

No generic tool registry or arbitrary argument envelope exists.

## Gate 11.4 real Bedrock reference baseline

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

The first authenticated runtime attempt exposed that Bedrock structured outputs reject JSON Schema `oneOf`. The provider schema was reduced to a flat closed object while ACT/non-null and ABSTAIN/null consistency remained deterministic application authority.

Preserved first real baseline:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
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

The cost is derived from observed token usage and contemporaneously verified Bedrock pricing. It is not AWS invoice reconciliation. The six-case result is an acceptance-corpus result, not a universal model-correctness claim.

## Gate 11.5 measured optimization decision

Gate 11.5 reviewed the real baseline and merged:

```text
optimization decision: NO-CHANGE / NO-EXPERIMENT
additional model calls: 0
prompt change:          NO
model/profile change:   NO
cache change:           NO
retry/fallback change:  NO
authority change:       NO
```

Prompt compression, model switching, prompt caching, retry/fallback expansion, and capability expansion were rejected because no material measured target justified the added behavioral or security complexity. Client warm-up/connection reuse remains deferred because the observed first-call client/provider latency difference has no proven cause or repeatability.

## What Phase 11 proves

```text
one real model reasoning boundary can remain proposal-only
capability allowlists remain code-owned
capability authorization remains deterministic
execution remains typed and independently bounded
result admission preserves exact downstream identity
evaluation remains deterministic and decomposed
real token/latency/retry evidence can be captured without granting authority
measured evidence can justify NO-CHANGE instead of speculative tuning
```

## What Phase 11 does not prove

```text
multi-agent quality or coordination
public/deployed agent runtime
production request volume
production p95/p99 or SLO compliance
AgentCore runtime behavior
MCP interoperability
A2A interoperability
runtime exposure / Amazon Inspector evidence
universal model correctness
production cost/request
AWS billing reconciliation
```

## AWS / IAM / runtime boundary

Phase 11 introduced no new deployed agent runtime, public agent endpoint, AgentCore runtime, MCP runtime, A2A runtime, or runtime-exposure authority.

The real Gate 11.4 replay used the already-authorized local `opslens-bootstrap` IAM Identity Center profile. No credentials are stored in the repository.

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It remains deferred and must be re-evaluated against the current OpsLens architecture before any merge.

## Next authorized phase

```text
Phase 12 — Multi-Agent Architecture
```

Phase 12 must not add agents merely because the roadmap contains a multi-agent phase. Every specialization requires one explicit bounded responsibility, explicit handoff/failure/stopping semantics, preserved deterministic authority, and comparative evaluation against the frozen Phase 11 single-agent reference before any improvement claim.

AgentCore, MCP, and A2A remain separate future architecture decisions.
