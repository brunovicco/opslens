# OpsLens Documentation

_Last updated: 2026-09-10_

This directory contains the retained architecture, operational state, decisions, learning maps, and runbooks for OpsLens.

## Start here

- [`current-state.md`](current-state.md) — authoritative current project state and next decision boundary.
- [`roadmap.md`](roadmap.md) — evidence-gated phase/gate progression.
- [`architecture.md`](architecture.md) — retained architecture and authority boundaries.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture view.
- [`portfolio-evidence.md`](portfolio-evidence.md) — recruiter/architect-facing evidence projection.
- [`aip-c01-learning-map.md`](aip-c01-learning-map.md) — current AIP-C01 task-to-evidence learning map.
- [`adr/README.md`](adr/README.md) — Architecture Decision Record index.
- [`runbooks/`](runbooks/) — bounded operational procedures.

## Retained security lineage

Phase 19 remains downstream of the Phase 17 security controls and the Phase 18 evidence closeout. **Gate 17.1** established the evidence-first threat/control-gap inventory, and **Gate 17.2** hardened CI/CD and workflow authority. The `Repository security invariants` protected-main context, full-SHA external actions, Dependency Review, CodeQL, adversarial authority regression, content-minimized Lambda telemetry, and the narrowly scoped scheduled-ingestion pause remain part of the retained platform authority chain.

## Phase 18 closeout

Phase 18 is complete. Its protected closeout was squash-merged through PR #290 at:

```text
feca774535b7d83f57c26f4e9fe7da71ce268f0f
```

The historical Phase 18 closeout artifacts intentionally preserve the state that existed before their protected merge:

- [`../labs/phase-18-closeout.md`](../labs/phase-18-closeout.md)
- [`../labs/evidence/phase-18-closeout-v1.json`](../labs/evidence/phase-18-closeout-v1.json)
- [`adr/0075-phase18-evaluation-cost-portfolio-closeout.md`](adr/0075-phase18-evaluation-cost-portfolio-closeout.md)

Do not rewrite those historical artifacts to make them look post-merge. Current-facing documents carry the post-merge state instead.

The retained Phase 18 evidence semantics remain:

```text
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
lab measurement != production SLO
cost evidence != production TCO
portfolio claim != new evidence authority
AIP-C01 topic != product requirement
AIP-C01 coverage != certification guarantee
historical experiment != standing authority
```

## Phase 19 — Bounded Public Runtime & Productization

Gate 19.1 is the current implementation boundary:

```text
public-analysis-workload:v1
runtime decision: DEFERRED_PENDING_MEASUREMENT
leading hypothesis: ASYNC_SUBMIT_STATUS_RESULT
AWS mutations: 0
IAM mutations: 0
new AWS resources: 0
public endpoints: 0
model/capability executions: 0
```

The Gate 19.1 human-readable lab is [`../labs/phase-19-gate-19-1-public-runtime-hypothesis.md`](../labs/phase-19-gate-19-1-public-runtime-hypothesis.md). Its machine-readable contract is [`../labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`](../labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json), with architecture decision rationale in [`adr/0076-bounded-public-runtime-hypothesis-and-launch-contract.md`](adr/0076-bounded-public-runtime-hypothesis-and-launch-contract.md).

Gate 19.1 does not deploy API Gateway, Lambda Function URLs, public Lambda compute, SQS, a result store, WAF, ECS/Fargate, AgentCore, or runtime IAM. It first distinguishes the retained application boundary from the downstream capabilities that exist but are not yet composed into one public product execution.

Current runtime selection remains deferred until Gate 19.2 measures a representative **non-public** product workload end to end. `ASYNC_SUBMIT_STATUS_RESULT` is a leading hypothesis, not a selected topology.

## Evidence location rule

Canonical machine-readable artifacts live under `../labs/evidence/`. Human-readable experiment and closeout records live under `../labs/`. ADRs explain why a decision was made; labs/evidence record what was measured, proven, rejected, or intentionally left `UNMEASURED`.

PR #89 remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency unless explicitly re-evaluated later.
