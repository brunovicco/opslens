# Phase 2.4-0 — Documentation Reconciliation

_Date: 2026-08-27_

## Purpose

Phase 2.4-0 reconciles the public repository documentation with the real `main` checkpoint before any GitHub Security Advisories implementation begins.

This is a documentation-only gate. It does not add GHSA ingestion, AWS resources, runtime IAM, schedulers, schemas, correlation logic, Bedrock, RAG, or agentic capabilities.

## Baseline verified

Repository baseline before this reconciliation:

```text
branch: main
commit: 5e4147533311e0f7212f02ffaaba37d1a5dbd667
PR:     #28 — fix(infra): pin legacy Lambda deployment artifacts
status: merged
```

PR #28 completed the migration of the remaining EPSS, KEV, and NVD Bootstrap Lambda deployments from mutable local ZIP inputs to immutable, content-addressed, versioned S3 artifact coordinates.

The validated environment closeout was:

```text
No changes. Your infrastructure matches the configuration.
POST_APPLY_PLAN_RC=0
```

## Reconciled drift

### Legacy Lambda artifact lifecycle

Some public documentation still described a pre-existing Terraform convergence exception for legacy EPSS, KEV, and NVD Bootstrap Lambda hashes.

That statement became stale after PR #28.

The canonical state is now:

```text
all deployed Lambda artifacts
    -> deterministic build
    -> SHA-256 identity
    -> content-addressed S3 key
    -> exact S3 VersionId
    -> Terraform immutable pin
```

There is no remaining known global `dev` Terraform drift from that legacy artifact lifecycle at this checkpoint.

### NVD incremental physical-observation identity

Some public diagrams still showed incremental NVD pages directly below `update_id`.

The implemented contract distinguishes:

```text
update_id
    logical incremental-window identity

attempt_id
    exact physical source-observation identity
```

The canonical Bronze hierarchy therefore includes both identities:

```text
bronze/nvd/cve/updates/
  update_id=<logical-window-identity>/
    attempt_id=<exact-physical-observation>/
      page_start=.../response.json
    manifest.json
```

This distinction protects replay semantics when the NVD API returns different exact bytes for the same logical window.

### Phase 3 naming and scope

Public documentation used the label `AI reasoning / agentic capabilities` for Phase 3.

The canonical roadmap defines Phase 3 as:

```text
Phase 3 — Vulnerability Correlation Engine
```

Its responsibility is deterministic package/version-to-vulnerability matching. LLMs do not decide vulnerability applicability.

Bedrock semantic planning starts later in Phase 6, and agentic work starts later still.

## Milestone boundary after this gate

After Phase 2.4-0:

```text
Phase 0 — AWS Foundation:                    COMPLETE
Phase 1 — EPSS Vertical Slice:               COMPLETE
Phase 2.1 — CISA KEV Bronze:                 COMPLETE
Phase 2.2 — CISA KEV Silver/Analytics:       COMPLETE
Phase 2.3A–2.3G — NVD/CVE:                   COMPLETE
Legacy Lambda artifact lifecycle migration: COMPLETE
Phase 2.4-0 — Documentation reconciliation:  COMPLETE
Phase 2.4A — GHSA Source Contract:           NEXT
Phase 2.5 — Historical EPSS expansion:       NOT STARTED
Phase 3 — Vulnerability Correlation Engine:  NOT STARTED
```

Phase 2 remains open.

## Next gate

The next implementation gate is **Phase 2.4A — GHSA Source Contract & Workload Spike**.

Before creating AWS resources, Phase 2.4A must validate the current official GitHub Security Advisory interface and decide:

- authoritative source/API;
- authentication and rate-limit behavior;
- pagination and bounded retrieval;
- snapshot vs incremental/update semantics;
- advisory identity and update identity;
- GHSA/CVE alias semantics;
- package ecosystem and package identity boundaries;
- affected-version-range representation;
- fixed-version evidence representation;
- source provenance and replay semantics.

Package/version applicability remains outside Phase 2.4 and belongs to the deterministic Phase 3 correlation engine.

## Invariant

> **Agents reason. Code verifies evidence.**
