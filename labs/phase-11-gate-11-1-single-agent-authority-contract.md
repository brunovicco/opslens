# Phase 11 — Gate 11.1: Bounded Single-Agent Capability Authority

_Date: 2026-09-07_

## Status

**IMPLEMENTED — final exact-head CI and protected merge pending.**

Starting main:

```text
184a0b42c0ad0125bb692d8f86ae02b2bc76ff13
```

Tracking:

```text
issue:  #146
branch: feat/phase11-single-agent-authority
PR:     #147 (draft)
```

## Goal

Start the OpsLens Single-Agent Baseline by freezing capability-selection authority before introducing model variability or execution.

The gate is intentionally smaller than a traditional agent loop:

```text
bounded task
 -> code-owned capability allowlist
 -> untrusted one-step proposal
 -> deterministic authorization
 -> AuthorizedAgentAction | AgentAbstention
 -> STOP
```

No capability execution occurs.

## Permanent distinction

```text
agent action proposal != capability authorization != execution result
```

And the existing OpsLens rule remains:

```text
Agents reason. Code verifies evidence.
```

A future LLM may propose an action. It will not own the action's authorization.

## Frozen contract

```text
single-agent-authority:v1
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

## Initial capability enum

```text
structured_security_query
knowledge_guidance
hybrid_security_answer
public_repository_analysis
```

The enum identifies governed capability classes only. It does not expose a direct provider, shell, browser, file system, network, SQL, or generic tool API.

## Task admission

`SingleAgentTask` binds:

```text
exact bounded task text
+ canonical code-owned capability allowlist
+ single-agent-authority:v1
 -> SHA-256 task identity
```

Important properties:

- capability order is canonicalized before hashing;
- empty capability sets fail closed;
- duplicate capabilities fail closed;
- raw strings masquerading as `AgentCapability` fail closed;
- task size is measured in UTF-8 bytes;
- changing text or capability authority changes task identity.

The task text remains untrusted content. Its presence in a task does not grant executable authority.

## Proposal admission

`AgentActionProposal` contains only:

```text
task_id
decision
capability | null
proposal_sha256
proposal_id
```

Decision consistency:

```text
act      -> exactly one typed capability
abstain  -> capability must be null
```

A proposal has no generic argument bag.

Explicitly absent:

```text
args
kwargs
tool_name
url
sql
command
provider
model_id
credentials
retry/fallback policy
```

This is a central authority boundary, not merely input validation.

## Authorization

`authorize_agent_action(task, proposal)` verifies the exact task binding and code-owned allowlist.

### Allowlisted ACT

```text
valid proposal
+ exact task identity
+ proposed capability in allowlist
 -> AuthorizedAgentAction
```

The action is content-addressed over:

```text
task_id
proposal_id
capability
contract version
```

It is authorization evidence only. Gate 11.1 still executes zero capabilities.

### Out-of-allowlist ACT

A proposal selecting a known but unauthorized capability remains structurally valid as a proposal, then fails closed at deterministic authorization.

This proves:

```text
proposal validity != authorization
```

### ABSTAIN

Abstention is a valid first-class outcome:

```text
AgentAbstention
```

It is content-addressed and contains no capability field. There is no implicit fallback action.

## Tamper resistance

Direct construction with mismatched SHA-256 or content-addressed IDs is rejected for tasks and proposals. Authorized actions and abstentions also validate their own deterministic identity contracts.

A proposal tied to one admitted task cannot be replayed as authority for another task even when both allow the same capability.

## Initial executable validation

The first implementation head was:

```text
c401368908e680af48b42d846b795a9c5c28399c
```

Single-Agent CI:

```text
run: 34148793155 / run #1
job: 101826450390
result: SUCCESS
```

Quality evidence:

```text
uv lock --check: PASS
Ruff:            PASS
Pyright strict:  0 errors / 0 warnings / 0 informations
pytest:           14 passed
```

This validation covered the executable authority contract before the ADR/lab documentation commits. The final PR head must be revalidated before merge.

## Regression coverage

Tests prove:

- exact contract/budget constants;
- canonical capability ordering;
- deterministic identity for identical semantics;
- task identity changes for text/authority changes;
- UTF-8 byte limit behavior with multibyte text;
- empty/duplicate/raw capability surfaces rejected;
- allowlisted ACT authorizes deterministically;
- out-of-allowlist ACT fails closed;
- ABSTAIN creates no capability authority;
- ACT/ABSTAIN inconsistency fails before authorization;
- raw decision strings fail runtime type admission;
- mismatched task identity is denied;
- forged task/proposal identity is rejected;
- generic tool/argument/provider/SQL/command fields do not exist.

## Architecture boundary

ADR:

```text
docs/adr/0036-bounded-single-agent-capability-authorization.md
```

The ADR freezes the architecture before any model or agent framework is selected.

## Observability boundary

Gate 11.1 does **not** add agent steps to `operational-telemetry:v1`.

Phase 10 principles still apply:

```text
content minimization
low cardinality
bounded failure categories
telemetry != business/route authority
```

But agent-step semantics require a separately versioned operational contract if/when they are introduced. Mutating the five frozen public-analysis stages would make the telemetry contract ambiguous.

## IAM / runtime boundary

```text
real model calls:              0
real capability calls:         0
AWS calls:                     0
new AWS resources:             0
new IAM roles/policies:        0
Bedrock Agents:                0
AgentCore runtime:             0
MCP:                           0
A2A:                           0
```

PR #89 remains untouched/deferred.

## Cost boundary

No runtime/model/capability cost is measured because none executes in this gate.

```text
zero calls in this gate != zero future agent cost
```

A later real baseline must measure model turns, capability calls, latency, retries, and provider/runtime cost separately.

## AIP-C01 learning notes

Gate 11.1 is a concrete example of why agentic architecture starts with authorization rather than with a framework:

- model output is proposal data;
- allowlists are deterministic application authority;
- structured output does not imply authorization;
- abstention is an explicit safe outcome;
- IAM should follow concrete adapters/runtime responsibilities;
- provider-neutral contracts enable later Bedrock/AgentCore comparison without changing authority semantics;
- offline failure tests remove model nondeterminism while security boundaries are being established.

## Proposed Phase 11 sequence

```text
Gate 11.1 — Capability Authorization Contract                CURRENT
Gate 11.2 — Typed Capability Bindings + Offline Executor      BLOCKED
Gate 11.3 — Frozen Single-Agent Evaluation Fixture            BLOCKED
Gate 11.4 — First Bounded Model Reasoning Baseline            BLOCKED
Gate 11.5 — Measured Optimization Decision                    BLOCKED
Gate 11.6 — Phase 11 Closeout                                 BLOCKED
```

The sequence intentionally creates execution/result authority and evaluation fixtures before a real reasoning model is admitted.

## Exit checklist

```text
[x] issue #146 opened
[x] branch created from exact Phase 10 checkpoint
[x] single-agent-authority:v1 implemented
[x] closed capability enum implemented
[x] deterministic task identity implemented
[x] proposal/authorization separation implemented
[x] explicit abstention implemented
[x] zero execution/retry budget frozen
[x] strict regression suite implemented
[x] dedicated Single-Agent CI created
[x] initial executable CI green
[x] ADR 0036 recorded
[x] Gate 11.1 lab recorded
[ ] final exact-head Single-Agent CI green
[ ] PR #147 ready / mergeable
[ ] protected squash merge
[ ] issue #146 CLOSED / COMPLETED
[ ] postmerge state sync
```
