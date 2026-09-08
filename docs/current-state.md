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
Phase 12   Multi-Agent Architecture                            COMPLETE
  Gate 12.1 Bounded specialization handoff contract            COMPLETE / MERGED
  Gate 12.2 Comparative multi-agent evaluation contract        COMPLETE / MERGED
  Gate 12.3 First bounded real two-model comparison            COMPLETE / MERGED
  Gate 12.4 Measured multi-agent retention decision            COMPLETE / MERGED
  Gate 12.5 Multi-agent phase closeout                         COMPLETE / MERGED
Phase 13   MCP                                                 NEXT
Phase 14   Amazon Bedrock AgentCore                            PLANNED
Phase 15   A2A                                                 PLANNED
Phase 16   Runtime Exposure with Amazon Inspector              PLANNED
Phase 17   Security Hardening                                  PLANNED
Phase 18   Evaluation, Cost & Portfolio Readiness              PLANNED
```

Latest merged checkpoint:

```text
Phase 12 Gate 12.5 / PR #178
aca4264e9c98f81c239b44b55c8772ef02debc4c
```

Gate 12.5 exact validation and merge:

```text
issue #177:               closeout tracker; closure follows final state synchronization
PR #178 final head:       3d9ad6a6d302299fb8209b40c7232bc18555c2dd
PR merge test commit:     f2de18db9a2b23413be4977e3f4b21a5846ed837
Multi-Agent CI:           34220492021 / run #34 / PASS
job:                      102042205489
uv lock --check:          PASS
offline comparison:       PASS
real CLI --help smoke:    PASS
Ruff:                     PASS
Pyright strict:           0 errors / 0 warnings / 0 informations
pytest:                   33 passed in 0.35s
review threads:           0
new model invocations:    0
new inference cost:       USD 0.00
PR #178 merge SHA:        aca4264e9c98f81c239b44b55c8772ef02debc4c
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

## Retained measured reasoning architecture

Phase 12 does **not** replace the Phase 11 single-agent reference.

Retained/default reasoning path:

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

Frozen Phase 11 six-case reference:

```text
provider:                     Amazon Bedrock Converse
region:                       us-east-1
model/profile:                us.anthropic.claude-haiku-4-5-20251001-v1:0
quality:                      6/6
model invocations:            6
input/output/total tokens:    3291 / 104 / 3395
provider latency median:      809.5 ms
client elapsed median:        977.5 ms
SDK retries:                  0
capability executions:        0
derived six-case cost:        USD 0.0041921
```

Historical reference:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

## Retained Phase 12 mechanism

Gate 12.1 remains the retained deterministic specialization/handoff authority primitive:

```text
source task
 -> code-owned specialization mapping
 -> deterministic intersection with source allowed_capabilities
 -> narrowed specialist task
```

Code-owned partition:

```text
EVIDENCE_ANALYSIS
 -> public_repository_analysis
 -> structured_security_query

GUIDANCE_SYNTHESIS
 -> hybrid_security_answer
 -> knowledge_guidance
```

The `4 -> <=2` capability reduction is reasoning-surface narrowing, not runtime privilege reduction. Models still have no capability execution authority.

Gate 12.2 remains the retained deterministic comparison discipline:

```text
dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
report_sha256:  0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
synthetic conformance: 6/6
```

Synthetic fixture conformance is evaluator/contract evidence only, not model quality.

## Historical Gate 12.3 two-model experiment

The first authenticated bounded two-model experiment remains preserved at:

```text
labs/evidence/phase-12-gate-12-3-first-real-two-model-comparison-v1.json

dataset_sha256: 0439ebaa6215b2de7eaa82624188576743b5a50cc847137e04dc97ee7a199be7
report_sha256:  45edf58ac911ec14e872a00464dad5d5311d82165d6b8ac4321da4a0dc5ad09b
```

Observed result:

```text
quality:                           6/6
model invocations:                 10
input/output/total tokens:          5788 / 194 / 5982
provider latency median per task:  1694.0 ms
client elapsed median per task:    2135.0 ms
SDK retries:                       0
capability executions:             0
derived six-case cost:             USD 0.0074338
```

Compared with the retained Phase 11 reference:

```text
quality                    6/6 -> 6/6       no lift
model invocations          6 -> 10          +66.67%
total tokens               3395 -> 5982     +76.20%
provider latency median    809.5 -> 1694.0  +109.26%
client elapsed median      977.5 -> 2135.0  +118.41%
derived cost               0.0041921 -> 0.0074338 USD  +77.33%
SDK retries                0 -> 0
capability executions      0 -> 0
```

## Frozen Phase 12 retention decision

Gate 12.4 records:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
new rescue/tuning experiment:                   NOT AUTHORIZED WITHOUT NEW HYPOTHESIS
```

Decision and closeout evidence:

```text
labs/evidence/phase-12-gate-12-4-retention-decision-v1.json
labs/evidence/phase-12-closeout-v1.json
docs/adr/0045-do-not-retain-two-model-topology-without-measured-lift.md
docs/adr/0046-phase12-multi-agent-closeout.md
labs/phase-12-gate-12-5-multi-agent-closeout.md
```

Phase 12 closes around the architecture that survived measurement rather than around the most complex experiment.

## Phase 12 proof boundary

Phase 12 proves:

```text
deterministic specialization can narrow reasoning scope without moving authority into a model
comparison semantics can be frozen before adding a second model call
a bounded two-model topology can preserve deterministic authority and frozen-corpus quality
provider evidence can quantify coordination overhead
successful multi-agent execution does not imply architecture-retention success
measured evidence can justify retaining the simpler reference
```

Phase 12 does **not** prove:

```text
multi-agent capability execution in a deployed runtime
public/deployed agent runtime
production agent SLOs
Amazon Bedrock AgentCore runtime behavior
MCP interoperability
A2A interoperability
runtime exposure / Amazon Inspector evidence
universal superiority of multi-agent architecture
model-owned handoff admission
model-owned capability authorization
```

## AWS / IAM / runtime closeout

```text
new model invocations in Gate 12.5: 0
new inference cost:                 USD 0.00
new AWS resources:                  0
new IAM roles/policies:             0
GitHub OIDC trust changes:          0
capability executions:              0
AgentCore runtime:                  0
MCP implementation:                 0
A2A implementation:                 0
public agent runtime:               0
runtime-exposure authority:         0
Governed LLM Gateway changes:       0
```

## Deferred Governed LLM Gateway integration

Long-lived OpsLens PR #89 remains open/draft consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It remains deferred and must be re-evaluated against the current OpsLens architecture before any merge.

Preserved historical head:

```text
3781831795d500b05fa4bc602d50f376b4b1539f
```

## Next authorized phase

```text
Phase 13 — MCP
```

Phase 13 may expose already-bounded OpsLens capabilities through explicit MCP contracts. MCP is an interoperability boundary, not new business or execution authority.

Entry rules:

```text
MCP must not bypass deterministic capability authorization
MCP must not introduce arbitrary executable argument surfaces
MCP must preserve typed capability invocation/result admission
MCP must preserve evidence provenance and content-addressed identity
MCP must preserve least privilege and fail-closed behavior
MCP must not reinterpret Repository Risk as Runtime Exposure
AgentCore and A2A remain separate later architecture decisions
```
