# Phase 12 — Gate 12.3 — First Bounded Real Two-Model Comparison

## Status

```text
provider-neutral triage path:      COMPLETE
bounded two-model composition:     COMPLETE
frozen real corpus/evaluator:      COMPLETE
offline contract CI:               COMPLETE
real Bedrock corpus replay:        PENDING
observed token/latency/cost:       PENDING
gate completion:                   BLOCKED ON REAL BASELINE
```

Gate 12.3 is intentionally not complete until the first authenticated Bedrock replay is preserved. Offline tests prove contract conformance and deterministic authority boundaries; they do not prove real multi-agent model quality.

## Purpose

Gate 12.1 froze deterministic specialization. Gate 12.2 froze deterministic comparison semantics before a second model existed. Gate 12.3 now adds the first real two-model experiment while keeping execution and authorization authority in code.

```text
SingleAgentTask
 -> one triage model invocation
 -> transient specialization-only proposal
 -> deterministic parser
 -> existing deterministic handoff admission
 -> ABSTAIN / rejected? STOP
 -> narrowed SpecialistAgentTask
 -> one specialist model invocation
 -> existing deterministic capability authorization
 -> STOP before capability execution
```

The experiment is allowed to show that the two-model topology is not worth keeping.

## Frozen hard bounds

```text
maximum model invocations per task: 2
maximum handoffs per task:          1
maximum specialist capability width: 2
adaptive application retries:       0
adaptive fallbacks:                  0
capability executions:               0
```

For an admitted handoff, exactly two model calls are expected. Triage abstention or deterministic handoff rejection must not invoke the specialist.

## Fixed provider configuration

Both stages use the same fixed provider/model profile as the Phase 11 single-agent reference:

```text
provider:       Amazon Bedrock Converse
region:         us-east-1
model/profile:  us.anthropic.claude-haiku-4-5-20251001-v1:0
temperature:    0.0
streaming:      no
tools:          disabled
```

Holding the model fixed isolates specialization topology as the primary changed variable.

## Triage proposal boundary

The triage model may emit only:

```json
{
  "decision": "handoff | abstain",
  "target_specialization": "evidence_analysis | guidance_synthesis | null"
}
```

It cannot select capabilities, provider/model, arguments, SQL, URLs, shell commands, credentials, retry/fallback policy, tools, or execution results.

Raw model text is transient and untrusted. Deterministic parsing creates the existing `MultiAgentHandoffProposal`; deterministic Gate 12.1 code owns handoff admission and target scope.

## Specialist boundary

An admitted handoff creates a narrowed `SpecialistAgentTask`. The specialist then reuses the existing Phase 11 reasoning path:

```text
specialist task
 -> transient {decision, capability}
 -> deterministic parser
 -> AgentActionProposal
 -> deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | rejection
 -> STOP
```

No capability executor participates in Gate 12.3.

## Frozen real-comparison corpus

The new fixture is:

```text
tests/fixtures/multi_agent/golden_multi_agent_real_comparison_v1.json
```

It binds exact historical evidence:

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

The six tasks remain directly comparable with the previous evaluation layers:

1. structured security question -> `EVIDENCE_ANALYSIS` -> `structured_security_query`;
2. knowledge guidance -> `GUIDANCE_SYNTHESIS` -> `knowledge_guidance`;
3. hybrid answer -> `GUIDANCE_SYNTHESIS` -> `hybrid_security_answer`;
4. public repository analysis -> `EVIDENCE_ANALYSIS` -> `public_repository_analysis`;
5. unsupported arbitrary execution -> triage `ABSTAIN`, no specialist;
6. allowlist conflict -> triage `ABSTAIN`, no specialist.

## Deterministic evaluation contract

`multi-agent-real-comparison:v1` records decomposed dimensions for every case:

```text
triage_decision_match
specialization_match
admission_match
target_scope_match
non_broadening
specialist_decision_match
specialist_capability_match
specialist_authorization_match
runtime_bounds_compliant
passed
```

The report also aggregates observed invocation counts, triage/specialist/total token usage, provider/client latency, SDK retries, and capability-execution count.

No LLM judge owns metric authority.

## Evidence minimization

Each provider invocation admits content-minimized runtime evidence such as:

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

Raw model output is not persisted in the canonical runtime report or CLI output.

`inference_cost_usd` remains `null` in the canonical report. Cost is derived only after real token usage exists and contemporaneous Bedrock pricing has been verified separately.

## Offline CI checkpoint

The provider-neutral core reached a green offline checkpoint before adding the real CLI/documentation layer:

```text
PR:                     #172
head:                   d60b41c2834923a11eab4cf813d24271c3d8bdab
Multi-Agent CI:         34178484611 / run #22 / PASS
job:                    101912528188
offline fixture:        PASS
Ruff:                   PASS
Pyright strict:         PASS
pytest multi-agent:     PASS
```

This is historical implementation evidence, not the final Gate 12.3 head. The final offline-pre-replay head must be revalidated after the CLI, workflow, ADR, and lab changes.

## Real replay entrypoint

The bounded runtime CLI is:

```text
scripts/run_multi_agent_real_comparison.py
```

It exposes only local credential-profile and frozen-dataset path options. It does not expose provider, model, region, retry, fallback, or capability-execution selection.

CI executes only `--help` as an import/entrypoint smoke test. CI does not invoke Bedrock.

## Existing human AWS identity path

Use the already established IAM Identity Center profile. Do not create credentials, broaden the deploy role, or change GitHub OIDC trust merely for this experiment.

Refresh the existing profile:

```bash
aws sso login --profile opslens-bootstrap
```

Confirm the effective session:

```bash
aws sts get-caller-identity \
  --profile opslens-bootstrap \
  --region us-east-1
```

Then run the frozen real corpus:

```bash
PYTHONPATH=src uv run python scripts/run_multi_agent_real_comparison.py \
  --profile opslens-bootstrap \
  > /tmp/opslens-gate12-3-two-model.json \
  2> /tmp/opslens-gate12-3-two-model.stderr

exit_code=$?

echo "exit_code=$exit_code"

echo
echo "STDERR:"
cat /tmp/opslens-gate12-3-two-model.stderr

echo
echo "RESULT:"
cat /tmp/opslens-gate12-3-two-model.json
```

Return the complete `exit_code`, stderr, and JSON evidence for analysis.

## First-observation preservation rule

The first authenticated replay is historical evidence even when model quality is imperfect.

```text
exit 0 -> all frozen cases passed
exit 2 -> real model-quality mismatch; preserve before tuning
exit 1 -> runtime/environment failure; diagnose without fabricating model evidence
```

If a real Bedrock response exists but one or more cases fail, preserve the complete content-minimized observation set before changing prompts, model configuration, or topology.

If the request fails before Bedrock returns a provider response, do not claim token usage, request IDs, provider latency, model quality, or inference cost.

## Pricing step after successful provider evidence

After a real replay produces observed tokens:

1. preserve the first runtime evidence;
2. verify contemporaneous Bedrock pricing for the fixed model/profile from an authoritative current source;
3. derive cost only from the observed token counts;
4. keep the pricing source and arithmetic separate from provider invocation identity;
5. compare the measured two-model overhead against the frozen Phase 11 single-agent reference.

The Phase 11 historical cost must not be reused as if it were current pricing.

## Decision rule

The two-model topology is not automatically retained if it gets `6/6`.

If final quality remains equal to the Phase 11 reference while model calls, token use, latency, cost, failure surface, and complexity materially increase without a demonstrated benefit, the next decision gate should reject or defer the topology.

## Non-goals

```text
capability execution
recursive delegation
agent loops
generic agent framework
model-authored executable context
new AWS resources
unjustified IAM expansion
AgentCore
MCP
A2A
public agent runtime
runtime-exposure authority
Governed LLM Gateway integration
modifying deferred PR #89
```

## AIP-C01 learning checkpoint

Gate 12.3 turns agent architecture into a controlled experiment: deterministic authority boundaries remain explicit, provider telemetry becomes provenance rather than control, retries/fallbacks are bounded to expose first-pass behavior, cost follows measured token evidence, and a more complex agent topology must justify itself against an existing reference rather than being accepted because it is more agentic.
