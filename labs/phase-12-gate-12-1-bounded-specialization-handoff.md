# Phase 12 — Gate 12.1: Bounded Specialization Handoff Contract

_Date: 2026-09-07_

## Status

```text
Phase 11 reference:          COMPLETE / FROZEN
handoff contract:            COMPLETE / MERGED
specialization mapping:      COMPLETE / MERGED
source allowlist narrowing:  COMPLETE / MERGED
loop prevention:             COMPLETE / MERGED
real model calls:            0
capability executions:       0
exact-head CI:               PASS
Gate 12.1 completion:        COMPLETE / MERGED
state synchronization:       IN PROGRESS
```

Merged checkpoint:

```text
issue:  #165
PR:     #166
head:   567cdbde81f058d9545328ca78b718c24d79c9fb
merge:  eceed76a6cfc5d7e28e88dfdc503b4863b526ba0
```

## Objective

Create the minimum deterministic authority required to evaluate one multi-agent specialization hypothesis later, without introducing another model call, graph framework, execution authority, AWS resource, or managed agent runtime.

The Gate 12.1 question is not:

> How do we add more agents?

It is:

> What exact handoff authority must exist before adding another reasoning step can be evaluated safely?

## Phase 11 reference

The first real single-agent reasoning baseline remains the comparison reference:

```text
quality:                    6/6
bounds compliance:          6/6
SDK retries:                0
capability executions:      0
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
derived six-case cost:      USD 0.0041921
```

Historical evidence remains unchanged:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Gate 11.5 remains `NO-CHANGE / NO-EXPERIMENT`. Gate 12.1 does not reinterpret that result as a hidden quality gap.

## Frozen contract

```text
multi-agent-handoff:v1
```

Hard bounds:

```text
maximum handoffs per task:       1
maximum specialist capabilities: 2
real model invocations:          0
capability executions:           0
adaptive retry/fallback:         0
```

## Specialization hypothesis

Code-owned partition:

```text
EVIDENCE_ANALYSIS
 -> public_repository_analysis
 -> structured_security_query

GUIDANCE_SYNTHESIS
 -> hybrid_security_answer
 -> knowledge_guidance
```

A future triage model may propose only one specialization. It does not select a capability or provide executable arguments.

Deterministic code intersects the selected specialization scope with the already-admitted source task allowlist. For a source task containing all four Phase 11 capabilities, the maximum specialist scope is reduced from four to two.

This is frozen as:

```text
reasoning-surface narrowing != runtime privilege reduction
```

No model in Phase 11 or Gate 12.1 has capability execution authority.

## Handoff authority boundary

```text
SingleAgentTask
 -> TriageAgentTask
 -> untrusted MultiAgentHandoffProposal
 -> deterministic source-task identity check
 -> deterministic specialization scope lookup
 -> deterministic intersection with source allowed_capabilities
 -> empty intersection? FAIL CLOSED
 -> narrowed SingleAgentTask
 -> content-addressed AuthorizedMultiAgentHandoff
 -> SpecialistAgentTask
 -> STOP
```

Explicit abstention:

```text
MultiAgentHandoffProposal(decision=ABSTAIN)
 -> content-addressed MultiAgentHandoffAbstention
 -> no SpecialistAgentTask
 -> STOP
```

## Proposal surface

```text
source_task_id
decision
target_specialization
proposal_sha256
proposal_id
```

Explicitly absent:

```text
capability
arbitrary message/context
args / kwargs
SQL
URL
shell command
credential
provider/model selection
retry/fallback policy
execution result
```

The handoff channel therefore does not become a generic inter-agent instruction bus.

## One-way role boundary

The application API accepts:

```text
TriageAgentTask
```

and may produce:

```text
SpecialistAgentTask
```

`SpecialistAgentTask` is not an accepted source type for the handoff service. This structurally prevents recursive delegation/cycles in v1 without requiring a graph runtime or probabilistic loop detection.

## Content-addressed evidence

The gate freezes content-addressed identities for:

```text
MultiAgentHandoffProposal
AuthorizedMultiAgentHandoff
MultiAgentHandoffAbstention
```

`AuthorizedMultiAgentHandoff` binds source task identity, proposal identity, target specialization, target task identity, and the narrowed capability tuple. It does not persist model-authored reasoning text or arbitrary handoff messages.

## Deterministic scope rules

Full source scope to evidence specialist:

```text
source allowed: 4 capabilities
specialization: EVIDENCE_ANALYSIS
target allowed:
  public_repository_analysis
  structured_security_query
```

Full source scope to guidance specialist:

```text
source allowed: 4 capabilities
specialization: GUIDANCE_SYNTHESIS
target allowed:
  hybrid_security_answer
  knowledge_guidance
```

Restricted source authority is preserved by intersection. If the source allows only `structured_security_query`, the evidence specialist receives only that capability.

If the specialization/source intersection is empty, admission fails closed with stable `MultiAgentHandoffAuthorizationError` before a specialist task can exist.

## Tests

Gate 12.1 covers:

```text
contract version and hard bounds
closed specialization mapping
4 -> 2 evidence-scope narrowing
4 -> 2 guidance-scope narrowing
source allowlist intersection
empty-intersection failure
source-task mismatch failure
explicit abstention
forged proposal identity rejection
one-way type boundary / no specialist re-handoff
```

The first CI attempt exposed five unnecessary `cast()` calls under strict Pyright. Those were removed rather than suppressed. No `type: ignore` was introduced.

## Exact-head validation

Validated PR head:

```text
567cdbde81f058d9545328ca78b718c24d79c9fb
```

PR merge test commit:

```text
b1e40ea858726c0672601db8c51c353ffbcc03ae
```

Multi-Agent CI:

```text
run:               34172909750 / run #3 / PASS
job:               101896544229
uv lock --check:   PASS
Ruff:              PASS
Pyright strict:    0 errors / 0 warnings / 0 informations
pytest:            10 passed in 0.39s
```

Phase 11 regression validation on the same exact PR head:

```text
Single-Agent CI:   34172909748 / run #48 / PASS
job:               101896544157
entrypoint smoke:  PASS
Ruff:              PASS
Pyright strict:    0 errors / 0 warnings / 0 informations
pytest:            56 passed in 0.44s
```

The final workflow-filter correction also prevents Phase 12 ADRs from matching the Phase 11 `docs/adr/004*.md` path filter; Single-Agent CI is now scoped explicitly to ADRs 0036–0041.

## Protected merge

PR #166 was marked ready only after the exact head above had green Multi-Agent and Single-Agent validation and no unresolved inline review threads.

Protected squash merge used the exact expected head SHA:

```text
expected head: 567cdbde81f058d9545328ca78b718c24d79c9fb
merge SHA:     eceed76a6cfc5d7e28e88dfdc503b4863b526ba0
```

## AWS / IAM / runtime boundary

```text
real model calls:               0
real AWS calls:                 0
new AWS resources:              0
new IAM roles/policies:         0
capability executions:          0
AgentCore runtime:              0
MCP:                            0
A2A:                            0
public agent runtime:           0
runtime-exposure authority:     0
Governed LLM Gateway changes:   0
```

No runtime cost is measured because Gate 12.1 performs no runtime/model call. Absence of a call is not presented as a measured zero inference price.

## What Gate 12.1 proves

```text
handoff proposal can remain untrusted
specialization scope can remain code-owned
source capability authority cannot be broadened by handoff
specialist capability surface is deterministically bounded to <= 2
empty specialization/source intersection fails closed
handoff evidence can be content-addressed without free-form context
v1 delegation can be structurally one-way without a graph runtime
```

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
capability execution through multi-agent flow
AgentCore/MCP/A2A behavior
```

## Gate 12.2 entry boundary

A real two-model experiment is not automatically authorized by Gate 12.1.

Before a second model adapter/call is allowed, Gate 12.2 must freeze a deterministic comparative evaluation contract against the Phase 11 reference. At minimum it must measure:

```text
routing/proposal quality
bounds compliance
specialist capability-surface width
model invocation count
tokens
provider/client latency
SDK retries
inference cost
capability executions
```

The topology must be rejected if the measured specialization benefit does not justify its extra calls, latency, cost, complexity, or failure surface.

## Deferred integration

PR #89 remains deferred cross-project Governed LLM Gateway work and remains unchanged at:

```text
3781831795d500b05fa4bc602d50f376b4b1539f
```

## Architecture record

```text
docs/adr/0042-bounded-multi-agent-specialization-handoff.md
```
