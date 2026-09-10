# OpsLens — Current State

_Last updated: 2026-09-10_

## Authoritative checkpoint

```text
protected main at Gate 18.4 start:
e1ad16d309d1b5412e098e11ef2606dfb1eccd2d

Phase 18 — Evaluation, Cost & Portfolio Readiness
status: IN PROGRESS

Gate 18.1 — Cross-phase Evidence Inventory                 COMPLETE
Gate 18.2 — Consolidated Evaluation & Reliability View     COMPLETE
Gate 18.3 — Cost Accounting & Budget Envelopes             COMPLETE
Gate 18.4 — Portfolio Evidence Pack & AIP-C01 Mapping       IN PROGRESS
```

Phases 0–17 remain complete. PR #89 / `feat/governed-gateway-semantic-planner` is unrelated deferred work and is not part of the Phase 18 authority chain.

## Retained platform architecture

OpsLens currently retains AWS dev infrastructure in `us-east-1`, source-preserving threat intelligence, deterministic repository-vulnerability correlation and Risk Policy v1, bounded semantic planning with deterministic query/SQL admission, Amazon Bedrock Knowledge Bases with Amazon S3 Vectors, hybrid structured/semantic evidence, direct Bedrock single-agent reasoning as the retained reference/default, deterministic multi-agent specialization/handoff, bounded offline MCP/A2A contracts, optional-lab AgentCore evidence, bounded Inspector read contracts, content-minimized observability, and Phase 17 security/recovery controls.

## Phase 17 retained security lineage

The current security posture still depends on the Phase 17 evidence chain. **Gate 17.1** established the evidence-first threat/control-gap inventory, and **Gate 17.2** hardened CI/CD and workflow authority before broader dependency/code scanning, adversarial, telemetry, and recovery controls were added. The retained protected-main context remains `Repository security invariants`; Phase 18 portfolio documentation does not supersede that authority.

## Phase 18 evidence chain

Gate 18.1 froze `MEASURED`, `DERIVED`, `UNMEASURED`, and `NOT_APPLICABLE`. Its canonical inventory contains 27 metrics from 8 artifacts, 20 comparability groups, and 11 explicit non-comparability assertions.

Gate 18.2 projects the same 27 metrics into five independent dimensions and preserves four decision signals: grounding failure, two-model no-lift, AgentCore-not-default, and zero-Inspector-records-not-zero-exposure.

Gate 18.3 adds a cost/resource view with:

```text
entries:                  16
cost observations:         7
resource observations:     2
configured limits:         7
UNMEASURED:                 3
NOT_APPLICABLE:             1
```

Cross-component cost summation, alternative-workload summation, and monthly extrapolation without a frozen workload remain forbidden. No production TCO exists.

## Gate 18.4 current work

Gate 18.4 creates two safe projections: a recruiter/architect-facing portfolio pack whose numeric claims remain source-bound to Gate 18.2/18.3, and an AIP-C01 evidence map covering all 20 current exam tasks with `EVIDENCED`, `PARTIAL`, or `STUDY_ONLY` states.

The certification map is a learning aid, not a readiness score and not authorization to add AWS services solely for exam coverage.

## Permanent truth boundaries

```text
Agents reason. Code verifies evidence.
Repository Risk != Runtime Exposure.
retrieved content != instruction authority
model proposal != authorization
protocol success != business truth
historical evidence != standing authority
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
one lab run != production distribution
portfolio claim != new evidence authority
AIP-C01 topic != product requirement
```

## Next checkpoint

Gate 18.4 closes only after its portfolio/AIP artifacts, validator, failure-path tests, documentation synchronization, and exact-head read-only CI pass on a protected-merge PR. No AWS/IAM/model/tool mutation is required for this gate.
