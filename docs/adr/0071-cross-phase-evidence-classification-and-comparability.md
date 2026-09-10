# ADR 0071 — Classify Cross-Phase Evidence Before Portfolio Consolidation

- Status: Accepted
- Date: 2026-09-10
- Phase: 18 — Evaluation, Cost & Portfolio Readiness
- Gate: 18.1 — Cross-phase evidence inventory and comparability matrix
- Issue: #280

## Context

OpsLens entered Phase 18 after completing the evidence-first Security Hardening phase. The repository now contains measured and derived evidence from different workloads: knowledge grounding, hybrid synthesis, single-agent reasoning, two-model comparison, AgentCore hosting, offline A2A interoperability, Inspector read-only discovery, and security/recovery controls.

Those artifacts are useful together, but their numbers are not automatically comparable. A `0` may mean an observed zero, a contract that deliberately forbids an operation, or a value that was never measured. A USD value may be derived from token/resource quantities and verified unit rates rather than observed as a provider invoice. A latency value may represent direct Bedrock provider time, client elapsed time, managed runtime transport, an offline in-process adapter, or an AWS API discovery call.

Phase 18 therefore needs a deterministic evidence-classification boundary before it builds any consolidated dashboard, cost summary, recruiter-facing table, or AIP-C01 study pack.

## Decision

Create one versioned cross-phase evidence inventory:

```text
labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json
```

Every inventory record must be classified as exactly one of:

```text
MEASURED
DERIVED
UNMEASURED
NOT_APPLICABLE
```

The inventory also freezes explicit comparability groups. A metric may appear in exactly one group. Groups that permit numeric comparison must preserve one metric dimension and one unit. Descriptive-only groups remain useful for presentation but authorize no numeric comparison.

The inventory is repository evidence, not a new business-authority source. It may summarize canonical artifacts but may not rewrite the semantics of those artifacts.

## Classification semantics

### MEASURED

Use when the canonical evidence artifact directly records the observation. The inventory must point to an exact `source_metric_path`, and the deterministic verifier requires exact value equality.

Examples include measured token counts, provider/client latency fields, SDK retry counts, AgentCore CPU/memory quantities, Inspector record counts, and the measured Gate 17.6 pause/resume disposition.

### DERIVED

Use when the value is computed from measured observations and/or explicitly preserved pricing or review judgments. A non-empty derivation description is mandatory.

Examples include token-price inference cost, AgentCore compute cost derived from measured resource quantities, and Phase 7 groundedness ratios derived from human-reviewed claim/citation pairs.

A derived value may also be preserved as a field in its source artifact; that does not make the underlying quantity a direct measurement.

### UNMEASURED

Use when the relevant dimension exists but the canonical evidence does not establish a complete value. The value must remain `null` and a reason is mandatory.

Examples include the Gate 8 complete USD cost and the Phase 16 complete Inspector experiment cost.

```text
unmeasured != zero
```

### NOT_APPLICABLE

Use when the metric does not apply to the measured workload. The value must remain `null` and a reason is mandatory.

The Phase 15 A2A reference experiment is local/offline and creates no AWS runtime, so a cloud-runtime cost metric is `NOT_APPLICABLE`, not a measured zero-dollar cloud bill.

```text
not applicable != zero
```

## Comparability model

Gate 18.1 recognizes four dispositions:

```text
DIRECT_SAME_SEMANTICS
CONDITIONAL_SAME_WORKLOAD_FAMILY
WITHIN_WORKLOAD_ONLY
DESCRIPTIVE_ONLY
```

`DIRECT_SAME_SEMANTICS` is reserved for fields whose prior evidence explicitly preserved the same comparison semantics. The initial example is the Phase 11 vs Phase 12 provider/client median comparison recorded by the Phase 12 experiment.

`CONDITIONAL_SAME_WORKLOAD_FAMILY` permits comparison only while the frozen workload relationship and topology differences remain visible. The Phase 11 direct, Phase 12 two-model, and Phase 14 AgentCore replay measurements share a bounded six-case reasoning family, but runtime/topology differences must not be hidden.

`WITHIN_WORKLOAD_ONLY` is available when values share a local workload contract but do not justify cross-workload extrapolation.

`DESCRIPTIVE_ONLY` authorizes presentation, not numeric ranking or optimization conclusions.

The artifact also carries explicit non-comparability assertions for high-risk look-alikes such as:

```text
Phase 7 grounding support != Phase 8 hybrid groundedness
hybrid artifact latency != direct provider latency
AgentCore transport latency != direct Bedrock provider latency
offline A2A latency != Inspector AWS API latency
security regression coverage != model quality
configured Scheduler retry budget != observed SDK retry count
unmeasured/N/A cost != derived experiment cost
inference-only cost != total hosted-experiment cost
```

## Deterministic verifier

The retained verifier checks:

```text
artifact version
frozen classification vocabulary
unique metric IDs
non-empty metric scope/workload/unit/dimension
canonical labs/evidence/*.json path existence
JSON parseability
MEASURED source_metric_path existence and exact value equality
DERIVED non-empty derivation
UNMEASURED null + reason
NOT_APPLICABLE null + reason
exactly one comparability-group membership per metric
known comparison rules
same dimension/unit for groups that permit comparison
a minimum of two members for comparable groups
valid unique non-comparability assertions
```

Unknown/malformed evidence fails closed.

## Alternatives considered

### Build a portfolio dashboard immediately

Rejected. Presentation before evidence classification would encourage accidental comparison of unlike workloads and missing values.

### Normalize all missing values to zero

Rejected. It destroys provenance semantics and makes unmeasured or inapplicable dimensions look like observed zero cost/latency/risk.

### Create one composite readiness score

Rejected for Gate 18.1. Quality, groundedness, latency, cost, reliability, security regression, and operational controls are independent dimensions. A composite would require a separately governed hypothesis and weighting rationale.

### Re-run every historical benchmark under one new harness

Rejected for the first slice. Existing immutable evidence is sufficient to build the classification boundary. New experiments belong only to later gates when the inventory exposes a material missing decision variable.

### Let an LLM classify evidence

Rejected as authority. A model may later explain the inventory, but record classification and comparison admission remain deterministic/reviewable data contracts.

## IAM and security

Gate 18.1 requires no AWS credentials, OIDC token, new IAM principal, or cloud mutation.

The CI workflow is deliberately:

```text
permissions:
  contents: read
```

It reads repository artifacts only. It does not invoke Bedrock, Athena, Inspector, AgentCore, MCP/A2A network surfaces, or OpsLens capabilities.

## Cost

Incremental AWS cost for Gate 18.1 is not applicable to the implementation path because verification is repository-local CI with no AWS calls.

This statement is scoped to Gate 18.1 execution. It does not convert historical unmeasured infrastructure dimensions into zero.

## Observability

The verifier emits one bounded machine-readable line on success:

```text
phase18_evidence_inventory=PASS records=<n> artifacts=<n> groups=<n> non_comparable_pairs=<n>
```

Failures emit a bounded reason and exit non-zero. Raw historical model/source content is not copied into the inventory or logs.

## Failure modes

The boundary is designed to reject:

- stale/missing evidence paths;
- typoed classifications or comparison rules;
- a `MEASURED` value that does not equal its canonical source field;
- a `DERIVED` value with no derivation;
- `UNMEASURED` or `NOT_APPLICABLE` values normalized to numeric zero;
- duplicate metric IDs;
- duplicate/unknown comparability-group membership;
- comparable groups that mix dimensions or units;
- invalid non-comparability assertions.

The verifier does not prove that every possible historical metric has been inventoried; Gate 18.1 review determines the headline evidence set. Later additions require a new artifact version or explicitly governed update rather than silent reinterpretation.

## AIP-C01 learning relevance

This gate exercises professional-level GenAI engineering disciplines without another model call:

- separate evaluation dimensions instead of collapsing quality into one score;
- preserve grounding/citation semantics and human-review provenance;
- distinguish model/runtime latency surfaces;
- distinguish measured usage from derived cost;
- avoid extrapolating a lab run into production SLO or monthly cost;
- make operational/security evidence traceable before presenting it as a portfolio claim.

## Consequences

### Positive

- Phase 18 gains a stable evidence vocabulary;
- headline values are traceable to canonical artifacts;
- missing and inapplicable values remain semantically honest;
- valid reasoning-family comparisons are explicit;
- high-risk look-alike comparisons are explicitly blocked;
- later dashboards/portfolio docs can consume a reviewed data contract instead of scraping prose.

### Constraints

- the first inventory is intentionally selective rather than an exhaustive index of every historical field;
- descriptive metrics are not automatically comparable;
- derived costs remain estimates under their preserved price basis;
- single-run and small-N measurements remain lab evidence, not production distributions.

## Permanent boundaries reinforced

```text
measured value != derived estimate
unmeasured != zero
not applicable != zero
one experiment != production distribution
quality metric != security metric
latency metric != cost metric
offline protocol latency != model-provider latency
runtime transport latency != direct provider latency
derived cost != measured provider invoice
zero no-execution observation != capability success rate
portfolio summary != new technical authority
```

## Next

After exact-head CI and protected merge, Gate 18.1 can close with the inventory/comparability contract frozen. Gate 18.2 may then build a consolidated evaluation and reliability view only from comparisons admitted by this contract.

PR #89 remains separate and untouched.
