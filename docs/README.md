# OpsLens Documentation

_Last updated: 2026-09-10_

This directory contains the retained architecture, operational state, decisions, learning maps, and runbooks for OpsLens.

## Start here

- [`current-state.md`](current-state.md) — authoritative current project state and next gate.
- [`roadmap.md`](roadmap.md) — phase/gate progression and exit direction.
- [`architecture.md`](architecture.md) — retained architecture and authority boundaries.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture view.
- [`portfolio-evidence.md`](portfolio-evidence.md) — recruiter/architect-facing evidence projection.
- [`aip-c01-learning-map.md`](aip-c01-learning-map.md) — current AIP-C01 task-to-evidence learning map.
- [`adr/README.md`](adr/README.md) — Architecture Decision Record index.
- [`runbooks/`](runbooks/) — bounded operational procedures.

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
```

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
```

## Historical phases

The repository retains detailed ADRs/labs for AWS foundation and data ingestion, vulnerability correlation, repository intelligence, risk prioritization, semantic query, Bedrock Knowledge Bases/S3 Vectors, hybrid retrieval, observability, agents, MCP, AgentCore, A2A, Amazon Inspector, and Security Hardening.

Use the ADR index when the question is **why** an architecture decision was made. Use labs/evidence when the question is **what was actually measured or proven**.
