# ADR 0039 — Introduce bounded single-agent model reasoning without transferring authority

- Status: Accepted
- Date: 2026-09-07
- Phase: 11 — Single-Agent Baseline
- Gate: 11.4 — First Bounded Model Reasoning Baseline

## Context

Gate 11.1 froze deterministic capability authorization as `single-agent-authority:v1`.
Gate 11.2 froze typed invocation/result admission as `single-agent-execution:v1`.
Gate 11.3 froze deterministic offline evaluation as `single-agent-evaluation:v1`.

OpsLens can therefore admit a task, authorize a bounded proposal, execute only exact typed
capability bindings, and evaluate those deterministic boundaries without a reasoning model.
The remaining Phase 11 gap is to measure whether one real model can make a useful bounded
capability-selection proposal without acquiring any of those deterministic authorities.

Introducing model reasoning directly into capability execution would combine two independent
questions:

1. did the model select the correct capability or abstain?;
2. did the selected capability execute and return an admissible result?

Gate 11.4 isolates the first question.

## Decision

Introduce a separate provider-neutral reasoning contract:

```text
single-agent-reasoning:v1
```

The bounded path is:

```text
SingleAgentTask
 -> one reasoning-model invocation
 -> transient untrusted structured output
 -> deterministic output parsing
 -> existing AgentActionProposal
 -> existing authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
 -> STOP
```

The final `STOP` is mandatory for this gate. Gate 11.4 does not execute a capability during the
first real model-quality baseline.

### Model output surface

The model may emit only:

```json
{
  "decision": "act | abstain",
  "capability": "closed capability enum | null"
}
```

The parser rejects unknown fields, malformed JSON, unsupported decisions/capabilities,
inconsistent ACT/ABSTAIN combinations, and outputs larger than the reasoning byte limit.

The model cannot emit or control:

- executable arguments or arbitrary kwargs;
- SQL, table names, URLs, or shell commands;
- credentials or IAM policy;
- provider/model selection;
- retry/fallback behavior;
- capability authorization;
- capability execution or result admission.

A JSON-Schema-valid model response is still an untrusted proposal. Only existing deterministic
Gate 11.1 code can grant capability authority.

### Invocation bounds

The first reasoning contract freezes:

```text
max reasoning invocations per task: 1
adaptive application retries:       0
capability executions in baseline:  0
```

Provider SDK retry observations are recorded separately as runtime evidence. They do not authorize
an application-level retry or alternate provider/model.

## Provider-neutral core

Application/domain code depends on the `AgentReasoningModel` port, not boto3 or Bedrock types.
The provider response is split into:

```text
transient output_text
metadata-only AgentReasoningInvocationEvidence
```

Raw model output is parsed and discarded after proposal creation. It is not persisted in reasoning
result or evaluation-report identity.

The provider-neutral invocation evidence records only admitted runtime metadata:

```text
task_id
provider
model_id
region
request_id
stop_reason
input/output/total/cache token counts
provider latency
client elapsed latency
SDK retry attempts
content-addressed evidence identity
```

Provider exception text is not admitted into reasoning evidence.

## First provider adapter

Use Amazon Bedrock Converse because OpsLens already has a validated non-streaming Converse boundary
from earlier phases and the same inference profile has been exercised successfully in `dev`.

The first fixed adapter uses:

```text
provider:          amazon_bedrock
region:            us-east-1
model/profile:     us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:         disabled
tools:             disabled
temperature:       0.0
maxTokens:         96
application retry: 0
fallback:          0
```

The model/profile remains code-owned configuration. The task/model cannot select a provider,
model, Region, retry strategy, or tool surface.

## Reasoning evaluation contract

Gate 11.4 also freezes a separate proposal-quality evaluation contract:

```text
single-agent-reasoning-evaluation:v1
```

It is intentionally distinct from Gate 11.3 execution evaluation. The six-case reasoning corpus
covers:

1. structured security query selection;
2. knowledge guidance selection;
3. hybrid security answer selection;
4. public repository analysis selection;
5. abstention for arbitrary shell/external-upload behavior;
6. abstention when the semantically matching capability is not present in the code-owned allowlist.

The deterministic report exposes independent integer dimensions:

```text
total_cases
passed_cases
decision_matches
capability_matches
authorization_matches
bounds_compliant_cases
```

A failed model decision therefore cannot be hidden behind one composite score.

## Evidence separation

The following remain distinct:

```text
model output
!= AgentActionProposal
!= authorization evidence
!= execution evidence
!= reasoning evaluation evidence
!= operational telemetry
```

`operational-telemetry:v1` remains frozen and is not overloaded with reasoning-step semantics.

Reasoning report identity contains only content-addressed task/case/result/evidence identities and
deterministic metrics. It contains no chain of thought, raw model output, arbitrary provider text,
or executor output.

## IAM and runtime boundary

Non-streaming Bedrock Converse requires `bedrock:InvokeModel`, but this ADR does not create a
synthetic deployed runtime, new IAM role, or broader policy merely to exercise the baseline.

The real Gate 11.4 experiment must run only with an already-authorized identity or a separately
justified least-privilege identity. Credentials never enter the repository.

No AgentCore, MCP, A2A, public agent runtime, runtime-exposure authority, or Governed LLM Gateway
integration is introduced.

## Cost and quality evidence

Offline tests may prove contract correctness but cannot prove model quality, token usage, latency,
or inference cost.

Gate 11.4 is complete only after the frozen corpus is replayed against the real fixed Bedrock
adapter and the following observations are preserved:

- exact corpus/report identities;
- case-level model decisions/capabilities and deterministic authorization outcomes;
- request IDs and stop reasons;
- observed input/output/total/cache token counts;
- provider/client latency observations;
- SDK retry observations;
- capability executions equal to zero;
- experiment-time cost derived from observed token use and a contemporaneously verified price.

No latency or cost value may be fabricated from offline tests.

## Alternatives considered

### Allow the model to invoke capability bindings directly

Rejected. It would collapse proposal, authorization, and execution into one authority surface and
make model-quality regressions harder to isolate.

### Reuse the Gate 11.3 evaluation corpus unchanged

Rejected. Gate 11.3 intentionally includes adversarial and synthetic execution-failure proposals.
Those cases test deterministic authority/execution contracts, not desired model behavior.

### Add a generic tool registry

Rejected. Gate 11.4 needs only closed capability selection. A generic tool-name/kwargs surface would
expand execution authority without evidence that it is necessary.

### Use LLM-as-a-judge

Rejected. Capability selection, abstention, allowlist behavior, authorization outcome, and invocation
bounds have exact deterministic expected values.

## Consequences

Positive:

- model usefulness can be measured independently from executor behavior;
- provider integration remains replaceable behind a narrow port;
- model output cannot bypass the already-frozen authorization boundary;
- reasoning runtime evidence remains content-minimized and content-addressed;
- the first real baseline has explicit proposal-quality dimensions and cost/latency observations.

Trade-offs:

- Gate 11.4 does not demonstrate end-to-end model-driven capability execution;
- a real model replay is required before the gate can close;
- provider/model changes require a new measured comparison rather than silent substitution.

## AIP-C01 connection

This gate practices constrained model invocation, structured output, deterministic validation,
least-authority tool selection, explicit model/runtime evaluation, and measured cost/latency before
optimization. A managed model or agent runtime does not replace application-owned authorization,
result admission, or evaluation criteria.
