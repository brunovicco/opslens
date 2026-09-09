# Phase 14 — Gate 14.3: AgentCore Runtime Retention Decision

_Date: 2026-09-09_

## Status

**DECISION RECORDED — RETAIN WITH CHANGES.**

```text
issue:       #222
source main: 8a9210edfd89ba0ceb1e2d0ea0ecda0190c843c2
```

Gate 14.3 answers the post-experiment question left open by Gate 14.2:

> Does the measured AgentCore hosting/session/operational value justify its IAM, lifecycle, network, latency, cost, and operational surface for the retained OpsLens reasoning architecture?

The answer is split deliberately:

```text
default reasoning runtime:                DO NOT RETAIN AgentCore
Phase 11 direct Bedrock reference:        RETAIN
AgentCore code + evidence:                RETAIN
AgentCore active deployment role:         OPTIONAL LAB TARGET ONLY
PUBLIC network decision:                  DO NOT RETAIN
standing experiment runtime resources:    DO NOT RETAIN
standing experiment-specific IAM:         CLEANUP REQUIRED
```

Overall decision class:

```text
RETAIN WITH CHANGES
```

## Comparable measured evidence

### Quality and authority

| Dimension | Phase 11 direct reference | Gate 14.2 AgentCore-hosted | Decision signal |
| --- | ---: | ---: | --- |
| Frozen corpus | same SHA | same SHA | comparable |
| Passed cases | 6 / 6 | 6 / 6 | no quality lift |
| Model invocations | 6 | 6 | no invocation lift |
| Input tokens | 3291 | 3291 | unchanged |
| Output tokens | 104 | 104 | unchanged |
| Total tokens | 3395 | 3395 | unchanged |
| SDK retries | 0 | 0 | unchanged |
| Capability executions | 0 | 0 | authority preserved |

The AgentCore run proved that managed hosting did not break the deterministic reasoning/authorization contract. It did not demonstrate a better reasoning topology.

## Cost comparison

Because both paths used the same frozen model/corpus and the same measured token counts, the inference component is directly comparable:

```text
Phase 11 Bedrock inference:      USD 0.004192100000000000
Gate 14.2 Bedrock inference:     USD 0.004192100000000000
Gate 14.2 AgentCore Runtime:     USD 0.002380345136128484
Gate 14.2 total:                 USD 0.006572445136128483
```

Incremental measured Runtime cost relative to the unchanged Bedrock inference component:

```text
+56.78168784448091%
```

Runtime compute represented 36.217040794206355% of the measured Gate 14.2 total experiment cost.

No monthly extrapolation is made.

## Latency discipline

Available raw measurements:

```text
Phase 11 client elapsed:
  sum:    8279 ms
  mean:   1379.833333 ms
  median: 977.5 ms

Gate 14.2 AgentCore transport elapsed:
  sum:    19981 ms
  mean:   3330.166667 ms
```

These are not retained as an apples-to-apples percentage delta.

Reasons:

- different measurement boundaries;
- different execution dates/runs;
- no normalized cold/warm decomposition against the original Phase 11 measurement;
- no matched per-case controlled direct-vs-hosted run under the same runtime conditions.

Decision:

```text
normalized latency delta: NOT PROVEN
```

The raw data is preserved, but Gate 14.3 does not invent a comparative SLO claim.

## Managed-runtime value actually exercised

The experiment did exercise:

```text
direct-code AgentCore Runtime
HTTP application protocol
IAM SigV4 invocation
runtime/session identity
managed runtime isolation
execution role separation
READY/delete lifecycle
CloudWatch CPU/memory runtime telemetry
bounded lifecycle configuration
independent runtime cleanup verification
```

This is meaningful engineering evidence and is worth retaining as an optional lab/deployment target.

The experiment did **not** exercise:

```text
OAuth/JWT end-user identity
application user -> runtime session ownership
multi-turn state value
AgentCore Memory
Gateway/Policy
Browser
Code Interpreter
MCP hosting
A2A hosting
AG-UI
capability execution inside AgentCore
production concurrency/scaling
production VPC/private connectivity
production SLO/security posture
```

The broader AgentCore platform therefore cannot be used as justification for default adoption.

## IAM/lifecycle burden measured by attempts #1–#11

Gate 14.2 required iterative evidence to derive the least-privilege lifecycle surface:

```text
CreateAgentRuntimeEndpoint
runtime create-time TagResource
Runtime Identity service-linked-role bootstrap
managed workload-identity TagResource
CreateWorkloadIdentity on workload-identity family
CreateWorkloadIdentity on default directory
TagResource on default directory
DeleteWorkloadIdentity on default directory
GetAgentRuntime through late DELETING
```

The final result is least-privilege, but the lifecycle surface is materially larger than direct Bedrock reasoning.

Important positive proof remains:

```text
main-only GitHub OIDC
OpsLensGitHubDeployRole cannot InvokeAgentRuntime
OpsLensGitHubDeployRole cannot iam:CreateServiceLinkedRole
OpsLensGitHubDeployRole cannot GetWorkloadIdentity
separate invocation-only replay role
zero capability execution
```

## Network decision

Gate 14.2 `PUBLIC` was explicitly temporary and dev-only.

The experiment did not justify carrying that posture forward. A real retained production Runtime would require a new VPC/private-connectivity decision and corresponding evidence.

Therefore:

```text
PUBLIC historical experiment evidence: PRESERVE
PUBLIC as retained active posture:      REJECT
```

## Cleanup/removability

Run #11 proved:

```text
Terraform cleanup: 0 add / 0 change / 3 destroy
independent verifier: RESOURCE_NOT_FOUND
```

The runtime itself is already absent.

However, human-bootstrap AgentCore experiment IAM remains a standing authority surface after the runtime experiment. Since AgentCore is not retained as the active/default runtime, that standing experiment authority no longer has a current workload justification.

Gate 14.3 therefore requires a **separate cleanup issue**. This gate will not mix IAM deletion with the architectural decision.

## Retention matrix

| Surface | Outcome | Rationale |
| --- | --- | --- |
| Phase 11 reasoning reference | RETAIN | simpler measured default; same 6/6 reasoning result |
| AgentCore HTTP contract | RETAIN | useful reproducible hosting experiment contract |
| Direct-code package path | RETAIN | deterministic, reproducible, optional lab value |
| AgentCore runtime Terraform | RETAIN DISABLED | optional future lab target only |
| AgentCore historical evidence | RETAIN | first-class operational/IAM learning |
| AgentCore as default runtime | DO NOT RETAIN | no quality/token/invocation lift; added runtime surface/cost |
| PUBLIC network mode | DO NOT RETAIN | dev-only exception, not production posture |
| Standing Runtime resource | DO NOT RETAIN | already cleaned; no active workload |
| Standing experiment replay/deploy IAM | DO NOT RETAIN | no active experiment; cleanup separately |
| Runtime Identity SLR | REVIEW FOR CLEANUP | remove only if no remaining account dependency |

## Residual gaps

The decision explicitly preserves these as gaps rather than claims:

```text
normalized direct-vs-AgentCore latency comparison: NOT PROVEN
production private networking:                     NOT MEASURED
production concurrency/scaling:                    NOT MEASURED
multi-turn application session value:              NOT MEASURED
production SLO/security posture:                   NOT PROVEN
```

No new Runtime deployment is authorized merely to fill those gaps. A future deployment requires a concrete consumer/hypothesis.

## Decision rationale

The key result is asymmetric:

```text
AgentCore compatibility: PROVEN
AgentCore default-runtime superiority: NOT PROVEN
```

For the current OpsLens reasoning architecture, AgentCore provided hosting/session/lifecycle/telemetry capabilities but no measured reasoning-quality or efficiency lift. It also introduced a measured runtime cost increment and a substantially larger IAM/network/lifecycle surface.

The evidence therefore supports retaining the implementation as an optional lab target while rejecting it as the default runtime.

## Next authorized action

Create a separate bounded cleanup issue for standing experiment-specific AgentCore bootstrap IAM. The cleanup must preserve repository evidence and disabled-by-default experiment code while removing ambient authority that no active workload currently requires.

After that cleanup is complete, Phase 14 can close and Phase 15 A2A may start without assuming AgentCore as its hosting substrate.

PR #89 remains separate and untouched.

## Evidence

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
labs/evidence/phase-14-gate-14-2-final-runtime-experiment-v1.json
labs/evidence/phase-14-gate-14-3-agentcore-retention-decision-v1.json
docs/adr/0054-retain-agentcore-only-as-optional-lab-target.md
```
