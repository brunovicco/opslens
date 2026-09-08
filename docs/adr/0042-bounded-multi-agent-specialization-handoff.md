# ADR 0042 — Bound multi-agent specialization before adding another model call

- Status: Accepted
- Date: 2026-09-07
- Phase: 12 — Multi-Agent Architecture
- Gate: 12.1 — Bounded Specialization Handoff Contract

## Context

Phase 11 closed with a real bounded single-agent reasoning baseline and an evidence-driven `NO-CHANGE / NO-EXPERIMENT` optimization decision.

The frozen six-case reasoning corpus scored:

```text
proposal quality:             6/6
bounds compliance:            6/6
SDK retries:                  0
capability executions:        0
input/output/total tokens:    3291 / 104 / 3395
provider latency median:      809.5 ms
client elapsed median:        977.5 ms
derived six-case cost:        USD 0.0041921
```

That baseline provides no measured quality failure that would justify multi-agent complexity merely as another attempt to improve routing accuracy.

Phase 12 still needs a safe architecture boundary if a future comparative experiment evaluates specialization. The first decision is therefore to freeze deterministic handoff authority before any triage or specialist model is introduced.

## Decision

Introduce provider-neutral contract:

```text
multi-agent-handoff:v1
```

The v1 candidate specialization partition is code-owned:

```text
EVIDENCE_ANALYSIS
 -> public_repository_analysis
 -> structured_security_query

GUIDANCE_SYNTHESIS
 -> hybrid_security_answer
 -> knowledge_guidance
```

This partition is intentionally coarse. A future triage model may propose one specialization without proposing a capability. Deterministic code then intersects that specialization scope with the original `SingleAgentTask.allowed_capabilities` before any specialist step exists.

The Gate 12.1 boundary is:

```text
SingleAgentTask
 -> TriageAgentTask
 -> untrusted MultiAgentHandoffProposal
 -> exact source-task binding
 -> code-owned specialization scope
 -> deterministic intersection with source allowlist
 -> AuthorizedMultiAgentHandoff | MultiAgentHandoffAbstention | fail closed
 -> narrowed SpecialistAgentTask
 -> STOP
```

Gate 12.1 performs no model call.

## Why this partition

The Phase 11 surface contains four capability classes with two broad evidence responsibilities:

```text
repository / structured security evidence
controlled guidance / hybrid answer synthesis
```

Grouping them into two fixed specializations provides one testable structural hypothesis for a later experiment: the specialist reasoning surface can be reduced from at most four candidate capabilities to at most two.

This is **not runtime privilege reduction**. The Phase 11 model already had no execution authority. The measured property is only capability-proposal surface width presented to a future specialist reasoning step.

If a later experiment cannot show that this narrowing justifies the additional invocation, latency, tokens, cost, and failure surface, the multi-agent topology must be rejected.

## Proposal boundary

`MultiAgentHandoffProposal` contains only:

```text
source_task_id
decision: handoff | abstain
target_specialization: evidence_analysis | guidance_synthesis | null
proposal_sha256
proposal_id
```

It contains no:

```text
capability selection
arbitrary message/context
args / kwargs
SQL
URL
shell command
credential
provider/model selector
retry/fallback policy
execution result
```

The proposal is untrusted and content-addressed. It is not handoff authority.

## Deterministic handoff admission

For `HANDOFF`, application code:

1. verifies the exact source task identity;
2. resolves the fixed specialization scope;
3. intersects it with the source task's already-authorized capability allowlist;
4. rejects an empty intersection before a specialist can exist;
5. creates a new `SingleAgentTask` with the same bounded untrusted task text and only the narrowed capability tuple;
6. creates content-addressed `AuthorizedMultiAgentHandoff` evidence;
7. wraps the target in `SpecialistAgentTask`.

The authorized handoff is still not capability authorization and not execution authority.

For `ABSTAIN`, deterministic code creates content-addressed `MultiAgentHandoffAbstention` and no specialist task.

## Handoff and loop bounds

```text
maximum handoffs per task:       1
maximum specialist capabilities: 2
real model calls in Gate 12.1:   0
capability executions:           0
```

The v1 API accepts only `TriageAgentTask` as a handoff source and produces `SpecialistAgentTask` as its target. `SpecialistAgentTask` is not accepted as a new source, so handoff chains/cycles are structurally excluded from the Gate 12.1 application boundary.

No graph framework, recursive delegation, or loop counter is required for this first one-way contract.

## Authority preservation

Phase 11 boundaries remain unchanged:

```text
agent action proposal != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
structured model output != trusted proposal
model selection != capability authority
```

Phase 12 adds:

```text
handoff proposal != handoff admission
handoff admission != capability authorization
specialization scope != capability authority
specialist task != capability invocation
```

Deterministic code continues to own capability allowlists, handoff scope, capability authorization, typed execution, result binding, provider/model selection, retry/fallback policy, evaluation metrics, and runtime-exposure authority.

## Evidence boundary

Canonical handoff identities contain task/proposal/specialization/target identity and the narrowed capability tuple. They do not require raw triage output, provider prose, prompts, or arbitrary context payloads.

The original task text remains part of the existing `SingleAgentTask` identity and may be copied only into the derived bounded specialist task. No model-authored context is forwarded by this contract.

## Comparative-evaluation requirement

Gate 12.1 does not authorize a real multi-agent experiment.

Before a later gate adds two model calls, it must freeze comparison metrics against the Phase 11 reference, including at minimum:

```text
routing/proposal quality
bounds compliance
specialist capability-surface width
model invocation count
input/output tokens
provider/client latency
SDK retries
inference cost
capability executions
```

Any improvement claim must account for the cost of the additional model step.

## Alternatives rejected

### Add a second model immediately

Rejected because the Phase 11 corpus currently exposes no measured quality failure and no handoff contract exists yet.

### Make the model choose arbitrary agent names

Rejected because open-ended agent identity is another unbounded authority surface.

### Pass free-form triage reasoning to the specialist

Rejected because it creates an uncontrolled prompt/context channel and complicates provenance and injection analysis.

### Map one specialist directly to each capability

Rejected for the first hypothesis because it would make triage specialization equivalent to selecting the final capability while still adding another model step.

### Adopt LangGraph, AgentCore, MCP, or A2A now

Rejected because Gate 12.1 needs only a small provider-neutral deterministic contract. Runtime/framework choices remain separate decisions.

## AWS / IAM / runtime impact

```text
new AWS resources:              0
new IAM roles/policies:         0
real model calls:               0
AgentCore runtime:              0
MCP:                            0
A2A:                            0
public agent runtime:           0
runtime-exposure authority:     0
Governed LLM Gateway changes:   0
```

PR #89 remains deferred cross-project integration work.

## Consequences

### Positive

- multi-agent coordination starts behind deterministic handoff admission;
- specialist scope narrowing is explicit and measurable;
- source capability restrictions cannot be broadened by specialization;
- empty handoff scope fails before any future specialist model call;
- free-form inter-agent context is excluded from v1;
- cycles are excluded without introducing a graph runtime;
- Phase 12 can later compare a precise hypothesis against the Phase 11 baseline.

### Trade-offs

- the two-specialization partition is only a hypothesis, not a proven optimal decomposition;
- Gate 12.1 provides no model-quality evidence for multi-agent behavior;
- actual multi-agent execution would add latency, tokens, cost, and additional failure modes;
- a later experiment may correctly conclude that the single-agent design should remain preferred.

## AIP-C01 learning relevance

This gate provides practical evidence for:

- designing agent boundaries before selecting managed runtime technology;
- deterministic authorization around agent delegation;
- least-authority reasoning surfaces without confusing them with execution privilege;
- explicit handoff provenance and content minimization;
- bounded delegation and loop prevention;
- evaluation-driven decisions about agent complexity;
- separating application contracts from AgentCore/MCP/A2A adoption.
