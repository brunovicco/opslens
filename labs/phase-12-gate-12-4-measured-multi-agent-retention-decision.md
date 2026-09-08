# Phase 12 — Gate 12.4 — Measured Multi-Agent Retention Decision

## Status

```text
frozen evidence review:             COMPLETE
new model experiment:               NOT AUTHORIZED / NOT RUN
measured topology decision:         COMPLETE
single-agent reference:             RETAIN
Gate 12.1 deterministic handoff:    RETAIN
Gate 12.3 two-model default:        DO NOT RETAIN
historical Gate 12.3 evidence:      PRESERVE
next gate:                          Phase 12 Gate 12.5 closeout
```

Gate 12.4 is intentionally a decision gate. It incurs no inference call and does not tune the successful Gate 12.3 routing behavior merely to justify a more complex topology.

## Decision question

```text
Does the measured specialization value justify the added
calls + tokens + latency + cost + failure surface + complexity?
```

For the first bounded experiment, the answer is **no**.

## Frozen inputs

Phase 11 historical evidence:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
corpus_sha256:
3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256:
724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Gate 12.3 historical evidence:

```text
labs/evidence/phase-12-gate-12-3-first-real-two-model-comparison-v1.json
dataset_sha256:
0439ebaa6215b2de7eaa82624188576743b5a50cc847137e04dc97ee7a199be7
report_sha256:
45edf58ac911ec14e872a00464dad5d5311d82165d6b8ac4321da4a0dc5ad09b
```

Gate 12.4 decision evidence:

```text
labs/evidence/phase-12-gate-12-4-retention-decision-v1.json
```

No earlier evidence file was rewritten.

## Measured comparison

```text
metric                     Phase 11       Gate 12.3        delta
quality                    6/6            6/6              no lift
model invocations          6              10               +66.67%
input tokens               3291           5788             +75.87%
output tokens              104            194              +86.54%
total tokens               3395           5982             +76.20%
provider latency median    809.5 ms       1694.0 ms        +109.26%
client elapsed median      977.5 ms       2135.0 ms        +118.41%
SDK retries                0              0                 unchanged
capability executions      0              0                 unchanged
derived cost               USD 0.0041921  USD 0.0074338    +77.33%
```

Gate 12.3 routing itself was correct:

```text
triage decision matches:           6/6
specialization matches:            6/6
handoff admission matches:         6/6
target-scope matches:              6/6
non-broadening cases:              6/6
specialist decision matches:       6/6
specialist capability matches:     6/6
specialist authorization matches:  6/6
runtime-bounds compliant:          6/6
```

There is therefore no measured routing-quality defect to fix in Gate 12.4. The observed issue is that the second model call did not buy a measured quality or authority benefit on the frozen corpus.

## Retention decision

Retain the Phase 11 single-agent reasoning path as the default/reference measured architecture:

```text
SingleAgentTask
 -> one bounded model invocation
 -> transient {decision, capability}
 -> deterministic parser
 -> deterministic capability authorization
 -> STOP before capability execution for reasoning-quality evaluation
```

Retain the Gate 12.1 deterministic specialization boundary as a reusable authority/scope primitive:

```text
source task
 -> code-owned specialization mapping
 -> deterministic capability intersection
 -> narrowed specialist task
```

Do **not** retain Gate 12.3 as the default reasoning topology:

```text
source task
 -> extra model triage invocation
 -> specialization proposal
 -> deterministic handoff admission
 -> specialist model invocation
```

Gate 12.3 remains in the repository as historical experimental implementation and evidence. This is deliberate preservation, not accidental dead-code endorsement.

## Why deterministic specialization survives

The important security property is not "two agents." It is the code-owned reduction in the reasoning surface.

Gate 12.1 proved that OpsLens can map a closed specialization to a closed capability subset and deterministically intersect that subset with the source task's admitted allowlist.

That boundary remains valuable because:

- the model cannot invent a specialization;
- the model cannot broaden the source capability surface;
- handoff admission remains deterministic;
- capability authorization remains deterministic;
- the narrowed scope can be reused by a future topology if evidence justifies one.

None of those properties require OpsLens to pay for an extra triage model call by default.

## Why no rescue experiment runs now

A second experiment would need a new hypothesis. Gate 12.3 already answered the question "does adding this bounded triage model preserve quality and justify itself on the frozen six-case baseline?"

Observed result:

```text
quality preserved: yes
material measured lift: no
runtime/cost overhead: yes
```

Changing the prompt, using a smaller model, enabling caching, or adding fallback after seeing this result would be a new optimization experiment. Doing that merely to make the architecture look better would create post-hoc success criteria and sunk-cost bias.

Therefore:

```text
new model invocations in Gate 12.4: 0
new inference cost in Gate 12.4:     USD 0.00
```

A future experiment is allowed only after documenting a concrete falsifiable benefit target that Gate 12.3 did not measure.

## Failure-surface reasoning

Even though Gate 12.3 observed zero SDK retries and all calls succeeded, a second model invocation creates another independent runtime failure opportunity.

It adds another:

```text
provider request
response parsing boundary
schema validation boundary
latency contribution
token-cost contribution
provider-side failure point
client-side failure point
observability/evidence surface
maintenance surface
```

Zero observed failures in six cases is not evidence that those extra failure modes do not exist. The simpler retained architecture therefore has a lower structural failure surface unless a measured benefit justifies the extra path.

## Authority remains unchanged

Gate 12.4 does not move authority into or out of a model.

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
capability authorization != invocation
invocation != execution result
```

Phase 11 remains the retained model reasoning reference. Gate 11.2 remains the separate typed capability invocation/result-admission authority.

Gate 12.1 remains the deterministic specialization/handoff authority if a future topology needs it.

## AWS / IAM / runtime impact

```text
real model calls:             0
new inference cost:           USD 0.00
new AWS resources:            0
new IAM roles/policies:       0
GitHub OIDC trust changes:    0
capability executions:        0
AgentCore:                    0
MCP:                          0
A2A:                          0
public runtime:               0
runtime-exposure authority:   0
Governed LLM Gateway changes: 0
```

## Architecture record

```text
docs/adr/0045-do-not-retain-two-model-topology-without-measured-lift.md
```

## Decision evidence

```text
labs/evidence/phase-12-gate-12-4-retention-decision-v1.json
```

The decision artifact binds the exact Phase 11 and Gate 12.3 evidence identities and records the retained/rejected boundaries explicitly.

## AIP-C01 learning checkpoint

This gate demonstrates that GenAI architecture selection is an optimization problem under quality, latency, cost, reliability, security, and maintainability constraints. A system that uses fewer model calls but preserves measured quality and deterministic governance can be the stronger production design even when a multi-agent alternative is technically successful.

It also reinforces experiment integrity: freeze the baseline, measure the changed variable, preserve the result, and do not change the success criterion after seeing the evidence.

## Next gate

```text
Phase 12 — Gate 12.5: Multi-Agent Phase Closeout
```

Gate 12.5 should close Phase 12 around the measured conclusion:

```text
retained runtime reasoning reference: Phase 11 single-agent
retained multi-agent mechanism:       deterministic specialization/handoff contract
non-retained default topology:        Gate 12.3 two-model triage + specialist
historical experiment evidence:       preserved
```

Phase 12 closeout must not imply that MCP, AgentCore, A2A, public runtime, capability execution, or runtime exposure have been implemented. Those remain independent future phases and proof obligations.
