# ADR 0044 — First Bounded Real Two-Model Comparison

- Status: Accepted
- Date: 2026-09-07
- Phase: 12 — Multi-Agent Architecture
- Gate: 12.3 — First Bounded Real Two-Model Comparison

## Context

Gate 12.1 froze the deterministic `multi-agent-handoff:v1` specialization boundary. Gate 12.2 then froze `multi-agent-comparison:v1`, a provider-neutral offline comparison contract bound to the exact Phase 11 single-agent reference before any second real model call existed.

The Phase 11 reference already achieved `6/6` on its frozen corpus. A two-model topology therefore starts with no presumption that it is better. It must earn its additional invocation count, token use, latency, cost, failure surface, and architectural complexity through measured evidence.

The first real experiment needs to isolate topology and specialization rather than simultaneously changing the model, provider, executor behavior, and authority model.

## Decision

Introduce the first real two-model reasoning path with strict deterministic authority boundaries:

```text
SingleAgentTask
 -> one bounded triage model invocation
 -> transient {decision, target_specialization}
 -> deterministic parser
 -> existing Gate 12.1 handoff admission
 -> ABSTAIN / rejected? STOP
 -> narrowed SpecialistAgentTask
 -> one bounded specialist reasoning invocation
 -> existing deterministic capability authorization
 -> STOP before capability execution
```

The triage model can propose only:

```json
{
  "decision": "handoff | abstain",
  "target_specialization": "evidence_analysis | guidance_synthesis | null"
}
```

It cannot select a capability, provider, model, execution target, tool, SQL statement, URL, shell command, argument, credential, retry policy, fallback policy, or execution result.

The specialist model reuses the Phase 11 proposal surface:

```json
{
  "decision": "act | abstain",
  "capability": "closed capability enum | null"
}
```

Deterministic code remains the only authority for handoff admission, target capability scope, specialist capability authorization, and any later execution.

## Initial provider boundary

Use the same fixed Bedrock model/profile for both triage and specialist calls:

```text
provider:       Amazon Bedrock Converse
region:         us-east-1
model/profile:  us.anthropic.claude-haiku-4-5-20251001-v1:0
temperature:    0.0
tools:          disabled
streaming:      no
```

Keeping the model/profile constant makes specialization topology the principal changed experimental variable. Provider/model selection remains code-owned and cannot be overridden by task text or model output.

## Hard runtime bounds

```text
maximum model invocations per source task: 2
maximum handoffs per source task:          1
maximum specialist capability width:      2
adaptive application retries:             0
adaptive fallbacks:                        0
capability executions:                     0
```

An admitted handoff is expected to contain exactly two model invocations. Triage abstention or deterministic handoff rejection must stop after one model invocation and cannot invoke the specialist.

## Evidence contract

Gate 12.3 adds provider-neutral, content-minimized triage invocation evidence and a content-addressed two-model terminal result.

Admitted runtime metadata includes only the fields required to prove the bounded invocation:

```text
provider
model_id
region
request_id
stop_reason
input/output/total tokens
cache read/write input tokens
provider latency
client elapsed latency
SDK retry attempts
```

Raw model output is transient and untrusted. It is parsed deterministically but is not persisted as canonical evidence.

The final real-comparison report remains decomposed rather than reducing the experiment to one opaque score. It records routing, specialization, admission, target-scope, non-broadening, specialist decision/capability/authorization, and runtime-bound compliance independently.

## Frozen experiment corpus

Freeze a new Gate 12.3 corpus rather than altering Gate 12.2 historical fixtures. The corpus binds exact identities from both earlier comparison layers:

```text
Phase 11 corpus_sha256:
3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc

Phase 11 report_sha256:
724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145

Gate 12.2 dataset_sha256:
1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491

Gate 12.2 report_sha256:
0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
```

The six task semantics remain directly comparable with prior evaluation:

```text
structured security question -> EVIDENCE_ANALYSIS -> structured_security_query
knowledge guidance            -> GUIDANCE_SYNTHESIS -> knowledge_guidance
hybrid answer                  -> GUIDANCE_SYNTHESIS -> hybrid_security_answer
public repository analysis     -> EVIDENCE_ANALYSIS -> public_repository_analysis
unsupported arbitrary work     -> ABSTAIN, no specialist
allowlist conflict             -> ABSTAIN, no specialist
```

The first authenticated observations must be preserved before any prompt, model, or topology tuning.

## Cost boundary

The canonical runtime report records observed tokens but keeps `inference_cost_usd = null`.

Cost is derived only after the real replay from observed usage and contemporaneous verified Bedrock pricing. Pricing is external evidence, not model output and not part of the provider invocation identity.

## CI and credential boundary

CI validates contract behavior, strict typing, tests, and the local CLI entrypoint only. It does not call Bedrock.

The authenticated real replay uses the existing human IAM Identity Center path, currently represented operationally by the `opslens-bootstrap` profile. This gate does not justify expanding GitHub OIDC trust, deploy-role permissions, AWS resources, or IAM policies merely to obtain a benchmark.

## Alternatives rejected

### Let triage choose a capability directly

Rejected because specialization proposal and capability authorization are distinct authority boundaries.

### Let the model author arbitrary handoff messages or executable context

Rejected because it would expand the proposal surface into hidden execution authority and complicate provenance.

### Use different models for triage and specialist in the first experiment

Rejected because changing topology and model quality simultaneously would confound the first comparison.

### Execute a capability after specialist authorization

Rejected because Gate 12.3 is measuring reasoning topology and coordination overhead. Executor behavior would add another experimental variable.

### Add retries or fallback to improve the benchmark

Rejected because adaptive recovery would hide first-pass model behavior and distort latency/cost evidence.

### Use an LLM judge

Rejected because deterministic evaluation already has explicit expected routing and capability semantics; metric authority remains code-owned.

### Run authenticated Bedrock inference in feature-branch CI

Rejected because it would require unnecessary credential/IAM expansion and mix cloud runtime evidence with the offline quality gate.

### Adopt a generic agent framework now

Rejected because a graph/runtime framework would add complexity before evidence shows that even the bounded two-model topology is worth retaining.

## Consequences

Positive:

- topology value can be compared against the exact Phase 11 reference;
- routing and specialist quality failures remain independently diagnosable;
- model outputs cannot broaden deterministic authority;
- first-pass provider latency, token usage, retries, and request IDs become auditable evidence;
- the project can reject multi-agent complexity without sunk-cost bias.

Costs:

- successful handoff cases require two model invocations;
- the experiment adds a second prompt/parser/evidence surface;
- a human-authenticated replay is required before the gate can complete;
- pricing must be verified separately after runtime usage exists.

## AWS / IAM / runtime impact before the real replay

```text
new AWS resources:          0
new IAM roles/policies:     0
CI model calls:             0
capability executions:      0
AgentCore:                  0
MCP:                        0
A2A:                        0
public runtime:             0
runtime-exposure authority: 0
```

## AIP-C01 learning connection

This gate exercises experiment design for generative AI systems: hold confounding variables constant, preserve deterministic authorization around model proposals, capture provider-neutral invocation provenance, measure latency/token/cost trade-offs, preserve first observations before tuning, and treat a more agentic topology as a hypothesis that can be rejected rather than as an architectural goal.
