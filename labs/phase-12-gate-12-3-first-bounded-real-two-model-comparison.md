# Phase 12 — Gate 12.3 — First Bounded Real Two-Model Comparison

## Status

```text
provider-neutral triage path:      COMPLETE
bounded two-model composition:     COMPLETE
frozen real corpus/evaluator:      COMPLETE
offline contract CI:               COMPLETE
real Bedrock corpus replay:        COMPLETE
observed token/latency/cost:       COMPLETE
gate completion:                   READY FOR FINAL CI / MERGE REVIEW
```

Gate 12.3 now has its first authenticated Amazon Bedrock replay preserved before any prompt, model, or topology tuning. The result is a successful controlled experiment, not evidence that the two-model topology should be retained.

## Purpose

Gate 12.1 froze deterministic specialization. Gate 12.2 froze deterministic comparison semantics before a second model existed. Gate 12.3 adds the first real two-model experiment while keeping execution and authorization authority in code.

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

Raw model output is not persisted in the canonical runtime report or historical evidence artifact.

`inference_cost_usd` remains `null` in the canonical report. Cost is derived separately from observed token usage and contemporaneous verified pricing so pricing cannot alter the content-addressed model-evidence identity.

## First authenticated Bedrock replay

Historical evidence is preserved at:

```text
labs/evidence/phase-12-gate-12-3-first-real-two-model-comparison-v1.json
```

The replay was executed on 2026-09-08 from exact source head:

```text
34cafc8a97952a4966208334ca09c47ce259a929
```

Observed terminal state:

```text
exit code:                         0
stderr:                            empty
quality:                           6 / 6
triage decision matches:           6 / 6
specialization matches:            6 / 6
handoff admission matches:         6 / 6
target-scope matches:              6 / 6
non-broadening cases:              6 / 6
specialist decision matches:       6 / 6
specialist capability matches:     6 / 6
specialist authorization matches:  6 / 6
runtime-bounds compliant:          6 / 6
model invocations:                 10
SDK retries:                       0
capability executions:             0
```

The two abstention cases stopped after the triage invocation. The four admitted handoff cases invoked exactly one specialist. Every provider response ended with `end_turn`; no application retry, fallback, or capability executor participated.

Content-addressed experiment identities:

```text
dataset_sha256:
0439ebaa6215b2de7eaa82624188576743b5a50cc847137e04dc97ee7a199be7

report_sha256:
45edf58ac911ec14e872a00464dad5d5311d82165d6b8ac4321da4a0dc5ad09b
```

## Measured token and latency evidence

Observed aggregate token usage:

```text
triage input / output / total:      3582 / 120 / 3702
specialist input / output / total:  2206 / 74 / 2280
overall input / output / total:     5788 / 194 / 5982
```

For direct task-level latency comparison with the Phase 11 one-call reference, sequential triage and specialist latencies are summed for handoff cases while abstention cases contain triage latency only.

```text
provider latency sum across cases:     9243 ms
provider latency mean per case:        1540.5 ms
provider latency median per case:      1694.0 ms
client elapsed sum across cases:       12535 ms
client elapsed mean per case:          2089.166667 ms
client elapsed median per case:        2135.0 ms
```

These are experiment observations, not an SLA claim.

## Contemporaneous pricing and derived cost

Pricing was revalidated on 2026-09-08 for the fixed US geographic cross-region Claude Haiku 4.5 profile. The applied rates are:

```text
input:   USD 1.10 / 1M tokens
output:  USD 5.50 / 1M tokens
```

Authoritative/current references used by the evidence artifact:

- AWS Bedrock Claude Haiku 4.5 model card;
- AWS Bedrock regional/model compatibility documentation, which identifies the `us.` profile as geographic cross-region inference;
- AWS Machine Learning Blog cost assessment listing Claude Haiku 4.5 on Bedrock at USD 1.10/1M input and USD 5.50/1M output tokens.

Derived arithmetic:

```text
triage input:       3582 * 1.10 / 1,000,000 = USD 0.0039402
triage output:       120 * 5.50 / 1,000,000 = USD 0.0006600
triage total:                                  USD 0.0046002

specialist input:   2206 * 1.10 / 1,000,000 = USD 0.0024266
specialist output:    74 * 5.50 / 1,000,000 = USD 0.0004070
specialist total:                              USD 0.0028336

two-model total:                               USD 0.0074338
```

The historical Phase 11 evidence used the same verified US geographic rates on 2026-09-07, but Gate 12.3 revalidated rather than assuming those rates remained current.

## Direct comparison with the frozen Phase 11 reference

The frozen single-agent reference is:

```text
quality:                    6 / 6
model invocations:          6
input / output / total:     3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
SDK retries:                0
capability executions:      0
derived cost:               USD 0.0041921
```

Gate 12.3 measured:

```text
quality:                    6 / 6        no lift
model invocations:          10           +66.67%
input tokens:               5788         +75.87%
output tokens:              194          +86.54%
total tokens:               5982         +76.20%
provider latency median:    1694.0 ms    +109.26%
client elapsed median:      2135.0 ms    +118.41%
SDK retries:                0            unchanged
capability executions:      0            unchanged
derived cost:               USD 0.0074338 +77.33%
```

The triage stage alone cost approximately USD 0.0046002 for the six cases, already about 9.73% more than the entire Phase 11 six-case single-agent reference.

## Experimental interpretation

Gate 12.3 proves that the bounded two-model topology can preserve the frozen `6/6` behavior while maintaining all deterministic authority and runtime bounds. It also produces no measured quality improvement on this corpus.

The measured coordination overhead is material: more calls, substantially more tokens, roughly double task-level median latency, higher inference cost, and a larger failure surface. The deterministic scope-narrowing property remains valid and all non-broadening checks pass, but this experiment does not demonstrate that a second model call is required to obtain that property.

Therefore Gate 12.3 should be merged as historical experiment evidence, not promoted directly into the retained architecture. A subsequent measured decision gate should decide whether to reject, defer, or redesign the two-model topology using these observations rather than architectural preference.

## Offline CI checkpoint

The final pre-replay implementation checkpoint was:

```text
PR:                     #172
head:                   34cafc8a97952a4966208334ca09c47ce259a929
PR merge test commit:   8e90eabd918ec644c561e8882b2eab0353b72703
Multi-Agent CI:         34178941178 / run #30 / PASS
job:                    101913858248
offline fixture:        PASS
real CLI --help smoke:  PASS
Ruff:                   PASS
Pyright strict:         0 errors / 0 warnings / 0 informations
pytest multi-agent:     33 passed in 0.34s
```

A new exact-head CI is required after committing the historical real-run evidence and this lab update. Only that final head may be promoted for merge.

## Non-goals preserved

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
