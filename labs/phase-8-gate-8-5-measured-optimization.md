# Phase 8 Gate 8.5 — Measured Optimization Decision

_Date: 2026-09-06_

## Objective

Make one measured and reversible optimization decision from the immutable Gate 8.4 real Bedrock baseline without weakening routing, evidence admission, structured-fact authority, or citation authority.

Starting point:

```text
main:       d484edfb7ac64e2c4a2f4b105fcb23ff257395cb
issue:      #117
branch:     feat/phase8-measured-optimization
hypothesis: H8.5-01
experiment: hybrid-optimization:h8.5-01-v1
```

Frozen dataset:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

The fixture and its human-adjudicated support/citation targets remained unchanged.

## Immutable Gate 8.4 baseline

Evidence:

```text
labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json
```

Measured result:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

Model-call totals:

```text
input tokens:   4150
output tokens:   289
total tokens:   4439
```

## Measured weakness

The only failing synthesis-quality case in the frozen fixture was the semantic-noise case:

```text
question:
How should I review transitive dependency changes after upgrading the vulnerable package?

S1 / rank 1
clean-environment guidance
admitted evidence, but NOT a fixture support/citation target

S2 / rank 2
transitive lockfile review
expected support/citation target
```

The Gate 8.4 model output included a correct S2 claim and a second generally useful S1 claim. Output admission correctly allowed both IDs because both were admitted evidence. The independent evaluator correctly scored the extra S1 claim as a groundedness/citation miss.

Preserved lesson:

```text
admission != semantic support
retrieval rank != groundedness
allowlisted citation != correct citation target
```

The required S2 evidence was already retrieved and admitted, so H8.5-01 tested the smallest downstream intervention rather than modifying retrieval.

## H8.5-01 — prompt-only hypothesis

Hypothesis:

> Explicitly requiring the smallest sufficient answer, direct relevance to the user's requested task for every claim, and omission of ancillary guidance will remove the extra S1 claim while preserving all deterministic authority boundaries.

Candidate prompt policy:

```text
hybrid-synthesis-prompt:h8.5-01-v1
```

Runtime default kept frozen as:

```text
hybrid-synthesis-prompt:v1
```

H8.5-01 changed only trusted synthesis instructions about answer scope and direct relevance. It did not change:

- the frozen dataset or support/citation targets;
- Gate 8.1 routing;
- Gate 8.2 evidence admission or completeness;
- structured `F*` fact projection;
- semantic `S*` evidence contents, order, ranks, or scores;
- output JSON Schema;
- model, Region, temperature, or max tokens;
- one-call-per-eligible-case budget;
- unsupported runtime-exposure behavior;
- IAM or AWS infrastructure.

Bedrock profile remained:

```text
region:      us-east-1
model:       us.anthropic.claude-haiku-4-5-20251001-v1:0
Converse:    non-streaming
tools:       none
temperature: 0.0
maxTokens:   2048
```

## Predeclared decision rule

Required non-regression guardrails:

```text
route_accuracy                        == 1.0
structured_fact_correctness           == 1.0
abstention                            == 1.0
planned_case_count                    == 6
synthesis_invocation_attempt_count    == 3
admitted_model_execution_count        == 3
all successful stop reasons           == end_turn
all successful SDK retry attempts     == 0
cost                                  == UNMEASURED / null
```

Quality target:

```text
semantic_groundedness == 1.0
citation_correctness  == 1.0
```

All targets must pass for `ACCEPT`; otherwise the candidate is `REJECT`. Latency and token deltas are reported independently and are not collapsed into a composite score.

## Exact-head pre-run validation

The only real H8.5-01 execution was authorized after exact-head CI passed on:

```text
8ac47d0d45e58a0d12e15e6214e4f820614ee19f
```

Python CI #341 / run `34065316124` passed all six repository slices. The hybrid retrieval slice passed:

```text
uv lock --check     PASS
Ruff                PASS
Pyright strict      PASS — 0 errors, 0 warnings
pytest              PASS — 73 passed
```

The operator then used a clean SSO credential path. STS preflight passed before the candidate invocation.

## Immutable H8.5-01 runtime evidence

The single real candidate run completed successfully at the execution level and is preserved at:

```text
labs/evidence/phase-8-gate-8-5-h85-01-first-run-v1.json
```

Execution facts:

```text
complete:                             true
planned_case_count:                   6
synthesis_invocation_attempt_count:   3
admitted_model_execution_count:       3
all stop reasons:                     end_turn
all SDK retry attempts:               0
region:                               us-east-1
model:                                us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Deterministic non-regression metrics:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
abstention:                   1.0
```

The unsupported runtime-exposure case still abstained with zero model calls. The incomplete structured-evidence case still rejected before synthesis with zero model calls. Structured-only output remained deterministic and model-free.

## Candidate quality result

Measured H8.5-01 result:

```text
semantic_groundedness:  0.6666666666666666
citation_correctness:   0.6666666666666666
latency_ms:             2997.0
cost:                   UNMEASURED / null
```

The quality target was therefore not met.

The semantic-noise case still produced two claims:

```text
claim 1 -> S2 / transitive-lock-review
           directly answers the requested task

claim 2 -> S1 / clean-environment-noise
           ancillary guidance, not a frozen support/citation target
```

The candidate prompt did not eliminate the exact failure observed in Gate 8.4.

## Token and latency deltas

Compared with the immutable Gate 8.4 baseline:

```text
input tokens:   4456   delta +306
output tokens:   263   delta  -26
total tokens:   4719   delta +280
latency_ms:     2997.0 delta +37.666666666666515
```

The prompt-only candidate slightly reduced output tokens but increased input and total tokens because the added instructions were themselves model-visible. The small single-run latency increase is reported as runtime evidence, not treated as a statistically meaningful regression gate.

USD cost remains intentionally unmeasured because no deterministic versioned pricing contract exists in this phase.

## Decision

```text
H8.5-01 = REJECT
```

Machine-recorded rejection reasons:

```text
semantic_groundedness_target_not_met
citation_correctness_target_not_met
```

This is a completed and valid optimization experiment. The rejection is not an execution failure.

The result is important: a plausible prompt refinement did **not** improve the frozen end-to-end semantic/citation metrics. Therefore OpsLens must not promote the candidate merely because the instructions appear semantically better to a human reviewer.

## Runtime policy after rejection

Rollback requires no code mutation because the candidate was never promoted. The runtime default remains:

```text
HybridSynthesisPromptPolicy.GATE_8_4_V1
hybrid-synthesis-prompt:v1
```

The candidate remains versioned experiment code/evidence only.

No second H8.5-01 run is authorized. Editing the candidate after seeing this result and rerunning against the same six-case fixture would be adaptive prompt tuning. A materially different intervention requires a new versioned hypothesis and new predeclared acceptance rule.

## Architecture and AIP-C01 lesson

Gate 8.5 demonstrates why RAG optimization must be stage-specific and evaluation-driven:

```text
retrieval availability  -> succeeded
admission                -> succeeded
deterministic routing    -> succeeded
structured authority     -> succeeded
synthesis relevance      -> still imperfect
```

The correct response is not to silently change embeddings, vector search, reranking, prompt, and thresholds together. Each intervention needs a bounded hypothesis, immutable evaluation target, measured result, and explicit accept/reject decision.

It also demonstrates why output admission and semantic evaluation are separate controls: the S1 citation was validly allowlisted and grounded to an admitted chunk, yet still incorrect for the frozen question-specific citation target.

## Gate status

```text
COMPLETE — H8.5-01 REJECTED
```

Gate 8.6 is the next authorized Phase 8 step. Phase 9 remains blocked until Phase 8 closeout is recorded.
