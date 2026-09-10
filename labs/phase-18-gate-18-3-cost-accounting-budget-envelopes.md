# Phase 18 — Gate 18.3: Cost Accounting & Budget Envelopes

_Date: 2026-09-10_

## Status

**IMPLEMENTED — pending exact-head CI and protected merge.**

## Source checkpoint

```text
protected main: 3009b9c25ff217e87f087c68d7ba6c7417a919e8
Gate 18.2 PR: #284 / MERGED
Gate 18.3 issue: #285
branch: feat/phase18-gate18-3-cost-accounting
```

Gate 18.3 begins from the protected Gate 18.2 consolidated evaluation view. It does not rerun historical workloads or refresh historical prices. Its purpose is to make already-admitted cost/resource evidence and retained deterministic limits useful without manufacturing production TCO.

## Problem

OpsLens has useful but heterogeneous cost/resource signals:

```text
measured token volume
derived Bedrock inference cost
derived bounded AgentCore experiment cost
explicitly unmeasured complete/monthly cost
not-applicable cloud cost for offline A2A
configured model-output ceilings
Athena bytes-scanned cutoff
Scheduler retry/event-age limits
```

They are not one metric family. Adding or normalizing them would erase component boundaries.

## Gate contract

The canonical artifact is:

```text
labs/evidence/phase-18-gate-18-3-cost-accounting-v1.json
```

Frozen first slice:

```text
entries:                  16
cost observations:         7
resource observations:     2
configured limits:         7
UNMEASURED records:         3
NOT_APPLICABLE records:     1
```

Allowed Gate 18.3 classifications:

```text
OBSERVED
DERIVED
CONFIGURED_LIMIT
UNMEASURED
NOT_APPLICABLE
```

## Cost observations

Gate 18.3 consumes the exact Gate 18.2 values rather than deriving new numbers:

```text
Phase 8 hybrid complete cost             UNMEASURED / null
Phase 11 inference-only cost             DERIVED / USD 0.0041921
Phase 12 inference-only cost             DERIVED / USD 0.0074338
Phase 14 AgentCore experiment total      DERIVED / USD 0.006572445136128483
Phase 14 monthly extrapolation           UNMEASURED / null
Phase 15 A2A AWS runtime cost            NOT_APPLICABLE / null
Phase 16 Inspector complete cost         UNMEASURED / null
```

These values are presentation/accounting inputs only. Gate 18.3 does not reinterpret historical pricing assumptions or claim that a derived estimate is a provider invoice.

## Resource observations

The same-family Phase 11/12 reasoning evidence retains measured token totals:

```text
Phase 11 total tokens: 3395
Phase 12 total tokens: 5982
```

This is useful because the Phase 12 experiment matched Phase 11 quality while consuming more model-token volume. The observation remains workload-scoped rather than becoming a generic cost ratio.

## Configured limits

Seven retained controls are exposed as `CONFIGURED_LIMIT`:

```text
semantic planner output ceiling          256 tokens/response
single-agent output ceiling               96 tokens/response
multi-agent triage output ceiling         64 tokens/response
knowledge synthesis output ceiling      2048 tokens/response
Athena scan cutoff/query             10485760 bytes
Scheduler maximum event age             3600 seconds
Scheduler maximum retry attempts            2
```

The validator requires two independent repository signals for each configured limit:

```text
current source literal
        +
Phase 17 retained control evidence value
        ↓
CONFIGURED_LIMIT admitted
```

A configured limit is not observed utilization and is not a tenant quota.

## Aggregation policy

The first slice freezes:

```text
cross_component_sum                           FORBIDDEN
alternative_workload_sum                      FORBIDDEN
monthly_extrapolation_without_frozen_workload FORBIDDEN
```

This prevents three common portfolio mistakes:

1. double counting inference by summing an inference-only estimate into a managed-runtime experiment total;
2. adding Phase 11 and Phase 12 alternative topologies as though they run together;
3. extrapolating one bounded experiment to monthly production spend without a frozen workload assumption.

## Deterministic verifier

Implementation:

```text
src/opslens/evaluation_readiness/cost_accounting.py
scripts/verify_phase18_cost_accounting.py
```

The verifier checks:

- exact 16-entry first-slice identity;
- exact Gate 18.2 source metric binding;
- exact value/unit preservation;
- `MEASURED -> OBSERVED` and `DERIVED -> DERIVED` mapping;
- null preservation for `UNMEASURED` and `NOT_APPLICABLE`;
- exact configured source path/literal;
- exact Phase 17 control-evidence value path;
- positive configured limits;
- fixed no-aggregation policy;
- summary counts;
- forbidden production/composite cost fields.

Expected success marker:

```text
phase18_cost_accounting=PASS entries=16 cost_observations=7 resource_observations=2 configured_limits=7 unmeasured=3 not_applicable=1
```

## Meaningful failure tests

The unit suite deliberately rejects:

- unknown or switched source metrics;
- `UNMEASURED -> 0` laundering;
- `NOT_APPLICABLE -> 0` laundering;
- `DERIVED -> OBSERVED` relabeling;
- configured-limit literal drift;
- repository/evidence configured-value disagreement;
- zero or negative configured limits;
- configured source-binding drift;
- missing frozen entries;
- cross-component aggregation permission;
- synthetic production TCO fields.

## IAM / AWS / runtime boundary

```text
AWS mutations:          0
IAM changes:            0
runtime changes:        0
model invocations:      0
capability executions:  0
new benchmark runs:     0
pricing refresh:        false
PR #89 touched:         false
```

The Evaluation Readiness CI remains `contents: read` only and has no AWS/OIDC authority.

## Cost

Gate 18.3 itself incurs no AWS/model experiment cost. Repository-local CI validates committed source/evidence.

This is not a claim that the historical platform has zero cost. Complete infrastructure cost remains unmeasured wherever canonical evidence does not establish it.

## Observability

The verifier emits one bounded success/failure summary and no business content. CI preserves the same repository-only evidence path used by Gates 18.1 and 18.2.

## Architecture decision

ADR 0073 records the retained rule:

```text
cost evidence != configured budget envelope
```

and prohibits production TCO until a future gate freezes workload/traffic/storage/pricing assumptions explicitly.

## AIP-C01 learning checkpoint

This gate exercises GenAI cost-engineering judgment rather than simple arithmetic:

- distinguish model utilization from configured output ceilings;
- use token and cost evidence within workload/component boundaries;
- retain denial-of-wallet limits without calling them quotas;
- distinguish inference-only estimates from managed-runtime totals;
- preserve unknown and inapplicable cost dimensions explicitly;
- require workload assumptions before production extrapolation.

## Exit criteria

Gate 18.3 may close when:

```text
Ruff                                      PASS
Pyright strict                            PASS
pytest                                    PASS
phase18_evidence_inventory                PASS
phase18_consolidated_view                 PASS
phase18_cost_accounting                   PASS
Security Hardening CI                     SUCCESS
Dependency Review                         SUCCESS
CodeQL / Python                           SUCCESS
```

No human AWS experiment is required for this gate because no new AWS state or pricing calculation is introduced.

## Next

After protected merge, synchronize the Phase 18 current-state/roadmap checkpoint and proceed to **Gate 18.4 — Portfolio/Demo Evidence Pack & AIP-C01 Synchronization**.

PR #89 remains separate and untouched.
