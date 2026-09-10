# Phase 18 — Gate 18.1: Cross-Phase Evidence Inventory and Comparability Matrix

_Date: 2026-09-10_

## Status

**IMPLEMENTED — pending exact-head CI and protected merge.**

## Source checkpoint

```text
source protected main:  2d5e137c0d2e0520806d6b3070e3ef7cb47497c5
Phase 17 closeout PR:    #279
Gate 18.1 issue:         #280
```

Phase 17 is complete. Gate 18.1 begins Phase 18 with evidence consolidation, not a new runtime or benchmark.

## Goal

Freeze a machine-checkable answer to two questions before any portfolio/evaluation dashboard is built:

1. **What kind of evidence is each headline value?**
2. **Which values may actually be compared?**

The canonical inventory is:

```text
labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json
```

## Classification contract

Every record has exactly one classification:

```text
MEASURED        canonical artifact directly records the observation
DERIVED         value is computed; derivation/provenance is explicit
UNMEASURED      relevant dimension exists, but no complete value exists
NOT_APPLICABLE  metric does not apply to this workload
```

The two null classifications deliberately preserve:

```text
unmeasured != zero
not applicable != zero
```

A zero may still be a valid `MEASURED` value when the source artifact directly records zero, such as zero SDK retries or zero Inspector findings. The distinction is provenance, not numerical magnitude.

## First inventory scope

The first slice contains **64 headline records** sourced from **8 canonical evidence artifacts**:

```text
Phase 7   human-reviewed grounding/citation evidence
Phase 8   hybrid evaluation baseline
Phase 11  direct single-agent reasoning baseline
Phase 12  real two-model comparison
Phase 14  final AgentCore runtime experiment
Phase 15  bounded offline A2A closeout
Phase 16  Inspector read-only closeout
Phase 17  Security Hardening closeout
```

The inventory contains **50 comparability groups** and **14 explicit non-comparability assertions**.

This is intentionally not a dump of every numeric value in `labs/evidence/`. A value is included when it is a retained headline evaluation, latency, cost, retry, execution, security, or operational-readiness observation with sufficiently explicit semantics.

## Important classifications

### Phase 7 grounding

The canonical review artifact stores human support judgments and hashes rather than precomputed aggregate ratios. Gate 18.1 therefore marks aggregate decision/support/citation rates as `DERIVED`, with the derivation stated explicitly.

The retained baseline includes:

```text
decision accuracy:            1.0        DERIVED / 4 of 4 decisions
claim supportedness:          0.8461538  DERIVED / 11 of 13 claims
citation correctness:         0.8461538  DERIVED / 11 of 13 pairs
citation target precision:    0.2857143  DERIVED / 2 of 7 selected targets
citation target recall:       0.5        DERIVED / 2 of 4 expected targets
```

These values are not normalized into Phase 8 metrics because the evaluation contracts differ.

### Phase 8 hybrid baseline

The Gate 8.4 artifact directly stores:

```text
route accuracy:               1.0        MEASURED
structured fact correctness:  1.0        MEASURED
semantic groundedness:        0.6666667  MEASURED
citation correctness:         0.6666667  MEASURED
abstention:                   1.0        MEASURED
latency:                      2959.3333 ms MEASURED
cost:                         null       UNMEASURED
```

`cost=null` stays null. It is not rewritten as `$0`.

### Same-family reasoning comparison

Phase 11, Phase 12, and the AgentCore replay preserve a bounded six-case reasoning family. Gate 18.1 therefore permits conditional same-family comparison for compatible dimensions while keeping topology/runtime context visible.

```text
                         Phase 11        Phase 12        Phase 14 AgentCore
passed / total           6 / 6           6 / 6           6 / 6
total tokens             3395            5982            3395
SDK retries              0               0               0
capability executions    0               0               0
derived inference cost   $0.0041921      $0.0074338      $0.0041921
```

Only Phase 11 vs Phase 12 provider/client median latency is admitted as a direct same-semantics comparison because the Phase 12 artifact explicitly froze that comparison:

```text
provider median: 809.5 ms -> 1694.0 ms
client median:   977.5 ms -> 2135.0 ms
```

AgentCore `transport_elapsed_ms_sum=19981` is intentionally excluded from that latency group because it measures a different hosting/transport boundary.

### AgentCore cost

The runtime artifact directly measured CPU and memory usage, while USD cost is derived from those quantities and preserved prices:

```text
CPU usage:                 0.005455525277778 vCPUh   MEASURED
memory usage:              0.200219642726704 GBh     MEASURED
AgentCore runtime cost:    $0.002380345136128484     DERIVED
Bedrock inference cost:    $0.0041921                 DERIVED
total experiment cost:     $0.006572445136128483     DERIVED
monthly extrapolation:     null                       UNMEASURED
```

The single lab experiment does not authorize a monthly-production extrapolation.

### Offline A2A

A2A timing and request/retry counts are measured local protocol observations. The inventory normalizes cloud-runtime cost to:

```text
NOT_APPLICABLE / null
```

rather than reusing the closeout artifact's `incremental_aws_cost_usd=0.0` as though a cloud bill had been measured.

### Inspector

The bounded Inspector run directly observed:

```text
client elapsed:      465.877452 ms
coverage records:    0
finding records:     0
SDK retries:         0 / 0
model invocations:   0
capability execs:    0
```

These zeros are `MEASURED` because the artifact actually observed them. A complete experiment USD cost is absent and remains `UNMEASURED / null`.

### Security/recovery evidence

Gate 18.1 carries Phase 17 operational/security scope as descriptive evidence, not as a model-quality score:

```text
adversarial cases:              8
threat classes:                 7
telemetry-hardened handlers:    12
recovery-controlled schedules:  3
Scheduler event-age budget:     3600 s
Scheduler retry budget:         2
pause/resume proof:             PASS
final state:                    ENABLED_AND_TERRAFORM_CONVERGED
```

No composite “security score” is introduced.

## Comparability matrix

The matrix encodes four dispositions:

```text
DIRECT_SAME_SEMANTICS
CONDITIONAL_SAME_WORKLOAD_FAMILY
WITHIN_WORKLOAD_ONLY
DESCRIPTIVE_ONLY
```

The first artifact intentionally uses many single-member `DESCRIPTIVE_ONLY` groups. That is a feature: inclusion in a portfolio inventory does not itself authorize cross-metric comparison.

Examples explicitly rejected by the matrix include:

```text
Phase 7 support rate      vs Phase 8 groundedness
Phase 7 citation support  vs Phase 8 citation correctness
hybrid latency            vs direct provider/client latency
AgentCore transport       vs direct Bedrock provider latency
AgentCore transport       vs local A2A timing
A2A timing                vs Inspector API timing
security case count       vs reasoning passed-case count
telemetry handler count   vs reasoning quality
A2A N/A cloud cost        vs derived AgentCore total cost
Inspector unmeasured cost vs derived AgentCore total cost
Gate 8 unmeasured cost    vs derived reasoning inference cost
Scheduler retry budget    vs observed SDK retry attempts
inference-only cost       vs total hosted-experiment cost
```

## Deterministic verifier

Implementation:

```text
src/opslens/evaluation_readiness/evidence_inventory.py
scripts/verify_phase18_evidence_inventory.py
tests/unit/evaluation_readiness/test_evidence_inventory.py
```

The verifier fails closed on malformed classification semantics, missing canonical evidence, source-value mismatch, invalid comparison rules, duplicate membership, and unlike dimensions/units inside a comparison-enabled group.

Unit tests include meaningful negative cases for:

```text
unknown classification
UNMEASURED normalized to zero
NOT_APPLICABLE normalized to zero
missing canonical artifact
MEASURED source value mismatch
unknown comparability group
duplicate metric membership
cross-semantic comparison-enabled group
```

## CI authority

Workflow:

```text
.github/workflows/evaluation-readiness-ci.yml
```

Authority:

```text
GitHub permission:        contents: read
AWS OIDC:                 none
AWS credentials:          none
model calls:              0
capability executions:    0
runtime mutations:        0
```

The workflow runs lockfile verification, Ruff, strict Pyright, unit tests, and canonical inventory validation.

Expected canonical verifier marker:

```text
phase18_evidence_inventory=PASS records=64 artifacts=8 groups=50 non_comparable_pairs=14
```

## Cost and observability

Gate 18.1 invokes no AWS service, model, or capability. Its operational signal is the bounded verifier output and CI conclusion.

Historical costs remain attached to their original evidence classification. No new pricing lookup or cost extrapolation is needed to prove this gate.

## AIP-C01 learning checkpoint

This gate reinforces a recurring professional-level design principle: **evaluation evidence must preserve its measurement contract**. Groundedness, retrieval, reasoning quality, latency, retries, token usage, and cost answer different questions. Good architecture makes those dimensions traceable and comparable only where the underlying workload semantics justify it.

## Exit criteria

Gate 18.1 can close after:

```text
canonical inventory verifier PASS
Ruff/Pyright/pytest PASS
Evaluation Readiness CI PASS
Repository security invariants PASS
Dependency Review/CodeQL PASS if scheduled
protected squash merge
post-merge issue/evidence synchronization
```

No AWS experiment is required for this gate.

## Next

After Gate 18.1 closeout, Gate 18.2 may produce a consolidated evaluation/reliability view from the admitted comparison groups. It must preserve the non-comparability assertions instead of ranking unlike workloads.

PR #89 remains untouched.
