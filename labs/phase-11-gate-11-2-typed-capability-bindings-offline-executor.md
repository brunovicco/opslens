# Phase 11 — Gate 11.2: Typed Capability Bindings + Offline Executor

_Date: 2026-09-07_

## Status

**IMPLEMENTED — final exact-head CI and protected merge pending.**

Starting main:

```text
46346ab68737b8a866c85563f3804adbdccc1a92
```

Tracking:

```text
issue:  #149
branch: feat/phase11-typed-capability-execution
PR:     #150 (draft)
```

## Goal

Continue the Phase 11 single-agent baseline without introducing a reasoning model, generic tool registry, or managed runtime.

Gate 11.1 already proved:

```text
agent action proposal != capability authorization != execution result
```

Gate 11.2 adds the missing deterministic execution boundary:

```text
AuthorizedAgentAction
 -> typed capability invocation
 -> deterministic action/capability binding
 -> one explicit executor port call
 -> typed downstream result admission
 -> AgentCapabilityExecution
 -> STOP
```

## Frozen execution contract

```text
single-agent-execution:v1
```

This is intentionally separate from:

```text
single-agent-authority:v1
```

Limits:

```text
max executions per call: 1
execution retries:        0
adaptive fallbacks:       0
real reasoning calls:     0
```

## Exact capability bindings

The implementation has no generic `tool_name` or arbitrary argument bag.

The four bindings are explicit:

```text
structured_security_query
 -> StructuredSecurityQueryInvocation
 -> SemanticQuery
 -> StructuredSecurityQueryResultBinding

knowledge_guidance
 -> KnowledgeGuidanceInvocation
 -> SynthesisRequest
 -> SynthesisResult

hybrid_security_answer
 -> HybridSecurityAnswerInvocation
 -> HybridSynthesisRequest
 -> HybridSynthesisResult

public_repository_analysis
 -> PublicRepositoryAnalysisInvocation
 -> PublicAnalysisRequest
 -> PublicAnalysisAdmissionHandoff
```

Each invocation includes the exact Gate 11.1 `AuthorizedAgentAction` and validates that the action capability matches the invocation type before any executor call can happen.

## Invocation identity

Typed invocations are content-addressed over:

```text
action_id
capability
single-agent-execution:v1
capability-specific input identity
```

Capability-specific identities are intentionally narrow:

```text
structured -> canonical SemanticQuery semantics
knowledge  -> exact SynthesisRequest.request_sha256
hybrid     -> exact HybridSynthesisRequest.request_sha256
public     -> exact PublicAnalysisRequest request_id + request_sha256
```

Equivalent semantics produce equivalent invocation identities. Changed query/request semantics change identity.

## Structured result binding

The existing `AthenaQueryResult` contains execution evidence but not the exact originating `SemanticQuery` identity.

Gate 11.2 therefore adds:

```text
StructuredSecurityQueryResultBinding
```

which binds the exact result to:

```text
invocation_sha256
```

before an `AgentCapabilityExecution` may be created.

A structured result produced for another typed invocation is rejected with `result_contract`.

## Knowledge and hybrid result admission

These downstream result types already contain deterministic request identities.

The executor boundary verifies:

```text
SynthesisResult.request_sha256
 == KnowledgeGuidanceInvocation.request.request_sha256
```

and:

```text
HybridSynthesisResult.request_sha256
 == HybridSecurityAnswerInvocation.request.request_sha256
```

A result for another request is not rebound to the current agent invocation.

## Public-analysis result admission

The public capability accepts only a `PublicAnalysisAdmissionHandoff` that remains bound to the exact public request in the invocation.

Both identities are checked:

```text
request_id
request_sha256
```

The existing Phase 9 request/source/route/handoff authority remains authoritative.

## Closed executor ports

The application boundary defines:

```text
StructuredSecurityQueryExecutor
KnowledgeGuidanceExecutor
HybridSecurityAnswerExecutor
PublicRepositoryAnalysisExecutor
```

and injects them through `AgentCapabilityExecutors`.

This is a closed dependency set, not a runtime registry. Caller-provided strings cannot select a new tool or executor.

## Failure semantics

The bounded failure taxonomy is:

```text
executor_failure
result_contract
```

The downstream exception message is not copied into the public execution error or admitted execution evidence.

Executor failure behavior is:

```text
one attempted call
 -> content-free executor_failure
 -> STOP
```

There is no retry, alternate capability, fallback provider, or implicit second execution.

## Successful execution evidence

`AgentCapabilityExecution` binds:

```text
action_id
capability
invocation_id
downstream_result_sha256
single-agent-execution:v1
```

and exposes a deterministic content-addressed execution identity.

This is execution evidence. It does not make agent reasoning authoritative over the downstream business/security truth.

## Regression coverage

The current tests prove:

- execution has a separate frozen versioned contract;
- one execution / zero retry / zero adaptive fallback limits;
- equivalent structured query semantics produce the same invocation identity;
- changed query semantics change invocation identity;
- capability mismatch between authorization and invocation fails before execution;
- forged invocation identities fail closed;
- forged execution identities fail closed;
- structured execution calls exactly one executor once;
- downstream exception text does not enter the bounded execution failure;
- structured result bound to another invocation is rejected;
- knowledge result from another synthesis request is rejected;
- hybrid result from another synthesis request is rejected;
- public handoff from another public request is rejected;
- all four happy-path capability bindings produce execution evidence;
- arbitrary runtime objects cannot enter typed dispatch;
- the frozen Gate 11.1 proposal still has no generic args/tool/URL/SQL/provider/model/retry surface.

All tests use injected fakes or frozen local fixtures. Third-party repository code is never executed.

## CI history

### Initial implementation

Head:

```text
7f573c1021c7608c242b7468199b145a96d542f8
```

Single-Agent CI:

```text
run: 34150844198 / run #6
result: FAILURE at Ruff
```

The failure was mechanical lint debt only:

```text
D107 missing __init__ docstring
RUF022 __all__ ordering
UP040 Python 3.13 type-alias syntax
E501 line length
D103 test docstrings
```

Pyright and pytest were skipped by that failed job, so this run is not executable-quality evidence.

### First green executable slice

Head:

```text
e0e2da20624619f7e29ad933002cd5cb0b65d1ec
```

Single-Agent CI:

```text
run: 34155372006 / run #7
result: SUCCESS
Ruff: PASS
Pyright strict: 0 errors / 0 warnings / 0 informations
pytest: 27 passed in 0.41s
```

### Hardened result-binding baseline

Head:

```text
8047cfa884879d246c54245c195ca70e66c6e9da
```

Single-Agent CI:

```text
run: 34155612755 / run #9
job: 101846689640
result: SUCCESS
checkout PR merge commit: c384e125c18a808fdd8ff93de11144ac56ddb7f3
uv lock --check: PASS
Ruff: PASS
Pyright strict: 0 errors / 0 warnings / 0 informations
pytest: 31 passed in 0.47s
```

This is the latest executable-quality evidence before ADR/lab documentation changes. The final PR head must be revalidated before merge.

## Authority boundary

Gate 11.2 does not move these authorities into agent execution:

```text
SemanticQuery validation / SQL compilation
vulnerability applicability
Risk Policy
knowledge evidence admission
hybrid route/evidence/citation authority
public request/source/route/handoff authority
runtime-exposure authority
telemetry authority
```

The agent layer receives only already-authorized actions and already-admitted typed capability inputs.

## Observability boundary

Gate 11.2 does not mutate `operational-telemetry:v1`.

Phase 10 remains frozen at the five governed public-analysis stages. Agent execution needs a separately versioned telemetry contract if introduced later.

Permanent rules remain:

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry evidence != execution authority
```

## AWS / IAM / runtime boundary

```text
real reasoning model calls:   0
real AWS calls:               0
new AWS resources:            0
new IAM roles/policies:       0
public runtime:               0
Bedrock Agents:               0
AgentCore runtime:            0
MCP:                          0
A2A:                          0
runtime-exposure authority:   0
```

No claim is made that an AWS API was called merely because existing OpsLens capability contracts can have AWS-backed adapters in other phases.

PR #89 remains open/draft and untouched/deferred.

## Cost boundary

No real model/provider/AWS runtime execution occurs in this gate, therefore runtime cost remains unmeasured.

```text
no real calls in Gate 11.2 != zero future agent cost
```

A future real single-agent baseline must measure reasoning calls, capability calls, latency, failures/retries, and provider/runtime cost separately.

## AIP-C01 learning notes

This gate exercises several certification-relevant engineering decisions:

- managed tool use does not replace deterministic authorization;
- structured arguments still require application-owned admission;
- least privilege begins with narrowing the capability contract before adding IAM;
- execution requests and results need explicit provenance and identity binding;
- retry/fallback policy is part of the safety contract, not an incidental SDK setting;
- provider-neutral ports allow later Bedrock/AgentCore choices without moving authority;
- deterministic offline evaluation is useful before model and managed-runtime variability is introduced.

## Proposed Phase 11 sequence

```text
Gate 11.1 — Capability Authorization Contract                COMPLETE / MERGED
Gate 11.2 — Typed Capability Bindings + Offline Executor      CURRENT
Gate 11.3 — Frozen Single-Agent Evaluation Fixture            BLOCKED
Gate 11.4 — First Bounded Model Reasoning Baseline            BLOCKED
Gate 11.5 — Measured Optimization Decision                    BLOCKED
Gate 11.6 — Phase 11 Closeout                                 BLOCKED
```

Gate 11.3 must freeze cases and metrics before the first real reasoning model call in Gate 11.4.

## Exit checklist

```text
[x] issue #149 opened
[x] branch created from exact post-Gate-11.1 state-sync main
[x] single-agent-execution:v1 implemented
[x] four closed typed invocation contracts implemented
[x] deterministic invocation identity implemented
[x] structured query/result binding implemented
[x] knowledge request/result identity admission implemented
[x] hybrid request/result identity admission implemented
[x] public request/handoff identity admission implemented
[x] explicit capability-specific executor ports implemented
[x] one-execution / zero-retry / zero-fallback limits frozen
[x] content-free failure taxonomy implemented
[x] downstream result rebinding regressions implemented
[x] Single-Agent CI green on hardened executable head
[x] ADR 0037 recorded
[x] Gate 11.2 lab recorded
[ ] final exact-head Single-Agent CI green after docs
[ ] PR #150 ready / mergeable
[ ] protected squash merge
[ ] issue #149 CLOSED / COMPLETED
[ ] postmerge state sync
```
