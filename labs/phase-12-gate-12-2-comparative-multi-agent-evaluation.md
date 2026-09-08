# Phase 12 — Gate 12.2: Comparative Multi-Agent Evaluation Contract

_Date: 2026-09-07_

## Status

```text
Phase 11 reference binding:     COMPLETE
comparison contract:            COMPLETE
frozen synthetic fixture:       COMPLETE
offline evaluator:              COMPLETE
offline CLI harness:            COMPLETE
real model calls:               0
capability executions:          0
exact-head CI:                  PENDING
Gate 12.2 completion:           IN PROGRESS
```

Starting checkpoint:

```text
main:   7addd9f6499e9fd9b3ad08cb2ac4a27d6d5cbe0e
issue:  #168
branch: feat/phase12-comparative-evaluation-contract
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

A `6/6` offline conformance result, if observed, proves that the evaluation/admission contract behaves as expected for the fixture. It is not a real multi-agent quality baseline.

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

Aggregate:

```text
total_cases
passed_cases
decision_matches
specialization_matches
admission_matches
target_scope_matches
non_broadening_cases
bounds_compliant_cases
handoff_cases
abstention_cases
source_capability_slots_for_handoffs
specialist_capability_slots
capability_slots_removed
```

The comparison deliberately preserves individual dimensions. A wrong specialization can therefore fail specialization/scope quality while still showing that bounds and non-broadening remained intact.

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

## CI boundary

Multi-Agent CI now includes:

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

A later Gate 12.3 may introduce the first bounded real two-model comparison only after Gate 12.2 merges.

The first experiment should preserve:

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

The two-model topology is rejected if the measured coordination/specialization value does not justify the additional call, latency, token cost, failure surface, or implementation complexity.

## Deferred integration

PR #89 remains deferred cross-project Governed LLM Gateway work and must remain untouched during Gate 12.2.

## Architecture record

```text
docs/adr/0043-freeze-multi-agent-comparison-before-second-model-call.md
```
