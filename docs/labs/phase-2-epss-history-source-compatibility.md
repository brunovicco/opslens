# Phase 2.5B — Historical EPSS Representative Source Compatibility

Status: **COMPLETE**

## Purpose

Phase 2.5B tests real immutable EPSS historical source bytes before any AWS backfill design is authorized.

The proof answers:

- whether representative archive files are exact bytes from the pinned Git commit;
- how physical file shape differs across EPSS model eras;
- whether the existing OpsLens parser accepts each era;
- representative compressed/uncompressed size and row count;
- representative current parse + Silver serialization time;
- which metadata is physically source-declared and which information exists only in the archive coordinate.

No AWS state was changed and no third-party repository code was executed.

## Immutable source coordinate

```text
repository: empiricalsec/epss_scores
commit:     7ba701f5599057c496489ceecd701cbd43911f5c
```

The probe selected the first published archive snapshot in each documented model era:

```text
v1 -> 2021-04-14
v2 -> 2022-02-04
v3 -> 2023-03-07
v4 -> 2025-03-17
v5 -> 2026-06-15
```

For each sample, the downloaded raw bytes were checked against the GitHub content API blob SHA by recomputing the Git blob identity. All five exact blob checks passed.

## Real compatibility result

```text
current parser accepted: v2, v3, v4, v5
current parser rejected: v1
```

The v1 rejection is not an incidental parser bug. The physical source contract is different.

### v1 physical shape

Pinned file:

```text
2021/epss_scores-2021-04-14.csv.gz
```

Observed:

```text
metadata comment:              absent
CSV header:                    cve,epss
percentile column:             absent
source-declared model version: absent
source-declared score date:    absent
rows:                          64,712
compressed bytes:              243,932
uncompressed bytes:            1,454,247
```

The current parser rejected it with:

```text
Unexpected EPSS CSV header. Expected 'cve,epss,percentile',
received 'CVE-2020-5902,0.65117'.
```

That message results from the current parser treating the first physical v1 line as a metadata row and the first data row as the expected CSV header.

This proves two separate legacy gaps:

```text
v1 has no FIRST metadata comment
v1 has no percentile field
```

OpsLens must not synthesize either as though it were source-declared evidence.

## v2 physical shape

Pinned file:

```text
2022/epss_scores-2022-02-04.csv.gz
```

Observed:

```text
metadata comment:              present
CSV header:                    cve,epss,percentile
model_version:                 v2022.01.01
score_date:                    2022-02-04T00:00:00+0000
archive/source date match:     true
rows:                          168,325
compressed bytes:              710,931
uncompressed bytes:            5,081,090
current parser:                PASS
current Silver serialization:  PASS
Parquet bytes:                 1,647,803
parse + Silver elapsed:        ~4.10 s
Python tracemalloc peak:        ~40.8 MiB
```

## v3 physical shape

Pinned file:

```text
2023/epss_scores-2023-03-07.csv.gz
```

Observed:

```text
metadata comment:              present
CSV header:                    cve,epss,percentile
model_version:                 v2023.03.01
score_date:                    2023-03-07T00:00:00+0000
archive/source date match:     true
rows:                          196,955
compressed bytes:              1,226,422
uncompressed bytes:            5,880,806
current parser:                PASS
current Silver serialization:  PASS
Parquet bytes:                 2,684,345
parse + Silver elapsed:        ~5.26 s
Python tracemalloc peak:        ~46.4 MiB
```

## v4 physical shape

Pinned file:

```text
2025/epss_scores-2025-03-17.csv.gz
```

Observed:

```text
metadata comment:              present
CSV header:                    cve,epss,percentile
model_version:                 v2025.03.14
score_date:                    2025-03-17T12:55:00Z
archive/source date match:     true
rows:                          270,564
compressed bytes:              1,809,444
uncompressed bytes:            8,185,862
current parser:                PASS
current Silver serialization:  PASS
Parquet bytes:                 4,132,772
parse + Silver elapsed:        ~7.09 s
Python tracemalloc peak:        ~50.8 MiB
```

## v5 physical shape

Pinned file:

```text
2026/epss_scores-2026-06-15.csv.gz
```

Observed:

```text
metadata comment:              present
CSV header:                    cve,epss,percentile
model_version:                 v2026.06.15
score_date:                    2026-06-15T12:03:41Z
archive/source date match:     true
rows:                          340,247
compressed bytes:              2,412,604
uncompressed bytes:            10,318,479
current parser:                PASS
current Silver serialization:  PASS
Parquet bytes:                 5,450,714
parse + Silver elapsed:        ~9.14 s
Python tracemalloc peak:        ~65.8 MiB
```

`tracemalloc` measures Python-managed allocations and does not account for every native allocation inside PyArrow. It is therefore supporting workload evidence, not a Lambda memory proof.

## Source-declared versus coordinate-derived evidence

### v2–v5

The representative files physically declare:

```text
model_version
score_date
```

Their source `score_date` matched the canonical archive date in every tested era.

### v1

The representative v1 file physically declares neither value. Its canonical archive path carries the date coordinate:

```text
2021/epss_scores-2021-04-14.csv.gz
```

The model era is known from the documented FIRST publishing history, but that is external model-era evidence rather than metadata physically present in the source CSV.

Therefore future historical normalization must keep these semantics distinct:

```text
archive snapshot date != fabricated source score timestamp
model era            != fabricated source model_version
```

## Schema implication

The existing EPSS Silver record assumes all rows have:

```text
cve
EPSs
percentile
model_version
score_timestamp
```

The v1 source cannot truthfully satisfy that contract because both `percentile` and source-declared model/timestamp metadata are absent.

Phase 2.5C must therefore make an explicit schema/provenance decision before implementation. Acceptable design work may include nullable historical fields and snapshot-level provenance, but the following are forbidden:

- setting a fake percentile such as `0`, `-1`, or a recalculated modern percentile;
- inventing a source timestamp at midnight solely from the filename;
- claiming a literal source `model_version` was present in v1;
- silently dropping all v1 snapshots while still claiming complete archive coverage.

## Runtime implication

The representative v2–v5 source files all completed the current parser + transformer + Parquet writer in under 10 seconds on the GitHub-hosted runner, with source sizes through ~2.4 MiB compressed / ~10.3 MiB uncompressed and through 340,247 rows.

This supports the hypothesis that the deployed 60-second, 1-GiB Silver Lambda may be sufficient for an **individual** modern historical snapshot.

It does **not** prove the AWS runtime boundary and does **not** authorize a 1,956-object backfill. A real Lambda proof must follow only after the historical schema, exact-version provenance, replay behavior, and orchestration boundary are implemented.

## 2.5B gates

```text
EPSS_HISTORY_PINNED_SAMPLE_BLOB_IDENTITY_GATE=PASS
EPSS_HISTORY_V1_NO_METADATA_GATE=PASS
EPSS_HISTORY_V1_NO_PERCENTILE_GATE=PASS
EPSS_HISTORY_V2_V5_METADATA_GATE=PASS
EPSS_HISTORY_V2_V5_CURRENT_PARSER_GATE=PASS
EPSS_HISTORY_V2_V5_CURRENT_SILVER_SERIALIZATION_GATE=PASS
EPSS_HISTORY_SOURCE_DECLARED_VS_DERIVED_GATE=PASS
EPSS_HISTORY_INDIVIDUAL_WORKLOAD_PLAUSIBILITY_GATE=PASS
EPSS_HISTORY_NO_AWS_MUTATION_GATE=PASS
EPSS_2_5B_GATE=PASS
```

## Next authorized gate

Phase 2.5C must freeze and implement the historical Bronze/Silver evidence contract before any bulk backfill:

1. exact immutable historical source coordinates and Bronze identity;
2. legacy v1 representation without fabricated percentile/metadata;
3. exact S3 `VersionId` reads in Silver;
4. replay verification of existing Silver bytes rather than accepting `412` blindly;
5. coexistence with the forward-daily pipeline;
6. a controlled backfill trigger boundary that cannot fan out 1,956 objects accidentally.
