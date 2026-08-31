# Phase 2.5D-1 — Historical EPSS Bootstrap Runtime Decision and Bounded Execution Contract

Status: **COMPLETE — runtime and bounded execution contract frozen; 2.5D-2 NEXT**

## Purpose

Phase 2.5D-1 selects the smallest justified execution model for historical EPSS bootstrap before any historical AWS mutation.

This gate turns the already-implemented one-snapshot evidence path from Phase 2.5C into an operationally bounded backfill plan. It does not perform the backfill.

The governing invariant remains:

> **Agents reason. Code verifies evidence.**

The operational consequence is equally important:

> **The coordinator schedules work. Exact evidence determines whether a snapshot is acceptable.**

## Inputs already proven

Phase 2.5A-C established the following immutable inputs:

```text
historical repository: empiricalsec/epss_scores
archive commit:         7ba701f5599057c496489ceecd701cbd43911f5c
root tree:              2a12b2030cda9b94573bca01b67a6f0d72ab71e8
archive start:          2021-04-14
archive pin end:        2026-08-30
available snapshots:    1,956
source-missing dates:   9
compressed bytes:       2,580,729,807
```

The nine source absences remain absences and are never synthesized:

```text
2021-04-22
2021-04-23
2021-04-24
2021-04-25
2021-04-26
2021-06-07
2021-06-18
2022-07-14
2024-12-01
```

The one-snapshot historical transformation contract is already implemented:

```text
explicit invocation
  -> exact Bronze manifest VersionId
  -> exact Bronze source VersionId
  -> source SHA-256 + Git blob identity validation
  -> historical parser
  -> deterministic Silver v2 Parquet
  -> create-only / exact-replay-verified Silver
  -> completion evidence written last
```

No implicit S3 fan-out is permitted.

## Current dev forward-authority evidence

The latest real `dev` evidence already recorded by the Phase 2.5C design identifies the earliest canonical forward snapshot as:

```text
first_forward_snapshot_date = 2026-08-15
```

This value is **environment evidence**, not a product constant.

Therefore the current D1 planning boundary is:

```text
historical eligible date < 2026-08-15
```

and the current candidate interval is:

```text
2021-04-14 .. 2026-08-14
```

D1 does not hard-code `2026-08-15` into domain code. Before the first D2 mutating execution, the coordinator must rediscover the earliest forward snapshot read-only from the target environment. If the observed boundary differs, the worklist and `plan_id` must be regenerated before any historical write.

This is a fail-closed precondition.

## Deterministic candidate workload

Using the pinned archive inventory and the currently evidenced dev boundary:

```text
calendar dates in candidate interval: 1,949
source absences in candidate interval:     9
available candidate snapshots:         1,940
candidate compressed source bytes:     2,539,677,859
candidate compressed MiB:              ~2,422.03
```

Candidate snapshots by model era:

| Era | Candidate snapshots |
| --- | ---: |
| v1 | 289 |
| v2 | 395 |
| v3 | 740 |
| v4 | 455 |
| v5 | 61 |
| **Total** | **1,940** |

The 16 archive snapshots from `2026-08-15` through `2026-08-30` are excluded from the current dev historical plan because they are on or after the forward-authority boundary.

## Worklist contract

The bootstrap worklist is generated from the immutable Git tree, never from a moving repository branch.

Each available work item binds at least:

```text
snapshot_date
archive_repository
archive_commit
archive_path
archive_git_blob_sha1
compressed_size_bytes
model_era
```

The worklist generator must:

1. read the pinned root tree and the six pinned year trees;
2. validate canonical `YYYY/epss_scores-YYYY-MM-DD.csv.gz` coordinates;
3. preserve missing calendar dates as explicit source absences, not work items;
4. exclude every date on or after the freshly discovered forward boundary;
5. sort work items by `snapshot_date` ascending;
6. serialize the resulting plan canonically before execution.

The full inventory requires eight GitHub metadata GETs: one root tree, six year trees and the immutable commit/root coordinate already known by the plan. Per-snapshot GitHub API metadata calls are not required.

## Plan identity versus execution identity

D1 distinguishes the immutable work plan from an individual attempt to execute it.

### `plan_id`

`plan_id` is deterministic:

```text
plan_id = SHA-256(canonical plan bytes)
```

The canonical plan binds at least:

```text
schema_version
archive_repository
archive_commit
root_tree_sha
first_forward_snapshot_date
candidate_count
candidate_compressed_bytes
ordered work items
source-absence coordinates
```

The same source pin + same target boundary + same worklist must produce the same `plan_id`.

### `run_id`

`run_id` identifies one operational attempt and is intentionally unique.

A retry of the same plan therefore has:

```text
same plan_id
new run_id
```

This allows audit records to distinguish deterministic scope from execution history.

## Runtime options considered

### Option A — operator/CLI performs acquisition and transformation

Advantages:

- no new AWS compute resource;
- simplest infrastructure count;
- straightforward sequential execution.

Rejected for transformation because it would require a long-lived operator identity with direct Silver/completion write authority, mix archive acquisition and transformation privileges, move all PyArrow compute to the operator host, and weaken centralized AWS runtime telemetry.

The operator remains useful as a bounded **coordinator**.

### Option B — dedicated historical Lambda

Advantages:

- maps directly to the existing strict one-snapshot invocation contract;
- naturally bounded per snapshot;
- no server lifecycle;
- centralized logs/metrics/request identity;
- IAM can be narrower than the coordinator identity;
- existing OpsLens EPSS Silver packaging already supports PyArrow;
- representative modern snapshots completed parse + Silver serialization in under ten seconds during Phase 2.5B.

AWS Lambda permits up to 900 seconds per invocation and up to 10,240 MB memory, leaving substantial room above the measured individual-snapshot workload.

Selected for the transformation boundary.

### Option C — ECS/Fargate task

Technically viable, including for multi-hour bootstrap coordination, but not justified by the current individual-snapshot workload. It adds task definition, image/runtime lifecycle and network/container operational surface without solving a demonstrated Lambda constraint.

Keep as a fallback if real AWS canary evidence invalidates the Lambda envelope.

### Option D — AWS Batch

AWS Batch itself has no additional service fee, but still requires an underlying compute environment/job definition and adds scheduling infrastructure. The current workload does not require queue prioritization, heterogeneous fleets or large batch-compute provisioning.

Do not introduce Batch solely because the workload is called a backfill.

### Option E — Step Functions

Not selected. C5 already provides deterministic one-snapshot composition and D1 requires only bounded operator-driven sequencing/resume. A state machine would add orchestration state and transitions before a durable coordination need has been demonstrated.

## Runtime decision

D1 selects a **hybrid bounded operator coordinator + dedicated historical transformer Lambda**.

```text
operator bootstrap coordinator
  |
  |-- discover forward boundary read-only
  |-- build immutable worklist from pinned Git tree
  |-- fetch exact archive bytes
  |-- verify Git blob SHA-1 + SHA-256
  |-- create exact Bronze source + Bronze manifest
  |-- invoke one historical transformation synchronously
  |-- record result/checkpoint
  v
historical transformer Lambda
  |
  |-- exact Bronze VersionId reads
  |-- parse/transform deterministic Silver
  |-- create or exact-replay-verify Silver
  |-- write completion evidence last
  v
return exact result to coordinator
```

The Lambda is invoked synchronously (`RequestResponse`) by the coordinator. D1 does not authorize asynchronous bulk invocation, S3-triggered history transformation, or fire-and-forget fan-out.

## Proposed Lambda envelope for the canary

Initial bounded configuration for the historical transformer:

```text
memory:                1024 MB
timeout:               120 seconds
reserved concurrency: 2
invocation mode:       synchronous RequestResponse
one invocation:        exactly one historical snapshot
```

The 120-second timeout is a safety envelope, not an expected duration. Lambda duration is billed for actual execution time.

The first D2 execution slice must still use **coordinator concurrency 1**, regardless of the reserved concurrency ceiling. Concurrency may increase to at most 2 only after the seven-snapshot canary is reviewed.

No evidence currently justifies concurrency above 2.

## Full-bootstrap bounded execution contract

If the canary later authorizes continuation, the default D1 full-plan limits are:

```text
logical batch size:       25 snapshots
maximum concurrency:       2 snapshots
per-snapshot authority:    exact one-snapshot invocation
ordering:                  ascending snapshot_date within submitted work
checkpoint frequency:      after every completed snapshot
batch boundary summary:    after each group of 25
```

The batch size is a coordinator/checkpoint boundary, not a Lambda payload containing 25 snapshots.

A Lambda invocation always handles exactly one snapshot.

## Source acquisition contract

The coordinator owns source acquisition. The transformation Lambda does not call GitHub.

For each work item, the coordinator must fetch bytes from the **commit-pinned archive coordinate**, never from mutable `main`, then verify before Bronze acceptance:

```text
Git blob identity = SHA1("blob " + byte_length + NUL + raw_bytes)
computed blob SHA1 == worklist archive_git_blob_sha1
SHA-256(raw_bytes) == Bronze source identity
byte length == pinned tree compressed_size_bytes
```

Only exact verified bytes may become a historical Bronze source object.

No code from the third-party archive repository is executed. The archive is treated only as immutable data bytes and Git metadata.

## GitHub request and retry budget

The worklist requires only a small fixed metadata request budget. Source byte retrieval should use immutable commit-pinned raw/content coordinates and avoid a metadata API call per file when it is unnecessary.

GitHub currently documents primary REST limits of 60 requests/hour for unauthenticated public requests, 5,000/hour for authenticated user requests and 1,000/hour/repository for a standard Actions `GITHUB_TOKEN`.

The coordinator must observe response rate-limit headers. On `403`/`429`:

```text
Retry-After present
  -> wait exactly that period before retry

x-ratelimit-remaining == 0
  -> wait until x-ratelimit-reset

secondary limit without explicit delay
  -> wait at least one minute
  -> exponential increase on repeated failure
  -> stop after bounded attempts
```

Source acquisition should be serial or low-concurrency. There is no benefit in stressing GitHub to make Lambda concurrency higher.

## Retry classification

### Deterministic failures — no automatic retry

Examples:

```text
invalid archive path/date
unknown model-era coordinate
unexpected legacy/modern header
modern metadata/date mismatch
Git blob SHA-1 mismatch
source SHA-256 mismatch
source size mismatch
Bronze VersionId mismatch
Silver replay byte/hash mismatch
completion replay byte/hash mismatch
forward-authority overlap
```

These fail closed and require investigation or a new plan/code revision.

### Retryable operational failures — bounded retry

Examples:

```text
GitHub rate limit / transient 5xx / network timeout
AWS API throttling
transient AWS 5xx
synchronous Lambda transport error
```

Default operational retry limit:

```text
maximum attempts per snapshot per run: 3
backoff: exponential + jitter
```

Rate-limit responses always honor provider-specified delay first.

HTTP/S3 `409` concurrent-create conditions remain distinct conflicts and are not silently classified as successful replay.

## Resume and replay semantics

Completion manifests are the authoritative persisted evidence that a historical transformation completed.

The coordinator may maintain a mutable local/run checkpoint for efficiency, but that checkpoint is not the evidence authority.

If a coordinator process stops:

```text
restart same plan
  -> use same plan_id
  -> new run_id
  -> skip items proven completed by trusted run/checkpoint evidence when available
  -> otherwise safely resubmit one-snapshot work
```

Resubmission is safe because historical Bronze, Silver and completion writes are create-only and existing deterministic keys are accepted only after exact replay verification.

Loss of a local checkpoint therefore causes extra reads/replay verification, not silent overwrites.

## IAM separation

The coordinator and transformer must not share a convenience super-role.

### Coordinator authority

Required logical capabilities:

```text
read forward EPSS key metadata needed to discover earliest forward authority
create historical Bronze source objects
create historical Bronze manifests
read exact historical Bronze objects only when required for create/replay verification
invoke the dedicated historical transformer Lambda synchronously
write bounded bootstrap run evidence/checkpoints if that prefix is implemented
```

The coordinator must not have:

```text
Silver EPSS write authority
completion-manifest write authority
delete permission on Bronze/Silver history
permission to alter the forward scheduler
```

### Transformer Lambda authority

Required logical capabilities:

```text
s3:GetObjectVersion on bronze/epss-history/*
s3:PutObject on silver/epss/snapshot_date=*/part-00000.parquet
s3:GetObject / s3:GetObjectVersion on the exact Silver namespace for replay proof
s3:PutObject on silver/epss-history/completions/*
s3:GetObject / s3:GetObjectVersion on completion objects for replay proof
CloudWatch Logs / required telemetry
```

The transformer does not require:

```text
GitHub credentials
internet archive acquisition
s3:DeleteObject
broad s3:ListBucket for transformation
access to unrelated Bronze/Silver datasets
```

Exact final IAM resources/actions must be proven in Terraform during D2 before deployment.

## Observability and run evidence

Every bootstrap attempt must make the following reconstructable:

```text
plan_id
run_id
archive repository
archive commit
root/year tree identities
freshly discovered first_forward_snapshot_date
candidate snapshot count
candidate compressed bytes
start/end timestamps
attempted snapshots
created snapshots
replay-verified snapshots
source-absent dates
forward-skipped dates
failed snapshots
failure category and snapshot date
retry count
Lambda request identity / duration where available
exact Silver VersionId + SHA-256
exact completion VersionId + SHA-256
```

A future run-evidence prefix may use a separate namespace such as:

```text
silver/epss-history/runs/
  plan_id=<sha256>/
    run_id=<unique-id>/
      summary.json
```

If implemented, this is operational audit evidence, not a replacement for per-snapshot completion manifests.

## Cost envelope

D1 uses a deliberately conservative estimate before AWS mutation.

### Lambda

For the current 1,940-snapshot dev candidate set at 1 GB memory:

| Average billed duration | GB-seconds | Approx. compute charge before free tier |
| ---: | ---: | ---: |
| 15 s | 29,100 | ~$0.49 |
| 20 s | 38,800 | ~$0.65 |
| 30 s | 58,200 | ~$0.97 |

At $0.20 per one million requests, 1,940 invocations are materially below one cent before any free-tier effect.

D1 therefore sets this compute guardrail:

```text
full-run Lambda expectation: < $1 if observed average duration <= 30 s
```

If the canary indicates a materially larger envelope, the full plan is not authorized without revisiting D1.

### S3 requests

An all-created full run is expected to produce approximately four durable objects per snapshot:

```text
historical Bronze source
historical Bronze manifest
Silver Parquet
completion manifest
```

For 1,940 snapshots that is about 7,760 object writes, plus exact reads used by transformation/replay verification.

Using representative S3 Standard US East (N. Virginia) rates of $0.005/1,000 PUT-class requests and $0.0004/1,000 GET-class requests, request charges remain only a few cents for this workload.

Actual account/region pricing must be rechecked immediately before the full run.

### Storage

Candidate Bronze compressed source bytes are approximately 2.54 GB.

A deliberately conservative Silver upper bound uses the largest representative Phase 2.5B Parquet artifact for every candidate snapshot:

```text
largest representative Parquet: ~5.45 MB
1,940 * ~5.45 MB:               ~10.57 GB
Bronze + conservative Silver:   ~13.1 GB
```

At a representative S3 Standard rate near $0.023/GB-month, this is roughly $0.30/month before small manifest/version overhead. Actual historical Silver storage should be lower because earlier snapshots are much smaller.

### Operational budget guardrail

D1 freezes a deliberately loose guardrail rather than optimizing cents prematurely:

```text
seven-snapshot canary incremental AWS budget: < $1
full historical execution one-time AWS budget: $5
expected ongoing added storage:               < $0.50/month
```

The full-run budget is not an authorization to run. It is a stop condition for later gates.

## Why Lambda rather than Fargate/Batch at this point

The choice is based on measured shape rather than certification coverage.

Representative snapshots require seconds, not hours, of transformation. Lambda already supports the required execution ceiling and the repository already has a PyArrow Silver Lambda packaging pattern.

Fargate is inexpensive but introduces container/task lifecycle without a demonstrated need. AWS Batch adds no Batch service fee, but still requires the underlying compute/job scheduling surface. Neither improves the exact one-snapshot evidence contract enough to justify the additional architecture now.

If the real canary later shows any of the following, D1 must be reopened before scaling:

```text
individual snapshots approach the Lambda timeout envelope
native memory usage materially exceeds the chosen Lambda memory
PyArrow package/runtime constraints become operationally unstable
sustained throughput requires a different compute model
operator coordination becomes unreliable enough to justify durable managed orchestration
```

## Estimated elapsed time

Using the current 1,940-snapshot candidate set:

```text
15 s average, concurrency 2 -> ~4.0 h of transformation wall time
20 s average, concurrency 2 -> ~5.4 h of transformation wall time
```

This excludes GitHub acquisition, retries and coordinator overhead.

A several-hour one-time operator-supervised bootstrap with deterministic resume is acceptable. That duration alone does not justify a new batch platform.

## First authorized execution slice for D2

D1 freezes a **seven-snapshot canary** that covers every known physical/model transition plus the current forward boundary edge:

| Snapshot | Purpose |
| --- | --- |
| `2021-04-14` | earliest archive snapshot; early v1 two-column shape |
| `2022-02-03` | late v1 three-column transition shape |
| `2022-02-04` | first v2 snapshot |
| `2023-03-07` | first v3 snapshot |
| `2025-03-17` | first v4 snapshot |
| `2026-06-15` | first v5 snapshot |
| `2026-08-14` | latest date currently eligible immediately before forward authority |

Known compressed source bytes for this slice total approximately:

```text
9,345,356 bytes
~8.91 MiB
```

The first canary must execute sequentially:

```text
coordinator concurrency = 1
maximum snapshots        = 7
```

If every snapshot is newly created, the slice produces at most:

```text
7 Bronze source objects
7 Bronze manifests
7 Silver Parquet objects
7 completion manifests
--------------------------------
28 snapshot-bound durable objects
```

An optional run summary/checkpoint is separate from that count.

No eighth snapshot is authorized until the canary evidence is reviewed.

## D2 pre-write gates

Before the first historical Bronze write, D2 must prove all of the following:

```text
EPSS_HISTORY_D2_FORWARD_BOUNDARY_REVALIDATED_GATE
EPSS_HISTORY_D2_PLAN_ID_FROZEN_GATE
EPSS_HISTORY_D2_PINNED_WORKLIST_GATE
EPSS_HISTORY_D2_COORDINATOR_IAM_GATE
EPSS_HISTORY_D2_TRANSFORMER_IAM_GATE
EPSS_HISTORY_D2_SYNCHRONOUS_INVOCATION_GATE
EPSS_HISTORY_D2_CONCURRENCY_ONE_GATE
EPSS_HISTORY_D2_SEVEN_SNAPSHOT_LIMIT_GATE
EPSS_HISTORY_D2_OBSERVABILITY_GATE
EPSS_HISTORY_D2_COST_GUARDRAIL_GATE
```

If fresh target-environment discovery does not return `2026-08-15`, the current candidate calculations are informational only: D2 must regenerate the canonical plan and `plan_id` from the newly observed boundary before mutation.

## D1 gates

```text
EPSS_HISTORY_D1_FORWARD_AUTHORITY_EVIDENCE_GATE=PASS
EPSS_HISTORY_D1_PINNED_WORKLIST_CONTRACT_GATE=PASS
EPSS_HISTORY_D1_RUNTIME_COMPARISON_GATE=PASS
EPSS_HISTORY_D1_HYBRID_LAMBDA_DECISION_GATE=PASS
EPSS_HISTORY_D1_BOUNDED_CONCURRENCY_GATE=PASS
EPSS_HISTORY_D1_RETRY_RESUME_GATE=PASS
EPSS_HISTORY_D1_IAM_SEPARATION_GATE=PASS
EPSS_HISTORY_D1_OBSERVABILITY_CONTRACT_GATE=PASS
EPSS_HISTORY_D1_COST_ENVELOPE_GATE=PASS
EPSS_HISTORY_D1_SEVEN_SNAPSHOT_CANARY_GATE=PASS
EPSS_HISTORY_D1_NO_AWS_MUTATION_GATE=PASS
EPSS_2_5D1_GATE=PASS
```

## AWS mutation boundary

D1 is documentation/decision work only.

```text
historical Bronze writes: 0
historical Silver writes: 0
completion writes:         0
new AWS resources:         0
Terraform changes:         0
historical Lambda deploy:  NO
backfill snapshots run:    0
```

## Phase status after D1

```text
Phase 2.5 — IN PROGRESS

2.5A   COMPLETE
2.5B   COMPLETE
2.5C   COMPLETE / CLOSED
2.5D-1 COMPLETE
2.5D-2 NEXT

Phase 3 BLOCKED
```

## Next authorized step

Perform only **2.5D-2 — bounded bootstrap implementation and seven-snapshot canary plumbing**.

D2 may implement the coordinator/runtime/IAM surface required to execute the frozen seven-snapshot canary, but it must revalidate the forward boundary before its first historical write and must not execute more than the seven frozen snapshots.

The full 1,940-snapshot historical plan remains unauthorized until the canary has been executed, reviewed and closed by a later gate.
