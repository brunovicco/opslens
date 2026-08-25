# Phase 2.3F — NVD Authoritative Runtime Closeout

## Objective

Phase 2.3F operationalizes the NVD incremental CVE API runtime and proves that the authoritative watermark advances only after exact Bronze and deterministic Silver evidence exist.

The authority states remain distinct:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
```

The incremental runtime never writes the authoritative watermark. Promotion is the only component allowed to advance authority, and it does so only after verifying exact persisted evidence.

## Final deployed chain

```text
EventBridge Scheduler
    |
    v
NVD Incremental Lambda
    |
    +--> authoritative watermark read
    +--> closed lastModified window
    +--> NVD CVE API 2.0 pagination
    +--> 500 records/page
    +--> 6-second request pacing
    +--> immutable Bronze page writes
    +--> Bronze COMPLETE written last
    |
    v
S3 ObjectCreated
    |
    v
NVD Silver Lambda
    |
    +--> exact Bronze COMPLETE VersionId
    +--> exact Bronze page VersionIds
    +--> deterministic transformation
    +--> Parquet
    +--> Silver COMPLETE written last
    |
    v
S3 ObjectCreated
    |
    v
NVD Promotion Lambda
    |
    +--> exact Silver COMPLETE VersionId
    +--> exact Silver Parquet VersionId
    +--> current authoritative watermark
    +--> conditional monotonic promotion
    |
    v
control/nvd/cve/incremental/watermark.json
```

## Runtime discoveries

### Scheduler context attribute

The first enabled unattended execution at `2026-08-25T21:25:00Z` reached the Incremental Lambda but failed at invocation parsing because Terraform `jsonencode` escaped the EventBridge Scheduler context attribute.

The fix preserves structured JSON generation while restoring only the angle brackets required for the literal Scheduler token:

```text
<aws.scheduler.scheduled-time>
```

A Terraform check prevents regression to the escaped representation.

### NVD response-size boundary

The next unattended execution at `2026-08-25T22:25:00Z` proved context substitution but failed closed before Bronze persistence because the NVD default page exceeded the local 16 MiB defensive response limit.

The exact failing window was measured independently:

```text
window start:             2026-08-18T08:20:12Z
window end:               2026-08-25T22:25:00Z
totalResults:             6724
resultsPerPage=500:       4,202,454 bytes for page 0
pages at 500 records:     14
minimum pacing floor:     78 seconds
Lambda timeout:           300 seconds
response byte cap:        16,777,216 bytes
```

The runtime now explicitly configures:

```text
NVD_CVE_API_RESULTS_PER_PAGE=500
NVD_CVE_API_MAX_RESPONSE_BYTES=16777216
NVD_CVE_API_MINIMUM_INTERVAL_SECONDS=6
NVD_CVE_API_MAX_ATTEMPTS=3
```

The byte cap, timeout, and memory were not increased to mask the source-page problem.

### Stable Scheduler IAM identity

The first bounded-page Terraform plan exposed a non-semantic Scheduler IAM rewrite because the policy referenced the Lambda resource ARN directly and Terraform marked that value unknown during the Lambda update.

The allowed Lambda ARN is now derived from stable region/account/function-name inputs. The Scheduler target still references the real Lambda resource. The corrected bounded-page deployment plan updated only:

```text
aws_lambda_function.nvd_incremental
```

### Maintenance cadence

The enabled runtime was initially hourly for operational proof. After the successful end-to-end execution, the schedule was aligned to the NVD maintenance recommendation of no more than one automated maintenance request every two hours.

The deployed expression is:

```text
cron(25 1/2 * * ? *)
```

The existing physical schedule name is retained to avoid replacement:

```text
opslens-dev-nvd-incremental-hourly
```

A Terraform cadence check prevents accidental regression to a more frequent schedule.

## Positive unattended end-to-end proof

The Scheduler execution for `2026-08-25T23:25:00Z` completed the complete authoritative chain without manual invocation.

### Incremental

```text
target_end_at:            2026-08-25T23:25:00Z
prior authority:          2026-08-18T08:20:12Z
results_per_page:         500
API requests:             14
HTTP result:              14 x 200
source attempt:           1 for every page
total_results:            6749
update_id:                65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e
Bronze COMPLETE VersionId: b9eVXEobSlusbDghQAptQKQM8rKnRrBK
Bronze COMPLETE SHA-256:   d30f218690edcb2aa436561acc79045ea5471c0e356fc511e4c526415095baf9
duration:                  80.222 s
billed duration:           81.197 s
memory configured:         1024 MiB
max memory used:           184 MiB
```

All fourteen immutable Bronze response objects were persisted before the canonical COMPLETE manifest.

### Silver

Silver consumed the exact Bronze COMPLETE version and every exact Bronze page version referenced by it.

```text
rows:                      6749
Parquet bytes:             4,724,916
Parquet SHA-256:           d95c409ef20d787632f45419a436855d0cd3d543704fe5b189af32025ad2fac8
Parquet VersionId:         f.L5xLSzp1eabl4R9VA8ebt6ReWEp9cm
Silver COMPLETE VersionId: 0lrrflijjrZvIqgxr1aqcA08fjQ589G7
Silver COMPLETE SHA-256:   e144fc21847acd500b74eed4855dfcc361e540c49673cb70e5e3d0a652d37ae9
duration:                  7.652 s
billed duration:           8.807 s
memory configured:         3008 MiB
max memory used:           603 MiB
```

The cardinality invariant held:

```text
Silver row_count == verified Bronze total_results == 6749
```

### Promotion

Promotion consumed the exact Silver COMPLETE and Parquet versions and loaded the previous authoritative watermark before committing.

```text
prior watermark VersionId: Kz1WxsZYIup2V_FEKbXhExCEoKxgpbqf
new watermark VersionId:   S8GnyKJhDlfvmsWs3gbl9Zg8JWnQio2o
new watermark ETag:        "59f6abee97a4f41ea7148706e3f32c7e"
status:                     committed
committed_through_at:       2026-08-25T23:25:00Z
duration:                   0.518 s
billed duration:            1.839 s
memory configured:          1024 MiB
max memory used:            148 MiB
```

Watermark bytes changed only after successful promotion:

```text
before SHA-256: 0f7bcdb409b7f78d9fcac2b2d3fc14b1eb9a6feb098c103e42194740d6ce4c6b
after SHA-256:  51385b65b18a45fa7b5d3e783bd192065381344ba9bef24c074d3d1787b8c348
```

The final authority boundary exactly equals the Scheduler-supplied target boundary.

## Trace continuity

The same X-Ray root trace propagated across all three runtime stages:

```text
1-6a8e2473-5030216076c8845c2e81383c
```

Observed sequence:

```text
Incremental start: 23:25:40Z
Bronze COMPLETE:   23:27:00Z
Silver COMPLETE:   23:27:11Z
Watermark commit:  23:27:15Z
```

The complete chain therefore reached committed authority in approximately 95 seconds from the Incremental start.

## Runtime and cost observations

The successful proof consumed approximately:

```text
Incremental: 81.197 GB-s
Silver:      ~25.88 GB-s
Promotion:    1.839 GB-s
Total:       ~108.92 GB-s
```

These figures use billed duration multiplied by configured Lambda memory. They are recorded as workload evidence rather than as a final right-sizing recommendation.

The successful backlog window used only 184 MiB of the Incremental Lambda's 1024 MiB allocation. Silver used 603 MiB of 3008 MiB. Promotion used 148 MiB of 1024 MiB. No memory increase is justified by this proof.

## Failure and replay properties proven

Phase 2.3F validated the following behaviors in real AWS:

- malformed Scheduler context fails before source processing;
- source responses exceeding the defensive byte cap fail before Bronze persistence;
- failed Incremental paths do not trigger Silver or Promotion;
- failed paths do not advance authoritative state;
- Scheduler retries are bounded;
- exact NVD source observations have physical `attempt_id` identity independent of logical `update_id`;
- source-byte volatility for the same logical window does not collapse physical evidence identity;
- canonical COMPLETE races require verification of winning immutable evidence;
- Silver reads exact Bronze object versions rather than unversioned latest objects;
- Promotion reads exact Silver evidence versions;
- only Promotion can advance the authoritative watermark;
- successful promotion is monotonic and bound to exact persisted evidence.

## Terraform closeout

The bounded-page deployment was validated with:

```text
0 add / 1 change / 0 destroy
only aws_lambda_function.nvd_incremental updated
```

The cadence deployment was validated with:

```text
0 add / 1 change / 0 destroy
only aws_scheduler_schedule.nvd_incremental_hourly updated
```

Post-apply Terraform convergence returned no changes.

Terraform CI was green for both the bounded-page/runtime stabilization and cadence changes.

## Phase 2.3F result

Phase 2.3F is complete.

The final proven invariant is:

```text
Scheduler
 -> Incremental
 -> Bronze COMPLETE
 -> Silver COMPLETE
 -> Promotion
 -> authoritative watermark committed
```

with:

```text
bronze_complete != silver_complete != watermark_committed
```

NVD Glue/Athena analytics remain intentionally outside this phase and belong to the next NVD increment.
