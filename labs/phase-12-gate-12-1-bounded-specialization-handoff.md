# Phase 12 — Gate 12.1: Bounded Specialization Handoff Contract

_Date: 2026-09-07_

## Status

```text
Phase 11 reference:          COMPLETE / FROZEN
handoff contract:            IMPLEMENTED
specialization mapping:      IMPLEMENTED
source allowlist narrowing:  IMPLEMENTED
loop prevention:             IMPLEMENTED
real model calls:            0
capability executions:       0
exact-head CI:               PENDING
Gate 12.1 completion:        PENDING CI / MERGE
```

Starting checkpoint:

```text
main:   72bee85d06f50b736f0ab6045f7c8a8a135b7a79
issue:  #165
branch: feat/phase12-bounded-specialization-handoff
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

Gate 11.5 also remains `NO-CHANGE / NO-EXPERIMENT`. Gate 12.1 does not reinterpret that result as a hidden quality gap.

## New frozen contract

```text
multi-agent-handoff:v1
```

Bounds:

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

A future triage model would propose only one specialization. It would not select a capability or provide executable arguments.

Deterministic code then intersects the selected specialization scope with the already-admitted source task allowlist.

For a source task containing all four Phase 11 capabilities, the maximum future specialist scope is therefore reduced from four to two.

This is recorded as:

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

This prevents the handoff channel from becoming a generic inter-agent instruction bus.

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

The gate introduces content-addressed identities for:

```text
MultiAgentHandoffProposal
AuthorizedMultiAgentHandoff
MultiAgentHandoffAbstention
```

`AuthorizedMultiAgentHandoff` binds:

```text
source task identity
proposal identity
target specialization
target task identity
narrowed capability tuple
```

It does not persist model-authored reasoning text or arbitrary handoff messages.

## Deterministic scope rules

### Full source scope -> evidence specialist

```text
source allowed:
  hybrid_security_answer
  knowledge_guidance
  public_repository_analysis
  structured_security_query

specialization:
  EVIDENCE_ANALYSIS

target allowed:
  public_repository_analysis
  structured_security_query
```

### Full source scope -> guidance specialist

```text
specialization:
  GUIDANCE_SYNTHESIS

target allowed:
  hybrid_security_answer
  knowledge_guidance
```

### Restricted source scope

If source authority contains only:

```text
structured_security_query
```

then `EVIDENCE_ANALYSIS` produces a target containing only:

```text
structured_security_query
```

The specialization mapping can narrow source authority but cannot broaden it.

### Empty intersection

If the source task allows only:

```text
knowledge_guidance
```

and an untrusted proposal requests:

```text
EVIDENCE_ANALYSIS
```

handoff admission raises stable `MultiAgentHandoffAuthorizationError` before a specialist task can exist.

## Tests

The Gate 12.1 unit slice covers:

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

No fake model or executor is required because Gate 12.1 is a deterministic handoff authority slice.

## Dedicated CI

```text
.github/workflows/multi-agent-ci.yml
```

The workflow validates only the new bounded multi-agent slice:

```text
uv lock --check
uv sync --frozen
Ruff
Pyright strict
pytest tests/unit/multi_agent
```

It has no AWS credentials or model invocation step.

## Failure semantics

```text
structural contract failure -> MultiAgentHandoffValidationError
empty authorized scope      -> MultiAgentHandoffAuthorizationError
explicit abstention         -> MultiAgentHandoffAbstention
```

Provider exception taxonomy is intentionally absent because no provider exists in this gate.

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

These require later evidence.

## Gate 12.2 entry boundary

A real two-model experiment is not automatically authorized by Gate 12.1 implementation.

Before a model adapter is added, Gate 12.2 must freeze a comparative evaluation contract against the Phase 11 reference. At minimum it must measure:

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

PR #89 remains deferred cross-project Governed LLM Gateway work and is untouched by Gate 12.1.

## Architecture record

```text
docs/adr/0042-bounded-multi-agent-specialization-handoff.md
```
