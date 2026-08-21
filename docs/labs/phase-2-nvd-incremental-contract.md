# Phase 2.3C — NVD Incremental CVE API Bronze Contract

_Date: 2026-08-21_

## Scope

Phase 2.3C implements the deterministic application and domain contract for
incremental NVD CVE API 2.0 ingestion.

It does not deploy a new AWS runtime and it does not implement NVD Silver.

The architectural invariant remains:

> **Agents reason. Code verifies evidence.**

## Implemented flow

```text
closed lastModified window
    |
    v
NVD CVE API 2.0
    |
    v
complete pagination validation
    |
    v
immutable Bronze pages
    |
    v
COMPLETE manifest
    |
    v
bronze_complete watermark candidate
    |
    X
no authoritative watermark advancement
```

## Contract boundaries

The implementation provides:

- timezone-aware closed windows with deterministic `update_id`;
- CVE API page-envelope validation;
- fail-closed pagination consistency checks;
- bounded HTTP retrieval with polite pacing and transient retries;
- exact-response-byte preservation;
- immutable conditional Bronze persistence;
- exact S3 `VersionId` evidence;
- deterministic COMPLETE manifest serialization;
- Bronze-complete watermark candidate state;
- application orchestration and deterministic replay behavior.

The authoritative watermark remains unchanged until deterministic Silver
processing is successfully completed by a later increment.

## Failure behavior

Pagination inconsistency fails before any Bronze write.

A page persistence failure may leave immutable partial page evidence, but
the COMPLETE manifest is not written.

A replay of the same logical window reuses the same `update_id`, object
keys, exact object versions, manifest bytes, and candidate bytes.

## Closeout evidence

The Phase 2.3C branch is based on the Phase 2.3B merge commit and contains
seven implementation commits.

The branch diff is restricted to NVD ingestion source and unit-test paths.

Validated gates:

```text
Ruff lint                         PASS
Pyright strict                    PASS
full Pytest regression suite      PASS
NVD unit regression suite         PASS
git diff --check                  PASS
Phase 2.3C scoped Ruff format     PASS
out-of-scope source changes       NONE
NVD Silver implementation         NONE
new runtime infrastructure        NONE
authoritative watermark write     NONE
```

A repository-wide `ruff format --check .` currently reports formatter drift
in pre-existing KEV and EPSS files that are unchanged by this branch.
Those unrelated files are intentionally excluded from the Phase 2.3C PR.

## Exit decision

Phase 2.3C is complete once this documentation closeout is merged.

The next implementation increment is:

```text
Phase 2.3D — Versioned Silver Contract
```
