# ADR 0038 — Evaluate the bounded single-agent baseline offline before runtime integration

- Status: Accepted
- Date: 2026-09-07
- Phase: 11 — Single-Agent Baseline
- Gate: 11.3 — Offline Agent Evaluation Harness

## Context

Gate 11.1 froze deterministic capability authorization as `single-agent-authority:v1`.
Gate 11.2 then added `single-agent-execution:v1`, where an already-authorized action can
be bound to exactly one typed capability invocation and one admitted result.

Those contracts prove authority and execution boundaries, but they do not yet provide an
objective baseline for answering questions such as:

- Did the proposal produce the expected authorization outcome?
- Was the expected capability selected?
- Did abstention remain non-executable?
- Was a typed execution admitted or rejected for the expected reason?
- Did evaluation itself remain inside the one-attempt execution bound?

Introducing a real reasoning model, provider, AgentCore runtime, or governed gateway before
freezing this baseline would mix deterministic contract regressions with model/runtime
nondeterminism, latency, and cost.

## Decision

Introduce a separate versioned evaluation contract:

```text
single-agent-evaluation:v1
```

The Gate 11.3 path is:

```text
golden evaluation case
 -> frozen SingleAgentTask + untrusted AgentActionProposal
 -> deterministic Gate 11.1 authorization
 -> optional typed Gate 11.2 invocation
 -> at most one offline executor call
 -> stable observed outcome
 -> deterministic decomposed scoring
 -> content-addressed evaluation report
```

The evaluator is provider-neutral and offline. It does not invoke Bedrock, AWS APIs,
AgentCore, MCP, A2A, or the Governed LLM Gateway.

### Golden case authority

A checked-in strict-schema JSON corpus owns explicit expectations. Fixture admission rejects
missing or unknown fields and unsupported enum values. Each typed case and the complete corpus
receive deterministic SHA-256 identities.

The initial corpus covers:

1. authorized action without execution;
2. explicit abstention;
3. unauthorized capability rejection;
4. admitted typed structured execution;
5. executor failure;
6. result-contract failure.

The corpus does not grant execution authority. It supplies test inputs and expected outcomes;
Gate 11.1 and Gate 11.2 still decide what can be authorized and admitted.

### Decomposed metrics

The report exposes integer counts for:

- authorization matches;
- capability matches;
- execution-outcome matches;
- failure-category matches;
- execution-bound-compliant cases;
- exact passed cases;
- total cases.

There is intentionally no opaque `agent_correctness` score. Future model/runtime comparisons
can derive rates from these stable counts while retaining the underlying case evidence.

### Failure evidence

Only stable content-free categories enter evaluation evidence:

```text
authority_validation
capability_authorization
invocation_contract
executor_failure
result_contract
```

Arbitrary executor/provider exception text is not copied into evaluation artifacts.

### Evidence identities

Evaluation results and reports are content-addressed. Report identity includes:

- exact corpus SHA-256;
- `single-agent-authority:v1`;
- `single-agent-execution:v1`;
- `single-agent-evaluation:v1`;
- decomposed metrics;
- ordered case-result identities.

This permits historical reports to be persisted under immutable/content-addressed paths later
without overwriting prior evidence.

## Authority boundary

This ADR does not change the existing authority hierarchy:

```text
agent proposal != authorization != execution result != evaluation score
```

Deterministic code continues to own capability authorization, invocation/result binding,
execution limits, expected outcomes, metric computation, and report identity.

Operational telemetry also remains separate:

```text
authorization evidence
!= execution evidence
!= evaluation evidence
!= operational telemetry
```

`operational-telemetry:v1` is not reused for Gate 11.3 evaluation evidence.

## Alternatives considered

### Evaluate only after adding a real model

Rejected. It would make contract regressions harder to distinguish from model variance and would
add cost before a deterministic baseline exists.

### Use LLM-as-a-judge for capability correctness

Rejected for this gate. Authorization, execution admission, and expected capability selection are
deterministic properties with exact expected values. A model judge would weaken the authority
boundary rather than improve it.

### Produce one aggregate correctness percentage

Rejected. It hides whether failures came from authorization, capability selection, execution,
result admission, or bound enforcement.

## Consequences

Positive:

- future runtime/provider experiments get a reproducible baseline;
- authority drift can be detected before paid calls are introduced;
- failure categories remain safe and comparable;
- evaluation artifacts can be persisted without mutable "latest" truth;
- agent quality can be discussed dimension by dimension.

Trade-offs:

- the offline corpus does not measure reasoning quality from a real model;
- executor fixtures are intentionally synthetic and do not measure AWS/provider latency or cost;
- later gates must add runtime metrics separately rather than overloading this contract.

## AIP-C01 connection

This gate practices safeguarded tool integration, bounded agent execution, deterministic
validation of model/tool outputs, decomposed agent evaluation, and evaluation before deployment.
A managed agent runtime can help with orchestration, but it does not replace application-owned
authorization or deterministic evaluation criteria.
