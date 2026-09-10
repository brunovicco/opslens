# Phase 18 — Gate 18.4: Portfolio Evidence Pack & AIP-C01 Synchronization

_Date: 2026-09-10_

## Status

**IMPLEMENTED — exact-head CI and protected merge required before closeout.**

Starting protected main:

```text
e1ad16d309d1b5412e098e11ef2606dfb1eccd2d
```

Tracking:

```text
issue:  #287
branch: feat/phase18-gate18-4-portfolio-aip-map
```

## Purpose

Project retained evidence into a recruiter/architect-facing portfolio view and synchronize the AIP-C01 learning map without inventing production claims, readiness scores, or certification-driven AWS architecture.

## Evidence chain

```text
Gate 18.1 evidence classification/comparability
  -> Gate 18.2 independent-dimension consolidated view
  -> Gate 18.3 cost/resource accounting and configured limits
  -> Gate 18.4 validated portfolio projection
```

Gate 18.4 adds no new measurement. Eleven headline numeric claims remain bound to Gate 18.2 metrics. Seven configured budget claims remain bound to Gate 18.3 entries. Four negative/rejected-default decision signals remain mandatory.

## AIP-C01 synchronization

The attached official 2026 AIP-C01 exam guide was human-reviewed to freeze five domain titles/weights and twenty task titles. The PDF is not copied into the repository and is not a CI dependency.

Coverage states:

```text
EVIDENCED   substantial repository evidence exercises the core task concerns
PARTIAL     only part of the task is exercised; important subskills remain study-only
STUDY_ONLY  no product-backed implementation evidence is claimed
```

Initial mapping:

```text
AIP tasks:       20
EVIDENCED:       14
PARTIAL:          6
STUDY_ONLY:       0
```

This count is not a readiness percentage. The explicit study-only topic list captures service/examples not justified by current OpsLens requirements.

## Failure modes tested

The validator must fail closed when a portfolio numeric value/classification/unit/scope drifts from Gate 18.2, a configured budget value drifts from Gate 18.3, a known negative decision signal disappears, a `not_claimed` boundary is removed, a synthetic readiness/production-cost field is added, an AIP task/domain/title/weight drifts, evidence is missing, or `STUDY_ONLY` is given implementation evidence.

## IAM, cost, observability, and failure boundary

This gate is repository-local and read-only. It requires no AWS/OIDC authority and incurs no incremental AWS/model cost. Its operational evidence is CI plus deterministic verifier output. A failing verifier blocks the portfolio/AIP projection but does not mutate application/runtime authority.

## Exit criteria

```text
portfolio headline metrics: 11, all source-bound
configured budget claims:    7, all source-bound
decision signals:            4, exact
AIP task IDs:                20/20
synthetic readiness score:   NONE
production TCO/SLO claim:    NONE
AWS/IAM/model/tool mutation: 0
PR #89 touched:              false
```

Gate 18.4 closes only after exact-head CI and protected squash merge.
