# Phase 11 — Gate 11.6: Single-Agent Baseline Closeout

_Date: 2026-09-07_

## Status

```text
Phase 11 gates 11.1-11.5:  COMPLETE / MERGED
Gate 11.6 documentation:   COMPLETE
exact-head CI:             PENDING
protected squash merge:    PENDING
Phase 11 closeout:         IN PROGRESS
```

Starting checkpoint:

```text
main: 8aeca3098b9269fcbf74f775a2ee135c987306dd
issue: #162 — OPEN
branch: docs/phase11-closeout
```

Gate 11.6 is documentation/architecture closeout only. It adds no application/runtime code, AWS resources, IAM permissions, provider/model calls, AgentCore, MCP, A2A, public runtime, runtime-exposure authority, or Governed LLM Gateway integration.

## Completed Phase 11 sequence

```text
Gate 11.1 — Capability Authorization Contract                COMPLETE / MERGED
Gate 11.2 — Typed Capability Bindings + Offline Executor      COMPLETE / MERGED
Gate 11.3 — Frozen Single-Agent Evaluation Fixture            COMPLETE / MERGED
Gate 11.4 — First Bounded Model Reasoning Baseline            COMPLETE / MERGED
Gate 11.5 — Measured Optimization Decision                    COMPLETE / MERGED — NO-CHANGE
Gate 11.6 — Phase 11 Closeout                                 IN PROGRESS
```

## Frozen contracts

```text
single-agent-authority:v1
single-agent-execution:v1
single-agent-evaluation:v1
single-agent-reasoning:v1
single-agent-reasoning-evaluation:v1
```

These contracts are the Phase 12 comparison baseline. Later phases may add new contracts but must not silently weaken the authority distinctions frozen here.

## Permanent authority path

```text
SingleAgentTask
 -> code-owned AgentCapability allowlist
 -> one bounded model reasoning invocation
 -> transient untrusted {decision, capability}
 -> deterministic reasoning-output parser
 -> AgentActionProposal
 -> deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
 -> STOP in the Gate 11.4 model-quality baseline
```

The `STOP` is intentional. The real reasoning baseline measures proposal quality and deterministic authorization without conflating it with capability execution.

Gate 11.2 independently freezes typed execution:

```text
AuthorizedAgentAction
 -> exact typed capability invocation
 -> deterministic capability/type match
 -> capability-specific executor port
 -> one bounded execution attempt
 -> typed downstream result admission
 -> content-addressed AgentCapabilityExecution
```

A valid proposal is not execution authority.

## Frozen capability surface

```text
structured_security_query
knowledge_guidance
hybrid_security_answer
public_repository_analysis
```

No generic tool registry or arbitrary argument envelope exists.

The model cannot author:

```text
arbitrary args / kwargs
SQL
URLs
shell commands
credentials
provider/model selection
retry/fallback policy
result data
runtime-exposure truth
```

## Gate 11.1 evidence

```text
issue #146:              CLOSED / COMPLETED
PR #147 final head:      12f63c54add74498478f2e48bc3835485fc3f5f5
Single-Agent CI:         34149074387 / run #5 / PASS
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest:                  16 passed in 0.09s
merge SHA:               641fc20d29cf1148d63b460948a08362158be113
```

Gate 11.1 froze `single-agent-authority:v1` and the distinction:

```text
agent action proposal != capability authorization
```

## Gate 11.2 evidence

```text
issue #149:              CLOSED / COMPLETED
PR #150 final head:      1f2dae3ece3b4a2dc9280575fd5a1a3c315751f4
Single-Agent CI:         34155862646 / run #11 / PASS
job:                     101847434766
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest:                  31 passed in 0.44s
merge SHA:               0fb70ace5bd544c6ef5f17f1030bdbcbeb8063b7
```

Gate 11.2 froze `single-agent-execution:v1`, exact typed capability bindings, one execution attempt, zero adaptive fallback, content-free failure categories, and result identity binding.

## Gate 11.3 evidence

```text
issue #153:              CLOSED / COMPLETED
PR #154 final head:      2dcc7abfc559a8a0b053278a68c926b5dc38d694
Single-Agent CI:         34163023511 / run #14 / PASS
job:                     101868535029
PR merge test commit:    96628ebc2bb5acffa6e27446de28e1073e9d6100
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest:                  37 passed in 0.54s
merge SHA:               b1b2f4e45005f1d55a017f4761f3b7e061f8a070
```

Gate 11.3 froze `single-agent-evaluation:v1`, a strict golden fixture, deterministic decomposed metrics, execution-bound scoring, and content-addressed report identity. It uses no LLM judge.

## Gate 11.4 real reasoning evidence

```text
issue #156:              CLOSED / COMPLETED
PR #157 final head:      2ec5b3804fa8c6454e1ea7d824b82d2db9113f91
Single-Agent CI:         34170308179 / run #37 / PASS
job:                     101889202476
PR merge test commit:    bd3802bf4003e5a447e5e104caad0a86cf8388ec
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest:                  56 passed in 0.43s
merge SHA:               8b41025facf4451490bf96223d69fbed19b4a00f
```

Frozen provider boundary:

```text
provider:        Amazon Bedrock Converse
region:          us-east-1
model/profile:   us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:       disabled
tools:           disabled
temperature:     0.0
maxTokens:       96
```

The first authenticated runtime attempt proved a concrete provider compatibility constraint: Bedrock structured outputs rejected JSON Schema `oneOf`. The provider schema was reduced to a flat closed object while ACT/non-null and ABSTAIN/null consistency remained deterministic application authority.

Historical first real baseline:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
```

Content identities:

```text
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Measured result:

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

Measured runtime evidence:

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

The cost is a token-price derivation from observed usage and contemporaneously verified Bedrock pricing, not AWS invoice reconciliation.

The six-case result is an acceptance-corpus result. It is not a universal correctness claim.

## Gate 11.5 measured optimization decision

```text
issue #159:              CLOSED / COMPLETED
PR #160 final head:      12c96dfa4bed1daa182adaddda52f4ab589ceeeb
Single-Agent CI:         34171028733 / run #42 / PASS
job:                     101891204255
PR merge test commit:    c74afd8683da27000394854779918faff2da7705
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest:                  56 passed in 0.43s
merge SHA:               14b2922239579e333f6cf331d96aa881eccd0423
optimization decision:   NO-CHANGE / NO-EXPERIMENT
additional model calls:  0
```

Rejected/deferred candidates:

```text
prompt compression             REJECT
model/profile switch           REJECT
prompt caching                 REJECT
retry/fallback expansion       REJECT
client warm-up/reuse           DEFER — cause/repeatability unproven
capability/tool expansion      REJECT
```

The absence of a justified optimization was recorded as an engineering result rather than treated as missing work.

## Evidence admission boundary

Phase 11 keeps raw model output transient. Canonical reasoning/evaluation evidence does not automatically persist arbitrary prompt text, provider prose, provider exception strings, or model-generated explanations.

Stable evidence identities, typed observations, request IDs, token usage, stop reason, latency, retry attempts, authorization outcomes, and deterministic scores are admitted through explicit contracts.

## What Phase 11 proves

```text
one real model reasoning boundary can remain proposal-only
capability allowlists remain code-owned
capability authorization remains deterministic
execution remains typed and independently bounded
result admission preserves exact downstream identity
evaluation remains deterministic and decomposed
real tokens/latency/retry evidence can be captured without granting authority
real inference cost can be derived from observed usage without inventing billing evidence
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

These remain future evidence requirements.

## AWS / IAM / runtime closeout

```text
new AWS resources in Gate 11.6:    0
new IAM roles/policies:             0
new model calls in Gate 11.6:       0
AgentCore runtime:                  0
MCP runtime:                        0
A2A runtime:                        0
public agent runtime:               0
runtime-exposure authority:         0
Governed LLM Gateway changes:       0
```

The Gate 11.4 real replay used the already-authorized local `opslens-bootstrap` IAM Identity Center profile. No credentials are persisted.

## Phase 12 entry criteria

Next planned phase after Gate 11.6 merges:

```text
Phase 12 — Multi-Agent Architecture
```

Entry rules:

```text
1. multi-agent complexity needs a concrete bounded responsibility
2. deterministic authorities frozen through Phase 11 remain code-owned
3. no generic tool registry or arbitrary executable argument surface
4. handoff identity, failure, and stopping semantics are explicit before implementation
5. comparative evaluation uses the Phase 11 single-agent baseline as reference
6. specialization is retained only when measured evidence justifies it
7. AgentCore, MCP, and A2A remain separate future decisions
8. Repository Risk != Runtime Exposure remains frozen
9. PR #89 remains deferred cross-project integration work
```

## Deferred Governed LLM Gateway integration

PR #89 remains open/draft and outside the Phase 11 closeout. Its consumer branch is not rebased, modified, merged, or closed by this gate.

## AIP-C01 learning map

Phase 11 provides practical evidence for:

- bounded structured model output;
- provider-neutral ports plus an Amazon Bedrock adapter;
- deterministic authorization around generative reasoning;
- deterministic evaluation instead of unnecessary model-as-judge evaluation;
- real inference token/latency/retry measurement;
- cost derivation from observed usage;
- least-privilege IAM decisions tied to a concrete runtime need;
- evaluation-before-optimization discipline;
- failure-path learning from the Bedrock structured-output schema constraint;
- explicit separation between managed runtime technology and application authority.

## Closeout checklist

```text
[x] Gates 11.1-11.5 merged
[x] five Phase 11 contracts enumerated
[x] authority boundary frozen
[x] typed execution boundary frozen
[x] evaluation boundary frozen
[x] first real reasoning baseline preserved
[x] token/latency/retry/cost evidence preserved
[x] Gate 11.5 NO-CHANGE decision preserved
[x] proof boundary enumerated
[x] non-claims enumerated
[x] AWS/IAM/runtime non-expansion frozen
[x] Phase 12 entry criteria defined
[x] closeout ADR added
[x] closeout lab added
[ ] public/current docs synchronized
[ ] exact-head CI PASS
[ ] PR review state clean
[ ] protected squash merge
[ ] issue #162 CLOSED / COMPLETED
[ ] post-merge main/state verified
```

## Architecture record

```text
docs/adr/0041-phase11-single-agent-baseline-closeout.md
```
