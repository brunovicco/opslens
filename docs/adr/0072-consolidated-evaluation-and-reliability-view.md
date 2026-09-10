# ADR 0072 — Build a Traceable Consolidated Evaluation View Without Creating New Evidence Authority

- Status: Accepted
- Date: 2026-09-10
- Phase: 18 — Evaluation, Cost & Portfolio Readiness
- Gate: 18.2 — Consolidated Evaluation & Reliability View
- Issue: #283

## Context

Gate 18.1 introduced a machine-checkable inventory for retained headline evidence. Each metric is classified as `MEASURED`, `DERIVED`, `UNMEASURED`, or `NOT_APPLICABLE` and belongs to an explicit comparability group.

That boundary solves evidence admission, but the raw inventory is not yet an engineering or portfolio view. A useful consolidated presentation must group related observations while preserving their original workload, unit, provenance, classification, and comparison rule.

The repository also contains important negative and rejected evidence that cannot be represented as a numeric metric alone. Examples include the Phase 7 isolation grounding failure, the Phase 12 two-model no-lift decision, the decision not to retain AgentCore as the default runtime, and the Phase 16 zero-record Inspector observation.

A success-only dashboard would discard exactly the evidence needed to explain why the retained architecture is simpler than some of the experiments that preceded it.

## Decision

Create a versioned repository-local consolidated view:

```text
labs/evidence/phase-18-gate-18-2-consolidated-view-v1.json
```

The view consumes the Gate 18.1 inventory as its metric authority and groups all 27 admitted headline metrics into five presentation dimensions:

```text
groundedness_and_quality
latency_surfaces
token_and_cost
execution_authority
runtime_security_and_recovery
```

Every projected metric preserves its Gate 18.1 fields and additionally carries the exact comparison rule and semantics from its registered comparability group.

The view does not independently classify metrics, derive new values, normalize units, or infer comparison permission.

## Decision-signal manifest

Retained negative and architecture-disposition evidence is carried through a separate versioned manifest:

```text
labs/evidence/phase-18-gate-18-2-decision-signals-v1.json
```

Each signal has:

```text
signal_id
kind
statement
interpretation
canonical evidence_path
supporting_document
one or more exact source assertions
```

The deterministic validator resolves every assertion against the canonical JSON evidence before admitting the signal into the consolidated view.

Allowed signal kinds are:

```text
FAILURE_SIGNAL
REJECTED_DEFAULT
ZERO_OBSERVATION
LIMITATION
```

The first Gate 18.2 slice preserves four signals:

1. Phase 7 isolation grounding/citation-attribution failure.
2. Phase 12 two-model topology rejected as the default after no measured quality lift and higher resource/latency/cost use.
3. AgentCore retained only as an optional disabled-by-default lab target, not the default runtime.
4. Inspector zero coverage/finding records retained as a bounded zero observation, not proof of zero runtime exposure.

## Comparison authority

Gate 18.2 inherits, rather than redefines, Gate 18.1 comparison dispositions:

```text
DIRECT_SAME_SEMANTICS
CONDITIONAL_SAME_WORKLOAD_FAMILY
WITHIN_WORKLOAD_ONLY
DESCRIPTIVE_ONLY
```

A view row may display `DESCRIPTIVE_ONLY` evidence, but presentation does not grant permission to rank or compare it numerically.

The complete Gate 18.1 non-comparability set is copied into the view and deterministically checked for exact equality. This makes high-risk false equivalences visible to downstream consumers.

## No composite score

Gate 18.2 deliberately introduces no overall readiness, quality, security, reliability, or cost score.

A recursive validation guard rejects presentation fields named:

```text
score
rank
ranking
readiness_score
overall_score
composite_score
```

This is intentionally conservative. A future composite would require a separate hypothesis, weighting rationale, normalization model, and evidence contract.

## Alternatives considered

### Render directly from historical Markdown

Rejected. Prose is useful explanation but is not a stable data contract and could bypass the Gate 18.1 classification/comparability boundary.

### Build a visually polished dashboard first

Rejected for this gate. A UI before projection invariants would move presentation ahead of evidence semantics and encourage accidental comparison of unlike measurements.

### Re-run all workloads under one benchmark harness

Rejected. Gate 18.2 is a consolidation gate. Existing retained evidence is sufficient to construct the first view; new model/cloud runs require a decision-relevant missing variable.

### Normalize all latency and cost fields

Rejected. Direct Bedrock latency, AgentCore transport elapsed time, local A2A timing, Inspector API elapsed time, inference-only cost, hosted-experiment cost, unmeasured cost and not-applicable cost represent different measurement boundaries.

### Hide failed or rejected experiments

Rejected. Negative evidence explains architecture retention decisions and is necessary for an evidence-first portfolio narrative.

## Validation boundary

The Gate 18.2 validator fails closed when:

- the Gate 18.1 inventory itself is invalid;
- a decision signal references a missing/unsafe evidence path;
- a decision signal source assertion does not exactly match canonical evidence;
- a projected metric is unknown, duplicated, omitted, or differs from the inventory;
- comparison rule or comparison semantics drift from Gate 18.1;
- the five frozen presentation sections are changed or left empty;
- a Gate 18.1 non-comparability assertion is added, removed, or rewritten;
- a decision signal is omitted or duplicated;
- summary counts differ from validated content;
- a forbidden score/ranking field appears.

The validator does not claim that the 27-record Gate 18.1 inventory is exhaustive of every historical repository value. It validates the retained first-slice contract.

## IAM and security

Gate 18.2 requires no AWS authentication or cloud authority.

The Evaluation Readiness workflow retains:

```yaml
permissions:
  contents: read
```

It uses no `id-token: write`, AWS credentials, model calls, capability execution, or Terraform mutation.

## Cost

Gate 18.2 creates no AWS/model runtime cost because the implementation and validation path is repository-local CI.

This does not convert historical `UNMEASURED` cost into zero. The view explicitly preserves:

- Gate 8 hybrid cost as `UNMEASURED / null`;
- AgentCore monthly extrapolation as `UNMEASURED / null`;
- Inspector complete experiment cost as `UNMEASURED / null`;
- offline A2A AWS runtime cost as `NOT_APPLICABLE / null`.

## Observability

Successful validation emits one bounded line:

```text
phase18_consolidated_view=PASS sections=<n> metrics=<n> decision_signals=<n> unmeasured=<n> not_applicable=<n> non_comparable_pairs=<n>
```

Failure emits a bounded reason and exits non-zero. Historical model/source bodies are not copied into logs.

## Failure modes

The main failure mode is semantic laundering: making heterogeneous historical evidence look uniform by placing it in one table. Gate 18.2 counters this by keeping classification, workload, unit, comparison disposition, negative signals, and explicit non-comparability attached to the presentation data.

Other bounded failure modes include stale evidence paths, changed canonical values, accidental omission of negative evidence, and presentation code introducing a synthetic score.

## AIP-C01 relevance

This gate reinforces professional-level evaluation and operations skills:

- separate model quality, groundedness, latency, cost, reliability and security dimensions;
- preserve measurement provenance and small-sample limitations;
- distinguish direct model-provider latency from managed-runtime and protocol transport timings;
- distinguish measured observations from derived cost;
- retain failed/rejected experiments as architecture evidence;
- use deterministic validation around presentation of GenAI evaluation results.

These are directly useful when deciding whether a more complex GenAI architecture provides measurable value rather than merely demonstrating additional services.

## Consequences

### Positive

- one stable view can support engineering, portfolio and later demo artifacts;
- every displayed metric remains traceable to Gate 18.1;
- negative/rejected evidence stays visible;
- `UNMEASURED` and `NOT_APPLICABLE` remain distinct;
- comparison semantics cannot be silently widened by presentation code;
- the gate requires no new AWS/model experiment.

### Constraints

- the view is intentionally not a production SLO dashboard;
- it does not normalize or rank unlike workloads;
- it carries only the retained Gate 18.1 first-slice metrics;
- future evidence additions require an explicit inventory/view version update.

## Permanent boundaries reinforced

```text
view != new evidence authority
presentation != comparison admission
same unit != same measurement semantics
missing != zero
UNMEASURED != NOT_APPLICABLE
lab observation != production SLO
failure signal != universal failure rate
zero runtime records != zero runtime exposure
historical experiment != retained default architecture
quality success != cost/latency justification
```

## Next

After exact-head CI and protected merge, Gate 18.2 can close without an AWS experiment if the committed consolidated view and decision-signal manifest validate against the canonical repository evidence.

Gate 18.3 may then focus specifically on **cost accounting and budget envelopes**, using only cost/token/retry boundaries already admitted by Gates 18.1 and 18.2 unless a material cost decision requires new measurement.

PR #89 remains separate and untouched.
