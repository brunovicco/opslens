# ADR 0027 — Frozen Hybrid Evaluation Contract

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 8 — Hybrid Retrieval, Gate 8.3

## Context

Gates 8.1 and 8.2 froze deterministic routing authority and the provider-independent hybrid evidence envelope. Gate 8.4 will be the first point at which a model may receive that envelope.

Evaluation must therefore be frozen **before** hybrid synthesis or tuning exists. Otherwise prompt, retrieval, or answer behavior could be observed first and the benchmark selected afterward, creating an evaluation target that rewards the implementation it was supposed to measure.

The evaluation also has to preserve a permanent distinction:

```text
retrieval/admission success
 != semantic support
 != structured factual correctness
 != citation correctness
```

A single aggregate score would hide failures across those authority boundaries.

## Decision

Gate 8.3 freezes a provider-independent dataset:

```text
hybrid-evaluation-golden:v1
```

Canonical fixture SHA-256:

```text
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

The fixture contains exactly one case for each required v1 scenario:

```text
structured_only_factual
semantic_only_remediation
true_hybrid
unsupported_out_of_authority
partial_structured_evidence
semantic_retrieval_noise
```

Each case freezes:

- question;
- evidence needs;
- expected deterministic route;
- expected envelope outcome;
- expected downstream answer behavior;
- structured evidence rows when applicable;
- semantic evidence chunks when applicable;
- exact structured facts later synthesis must preserve;
- semantic chunks judged relevant to the requested guidance;
- expected citation target chunks.

The fixture is synthetic and hermetic. It exercises OpsLens contracts rather than live provider availability and therefore cannot drift with an AWS service, corpus ingestion, vector score, or external document update.

## Semantic-noise case

One case deliberately contains:

```text
rank 1 -> admitted but non-supporting semantic neighbor
rank 2 -> expected supporting/citation chunk
```

The evidence envelope is expected to be admitted because both chunks satisfy Gate 8.2 structural/provenance requirements. That admission does **not** assert that rank 1 supports the question.

This freezes the distinction:

> **Evidence admission != semantic groundedness.**

The case is intentionally available before Gate 8.4 so future synthesis cannot redefine retrieved relevance as factual or semantic support.

## Partial structured case

The partial structured case requests both:

```text
vulnerability_facts
risk_priority
```

but carries only vulnerability evidence. The deterministic route remains `STRUCTURED`, while envelope assembly must reject the case before synthesis because `ALL_REQUIRED` need-level completeness is not satisfied.

This prevents class presence from hiding missing deterministic authority.

## Unsupported case

The runtime-exposure case remains:

```text
route: UNSUPPORTED
envelope: NOT_APPLICABLE
answer behavior: ABSTAIN
```

No repository-risk evidence is introduced to make runtime exposure appear available.

## Metric contract

Gate 8.3 freezes the following dimensions independently:

| Metric | Earliest legitimate stage | Unit |
|---|---|---|
| `route_accuracy` | Gate 8.3 offline | ratio |
| `structured_fact_correctness` | Gate 8.4 synthesis | ratio |
| `semantic_groundedness` | Gate 8.4 synthesis | ratio |
| `citation_correctness` | Gate 8.4 synthesis | ratio |
| `abstention` | Gate 8.4 synthesis | ratio |
| `latency` | runtime | milliseconds |
| `cost` | runtime | USD |

No composite quality score is defined.

Gate 8.3 measures only what its offline execution can actually observe. `route_accuracy` is a response-quality metric available now. Deterministic envelope outcome agreement is also preserved as a separate `evidence_admission_accuracy` diagnostic.

The synthesis and runtime dimensions remain explicitly:

```text
UNMEASURED
value = null
```

They are not reported as zero, pass, or success.

## Offline evaluator

The Gate 8.3 evaluator executes only:

```text
frozen evidence needs
 -> HybridRoutingRequest
 -> route_evidence_request
 -> HybridRouteDecision
 -> assemble_hybrid_evidence when route is supported
 -> observed route/envelope result
```

No model receives the question or evidence.

This baseline evaluates the deterministic contracts that already exist without pre-implementing Gate 8.4.

## Fixture admission

The loader fails closed on:

- invalid JSON;
- missing or additional schema fields;
- unknown enum values;
- unsupported scalar/provenance values;
- duplicate evidence needs/IDs where forbidden by the underlying contracts;
- inconsistent expected facts or support/citation targets;
- missing required v1 case types;
- duplicated case types or case IDs;
- missing or duplicated metric dimensions;
- metric stage/unit drift;
- any canonical fixture content whose SHA-256 differs from the frozen v1 hash.

A benchmark edit therefore requires an explicit new version/hash rather than silent mutation.

## Alternatives considered

### Freeze the benchmark after first hybrid model run

Rejected. It would allow benchmark selection to follow observed model behavior and weaken the value of the baseline.

### Use only live AWS evidence in the fixture

Rejected for Gate 8.3. Live retrieval/provider behavior would introduce unrelated drift into the contract benchmark and require cost/IAM/runtime dependencies before synthesis has even been authorized.

### Use only happy-path cases

Rejected. Partial structured evidence, unsupported authority, and semantic noise are core failure boundaries, not optional edge cases.

### Collapse metrics into one hybrid-quality score

Rejected. A high route score cannot compensate for fabricated structured facts, unsupported semantic claims, bad citations, or failure to abstain.

### Report unavailable metrics as zero

Rejected. Zero latency/cost or zero factual error would incorrectly imply a measurement occurred. The contract records unmeasured dimensions explicitly.

## AWS, IAM, cost, and observability

Gate 8.3 is offline-only:

```text
AWS resources:     0
IAM changes:       0
Athena calls:      0
Bedrock calls:     0
S3 Vectors calls:  0
model calls:       0
```

The dataset identity, case IDs, expected/observed route, expected/observed envelope outcome, and eventual metric values provide stable evaluation/audit dimensions without inventing provider telemetry.

## AIP-C01 relevance

This gate demonstrates benchmark-first evaluation, separation of retrieval quality from grounded generation, explicit abstention cases, immutable evaluation inputs, and the need to keep quality, latency, and cost measurements distinct. It also reinforces that retrieval scores and admitted context are evidence inputs rather than answer authority.

## Consequences

Positive:

- Gate 8.4 starts against a benchmark that predates its model behavior;
- deterministic routing/admission regressions are measurable offline;
- semantic retrieval noise is represented before synthesis tuning;
- structured facts and semantic/citation targets have independent expected outcomes;
- unmeasured dimensions cannot be mistaken for successful measurements.

Trade-offs:

- the v1 fixture is deliberately small and synthetic;
- Gate 8.3 does not measure model quality, latency, or cost;
- adding or changing benchmark semantics requires explicit versioning rather than editing v1 in place.

## Follow-up

Gate 8.4 may introduce the first bounded hybrid synthesis only after this dataset, loader, evaluator, tests, and CI are merged. Gate 8.4 must populate the frozen synthesis metrics without changing `hybrid-evaluation-golden:v1` to accommodate observed model behavior.
