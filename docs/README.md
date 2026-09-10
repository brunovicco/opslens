# OpsLens Documentation

_Last updated: 2026-09-10_

This directory contains the retained architecture, operational state, decisions, learning maps, and runbooks for OpsLens.

## Start here

- [`current-state.md`](current-state.md) — authoritative current project state and next decision boundary.
- [`roadmap.md`](roadmap.md) — phase/gate progression and evidence-gated direction.
- [`architecture.md`](architecture.md) — retained architecture and authority boundaries.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture view.
- [`portfolio-evidence.md`](portfolio-evidence.md) — recruiter/architect-facing evidence projection.
- [`aip-c01-learning-map.md`](aip-c01-learning-map.md) — current AIP-C01 task-to-evidence learning map.
- [`adr/README.md`](adr/README.md) — Architecture Decision Record index.
- [`runbooks/`](runbooks/) — bounded operational procedures.

## Retained security lineage

Phase 18 remains downstream of Phase 17. **Gate 17.1** established the evidence-first threat/control-gap inventory and **Gate 17.2** hardened CI/CD and workflow authority. The `Repository security invariants` protected-main context and later Phase 17 hardening controls remain part of the retained documentation/evidence authority chain.

## Phase 18 evidence chain

```text
Gate 18.1
cross-phase evidence inventory + comparability matrix
        |
        v
Gate 18.2
consolidated evaluation & reliability view
        |
        v
Gate 18.3
cost accounting & configured budget envelopes
        |
        v
Gate 18.4
portfolio projection + AIP-C01 evidence map
        |
        v
Gate 18.5
Phase 18 evidence-backed closeout
```

Gates 18.1–18.4 are complete. Gate 18.5 closes the phase after exact-head CI and protected merge; it adds no AWS/IAM/model/capability authority and no new benchmark.

Canonical machine-readable artifacts live under `../labs/evidence/`. Human-readable experiment and closeout records live under `../labs/`.

Phase 18 preserves:

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

The Phase 18 closeout record is [`../labs/phase-18-closeout.md`](../labs/phase-18-closeout.md), with machine-readable evidence at [`../labs/evidence/phase-18-closeout-v1.json`](../labs/evidence/phase-18-closeout-v1.json).

## Historical phases

The repository retains detailed ADRs/labs for AWS foundation and data ingestion, vulnerability correlation, repository intelligence, risk prioritization, semantic query, Bedrock Knowledge Bases/S3 Vectors, hybrid retrieval, observability, agents, MCP, AgentCore, A2A, Amazon Inspector, Security Hardening, and Evaluation/Cost/Portfolio Readiness.

Use the ADR index when the question is **why** an architecture decision was made. Use labs/evidence when the question is **what was actually measured or proven**.

The next implementation phase is intentionally not pre-authorized. It must be selected from observed product/evidence gaps after the Phase 18 closeout protected merge. PR #89 remains separate deferred work unless explicitly re-evaluated and resumed.
