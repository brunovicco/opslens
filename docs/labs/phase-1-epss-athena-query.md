# Phase 1 Lab — EPSS Athena Query Validation

## Purpose

Validate the deterministic analytical path from the EPSS Silver Parquet
dataset through AWS Glue Data Catalog and Amazon Athena.

The analytical question validated in this lab is:

> Which CVEs have EPSS greater than 0.7 for a specific snapshot?

The snapshot date is intentionally explicit. The `snapshot_date` partition
uses Athena injected partition projection, so consumers must provide the
partition value instead of relying on an implicit "latest" snapshot.

## Analytical resources

- AWS Region: `us-east-1`
- Glue database: `opslens_dev`
- Glue table: `epss_scores`
- Athena workgroup: `opslens-dev`
- Athena engine: `Athena engine version 3`
- Silver prefix:
  `s3://opslens-dev-data-487757851499-us-east-1/silver/epss/`
- Athena results prefix:
  `s3://opslens-dev-data-487757851499-us-east-1/athena-results/`

The Athena workgroup enforces:

- workgroup configuration;
- SSE-S3 result encryption;
- expected bucket owner `487757851499`;
- CloudWatch metrics;
- a per-query scan cutoff of `10,485,760` bytes.

## Validated query

The Phase 1 validation used snapshot `2026-08-16`.

```sql
SELECT
    cve,
    epss,
    percentile
FROM epss_scores
WHERE snapshot_date = '2026-08-16'
  AND epss > 0.7
ORDER BY epss DESC, cve;
```

The explicit `snapshot_date` makes the query temporally reproducible and
allows Athena to resolve the projected S3 partition:

```text
silver/epss/snapshot_date=2026-08-16/
```

## Reproduce with the AWS CLI

Do not paste the SQL directly into the shell. Build the query string first
and submit it through the Athena API.

```bash
ATHENA_DATABASE="opslens_dev"
ATHENA_WORKGROUP="opslens-dev"
SNAPSHOT_DATE="2026-08-16"

QUERY_STRING="$(
cat <<'SQL'
SELECT
    cve,
    epss,
    percentile
FROM epss_scores
WHERE snapshot_date = '2026-08-16'
  AND epss > 0.7
ORDER BY epss DESC, cve;
SQL
)"

QUERY_ID="$(
  aws athena start-query-execution \
    --query-string "$QUERY_STRING" \
    --query-execution-context \
      Database="$ATHENA_DATABASE",Catalog=AwsDataCatalog \
    --work-group "$ATHENA_WORKGROUP" \
    --region us-east-1 \
    --profile opslens-bootstrap \
    --query QueryExecutionId \
    --output text
)"

echo "QUERY_ID=$QUERY_ID"
```

Wait until Athena reaches a terminal state:

```bash
while true; do
  STATE="$(
    aws athena get-query-execution \
      --query-execution-id "$QUERY_ID" \
      --region us-east-1 \
      --profile opslens-bootstrap \
      --query 'QueryExecution.Status.State' \
      --output text
  )"

  echo "ATHENA_STATE=$STATE"

  case "$STATE" in
    SUCCEEDED|FAILED|CANCELLED)
      break
      ;;
  esac

  sleep 2
done
```

Inspect execution statistics:

```bash
aws athena get-query-execution \
  --query-execution-id "$QUERY_ID" \
  --region us-east-1 \
  --profile opslens-bootstrap \
  --query 'QueryExecution.{
    QueryExecutionId:QueryExecutionId,
    State:Status.State,
    Database:QueryExecutionContext.Database,
    WorkGroup:WorkGroup,
    EngineVersion:EngineVersion.EffectiveEngineVersion,
    DataScannedInBytes:Statistics.DataScannedInBytes,
    EngineExecutionTimeMs:Statistics.EngineExecutionTimeInMillis,
    TotalExecutionTimeMs:Statistics.TotalExecutionTimeInMillis,
    OutputLocation:ResultConfiguration.OutputLocation
  }' \
  --output json
```

## Validated execution

Validation date: `2026-08-16`

```text
QueryExecutionId:
cd0f145b-59e4-435f-9e42-7c836c56bbef

State:
SUCCEEDED

Snapshot:
2026-08-16

Source Silver rows:
360399

Rows matching EPSS > 0.7:
2457

Data scanned:
6084428 bytes

Athena workgroup cutoff:
10485760 bytes

Cutoff utilization:
58.0256%

Engine execution time:
1312 ms

Total execution time:
1501 ms

Result reuse:
false

Result:
s3://opslens-dev-data-487757851499-us-east-1/athena-results/cd0f145b-59e4-435f-9e42-7c836c56bbef.csv
```

The first validated rows were:

```text
CVE-2014-0160   0.99999   0.99997
CVE-2014-3566   0.99999   1.0
CVE-2014-6271   0.99999   0.99993
CVE-2015-1635   0.99999   0.99999
CVE-2017-5638   0.99999   0.99994
```

## Independent Parquet cross-check

The Athena result was independently compared with the original Silver
Parquet file by:

1. reading only `cve`, `epss`, and `percentile`;
2. filtering locally with `epss > 0.7`;
3. sorting by `epss DESC, cve ASC`;
4. comparing every result row with the Athena CSV.

Validation result:

```text
ATHENA_ROW_COUNT=2457
PARQUET_FILTERED_ROW_COUNT=2457

SameRowCount=PASS
SameCves=PASS
SameEpss=PASS
SamePercentiles=PASS
AthenaPredicateValid=PASS
AthenaSortValid=PASS

ATHENA_PARQUET_CROSSCHECK_GATE=PASS
```

This cross-check demonstrates that the Athena result is equivalent to an
independent evaluation of the Silver Parquet artifact.

## Query cost evidence

Athena reported:

```text
DATA_SCANNED_BYTES=6084428
```

The validated pricing calculation applied the Athena minimum billable scan
of 10 MB for the query:

```text
BILLABLE_BYTES=10000000
ESTIMATED_ATHENA_QUERY_COST_USD=0.00005000
```

Validation result:

```text
QuerySucceeded=PASS
ExpectedScannedBytes=PASS
BelowWorkgroupCutoff=PASS
MinimumBillingApplied=PASS
ExpectedAthenaCost=PASS

ATHENA_QUERY_COST_GATE=PASS
```

Pricing is time-sensitive. Revalidate the current Amazon Athena pricing
before using this value as a future cost estimate.

## Result lifecycle

Athena query results are derived artifacts rather than canonical OpsLens
evidence.

The `athena-results/` prefix therefore uses:

```text
current object expiration:     7 days
noncurrent version expiration: 1 day
```

Bronze and Silver current objects do not use this expiration rule.

## Phase 1 conclusion

The analytical path demonstrated by this lab is:

```text
FIRST EPSS
    ↓
S3 Bronze
    ↓
S3 ObjectCreated
    ↓
Silver Lambda
    ↓
Parquet Silver
    ↓
Glue Data Catalog
    ↓
Athena partition projection
    ↓
deterministic SQL
    ↓
validated result + measured scan + cost evidence
```

The validated Phase 1 analytical question has a deterministic,
cross-checked, temporally reproducible answer.
