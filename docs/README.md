# OpsLens Documentation

This directory contains the public technical documentation for OpsLens.

The documentation is intentionally split by purpose:

```text
docs/
├── architecture.md
├── adr/
└── labs/
```

## Architecture

[`architecture.md`](architecture.md) describes the architecture that is implemented today.

It focuses on:

- AWS identity and deployment boundaries;
- EPSS Bronze and Silver data flow;
- event-driven transformation;
- Glue and Athena analytics;
- runtime IAM separation;
- observability and failure recovery;
- current architectural constraints.

It is not a future-state architecture document.

## Architecture Decision Records

[`adr/`](adr/) contains Architecture Decision Records.

ADRs are used only for decisions whose trade-offs should remain traceable over time.

Current records:

- [`0001 — Terraform state strategy`](adr/0001-terraform-state-strategy.md)
- [`0002 — GitHub Actions OIDC deployment identity`](adr/0002-github-actions-oidc.md)
- [`0003 — AWS regional strategy`](adr/0003-aws-region-strategy.md)

See [`adr/README.md`](adr/README.md) for the ADR index.

## Labs and operational evidence

[`labs/`](labs/) contains reproducible operational experiments, failure investigations, and validation evidence.

Phase 0:

- [`phase-0-iam-oidc-failure.md`](labs/phase-0-iam-oidc-failure.md)
- [`phase-0-cloudwatch-authorization-failure.md`](labs/phase-0-cloudwatch-authorization-failure.md)

Phase 1:

- [`phase-1-epss-athena-query.md`](labs/phase-1-epss-athena-query.md)

The Phase 1 lab documents:

- the validated EPSS Athena query;
- the exact snapshot used;
- Athena execution statistics;
- bytes scanned;
- approximate query cost;
- Athena-to-Parquet cross-check;
- Athena-to-raw-source cross-check.

## Documentation conventions

Public repository documentation should describe:

- implemented behavior;
- architectural decisions;
- reproducible evidence;
- operational lessons;
- security boundaries;
- cost and observability characteristics when relevant.

Planning and conversational coordination artifacts are intentionally kept outside the public repository.

## Current milestone

```text
Phase 0 — AWS Foundation:          COMPLETE
Phase 1 — EPSS Vertical Slice:     COMPLETE
Phase 2 — Threat Intelligence Lake: NEXT
```
