# OpsLens Documentation

This directory contains the public technical documentation for OpsLens.

```text
docs/
├── architecture.md
├── adr/
└── labs/
```

## Architecture

[`architecture.md`](architecture.md) describes the architecture implemented today.

It covers AWS identity and deployment boundaries, FIRST EPSS Bronze/Silver/Glue/Athena, CISA KEV Bronze ingestion, EventBridge Scheduler, runtime IAM separation, idempotency, observability, asynchronous failure recovery, and current architectural constraints.

It is not a speculative future-state architecture document.

## Architecture Decision Records

- [`0001 — Terraform state strategy`](adr/0001-terraform-state-strategy.md)
- [`0002 — GitHub Actions OIDC deployment identity`](adr/0002-github-actions-oidc.md)
- [`0003 — AWS regional strategy`](adr/0003-aws-region-strategy.md)

See [`adr/README.md`](adr/README.md) for the ADR index.

## Labs and operational evidence

Phase 0:

- [`phase-0-iam-oidc-failure.md`](labs/phase-0-iam-oidc-failure.md)
- [`phase-0-cloudwatch-authorization-failure.md`](labs/phase-0-cloudwatch-authorization-failure.md)

Phase 1:

- [`phase-1-epss-athena-query.md`](labs/phase-1-epss-athena-query.md)

Phase 2:

- [`phase-2-kev-async-failure-recovery.md`](labs/phase-2-kev-async-failure-recovery.md)

## Current milestone

```text
Phase 0 — AWS Foundation:              COMPLETE
Phase 1 — EPSS Vertical Slice:         COMPLETE
Phase 2.1 — CISA KEV Bronze:           FINAL RUNTIME VALIDATION
Phase 2.2 — CISA KEV Silver/Analytics: NEXT
```
