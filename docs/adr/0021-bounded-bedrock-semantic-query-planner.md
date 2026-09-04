# ADR 0021 — Bounded Bedrock planner before model invocation

Status: Accepted for Phase 6 Gate 6.3

Date: 2026-09-04

## Context

Gate 6.1 established the typed `SemanticQuery` contract and deterministic SQL
compiler. Gate 6.2 proved bounded read-only execution against the real
`opslens-dev` Athena workgroup.

Phase 6 can now introduce natural-language planning, but the model must not become
an authority for SQL, temporal defaults, numerical bounds, or unsupported query
semantics.

The current supported semantic surface remains deliberately narrow:

```text
metric:       epss_score
dimension:    cve
snapshot:     explicit YYYY-MM-DD only
threshold:    optional inclusive minimum_score in 0.0..1.0
order:        epss_score ASC|DESC
limit:        1..100
```

## Decision

Introduce the Bedrock planner in two steps.

Gate 6.3 freezes and tests the planner contract **offline**:

```text
natural-language question
 -> bounded request
 -> Bedrock Converse request shape
 -> structured-output JSON Schema
 -> deterministic planner-output parser
 -> existing SemanticQuery construction/validation
 -> field-level planner evaluation
```

Gate 6.3 performs no Bedrock inference call and adds no AWS resource or IAM
permission. A real model invocation belongs to the next gate after the contract
and golden evaluation set are stable.

The planner output has exactly two decisions:

```text
semantic_query
  -> complete typed proposal for the existing SemanticQuery surface

unsupported
  -> one allowlisted fail-closed reason
```

Unsupported reasons in v1 are:

```text
missing_explicit_snapshot_date
unsupported_semantics
ambiguous
```

The model never emits SQL.

## Bedrock API choice

Use the Amazon Bedrock **Converse API** through `bedrock-runtime`.

Reasons:

- AWS recommends Converse as the consistent message inference API when supported;
- Converse supports Bedrock structured outputs through `outputConfig.textFormat`;
- token usage and latency are returned in the standard Converse response;
- the future runtime needs only model invocation authority, not agent/tool
  orchestration.

The first request contract uses:

```text
temperature: 0.0
maxTokens:   256
tools:       none
streaming:   none
```

Input questions are bounded to 1,000 characters before any future model call.

## Structured output choice

Use Bedrock native JSON Schema structured output instead of prompt-only JSON.

The schema uses the supported JSON Schema Draft 2020-12 subset:

- basic JSON types;
- enums and const;
- `anyOf`;
- date format;
- `minItems: 1`;
- `additionalProperties: false`.

Bedrock structured output currently does **not** support numerical constraints
such as `minimum` and `maximum`. Therefore the schema cannot be the final authority
for EPSS `0.0..1.0` or query limit `1..100`.

Deterministic application validation remains mandatory after every model response.

## First model candidate

Gate 6.3 freezes the current first smoke-test candidate as:

```text
provider:  Anthropic
model:     Claude Haiku 4.5
model ID:  anthropic.claude-haiku-4-5-20251001-v1:0
Region:    us-east-1
endpoint:  bedrock-runtime
mode:      in-Region
```

Current AWS documentation shows that Claude Haiku 4.5 supports Converse and
structured outputs and is available in-Region in `us-east-1`.

This is a **Gate 6 candidate**, not a permanent vendor/model commitment. Its model
lifecycle and availability must be revalidated immediately before the first real
invocation.

### Alternatives considered

**Amazon Nova 2 Lite**

Attractive for cost-efficient simple automation, but current Bedrock model
documentation does not list structured outputs as supported. It is not selected
for the first strict planner.

**Claude Sonnet 4.6**

Supports structured outputs and has a stronger lifecycle position, but current
`us-east-1` availability requires Geo or Global cross-Region inference. The first
OpsLens planner does not need that broader routing/data-processing boundary.

**Prompt-only JSON with any model**

Rejected for the first implementation because schema-constrained output is
available and directly exercises an AIP-C01-relevant Bedrock production control.

**Strict tool use**

Not selected because the planner needs no tool call. Its only responsibility is
to produce a typed plan.

## Semantic rules

The first planner must fail closed when a question cannot be represented exactly.

Examples:

```text
"at least 0.7" + explicit date     -> supported
"70%" + explicit date              -> normalize to 0.7
"highest"                          -> DESC
"lowest"                           -> ASC

no date                            -> unsupported
today/current/latest              -> unsupported
relative/ambiguous date            -> unsupported
strict "greater than" / "above"    -> unsupported
KEV/remediation/priority questions -> unsupported
limit > 100                        -> unsupported
EPSS outside 0.0..1.0              -> unsupported
```

No planner may silently convert strict `>` semantics into the compiler's supported
`>=` predicate.

## Evaluation

Gate 6.3 introduces a versioned golden JSONL dataset and measures separately:

```text
decision accuracy
metric accuracy
dimensions accuracy
snapshot_date accuracy
minimum_score accuracy
order_by accuracy
order_direction accuracy
limit accuracy
exact SemanticQuery accuracy
unsupported-reason accuracy
```

This prevents one aggregate score from hiding a dangerous date, threshold, or
limit error.

## IAM boundary

Gate 6.3 performs no model invocation and therefore adds no IAM permission.

Before a real Converse call, the validation identity/runtime should receive only
the required `bedrock:InvokeModel` authority for the selected foundation model.
`ConverseStream` is not used, so `bedrock:InvokeModelWithResponseStream` is not
required for this slice.

A final deployed runtime role remains a later Phase 6 exit item.

## Cost and observability

Gate 6.3 incremental AWS cost is `$0` because it is offline.

The next gate must record from real Converse responses:

```text
inputTokens
outputTokens
totalTokens
latencyMs
```

and use the current Bedrock/model pricing at invocation time to calculate observed
planner cost.

## Consequences

Positive:

- model authority is narrower than the deterministic query authority;
- structured output reduces parse/retry failure modes;
- semantic fields are independently measurable;
- unsupported questions are explicit;
- model/IAM/cost exposure is deferred until the contract is testable.

Trade-offs:

- the schema cannot express all business constraints;
- the first semantic surface remains intentionally small;
- structured-output schema compilation can add first-use latency;
- the selected model must be revalidated before real invocation.
