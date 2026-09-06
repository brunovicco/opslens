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
sha256:     68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

The fixture was consumed unchanged.

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

The model never owns canonical structured values. Its positive authority is limited to explanatory synthesis over admitted semantic evidence, with optional references to already-admitted structured `F` handles.

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

A model answer is admitted only when it satisfies the exact structured-output contract. Every answer claim requires at least one allowlisted semantic `S` citation. Unknown `S`/`F` IDs, malformed JSON, extra keys, excessive output, invalid route references, provider failure, or non-`end_turn` stop reason fail closed.

## Prompt-injection boundary

Trusted instructions are serialized separately from the user question and admitted evidence. Question and evidence text remain untrusted data. Retrieved instructions cannot change policy, request tools or SQL, broaden evidence authority, or turn similarity/rank into truth.

## Bedrock runtime profile

```text
region:      us-east-1
model:       us.anthropic.claude-haiku-4-5-20251001-v1:0
Converse:    non-streaming
tools:       none
temperature: 0.0
maxTokens:   2048
```

No AWS infrastructure or IAM resource change was introduced by Gate 8.4.

## Runtime-history evidence

### Preflight — import defect

Head:

```text
efe3bb266baf61687fe51fb7f026e67dbf032535
```

The first command failed during Python module initialization because of an eager package re-export circular import. It emitted zero JSON bytes and did not reach the provider path. A fresh-interpreter CLI import regression was added.

### Attempt A — ambiguous provider-path failure

Head:

```text
7b06e559cdfe3c8dbb074609faf5dcfbbf2533cd
```

Observed:

```text
exit_code: 1
complete:  false
JSON:      2626 bytes
```

The deterministic structured case completed, while the first semantic case failed with `BedrockHybridSynthesisRuntimeError`. The original `model_call_count` counted only successfully admitted executions, so the attempt exposed an observability ambiguity.

### Attempt B — bounded failure-observability retry

Head:

```text
e2cbaa234edd8f4252f7a7610b1067115edcb55f
```

CI #332 / run `34063537197` passed all six repository slices. Hybrid retrieval gates passed lock check, Ruff, strict Pyright, and 66 tests.

Observed:

```text
exit_code:                           1
complete:                            false
synthesis_invocation_attempt_count:  1
admitted_model_execution_count:      0
failure_category:                    provider_invocation
failure_diagnostic:                  provider_type=RuntimeError
provider_request_id:                 null
```

This established that the synthesis invocation path was entered but no model execution was admitted.

## Root-cause diagnostic — AWS credential precedence

A zero-model-call diagnostic reproduced the failure while resolving credentials:

```text
botocore_version=1.43.72
profile=opslens-bootstrap
credential_object=RefreshableCredentials
credential_method=env
credential_resolution=error
exception_type=RuntimeError
exception_marker=credentials_refreshed_still_expired
```

The shell contained expired AWS credential environment variables:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN
AWS_CREDENTIAL_EXPIRATION
```

Those environment credentials had precedence over the requested SSO profile.

A clean subshell removed the stale variables and proved the intended chain without invoking a model:

```text
profile=opslens-bootstrap
credential_object=DeferredRefreshableCredentials
credential_method=sso
credential_resolution=ok
sts_signed_request=ok
local_converse_output_config=supported
diagnostic=PASS
```

No prompt, fixture, model, retrieval logic, authority rule, or synthesis-output rule was changed to obtain the complete baseline.

## First complete real Bedrock baseline

Input branch head:

```text
7d06bdb87830f32bb1fc848c9580f8575e52895c
```

The run was executed in a clean credential subshell with `AWS_PROFILE=opslens-bootstrap` after removing stale environment credentials.

Observed operator result:

```text
exit_code:                           0
stderr:                              empty
JSON bytes:                          12632
complete:                            true
planned_case_count:                  6
synthesis_invocation_attempt_count:  3
admitted_model_execution_count:      3
```

Immutable evidence:

```text
labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json
```

Frozen identity remained exact:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

### Independent metrics

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

No composite score is introduced.

### Runtime observations

Three eligible cases reached Bedrock, all with `retry_attempts = 0` and `stop_reason = end_turn`.

```text
hybrid-semantic-remediation-01
  client_elapsed_ms: 5313
  bedrock_latency_ms: 3915
  tokens: 1157 input / 109 output / 1266 total
  citation target: remediation-lock-review:01
  observed citations: remediation-lock-review:01
  result: grounded/citation-correct

hybrid-true-hybrid-01
  client_elapsed_ms: 1932
  bedrock_latency_ms: 1772
  tokens: 1595 input / 81 output / 1676 total
  deterministic structured facts: priority_score=95, priority_tier=P0, review_required=false
  semantic target: isolated-validation:01
  observed citation: isolated-validation:01
  result: grounded/citation-correct

hybrid-semantic-noise-01
  client_elapsed_ms: 1633
  bedrock_latency_ms: 1426
  tokens: 1398 input / 99 output / 1497 total
  expected support/citation target: S2 / transitive-lock-review:01
  observed claim 1: S2 / transitive-lock-review:01
  observed claim 2: S1 / clean-environment-noise:01
  result: output admitted, but semantic_groundedness=false and citation_correctness=false for this case
```

The noise case is the critical measured result. The model correctly used the rank-two supporting chunk for one claim but also introduced an additional claim grounded in an admitted yet fixture-adjudicated non-target neighbor. This demonstrates the frozen distinction:

```text
admission != semantic support
retrieval rank != groundedness
allowlisted citation != correct citation target
```

The application correctly did not reinterpret the model's extra admitted citation as deterministic truth. Instead, the independent evaluation metrics degraded to `2/3` while routing, structured truth, and abstention remained perfect.

## Gate 8.4 review

Gate 8.4 exit criteria are satisfied:

- provider-independent bounded synthesis contract exists;
- structured routes bypass the LLM;
- unsupported and incomplete evidence fail without model calls;
- semantic and hybrid calls are bounded to one invocation per eligible case;
- canonical structured truth remains deterministic;
- citation IDs are allowlisted and mapped back to canonical evidence;
- first complete Bedrock baseline exists with exact provenance and runtime evidence;
- quality metrics are measured independently;
- cost remains explicitly unmeasured rather than fabricated;
- the semantic-noise case produced a real, observable quality failure without violating the output-admission boundary.

The `2/3` semantic-groundedness and citation-correctness values are not Gate 8.4 implementation failures. They are the measured baseline that Gate 8.5 may use to decide whether an optimization experiment is justified. Gate 8.4 must not tune the prompt or retrieval after observing this baseline.

## AIP-C01 learning points

- AWS credential-provider precedence can override an explicitly named profile;
- authentication success in the CLI does not prove an SDK is using the intended credential source;
- provider invocation belongs downstream of deterministic authorization and evidence admission;
- structured factual authority can bypass LLM synthesis entirely;
- retrieved context is untrusted data;
- structured output constrains syntax but does not establish semantic truth;
- citation allowlisting is output admission, not semantic correctness;
- retrieval rank is not groundedness;
- runtime invocation attempts and admitted model executions are distinct observability concepts;
- evaluation dimensions should remain independent;
- token/runtime evidence is not authoritative cost without a versioned pricing contract.

## Gate status

```text
COMPLETE — pending final exact-head CI and protected squash merge
```

Gate 8.5 optimization remains out of scope until PR #115 is revalidated and merged.
