# ADR 0074 — Evidence-bound portfolio projection and AIP-C01 mapping

**Status:** Accepted

**Date:** 2026-09-10

## Context

Gates 18.1–18.3 established an evidence inventory, explicit comparability semantics, a consolidated evaluation/reliability view, and cost/resource accounting. OpsLens now has enough retained evidence to present the project concisely to architects/recruiters and to use the repository as an AIP-C01 learning map.

A portfolio layer creates a new risk: copying attractive numbers into prose can detach them from their measurement classification and scope. A certification map creates a similar risk: implementing AWS services merely because they appear in an exam guide can distort the product architecture.

## Decision

Create two repository-local projections:

1. an evidence-bound portfolio pack whose headline numeric claims resolve to admitted Gate 18.2/18.3 values; and
2. an AIP-C01 task map that classifies coverage as `EVIDENCED`, `PARTIAL`, or `STUDY_ONLY` and requires repository evidence for the first two states.

The projections are validated deterministically. They do not become new evidence authority, cost authority, production-SLO authority, or certification authority.

## Consequences

Positive consequences:

- recruiter/architect claims remain traceable to immutable project evidence;
- negative and rejected-default decisions remain visible;
- configured resource limits cannot be presented as measured utilization;
- all 20 current AIP-C01 task IDs remain represented without creating a synthetic readiness score;
- exam-service breadth can be studied separately from product architecture.

Trade-offs:

- the portfolio layer is intentionally conservative and may omit interesting values that are not yet admitted by the evidence chain;
- AIP-C01 coverage states require manual engineering judgment at the task level even though their shape and evidence references are validated automatically;
- future exam-guide revisions require an explicit mapping update rather than silent drift.

## Rejected alternatives

**Generate a single portfolio score.** Rejected because unlike dimensions and evidence classes are not safely aggregatable.

**Calculate certification readiness percentage.** Rejected because repository implementation breadth is not an exam pass probability.

**Implement every service named by the exam guide.** Rejected because certification examples do not constitute product requirements.

**Copy lab metrics directly into README without validation.** Rejected because values could drift from their source classification, unit, or scope.

## Authority boundaries

```text
portfolio claim != new evidence authority
AIP-C01 mapping != certification guarantee
EVIDENCED != complete coverage of every task example
PARTIAL != EVIDENCED
STUDY_ONLY != implemented
configured limit != measured utilization
lab metric != production SLO
cost evidence != production TCO
```

This ADR authorizes no AWS/IAM mutation, model invocation, capability execution, benchmark replay, pricing refresh, or PR #89 change.
