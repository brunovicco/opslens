# ADR 0028 — Bound Hybrid Synthesis Behind Deterministic Route and Evidence Authority

- Status: Accepted
- Date: 2026-09-06
- Phase: 8 — Hybrid Retrieval
- Gate: 8.4 — First bounded hybrid synthesis

## Context

Gate 8.1 froze deterministic hybrid routing. Gate 8.2 froze a typed evidence envelope with `ALL_REQUIRED` class- and need-level completeness. Gate 8.3 froze `hybrid-evaluation-golden:v1` before any hybrid synthesis was allowed.

The next question is not simply which model to call. The architectural question is which already-authorized routes need a model at all, which values may be model-authored, how semantic citations are bounded, and how model quality is measured without laundering similarity or prose into structured authority.

OpsLens already has a bounded Phase 7 Bedrock Converse synthesis profile. Reusing that transport profile is lower-risk than introducing another model/provider surface, but the Phase 8 authority contract is different because structured and semantic evidence coexist and must remain distinguishable.

## Decision

Adopt provider-independent `hybrid-synthesis:v1` with route-aware execution:

```text
STRUCTURED
 -> deterministic structured fact projection
 -> answer without model synthesis
 -> 0 model calls

SEMANTIC
 -> admitted semantic evidence
 -> bounded citation-aware explanatory synthesis
 -> at most 1 model call

HYBRID
 -> deterministic structured fact projection
 + admitted semantic evidence
 -> bounded explanatory synthesis
 -> at most 1 model call

UNSUPPORTED
 -> explicit abstention
 -> 0 model calls

incomplete evidence
 -> reject before synthesis
 -> 0 model calls
```

A question does not itself authorize model execution. `HybridRouteDecision` plus a complete `HybridEvidenceEnvelope` remain the execution authority.

## Structured facts remain code-owned

Every admitted structured field is projected deterministically as a short handle:

```text
F1, F2, ...
```

The projection preserves:

- structured evidence ID;
- evidence need;
- deterministic authority;
- source artifact identity and SHA-256;
- row key;
- field name;
- exact scalar value.

The model may reference an admitted `F` handle in a hybrid explanatory claim, but it does not author, normalize, score, override, or replace the value. The final system response can therefore combine deterministic structured facts with model-authored explanation without making the model a source of structured truth.

## Semantic citations remain allowlisted

Every admitted semantic chunk is projected deterministically as:

```text
S1, S2, ...
```

The short ID resolves back to immutable chunk/document/source provenance. Model claims must cite at least one admitted `S` ID. Unknown IDs fail closed.

Admission is not support. A chunk may be inside the evidence envelope and still be an incorrect support target for a particular claim. The frozen semantic-noise case deliberately keeps an admitted rank-one neighbor that is not an expected support/citation target.

## Output contract

The model may return only:

```text
answer
insufficient_evidence
```

An `answer` contains bounded explanatory claims. Each claim contains only:

- text;
- admitted semantic citation IDs;
- optional admitted structured fact IDs.

The output parser rejects:

- malformed JSON;
- extra keys;
- unknown `F` or `S` IDs;
- claims without semantic citations;
- structured references on semantic-only routes;
- excessive claims/output length;
- non-canonical answer/abstention shape.

Provider failure, malformed response shape, unsupported stop reason, or failed output admission is not converted into a normal answer.

## Trust boundary

Trusted synthesis instructions are serialized separately from:

- user question;
- structured evidence values;
- semantic evidence text.

All three are untrusted data. Retrieved text cannot request tools, SQL, authority changes, policy changes, or a broader route. Similarity rank/score cannot become factual authority.

## Hard bounds

`hybrid-synthesis:v1` freezes:

```text
max model calls per eligible case: 1
max explanatory output chars:      4000
max claims:                         16
max structured fact projections:   64
max semantic chunks:               10
max canonical evidence JSON:       24 KiB
streaming:                          disabled
tools:                              disabled
temperature:                        0.0
```

## Bedrock profile

Reuse the already-proven Phase 7 Converse profile:

```text
region:    us-east-1
model:     us.anthropic.claude-haiku-4-5-20251001-v1:0
maxTokens: 2048
```

This is a transport/model choice, not a new business authority.

No new AWS resource, IAM role/policy, Knowledge Base, S3 Vectors resource, Athena surface, agent, tool, or `RetrieveAndGenerate` path is authorized by this ADR.

## Gate 8.4 metric semantics

The Gate 8.3 dimensions remain independent. Gate 8.4 computes them deterministically as follows.

### `structured_fact_correctness`

Population: expected-answer cases that freeze structured target facts.

A case passes when every frozen expected scalar fact is present unchanged in the deterministic structured projection. Additional admitted structured fields do not count as an error because they remain code-owned evidence rather than model output.

### `semantic_groundedness`

Population: completed model-required cases.

A case passes only when the model answers and every explanatory claim cites only chunk IDs pre-adjudicated as supporting by the frozen fixture. Model abstention on a fixture case that expects an answer scores false.

This metric is evidence-target groundedness under the frozen fixture. It does not claim universal semantic entailment beyond the adjudicated benchmark.

### `citation_correctness`

Population: completed model-required cases.

A case passes when the union of canonical chunk IDs selected by model citation handles exactly equals the case's frozen expected citation target set.

This remains distinct from groundedness: a supporting chunk set and the exact expected citation target set are related but not interchangeable concepts.

### `abstention`

Population: fixture cases whose expected behavior is not `answer`.

A case passes only when the system produces the exact frozen non-answer behavior (`abstain` or `reject_before_synthesis`). This is a system-level metric, not merely a model refusal rate.

### `latency`

For a complete first runtime baseline, latency is the arithmetic mean of client elapsed milliseconds across successful model-required calls only. Deterministic zero-call routes do not inject artificial zero-latency observations into the model latency metric.

### `cost`

Cost remains `UNMEASURED` until OpsLens freezes a deterministic pricing/version contract. Token usage is retained as runtime evidence, but token counts are not multiplied by an unstated or time-varying price and presented as authoritative cost.

There is no composite hybrid quality score.

## Failure semantics for first baseline

The first real Gate 8.4 run executes the immutable six-case fixture once. Expected deterministic rejection/unsupported outcomes continue through the fixture without provider calls. The runner stops after the first provider/application synthesis failure and preserves partial evidence rather than adaptively retrying cases at the application layer.

SDK transport retries remain bounded metadata and do not change the single application synthesis-attempt contract.

## Consequences

### Positive

- structured truth cannot be overwritten by fluent model output;
- semantic citation authority is explicit and reviewable;
- structured-only questions avoid unnecessary model latency and cost;
- unsupported and incomplete cases fail before model execution;
- the frozen Gate 8.3 benchmark can detect rank/similarity laundering;
- provider metadata remains evidence rather than business authority;
- future optimization can compare dimensions independently.

### Trade-offs

- the final response is assembled from deterministic facts plus explanatory claims rather than one unconstrained model string;
- `S` citation handles currently refer only to semantic chunks, while structured provenance is rendered separately through `F` projections;
- cost is intentionally unavailable until a pricing contract exists;
- fixture-adjudicated groundedness is narrower than open-domain semantic entailment evaluation;
- model invocation is intentionally absent from the structured route even if prose could sound more natural.

## Rejected alternatives

### Send every route to the model

Rejected because a model call is not required to restate deterministic structured truth and would increase cost, latency, and factual-authority ambiguity.

### Let the model author the entire hybrid answer including risk facts

Rejected because risk tier, vulnerability applicability, and other structured values are deterministic authorities.

### Treat every admitted semantic chunk as valid support

Rejected because retrieval/admission and semantic support are separate properties. Gate 8.3 deliberately freezes a counterexample.

### Use a single aggregate hybrid quality score

Rejected because it could hide factual, groundedness, citation, abstention, latency, or cost regressions behind improvements in another dimension.

### Add reranking or another retrieval strategy in Gate 8.4

Rejected because the purpose of this gate is to measure first bounded synthesis over the already-frozen evidence contract. Retrieval optimization belongs to Gate 8.5 only after the baseline is observed.
