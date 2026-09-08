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
  Gate 12.4 Measured multi-agent retention decision            COMPLETE / MERGED
  Gate 12.5 Multi-agent phase closeout                         NEXT
Phase 13   MCP                                                 PLANNED
Phase 14   Amazon Bedrock AgentCore                            PLANNED
Phase 15   A2A                                                 PLANNED
Phase 16   Runtime Exposure with Amazon Inspector              PLANNED
Phase 17   Security Hardening                                  PLANNED
Phase 18   Evaluation, Cost & Portfolio Readiness              PLANNED
```

Latest merged checkpoint:

```text
Phase 12 Gate 12.4 / PR #175
fabe8128d1d6077e8de92225991b5e26c1b72ab3
```

Gate 12.4 exact validation and merge:

```text
issue #174:               CLOSED / COMPLETED
PR #175 final head:       c2accab5c7a353f4c2a721cf6912d498e53b76f1
PR merge test commit:     7a57c16f55c4a432874eea2b07bf7a104e75ace2
Multi-Agent CI:           34219145838 / run #33 / PASS
job:                      102037888575
uv lock --check:          PASS
offline comparison:       PASS
real CLI --help smoke:    PASS
Ruff:                     PASS
Pyright strict:           0 errors / 0 warnings / 0 informations
pytest:                   33 passed in 0.34s
new model invocations:    0
new inference cost:       USD 0.00
PR #175 merge SHA:        fabe8128d1d6077e8de92225991b5e26c1b72ab3
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

## Retained Phase 11 single-agent reference

The retained/default measured reasoning path remains:

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

Frozen six-case reference:

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

Historical evidence:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

## Retained Phase 12 deterministic specialization boundary

Gate 12.1 remains a reusable deterministic authority/scope primitive:

```text
source task
 -> code-owned specialization mapping
 -> deterministic intersection with source allowed_capabilities
 -> narrowed specialist task
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

The `4 -> <=2` capability reduction is reasoning-surface narrowing, not runtime privilege reduction. Models still have no capability execution authority.

## Gate 12.2 frozen comparison boundary

Gate 12.2 froze deterministic comparison criteria before the second model call existed.

```text
dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
report_sha256:  0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
synthetic conformance: 6/6
```

Synthetic fixture conformance is not model quality.

## Gate 12.3 historical real two-model experiment

The first authenticated bounded two-model experiment is preserved at:

```text
labs/evidence/phase-12-gate-12-3-first-real-two-model-comparison-v1.json
```

Experiment identity:

```text
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

The experiment proved that the topology can preserve quality and deterministic authority. It did not prove that the extra model invocation adds material value.

## Gate 12.4 measured retention decision

Decision artifact:

```text
labs/evidence/phase-12-gate-12-4-retention-decision-v1.json
```

Architecture decision:

```text
docs/adr/0045-do-not-retain-two-model-topology-without-measured-lift.md
```

Measured comparison:

```text
metric                     Phase 11       Gate 12.3        delta
quality                    6/6            6/6              no lift
model invocations          6              10               +66.67%
input tokens               3291           5788             +75.87%
output tokens              104            194              +86.54%
total tokens               3395           5982             +76.20%
provider latency median    809.5 ms       1694.0 ms        +109.26%
client elapsed median      977.5 ms       2135.0 ms        +118.41%
derived cost               USD 0.0041921  USD 0.0074338    +77.33%
SDK retries                0              0                 unchanged
capability executions      0              0                 unchanged
```

Frozen retention decision:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
new rescue/tuning experiment:                   NOT AUTHORIZED WITHOUT NEW HYPOTHESIS
```

The distinction is intentional: deterministic specialization/handoff is a code-owned authority mechanism; the extra triage model invocation is a runtime topology that must justify its additional cost and failure surface.

Gate 12.4 ran no model calls and incurred no inference cost.

## AWS / IAM / runtime boundary

Gate 12.4 introduced no runtime change:

```text
new model invocations:       0
new inference cost:           USD 0.00
new AWS resources:            0
new IAM roles/policies:       0
GitHub OIDC trust changes:    0
capability executions:        0
AgentCore:                    0
MCP:                          0
A2A:                          0
public runtime:               0
runtime-exposure authority:   0
Governed LLM Gateway changes: 0
```

## Deferred Governed LLM Gateway integration

Long-lived PR #89 remains open/draft for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It remains deferred and must be re-evaluated against the current OpsLens architecture before any merge.

Preserved historical head:

```text
3781831795d500b05fa4bc602d50f376b4b1539f
```

## Next authorized gate

```text
Phase 12 — Gate 12.5: Multi-Agent Phase Closeout
```

Gate 12.5 should close Phase 12 around the measured conclusion:

```text
retained runtime reasoning reference: Phase 11 single-agent
retained Phase 12 mechanism:          deterministic specialization/handoff
non-retained default topology:        Gate 12.3 two-model triage + specialist
historical experiment evidence:       preserved
```

The closeout must not claim capability execution, public/deployed agent runtime, AgentCore, MCP, A2A, runtime exposure, or production SLOs that Phase 12 did not prove.
