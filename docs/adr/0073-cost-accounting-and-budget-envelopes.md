# ADR 0073 — Separate Cost Evidence from Configured Budget Envelopes

- Status: Accepted
- Date: 2026-09-10
- Phase: 18 — Evaluation, Cost & Portfolio Readiness
- Gate: 18.3 — Cost Accounting & Budget Envelopes
- Issue: #285

## Context

Gate 18.1 classified retained cross-phase evidence and froze comparison semantics. Gate 18.2 projected those records into a consolidated evaluation and reliability view without creating new evidence authority.

The retained evidence now contains several values that are useful for cost engineering but have different meanings:

- measured model token volumes;
- derived inference-cost estimates from historical bounded experiments;
- one derived AgentCore experiment total;
- explicitly unmeasured complete or monthly costs;
- a not-applicable cloud-runtime cost for an offline A2A experiment;
- configured model-output, Athena-scan, and Scheduler delivery limits.

Putting all of these values into one cost table without an additional contract would invite false aggregation. A configured `max_tokens` value is not observed token consumption. An Athena bytes-scanned cutoff is not a measured query bill. A single AgentCore experiment total is not a monthly production run rate.

## Decision

Create a versioned repository-local cost-accounting artifact:

```text
labs/evidence/phase-18-gate-18-3-cost-accounting-v1.json
```

The artifact contains exactly three kinds of first-slice entries:

```text
COST_OBSERVATION
RESOURCE_OBSERVATION
CONFIGURED_LIMIT
```

Every entry is classified as exactly one of:

```text
OBSERVED
DERIVED
CONFIGURED_LIMIT
UNMEASURED
NOT_APPLICABLE
```

The first slice contains:

```text
entries:                 16
cost observations:        7
resource observations:    2
configured limits:        7
UNMEASURED:                3
NOT_APPLICABLE:            1
```

Cost/resource observations are bound to already-admitted Gate 18.2 metric IDs. Gate 18.3 does not scrape historical prose or recalculate those values.

Configured limits are admitted only when the validator can prove both:

1. the exact value remains present in the retained repository source; and
2. the same value is preserved in the Phase 17 operational-recovery evidence artifact.

This dual binding prevents portfolio documentation from silently drifting away from the actual deterministic configuration.

## Retained first-slice observations

The cost observations preserve these existing evidence semantics:

```text
Phase 8 complete hybrid cost               UNMEASURED / null
Phase 11 six-case inference cost           DERIVED / USD 0.0041921
Phase 12 six-case inference cost           DERIVED / USD 0.0074338
Phase 14 bounded AgentCore experiment      DERIVED / USD 0.006572445136128483
Phase 14 monthly AgentCore run rate        UNMEASURED / null
Phase 15 A2A AWS runtime cost              NOT_APPLICABLE / null
Phase 16 complete Inspector experiment     UNMEASURED / null
```

The two retained resource observations are measured token volumes:

```text
Phase 11 six-case total tokens             OBSERVED / 3395
Phase 12 six-case total tokens             OBSERVED / 5982
```

Gate 18.3 does not change the historical pricing assumptions used by the Phase 11, Phase 12, or Phase 14 artifacts. No new pricing lookup or refreshed cost calculation is introduced because this gate is classifying and constraining existing evidence rather than producing a new monetary measurement.

## Configured budget envelopes

The first slice binds seven deterministic limits:

```text
semantic planner output ceiling            256 tokens/response
single-agent reasoning output ceiling        96 tokens/response
multi-agent triage output ceiling             64 tokens/response
knowledge synthesis output ceiling          2048 tokens/response
Athena bytes-scanned cutoff/query       10485760 bytes
Scheduler maximum event age                 3600 seconds
Scheduler maximum retry attempts                2
```

These are safety/resource envelopes. They are not utilization measurements, tenant quotas, invoices, or production SLOs.

## Aggregation policy

Gate 18.3 explicitly forbids three forms of aggregation:

```text
cross_component_sum                           FORBIDDEN
alternative_workload_sum                      FORBIDDEN
monthly_extrapolation_without_frozen_workload FORBIDDEN
```

Therefore:

- inference-only costs cannot be silently added to a hosted experiment total whose component boundary may already include inference;
- alternative Phase 11 and Phase 12 reasoning topologies are not summed as if both execute for one request;
- a bounded AgentCore experiment cannot be extrapolated into a monthly production estimate without a separately frozen workload assumption.

## No production TCO

Gate 18.3 deliberately does not create production TCO, monthly run-rate, or portfolio-total fields.

The validator recursively rejects fields named:

```text
production_tco_usd
monthly_run_rate_usd
projected_monthly_cost_usd
portfolio_total_usd
composite_cost_score
readiness_score
```

A future production-cost model would require an explicit workload model, traffic assumptions, retention/storage assumptions, service pricing date/Region, and uncertainty treatment. None of those may be inferred from this bounded evidence pack.

## Validation boundary

The deterministic validator fails closed when:

- the Gate 18.2 source metric ID changes;
- an observed/derived/null value drifts from Gate 18.2;
- `UNMEASURED` or `NOT_APPLICABLE` is converted into zero;
- a derived cost is relabeled as observed spend;
- a configured limit is zero/negative;
- a configured limit source path or literal no longer exists;
- repository configuration and retained control evidence disagree;
- a configured limit masquerades as an observed metric;
- one of the frozen 16 first-slice entries is added, removed, or renamed;
- cross-component aggregation is enabled;
- a forbidden production/composite cost field appears;
- summary counts differ from validated content.

## Alternatives considered

### Sum every USD value into one total

Rejected. The values have incompatible component and workload boundaries. Inference-only estimates, hosted-experiment totals, unmeasured fields, and not-applicable fields cannot be safely aggregated.

### Refresh all AWS prices during this gate

Rejected. Gate 18.3 introduces no new monetary derivation. Refreshing prices would change historical evidence rather than classify it. A future new estimate must verify current official AWS pricing under its own dated evidence contract.

### Treat configured limits as measured savings

Rejected. A ceiling proves a deterministic upper bound on one resource dimension, not utilization or avoided spend.

### Convert missing costs to zero for presentation

Rejected. `UNMEASURED` means evidence is absent; `NOT_APPLICABLE` means the measurement does not belong to that workload. Neither is zero spend.

### Build monthly cost scenarios immediately

Rejected. No traffic/load/retention workload model is frozen in the current scope, so monthly projections would create false precision.

## IAM and security

Gate 18.3 requires no AWS authentication, OIDC token, IAM change, model invocation, or capability execution.

The Evaluation Readiness workflow remains repository-local with:

```yaml
permissions:
  contents: read
```

Configured-limit source validation reads committed text and canonical evidence only.

## Cost of this gate

The implementation path adds no AWS/model runtime cost. CI executes deterministic repository-local validation only.

This statement describes the incremental execution authority of Gate 18.3; it does not reinterpret historical cloud costs as zero.

## Observability

Successful validation emits one bounded summary line:

```text
phase18_cost_accounting=PASS entries=<n> cost_observations=<n> resource_observations=<n> configured_limits=<n> unmeasured=<n> not_applicable=<n>
```

Failure emits a bounded validation reason and exits non-zero. No historical prompt, retrieved evidence body, or business payload is logged.

## Failure modes

The dominant failure mode is cost semantic laundering: presenting unlike values as one spend number. Other risks are stale configured limits, accidental zero normalization, hidden monthly extrapolation, and confusing a configured guardrail with measured utilization.

The first-slice validator addresses these failures with exact source bindings, strict classifications, fixed entry identity, explicit component boundaries, and forbidden aggregation policies.

## AIP-C01 relevance

This gate reinforces professional GenAI cost-optimization and operations reasoning:

- distinguish token utilization from `max_tokens` configuration;
- reason about cost by workload and component boundary;
- retain explicit model-output and retry limits as denial-of-wallet controls without claiming they are tenant quotas;
- distinguish provider inference estimates from managed-runtime experiment totals;
- preserve `UNMEASURED` and `NOT_APPLICABLE` semantics;
- avoid extrapolating a bounded experiment into production TCO without workload evidence;
- use deterministic validation to keep cost evidence traceable.

The certification-relevant lesson is that cost optimization is an architectural measurement discipline, not merely a price multiplication exercise.

## Consequences

### Positive

- existing cost evidence becomes usable without losing provenance;
- configured resource envelopes are visible and machine-checkable;
- hidden zero normalization and accidental double counting fail closed;
- the first slice needs no AWS/model experiment;
- future portfolio material can state what is known, derived, bounded, and still unknown.

### Constraints

- this is not a billing dashboard;
- no production monthly cost is available from this artifact;
- historical derived costs retain their original pricing assumptions;
- storage, logs, data transfer, Knowledge Base ingestion, and other service costs remain outside the first slice unless separately admitted by evidence.

## Permanent boundaries reinforced

```text
budget != observed spend
configured limit != measured utilization
derived inference cost != provider invoice
inference-only cost != hosted-experiment total
single experiment != monthly production estimate
UNMEASURED != zero
NOT_APPLICABLE != zero
token budget != tenant quota
retry budget != guaranteed delivery
Athena scan cap != query cost measurement
portfolio cost summary != billing authority
```

## Next

After exact-head CI and protected merge, Gate 18.3 can close without an AWS experiment if the 16-entry artifact validates against Gate 18.2 and retained repository configuration.

Gate 18.4 may then build the recruiter/architect-facing portfolio evidence pack and synchronize AIP-C01 learning references while consuming, rather than weakening, Gates 18.1–18.3.

PR #89 remains separate and untouched.
