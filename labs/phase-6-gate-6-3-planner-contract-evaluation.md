# Phase 6 Gate 6.3 — Bounded planner contract and evaluation foundation

Status: implementation gate; no Bedrock invocation in this gate.

Date: 2026-09-04

## Purpose

Gate 6.1 froze the typed semantic-query and deterministic SQL compiler. Gate 6.2
proved bounded Athena execution. Gate 6.3 introduces the natural-language planner
boundary without yet granting a model any AWS authority.

The architecture for this gate is:

```text
natural-language question
 -> SemanticPlannerRequest
 -> bounded Bedrock Converse request shape
 -> Bedrock structured-output JSON Schema
 -> deterministic planner-output parser
 -> existing SemanticQuery validation
 -> offline field-level evaluation
```

There is deliberately no network call after the request builder.

## Frozen planner surface

Supported semantic query:

```text
decision:         semantic_query
metric:           epss_score
dimensions:       [cve]
snapshot_date:    explicit YYYY-MM-DD
minimum_score:    null or inclusive EPSS threshold
order_by:         epss_score
order_direction:  asc | desc
limit:            1..100
```

Fail-closed planner decision:

```text
decision: unsupported

reason:
  missing_explicit_snapshot_date
  unsupported_semantics
  ambiguous
```

The structured schema contains no SQL field or arbitrary identifier field.

## Input bound

`SemanticPlannerRequest` trims the question and rejects:

- blank questions;
- non-string inputs;
- questions longer than 1,000 characters.

This creates a deterministic pre-model token/cost abuse bound independent of model
behavior.

## Bedrock request contract

The pure request builder currently freezes:

```text
API:          Converse
endpoint:     bedrock-runtime
Region:       us-east-1
model:        anthropic.claude-haiku-4-5-20251001-v1:0
temperature:  0.0
maxTokens:    256
streaming:    no
tools:        none
```

The response format uses `outputConfig.textFormat` with a JSON Schema.

No Bedrock client is constructed and no model call occurs in Gate 6.3.

## Why structured output is not enough

Bedrock validates the response against the supported JSON Schema subset, but
numerical `minimum` / `maximum` constraints are not supported.

Therefore these remain deterministic application responsibilities:

```text
EPSS score must be finite and in 0.0..1.0
limit must be integer in 1..100
snapshot_date must be canonical explicit date
metric/dimension/order enums must be allowlisted
SemanticQuery combination must be supported
```

Every structured model response is parsed back through the existing `SemanticQuery`
constructor before it can reach the SQL compiler.

## Semantic fail-closed examples

```text
"Which CVEs have EPSS at least 0.7 on 2026-09-03?"
  -> semantic_query

"Which CVEs have EPSS at least 70% on 2026-09-03?"
  -> semantic_query / minimum_score 0.7

"Show 10 CVEs with the lowest EPSS on 2026-09-03."
  -> semantic_query / asc / limit 10

"Which CVEs have EPSS at least 0.7?"
  -> unsupported / missing_explicit_snapshot_date

"Which CVEs have EPSS at least 0.7 in the latest snapshot?"
  -> unsupported / missing_explicit_snapshot_date

"Which CVEs have EPSS above 0.7 on 2026-09-03?"
  -> unsupported / unsupported_semantics
     (`above` is strict >; current compiler supports >= only)

"Which vulnerabilities are in CISA KEV on 2026-09-03?"
  -> unsupported / unsupported_semantics
```

## Golden evaluation dataset

Fixture:

`tests/fixtures/semantic_query/planner_eval_v1.jsonl`

Initial corpus:

```text
18 total cases
  8 supported semantic-query cases
 10 fail-closed unsupported cases
```

It covers:

- canonical threshold/date;
- no threshold;
- top-N;
- ascending/descending;
- percentage normalization;
- multiple explicit dates;
- boundary threshold values;
- missing/latest/today dates;
- strict greater-than semantics;
- KEV/remediation/priority questions;
- ambiguous relative time;
- excessive limit;
- invalid EPSS threshold.

## Evaluation metrics

`PlannerEvaluation` reports:

```text
decision_accuracy
metric_accuracy
dimensions_accuracy
snapshot_date_accuracy
minimum_score_accuracy
order_by_accuracy
order_direction_accuracy
limit_accuracy
exact_semantic_query_accuracy
unsupported_reason_accuracy
```

Supported-field metrics use supported expected cases as their denominator.
Unsupported-reason accuracy uses unsupported expected cases.

Tests also mutate one field while leaving the others correct to prove that the
evaluator can localize semantic planner regressions rather than hiding them in a
single aggregate score.

## Failure paths

Unit tests intentionally reject:

- prose/non-JSON planner output;
- missing or extra output fields;
- an injected `sql` field;
- relative/noncanonical/impossible dates;
- boolean or out-of-range EPSS values;
- boolean or out-of-range limits;
- missing prediction IDs in an evaluation run.

These failures occur before the existing compiler/Athena execution path.

## AWS / IAM

Gate 6.3 introduces:

```text
new AWS resources:   0
new IAM permissions: 0
Bedrock calls:       0
Athena calls:        0
```

The first real Converse gate must separately prove the invocation IAM boundary.
Converse requires `bedrock:InvokeModel`; streaming is not selected.

## Cost

Gate 6.3 incremental AWS cost: `$0`.

Real token and latency cost evidence is intentionally deferred until the first
model invocation. The future invocation record must capture:

```text
inputTokens
outputTokens
totalTokens
latencyMs
model ID
Region/inference mode
estimated cost using then-current pricing
```

## AIP-C01 learning

This gate directly practices:

- Bedrock Converse request design;
- structured model output;
- prompt/output governance;
- deterministic post-model validation;
- bounded input/output controls;
- planner golden datasets;
- per-field evaluation instead of opaque pass/fail;
- cost/token instrumentation design before deployment.

## Gate 6.3 closeout

Mark Gate 6.3 complete only when:

1. planner input is bounded;
2. output schema is explicit and contains no SQL authority;
3. deterministic parser reconstructs `SemanticQuery`;
4. invalid values fail closed after model-schema validation;
5. golden dataset exists;
6. per-field evaluator is tested;
7. semantic-query CI is green;
8. no AWS/model authority was introduced.

After closeout, Gate 6.4 may add the first real Bedrock Converse invocation and
record token, latency, model, IAM, failure, and cost evidence.
