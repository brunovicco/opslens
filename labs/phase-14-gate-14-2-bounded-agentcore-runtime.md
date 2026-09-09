# Phase 14 — Gate 14.2: First Bounded AgentCore HTTP/SigV4 Runtime Experiment

_Date: 2026-09-09_

## Status

**COMPLETE — TERMINAL MEASURED EXPERIMENT RECORDED.**

```text
source main: e5072ec68b421677359cebb1eb449578ef7d5b49
workflow:    AgentCore Runtime Experiment
run:         34378942784 / run #11 / SUCCESS
job:         102558703872
issue:       #200 final state synchronization
```

Gate 14.2 proved one removable, bounded Amazon Bedrock AgentCore Runtime around the retained Phase 11 reasoning path. It did **not** approve AgentCore as the default or production OpsLens runtime.

## Objective and authority boundary

The experiment remained intentionally narrower than the existing OpsLens capability surface:

```text
raw JSON bytes
 -> exact-key admission
 -> 4,096-byte runtime envelope
 -> existing 2,048-byte SingleAgentTask text authority
 -> closed AgentCapability allowlist
 -> content-addressed SingleAgentTask
 -> existing reason_about_task(...)
 -> exactly one bounded model proposal
 -> existing deterministic authorize_agent_action(...)
 -> content-addressed AgentCoreReasoningProjection
 -> metadata-only response
 -> STOP before capability execution
```

Frozen contract:

```text
agentcore-runtime-invocation:v1
```

Hard bounds remained:

```text
model invocations/request:       1
capability executions:           0
adaptive application retries:    0
adaptive fallbacks:              0
MCP runtime calls:               0
A2A handoffs:                    0
Gateway/Policy calls:            0
Memory calls:                    0
Browser calls:                   0
Code Interpreter calls:          0
runtime-exposure authority:      0
```

Fixed model/profile:

```text
us.anthropic.claude-haiku-4-5-20251001-v1:0
```

## Deployment artifact and network decision

The reproducible direct-code artifact remained unchanged through the successful run:

```text
runtime:       PYTHON_3_13
architecture:  arm64
compressed:    16,058,438 bytes
sha256:        a846034ad646c4f6383ac08e47d9ed065b4a9f3349c14104db49a2d510b3ec88
version_id:    zbr0hWXEjhjAlBEFZO4782AHyhL5mbfm
native files:  []
```

The experiment used:

```text
protocol:      HTTP
network mode:  PUBLIC
```

`PUBLIC` remains a **time-bounded development experiment exception** from ADR 0053. It is not a production network decision. If AgentCore Runtime is later retained, the network posture must be reconsidered independently; Gate 14.2 does not waive the previously documented Security Hub consequence of PUBLIC mode.

## Terminal successful runtime

Run #11 created and reached `READY` for:

```text
runtime ID:
opslens_dev_bounded_runtime-Cl8aNBDGzh

runtime ARN:
arn:aws:bedrock-agentcore:us-east-1:487757851499:runtime/opslens_dev_bounded_runtime-Cl8aNBDGzh
```

The preserved GitHub Actions evidence artifact is:

```text
artifact ID: 10115123076
name:        phase-14-gate-14-2-agentcore-runtime-evidence-34378942784
digest:      sha256:7006a7c2bfda1658a9e66fcfe38f61b06dc64e6f54705ffbf6b02574870ef65c
```

It contains the runtime identity, publication evidence, replay report, deployment-principal denial, and lifecycle/cleanup evidence.

Immutable repository closeout evidence:

```text
labs/evidence/phase-14-gate-14-2-final-runtime-experiment-v1.json
```

## Authenticated replay result

The frozen Phase 11 corpus was replayed unchanged:

```text
corpus_sha256:          3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
cases:                  6 / 6 PASS
HTTP responses:         200
capability executions:  0
SDK retries:            0
input tokens:           3291
output tokens:          104
total tokens:           3395
transport elapsed sum:  19981 ms
replay report SHA256:   736d573ea31222c39401eccad23af342ffd24ce1fb29b3876f07b8732bfc7f1a
```

This proves transport/runtime hosting preserved the frozen six-case reasoning contract under the measured experiment. It does not prove a broader production quality, latency, reliability, or security claim.

## Negative authorization proof

The deployment principal remained unable to invoke the Runtime:

```text
principal: OpsLensGitHubDeployRole
action:    bedrock-agentcore:InvokeAgentRuntime
result:    AccessDeniedException
HTTP:      403
```

The replay identity remained separate and invocation-only. Feature-branch OIDC trust was never widened.

## Cleanup proof

The terminal cleanup sequence completed:

```text
Terraform plan:   0 to add / 0 to change / 3 to destroy
Terraform apply:  0 added / 0 changed / 3 destroyed
verifier:         RESOURCE_NOT_FOUND
```

Therefore Gate 14.2 no longer needs another runtime attempt for the lifecycle/IAM path established by runs #1–#11.

## Attempts #1–#11 — measured remediation history

The failed attempts are retained as architectural evidence rather than rewritten away.

| Attempt | Run | Result | Measured lesson |
| --- | ---: | --- | --- |
| 1 | `34299888243` | failure before AgentCore | GitHub Actions source-layout CLI import needed the repository `src` package path. |
| 2 | `34301232610` | deployment IAM failure | `CreateAgentRuntime` required dependent `CreateAgentRuntimeEndpoint` on the runtime pre-creation family. |
| 3 | `34302810527` | deployment IAM failure | Runtime creation required create-time `TagResource` on the runtime pre-creation family. |
| 4 | `34304163709` | bootstrap prerequisite | Runtime Identity required the service-linked role; `iam:CreateServiceLinkedRole` stayed in the human bootstrap plane. |
| 5 | `34305577967` | workload-identity IAM failure | Managed workload identity creation required create-time `TagResource` on its pre-creation family. |
| 6 | `34306870906` | workload-identity IAM failure | Managed identity creation required `CreateWorkloadIdentity`. |
| 7 | `34307984723` | directory IAM failure | `CreateWorkloadIdentity` also evaluated the exact default workload-identity directory. |
| 8 | `34309162599` | directory tag IAM failure | Create-time `TagResource` also evaluated the exact default workload-identity directory. |
| 9 | `34357918962` | replay passed; cleanup failed | `DeleteAgentRuntime` required `DeleteWorkloadIdentity` on the exact default directory; Terraform state removal alone was not cleanup proof. |
| 10 | `34375198394` | replay passed; delete waiter failed | `GetAgentRuntime` had to remain readable throughout `DELETING`; a ResourceTag-conditioned read disappeared late in the lifecycle. |
| 11 | `34378942784` | success | Runtime, replay, denial proof, delete lifecycle, and independent cleanup all completed under the corrected least-privilege policy. |

Detailed immutable evidence for attempts #1–#10 remains under `labs/evidence/phase-14-gate-14-2-*`.

## Final IAM lessons

The deployment path exposed real AgentCore lifecycle dependencies that were not safely inferable as a future-looking IAM superset:

```text
CreateAgentRuntimeEndpoint
TagResource during runtime creation
human-bootstrap iam:CreateServiceLinkedRole
managed workload-identity TagResource
CreateWorkloadIdentity
workload-identity directory scope
DeleteWorkloadIdentity
GetAgentRuntime throughout delete lifecycle
```

The final deployment authority preserves:

```text
GitHub OIDC:                              main-only
deployment role InvokeAgentRuntime:       NO
deployment role iam:CreateServiceLinkedRole: NO
deployment role GetWorkloadIdentity:      NO
feature-branch OIDC widening:             NO
```

Lifecycle reads and mutations remain intentionally separated:

```text
ReadExactBoundedAgentCoreRuntimeLifecycle
 -> GetAgentRuntime
 -> exact OpsLens runtime family
 -> no runtime ResourceTag condition
```

Mutation remains tag-gated for:

```text
DeleteAgentRuntime
ListTagsForResource
TagResource
UntagResource
UpdateAgentRuntime
```

The reason is operational rather than cosmetic: delete waiters must be able to observe an exact runtime through the transition where deletion can make its tags unavailable, while mutation remains constrained by the resource-tag policy.

## Observed cost

Delayed AgentCore Runtime CloudWatch telemetry arrived after run #11. The Gate 14.2 cost checkpoint is based on observed service resource usage, not wall-clock inference.

Observed quantities:

```text
CPUUsed-vCPUHours:   0.005455525277778
MemoryUsed-GBHours:  0.200219642726704
```

Rates used by the recorded checkpoint:

```text
AgentCore CPU:     USD 0.0895 / vCPU-hour
AgentCore memory:  USD 0.00945 / GB-hour
```

Derived cost:

```text
CPU:               USD 0.000488269512361131
Memory:            USD 0.001892075623767353
AgentCore Runtime: USD 0.002380345136128484
Bedrock inference: USD 0.004192100000000000
------------------------------------------------
TOTAL:             USD 0.006572445136128483
```

This is the observed cost of the successful six-case experiment. **No monthly extrapolation is part of Gate 14.2.**

## What Gate 14.2 proves

Gate 14.2 now proves that, for this bounded experiment:

- the direct-code package can run in AgentCore Runtime;
- IAM SigV4 invocation works through a separate invocation-only identity;
- the retained Phase 11 six-case reasoning contract remains 6/6;
- runtime hosting did not create capability-execution authority;
- the deployment role remained unable to invoke the runtime;
- exact lifecycle IAM could be derived from measured failures without granting broad authority;
- targeted destroy can be observed to independent `RESOURCE_NOT_FOUND` completion;
- AgentCore Runtime and Bedrock inference cost can be separated from observed evidence.

## What Gate 14.2 does not prove

The result must not be converted into any of the following claims:

```text
AgentCore approved as the default OpsLens runtime
AgentCore approved for production
PUBLIC approved for production
production SLO established
production security posture established
runtime deployment == runtime exposure
runtime telemetry == business truth
runtime authentication == capability authorization
AgentCore hosting == business authorization
```

No MCP runtime, A2A handoff, AgentCore Gateway/Policy, Memory, Browser, Code Interpreter, or capability execution occurred.

## Retention decision is deliberately deferred

The measured experiment answers whether the bounded runtime path can work and what it costs/operationally requires. It does not pre-commit the architecture to retaining it.

The next decision, if formalized after roadmap review, must answer:

> Does the measured AgentCore hosting/session/operational value justify its IAM, lifecycle, network, latency, cost, and operational surface for the retained OpsLens reasoning architecture?

A valid answer may be `RETAIN`, `RETAIN WITH CHANGES`, or `DO NOT RETAIN`, but no answer is authorized by this closeout alone.

## Related architecture records

```text
docs/adr/0052-agentcore-runtime-capability-fit.md
docs/adr/0053-bounded-agentcore-direct-code-public-network-experiment.md
labs/evidence/phase-14-gate-14-2-final-runtime-experiment-v1.json
```

PR #89 remains separate governed cross-project integration work and is untouched by this gate.

## Exit checklist

```text
[x] exact HTTP request/projection contract frozen
[x] request refusal/fail-closed tests
[x] zero capability execution boundary
[x] reproducible direct-code artifact
[x] network decision + explicit PUBLIC exception
[x] separate deployment/runtime/replay authority
[x] immutable attempts #1–#10 failure evidence
[x] authenticated Runtime deployment + READY evidence
[x] unchanged six-case Phase 11 replay through AgentCore
[x] deployment-role InvokeAgentRuntime denial
[x] latency/session/token/retry evidence
[x] runtime cleanup independently proven
[x] delayed CPU/memory telemetry captured
[x] AgentCore Runtime cost derived from observed usage
[x] Bedrock inference cost preserved separately
[x] final Gate 14.2 immutable evidence recorded
[x] retention decision left open for a separately governed next step
```
