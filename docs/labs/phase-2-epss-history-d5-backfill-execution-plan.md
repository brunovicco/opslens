# Phase 2.5D-5 — Historical EPSS Backfill Execution Plan

Status: **PLAN ONLY — execution not authorized**

## Purpose

Define the controlled execution gate for the full historical EPSS bootstrap after the seven-snapshot canary completed successfully and its persisted evidence was verified by exact S3 VersionId and SHA-256.

This document does **not** authorize or trigger the historical backfill.

## Frozen authority

The backfill must reuse the same deterministic authority already validated by the canary:

- archive repository: `empiricalsec/epss_scores`
- archive commit: `7ba701f5599057c496489ceecd701cbd43911f5c`
- root tree SHA: `2a12b2030cda9b94573bca01b67a6f0d72ab71e8`
- first forward snapshot date: `2026-08-14`
- historical eligibility: `snapshot_date < 2026-08-14`
- candidate interval: `2021-04-14` through `2026-08-13`
- candidate count: `1,939`
- candidate compressed bytes: `2,537,138,865`
- plan id: `3b3c8c58009f46b61f6bb9e82f6b6c0bcf675e72b940326d7fcccf962d7bd4de`

If fresh environment evidence produces a different forward boundary, candidate set, candidate byte total, pinned Git inventory, or plan id, execution must fail closed and a new plan must be reviewed before any historical mutation.

## Source absences

The following nine calendar dates are intentionally absent from the pinned upstream archive and are not executable work items:

- `2021-04-22`
- `2021-04-23`
- `2021-04-24`
- `2021-04-25`
- `2021-04-26`
- `2021-06-07`
- `2021-06-18`
- `2022-07-14`
- `2024-12-01`

They must remain explicit provenance evidence and must never be synthesized.

## Canary evidence already closed

The frozen seven-snapshot canary completed successfully for:

1. `2021-04-14`
2. `2022-02-03`
3. `2022-02-04`
4. `2023-03-07`
5. `2025-03-17`
6. `2026-06-15`
7. `2026-08-13`

The execution processed exactly seven snapshots under the frozen plan id. The resulting seven Silver objects and seven completion manifests were subsequently read by their exact S3 VersionIds and all fourteen SHA-256 checks matched:

```text
checked_objects=14
failures=0
EPSS_HISTORY_CANARY_EVIDENCE=PASS
```

These seven snapshots are therefore already materialized historical state. The full backfill must treat them as replay candidates and must verify/reuse them rather than overwrite them.

## Required object contracts

Historical Bronze source and manifest:

```text
bronze/epss-history/schema_version=1/archive_commit=<archive_commit>/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
bronze/epss-history/schema_version=1/archive_commit=<archive_commit>/snapshot_date=YYYY-MM-DD/manifest.json
```

Historical Silver:

```text
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

Historical completion marker:

```text
silver/epss-history/completions/schema_version=1/archive_commit=<archive_commit>/snapshot_date=YYYY-MM-DD/manifest.json
```

The completion manifest is written last and is the durable signal that one historical snapshot finished successfully.

## Mutation rules

For every candidate snapshot, execution must remain fail closed:

1. Fetch the exact compressed source bytes from the pinned Git coordinate.
2. Verify compressed byte length against pinned Git metadata.
3. Verify Git blob SHA-1 from the exact source bytes.
4. Parse using the historical EPSS compatibility contract and verify model era.
5. Publish Bronze source create-only using `If-None-Match: *`.
6. On an existing Bronze key, read the exact current VersionId and verify exact bytes before reuse.
7. Publish the Bronze manifest create-only and preserve its exact VersionId.
8. Invoke the dedicated transformer synchronously using only `bronze_manifest_key + bronze_manifest_version_id` as authority.
9. Persist Silver create-only. If the deterministic Silver key already exists, verify the current version's bytes and SHA-256 exactly before treating it as replay.
10. Persist completion create-only only after Silver success. Existing completion state must be exact-replay verified before reuse.
11. Record returned VersionIds, SHA-256 values, request id, replay status, snapshot date, plan id, and run id as execution evidence.

A mismatch at any replay boundary is a hard failure. The executor must not repair, delete, replace, or silently advance past conflicting state.

## Ordering and concurrency

Initial full-backfill authorization must use deterministic ascending snapshot order and coordinator concurrency `1`.

Rationale:

- the seven-snapshot canary already validated sequential behavior;
- sequential execution minimizes blast radius during the first full historical run;
- replay-safe object contracts provide resume behavior without requiring parallel workers;
- a failure leaves a precise last-completed snapshot and does not create an ambiguous fan-out of partially completed work.

Increasing concurrency is outside this gate and requires a separate explicit decision supported by new evidence.

## Resume behavior

A full run may be restarted after a failure, but restart is not equivalent to blind continuation.

On every invocation the coordinator must:

1. rediscover the fresh forward boundary;
2. rebuild the full plan from the pinned Git inventory;
3. require the exact frozen plan id before mutation;
4. iterate all 1,939 work items in deterministic order;
5. rely on exact replay verification for already completed snapshots;
6. continue only when prior Bronze, Silver, and completion evidence is byte-identical to the deterministic expected state.

This deliberately avoids maintaining a mutable external cursor as execution authority. Persisted deterministic object evidence is the resume authority.

## Progress evidence

The executor should emit machine-readable progress after each completed work item with at least:

- `plan_id`
- `run_id`
- `snapshot_date`
- ordinal position and total candidate count
- source SHA-256
- Bronze manifest key and VersionId
- Lambda request id
- Silver key, VersionId, SHA-256, and replay status
- completion key, VersionId, SHA-256, and replay status

The final result must include:

- `processed_snapshots = 1939`
- `failed_snapshots = 0`
- unchanged `first_forward_snapshot_date = 2026-08-14`
- unchanged frozen `plan_id`
- a unique run id for that execution attempt.

## Failure policy

Execution stops on the first failed work item.

Do not automatically retry the entire workflow after:

- source identity mismatch;
- boundary or plan-id drift;
- Bronze replay mismatch;
- transformer `FunctionError`;
- Silver replay mismatch;
- completion replay mismatch;
- unexpected AWS authorization failure;
- malformed transformer evidence.

Transient network/provider reads may use only the existing bounded retry behavior. Semantic or persistence conflicts must not be retried as transient failures.

## Cost and runtime guardrails

The authorized candidate source volume is exactly `2,537,138,865` compressed bytes under the frozen plan.

The full run must not accept an arbitrary date list, arbitrary archive commit, arbitrary function name, arbitrary bucket, or unbounded concurrency from workflow inputs.

The workflow should expose only:

- plan-only as the default mode;
- a boolean execute switch;
- one exact high-friction execution confirmation token.

The confirmation token for the full backfill must be distinct from `EPSS-HISTORY-CANARY-7` and must be reviewed before the execution workflow is merged or invoked.

## Implementation gate

Before full execution is authorized, repository implementation must provide:

- a dedicated full-backfill coordinator path reusing the existing deterministic plan/source/Bronze/transformer contracts;
- a plan-only default that reports the exact frozen candidate count, bytes, boundary, source absences, and plan id without historical mutation;
- exact execution confirmation distinct from the canary token;
- sequential execution only;
- explicit per-item progress evidence;
- exact replay behavior for the seven already materialized canary snapshots;
- tests proving boundary drift fails closed;
- tests proving the full executor cannot accept arbitrary subsets or concurrency;
- tests proving first-error stop behavior;
- tests proving completed items can be replay-verified during a resumed attempt.

## Authorization gates

The remaining sequence is intentionally split:

1. **D5-A — implementation:** implement the full-backfill coordinator/workflow and tests. No AWS historical writes.
2. **D5-B — plan-only validation:** merge the implementation, run the new workflow in default plan-only mode, and compare its output to this frozen authority. No AWS historical writes.
3. **D5-C — explicit execution authorization:** only after D5-B passes may the operator explicitly authorize the full backfill.
4. **D5-D — full execution:** process the 1,939 deterministic work items with concurrency 1 and fail on first error.
5. **D5-E — post-run evidence:** verify completion coverage and selected exact-version/SHA evidence before Phase 2.5 can close.

Phase 3 remains blocked until the full historical EPSS backfill and its evidence gate are complete.

## Current decision

**D5 planning is complete when this document is reviewed and merged. Full backfill execution remains unauthorized.**
