# Phase 6 Gate 6.2 — Bounded read-only Athena execution

Status: **COMPLETE** — real `dev` success and intentional fail-closed evidence recorded on 2026-09-04.

## Purpose

Gate 6.1 froze the first semantic-query contract and deterministic SQL compiler. Gate 6.2 adds the first AWS execution boundary without adding Bedrock, RAG, agents, or a public runtime.

The supported question remains deliberately narrow:

> Which CVEs have EPSS of at least 0.7 on an explicit snapshot date?

Execution path:

```text
SemanticQuery
 -> deterministic compiler
 -> CompiledAthenaQuery
 -> bounded Athena executor
 -> opslens-dev workgroup
 -> opslens_dev.epss_scores
 -> bounded structured execution evidence
```

## Fixed execution authority

The executor fixes these values in application-owned code:

```text
database   opslens_dev
workgroup  opslens-dev
relation   "opslens_dev"."epss_scores"
```

A caller or future model cannot select another database, workgroup, table, column, or SQL fragment.

The adapter additionally requires the exact Gate 6.1 compiler grammar before calling Athena:

```text
SELECT "cve", "epss"
FROM "opslens_dev"."epss_scores"
WHERE "snapshot_date" = ? [AND "epss" >= ?]
ORDER BY "epss" ASC|DESC, "cve" ASC
LIMIT 1..100
```

The SQL `LIMIT` must equal the already-validated semantic result bound. The adapter also validates the positional literal shapes: a quoted explicit ISO calendar date and, when present, a finite EPSS value from `0.0` through `1.0`. This defense in depth prevents a manually forged `CompiledAthenaQuery` from using the allowed relation as a bridge to joins, different projections/predicates/orderings, injected execution-parameter semantics, or a broader SQL limit.

The adapter also rejects:

- SQL outside the exact compiler-owned EPSS grammar;
- SQL/result-bound mismatches;
- invalid execution-parameter literal shapes;
- row bounds outside `1..100`;
- pagination that exceeds the semantic row bound;
- repeated/cyclic Athena pagination tokens;
- malformed or changing result metadata;
- malformed result row widths;
- unknown Athena states.

## Bounded runtime behavior

The synchronous executor polls only the documented Athena states:

```text
active:    QUEUED | RUNNING
terminal:  SUCCEEDED | FAILED | CANCELLED
```

A polling timeout triggers `StopQueryExecution` before raising a typed timeout error.

`GetQueryResults` pagination is treated as an Athena transport concern, not as broader query authority. Continuation tokens may be followed only while the accumulated result remains inside the already-validated semantic row limit. Token cycles and excess rows fail closed.

The successful result records:

```text
query_execution_id
data_scanned_bytes
engine_execution_time_ms
total_execution_time_ms
columns
bounded rows
```

This makes the first Athena cost/latency evidence observable without adding a new runtime service.

## Existing AWS control reused

No new AWS service is introduced by this gate. It reuses the existing Terraform-managed workgroup:

```text
name: opslens-dev
workgroup configuration enforced: true
CloudWatch metrics: enabled
bytes scanned cutoff per query: 10 MiB
result location: existing OpsLens data bucket / athena-results/
encryption: SSE-S3
```

The application does not supply a result location, so the enforced workgroup configuration remains authoritative.

## IAM note

This gate does not create a long-lived runtime role yet because there is no deployed semantic-query runtime to attach it to.

The real smoke test therefore used an explicitly selected local IAM Identity Center validation profile through the standard SDK credential chain. That identity is validation-only evidence and does **not** satisfy the final Phase 6 runtime least-privilege IAM criterion.

Before a Lambda/API/agent runtime is introduced, create a dedicated least-privilege execution role scoped to the required Athena workgroup, Glue catalog/database/table metadata, source S3 objects, and Athena result location.

## Official AWS behavior verified before implementation

Current AWS documentation was checked for:

- `StartQueryExecution` execution parameters, database context, and explicit workgroup selection;
- `GetQueryExecution` terminal/active state semantics;
- `GetQueryResults` result retrieval, `MaxResults`, continuation tokens, and S3 result-object permission implications;
- workgroup-enforced query settings and bytes-scanned controls.

Important security implication: permission to the Athena result S3 location can allow direct result-object access independently of `athena:GetQueryResults`. Final runtime IAM must therefore constrain both Athena API actions and S3 result access.

## CI validation

The semantic-query CI slice must remain green for:

```text
uv lock --check
uv sync --frozen
ruff
pyright strict
pytest tests/unit/semantic_query
```

Failure-path tests cover:

- Athena `FAILED`;
- Athena `CANCELLED`;
- timeout + cancellation;
- unknown future state;
- missing execution ID;
- pagination that would exceed the semantic row bound;
- repeated pagination tokens;
- malformed or changing result metadata;
- malformed row width;
- direct attempts to bypass the exact compiler-owned SQL grammar;
- forged execution parameters;
- SQL/result-bound mismatches.

## Real dev smoke

The repository currently uses a `src/` layout without installing the local project package during `uv sync`, so the local smoke command explicitly adds `src` to `PYTHONPATH`:

```bash
PYTHONPATH=src uv run python scripts/run_semantic_query_athena.py \
  --snapshot-date 2026-09-03 \
  --epss-min 0.7 \
  --limit 20 \
  --region us-east-1 \
  --profile opslens-bootstrap
```

No `latest` fallback exists. Temporal selection remains explicit.

### Successful end-to-end evidence — 2026-09-04

The corrected executor completed the real query end to end through `opslens-dev` and returned bounded structured evidence:

```text
query_execution_id:         958fb573-1a69-4ce6-8a36-d9be45e71c79
columns:                    cve, epss
row_count:                  20
data_scanned_bytes:         3,785,003
engine_execution_time_ms:   973
total_execution_time_ms:    1,128
```

`3,785,003` bytes is approximately `3.61 MiB`, below the existing `10 MiB` workgroup cutoff.

First bounded rows:

```text
CVE-2014-0160   0.99999
CVE-2014-3566   0.99999
CVE-2014-6271   0.99999
CVE-2015-1635   0.99999
CVE-2017-5638   0.99999
```

All 20 returned rows were within the requested `EPSS >= 0.7` filter. The equal-score rows also demonstrated the deterministic secondary `cve ASC` ordering compiled by application code.

### Intentional safe failure — 2026-09-04

The explicit failure test used an invalid semantic limit of `101`:

```bash
PYTHONPATH=src uv run python scripts/run_semantic_query_athena.py \
  --snapshot-date 2026-09-03 \
  --epss-min 0.7 \
  --limit 101 \
  --region us-east-1 \
  --profile opslens-bootstrap
```

Observed failure:

```text
SemanticQueryValidationError:
Semantic query limit must be an integer from 1 to 100.
```

The failure occurs while constructing `SemanticQuery`, before compilation or any Athena API call. This is the intended fail-closed behavior for unsupported query authority.

A nonexistent explicit partition date is **not** used as a failure test because Athena may legitimately return a successful empty result for a valid query whose selected partition contains no rows.

### 2026-09-04 integration finding — Athena result pagination

The first real `dev` attempt reached a successful Athena execution and entered `GetQueryResults`, but the application rejected the response because Athena returned a `NextToken` even though the compiler-owned SQL already had `LIMIT 20`.

Observed application failure:

```text
SemanticQueryResultError:
Athena returned pagination for a SQL query that is already row-bounded.
```

This exposed an incorrect application assumption: SQL row bounds and Athena result-page transport are separate concerns. AWS documents `GetQueryResults` as a paginated API whose `NextToken` continues a truncated response.

The corrective boundary is:

```text
compiler-owned SQL LIMIT <= 100
 + bounded GetQueryResults page size
 + bounded continuation-token traversal
 + accumulated rows must remain <= semantic limit
 + repeated token => fail closed
```

The integration failure is retained as evidence because it produced a real implementation correction rather than being hidden by mocks.

## Cost

Incremental infrastructure cost: `0`.

The smoke query itself incurred normal Athena data-scanned charges plus existing S3/Glue costs. The workgroup's 10 MiB cutoff remained the hard query scan bound for this dev slice; the observed query scanned approximately 3.61 MiB.

## Gate 6.2 closeout

Gate 6.2 is complete because:

1. CI is green for the merged execution/pagination implementation and must remain green for this closeout hardening;
2. one real query succeeded end to end in `opslens-dev`;
3. bytes scanned and execution timing were recorded;
4. one intentional fail-closed semantic validation was recorded;
5. no broader AWS service or model authority was introduced;
6. direct adapter admission was narrowed to the exact compiler-owned Gate 6.1 grammar and literal parameter shapes.

Bedrock remains outside Gate 6.2. Phase 6 as a whole remains **IN PROGRESS**.
