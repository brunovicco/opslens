# ADR 0054 — Retain AgentCore Runtime Only as an Optional Lab Target, Not the Default OpsLens Runtime

- Status: Accepted
- Date: 2026-09-09
- Phase: 14 — Amazon Bedrock AgentCore
- Gate: 14.3 — AgentCore Runtime Retention Decision
- Decision class: RETAIN WITH CHANGES

## Context

Gate 14.1 authorized exactly one bounded AgentCore Runtime experiment around the retained Phase 11 single-agent reasoning boundary. Gate 14.2 then completed that experiment with an authenticated HTTP/SigV4 runtime, unchanged six-case replay, separated deployment/replay identities, negative authorization proof, measured lifecycle behavior, independent cleanup proof, and observed AgentCore CPU/memory cost.

The retention question is therefore no longer whether AgentCore Runtime can host the bounded OpsLens reasoning path. It can. The question is whether the demonstrated value justifies making that managed runtime part of the default retained architecture.

The retained Phase 11 reference remains:

```text
quality:                    6 / 6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
SDK retries:                0
capability executions:      0
Bedrock inference cost:     USD 0.0041921
```

Gate 14.2 used the same frozen corpus and model profile and observed:

```text
quality:                    6 / 6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
SDK retries:                0
capability executions:      0
AgentCore Runtime cost:     USD 0.002380345136128484
Bedrock inference cost:     USD 0.0041921
total experiment cost:      USD 0.006572445136128483
```

The measured Runtime compute layer therefore added USD 0.002380345136128484 to the unchanged six-case model inference cost, an observed incremental cost of 56.78168784448091% relative to the direct Bedrock inference cost for that experiment. No monthly extrapolation is authorized.

## Evidence comparison

### Quality, model count, tokens, and authority

The comparable evidence shows no reasoning-quality, model-invocation, or token-efficiency lift from AgentCore hosting:

```text
Phase 11 direct reference:  6 / 6, 6 calls, 3395 tokens
Gate 14.2 AgentCore-hosted: 6 / 6, 6 calls, 3395 tokens
```

The experiment did prove that the existing deterministic authority boundary survives managed hosting:

```text
AgentCore hosting != business authorization
runtime authentication != capability authorization
runtime session != identity authority
runtime execution role != model/tool authority
runtime transport success != business/evidence truth
runtime telemetry != business truth
runtime deployment != runtime-exposure truth
```

That is a successful compatibility result, not an architectural lift over the retained Phase 11 reasoning semantics.

### Latency evidence

The recorded raw measurements are:

```text
Phase 11 client elapsed sum:       8279 ms
Phase 11 client elapsed median:    977.5 ms
Gate 14.2 transport elapsed sum:   19981 ms
```

These measurements are not normalized enough for a retained percentage latency claim. They were captured through different transport boundaries and on different runs, and Gate 14.2 does not preserve a directly comparable cold/warm per-case decomposition against the original Phase 11 client measurement.

Therefore this ADR records only:

```text
normalized latency comparison: NOT PROVEN
raw AgentCore transport overhead: observed, but not converted into a comparative SLO claim
```

No retention decision is justified by manufacturing an apples-to-apples latency percentage that the evidence does not support.

### Managed-runtime value actually demonstrated

Gate 14.2 did demonstrate useful managed-runtime properties:

- direct-code packaging and managed Runtime hosting;
- IAM SigV4 invocation through an invocation-only identity;
- runtime session identity and isolated managed runtime execution;
- explicit READY/delete lifecycle behavior;
- separate deployment, replay, and execution-role identities;
- runtime CPU/memory telemetry in CloudWatch;
- bounded lifecycle controls and independently verified deletion.

Those properties are valuable as a platform experiment and future deployment option.

However, the current retained OpsLens reasoning workload did not demonstrate a concrete requirement for persistent managed sessions, application-user-to-runtime-session mapping, public/end-user authentication, managed memory, AgentCore Gateway/Policy, Browser, Code Interpreter, MCP hosting, A2A hosting, or capability execution inside AgentCore.

### IAM and lifecycle surface

Attempts #1–#11 exposed real additional control-plane and identity complexity, including:

```text
CreateAgentRuntimeEndpoint
create-time TagResource on runtime resources
Runtime Identity service-linked-role bootstrap
managed workload-identity TagResource
CreateWorkloadIdentity
workload-identity directory authorization
DeleteWorkloadIdentity
GetAgentRuntime through the late delete lifecycle
```

The final design preserved least privilege, but preserving least privilege required a materially larger lifecycle/IAM surface than the direct retained reasoning reference.

### Network posture

The successful experiment used `PUBLIC` only as a time-bounded dev exception. ADR 0053 explicitly did not approve PUBLIC for production, and the experiment did not measure the VPC/private-connectivity topology that would be the stronger candidate for retained production hosting.

Therefore default/production AgentCore retention would require an additional network architecture decision and new infrastructure evidence that the current workload has not justified.

## Decision

Use the following split decision:

```text
default OpsLens reasoning runtime:            DO NOT RETAIN AgentCore
Phase 11 direct Bedrock reasoning reference: RETAIN
AgentCore implementation/evidence:           RETAIN
AgentCore deployment role in architecture:   OPTIONAL LAB / FUTURE CONSUMER TARGET ONLY
PUBLIC network mode:                         DO NOT RETAIN
standing AgentCore Runtime resources:        DO NOT RETAIN
standing experiment-specific IAM:            DO NOT RETAIN without an active experiment
```

Overall decision class:

```text
RETAIN WITH CHANGES
```

AgentCore is retained only as a reproducible, disabled-by-default laboratory/deployment target and as measured operational evidence. It is not promoted into the default OpsLens reasoning path.

The direct Phase 11 reasoning architecture remains the default because Gate 14.2 showed compatibility but no quality, token, or invocation-count lift, while adding measured runtime cost and a larger IAM/network/lifecycle surface.

## Standing IAM consequence

Because the experiment is complete and AgentCore is not retained as the active/default runtime, standing experiment-specific deployment/replay IAM is no longer justified merely for convenience.

Cleanup must be handled in a separate bounded issue and human-bootstrap change, not mixed into this decision gate.

The cleanup scope should review and, where safe and unused, remove:

```text
OpsLensAgentCoreReplayRole
OpsLensAgentCoreDeployDevAccess attachment/policy
AgentCore experiment-specific bootstrap outputs/state
AWSServiceRoleForBedrockAgentCoreRuntimeIdentity only if no remaining account dependency requires it
```

The optional lab implementation and historical evidence may remain in the repository with experiment creation disabled by default. Re-running the lab later must require an explicit new hypothesis plus human bootstrap of the minimum required authority.

## Future AgentCore re-entry criteria

AgentCore may be reconsidered for an active runtime only when a concrete consumer or operational requirement exists, for example:

- a real multi-turn session/isolation requirement;
- an independently justified A2A or protocol-hosting deployment boundary;
- a service/runtime SLO that managed hosting can materially improve;
- a need for managed runtime telemetry or lifecycle that outweighs the added control-plane surface;
- a production network design with explicit VPC/private-connectivity evidence.

A future re-entry decision must not inherit the Gate 14.2 PUBLIC exception automatically.

## Consequences

Positive:

- preserves the simplest measured default reasoning architecture;
- retains all AgentCore implementation and operational learning without forcing adoption;
- avoids converting a successful experiment into an unnecessary production dependency;
- preserves future optionality if a real runtime consumer appears;
- removes the justification for standing experiment-only IAM after cleanup;
- keeps Phase 15 A2A independent from an AgentCore hosting assumption.

Trade-offs:

- OpsLens does not receive a continuously deployed managed AgentCore hosting layer today;
- future AgentCore experiments require deliberate re-bootstrap rather than ambient standing authority;
- production AgentCore networking, SLOs, concurrency, warm/cold latency, and application-session value remain unmeasured.

## Residual evidence gaps

The following are explicitly not converted into claims:

```text
normalized direct-vs-AgentCore latency delta: NOT PROVEN
production VPC/private-connectivity cost:      NOT MEASURED
production concurrency/scaling behavior:       NOT MEASURED
multi-turn application session value:          NOT MEASURED
production SLO/security posture:                NOT PROVEN
```

None of those gaps justify another deployment under Gate 14.3 because the current decision does not need them to reject AgentCore as the default runtime.

## Phase outcome

Gate 14.3 completes the architectural retention decision for AgentCore Runtime.

Phase 14 remains operationally open only for the separately governed removal of standing experiment-specific IAM. No additional AgentCore feature expansion is authorized by this ADR.

PR #89 and `feat/governed-gateway-semantic-planner` remain separate cross-project Governed LLM Gateway work and are untouched.

## AIP-C01 learning connection

A managed service can be technically successful and still fail the retention test for the current workload. Architecture should compare the value actually exercised against measurable cost, IAM, networking, lifecycle, and operational complexity rather than retain a platform simply because deployment succeeded.

The important distinction is:

> **capability fit is not adoption, and successful hosting is not proof that managed hosting should become the default.**
