# Gate 18.2 — Exact-Head Validation Plan

This short-lived gate document records the validation contract before protected merge.

The Gate 18.2 implementation is repository-local and read-only. No AWS, IAM, Terraform, model invocation, capability execution, or benchmark replay is authorized by this validation step.

Exact-head acceptance requires all of the following on the final pull-request head:

```text
Evaluation Readiness CI   SUCCESS
Security Hardening CI     SUCCESS
Dependency Review         SUCCESS
CodeQL / Python           SUCCESS
```

The Evaluation Readiness CI must execute:

```text
Ruff
Pyright strict
unit tests
Gate 18.1 inventory verifier
Gate 18.2 consolidated-view verifier
```

Expected deterministic markers:

```text
phase18_evidence_inventory=PASS records=27 artifacts=8 groups=20 non_comparable_pairs=11
phase18_consolidated_view=PASS sections=5 metrics=27 decision_signals=4 unmeasured=3 not_applicable=1 non_comparable_pairs=11
```

Any mismatch, missing canonical evidence path, decision-signal assertion drift, comparison-semantics drift, forbidden score/ranking field, or unexpected authority change blocks merge.

After protected merge this validation plan is superseded by the Gate 18.2 closeout artifact.
