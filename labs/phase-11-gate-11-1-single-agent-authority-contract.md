# Phase 11 — Gate 11.1: Bounded Single-Agent Capability Authority

_Date: 2026-09-07_

## Status

**COMPLETE / MERGED**

Starting main:

```text
184a0b42c0ad0125bb692d8f86ae02b2bc76ff13
```

Final merged checkpoint:

```text
issue:               #146 CLOSED / COMPLETED
PR:                  #147 MERGED
final PR head:       12f63c54add74498478f2e48bc3835485fc3f5f5
merge SHA:           641fc20d29cf1148d63b460948a08362158be113
Single-Agent CI:     34149074387 / run #5 / PASS
```

## Goal

Start the OpsLens Single-Agent Baseline by freezing capability-selection authority before introducing model variability or execution.

The gate intentionally stops before a traditional agent loop:

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

Existing project rule:

```text
Agents reason. Code verifies evidence.
```

A future LLM may propose an action. It will not own action authorization.

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

These values identify governed capability classes only. They do not expose provider, shell, browser, file-system, network, SQL, or generic tool authority.

## Task admission

`SingleAgentTask` binds:

```text
exact bounded task text
+ canonical code-owned capability allowlist
+ single-agent-authority:v1
 -> SHA-256 task identity
```

Properties:

- capability order is canonicalized before hashing;
- empty capability sets fail closed;
- duplicate capabilities fail closed;
- raw strings masquerading as `AgentCapability` fail closed;
- task size is measured in UTF-8 bytes;
- changing task text or capability authority changes task identity.

Task text remains untrusted content. Its presence never grants executable authority.

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

This is an authority boundary, not merely schema hygiene.

## Authorization

`authorize_agent_action(task, proposal)` verifies the exact task binding and code-owned allowlist.

### Allowlisted ACT

```text
valid proposal
+ exact task identity
+ proposed capability in allowlist
 -> AuthorizedAgentAction
```

The authorized action is content-addressed over task identity, proposal identity, capability, and contract version.

### Out-of-allowlist ACT

A structurally valid proposal selecting a known but unauthorized capability fails closed at deterministic authorization.

```text
proposal validity != authorization
```

### ABSTAIN

Abstention is a first-class safe outcome:

```text
AgentAbstention
```

It is content-addressed and contains no capability authority. There is no implicit fallback action.

## Tamper resistance

The contract rejects forged/mismatched identities for:

```text
SingleAgentTask
AgentActionProposal
AuthorizedAgentAction
AgentAbstention
```

A proposal bound to one task cannot be replayed as authority for another task even when both tasks expose the same capability class.

## Exact-head executable validation

Final PR head:

```text
12f63c54add74498478f2e48bc3835485fc3f5f5
```

GitHub Actions evidence:

```text
workflow: Single-Agent CI
run:      34149074387 / run #5
job:      101827298939
result:   SUCCESS
```

Quality evidence:

```text
uv lock --check: PASS
Ruff:            PASS
Pyright strict:  0 errors / 0 warnings / 0 informations
pytest:           16 passed in 0.09s
```

The final regression set explicitly covers forged `AuthorizedAgentAction` and `AgentAbstention` identity rejection in addition to the original task/proposal tamper checks.

The workflow checkout validated PR merge commit:

```text
6c6e5384783e8b8dc92bc76c821ddf9d3bcbe6be
```

against base main:

```text
184a0b42c0ad0125bb692d8f86ae02b2bc76ff13
```

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
- forged task/proposal/action/abstention identities are rejected;
- generic tool/argument/provider/SQL/command fields do not exist.

## Architecture record

```text
docs/adr/0036-bounded-single-agent-capability-authorization.md
```

The ADR freezes the architecture before any reasoning model or agent framework is selected.

## Observability boundary

Gate 11.1 does **not** add agent steps to `operational-telemetry:v1`.

Phase 10 principles still apply:

```text
content minimization
low cardinality
bounded failure categories
telemetry != business/route authority
```

Agent-step semantics require a separately versioned operational contract if they are introduced later.

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

Gate 11.1 demonstrates why agentic architecture starts with authorization rather than a framework:

- model output is proposal data;
- allowlists are deterministic application authority;
- structured output does not imply authorization;
- abstention is an explicit safe outcome;
- IAM should follow concrete adapters/runtime responsibilities;
- provider-neutral contracts enable later Bedrock/AgentCore comparison without changing authority semantics;
- offline failure tests remove model nondeterminism while security boundaries are established.

## Phase 11 sequence after merge

```text
Gate 11.1 — Capability Authorization Contract                COMPLETE / MERGED
Gate 11.2 — Typed Capability Bindings + Offline Executor      NEXT
Gate 11.3 — Frozen Single-Agent Evaluation Fixture            BLOCKED
Gate 11.4 — First Bounded Model Reasoning Baseline            BLOCKED
Gate 11.5 — Measured Optimization Decision                    BLOCKED
Gate 11.6 — Phase 11 Closeout                                 BLOCKED
```

Gate 11.2 is now authorized because Gate 11.1 has merged and the authoritative state-sync records the completed boundary.

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
[x] ADR 0036 recorded
[x] Gate 11.1 lab recorded
[x] final exact-head Single-Agent CI green
[x] PR #147 ready / mergeable
[x] protected squash merge
[x] issue #146 CLOSED / COMPLETED
[x] postmerge state sync
```
