# ADR 0046 — Close Phase 12 Around the Measured Architecture

- Status: Accepted
- Date: 2026-09-08
- Phase: 12 — Multi-Agent Architecture
- Gate: 12.5 — Multi-Agent Phase Closeout

## Context

Phase 12 began with a deliberately narrow question: can OpsLens introduce specialization semantics without moving deterministic authority into agents, and does adding a second model call produce enough measured value to justify its cost and complexity?

The phase answered that question incrementally.

Gate 12.1 froze deterministic specialization/handoff authority. Gate 12.2 froze comparison criteria before the second model call existed. Gate 12.3 ran the first authenticated bounded two-model experiment. Gate 12.4 then made the topology-retention decision from frozen evidence without rescue tuning.

The phase therefore has enough evidence to close. Additional model experimentation would not be closeout work; it would be a new hypothesis and must be treated as a future gate.

## Decision

Close Phase 12 with the following retained architecture:

```text
retained runtime reasoning reference:
  Phase 11 single-agent bounded reasoning

retained Phase 12 mechanism:
  Gate 12.1 deterministic specialization/handoff boundary

retained evaluation discipline:
  Gate 12.2 deterministic comparison contract
```

Do not retain the Gate 12.3 model-driven triage-to-specialist topology as the default/reference reasoning path.

Preserve the complete Gate 12.3 implementation and evidence historically. Non-retention means "not promoted to the retained architecture," not "erase the experiment."

## Evidence trail

### Gate 12.1 — deterministic specialization/handoff

```text
PR #166
merge SHA: eceed76a6cfc5d7e28e88dfdc503b4863b526ba0
ADR: 0042
```

Retained property:

```text
source task
 -> code-owned specialization mapping
 -> deterministic intersection with source allowed_capabilities
 -> narrowed specialist task
```

### Gate 12.2 — frozen comparative evaluation

```text
PR #169
merge SHA: 865ba70c813711cb88da9ac7308c8966ff983fd0
ADR: 0043

dataset_sha256:
1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491

report_sha256:
0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
```

Synthetic fixture conformance remains evaluator/contract evidence only.

### Gate 12.3 — first real two-model experiment

```text
PR #172
merge SHA: f51cb70ad070716e774419b8d2c62918d3e65210
ADR: 0044

dataset_sha256:
0439ebaa6215b2de7eaa82624188576743b5a50cc847137e04dc97ee7a199be7

report_sha256:
45edf58ac911ec14e872a00464dad5d5311d82165d6b8ac4321da4a0dc5ad09b
```

Observed result:

```text
quality:                    6/6
model invocations:          10
input/output/total tokens:  5788 / 194 / 5982
provider latency median:    1694.0 ms
client elapsed median:      2135.0 ms
SDK retries:                0
capability executions:      0
derived cost:               USD 0.0074338
```

### Gate 12.4 — measured retention decision

```text
PR #175
merge SHA: fabe8128d1d6077e8de92225991b5e26c1b72ab3
ADR: 0045
```

Compared with the retained Phase 11 reference:

```text
quality:                    6/6 -> 6/6      no lift
model invocations:          6 -> 10         +66.67%
total tokens:               3395 -> 5982    +76.20%
provider latency median:    809.5 -> 1694   +109.26%
client elapsed median:      977.5 -> 2135   +118.41%
derived cost:               0.0041921 -> 0.0074338 USD  +77.33%
SDK retries:                0 -> 0
capability executions:      0 -> 0
```

Gate 12.4 therefore retained the simpler single-agent reference and deterministic specialization boundary while rejecting the two-model topology as the default/reference path.

## Why the phase can close without another model run

There is no unresolved measured quality defect in the Gate 12.3 experiment. Routing, specialization, handoff admission, target-scope projection, specialist decision, specialist capability, authorization, and runtime bounds all matched the frozen corpus.

The decision problem is architectural efficiency, not model correctness.

Running another inference experiment merely to make the multi-agent topology cheaper or faster would introduce a new optimization hypothesis after the original experiment failed to demonstrate material benefit. That is outside closeout scope.

Phase 12 therefore closes with:

```text
new model invocations in closeout: 0
new inference cost in closeout:     USD 0.00
```

## Retained authority model

Phase 12 does not change the authority separation frozen through earlier phases:

```text
model proposal != deterministic admission
handoff proposal != handoff admission
handoff admission != capability authorization
capability authorization != invocation
invocation != execution result
```

Models can reason within closed proposal surfaces. Code remains the authority for scope, authorization, execution admission, evidence, metrics, and runtime truth.

## Phase 12 non-claims

Phase 12 did **not** prove or implement:

```text
multi-agent capability execution in a deployed runtime
public/deployed agent runtime
production agent SLOs
Amazon Bedrock AgentCore runtime behavior
MCP interoperability
A2A interoperability
runtime exposure / Amazon Inspector evidence
universal superiority of multi-agent architecture
model-owned handoff admission
model-owned capability authorization
```

These boundaries remain explicit so later phases cannot reinterpret Phase 12 evidence as proof of capabilities that were never exercised.

## Historical code disposition

The Gate 12.3 two-model implementation remains in the repository because:

- its evidence is reproducible only if the bounded implementation remains inspectable;
- it provides a reference for future experiments;
- deleting it would erase useful negative/neutral architectural evidence;
- non-default experimental code can be valuable when its status is explicit.

It must not be silently wired into a default/public runtime without a new architecture decision and measured hypothesis.

## Next phase boundary

After Phase 12 state synchronization, the next roadmap phase is:

```text
Phase 13 — MCP
```

Phase 13 may expose already-bounded OpsLens capabilities through explicit MCP contracts, but it must not use MCP as a way to bypass capability authorization, deterministic evidence admission, or typed execution/result contracts.

MCP is an interoperability boundary, not new business authority.

Amazon Bedrock AgentCore and A2A remain later independent phases.

## Deferred Governed LLM Gateway integration

Long-lived OpsLens PR #89 remains separate cross-project work for **Phase 14 — Case 3 of `brunovicco/governed-llm-gateway`**.

Phase 12 closeout does not authorize modifying, rebasing, merging, or reusing that deferred PR. Any future reactivation must re-evaluate it against the then-current OpsLens architecture.

## AWS / IAM / runtime impact

```text
new model invocations:       0
new inference cost:           USD 0.00
new AWS resources:            0
new IAM roles/policies:       0
GitHub OIDC trust changes:    0
capability executions:        0
AgentCore:                    0
MCP implementation:          0
A2A implementation:          0
public runtime:               0
runtime-exposure authority:   0
Governed LLM Gateway changes: 0
```

## AIP-C01 learning connection

Phase 12 closes with a production-oriented lesson: successful multi-agent execution is not enough to justify multi-agent retention. Architecture selection must compare quality, token usage, latency, cost, reliability surface, security boundaries, maintainability, and operational complexity against a frozen simpler reference.

The strongest design can be the one that keeps deterministic specialization semantics while declining to pay for an additional model invocation that did not demonstrate measurable value.
