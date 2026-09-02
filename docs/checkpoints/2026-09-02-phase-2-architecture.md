# OpsLens — Phase 2 Closeout Architecture

_Last updated: 2026-09-02_

This document records the architecture delta required to close Phase 2 after Historical EPSS completion. It supplements the accumulated architecture baseline without starting Phase 3.

## Phase 2 data plane at closeout

```text
FIRST EPSS current snapshots
    -> Scheduler
    -> EPSS ingestion Lambda
    -> S3 Bronze
    -> EPSS Silver Lambda
    -> shared EPSS Silver / Parquet
    -> Glue / Athena

CISA KEV
    -> Scheduler
    -> KEV ingestion Lambda
    -> S3 Bronze
    -> KEV Silver Lambda
    -> Silver / Parquet
    -> Glue / Athena

NVD yearly feeds + CVE API 2.0
    -> immutable Bronze
    -> versioned Silver
    -> Silver COMPLETE
    -> authoritative watermark
    -> analytics projection
    -> Glue / Athena

GitHub Security Advisories
    -> reviewed-advisory Bronze
    -> immutable advisory-version Silver
    -> Silver COMPLETE
    -> Glue / Athena

Pinned Historical EPSS archive
    -> frozen full-plan coordinator
    -> historical Bronze + manifest
    -> dedicated historical transformer
    -> shared canonical EPSS Silver
    -> historical completion manifest
    -> independent read-only evidence verification
```

All source paths preserve source-local authority. Phase 2 does not create a lossy universal source record and does not delegate deterministic applicability decisions to a model.

## Historical EPSS source authority

Historical bulk source authority is the immutable public Git repository pin:

```text
repository: empiricalsec/epss_scores
commit:     7ba701f5599057c496489ceecd701cbd43911f5c
root tree:  2a12b2030cda9b94573bca01b67a6f0d72ab71e8
```

The canonical forward EPSS path remains authoritative from the first current snapshot already present in `dev`:

```text
first_forward_snapshot_date = 2026-08-14
```

Therefore historical eligibility is strictly:

```text
snapshot_date < 2026-08-14
```

The frozen historical workload contains 1,939 available source snapshots from `2021-04-14` through `2026-08-13`, plus nine explicit source-absent dates.

## Historical Bronze

Canonical historical Bronze layout:

```text
bronze/epss-history/schema_version=1/
  archive_commit=<40-char-sha>/
    snapshot_date=YYYY-MM-DD/
      epss_scores.csv.gz
      manifest.json
```

The source object is create-only. Existing keys can satisfy replay only after exact current-version verification.

The manifest binds:

- archive repository;
- archive commit;
- archive path;
- Git blob SHA-1;
- compressed source byte size;
- snapshot date;
- model era;
- metadata-presence semantics;
- source object key;
- exact source object VersionId;
- source SHA-256.

The manifest is the invocation authority for historical transformation.

## Historical model-era compatibility

The pinned archive spans five documented model eras:

```text
v1: 2021-04-14 .. 2022-02-03
v2: 2022-02-04 .. 2023-03-06
v3: 2023-03-07 .. 2025-03-16
v4: 2025-03-17 .. 2026-06-14
v5: 2026-06-15 .. historical boundary
```

Historical parsing preserves physical source truth:

- v1 has no fabricated model version or score timestamp;
- early v1 may not contain percentile;
- later v1 may physically contain percentile;
- v2+ requires source metadata and documented model-version agreement;
- nullable Silver fields preserve unavailable legacy evidence rather than inventing values.

Final frozen era counts are:

```text
v1  289
v2  395
v3  740
v4  455
v5   60
```

## Shared EPSS Silver

Historical transformation writes to the same canonical deterministic Silver namespace used by forward EPSS:

```text
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

This creates one temporal EPSS relation rather than separate historical and forward analytical schemas.

Historical Silver uses the EPSS Silver v2 physical contract with nullable legacy fields and deterministic Parquet serialization. Existing deterministic keys are replay-verified byte-for-byte rather than overwritten.

## Completion evidence

Completion is written only after verified Bronze and verified Silver exist:

```text
silver/epss-history/completions/schema_version=1/
  archive_commit=<sha>/
    snapshot_date=YYYY-MM-DD/
      manifest.json
```

Completion binds the exact Bronze manifest VersionId, exact source VersionId/SHA-256, exact Silver VersionId/SHA-256, schema version, row count, snapshot date, and archive commit.

Replay status is intentionally not invocation-specific in durable completion bytes. The completion artifact represents snapshot authority, so retries reproduce identical completion bytes.

## Full-backfill coordinator

The full coordinator has no arbitrary subset, date-range, archive, function, bucket, or concurrency controls.

Frozen execution contract:

```text
candidate_count              1939
candidate_compressed_bytes   2537138865
plan_id                      3b3c8c58009f46b61f6bb9e82f6b6c0bcf675e72b940326d7fcccf962d7bd4de
execution_order              snapshot_date_ascending
coordinator_concurrency      1
first_error                  stop
```

Execution requires the exact confirmation token and a fresh plan that matches the frozen authority before mutation.

The coordinator role has a six-hour maximum STS session because real full execution required approximately three hours. The session-duration change was made without broadening the data-plane scope.

## Independent evidence plane

Phase 2 closeout adds a distinct read-only audit identity:

```text
GitHub Actions
    -> OIDC
    -> OpsLensEpssHistoryEvidenceRole
    -> S3 ListBucket / ListBucketVersions
    -> S3 GetObject / GetObjectVersion
```

The evidence role is restricted to the required EPSS prefixes and has no data mutation or Lambda invocation authority.

The verifier:

1. rebuilds the frozen plan from the current forward boundary and pinned Git inventory;
2. inventories historical Bronze source and manifest objects;
3. inventories canonical EPSS Silver and historical completion objects;
4. validates Bronze provenance, SHA-256, Git blob identity, and VersionId authority;
5. reconstructs deterministic Silver from exact Bronze evidence and compares persisted bytes;
6. reconstructs deterministic completion bytes and compares persisted authority;
7. validates all retained versions for the seven frozen canary dates;
8. proves the nine source-absent dates contain no historical artifacts;
9. proves the historical namespace does not cross the `2026-08-14` forward boundary;
10. emits a machine-readable PASS/FAIL result.

The successful read-only evidence run is `33626865216`.

## Identity separation

At Phase 2 closeout, the relevant trust boundaries are intentionally distinct:

```text
Human bootstrap
    -> IAM Identity Center temporary credentials

GitHub deployment
    -> OpsLensGitHubDeployRole

Forward ingestion/transformation
    -> source-specific runtime roles

Historical EPSS execution
    -> OpsLensEpssHistoryCoordinatorRole
    -> dedicated historical transformer runtime role

Historical EPSS audit
    -> OpsLensEpssHistoryEvidenceRole
```

The actor that verifies the completed backfill cannot modify the evidence being verified.

## Failure behavior proven during D5

The closeout preserved fail-closed behavior across three different defects:

- deterministic completion mismatch stopped execution before historical progress;
- STS expiration stopped execution without deleting or skipping prior completed snapshots;
- insufficient deploy-role IAM stopped Terraform before the coordinator session-duration mutation.

Each defect was remediated narrowly and followed by convergence or fresh plan validation before another write attempt.

## Phase 3 architectural boundary

Phase 3 may consume the complete Phase 2 evidence plane, but it must not weaken its authority model.

The following remain deterministic:

```text
package identity normalization
version parsing / comparison
vulnerable-range evaluation
fixed-version evaluation
CVE/GHSA alias handling
vulnerability applicability
match evidence construction
```

No LLM decides whether a package/version is vulnerable. Generative or agentic behavior remains downstream of validated deterministic evidence.
