# ADR 0040 — Preserve the measured reasoning baseline without premature optimization

- Status: Accepted
- Date: 2026-09-07
- Phase: 11 — Single-Agent Baseline
- Gate: 11.5 — Measured Optimization Decision

## Context

Gate 11.4 froze and measured the first real bounded single-agent reasoning baseline using Amazon Bedrock Converse with the fixed US geographic cross-Region Claude Haiku 4.5 inference profile.

The baseline is preserved in:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
```

Measured result:

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

Gate 11.5 exists to decide whether one bounded optimization experiment is justified by measured evidence. It is not an instruction to optimize unconditionally.

## Decision

Do **not** run a reasoning optimization experiment at Gate 11.5.

Preserve the Gate 11.4 reasoning prompt, model/profile, token bound, retry/fallback bounds, provider topology, and deterministic authority boundaries unchanged.

The Gate 11.5 outcome is therefore:

```text
optimization decision: NO-CHANGE
experiment authorized: NO
additional model calls: 0
new AWS resources:      0
new IAM changes:        0
```

## Evidence-based rationale

### Proposal quality

The frozen corpus has no observed proposal-quality failure: all six decision, capability, authorization, and bounds dimensions pass. There is therefore no measured correctness defect for prompt tuning or model replacement to target.

A `6/6` corpus is not a claim of universal model correctness. It is evidence that the current bounded acceptance corpus exposes no quality gap requiring an optimization experiment at this gate.

### Cost

The observed six-case inference cost is USD 0.0041921. The input-token component is USD 0.0036201 and the output-token component is USD 0.0005720.

Even the impossible upper bound of eliminating every measured input token would save only USD 0.0036201 for this six-case replay. OpsLens has no validated production request-volume baseline that would justify extrapolating that small experiment-level saving into a material business saving.

Therefore prompt compression, model switching, or caching is not justified by measured cost evidence.

### Latency

Median provider latency is 809.5 ms and median client elapsed latency is 977.5 ms.

The first call observed a materially larger client-minus-provider interval than the remaining calls. The evidence does not establish whether that difference is caused by credential refresh, connection establishment, local process initialization, provider behavior, or another factor, and there is only one such observation.

Therefore no client-warming, connection-reuse, or provider-routing optimization is authorized from that observation alone.

### Reliability and bounds

All six invocations completed with zero SDK retries and `end_turn`. Adding retries or fallback would therefore address no measured reliability defect while expanding behavior, cost, and authority surface.

### Caching

The baseline observed zero cache-read and zero cache-write input tokens. More importantly, Gate 11.4 does not contain a measured repeated-request workload or production traffic distribution. Introducing prompt caching without a measured reuse pattern would be speculative optimization.

## Candidate decisions

| Candidate | Decision | Evidence |
| --- | --- | --- |
| prompt compression | REJECT | no quality defect; absolute measured cost is already very low |
| model/profile switch | REJECT | no measured quality/cost/latency target justifies model-change risk |
| prompt caching | REJECT | no measured reuse pattern or traffic baseline |
| SDK/application retry | REJECT | observed retries are zero; would expand behavior/cost |
| provider fallback | REJECT | no provider failure in baseline; would expand topology and authority surface |
| client warm-up / connection reuse | DEFER | first-call gap exists, but cause and repeatability are unproven |
| capability/tool expansion | REJECT | not an optimization and violates the frozen authority boundary |

## Consequences

### Positive

- preserves the first measured baseline as a stable Phase 11 reference;
- avoids changing a `6/6` bounded-quality result without a target defect;
- avoids speculative provider/model/caching complexity;
- preserves deterministic authorization and execution boundaries;
- avoids unnecessary inference spend and additional real-model calls;
- makes "no change" a reviewable engineering decision rather than an implicit omission.

### Trade-off

Gate 11.5 does not explore whether another model, shorter prompt, cache strategy, or client lifecycle could improve isolated metrics. Those experiments remain available later if new measured evidence creates a material target.

## Revisit triggers

Re-open optimization only when at least one measured trigger exists, for example:

- proposal-quality regression on an expanded frozen corpus;
- materially higher observed provider/client latency across repeated runs;
- a real request-volume baseline that makes token cost material;
- measured repeated-prefix reuse that can support a cache hypothesis;
- observed provider reliability failures that justify a separately bounded resilience experiment.

Any future experiment must freeze its target metric and success threshold before implementation and must not rewrite the historical Gate 11.4 baseline.

## Authority boundary

This decision changes no authority contract:

```text
model output != trusted proposal
proposal != authorization
model selection != capability authority
reasoning evidence != execution evidence
```

`single-agent-authority:v1`, `single-agent-execution:v1`, `single-agent-evaluation:v1`, `single-agent-reasoning:v1`, `single-agent-reasoning-evaluation:v1`, and `operational-telemetry:v1` remain unchanged.

## AWS / IAM / integration boundary

Gate 11.5 introduces:

```text
real model calls:               0
new AWS resources:              0
new IAM roles/policies:         0
AgentCore:                      0
MCP:                            0
A2A:                            0
public agent runtime:           0
runtime-exposure authority:     0
Governed LLM Gateway changes:   0
```

Deferred OpsLens PR #89 remains outside this gate.

## AIP-C01 learning connection

This gate demonstrates an evaluation-first optimization discipline: measure quality, latency, token usage, retry behavior, and cost before changing model/runtime configuration. A mature generative-AI platform treats "no optimization justified" as a valid result when the measured benefit does not outweigh complexity, reliability, governance, or authority-boundary risk.
