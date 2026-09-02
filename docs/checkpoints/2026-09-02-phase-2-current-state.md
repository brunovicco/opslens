# OpsLens — Phase 2 Closeout Current State

_Last updated: 2026-09-02_

This checkpoint records the repository and deployed `dev` environment immediately after the completed Phase 2.5 Historical EPSS backfill and independent read-only evidence verification.

## Current status

```text
Phase 0 — AWS Foundation:                    COMPLETE
Phase 1 — EPSS Vertical Slice:               COMPLETE
Phase 2.1 — CISA KEV Bronze:                 COMPLETE
Phase 2.2 — CISA KEV Silver/Analytics:       COMPLETE
Phase 2.3 — NVD/CVE deterministic path:      COMPLETE
Phase 2.4 — GitHub Security Advisories:      COMPLETE
Phase 2.5 — Historical EPSS expansion:       COMPLETE
Phase 2 — Threat Intelligence Data Lake:     COMPLETE
Phase 3 — Vulnerability Correlation Engine:  NOT STARTED
```

Phase 3 is unblocked by Phase 2 completion, but no Phase 3 implementation is part of this checkpoint.

## Repository checkpoint

```text
main commit: 9c00a7e7fa373878a06df431d41a9c538ed48624
PR:          #59 — feat(epss): add read-only post-backfill evidence verifier
status:      merged
```

## Historical EPSS frozen authority

```text
archive repository:          empiricalsec/epss_scores
archive commit:              7ba701f5599057c496489ceecd701cbd43911f5c
first forward snapshot date: 2026-08-14
historical interval:         2021-04-14 .. 2026-08-13
candidate snapshots:         1,939
candidate compressed bytes:  2,537,138,865
plan_id:                     3b3c8c58009f46b61f6bb9e82f6b6c0bcf675e72b940326d7fcccf962d7bd4de
source-absent dates:         9
execution order:             snapshot_date ascending
coordinator concurrency:     1
```

The nine source-absent dates remain explicit evidence and were not fabricated or backfilled from another source.

## Historical EPSS storage contract

Historical Bronze is isolated by archive commit:

```text
bronze/epss-history/schema_version=1/
  archive_commit=<commit>/
    snapshot_date=YYYY-MM-DD/
      epss_scores.csv.gz
      manifest.json
```

Historical Silver deliberately reuses the canonical EPSS Silver namespace:

```text
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

Completion evidence is separate and written last:

```text
silver/epss-history/completions/schema_version=1/
  archive_commit=<commit>/
    snapshot_date=YYYY-MM-DD/
      manifest.json
```

The historical path preserves exact source bytes, Git blob SHA-1, source SHA-256, S3 VersionIds, model-era semantics, nullable legacy fields, deterministic Parquet bytes, and deterministic completion evidence.

## Full-backfill execution evidence

The final authorized execution completed successfully:

```text
workflow: EPSS History Backfill
run:      33554269746
result:   SUCCESS
scope:    all 1,939 frozen snapshots
```

The run replay-verified previously materialized snapshots and continued through the remaining work without deleting, skipping, or overwriting historical evidence.

## Post-backfill evidence verification

A dedicated read-only role and workflow independently verified the completed historical dataset:

```text
role:     OpsLensEpssHistoryEvidenceRole
workflow: EPSS History Evidence
run:      33626865216
job:      100236560359
commit:   9c00a7e7fa373878a06df431d41a9c538ed48624
result:   PASS
```

Final verifier summary:

```text
expected_snapshots                1939
bronze_sources                    1939
bronze_manifests                  1939
silver_objects                    1939
completion_manifests              1939
missing_expected                  0
unexpected_historical             0
provenance_failures               0
hash_failures                     0
version_authority_failures        0
completion_authority_failures     0
source_absent_dates_checked       9
source_absent_artifacts_found     0
boundary_violations               0
canary_dates_checked              7
canary_divergent_versions         0
era_v1                            289
era_v2                            395
era_v3                            740
era_v4                            455
era_v5                            60
result                            PASS
```

The verifier reconstructed deterministic Silver and completion artifacts from exact Bronze evidence and compared persisted authority rather than relying on object counts alone.

## Remediation history captured by the closeout

The full-backfill sequence intentionally failed closed and was remediated incrementally:

- run `33524129175` exposed completion replay nondeterminism before progress was committed; PR #56 canonicalized completion replay bytes;
- run `33528440534` progressed through 911/1,939 snapshots and then failed on expired STS credentials; PR #57 extended the coordinator role and workflow session to six hours;
- Terraform run `33543213744` then exposed missing bounded `iam:UpdateRole` authority on the deployment role; PR #58 added only that action for the exact coordinator role and the bootstrap stack was applied and converged;
- Terraform dev apply `33551616414` updated the coordinator session duration and `33551963887` proved convergence;
- plan-only run `33552924199` reproduced the exact frozen plan before the final write retry;
- run `33554269746` completed the full 1,939-snapshot execution;
- PR #59 added the independent read-only evidence verifier and dedicated evidence role;
- run `33626865216` returned the final comprehensive `PASS`.

## AWS and security state

The project still uses one real `dev` environment in account `487757851499`, primarily in `us-east-1`.

Human administration uses IAM Identity Center temporary credentials. GitHub Actions uses OIDC. The historical EPSS responsibilities are separated:

```text
OpsLensEpssHistoryCoordinatorRole
    bounded full-backfill coordination and writes

OpsLensEpssHistoryEvidenceRole
    read-only S3 listing/version listing/object reads
    no PutObject
    no DeleteObject
    no Lambda invoke
```

The evidence actor cannot repair the data it audits.

## Next boundary

The next roadmap milestone is Phase 3 — Vulnerability Correlation Engine.

Phase 3 must remain deterministic for package identity normalization, version-range matching, vulnerability applicability, alias handling, and emitted match evidence. No LLM decides whether a package version is vulnerable.
