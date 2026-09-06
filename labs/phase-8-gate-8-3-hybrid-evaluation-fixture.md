# Phase 8 Gate 8.3 — Frozen Hybrid Evaluation Fixture

_Date: 2026-09-06_

## Objective

Freeze hybrid-routing, evidence-admission, and future synthesis evaluation expectations before Gate 8.4 allows any model to receive a hybrid evidence envelope.

## Starting point

```text
main:   ece255ceb061c21f799fd40e1c3582fd2a08d7b5
issue:  #111
branch: feat/phase8-hybrid-evaluation-fixture
```

Gate 8.1 and Gate 8.2 were already merged. No AWS or model execution was required for this gate.

## Frozen dataset

```text
dataset_id: hybrid-evaluation-golden:v1
canonical sha256:
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Fixture:

```text
tests/fixtures/hybrid_retrieval/golden_hybrid_v1.json
```

The loader hashes canonical parsed JSON rather than file formatting. Equivalent whitespace does not change identity, while a semantic/schema value change does.

## Frozen cases

Exactly six v1 case types are required:

| Case type | Expected route | Envelope | Why it exists |
|---|---|---|---|
| `structured_only_factual` | `STRUCTURED` | admit | verify deterministic factual path |
| `semantic_only_remediation` | `SEMANTIC` | admit | verify bounded guidance evidence path |
| `true_hybrid` | `HYBRID` | admit | require structured + semantic evidence together |
| `unsupported_out_of_authority` | `UNSUPPORTED` | not applicable | preserve runtime-exposure boundary |
| `partial_structured_evidence` | `STRUCTURED` | reject | prove class presence is not need completeness |
| `semantic_retrieval_noise` | `SEMANTIC` | admit | prove admitted retrieval is not semantic support |

## Structured expected facts

Positive structured/hybrid cases freeze exact scalar facts that future synthesis is expected to preserve. These facts must already exist inside the fixture's Gate 8.2 structured evidence rows; the fixture cannot invent expected structured truth outside admitted evidence.

The partial structured case requests:

```text
vulnerability_facts
risk_priority
```

but carries only vulnerability evidence. The deterministic route is still `STRUCTURED`, while the expected envelope outcome is `REJECT` because `risk_priority` lacks Risk Policy evidence.

## Semantic support targets

Semantic cases distinguish:

```text
admitted semantic chunks
expected supporting chunks
expected citation chunks
```

The semantic-noise case deliberately contains:

```text
rank 1 -> clean-environment neighbor -> admitted, NOT a support target
rank 2 -> transitive lockfile review -> admitted, expected support/citation target
```

Therefore a successful envelope is not a groundedness result.

## Metric contract

Frozen dimensions:

```text
route_accuracy                gate_8_3_offline   ratio
structured_fact_correctness   gate_8_4_synthesis ratio
semantic_groundedness         gate_8_4_synthesis ratio
citation_correctness          gate_8_4_synthesis ratio
abstention                    gate_8_4_synthesis ratio
latency                       runtime             milliseconds
cost                          runtime             usd
```

There is no composite score.

Gate 8.3 legitimately measures only `route_accuracy` from the seven response/runtime metrics. Envelope outcome agreement is retained as a separate deterministic diagnostic named `evidence_admission_accuracy`.

Every other frozen metric is explicitly:

```text
status: UNMEASURED
value: null
```

No missing Bedrock call becomes zero cost. No absent synthesis becomes perfect factual correctness or groundedness.

## Offline evaluator

The evaluation path is:

```text
HybridEvaluationCase
 -> HybridRoutingRequest
 -> route_evidence_request
 -> HybridRouteDecision
 -> assemble_hybrid_evidence when supported
 -> HybridOfflineCaseResult
 -> HybridOfflineBaseline
```

The Gate 8.3 implementation evaluates expected route and expected envelope behavior only. It does not call a model and does not pre-implement Gate 8.4 output scoring.

Frozen offline baseline:

```text
route_accuracy:              1.0
evidence_admission_accuracy: 1.0
```

These results establish deterministic contract behavior only. They are not model-quality, retrieval-quality, latency, cost, factual-correctness, groundedness, citation, or abstention claims.

## Fail-closed fixture admission

The loader rejects:

- invalid JSON;
- extra or missing fields;
- unknown enum values;
- invalid Gate 8.2 evidence/provenance values;
- inconsistent structured expected facts;
- support targets not present in semantic evidence;
- citation targets outside support targets;
- missing/duplicate six-case coverage;
- missing/duplicate seven-metric coverage;
- incorrect metric stage/unit;
- any content edit that does not match the frozen canonical SHA-256.

## Quality gates

The existing CI slice includes both executable and fixture paths:

```text
src/opslens/hybrid_retrieval/**/*.py
tests/unit/hybrid_retrieval/**/*.py
tests/fixtures/hybrid_retrieval/**
```

and executes:

```text
uv lock --check
Ruff
Pyright strict
pytest tests/unit/hybrid_retrieval
```

Exact executable PR head:

```text
356b0ccf4d5205d4abd8dab52179423bb2b139e6
```

Python CI #306 / run `34050330182` completed successfully across all six repository slice jobs. Dedicated hybrid retrieval gate:

```text
uv lock --check     PASS
Ruff                PASS
Pyright strict      PASS — 0 errors, 0 warnings
pytest hybrid slice PASS — 49 passed
```

Correction history remained quality-gate driven:

- the initial PR run exposed Ruff findings for nested conditionals and import ordering;
- a later run exposed one strict Pyright redundant integer `cast`;
- all were corrected directly with no `noqa`, `type: ignore`, lint suppression, or weakened type-checking rule.

The frozen dataset hash and authority semantics were not changed to make CI pass.

## Merge checkpoint

PR #112 was promoted from draft only after CI #306 succeeded on the exact executable head above, then squash-merged with that SHA as the expected head.

```text
PR:           #112
issue:        #111 — CLOSED / COMPLETED
validated:    356b0ccf4d5205d4abd8dab52179423bb2b139e6
merge commit: 5c2e3b1caf4b56657ae0e840a35db46df44feaa5
```

## AWS / IAM / cost

```text
AWS resources created: 0
IAM permissions added: 0
Athena calls:          0
Bedrock calls:         0
S3 Vectors calls:      0
model calls:           0
```

Because no runtime request occurred, latency and cost remain unmeasured rather than being fabricated.

## Architecture record

See:

```text
docs/adr/0027-frozen-hybrid-evaluation-contract.md
```

## Next authorized work

Gate 8.3 is complete and merged. **Gate 8.4 — First bounded hybrid synthesis** is now the next authorized Phase 8 step.

Gate 8.4 must consume `hybrid-evaluation-golden:v1` unchanged as its frozen input. Observed model behavior may populate the synthesis metrics; it must not rewrite the benchmark to improve its own score.

The model may synthesize from an already-admitted typed hybrid envelope, but deterministic code must continue to own structured truth, evidence completeness, canonical provenance, output admission, and evaluation metric computation.