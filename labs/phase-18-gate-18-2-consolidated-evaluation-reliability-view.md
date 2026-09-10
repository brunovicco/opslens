# Phase 18 — Gate 18.2: Consolidated Evaluation & Reliability View

_Date: 2026-09-10_

## Status

**IMPLEMENTED — exact-head CI and protected merge required before closeout.**

## Source checkpoint

```text
source protected main:  ddc960f5ce0030b2822533a459d4754c7059187b
Gate 18.1 closeout PR:  #282
Gate 18.2 issue:        #283
```

Gate 18.1 established evidence classification and comparison admission. Gate 18.2 consumes that contract and builds a deterministic presentation projection without reclassifying metrics or creating new comparison authority.

## Goal

Create one repository-local view that is useful for engineering and portfolio review while preserving:

```text
provenance
classification
workload scope
measurement unit
comparison rule
non-comparability assertions
negative/rejected evidence
missing-vs-not-applicable semantics
```

The gate does not introduce a model call, cloud runtime, benchmark replay, synthetic score, or new production claim.

## Architecture

```text
Gate 18.1 canonical evidence inventory
            |
            v
 deterministic inventory validation
            |
            +-----------------------+
            |                       |
            v                       v
  comparability groups      decision-signal manifest
                                    |
                                    v
                         exact source assertions
                                    |
            +-----------------------+
            |
            v
 deterministic consolidated projector/validator
            |
            v
 phase-18-gate-18-2-consolidated-view-v1.json
```

The implementation lives under:

```text
src/opslens/evaluation_readiness/consolidated_view.py
scripts/verify_phase18_consolidated_view.py
tests/unit/evaluation_readiness/test_consolidated_view.py
```

## Consolidated dimensions

All 27 Gate 18.1 records are projected exactly once into five independent sections:

```text
groundedness_and_quality
latency_surfaces
token_and_cost
execution_authority
runtime_security_and_recovery
```

The committed artifact reports:

```text
sections:                  5
metrics:                  27
decision signals:          4
UNMEASURED records:        3
NOT_APPLICABLE records:    1
non-comparability pairs:  11
```

No aggregate readiness score exists.

## Comparison authority

The view inherits the Gate 18.1 rules exactly:

```text
DIRECT_SAME_SEMANTICS
CONDITIONAL_SAME_WORKLOAD_FAMILY
WITHIN_WORKLOAD_ONLY
DESCRIPTIVE_ONLY
```

A metric row carries both its comparison rule and comparison semantics. `DESCRIPTIVE_ONLY` permits presentation but does not permit numeric ranking or optimization conclusions.

The complete Gate 18.1 non-comparability set is copied into the view and checked for exact equality.

Important examples remain explicit:

```text
Phase 7 claim supportedness != Phase 8 hybrid groundedness
AgentCore transport latency != direct Bedrock provider latency
offline A2A elapsed time != Inspector AWS API elapsed time
security-regression case count != model quality
configured Scheduler retry budget != observed execution metric
inference-only cost != total hosted-experiment cost
```

## Negative and rejected evidence

The view is intentionally not success-only. Four decision signals are retained through a separately validated manifest.

### Phase 7 grounding failure

`grounding-isolation-01` emitted two claims whose human-reviewed support judgments were both false. The signal remains a bounded citation-attribution/grounding failure and is not converted into a universal failure rate.

### Phase 12 two-model no-lift decision

The two-model experiment preserved 6/6 quality but increased model calls, tokens, provider latency and derived inference cost. The implementation/evidence remains historical, while the topology is not the retained default.

### Phase 14 AgentCore default-runtime rejection

AgentCore remains a disabled-by-default optional lab target. A successful managed-runtime experiment does not grant default-runtime architecture authority.

### Phase 16 Inspector zero observation

The bounded read returned zero coverage records and zero finding records for the measured account/Region/time. This is not evidence of zero runtime exposure.

Canonical signal manifest:

```text
labs/evidence/phase-18-gate-18-2-decision-signals-v1.json
```

The Inspector signal points to the canonical Phase 16 closeout document:

```text
labs/phase-16-closeout.md
```

## Deterministic validation

The validator fails closed on:

```text
invalid Gate 18.1 inventory
unknown or duplicate metric IDs
missing Gate 18.1 metric projection
metric projection drift
comparison-rule drift
comparison-semantics drift
changed/missing frozen sections
changed/missing non-comparability assertion
invalid decision-signal kind
unsafe/missing repository evidence path
unsafe/missing supporting Markdown path
missing/duplicate source assertion
source assertion mismatch
missing/duplicate projected decision signal
summary-count drift
forbidden score/rank fields
```

A recursive guard rejects presentation keys such as:

```text
score
rank
ranking
readiness_score
overall_score
composite_score
```

## Success tests

The positive suite validates a complete fixture with all five sections, all metric classifications, decision-signal assertions, and inherited non-comparability semantics.

The repository verifier must emit:

```text
phase18_consolidated_view=PASS sections=5 metrics=27 decision_signals=4 unmeasured=3 not_applicable=1 non_comparable_pairs=11
```

The existing Gate 18.1 verifier must continue to emit:

```text
phase18_evidence_inventory=PASS records=27 artifacts=8 groups=20 non_comparable_pairs=11
```

## Meaningful failure tests

The unit suite includes failures for unknown/duplicate/omitted metrics, projection drift, comparison drift, invalid sections, changed non-comparability, malformed decision signals, failed source assertions, missing source/supporting paths, summary drift, and synthetic score/ranking fields.

This is important because Gate 18.2 protects presentation semantics, not only JSON syntax.

## IAM and security

Gate 18.2 adds no cloud authority.

```text
AWS credentials:         none
OIDC id-token:           none
new IAM permissions:     0
new IAM principals:      0
new AWS services:        0
runtime mutations:       0
model invocations:       0
capability executions:   0
PR #89 touched:          false
```

The Evaluation Readiness workflow remains:

```yaml
permissions:
  contents: read
```

## Cost

Incremental AWS/model cost for this gate is `NOT_APPLICABLE` to the implementation path because validation is repository-local CI with no AWS/model execution.

Historical cost semantics remain unchanged:

```text
Gate 8 hybrid complete USD cost        UNMEASURED / null
AgentCore monthly extrapolation        UNMEASURED / null
Inspector complete experiment cost     UNMEASURED / null
A2A AWS runtime cost                    NOT_APPLICABLE / null
```

The view must not normalize any of these to zero.

## Observability

Validation emits bounded machine-readable summaries only. It does not copy raw prompts, retrieved text, model responses, repository source content, or AWS payload bodies into CI logs.

## Failure modes and interpretation limits

The primary failure mode is **semantic laundering**: presenting heterogeneous evidence in one table so that unlike values appear directly comparable.

The retained boundaries are:

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

## AIP-C01 learning relevance

This gate exercises evaluation and operational reasoning expected from a professional GenAI engineer:

- keep quality, groundedness, latency, cost, reliability and security as independent dimensions;
- retain measurement provenance and workload scope;
- distinguish direct model-provider latency from managed-runtime and protocol timings;
- distinguish measured observations from derived cost estimates;
- retain rejected hypotheses and failure evidence;
- use deterministic controls around presentation of GenAI evaluation evidence.

The important lesson is that an evaluation dashboard is not merely visualization. Its schema determines which conclusions appear legitimate, so comparison admission belongs in deterministic engineering controls rather than presentation code or an LLM.

## Evidence

Canonical Gate 18.2 artifacts:

```text
docs/adr/0072-consolidated-evaluation-and-reliability-view.md
labs/phase-18-gate-18-2-consolidated-evaluation-reliability-view.md
labs/evidence/phase-18-gate-18-2-decision-signals-v1.json
labs/evidence/phase-18-gate-18-2-consolidated-view-v1.json
```

Gate 18.1 remains the upstream metric/comparability authority:

```text
docs/adr/0071-cross-phase-evidence-classification-and-comparability.md
labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json
```

## Exit criteria

Gate 18.2 may close only when:

1. every Gate 18.1 metric is projected exactly once;
2. every metric preserves classification, scope, unit and comparison semantics;
3. all 11 non-comparability assertions remain visible and exact;
4. all four negative/rejected decision signals resolve to canonical evidence;
5. `UNMEASURED` and `NOT_APPLICABLE` remain null and distinct;
6. the verifier fails closed on malformed/unauthorized presentation semantics;
7. the Evaluation Readiness CI remains read-only;
8. exact-head CI passes;
9. the PR is protected-mergeable;
10. PR #89 remains untouched.

## Next

After protected merge and closeout, proceed to **Gate 18.3 — Cost Accounting & Budget Envelope**. That gate should consume the admitted token/cost/retry evidence and keep measured, derived and unmeasured cost boundaries separate.
