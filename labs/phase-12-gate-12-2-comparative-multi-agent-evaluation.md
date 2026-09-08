# Phase 12 — Gate 12.2: Comparative Multi-Agent Evaluation Contract

_Date: 2026-09-07_

## Status

```text
Phase 11 reference binding:     COMPLETE
comparison contract:            COMPLETE
frozen synthetic fixture:       COMPLETE
offline evaluator:              COMPLETE
offline CLI harness:            COMPLETE
identity-pinned CI validation:  COMPLETE
real model calls:               0
capability executions:          0
final exact-head CI:            COMPLETE
protected squash merge:         COMPLETE
Gate 12.2 completion:           COMPLETE / MERGED
```

Starting checkpoint:

```text
main:   7addd9f6499e9fd9b3ad08cb2ac4a27d6d5cbe0e
issue:  #168
PR:     #169
branch: feat/phase12-comparative-evaluation-contract
```

Final merged checkpoint:

```text
PR #169 final head:     953467df99ddeaedd6e19471bd2dce6c5bb8de7c
PR merge test commit:   bab183ee1dbcca0eb6a0bb76b5130180f9f2f7c2
Multi-Agent CI:         34174680219 / run #7 / PASS
job:                    101901637997
merge SHA:              865ba70c813711cb88da9ac7308c8966ff983fd0
```

## Objective

Freeze the comparison protocol before OpsLens is allowed to make a second reasoning-model call.

Gate 12.2 asks:

> What must be measured, and how must it be admitted, before a two-model topology can be judged worth keeping?

It does not ask a model to solve that question and does not make a model call.

## Frozen contract

```text
multi-agent-comparison:v1
```

The comparison path is provider-neutral and offline:

```text
frozen fixture
 -> SingleAgentTask
 -> synthetic untrusted MultiAgentHandoffProposal
 -> Gate 12.1 deterministic handoff admission
 -> HANDOFF | ABSTAINED | REJECTED
 -> deterministic decomposed score
 -> content-addressed report
 -> runtime fields remain null
 -> STOP
```

## Synthetic fixture warning

The fixture proposals are deterministic test inputs. They do not come from Bedrock or any other model.

Therefore:

```text
synthetic fixture conformance != multi-agent model quality
```

The observed `6/6` offline conformance result proves that the evaluation/admission contract behaves as expected for the frozen fixture. It is not a real multi-agent quality baseline.

## Exact Phase 11 reference

The comparison dataset and report are hard-bound to:

```text
Phase 11 corpus_sha256:
3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc

Phase 11 report_sha256:
724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Measured Phase 11 reference remains:

```text
quality:                    6/6
bounds compliance:          6/6
SDK retries:                0
capability executions:      0
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
derived six-case cost:      USD 0.0041921
```

Gate 12.2 neither rewrites this evidence nor treats it as a hidden defect requiring multi-agent complexity.

## Frozen comparison fixture

```text
tests/fixtures/multi_agent/golden_multi_agent_comparison_v1.json
```

Cases:

```text
broad-structured-security-query
 -> synthetic HANDOFF / EVIDENCE_ANALYSIS
 -> expected target: public_repository_analysis + structured_security_query
 -> source width 4, target width 2

broad-knowledge-guidance
 -> synthetic HANDOFF / GUIDANCE_SYNTHESIS
 -> expected target: hybrid_security_answer + knowledge_guidance
 -> source width 4, target width 2

broad-hybrid-security-answer
 -> synthetic HANDOFF / GUIDANCE_SYNTHESIS
 -> source width 4, target width 2

broad-public-repository-analysis
 -> synthetic HANDOFF / EVIDENCE_ANALYSIS
 -> source width 4, target width 2

unsupported-arbitrary-execution
 -> synthetic ABSTAIN
 -> no specialist task

allowlist-conflict
 -> synthetic ABSTAIN
 -> no unauthorized specialist task
```

A separate unit case also proves that a synthetic HANDOFF whose specialization has an empty intersection with source authority is scored as deterministic `REJECTED`, rather than creating a specialist task.

## Frozen comparison evidence identities

The exact frozen fixture and deterministic scoring semantics produce:

```text
dataset_sha256:
1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491

dataset_id:
multi-agent-comparison:v1:dataset:1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491

report_sha256:
0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222

report_id:
multi-agent-comparison:v1:report:0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
```

These identities are pinned by tests. Any change to fixture semantics, expected outcomes, scoring dimensions, or the Phase 11 reference binding changes the content-addressed identity and must be reviewed explicitly.

## Decomposed deterministic metrics

Per case:

```text
decision_match
specialization_match
admission_match
target_scope_match
non_broadening
bounds_compliant
passed = conjunction of the six dimensions
```

Frozen synthetic aggregate:

```text
total_cases:                         6
passed_cases:                        6
decision_matches:                    6
specialization_matches:              6
admission_matches:                   6
target_scope_matches:                6
non_broadening_cases:                6
bounds_compliant_cases:              6
handoff_cases:                       4
abstention_cases:                    2
source_capability_slots_for_handoffs: 16
specialist_capability_slots:          8
capability_slots_removed:             8
offline_capability_executions:        0
```

The comparison deliberately preserves individual dimensions. A deliberately wrong synthetic specialization produces `5/6` specialization/scope matches while bounds and non-broadening remain `6/6`, proving those failure dimensions are independently visible.

## Runtime evidence is explicitly absent

Gate 12.2 performs no model call. The report contract requires these fields to remain `null`:

```text
model_invocation_count
input_tokens
output_tokens
total_tokens
provider_latency_ms
client_elapsed_ms
sdk_retries
inference_cost_usd
```

This prevents an unmeasured value from being confused with an observed zero.

The report separately records:

```text
offline_capability_executions = 0
```

because the offline evaluator does not call any capability executor. This is an evaluator-path fact, not a production/runtime statistic.

## Content-addressed evidence

The contract content-addresses:

```text
MultiAgentComparisonCase
MultiAgentComparisonDataset
MultiAgentComparisonCaseScore
MultiAgentComparisonReport
```

Dataset identity includes the ordered case identities and both exact Phase 11 reference digests.

Report identity includes decomposed score identities, aggregate metrics, exact reference digests, and explicit null runtime measurements.

## Offline CLI

```bash
PYTHONPATH=src uv run python scripts/run_multi_agent_comparison_fixture.py
```

The CLI:

- loads the strict frozen JSON fixture;
- performs no network/model call;
- performs no capability execution;
- prints content-addressed dataset/report identities, decomposed metrics, explicit null runtime measurements, and content-minimized case scores;
- exits `0` only when all frozen synthetic cases pass;
- exits `2` on comparison-conformance failure.

## Fail-closed fixture loading

The JSON loader rejects:

```text
unknown or missing fields
unsupported contract versions
unsupported decisions/specializations/capabilities
invalid source tasks
Phase 11 reference drift
proposal/task identity mismatch
invalid expected outcome combinations
```

## Tests

The Gate 12.2 tests cover:

```text
exact Phase 11 reference binding
exact frozen dataset/report identities
six-case fixture conformance
4-to-2 capability-slot narrowing
explicit null runtime metrics
wrong specialization visible by dimension
independent bounds/non-broadening evidence
expected deterministic authorization rejection
reference-drift failure
schema-drift failure
repeatable dataset/report identities
```

## Final exact-head validation

```text
PR #169 head:           953467df99ddeaedd6e19471bd2dce6c5bb8de7c
PR merge test commit:   bab183ee1dbcca0eb6a0bb76b5130180f9f2f7c2
Multi-Agent CI:         34174680219 / run #7 / PASS
job:                    101901637997
offline fixture CLI:    PASS
uv lock --check:        PASS
Ruff:                   PASS
Pyright strict:         0 errors / 0 warnings / 0 informations
pytest:                 18 passed in 0.27s
```

The exact-head run checked out the PR merge test commit against the then-current `main`, executed the frozen fixture before static/type/unit checks, and completed successfully. PR #169 was then squash-merged with the validated exact head as:

```text
865ba70c813711cb88da9ac7308c8966ff983fd0
```

## CI boundary

Multi-Agent CI includes:

```text
tests/fixtures/multi_agent/**
scripts/run_multi_agent_comparison_fixture.py
docs/adr/0043-*.md
```

The workflow executes the offline fixture before Ruff, strict Pyright, and pytest.

## AWS / IAM / runtime boundary

```text
real model calls:               0
real AWS calls:                 0
new AWS resources:              0
new IAM roles/policies:         0
capability executions:          0
AgentCore runtime:              0
MCP:                            0
A2A:                            0
public agent runtime:           0
runtime-exposure authority:     0
Governed LLM Gateway changes:   0
```

No inference cost is claimed for Gate 12.2 because no inference occurs.

## What Gate 12.2 proves

```text
comparison criteria exist before the real experiment
Phase 11 reference provenance is frozen
routing/handoff/scope/bounds metrics are deterministic and decomposed
synthetic handoff proposals can exercise the real deterministic handoff boundary
scope broadening remains independently visible
runtime values cannot be manufactured as zeros
a later two-model topology can be rejected against predeclared metrics
```

## What Gate 12.2 does not prove

```text
triage model quality
specialist model quality
multi-agent quality improvement
real model invocation count
real multi-agent tokens
real multi-agent latency
real multi-agent retries
real multi-agent inference cost
capability execution through a multi-agent flow
production reliability
AgentCore/MCP/A2A behavior
runtime privilege reduction
```

## Next-gate entry rule

Gate 12.3 may introduce the first bounded real two-model comparison because Gate 12.2 is now merged.

The first experiment must preserve:

```text
maximum model invocations per task: 2
adaptive application retries:       0
adaptive fallbacks:                 0
maximum handoffs:                   1
capability executions:              0
triage proposes specialization only
code admits/narrows handoff
specialist proposes capability only
code authorizes capability
STOP before execution
```

Real tokens, latency, retries, and cost must come only from observed provider evidence. Cost must be derived from observed token usage and contemporaneous verified pricing.

The first real observations must be preserved before any tuning. The two-model topology is rejected if measured coordination/specialization value does not justify the additional call, latency, token cost, failure surface, or implementation complexity relative to the frozen Phase 11 reference.

## Deferred integration

PR #89 remains deferred cross-project Governed LLM Gateway work and was not modified by Gate 12.2.

## Architecture record

```text
docs/adr/0043-freeze-multi-agent-comparison-before-second-model-call.md
```
