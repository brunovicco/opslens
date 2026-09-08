# Phase 14 — Gate 14.1: AgentCore Runtime Capability-Fit and Authority Boundary

_Date: 2026-09-08_

## Status

**IMPLEMENTED / DRAFT PR — FINAL EXACT-HEAD VALIDATION PENDING.**

Starting checkpoint:

```text
main:   e6f7862275fc0c1a860e70d04363f640d1f02cc8
issue:  #195
branch: docs/phase14-agentcore-capability-fit
PR:     #196
```

## Objective

Start Phase 14 by deciding whether Amazon Bedrock AgentCore Runtime should host any OpsLens boundary at all before creating runtime infrastructure, IAM, deployment artifacts, or new execution authority.

Permanent rules:

> **Agents reason. Code verifies evidence.**
>
> **MCP is an interoperability boundary, not new business authority.**
>
> **Repository Risk != Runtime Exposure.**

This gate is architecture/evidence only.

## Retained architecture entering Phase 14

```text
Phase 11 bounded single-agent reasoning reference: RETAIN
Phase 12 deterministic specialization/handoff:     RETAIN
Phase 12 two-model topology as default:             DO NOT RETAIN
Phase 13 bounded offline MCP architecture:           RETAIN
public/deployed MCP runtime:                         NOT CLAIMED
```

Phase 14 cannot reinterpret any of those historical conclusions merely because AgentCore supports multiple protocols and managed components.

## Current AgentCore capability check

The current service surface was re-verified from official AWS and HashiCorp documentation on 2026-09-08.

### Runtime protocols

AgentCore Runtime currently supports:

```text
HTTP
MCP
A2A
AG-UI
```

Relevant service-contract paths:

```text
HTTP: /invocations
MCP:  /mcp
```

Source:

```text
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-service-contract.html
```

### Authentication

Runtime inbound authentication supports:

```text
IAM SigV4
OAuth/JWT
```

The first OpsLens experiment has no end-user identity requirement, so SigV4 is sufficient and narrower.

### Sessions

AgentCore Runtime uses session identity to keep related requests on isolated runtime environments.

That property is useful for hosting/runtime state, but it does not answer:

```text
Which user owns this session?
Is this caller authorized for an OpsLens capability?
Is this result admissible business evidence?
```

Those remain application concerns.

Source:

```text
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html
```

### Runtime credentials

Execution-role temporary credentials are reachable by code inside the microVM through MMDS.

Security consequence:

```text
execution role scope == material application security boundary
```

Gate 14.2 must therefore start with the exact minimum permission set required by the first experiment rather than a future-looking superset.

Source:

```text
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/security-credentials-management.html
```

### Deployment modes

Current Runtime deployment options include:

```text
direct code ZIP
container image
```

Direct-code current documented limits:

```text
compressed:   250 MB
uncompressed: 750 MB
```

For the first small Python experiment, direct code is the preferred candidate because it minimizes container/ECR machinery. A container remains an allowed fallback only if exact dependency/native-binary packaging evidence requires it.

Sources:

```text
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy.html
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html
```

### Terraform compatibility

Actual OpsLens dev lock:

```text
provider: hashicorp/aws
version:  6.60.0
range:    >= 6.57.1, < 7.0.0
```

The exact locked provider schema was verified in AgentCore CI to expose:

```text
aws_bedrockagentcore_agent_runtime
```

The current resource supports the AgentCore Runtime configuration evaluated by this gate, including direct-code/container artifacts and protocol/network/authentication configuration.

Source:

```text
https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_agent_runtime
```

No Terraform provider-family migration is justified by Gate 14.1.

### Pricing facts versus OpsLens cost evidence

Current published Runtime list prices observed during the gate:

```text
CPU:    USD 0.0895 / vCPU-hour
memory: USD 0.00945 / GB-hour
```

Source:

```text
https://aws.amazon.com/bedrock/agentcore/pricing/
```

These are provider pricing facts only.

OpsLens evidence remains:

```text
Gate 14.1 runtime cost: USD 0.00
runtime cost baseline: UNMEASURED
```

No monthly estimate is invented before an authenticated replay.

## Capability-fit matrix

| Candidate | Current need | Decision for first experiment | Reason |
|---|---|---|---|
| AgentCore Runtime | Yes: managed hosting behavior needs measurement | **GO — bounded experiment only** | Concrete hosting/session/IAM/observability question exists |
| HTTP Runtime protocol | Yes | **SELECT** | Direct application invocation boundary |
| MCP Runtime protocol | No | **DEFER** | Phase 13 intentionally closed offline; no deployed MCP consumer |
| A2A Runtime protocol | No | **DEFER TO PHASE 15** | Separate interoperability phase |
| AG-UI | No | **DEFER** | No current interactive UI protocol requirement |
| IAM SigV4 inbound auth | Yes | **SELECT** | Narrow service/operator authentication for first experiment |
| OAuth/JWT inbound auth | No | **DEFER** | No public/end-user identity flow yet |
| Direct code artifact | Likely | **PREFER** | Small Python experiment, faster iteration, less container machinery |
| Container artifact | Conditional | **FALLBACK ONLY** | Use only if exact packaging/native dependency evidence requires it |
| PUBLIC network mode | Unknown | **DEFER** | Requires exact outbound dependency review |
| VPC network mode | Unknown | **DEFER** | Do not create VPC/endpoints before dependency evidence |
| AgentCore Gateway / Policy | No | **DEFER** | Not needed to test Runtime hosting |
| AgentCore Memory | No | **DEFER** | Existing experiment has no memory requirement |
| Browser | No | **REJECT FOR THIS PHASE ENTRY** | No browser requirement and would widen execution surface |
| Code Interpreter | No | **REJECT FOR THIS PHASE ENTRY** | No arbitrary-code execution requirement |

## Gate 14.1 decision

Proceed to one bounded experiment only:

```text
AgentCore Runtime
 + HTTP
 + IAM SigV4
 + retained Phase 11 reasoning path
 + deterministic capability authorization
 + STOP before capability execution
```

The experiment is explicitly rejectable after measurement.

## Why not host MCP first

Phase 13 already answered the MCP architecture question it was designed to answer:

```text
Can official MCP interoperability be added without authority drift?
```

The answer was yes, offline/in-process.

AgentCore Runtime introduces a different question:

```text
Does a managed runtime improve the hosting boundary enough to justify its
IAM, packaging, network, session, latency, observability, and cost surface?
```

Using HTTP keeps that experiment about Runtime itself. Publishing MCP first would mix both questions and would require promoting an SDK that Phase 13 intentionally kept dev-only.

## First experiment authority path

Gate 14.2 is authorized to design only this path:

```text
AgentCore Runtime HTTP invocation
 -> strict runtime request contract
 -> retained SingleAgentTask authority
 -> fixed provider/model selection owned by code
 -> one bounded Bedrock reasoning call
 -> transient untrusted model output
 -> deterministic output parser
 -> existing AgentActionProposal
 -> existing deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
 -> STOP
```

Hard initial bounds:

```text
capability executions:        0
adaptive application retries: 0
adaptive fallbacks:           0
A2A handoffs:                 0
MCP runtime calls:            0
Browser/Code Interpreter:     0
```

## Gate 14.2 questions that remain intentionally unresolved

Gate 14.1 does not invent answers for concerns that require implementation evidence.

Gate 14.2 must determine:

```text
exact HTTP request/response contract
exact runtime dependency slice
actual direct-code artifact compressed/uncompressed size
native/binary architecture compatibility
PUBLIC vs VPC network mode from exact outbound dependencies
minimum execution-role actions/resources
minimum caller InvokeAgentRuntime permission
runtime lifecycle/session timeout settings
runtime request/session identity evidence
health/ping behavior
failure taxonomy
observability activation needed for the experiment
runtime deployment/update/delete evidence
actual invocation latency
actual model + runtime token/cost observations
actual AgentCore CPU/memory/runtime cost evidence
cleanup evidence
```

No item above may be replaced by assumptions merely to accelerate deployment.

## Least-privilege principle for the first runtime

Because the first runtime stops before capability execution, its execution role must not receive permissions for:

```text
Athena execution
GitHub/network repository acquisition authority
S3 data-lake mutation
MCP runtime hosting
A2A
Browser
Code Interpreter
AgentCore Gateway
future runtime-exposure authority
```

If the retained reasoning adapter needs only Bedrock model invocation plus required runtime/log/artifact access, Gate 14.2 should prove and grant only that set.

## Session boundary

A future runtime session identifier is not sufficient authorization evidence.

Frozen separation:

```text
caller authentication
!=
application user/session ownership
!=
capability authorization
```

The first experiment may remain operator/service oriented and avoid inventing end-user identity semantics.

## Observability boundary

AgentCore runtime logs/traces/metrics may be measured as operational evidence, but they remain subordinate to existing OpsLens truth/evidence contracts.

```text
runtime telemetry != business truth
runtime telemetry != capability authorization
runtime telemetry != runtime-exposure truth
```

## Deterministic evidence artifact

Gate decision evidence:

```text
labs/evidence/phase-14-gate-14-1-agentcore-capability-fit-v1.json
```

It binds:

```text
source main SHA
Terraform AWS provider version/range
official AgentCore/HashiCorp sources
retained OpsLens architecture
first-experiment selection
explicit authority boundaries
zero Gate 14.1 runtime impact
explicit non-claims
PR #89 deferred state
next authorized gate
```

## CI validation checkpoint

A dedicated AgentCore CI workflow was introduced so Phase 14 has a bounded exact-head quality gate before any runtime exists.

The first run exposed a test-harness issue rather than an AgentCore/provider incompatibility:

```text
run:                     34253629119 / #1 / FAILED
job:                     102153832609
failure:                 terraform providers schema requested from the real
                         backend-bearing dev working directory after
                         init -backend=false
Terraform error:         Backend initialization required
provider resource check: NOT REACHED
AWS calls/resources:     0
```

The remediation intentionally did not initialize the real backend or change provider/state files. The workflow now reads the exact AWS provider version from the committed dev lock, creates an isolated temporary backend-free Terraform configuration pinned to that version, and probes that provider schema.

Corrected checkpoint:

```text
head:                    50975d2bfb34f5e2693e92477bf1e2005d1d065e
AgentCore CI:            34253894105 / run #2 / PASS
job:                     102154709747
uv lock --check:         PASS
Phase 14 evidence JSON:  PASS
locked AWS provider:     6.60.0
verified resource:       aws_bedrockagentcore_agent_runtime
AgentCore Python slice:  not introduced; architecture/evidence-only gate
AWS calls/resources:     0
IAM/model/capability:    0
```

The workflow also covers the authoritative/public state documents so the later Gate 14.1 state synchronization is validated by the same Phase 14 CI.

Because this lab update changes the PR head, one final exact-head AgentCore CI pass is required before the PR can leave draft state.

## Gate 14.1 AWS / IAM / runtime impact

```text
new AgentCore runtimes:      0
new model invocations:       0
new capability executions:   0
new AWS resources:           0
new IAM roles/policies:      0
GitHub OIDC trust changes:   0
new public endpoints:        0
new inference cost:          USD 0.00
AgentCore runtime cost:      USD 0.00
runtime cost baseline:       UNMEASURED
```

## Architecture record

```text
docs/adr/0052-agentcore-runtime-capability-fit.md
```

## Deferred Governed LLM Gateway integration

OpsLens PR #89 remains separate long-lived consumer-side work for Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project.

Preserved head:

```text
3781831795d500b05fa4bc602d50f376b4b1539f
```

This Gate 14.1 work does not modify, rebase, merge, close, or reuse it.

## AIP-C01 learning connection

AgentCore demonstrates a certification-relevant distinction between a managed runtime capability and application authority. Runtime hosting can supply isolation, protocols, lifecycle, identity integration, observability, and consumption billing, but the application still owns bounded inputs, business authorization, evidence semantics, least-privilege roles, and measurable acceptance criteria.

The stronger architecture is not the one that uses the most AgentCore components. It is the one that can explain why each adopted component is required and what authority it does **not** own.

## Exit checklist

```text
[x] Phase 13 complete and state synchronized
[x] issue #195 created
[x] branch created from exact main
[x] current AgentCore service surface verified
[x] actual Terraform provider compatibility recorded
[x] first hosted boundary selected
[x] HTTP selected for first experiment
[x] SigV4 selected for first experiment
[x] direct code preferred with evidence-based container fallback
[x] network mode deliberately deferred to exact dependency review
[x] capability execution kept at zero for first experiment
[x] authority boundaries frozen
[x] deterministic evidence artifact added
[x] ADR 0052 added
[x] ADR 0052 indexed
[x] draft PR #196 opened
[x] dedicated AgentCore CI added
[x] exact locked AWS provider schema probe verified
[ ] final exact-head AgentCore CI PASS after this lab checkpoint
[ ] PR scope/review threads clean
[ ] protected squash merge
[ ] post-merge state synchronization
[ ] issue #195 CLOSED / COMPLETED after state synchronization
```

## Next authorized gate

After protected merge and post-merge state synchronization:

```text
Phase 14 Gate 14.2 — First Bounded AgentCore HTTP/SigV4 Runtime Experiment
```

No AgentCore resource deployment is authorized before that transition is complete.
