# OpsLens Documentation

This directory contains the public technical documentation for OpsLens.

```text
docs/
├── architecture.md
├── architecture.pt-br.md
├── adr/
└── labs/
```

## Architecture

[`architecture.md`](architecture.md) contains the accumulated English architecture baseline through the complete NVD Bronze, Silver, authoritative watermark, permanent analytics projection, Glue, and Athena path. [`architecture.pt-br.md`](architecture.pt-br.md) provides the equivalent Portuguese architecture document.

The deployed Phase 2.3E/2.3F NVD runtime architecture and its real AWS evidence are captured in [`phase-2-nvd-authoritative-runtime-closeout.md`](labs/phase-2-nvd-authoritative-runtime-closeout.md). The Phase 2.3G permanent analytics implementation and evidence are captured by the NVD Glue/Athena lab series below.

The current implementation includes AWS identity and deployment boundaries, FIRST EPSS Bronze/Silver/Glue/Athena, the complete CISA KEV Bronze/Silver/Glue/Athena path, NVD CVE JSON 2.0 Bootstrap Bronze, incremental CVE API Bronze, versioned NVD Silver, deployed Incremental/Silver/Promotion runtimes, the authoritative watermark boundary, EventBridge Scheduler, runtime IAM separation, idempotency, observability, bounded failure recovery, the permanent NVD Glue/Athena analytics projection path, and immutable content-addressed deployment artifacts for all deployed Lambda runtimes.

Phase 2.4A has completed the GitHub Security Advisory source and synchronization contract before any GHSA AWS runtime is created.

## Architecture Decision Records

- [`0001 — Terraform state strategy`](adr/0001-terraform-state-strategy.md)
- [`0002 — GitHub Actions OIDC deployment identity`](adr/0002-github-actions-oidc.md)
- [`0003 — AWS regional strategy`](adr/0003-aws-region-strategy.md)
- [`0004 — NVD ingestion and vulnerability versioning strategy`](adr/0004-nvd-ingestion-and-versioning-strategy.md)
- [`0005 — GHSA source and synchronization strategy`](adr/0005-ghsa-source-and-synchronization-strategy.md) — Accepted from the completed Phase 2.4A source-contract and bounded live-workload evidence.

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
- [`phase-2-nvd-glue-athena-permanent-catalog.md`](labs/phase-2-nvd-glue-athena-permanent-catalog.md)
- [`phase-2-nvd-glue-athena-artifact-build.md`](labs/phase-2-nvd-glue-athena-artifact-build.md)
- [`phase-2-nvd-glue-athena-bootstrap-permanent-seed-proof.md`](labs/phase-2-nvd-glue-athena-bootstrap-permanent-seed-proof.md)
- [`phase-2-nvd-glue-athena-incremental-event-proof.md`](labs/phase-2-nvd-glue-athena-incremental-event-proof.md)
- [`phase-2-nvd-glue-athena-permanent-athena-proof.md`](labs/phase-2-nvd-glue-athena-permanent-athena-proof.md)
- [`phase-2-nvd-glue-athena-failure-replay-observability-proof.md`](labs/phase-2-nvd-glue-athena-failure-replay-observability-proof.md)
- [`phase-2-ghsa-documentation-reconciliation.md`](labs/phase-2-ghsa-documentation-reconciliation.md) — Phase 2.4-0 reconciliation of public documentation against the post-PR #28 `main` checkpoint before GHSA implementation.
- [`phase-2-ghsa-source-contract.md`](labs/phase-2-ghsa-source-contract.md) — completed Phase 2.4A source contract and workload-spike decision record.
- [`phase-2-ghsa-live-rest-probe.md`](labs/phase-2-ghsa-live-rest-probe.md) — authenticated live evidence for cursor pagination, rate limits, published/modified bounded windows, payload sizes, timings, and advisory/package multiplicity.

Cross-phase infrastructure closeout:

- [`legacy-lambda-artifact-lifecycle-migration.md`](labs/legacy-lambda-artifact-lifecycle-migration.md) — completed migration of the remaining local-file Lambda deployment artifacts to immutable content-addressed S3 pins, including exact S3 VersionId provenance and full dev convergence proof.

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
Phase 2.3G — NVD Glue/Athena Analytics:      COMPLETE
Legacy Lambda artifact lifecycle migration: COMPLETE
Phase 2.4-0 — Documentation reconciliation:  COMPLETE
Phase 2.4A — GHSA Source Contract:           COMPLETE
Phase 2.4B — GHSA Advisory/Silver Contract:  NEXT
Phase 2.5 — Historical EPSS expansion:       NOT STARTED
Phase 3 — Vulnerability Correlation Engine:  NOT STARTED
```

Phase 2.4A accepted the versioned reviewed GHSA REST source, authenticated production requirement, exact cursor pagination, calendar-month published bootstrap default, bounded closed modified-time synchronization, GHSA-first identity with optional CVE aliases, one-to-many package evidence, nullable structured patched-version evidence, and logical-versus-physical observation identity.

No GHSA AWS runtime was introduced by Phase 2.4A.

Phase 2 remains open. Phase 2.4B is the next GHSA gate; historical EPSS expansion follows later before Phase 2 can be closed or any Phase 3 work begins.
