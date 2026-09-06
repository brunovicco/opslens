# Phase 8 Gate 8.5 — Measured Optimization Decision

_Date: 2026-09-06_

## Objective

Make one measured and reversible optimization decision from the immutable Gate 8.4 real Bedrock baseline. Gate 8.5 does not authorize open-ended prompt tuning or upstream retrieval changes merely because one synthesis metric is imperfect.

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

The fixture and its human-adjudicated support/citation targets remain unchanged.

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

The only failing synthesis-quality case in the frozen fixture is the semantic-noise case:

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

This is synthesis selection/relevance behavior. The expected evidence was already retrieved and admitted, so the current observation does not justify changing retrieval before testing a smaller downstream intervention.

## H8.5-01 — prompt-only hypothesis

Hypothesis:

> Explicitly requiring the smallest sufficient answer, direct relevance to the user's requested task for every claim, and omission of ancillary guidance will remove the extra S1 claim while preserving all deterministic authority boundaries.

The candidate prompt policy is versioned as:

```text
hybrid-synthesis-prompt:h8.5-01-v1
```

The merged Gate 8.4 default remains:

```text
hybrid-synthesis-prompt:v1
```

The default v1 instructions remain byte-for-byte unchanged. H8.5-01 is opt-in only until the measured experiment is complete and explicitly accepted.

## Controlled variable

H8.5-01 changes exactly one conceptual variable: trusted synthesis instructions about answer scope and direct relevance.

It does **not** change:

- `hybrid-evaluation-golden:v1` or its SHA-256;
- support/citation targets;
- Gate 8.1 routing;
- Gate 8.2 evidence admission or `ALL_REQUIRED` completeness;
- structured `F*` fact projection;
- semantic `S*` evidence contents, order, ranks, or scores;
- output JSON Schema;
- model or inference profile;
- Region;
- temperature;
- max tokens;
- one-call-per-eligible-case budget;
- unsupported runtime-exposure behavior;
- IAM or AWS infrastructure.

Bedrock profile therefore remains:

```text
region:      us-east-1
model:       us.anthropic.claude-haiku-4-5-20251001-v1:0
Converse:    non-streaming
tools:       none
temperature: 0.0
maxTokens:   2048
```

## Why not reranking or hybrid keyword/vector search first?

The current frozen failure does not show retrieval unavailability:

```text
expected S2 -> retrieved -> admitted -> visible to model
```

Changing candidate budgets, reranking, metadata filters, embeddings, vector stores, or keyword+vector search would perturb an upstream stage that already supplied the required evidence. Such changes remain valid future hypotheses if measured evidence later supports them, but they are not the smallest intervention for H8.5-01.

This is an important evaluation principle for AIP-C01 and production RAG systems: optimize the stage that failed rather than changing the entire retrieval stack because an end-to-end score is below 1.0.

## Predeclared acceptance criteria

Non-regression guardrails:

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

The comparison is intentionally not a composite score.

Latency is reported independently and is not a hard acceptance gate from a single three-call sample. Input/output/total token deltas are reported as cost-pressure evidence. USD cost remains unmeasured unless a deterministic versioned pricing contract is introduced.

## Decision rule

```text
all guardrails pass
AND semantic_groundedness == 1.0
AND citation_correctness  == 1.0
 -> ACCEPT

otherwise
 -> REJECT
```

A completed REJECT is a valid Gate 8.5 result. It does not authorize another prompt edit under the same hypothesis.

Materially changing the candidate after observing the result would create adaptive tuning against the six-case fixture. A different intervention therefore requires a new versioned hypothesis rather than silently mutating H8.5-01.

## Rollback

Rollback is immediate and deterministic:

```text
keep HybridSynthesisPromptPolicy.GATE_8_4_V1 as the default
```

The experiment policy is injected explicitly into the existing Bedrock adapter. No provider transport fork or infrastructure change is required.

## Offline engineering controls

Before any real model invocation, CI must prove:

- Gate 8.4 v1 prompt fingerprints remain exactly equal to the preserved real baseline hashes;
- candidate prompt selection is explicit;
- candidate and baseline use identical request/evidence payloads;
- default runtime policy remains Gate 8.4 v1;
- synthetic quality success produces `ACCEPT`;
- the original semantic-noise behavior produces `REJECT`;
- an SDK retry produces `REJECT` even if quality targets pass;
- the Gate 8.5 CLI imports in a fresh interpreter without provider initialization;
- the existing complete hybrid test slice remains green under Ruff, strict Pyright, and pytest.

## Real-run rule

No real H8.5-01 Bedrock call is authorized until the draft PR's exact head is green across the repository quality gates.

When authorized, the operator must use the clean SSO credential path established during Gate 8.4. Stale `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_SECURITY_TOKEN`, or `AWS_CREDENTIAL_EXPIRATION` environment variables must not shadow `AWS_PROFILE=opslens-bootstrap`.

Exactly one complete H8.5-01 candidate execution is authorized. Its output must be preserved as immutable evidence before the ACCEPT/REJECT decision is closed.

## Gate status

```text
IN PROGRESS — OFFLINE IMPLEMENTATION / NO GATE 8.5 BEDROCK RUN YET
```

Gate 8.6 and Phase 9 remain blocked until the measured Gate 8.5 decision is recorded.
