# OpsLens Documentation

This directory contains the public technical documentation for OpsLens.

```text
docs/
├── architecture.md
├── adr/
└── labs/
```

## Architecture

[`architecture.md`](architecture.md) contains the accumulated architecture baseline through the NVD versioned Silver contract.

The deployed Phase 2.3E/2.3F NVD runtime architecture and its real AWS evidence are captured in [`phase-2-nvd-authoritative-runtime-closeout.md`](labs/phase-2-nvd-authoritative-runtime-closeout.md). Together they document the currently implemented architecture without introducing speculative future-state components.

The current implementation includes AWS identity and deployment boundaries, FIRST EPSS Bronze/Silver/Glue/Athena, the complete CISA KEV Bronze/Silver/Glue/Athena path, NVD CVE JSON 2.0 Bootstrap Bronze, incremental CVE API Bronze, versioned NVD Silver, deployed Incremental/Silver/Promotion runtimes, the authoritative watermark boundary, EventBridge Scheduler, runtime IAM separation, idempotency, observability, and bounded failure recovery.

## Architecture Decision Records

- [`0001 — Terraform state strategy`](adr/0001-terraform-state-strategy.md)
- [`0002 — GitHub Actions OIDC deployment identity`](adr/0002-github-actions-oidc.md)
- [`0003 — AWS regional strategy`](adr/0003-aws-region-strategy.md)
- [`0004 — NVD ingestion and vulnerability versioning strategy`](adr/0004-nvd-ingestion-and-versioning-strategy.md)

See [`adr/README.md`](adr/README.md) for the ADR index.

## Labs and operational evidence

Phase 0:

- [`phase-0-iam-oidc-failure.md`](labs/phase-0-iam-oidc-failure.md)
- [`phase-0-cloudwatch-authorization-failure.md`](labs/phase-0-cloudwatch-authorization-failure.md)

Phase 1:

- [`phase-1-epss-athena-query.md`](labs/phase-1-epss-athena-query.md)

Phase 2:

- [`phase-2-kev-async-failure-recovery.md`](labs/phase-2-kev-async-failure-recovery.md)
- [`phase-2-kev-silver-runtime.md`](labs/phase-2-kev-silver-runtime.md)
- [`phase-2-kev-athena-query.md`](labs/phase-2-kev-athena-query.md)
- [`phase-2-nvd-source-contract.md`](labs/phase-2-nvd-source-contract.md)
- [`phase-2-nvd-bootstrap-bronze.md`](labs/phase-2-nvd-bootstrap-bronze.md)
- [`phase-2-nvd-incremental-contract.md`](labs/phase-2-nvd-incremental-contract.md)
- [`phase-2-nvd-versioned-silver-contract.md`](labs/phase-2-nvd-versioned-silver-contract.md)
- [`phase-2-nvd-silver-workload-proof.md`](labs/phase-2-nvd-silver-workload-proof.md)
- [`phase-2-nvd-authoritative-runtime-closeout.md`](labs/phase-2-nvd-authoritative-runtime-closeout.md)
- [`phase-2-nvd-glue-athena-design.md`](labs/phase-2-nvd-glue-athena-design.md)
- [`phase-2-nvd-glue-athena-source-evidence.md`](labs/phase-2-nvd-glue-athena-source-evidence.md)
- [`phase-2-nvd-glue-athena-bootstrap-evidence.md`](labs/phase-2-nvd-glue-athena-bootstrap-evidence.md)
- [`phase-2-nvd-glue-athena-symlink-proof.md`](labs/phase-2-nvd-glue-athena-symlink-proof.md)
- [`phase-2-nvd-glue-athena-projection-design.md`](labs/phase-2-nvd-glue-athena-projection-design.md)
- [`phase-2-nvd-glue-athena-projection-proof.md`](labs/phase-2-nvd-glue-athena-projection-proof.md)
- [`phase-2-nvd-glue-athena-direct-parquet-proof.md`](labs/phase-2-nvd-glue-athena-direct-parquet-proof.md)
- [`phase-2-nvd-glue-athena-incremental-cleanup-proof.md`](labs/phase-2-nvd-glue-athena-incremental-cleanup-proof.md)
- [`phase-2-nvd-glue-athena-bootstrap-projection-proof.md`](labs/phase-2-nvd-glue-athena-bootstrap-projection-proof.md)
- [`phase-2-nvd-glue-athena-bootstrap-athena-proof.md`](labs/phase-2-nvd-glue-athena-bootstrap-athena-proof.md)
- [`phase-2-nvd-glue-athena-bootstrap-cleanup-proof.md`](labs/phase-2-nvd-glue-athena-bootstrap-cleanup-proof.md)
- [`phase-2-nvd-glue-athena-permanent-path-design.md`](labs/phase-2-nvd-glue-athena-permanent-path-design.md)
- [`phase-2-nvd-glue-athena-runtime-terraform.md`](labs/phase-2-nvd-glue-athena-runtime-terraform.md)

## Current milestone

```text
Phase 0 — AWS Foundation:                    COMPLETE
Phase 1 — EPSS Vertical Slice:               COMPLETE
Phase 2.1 — CISA KEV Bronze:                 COMPLETE
Phase 2.2 — CISA KEV Silver/Analytics:       COMPLETE
Phase 2.3A — NVD Source Contract:            COMPLETE
Phase 2.3B — NVD Bootstrap Bronze:           COMPLETE
Phase 2.3C — NVD Incremental API Contract:   COMPLETE
Phase 2.3D — NVD Versioned Silver Contract:  COMPLETE
Phase 2.3E — NVD Silver AWS Runtime:         COMPLETE
Phase 2.3F — NVD Authoritative Watermark:    COMPLETE
Phase 2.3G — NVD Glue/Athena Analytics:      IN PROGRESS
```
