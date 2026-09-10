# Phase 18 — Evaluation, Cost & Portfolio Readiness — Closeout

_Date: 2026-09-10_

## Status

**COMPLETE PENDING THIS CLOSEOUT PR PROTECTED MERGE.**

Phase 18 is closed at the smallest evidence-backed boundary that consolidates evaluation, reliability, cost/resource accounting, portfolio evidence, and AIP-C01 learning coverage without creating a new runtime, benchmark, readiness score, or production claim.

## Source checkpoint

```text
Gate 18.4 PR:                  #288
Gate 18.4 exact head:          c1eef255e6a98fb9a556fea191db8a41d13c2437
Gate 18.4 protected merge:     4a8e5d3d98504451cef26df4e9f274f2f9fd8dd0
Phase 18 closeout issue:       #289
```

Gate 18.4 exact-head validation before merge:

```text
Security Hardening CI    34508507768 / SUCCESS
Dependency Review        34508507778 / SUCCESS
Evaluation Readiness CI  34508507792 / SUCCESS
AgentCore CI             34508507802 / SUCCESS
CodeQL                   34508507840 / SUCCESS
```

## Gate progression

```text
Gate 18.1  cross-phase evidence inventory + comparability
             -> COMPLETE

Gate 18.2  consolidated evaluation & reliability view
             -> COMPLETE

Gate 18.3  cost accounting + configured budget envelopes
             -> COMPLETE

Gate 18.4  evidence-bound portfolio + AIP-C01 mapping
             -> COMPLETE

Gate 18.5  Phase 18 closeout
             -> COMPLETE BY THIS SLICE AFTER PROTECTED MERGE
```

## What Phase 18 established

### 1. Evidence classes are explicit

Phase 18 retains four distinct classifications:

```text
MEASURED
DERIVED
UNMEASURED
NOT_APPLICABLE
```

They are not interchangeable. Missing measurement is not silently converted to zero, and a derived estimate is not promoted to an observed value.

### 2. Comparability is admitted before aggregation

Gate 18.1 inventories 27 metrics from 8 source artifacts, groups comparable measurements deliberately, and preserves 11 explicit non-comparability assertions.

```text
same unit != same measurement semantics
same metric name != comparable workload
one experiment != production distribution
```

### 3. Evaluation dimensions remain independent

Gate 18.2 projects the retained evidence into five independent dimensions rather than collapsing quality, reliability, latency, cost, and security into one readiness score.

Four negative/rejected-default signals remain visible:

```text
phase7-isolation-grounding-failure
phase12-two-model-no-lift
phase14-agentcore-not-default
phase16-zero-records-not-zero-exposure
```

Negative evidence is retained because it constrains architecture decisions.

### 4. Cost accounting is bounded by evidence scope

Gate 18.3 retains 16 entries across observed/derived cost evidence, resource evidence, configured limits, and unmeasured/not-applicable categories.

Configured limits include token ceilings, Athena bytes scanned per query, and Scheduler retry/event-age bounds. They are configuration evidence, not utilization measurements.

```text
configured limit != measured utilization
bounded experiment cost != production TCO
historical experiment cost != recurring monthly run rate
```

Cross-workload cost summation and monthly extrapolation without a frozen workload remain forbidden.

### 5. Portfolio claims are mechanically source-bound

Gate 18.4 exposes 11 selected headline claims and 7 configured-limit claims, but the validator requires them to resolve back to admitted Gate 18.2/18.3 source values with preserved classification, unit, and scope.

The portfolio keeps the four retained negative/rejected-default signals and an explicit `What is not claimed` boundary.

### 6. AIP-C01 learning coverage is evidence-aware

The repository-local AIP-C01 map covers all 20 current task IDs:

```text
EVIDENCED:  14
PARTIAL:     6
STUDY_ONLY:  0 task rows
```

Explicit study-only topics are still listed separately. They do not authorize service adoption or imply implementation.

```text
AIP-C01 topic != product requirement
PARTIAL != EVIDENCED
study topic != implemented capability
exam coverage != certification guarantee
```

## Retained architecture after Phase 18

Phase 18 changes no standing runtime authority. The retained system remains:

```text
source-preserving threat intelligence
 -> deterministic vulnerability applicability and Risk Policy v1
 -> bounded semantic query + deterministic SQL admission
 -> Bedrock Knowledge Base + S3 Vectors retrieval
 -> deterministic hybrid evidence routing/composition
 -> bounded Bedrock reasoning
 -> typed capability authorization/result admission
 -> bounded offline MCP/A2A interoperability
 -> optional historical AgentCore lab evidence
 -> read-only Inspector evidence boundary
 -> content-minimized observability and Phase 17 recovery/security controls
```

Phase 18 adds evidence interpretation and presentation surfaces around that architecture; it does not create new execution authority.

## Explicit non-claims retained

```text
public HTTP production runtime:                  NOT CLAIMED
production SLO from bounded lab measurements:   NOT CLAIMED
production TCO / monthly run rate:               NOT CLAIMED
public MCP/A2A runtime:                          NOT CLAIMED
AgentCore as default runtime:                    NOT RETAINED
zero runtime exposure from zero Inspector rows:  NOT CLAIMED
global platform kill switch:                     NOT CREATED
configured limits as measured utilization:       NOT CLAIMED
certification readiness score/pass probability:  NOT CREATED
```

## Why no Gate 18.6 experiment is justified

The original Phase 18 goal was evaluation, cost, and portfolio readiness. Gates 18.1–18.4 now provide a coherent evidence chain from canonical measurements to safe portfolio and certification-learning projections.

No open inconsistency in that chain requires another technical experiment before closeout. Adding a benchmark merely to produce more numbers would violate the phase's evidence-first principle.

Any future experiment must begin from a new concrete product/evidence gap rather than from a desire to increase portfolio breadth.

## Authority and cost impact of Gate 18.5

```text
AWS mutations:          0
IAM mutations:          0
new AWS services:       0
runtime mutations:      0
model invocations:      0
capability executions:  0
benchmark replays:      0
pricing refresh:        false
production TCO created: false
business authority:     unchanged
PR #89 touched:         false
```

## Canonical Phase 18 records

```text
docs/adr/0071-cross-phase-evidence-classification-and-comparability.md
docs/adr/0072-consolidated-evaluation-and-reliability-view.md
docs/adr/0073-cost-accounting-and-budget-envelopes.md
docs/adr/0074-portfolio-evidence-and-aip-c01-mapping.md
docs/adr/0075-phase18-evaluation-cost-portfolio-closeout.md

docs/portfolio-evidence.md
docs/aip-c01-learning-map.md

labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json
labs/evidence/phase-18-gate-18-2-consolidated-view-v1.json
labs/evidence/phase-18-gate-18-2-decision-signals-v1.json
labs/evidence/phase-18-gate-18-3-cost-accounting-v1.json
labs/evidence/phase-18-gate-18-4-portfolio-evidence-pack-v1.json
labs/evidence/phase-18-gate-18-4-aip-c01-evidence-map-v1.json
labs/evidence/phase-18-closeout-v1.json
```

## Next direction

The next implementation phase is intentionally **not authorized by this closeout**.

Select it from observed product/evidence gaps after Phase 18 is merged. PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred work and must be explicitly re-evaluated against the current retained architecture before any resumption.
