# Phase 18 — Gate 18.1: Cross-Phase Evidence Inventory and Comparability Matrix

_Date: 2026-09-10_

## Status

**IMPLEMENTED — exact-head CI required before protected merge.**

## Source checkpoint

```text
source protected main:  2d5e137c0d2e0520806d6b3070e3ef7cb47497c5
Phase 17 closeout PR:    #279
Gate 18.1 issue:         #280
```

Phase 17 is complete. Gate 18.1 begins Phase 18 with evidence consolidation, not a new runtime or benchmark.

## Goal

Freeze a machine-checkable answer to two questions before any portfolio/evaluation view is built:

1. **What kind of evidence is each retained headline value?**
2. **Which values may actually be compared?**

Canonical inventory:

```text
labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json
```

## Classification contract

Every inventory record has exactly one classification:

```text
MEASURED        canonical artifact directly records the observation
DERIVED         value is computed; derivation/provenance is explicit
UNMEASURED      relevant dimension exists, but no complete value exists
NOT_APPLICABLE  metric does not apply to the measured workload
```

The null classifications preserve two permanent boundaries:

```text
unmeasured != zero
not applicable != zero
```

A numeric zero may still be valid `MEASURED` evidence when the canonical artifact directly records zero. Provenance, not numeric magnitude, determines classification.

## Frozen Gate 18.1 scope

The first selective inventory contains:

```text
records:                  27
canonical artifacts:       8
comparability groups:     20
non-comparability pairs:  11
```

Evidence anchors:

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

This is deliberately a headline inventory rather than a dump of every historical numeric field. Inclusion requires sufficiently explicit workload, provenance, unit, and interpretation semantics.

## Retained evidence examples

### Phase 7 and Phase 8 groundedness remain distinct

Phase 7 human-reviewed claim supportedness is derived from 11 supported claims out of 13 reviewed claims:

```text
Phase 7 claim supportedness:  0.8461538461538461  DERIVED
```

Phase 8 directly records its own hybrid evaluation metric:

```text
Phase 8 semantic groundedness: 0.6666666666666666  MEASURED
Phase 8 complete USD cost:     null                UNMEASURED
```

The matrix explicitly refuses to compare the two groundedness-like values numerically because they come from different frozen datasets and metric contracts.

### Same-family reasoning evidence

The frozen six-case reasoning family permits bounded comparison where the source artifacts preserved compatible semantics:

```text
                                Phase 11       Phase 12       Phase 14 AgentCore
passed cases                    6              6              6
total tokens                    3395           5982           not inventoried here
capability executions           0              0              0
derived inference cost (USD)    0.0041921      0.0074338      different cost boundary
```

The direct same-semantics provider-latency comparison retained by Phase 12 is:

```text
Phase 11 provider median:           809.5 ms   MEASURED
Phase 12 provider median by case:  1694.0 ms   DERIVED
```

AgentCore transport timing is intentionally separate:

```text
Phase 14 authenticated transport elapsed sum: 19981 ms  MEASURED
```

Managed runtime transport is not direct Bedrock provider latency.

### Cost boundaries

```text
Phase 11 inference cost:       0.0041921 USD              DERIVED
Phase 12 inference cost:       0.0074338 USD              DERIVED
Phase 14 total experiment:     0.006572445136128483 USD   DERIVED
Phase 14 monthly extrapolation null                        UNMEASURED
Phase 15 A2A cloud-runtime     null                        NOT_APPLICABLE
Phase 16 Inspector total cost  null                        UNMEASURED
```

Inference-only cost is not compared to total hosted-experiment cost. A local/offline protocol has no cloud-runtime cost dimension to measure, while a missing complete Inspector USD value remains unmeasured rather than zero.

### Offline A2A and Inspector timing

```text
Phase 15 A2A client elapsed sum: 0.353039 ms   MEASURED / in-process offline
Phase 16 Inspector client elapsed: 465.877452 ms MEASURED / AWS API discovery
```

The common `milliseconds` unit does not make these measurements comparable.

### Phase 17 security and recovery

Gate 18.1 carries security/operational scope as descriptive evidence rather than inventing a composite score:

```text
adversarial cases:              8       MEASURED
telemetry-hardened handlers:    12      MEASURED
Scheduler retry budget:         2       MEASURED configuration
pause/resume proof:             PASS    MEASURED
```

A security regression case count is not model quality. A configured Scheduler retry budget is not an observed SDK retry count.

## Comparability matrix

Allowed dispositions:

```text
DIRECT_SAME_SEMANTICS
CONDITIONAL_SAME_WORKLOAD_FAMILY
WITHIN_WORKLOAD_ONLY
DESCRIPTIVE_ONLY
```

Gate 18.1 deliberately uses many `DESCRIPTIVE_ONLY` groups. Being useful in a portfolio does not authorize numeric ranking.

The frozen matrix explicitly rejects high-risk look-alikes including:

```text
Phase 7 claim support       vs Phase 8 semantic groundedness
AgentCore transport        vs direct Bedrock provider latency
AgentCore transport        vs offline A2A timing
offline A2A timing         vs Inspector API timing
security case count        vs reasoning passed-case count
telemetry handler count    vs reasoning quality
A2A N/A cloud cost         vs AgentCore total experiment cost
Inspector unmeasured cost  vs AgentCore total experiment cost
Gate 8 unmeasured cost     vs reasoning derived inference cost
Scheduler retry budget     vs reasoning capability executions
inference-only cost        vs total hosted-experiment cost
```

## Deterministic verifier

Implementation:

```text
src/opslens/evaluation_readiness/evidence_inventory.py
scripts/verify_phase18_evidence_inventory.py
tests/unit/evaluation_readiness/test_evidence_inventory.py
```

The verifier fails closed on:

- malformed or unknown classification semantics;
- missing/non-JSON canonical evidence paths;
- `MEASURED` source-value mismatches;
- `DERIVED` values without derivation;
- `UNMEASURED` or `NOT_APPLICABLE` normalized to zero;
- unknown or duplicate comparability membership;
- comparison-enabled groups mixing dimensions or units;
- invalid or duplicate non-comparability assertions.

Nine unit tests cover the valid contract and meaningful failure paths.

Expected canonical verifier marker:

```text
phase18_evidence_inventory=PASS records=27 artifacts=8 groups=20 non_comparable_pairs=11
```

## CI authority

Workflow:

```text
.github/workflows/evaluation-readiness-ci.yml
```

Authority boundary:

```text
GitHub permission:        contents: read
AWS OIDC:                 none
AWS credentials:          none
AWS calls:                0
model invocations:        0
capability executions:    0
runtime mutations:        0
```

The workflow executes lockfile verification, Ruff, strict Pyright, the unit suite, and canonical inventory validation.

## Cost and observability

Gate 18.1 adds no AWS service use. Its operational signal is the bounded verifier marker plus CI status. Historical cost values keep their original evidence classification and component boundary; no fresh price lookup or extrapolation is necessary for this gate.

## Failure modes and non-claims

Gate 18.1 does not prove that every historical number is inventoried, does not create a production latency distribution, does not convert single experiments into SLOs, and does not create a composite readiness/security/quality score.

The inventory is a reviewable evidence contract. It summarizes canonical artifacts but does not become business authority and does not rewrite historical evidence.

## AIP-C01 learning checkpoint

The gate demonstrates a professional-level evaluation discipline: preserve measurement contracts before consolidating results. Groundedness, reasoning quality, latency, retries, cost, security regression, and operational recovery answer different questions. Traceability and comparability must be explicit before a dashboard or portfolio narrative consumes them.

## Exit criteria

Gate 18.1 closes only after:

```text
canonical inventory verifier PASS
Ruff / strict Pyright / pytest PASS
Evaluation Readiness CI PASS
Security Hardening CI PASS
Dependency Review / CodeQL PASS when scheduled
protected squash merge
post-merge state synchronization
```

No AWS experiment is required.

## Next

After protected merge and post-merge synchronization, Gate 18.2 may build a consolidated evaluation/reliability view from the admitted groups while preserving the explicit non-comparability assertions.

PR #89 remains separate and untouched.
