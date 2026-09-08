# ADR 0052 — Use AgentCore Runtime Only for a Bounded HTTP/SigV4 Hosting Experiment

- Status: Accepted
- Date: 2026-09-08
- Phase: 14 — Amazon Bedrock AgentCore
- Gate: 14.1 — AgentCore Runtime Capability-Fit and Authority Boundary

## Context

Phase 13 closed at a bounded offline MCP boundary. OpsLens proved official MCP interoperability, deterministic invocation admission, typed capability execution bridging, and explicit structured result projection without claiming a public/deployed MCP runtime.

Phase 14 therefore must not start from the assumption that a managed agent runtime should host every interface already present in the repository. The architectural question is narrower:

```text
Does Amazon Bedrock AgentCore Runtime solve a concrete hosting problem for an
already-governed OpsLens boundary without becoming a second authorization,
execution, evidence, session-identity, or result-authority plane?
```

The retained reasoning reference remains the measured Phase 11 single-agent path. Phase 12 retained deterministic specialization/handoff but did not retain its measured two-model topology as the default. Phase 13 retained MCP as an interoperability boundary, not as a mandatory deployment protocol.

## Current external capability evidence

The AgentCore capability surface was re-verified on 2026-09-08 against current AWS/HashiCorp documentation.

### Runtime protocols

AgentCore Runtime supports separate service contracts for:

```text
HTTP  -> /invocations
MCP   -> /mcp
A2A   -> separate JSON-RPC agent contract
AG-UI -> interactive UI transport contract
```

This matters because protocol availability is not a reason to collapse those protocols into one OpsLens runtime. Phase 15 still owns A2A. Phase 13 MCP remains offline until a concrete MCP deployment consumer exists.

Source:

```text
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-service-contract.html
```

### Inbound authentication

AgentCore Runtime supports IAM SigV4 and OAuth/JWT inbound authorization modes.

For the first bounded experiment, no end-user identity flow is required. A service-to-service/operator invocation is sufficient to measure runtime hosting behavior, so IAM SigV4 is the narrower initial candidate.

OAuth/JWT remains a later identity decision and does not become capability authorization merely because the runtime validates a token.

Sources:

```text
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-service-contract.html
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-security-best-practices.html
```

### Session isolation and ownership

AgentCore Runtime routes related invocations to isolated runtime sessions/microVMs by session identity. That session mechanism is runtime routing/isolation state, not end-user authorization authority.

OpsLens must retain explicit ownership of any future mapping:

```text
application user / caller
 -> authorized application session
 -> AgentCore runtime session ID
```

A runtime session ID alone must never authorize a business capability.

Source:

```text
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html
```

### Execution-role credential exposure

AgentCore Runtime makes temporary execution-role credentials available inside the microVM through its metadata service. Code running inside the VM can attempt to use those credentials.

Therefore the runtime execution role is part of the application security boundary. It must be least-privilege for the exact experiment and must not receive permissions merely because future capabilities might need them.

Source:

```text
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/security-credentials-management.html
```

### Deployment artifact options

AgentCore Runtime supports both direct-code ZIP deployment and container deployment.

Current direct-code guidance documents:

```text
compressed package limit:   250 MB
uncompressed package limit: 750 MB
```

Direct code is recommended for simpler/rapid iteration workloads; containers remain the option when packaging/native-dependency or image-control requirements justify them.

The current HashiCorp AWS provider exposes both modes in `aws_bedrockagentcore_agent_runtime`.

Sources:

```text
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy.html
https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_agent_runtime
```

### Current Terraform compatibility

The actual OpsLens dev lock is:

```text
AWS provider: 6.60.0
constraints:  >= 6.57.1, < 7.0.0
```

The provider documentation for the current resource supports:

```text
aws_bedrockagentcore_agent_runtime
agent runtime artifact: direct code | container
network mode: PUBLIC | VPC
protocol: HTTP | MCP | A2A | AGUI
lifecycle configuration
optional custom JWT authorizer
```

No provider-family migration is justified merely to begin Phase 14.

### Pricing evidence

Current AgentCore Runtime pricing is consumption-based rather than a fixed monthly runtime allocation.

Published list prices observed on the decision date:

```text
CPU:    USD 0.0895 / vCPU-hour
memory: USD 0.00945 / GB-hour
```

Those prices are provider facts, not an OpsLens runtime-cost measurement.

OpsLens cost remains:

```text
runtime cost baseline: UNMEASURED
```

until an authenticated bounded runtime replay records actual consumption evidence.

Source:

```text
https://aws.amazon.com/bedrock/agentcore/pricing/
```

## Decision

Proceed to **one bounded AgentCore Runtime experiment**, not to general AgentCore adoption.

The first candidate experiment will host only the retained Phase 11 bounded reasoning path and stop before capability execution.

```text
AgentCore HTTP invocation
 -> bounded application request admission
 -> retained SingleAgentTask authority
 -> one fixed Bedrock reasoning invocation
 -> transient untrusted {decision, capability}
 -> deterministic parser
 -> existing AgentActionProposal
 -> existing deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
 -> STOP before capability execution
```

The experiment must answer whether AgentCore adds useful managed hosting/session/operational capabilities at acceptable latency, cost, packaging, IAM, and failure complexity.

It does not assume that the experiment will be retained afterward.

## Initial protocol decision

Use **HTTP** for the first experiment.

Rationale:

1. HTTP is AgentCore Runtime's direct application invocation protocol.
2. The experiment is about hosting the retained single-agent application boundary, not exposing a tool server.
3. Using MCP would prematurely turn the Phase 13 offline proof into a runtime requirement.
4. MCP runtime hosting would also require a new runtime dependency/deployment decision for `mcp==2.2.0`.
5. A2A belongs to Phase 15 and must not move forward simply because AgentCore supports it.
6. AG-UI has no concrete current OpsLens consumer requirement.

Therefore:

```text
HTTP:  SELECTED FOR FIRST EXPERIMENT
MCP:   NOT AUTHORIZED FOR FIRST EXPERIMENT
A2A:   DEFERRED TO PHASE 15
AG-UI: NOT REQUIRED
```

## Initial authentication decision

Use **IAM SigV4** for the first experiment.

The experiment has no justified end-user OAuth/JWT flow. SigV4 lets the first caller remain an AWS-authorized service/operator principal and avoids inventing an IdP, token lifecycle, claims model, or public user authorization layer.

Important separation:

```text
SigV4 invocation permission
!=
OpsLens capability authorization
```

Even an authenticated runtime caller cannot bypass `SingleAgentTask`, proposal parsing, or deterministic `authorize_agent_action(...)`.

## Deployment artifact decision

Prefer **direct code** for the first experiment, with an explicit evidence-based fallback to a container only if Gate 14.2 proves packaging/native-dependency constraints make direct code unsuitable.

This is not a blanket production recommendation.

Gate 14.2 must first determine the exact runtime dependency slice and artifact size. It must not vendor the entire repository dependency graph automatically.

Decision:

```text
direct code: preferred first experiment
container:   fallback only with concrete packaging/security evidence
```

## Network-mode decision

Do **not** freeze PUBLIC versus VPC in Gate 14.1.

Gate 14.2 must enumerate the exact outbound dependency set of the first runtime slice before choosing network mode.

The first experiment stops before capability execution, which materially narrows the expected dependency set. That review must determine whether the runtime needs only AWS Bedrock service access or additional endpoints/egress.

Creating a VPC, NAT path, security groups, endpoints, or broad public egress before that dependency review would violate least privilege.

Therefore:

```text
network mode: DEFERRED TO GATE 14.2
```

## Capability execution decision

The first AgentCore experiment performs:

```text
capability executions: 0
```

The managed runtime is initially evaluated as a hosting boundary for reasoning + deterministic authorization only.

This intentionally separates two questions:

```text
Can AgentCore host the bounded reasoning application safely?
!=
Should AgentCore execute OpsLens business capabilities?
```

If runtime hosting is not worth retaining, OpsLens avoids introducing execution-role privileges for capabilities that were never needed.

## Retry and fallback decision

The first experiment preserves the existing bounded reasoning discipline:

```text
adaptive application retries: 0
adaptive fallbacks:           0
```

AgentCore must not become an implicit retry/fallback authority. Any provider/runtime retry observations must remain operational evidence and be measured explicitly.

## Session authority

AgentCore runtime sessions are routing/isolation state only.

Future application code must own any user/caller-to-session relationship and must fail closed if that relationship cannot be established.

```text
runtime session != user identity authority
runtime session != capability authorization
```

## Observability authority

AgentCore/CloudWatch runtime telemetry may become useful operational evidence, but it does not replace the existing OpsLens distinction:

```text
telemetry evidence != business truth
telemetry evidence != route authority
```

Gate 14.2 may measure runtime/session latency, invocation outcomes, resource consumption, and failure behavior. It must not infer vulnerability, risk, evidence provenance, capability authorization, or runtime exposure truth from transport telemetry.

## Retained authority model

Phase 14 starts with these separations:

```text
AgentCore hosting != business authorization
runtime authentication != capability authorization
runtime session != user identity authority
runtime execution role != model/tool authority
runtime transport success != business/evidence truth
runtime telemetry != business truth
runtime deployment != runtime-exposure truth
MCP result != runtime-exposure truth
Repository Risk != Runtime Exposure
```

Existing deterministic code remains authoritative for task admission, capability allowlists, proposal parsing, capability authorization, typed capability invocation/result binding, evidence admission, citation identity, provider/model selection, retry/fallback policy, and runtime-exposure truth.

## Explicit non-claims

Gate 14.1 does not prove or implement:

```text
production AgentCore readiness
public AgentCore endpoint readiness
OAuth/JWT end-user authorization
MCP hosting in AgentCore Runtime
AgentCore Gateway or Policy adoption
AgentCore Memory adoption
Browser or Code Interpreter adoption
A2A interoperability
capability execution through AgentCore
production runtime SLOs
production monthly AgentCore cost
runtime exposure or Amazon Inspector evidence
```

## Alternatives rejected or deferred

### Deploy the Phase 13 MCP server first

Rejected for the first experiment.

Phase 13 deliberately closed without a deployed MCP runtime. Publishing it now simply because AgentCore supports MCP would turn protocol availability into architecture authority.

### Start with A2A

Rejected. A2A is Phase 15 and there is no current need to move it forward.

### Start with OAuth/JWT

Deferred. No public/end-user identity flow is required for the first runtime measurement.

### Grant capability execution permissions immediately

Rejected. The first runtime question can be answered while stopping before capability execution, so broader permissions would add risk without evidence value.

### Create VPC networking immediately

Deferred. The exact first-runtime outbound dependency set must be measured/reviewed first.

### Adopt AgentCore Gateway, Memory, Browser, or Code Interpreter now

Rejected for Gate 14.1. None is required to answer the first Runtime hosting question.

### Treat provider pricing examples as OpsLens cost evidence

Rejected. Provider list prices can be recorded, but OpsLens cost must come from observed runtime consumption.

## Gate 14.1 evidence

The deterministic decision artifact is:

```text
labs/evidence/phase-14-gate-14-1-agentcore-capability-fit-v1.json
```

It binds the exact source `main` SHA, Terraform AWS provider version, official-source findings, retained boundaries, decision, explicit non-claims, zero Gate 14.1 runtime impact, deferred PR #89 state, and the next authorized gate.

## AWS / IAM / runtime impact

Gate 14.1 creates no runtime resources:

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

## Next authorized gate

After Gate 14.1 is protected-merged and state-synchronized, authorize only:

```text
Phase 14 Gate 14.2 — First Bounded AgentCore HTTP/SigV4 Runtime Experiment
```

Gate 14.2 must freeze the actual runtime request contract, exact dependency/artifact shape, network-mode decision, least-privilege execution role, deployment/invocation evidence, cleanup behavior, and measured runtime latency/cost before any capability execution or broader AgentCore adoption.

## Deferred Governed LLM Gateway integration

OpsLens PR #89 remains separate long-lived consumer-side work for Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project.

OpsLens Phase 14 is unrelated numbering. This ADR does not authorize modifying, rebasing, merging, closing, or reusing PR #89.

## AIP-C01 learning connection

A managed agent runtime is not an authorization system by default. Production architecture still needs explicit identity, least-privilege execution roles, deterministic application authority, session ownership, evidence boundaries, observability semantics, cost measurement, and rollback criteria.

The important engineering lesson is to evaluate a managed runtime against one bounded workload first, rather than adopting every adjacent AgentCore component because the platform exposes it.
