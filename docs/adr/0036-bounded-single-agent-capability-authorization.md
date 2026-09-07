# ADR 0036 — Bounded Single-Agent Capability Authorization

- Status: Accepted
- Date: 2026-09-07
- Phase: 11 — Single-Agent Baseline
- Gate: 11.1

## Context

OpsLens has completed deterministic structured, semantic, hybrid, public-analysis admission, and operational-observability boundaries. Phase 11 may now introduce agent reasoning, but an agent must not inherit authority merely because an agent framework can call tools.

The first agent boundary therefore needs to answer a narrower question before any model or managed runtime is selected:

> What exactly may one agent propose, and what deterministic code must verify before that proposal becomes authorized action?

The architectural risk is authority laundering:

```text
model decides a tool name/arguments
 -> framework executes it
 -> model proposal silently becomes execution authority
```

That is incompatible with the existing OpsLens invariants.

## Decision

Freeze the provider-neutral contract:

```text
single-agent-authority:v1
```

with this authority flow:

```text
bounded SingleAgentTask
 -> deterministic capability allowlist
 -> untrusted AgentActionProposal
 -> deterministic authorization
 -> AuthorizedAgentAction | AgentAbstention
 -> STOP
```

The permanent distinction is:

```text
agent action proposal != capability authorization != execution result
```

Gate 11.1 ends at authorization. No capability is executed.

## Closed capability surface

The initial enum is deliberately small and represents existing governed capability classes rather than generic tools:

```text
structured_security_query
knowledge_guidance
hybrid_security_answer
public_repository_analysis
```

These identifiers do not grant shell, network, file-system, browser, SQL, provider, model, or credential authority. A future adapter must map an authorized capability to an existing OpsLens application boundary while preserving that boundary's own deterministic contracts.

Unknown capability names are invalid. There is no best-effort mapping from arbitrary strings.

## Task authority

`SingleAgentTask` contains:

```text
bounded untrusted task text
code-owned tuple[AgentCapability, ...]
content-addressed task identity
```

V1 bounds:

```text
max task UTF-8 bytes:      2048
max allowed capabilities:  4
```

Capability ordering is canonicalized before hashing. Duplicate, empty, oversized, or untyped capability surfaces fail closed.

The task identity binds both the exact task text and the exact authorized capability set. Changing either changes the task identity.

## Proposal semantics

`AgentActionProposal` is untrusted even when a future LLM produces it.

It contains only:

```text
task_id
decision: act | abstain
capability: AgentCapability | null
content-addressed proposal identity
```

Consistency rules:

```text
ACT      -> exactly one typed capability
ABSTAIN  -> no capability
```

The proposal deliberately has no fields for:

```text
tool_name
args / kwargs
URL
SQL
shell command
provider
model_id
credentials
retry/fallback policy
```

Structural proposal validity does not prove authorization. An out-of-allowlist capability can be represented as a valid proposal and is then denied by the deterministic authorization boundary.

## Authorization semantics

`authorize_agent_action(task, proposal)` owns the authorization decision.

It verifies:

1. exact admitted runtime types;
2. exact proposal-to-task identity binding;
3. ACT/ABSTAIN consistency already admitted by the domain contract;
4. capability membership in the task's deterministic allowlist.

Outcome:

```text
allowlisted ACT -> AuthorizedAgentAction
ABSTAIN         -> AgentAbstention
mismatched task -> reject
unauthorized capability -> reject
```

`AuthorizedAgentAction` is content-addressed and binds:

```text
task_id
proposal_id
capability
```

It is authorization evidence, not execution evidence.

`AgentAbstention` is also content-addressed and grants no capability authority.

## Execution budget

Gate 11.1 freezes:

```text
MAX_AGENT_PROPOSALS_PER_TASK = 1
MAX_AGENT_AUTHORIZATION_STEPS = 1
MAX_AGENT_CAPABILITY_EXECUTIONS = 0
MAX_AGENT_ADAPTIVE_RETRIES = 0
```

This is intentionally not yet an agent loop.

## Deterministic authority preservation

The following remain code-owned:

- package/version and vulnerability applicability;
- Risk Policy facts;
- SemanticQuery validation and SQL compilation;
- hybrid route and evidence completeness;
- evidence/citation admission;
- public repository request/source admission;
- operational telemetry admission;
- single-agent capability authorization.

The agent may later propose which authorized capability to use. It does not acquire those authorities.

## Failure semantics

Contract violations raise bounded validation failures. Capability denial raises a bounded authorization error without provider/model content.

No denied or malformed proposal is translated into another capability, implicit retry, or fallback.

## Observability decision

Gate 11.1 does not add agent events to `operational-telemetry:v1`.

Phase 10's content-minimization and cardinality principles remain mandatory, but agent-step telemetry has different semantics from the five frozen public-analysis stages. If agent telemetry becomes necessary, it requires a separately versioned contract instead of mutating or overloading the Phase 10 event vocabulary.

## AWS and IAM boundary

Gate 11.1 is offline and provider-neutral:

```text
real model calls:              0
real capability/tool calls:    0
AWS calls:                     0
new AWS resources:             0
new IAM roles/policies:        0
agent runtime infrastructure:  0
```

No Bedrock Agents, Amazon Bedrock AgentCore, Lambda, ECS, MCP, A2A, or Governed LLM Gateway integration is introduced by this decision.

Least-privilege IAM remains deferred until a concrete runtime and concrete capability adapter require permissions.

## Cost boundary

The gate adds no runtime/provider usage, so there is no model or AWS runtime cost measurement to report.

This does not imply future agent cost is zero. Later gates must measure model turns, capability executions, retries, latency, and provider/runtime cost from actual execution evidence.

## Consequences

### Positive

- model reasoning cannot silently become tool execution authority;
- agent proposals are independently testable without a model;
- abstention is explicit instead of hidden fallback;
- capability identities are closed and typed;
- action authorization is content-addressed and auditable;
- the architecture remains framework- and provider-neutral;
- future model/runtime choices can be compared against a stable authority contract.

### Trade-offs

- the first agent cannot author capability arguments;
- capability execution requires a later typed-binding gate;
- tasks need code-owned allowlists before reasoning;
- more sophisticated multi-step planning is intentionally deferred.

These constraints are deliberate. Phase 11 is establishing a trustworthy single-agent baseline, not maximizing autonomy.

## Rejected alternatives

### Generic string tool registry

Rejected because arbitrary `tool_name: str` plus free-form arguments would create a broad authority surface and make fail-closed validation difficult.

### Let the model choose tools and arguments directly

Rejected because it collapses proposal and authorization authority.

### Adopt Bedrock Agents or AgentCore first

Rejected for Gate 11.1 because runtime selection before freezing authority would let framework/provider mechanics define the security boundary.

### Reuse Phase 10 stage enums for agent steps

Rejected because operational public-analysis stages and future agent-step semantics are distinct contracts. Reuse without versioning would corrupt telemetry meaning.

## AIP-C01 learning notes

This decision demonstrates several professional GenAI engineering principles relevant to AWS Certified Generative AI Developer – Professional preparation:

- tool use should sit behind deterministic authorization boundaries;
- model output is untrusted proposal data even when structured;
- abstention and unsupported outcomes are safer than implicit fallback;
- managed-agent services do not replace application authorization design;
- least-privilege IAM follows concrete execution responsibilities;
- evaluation should first prove authority and failure behavior offline before adding provider/runtime variability;
- operational telemetry schemas should be versioned when semantics change.

## Next

Gate 11.2 may introduce typed capability bindings and an offline deterministic single-turn executor over injected fake capability ports. It must not add a model call or managed runtime until the execution/result authority boundary is explicit and evaluated.
