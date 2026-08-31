# Phase 2.5C-6 — Historical EPSS Repository Regression and Contract Closeout

Status: **COMPLETE — Phase 2.5C CLOSED; 2.5D-1 NEXT**

## Purpose

Phase 2.5C-6 closes the historical EPSS Bronze/Silver implementation contract after C1-C5.

The goal of this gate is not to add another runtime or begin backfill. It proves that the repository remains coherent after the historical compatibility work, that the deployed forward-daily EPSS surface was not unintentionally widened, that no infrastructure drift or temporary validation workflow remains, and that the next operational gate is explicit.

The governing invariant remains:

> **Agents reason. Code verifies evidence.**

## Scope completed

C6 performed only repository/contract closeout work:

```text
full Python lint regression
full strict Pyright regression
full unit-test regression
repository diff check against main
infrastructure/workflow drift check
forward EPSS runtime-surface check
temporary C6 workflow cleanup
Phase 2.5C status reconciliation
next-gate freeze
```

C6 did **not**:

- ingest historical EPSS snapshots into AWS;
- run a historical backfill;
- create or modify Terraform resources;
- create a Lambda, Step Functions state machine, queue, scheduler, ECS task, Batch job, or other historical runtime;
- change the forward daily EPSS source endpoint;
- change the forward daily Bronze key contract;
- add implicit S3 fan-out for historical data;
- authorize Phase 3.

## Repository baseline and branch relationship

The Phase 2.5 branch remains based on the Phase 2.4 checkpoint:

```text
main: 3b3a3a484b9b456cfaa03501c2e0d4216faa41bc
branch: phase-2-epss-history
relationship after C6 validation cleanup: ahead, 0 behind
```

After removing the temporary C6 workflow, the branch diff contains no `infra/` changes and no `.github/workflows/` changes relative to `main`.

The historical implementation remains isolated to historical EPSS source/domain/application/adapters, historical tests and lab evidence, plus the three intentionally shared Silver compatibility surfaces described below.

## Forward-daily EPSS compatibility review

The forward ingestion path itself remains structurally unchanged:

```text
FIRST current CSV
  -> current EPSS parser
  -> bronze/epss/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
  -> existing S3 ObjectCreated path
  -> existing forward Silver composition
  -> silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

No current EPSS ingestion handler, endpoint configuration, Bronze key factory, S3 event parser, Silver Lambda handler, Silver composition, scheduler, or Terraform definition is changed by Phase 2.5C.

Three shared Silver compatibility surfaces intentionally changed so historical v1 data can coexist in the same analytical relation:

```text
src/opslens/transformation/epss/application/schema.py
  schema metadata version: 1 -> 2
  percentile/model_version/score_timestamp become nullable

src/opslens/transformation/epss/domain/models.py
  the same three fields may be None
  modern non-null validation remains enforced when values are present

src/opslens/transformation/epss/adapters/outbound/parquet.py
  Arrow schema permits those three nullable fields
  None score_timestamp is serialized as NULL
```

For modern forward snapshots, the source parser still requires source metadata and `cve,epss,percentile`; modern transformed records still carry percentile, model version and timezone-aware score timestamp. Existing modern Parquet tests prove those values are preserved through serialization.

Therefore the intentional forward-visible change is the physical Silver schema version/nullability contract, not a change to modern forward source semantics.

## Historical contract now implemented

Phase 2.5C now implements the frozen historical evidence path:

```text
explicit one-snapshot invocation
  -> exact Bronze manifest VersionId
  -> exact Bronze source VersionId
  -> source SHA-256 + Git blob identity validation
  -> legacy/modern historical parser
  -> truthful nullable Silver v2 records
  -> deterministic Parquet bytes
  -> create-only Silver persistence
  -> exact current-VersionId replay verification on 412
  -> completion manifest built from exact Bronze + Silver evidence
  -> create-only completion persistence written last
  -> exact replay verification for completion
```

The historical path remains non-event-driven. Historical S3 source objects are not placed under the deployed `bronze/epss/` notification namespace.

## Legacy evidence semantics

EPSS v1 remains evidence-preserving:

```text
early v1 two-column source
  percentile      = NULL
  model_version   = NULL
  score_timestamp = NULL

late v1 three-column source
  percentile      = exact source value
  model_version   = NULL
  score_timestamp = NULL

v2-v5
  percentile      = exact source value
  model_version   = source-declared
  score_timestamp = source-declared
```

No missing historical value is synthesized merely to satisfy the modern schema.

## C6 validation proof

A temporary branch-only workflow was created solely to validate the closeout and was removed immediately after the successful run.

Final proof:

```text
workflow: Validate EPSS History 2.5C-6
run:      33342711263
commit:   9fe2f9282432d93578565347f065cd8ff8be4a0c
result:   SUCCESS
```

Validation executed:

```text
uv lock --check
uv sync --frozen
uv run ruff check src tests scripts
uv run pyright
uv run pytest -q
```

Observed results:

```text
Ruff full Python surface: PASS
Pyright:                 0 errors, 0 warnings, 0 informations
Full unit regression:    PASS
Infrastructure drift:    NONE (except temporary C6 workflow during the run)
Forward runtime surface: PASS — changes limited to the approved historical and Silver-v2 compatibility files
```

C6 gates:

```text
EPSS_HISTORY_FULL_RUFF_GATE=PASS
EPSS_HISTORY_FULL_PYRIGHT_GATE=PASS
EPSS_HISTORY_FULL_UNIT_REGRESSION_GATE=PASS
EPSS_HISTORY_NO_INFRA_DRIFT_GATE=PASS
EPSS_HISTORY_FORWARD_RUNTIME_SURFACE_GATE=PASS
EPSS_2_5C6_GATE=PASS
```

## Temporary workflow cleanup

The C6 validation workflow was removed after the successful run.

After cleanup, the branch diff against `main` contains no `.github/workflows/` changes and no `infra/` changes.

This preserves the project rule that narrow validation workflows are implementation evidence, not permanent runtime surface unless independently justified.

## Phase 2.5C final status

```text
2.5C-1 — evidence/storage/runtime contract
  COMPLETE

2.5C-2 — legacy-capable source model + parser + Silver schema v2
  COMPLETE

2.5C-3 — exact historical Bronze manifest reader + VersionId boundary
  COMPLETE

2.5C-4 — deterministic Silver persistence + byte-for-byte verified replay
  COMPLETE

2.5C-5 — completion evidence + strict explicit invocation composition
  COMPLETE

2.5C-6 — repository regression and contract closeout
  COMPLETE

Phase 2.5C
  CLOSED
```

The earlier Phase 2.5C design, source-compatibility, C4 and C5 documents remain immutable evidence of the decision sequence at the time each gate was executed. Their embedded `NEXT` status lines are historical checkpoints. **This C6 closeout document is the status authority for the completed Phase 2.5C gate.**

## AWS and cost boundary after C6

```text
historical AWS backfill: 0 snapshots
historical Bronze writes: 0
historical Silver writes: 0
new AWS resources:        0
Terraform changes:        0
new runtime/scheduler:    0
```

The archive inventory remains a batch workload of 1,956 available snapshots and approximately 2.58 GB of compressed source bytes. That workload must be explicitly costed and bounded before execution.

## Next frozen gate — Phase 2.5D-1

The only next authorized step is:

**2.5D-1 — Historical bootstrap runtime decision and bounded execution contract.**

This is a design/measurement gate. It must decide the smallest justified execution model before any historical AWS mutation.

The decision must cover at least:

```text
1. target-environment forward-authority discovery
   - determine the first canonical forward snapshot from real environment evidence
   - derive the historical candidate range without hard-coding 2026-08-15 globally

2. authoritative snapshot worklist
   - pinned archive commit only
   - preserve the nine known archive absences as absences
   - skip every date already under forward authority

3. runtime choice
   - compare bounded operator/CLI execution, Lambda, ECS/Fargate, Batch or another minimal option
   - choose from measured workload and operational needs, not preference

4. bounded execution
   - batch size
   - maximum concurrency
   - continuation/checkpoint semantics
   - retryable vs deterministic failures
   - restart/resume behavior

5. source acquisition
   - exact pinned archive coordinates
   - GitHub/API request budget and retry behavior
   - source byte and Git blob verification before Bronze acceptance

6. least privilege
   - separate acquisition/coordinator authority from transformation authority
   - no delete permission by convenience
   - exact-version reads where required

7. observability and audit
   - run identifier
   - archive commit
   - discovered forward boundary
   - attempted/created/replayed/skipped/failed snapshot counts
   - bounded structured failure evidence

8. cost model
   - source transfer/request volume
   - S3 requests/storage
   - compute duration/concurrency
   - Athena impact only if validation queries are justified
```

2.5D-1 must finish with an explicit runtime recommendation, expected cost envelope, IAM surface, retry/resume contract and a **small first execution slice**.

It must not execute the full historical backfill.

## Phase boundary

```text
Phase 2.5 — IN PROGRESS
Phase 2.5C — COMPLETE / CLOSED
Phase 2.5D-1 — NEXT
Phase 3 — BLOCKED
```

Phase 3 remains blocked until the complete Phase 2.5 historical expansion is implemented, validated and reconciled with the project state documents.
