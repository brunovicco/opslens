# Phase 8 — Gate 8.6: Hybrid Retrieval Architecture Closeout

_Date: 2026-09-06_

## Status

**COMPLETE — documentation/architecture closeout pending final PR merge.**

Gate 8.6 starts from exact main:

```text
1566f4fa0c6f5ad6504e291bf953d88411029532
```

Tracking issue:

```text
#120 — Phase 8 Gate 8.6 — close out Hybrid Retrieval architecture
```

Working branch:

```text
docs/phase8-closeout
```

## Goal

Close Phase 8 without reopening the rejected H8.5-01 prompt experiment.

Gate 8.6 consolidates what the completed hybrid-routing, evidence, synthesis, evaluation, and optimization work proved about authority, failures, IAM, cost, observability, documentation, and the entry boundary for Phase 9.

No provider/model replay, prompt tuning, retrieval change, IAM change, or AWS resource change is part of this gate.

## Documentation review

The closeout explicitly reviewed current top-level documentation after Gate 8.5.

Findings before correction:

```text
README.md
 -> Phase 8 still marked NEXT
 -> implemented system stopped at Phase 7 knowledge retrieval
 -> repository structure omitted hybrid_retrieval
 -> CI inventory omitted Hybrid Retrieval

README.pt-br.md
 -> same Phase 8 / hybrid architecture staleness

docs/README.md
 -> architecture baseline still described only through Phase 7
 -> Phase 8 still NEXT
 -> Phase 8 ADRs/labs/evidence not indexed

docs/architecture.md / architecture.pt-br.md
 -> accumulated architecture stopped at Phase 7
 -> Phase 8 still described as the next boundary

docs/roadmap.md
 -> Phase 8 still marked NEXT
 -> Gates 8.1–8.5 not recorded as complete

docs/current-state.md
 -> already synchronized through merged Gate 8.5
 -> correctly identifies Gate 8.6 as NEXT
```

Gate 8.6 synchronizes these current-view documents while leaving historical gate files untouched.

## Preserved Phase 8 contracts

### Gate 8.1 — deterministic route authority

Contract:

```text
hybrid-routing:v1
```

Evidence needs:

```text
vulnerability_facts
risk_priority
remediation_guidance
runtime_exposure
```

Deterministic route policy:

```text
vulnerability_facts and/or risk_priority -> STRUCTURED
remediation_guidance                      -> SEMANTIC
structured + remediation                 -> HYBRID
runtime_exposure, alone or mixed         -> UNSUPPORTED
```

Supported routes require `ALL_REQUIRED` evidence. Runtime exposure remains valid-but-unavailable and is never inferred from repository risk.

### Gate 8.2 — deterministic hybrid evidence

Contract:

```text
hybrid-evidence:v1
```

Structured and semantic evidence remain separate typed collections. Successful envelopes require exact need-level completeness. Extra/unrequested evidence, duplicate identities, malformed ranks, or class drift fail closed.

Similarity score and retrieval rank remain provenance/measurement metadata only.

### Gate 8.3 — frozen evaluation contract

Dataset:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Exactly six case types:

```text
structured_only_factual
semantic_only_remediation
true_hybrid
unsupported_out_of_authority
partial_structured_evidence
semantic_retrieval_noise
```

Independent dimensions:

```text
route_accuracy
structured_fact_correctness
semantic_groundedness
citation_correctness
abstention
latency
cost
```

No composite score exists.

### Gate 8.4 — bounded route-aware synthesis

Contract:

```text
hybrid-synthesis:v1
```

Execution authority:

```text
STRUCTURED
 -> deterministic F1/F2/... facts
 -> 0 model calls

SEMANTIC
 -> admitted S1/S2/... evidence
 -> <=1 bounded Bedrock Converse call

HYBRID
 -> deterministic facts + admitted semantic evidence
 -> <=1 bounded Bedrock Converse call

UNSUPPORTED
 -> explicit abstention
 -> 0 model calls

incomplete evidence
 -> reject_before_synthesis
 -> 0 model calls
```

The model never authors canonical structured facts or source identity. Every explanatory claim requires an admitted semantic citation ID. Unknown IDs, malformed output, response-contract drift, non-`end_turn`, provider failures, or output-admission failures fail closed.

## Immutable Gate 8.4 real baseline

Evidence:

```text
labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json
```

Measured execution:

```text
complete:                            true
planned_case_count:                  6
synthesis_invocation_attempt_count:  3
admitted_model_execution_count:      3
route_accuracy:                      1.0
structured_fact_correctness:         1.0
semantic_groundedness:               0.6666666666666666
citation_correctness:                0.6666666666666666
abstention:                          1.0
latency_ms:                          2959.3333333333335
cost:                                UNMEASURED / null
```

Model-call totals:

```text
input tokens:   4150
output tokens:   289
total tokens:   4439
```

The semantic-noise case intentionally preserves the useful failure:

```text
S1 / rank 1 -> admitted clean-environment neighbor, not support target
S2 / rank 2 -> expected transitive-lock-review support target

model output -> correct S2 claim + ancillary S1 claim
```

Therefore:

```text
admission != semantic support
retrieval rank != groundedness
allowlisted citation != correct question-specific citation target
```

## Gate 8.5 — measured optimization decision

H8.5-01 tested exactly one prompt-only candidate:

```text
experiment: hybrid-optimization:h8.5-01-v1
candidate:  hybrid-synthesis-prompt:h8.5-01-v1
```

The candidate required the smallest sufficient answer, direct question relevance for every claim, and omission of ancillary guidance.

The runtime default remained:

```text
HybridSynthesisPromptPolicy.GATE_8_4_V1
hybrid-synthesis-prompt:v1
```

No fixture, support target, route, evidence admission, structured fact, semantic evidence order/score, model, Region, output schema, inference parameter, IAM entitlement, or AWS resource changed.

Single real-run evidence:

```text
labs/evidence/phase-8-gate-8-5-h85-01-first-run-v1.json
```

Result:

```text
complete:                            true
planned_case_count:                  6
synthesis_invocation_attempt_count:  3
admitted_model_execution_count:      3
all stop reasons:                    end_turn
all SDK retry attempts:              0
route_accuracy:                      1.0
structured_fact_correctness:         1.0
semantic_groundedness:               0.6666666666666666
citation_correctness:                0.6666666666666666
abstention:                          1.0
latency_ms:                          2997.0
cost:                                UNMEASURED / null
```

Token deltas against Gate 8.4:

```text
input tokens:   +306
output tokens:   -26
total tokens:   +280
latency_ms:     +37.666666666666515
```

Decision:

```text
H8.5-01 = REJECT
semantic_groundedness_target_not_met
citation_correctness_target_not_met
```

The semantic-noise case still emitted the ancillary S1 claim. The candidate is not promoted and no second H8.5-01 run is authorized.

## Phase 8 failure taxonomy

Phase 8 extends the earlier stage-oriented failure taxonomy rather than collapsing everything into “RAG failed”:

```text
1. routing / authority failure
   wrong evidence class or unsupported need admitted

2. structured evidence failure
   deterministic structured authority unavailable, incomplete, or invalid

3. semantic provider retrieval failure
   Bedrock Retrieve transport/provider error

4. semantic evidence-admission failure
   invalid provenance/hash/location/rank/identity

5. hybrid completeness failure
   required evidence class or evidence need missing

6. structured fact projection failure
   canonical F fact projection is inconsistent or malformed

7. semantic relevance / selection failure
   admitted evidence exists but wrong/ancillary evidence is used for the requested claim

8. synthesis provider invocation failure
   provider transport/credential/throttle/error

9. synthesis response-contract failure
   malformed provider response metadata/content shape

10. synthesis stop-reason failure
    completion is not end_turn

11. synthesis output-admission failure
    JSON/schema/ID/bounds contract violation

12. citation-attribution failure
    valid admitted citation points to the wrong evidence for the requested claim

13. semantic groundedness failure
    cited evidence does not support the emitted claim under the frozen adjudication target

14. optimization-decision failure
    an intervention is promoted without its predeclared quality/guardrail criteria
```

The Gate 8.5 rejection demonstrates why the final category matters: a human-plausible prompt change is not an optimization unless the measured acceptance rule passes.

## IAM posture

No deployed public application compute principal exists at Phase 8 closeout.

Gate 8.6 therefore creates:

```text
new IAM roles:        0
new IAM policies:     0
new IAM permissions:  0
```

The future application-runtime boundary remains the one already documented in ADR 0024 for the semantic path:

```text
bedrock:Retrieve
 -> exact Knowledge Base BTVJ2PBR2A

bedrock:InvokeModel
 -> exact approved inference profile / required foundation-model resources
```

Hybrid routing, deterministic evidence assembly, F/S projection, and metric computation are application logic and do not require broader Bedrock permissions.

The structured path retains its existing bounded read-only Athena/query authority; Gate 8.6 does not invent or widen a role before real Phase 9 compute exists.

Runtime exposure remains unsupported, so no Amazon Inspector/runtime-observation entitlement is introduced here.

## Cost-accounting boundary

Phase 8 keeps cost dimensions separate:

```text
structured query execution / Athena scan cost
semantic query embedding / vector retrieval cost
S3 Vectors request + processed/returned units
model input tokens
model output tokens
```

Gate 8.4 and Gate 8.5 deliberately report:

```text
cost = UNMEASURED / null
```

because their runtime artifacts do not implement a deterministic, versioned end-to-end pricing contract.

Token totals are valid cost-pressure evidence but are not silently converted into a fabricated USD amount.

The rejected H8.5-01 candidate increased total model tokens by 280 despite reducing output tokens by 26, another reason to preserve cost dimensions independently from quality.

## Observability boundary

Hybrid runtime evidence already captures:

```text
case ID and route
expected/observed answer behavior
whether synthesis invocation was attempted
bounded failure category / diagnostic
failure request ID / stop reason when available
provider request IDs
model/profile and Region
input/output/total/cache token counts
Bedrock latency and client elapsed time
SDK retry count
stop reason
request / prompt / envelope / catalog / result hashes
structured F projections
semantic S citation/chunk mappings
independent quality metric values
optimization decision and rejection reasons
```

Phase 8 does **not** claim:

```text
production SLOs
continuous deployed hybrid metrics
public-user distributed trace correlation
production alert thresholds
high-volume percentile distributions
high-volume route/groundedness regression rates
complete per-request AWS bill attribution
```

Those require a deployed Phase 9 runtime and measured workload.

## Quality and regression evidence inventory

Phase 8 now has distinct layers:

```text
unit / contract quality
 -> Ruff
 -> Pyright strict
 -> pytest

routing / evidence quality
 -> deterministic Gate 8.1 / 8.2 contracts

frozen hybrid evaluation
 -> hybrid-evaluation-golden:v1

provider/runtime integration
 -> real bounded Bedrock Converse
 -> provider request IDs / latency / retries / token evidence

semantic/citation quality
 -> frozen support and citation targets
 -> independent groundedness/citation metrics

optimization governance
 -> versioned H8.5-01 hypothesis
 -> immutable before/after evidence
 -> deterministic ACCEPT / REJECT rule
```

No measured weakness is silently rewritten after the fact.

## Phase 9 entry criteria

Phase 9 may expose “Analyze Your Repository” only with these boundaries frozen:

```text
1. public repository acquisition remains bounded GET-only and never executes repository code
2. immutable repository snapshot identity remains mandatory before dependency analysis
3. vulnerability applicability and risk facts remain deterministic structured authority
4. hybrid route eligibility remains deterministic STRUCTURED / SEMANTIC / HYBRID / UNSUPPORTED
5. supported routes require ALL_REQUIRED evidence
6. runtime exposure remains explicit UNSUPPORTED until an independent runtime authority exists
7. model synthesis receives only already-admitted evidence and cannot author canonical provenance or structured truth
8. structured-only, unsupported, and incomplete-evidence cases preserve their zero-model-call behavior
9. runtime default remains hybrid-synthesis-prompt:v1; H8.5-01 remains rejected evidence
10. public API inputs, provider calls, output size, and execution budgets must be bounded before launch
11. fail-closed behavior must be preserved for provider, evidence, output, and citation-contract failures
12. telemetry must avoid automatic prompt/source-content logging and retain metadata/hashes sufficient for diagnosis
13. rate, abuse, cost, timeout, concurrency, and request-size controls must be designed for the public surface
14. production SLOs/alert thresholds may be defined only from measured deployed workload
15. a real application runtime IAM principal is created only when the Phase 9 compute boundary is concrete
16. new prompt/retrieval/reranking/vector experiments require new versioned hypotheses rather than reuse of H8.5-01
```

Phase 9 should expose the already-governed evidence system. It does not require agents, AgentCore, MCP, A2A, or a new vector technology merely to create a public demo.

## Deferred optimization backlog

The following remain possible future hypotheses only when measured evidence justifies them:

```text
larger retrieval candidate budget
metadata-filter changes
reranking
keyword + vector hybrid search
alternative embedding model
alternative vector technology
question-aware deterministic semantic filtering
new synthesis policy/schema version
runtime cache
similarity-score thresholding
```

The H8.5-01 rejection is preserved and must not be converted into permission for open-ended tuning.

## Deferred Governed LLM Gateway integration

PR #89 remains open/draft for the future Phase 14 Case 3 integration.

It is intentionally outside Phase 8. Gate 8.6 does not rebase, merge, mutate, or otherwise broaden that integration. It must be re-evaluated against the architecture current at the later Phase 14 boundary.

## AWS changes in Gate 8.6

```text
real AWS calls:        0
new AWS resources:    0
new IAM roles:        0
new IAM permissions:  0
new model calls:      0
```

This is intentional. Gate 8.6 is architecture/evidence closeout.

## AIP-C01 learning notes

Gate 8.6 reinforces production GenAI architecture distinctions that matter beyond this repository:

```text
routing proposal != execution authority
structured facts != vector-derived evidence
retrieval admission != semantic support
valid citation identity != correct citation attribution
model success != end-to-end quality success
prompt plausibility != measured optimization
negative experiment result can be the correct engineering decision
model tokens != complete AWS request cost
laboratory telemetry != production SLO evidence
least privilege should follow the real runtime boundary, not precede it with speculative permissions
```

## Exit checklist

```text
[x] Gate 8.4 real baseline preserved without silent tuning
[x] Gate 8.5 H8.5-01 rejection preserved
[x] Phase 8 failure taxonomy consolidated
[x] future runtime IAM boundary preserved without speculative permissions
[x] cost-accounting boundary documented
[x] observability boundary documented
[x] Phase 9 entry criteria frozen
[x] no AWS/IAM/model changes introduced
[ ] README EN synchronized
[ ] README PT-BR synchronized
[ ] docs index synchronized
[ ] architecture EN/PT-BR synchronized
[ ] roadmap synchronized
[ ] current-state final closeout synchronized
[ ] final closeout PR/path checks reviewed
[ ] protected squash merge
```

After the final items, Phase 8 is closed and Phase 9 becomes the next authorized product phase.
