# ADR 0045 — Do Not Retain Two-Model Topology Without Measured Lift

- Status: Accepted
- Date: 2026-09-08
- Phase: 12 — Multi-Agent Architecture
- Gate: 12.4 — Measured Multi-Agent Retention Decision

## Context

Gate 12.3 completed the first authenticated bounded two-model experiment under the authority boundaries frozen by Gates 12.1 and 12.2.

The experiment intentionally held provider/model configuration constant and stopped before capability execution. It therefore measured the incremental effect of adding a model-driven specialization triage step before the existing bounded specialist reasoning path.

The frozen Phase 11 single-agent reference is:

```text
quality:                    6/6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
SDK retries:                0
capability executions:      0
derived cost:               USD 0.0041921
report_sha256:              724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

The first real Gate 12.3 two-model result is:

```text
quality:                    6/6
model invocations:          10
input/output/total tokens:  5788 / 194 / 5982
provider latency median:    1694.0 ms
client elapsed median:      2135.0 ms
SDK retries:                0
capability executions:      0
derived cost:               USD 0.0074338
report_sha256:              45edf58ac911ec14e872a00464dad5d5311d82165d6b8ac4321da4a0dc5ad09b
```

Measured deltas are material:

```text
quality lift:               none on the frozen corpus
model invocations:          +66.67%
input tokens:               +75.87%
output tokens:              +86.54%
total tokens:               +76.20%
provider latency median:    +109.26%
client elapsed median:      +118.41%
derived inference cost:     +77.33%
SDK retries:                unchanged at 0
capability executions:      unchanged at 0
```

The deterministic Gate 12.1 handoff boundary did prove a useful property: code can reduce a source task's reasoning surface from four allowed capabilities to at most two specialist capabilities without transferring handoff admission or capability authorization into a model.

That property is distinct from requiring a second model invocation.

## Decision

Do **not** retain the Gate 12.3 two-model triage-to-specialist topology as the default or reference OpsLens reasoning architecture.

Retain instead:

```text
Phase 11 single-agent bounded reasoning
as the default/reference measured reasoning path
```

Also retain:

```text
Gate 12.1 deterministic specialization/handoff contract
as a reusable deterministic authority boundary
```

Preserve the complete Gate 12.3 implementation, tests, ADR, lab, and runtime evidence as historical experiment evidence. The experiment remains auditable and reproducible, but it is not promoted to the default architecture.

No new model experiment is authorized by Gate 12.4.

A future two-model or multi-agent experiment requires a new, explicit, falsifiable benefit hypothesis that Gate 12.3 did not already test. It must define its success criterion before execution and must compare against the retained Phase 11 reference.

## Why the decision separates handoff from topology

The retained deterministic boundary is:

```text
source task
 -> code-owned specialization mapping
 -> deterministic scope intersection
 -> narrowed specialist task
```

The rejected default topology is:

```text
source task
 -> extra model triage call
 -> specialization proposal
 -> deterministic handoff admission
 -> second specialist model call
```

The first boundary is an authority/scope mechanism. The second is a runtime topology with measurable cost and failure consequences.

Conflating them would create a false choice between "keep multi-agent" and "lose specialization safety." OpsLens can preserve deterministic specialization semantics without paying for a second model invocation on every admitted handoff.

## Evidence rule

The decision is bound to exact historical evidence:

```text
Phase 11 corpus_sha256:
3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc

Phase 11 report_sha256:
724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145

Gate 12.3 dataset_sha256:
0439ebaa6215b2de7eaa82624188576743b5a50cc847137e04dc97ee7a199be7

Gate 12.3 report_sha256:
45edf58ac911ec14e872a00464dad5d5311d82165d6b8ac4321da4a0dc5ad09b
```

The immutable decision summary is preserved at:

```text
labs/evidence/phase-12-gate-12-4-retention-decision-v1.json
```

## No rescue tuning

Gate 12.4 does not tune prompts, swap models, add caching, add fallback, or change the corpus merely to make the two-model topology appear competitive.

Doing so after observing the first result without a new predeclared hypothesis would weaken experiment credibility and create sunk-cost bias.

A new experiment is allowed only when a concrete benefit target exists, for example a previously unmeasured quality/safety domain where deterministic specialization plus one model cannot satisfy the requirement. That hypothesis must be frozen before changing the implementation.

## Authority consequences

This decision changes no deterministic authority.

```text
model proposal != handoff admission
handoff admission != capability authorization
capability authorization != invocation
invocation != execution result
```

The retained Phase 11 reasoning path still cannot execute a capability directly. Gate 11.2 remains the typed invocation/result-admission authority.

The Gate 12.1 specialization mapping remains code-owned. Model output never becomes scope or execution authority.

## Alternatives rejected

### Retain the two-model path because it passed 6/6

Rejected because matching the reference is not improvement. The experiment added material cost, latency, token usage, failure surface, and complexity without measured quality lift.

### Tune the triage prompt immediately

Rejected because the current issue is not a measured routing-quality failure. Triage achieved all expected decisions/specializations. Prompt tuning would optimize overhead rather than address a concrete quality defect.

### Switch the triage model to a cheaper/faster model

Rejected for this gate because it introduces a new experiment after the topology already failed to demonstrate value. A model-switch experiment would require its own predeclared hypothesis and acceptance criteria.

### Keep the two-model topology for architectural flexibility

Rejected because unused flexibility is not a measurable benefit and increases maintenance/failure surface.

### Remove all Gate 12 multi-agent code

Rejected because historical experiment evidence must remain reproducible and because the deterministic specialization/handoff boundary is independently useful.

### Treat deterministic capability narrowing as proof that the second model is beneficial

Rejected because the narrowing is enforced by code after handoff admission. Gate 12.3 did not show that a separate triage model invocation is required to obtain that deterministic property.

## Consequences

Positive:

- the retained reasoning reference remains simpler and cheaper;
- measured evidence, not architectural fashion, decides topology retention;
- deterministic specialization semantics remain available without making the second model call default;
- the project avoids post-hoc rescue tuning and sunk-cost bias;
- historical multi-agent evidence remains preserved for future comparison;
- Phase 13 can start from stable authority boundaries rather than an unjustified runtime topology.

Costs:

- the real two-model implementation remains in the repository as non-default experimental code that must stay clearly documented;
- a future specialization-quality hypothesis will require a new explicit gate rather than silently reactivating Gate 12.3;
- multi-agent demos must explain why the experiment was rejected as default rather than presenting complexity as a feature.

## AWS / IAM / runtime impact

```text
new model invocations:       0
new inference cost:           USD 0.00
new AWS resources:            0
new IAM roles/policies:       0
capability executions:        0
AgentCore:                    0
MCP:                          0
A2A:                          0
public runtime:               0
runtime-exposure authority:   0
Governed LLM Gateway changes: 0
```

## AIP-C01 learning connection

This decision demonstrates production GenAI engineering discipline: benchmark against a frozen reference, separate architectural mechanisms from runtime topology, account for token/latency/cost trade-offs, preserve failed or non-beneficial experiments, avoid post-hoc metric changes, and prefer the simplest architecture that satisfies measured requirements.
