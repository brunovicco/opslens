# OpsLens — Current State

_Last updated: 2026-09-10_

## Authoritative checkpoint

```text
protected main after Gate 18.4:
4a8e5d3d98504451cef26df4e9f274f2f9fd8dd0

Phase 18 — Evaluation, Cost & Portfolio Readiness
status: COMPLETE PENDING GATE 18.5 PROTECTED MERGE

Gate 18.1 — Cross-phase Evidence Inventory                 COMPLETE
Gate 18.2 — Consolidated Evaluation & Reliability View     COMPLETE
Gate 18.3 — Cost Accounting & Budget Envelopes             COMPLETE
Gate 18.4 — Portfolio Evidence Pack & AIP-C01 Mapping       COMPLETE
Gate 18.5 — Phase 18 closeout                               IN PROGRESS
```

Phases 0–17 remain complete. PR #89 / `feat/governed-gateway-semantic-planner` is unrelated deferred work and is not part of the Phase 18 authority chain.

## Retained platform architecture

OpsLens retains AWS dev infrastructure in `us-east-1`, source-preserving threat intelligence, deterministic repository-vulnerability correlation and Risk Policy v1, bounded semantic planning with deterministic query/SQL admission, Amazon Bedrock Knowledge Bases with Amazon S3 Vectors, hybrid structured/semantic evidence, direct Bedrock single-agent reasoning as the retained reference/default, deterministic multi-agent specialization/handoff, bounded offline MCP/A2A contracts, optional-lab AgentCore evidence, bounded Inspector read contracts, content-minimized observability, Phase 17 security/recovery controls, and Phase 18 evaluation/cost/portfolio evidence surfaces.

## Phase 17 retained security lineage

The security posture still depends on the Phase 17 evidence chain. **Gate 17.1** established the evidence-first threat/control-gap inventory, and **Gate 17.2** hardened CI/CD and workflow authority before dependency/code scanning, adversarial, telemetry, and recovery controls were added. The retained protected-main context remains `Repository security invariants`; Phase 18 evidence projections do not supersede that authority.

## Phase 18 retained evidence chain

Gate 18.1 froze `MEASURED`, `DERIVED`, `UNMEASURED`, and `NOT_APPLICABLE`. Its canonical inventory contains 27 metrics from 8 artifacts, 20 comparability groups, and 11 explicit non-comparability assertions.

Gate 18.2 projects the same 27 metrics into five independent dimensions and preserves four decision signals: grounding failure, two-model no-lift, AgentCore-not-default, and zero-Inspector-records-not-zero-exposure.

Gate 18.3 adds a cost/resource view with 16 entries: 7 cost observations, 2 resource observations, 7 configured limits, 3 `UNMEASURED`, and 1 `NOT_APPLICABLE`. Cross-component cost summation, alternative-workload summation, and monthly extrapolation without a frozen workload remain forbidden. No production TCO exists.

Gate 18.4 adds two safe projections: a recruiter/architect-facing portfolio pack whose numeric claims remain mechanically bound to Gate 18.2/18.3, and an AIP-C01 evidence map covering all 20 current exam tasks with `EVIDENCED`, `PARTIAL`, or `STUDY_ONLY` semantics. The retained map currently classifies 14 tasks as `EVIDENCED` and 6 as `PARTIAL`; explicit study-only topics remain separate and do not imply implementation.

Gate 18.4 protected merge evidence:

```text
PR:                       #288
exact head:               c1eef255e6a98fb9a556fea191db8a41d13c2437
protected squash merge:   4a8e5d3d98504451cef26df4e9f274f2f9fd8dd0
Security Hardening CI:    34508507768 / SUCCESS
Dependency Review:        34508507778 / SUCCESS
Evaluation Readiness CI:  34508507792 / SUCCESS
AgentCore CI:             34508507802 / SUCCESS
CodeQL:                   34508507840 / SUCCESS
```

## Gate 18.5 closeout boundary

Gate 18.5 adds no new benchmark, model call, AWS service, IAM authority, capability execution, production SLO, production TCO, or readiness score. It only records the completed Phase 18 evidence chain, synchronizes repository-facing documentation, and keeps the next implementation direction explicitly un-authorized until selected from observed product/evidence gaps.

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
AIP-C01 coverage != certification guarantee
cost evidence != production TCO
```

## Next checkpoint

After Gate 18.5 is protected-merged with exact-head CI green, Phase 18 is complete. The next implementation phase is intentionally **not authorized yet**; it must be chosen from observed product/evidence gaps. PR #89 remains deferred unless separately re-evaluated and explicitly resumed.
