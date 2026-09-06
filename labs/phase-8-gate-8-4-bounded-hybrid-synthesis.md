# Phase 8 Gate 8.4 — First Bounded Hybrid Synthesis

_Date: 2026-09-06_

## Objective

Execute the first model-assisted Phase 8 synthesis only after deterministic route and evidence admission, while preserving structured truth, semantic citation provenance, explicit abstention/rejection, and the frozen Gate 8.3 benchmark.

## Starting point

```text
main:   57d052d4bf768c0a1692631ffe1d1e553594fc74
issue:  #114
branch: feat/phase8-bounded-hybrid-synthesis
PR:     #115
```

Frozen input:

```text
dataset_id: hybrid-evaluation-golden:v1
sha256:
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

The fixture is consumed unchanged.

## Authority-preserving execution

```text
EvidenceNeed proposal
 -> deterministic Gate 8.1 routing
 -> deterministic Gate 8.2 ALL_REQUIRED envelope admission
 -> route-aware Gate 8.4 execution
```

Execution policy:

```text
STRUCTURED
 -> deterministic F1/F2/... fact projection
 -> 0 model calls

SEMANTIC
 -> deterministic S1/S2/... semantic citation projection
 -> <= 1 bounded Converse call

HYBRID
 -> deterministic F projections
 + deterministic S projections
 -> <= 1 bounded Converse call

UNSUPPORTED
 -> abstain
 -> 0 model calls

incomplete evidence
 -> reject_before_synthesis
 -> 0 model calls
```

The model never owns the structured values. Its only positive authority is bounded explanatory synthesis over admitted semantic evidence, with optional references to already-admitted structured `F` handles.

## Provider-independent synthesis contract

```text
contract: hybrid-synthesis:v1
```

Hard bounds:

```text
max model calls per eligible case: 1
max explanatory chars:             4000
max claims:                         16
max structured facts:              64
max semantic chunks:               10
max canonical evidence JSON:       24 KiB
```

A model answer is admitted only when it is exact JSON with:

```text
decision: answer | insufficient_evidence
claims[]:
  text
  semantic_citation_ids[]
  structured_fact_ids[]
```

Every answer claim requires at least one allowlisted semantic `S` citation. Unknown `S`/`F` IDs, extra keys, malformed JSON, excessive output, invalid route references, provider failure, or non-`end_turn` stop reason fail closed.

## Prompt injection boundary

Trusted instructions are separated from user question, structured fields, and semantic chunk text. All question/evidence content remains untrusted data. Retrieved instructions cannot change policy, request tools, request SQL, broaden evidence authority, or turn similarity rank into truth.

## Bedrock runtime profile

Gate 8.4 reuses the Phase 7 bounded synthesis transport profile:

```text
region:      us-east-1
model:       us.anthropic.claude-haiku-4-5-20251001-v1:0
Converse:    non-streaming
tools:       none
temperature: 0.0
maxTokens:   2048
```

No AWS infrastructure or IAM change is introduced by this gate.

## Frozen metric semantics

The Gate 8.3 metric dimensions remain independent:

- `route_accuracy`: deterministic Gate 8.3 route metric;
- `structured_fact_correctness`: frozen structured targets must be present unchanged in deterministic `F` projection;
- `semantic_groundedness`: every admitted explanatory claim must cite only fixture-adjudicated supporting chunks;
- `citation_correctness`: exact canonical citation-target set equality;
- `abstention`: exact expected non-answer behavior, preserving `abstain` vs `reject_before_synthesis`;
- `latency`: arithmetic mean of successful model-call client elapsed milliseconds only;
- `cost`: `UNMEASURED` until a deterministic versioned pricing contract exists.

There is no composite score.

## Semantic-noise proof

```text
S1 / rank 1 -> admitted clean-environment neighbor -> NOT support target
S2 / rank 2 -> transitive lockfile review       -> expected support/citation target
```

Admission and retrieval rank do not establish semantic support.

## Offline validation

Fake-client tests cover zero/one-call route behavior, malformed/unknown output, stop-reason/provider failure, metric independence, semantic-noise citation selection, CLI import isolation, and bounded runtime failure evidence.

## Runtime evidence

### Preflight — import defect

Validated head:

```text
efe3bb266baf61687fe51fb7f026e67dbf032535
```

The first local command failed during Python module initialization with a circular import before the runtime client path. It emitted `0` JSON bytes. This is preflight evidence, not a Bedrock baseline. The import boundary was corrected and covered by a fresh-process CLI import regression.

### Attempt A — ambiguous provider-path failure

Validated head:

```text
7b06e559cdfe3c8dbb074609faf5dcfbbf2533cd
```

Observed local result:

```text
exit_code: 1
stderr:    empty
JSON:      2626 bytes
complete:  false
```

The deterministic structured case completed with `F1..F4`. The first semantic case failed with `BedrockHybridSynthesisRuntimeError`; no admitted synthesis execution existed. The old `model_call_count = 0` counted only admitted executions and therefore could not prove whether the provider boundary had been attempted.

This led to a bounded observability correction. Runtime evidence now separates:

```text
synthesis_invocation_attempt_count
admitted_model_execution_count
```

and preserves only bounded failure diagnostics (`failure_category`, bounded diagnostic, optional request ID/stop reason, and invocation-attempt flag). Provider message bodies, prompts, rejected model output, and unrelated metadata are not serialized.

### Attempt B — diagnostic retry after observability correction

Exact validated head:

```text
e2cbaa234edd8f4252f7a7610b1067115edcb55f
```

Python CI #332 / run `34063537197` passed all six repository slices. Hybrid retrieval gates passed `uv lock --check`, Ruff, strict Pyright (`0 errors, 0 warnings`), and `66` tests.

The single justified diagnostic retry used a new output file and did not change the frozen fixture, prompt, model, output contract, retrieval behavior, or authority policy.

Observed local result supplied by the operator:

```text
exit_code:                           1
stderr:                              empty
JSON bytes:                          3079
complete:                            false
planned_case_count:                  6
synthesis_invocation_attempt_count:  1
admitted_model_execution_count:      0
```

Case observations:

```text
hybrid-structured-factual-01
  route: structured
  application_complete: true
  synthesis_invocation_attempted: false
  deterministic F1..F4 projection preserved

hybrid-semantic-remediation-01
  route: semantic
  application_complete: false
  synthesis_invocation_attempted: true
  failure_category: provider_invocation
  failure_diagnostic: Bedrock hybrid Converse synthesis failed provider_type=RuntimeError
  failure_request_id: null
  failure_stop_reason: null
  synthesis: null
```

Interpretation is deliberately narrow: one synthesis invocation path was entered, zero model executions were admitted, and no Bedrock request ID was recovered. `provider_type=RuntimeError` alone is insufficient to identify whether the failure occurred during credential refresh, local SDK request processing, or another pre-response runtime path. No further model invocation is authorized until this pre-response failure is diagnosed without calling the model again.

The frozen dataset identity remained exact:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Synthesis-quality metrics remain unmeasured because the runtime did not complete.

## Next diagnostic step

Use the same locked Python environment and AWS profile to resolve credentials without invoking Bedrock. This is a credential/runtime preflight, not a model-quality retry. If credential resolution succeeds, inspect the SDK request path next; if it reproduces `RuntimeError`, correct the credential/runtime boundary before any additional synthesis attempt.

## AIP-C01 learning points

- model invocation belongs downstream of deterministic authorization and evidence admission;
- structured factual authority can bypass LLM synthesis entirely;
- retrieved context is untrusted data;
- structured output constrains syntax but does not establish truth;
- citation allowlists and canonical provenance are application responsibilities;
- retrieval rank is not groundedness;
- evaluation dimensions should remain independently observable;
- invocation attempts and successfully admitted executions are different observability concepts;
- missing provider request ID is meaningful pre-response evidence but does not by itself identify the failing subsystem;
- token/runtime evidence is not authoritative cost without a pricing contract.

## Gate status

```text
IN PROGRESS
```

PR #115 remains draft. Gate 8.5 optimization is explicitly out of scope until Gate 8.4 produces a complete reviewed baseline.
