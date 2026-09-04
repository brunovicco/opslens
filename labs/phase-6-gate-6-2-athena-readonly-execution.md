# Phase 6 Gate 6.2 — Bounded read-only Athena execution

Status: implementation gate; real `dev` smoke evidence is required before closeout.

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

The adapter also rejects:

- non-`SELECT` statements;
- multiple statements / semicolons;
- statements outside the EPSS Silver relation;
- row bounds outside `1..100`;
- unexpected Athena pagination;
- malformed result metadata or row widths;
- unknown Athena states.

## Bounded runtime behavior

The synchronous executor polls only the documented Athena states:

```text
active:    QUEUED | RUNNING
terminal:  SUCCEEDED | FAILED | CANCELLED
```

A polling timeout triggers `StopQueryExecution` before raising a typed timeout error.

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

The real smoke test therefore uses an explicitly selected local AWS identity through the standard SDK credential chain. That identity is validation-only evidence and does **not** satisfy the final Phase 6 runtime least-privilege IAM criterion.

Before a Lambda/API/agent runtime is introduced, create a dedicated least-privilege execution role scoped to the required Athena workgroup, Glue catalog/database/table metadata, source S3 objects, and Athena result location.

## Official AWS behavior verified before implementation

Current AWS documentation was checked for:

- `StartQueryExecution` execution parameters, database context, and explicit workgroup selection;
- `GetQueryExecution` terminal/active state semantics;
- `GetQueryResults` result retrieval and S3 result-object permission implications;
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
- unexpected result pagination;
- malformed row width;
- direct attempts to bypass the read-only EPSS relation boundary.

## Real dev smoke

After the implementation PR is green, run the smoke script with an explicit snapshot date that exists in the EPSS Silver dataset:

```bash
uv run python scripts/run_semantic_query_athena.py \
  --snapshot-date 2026-09-03 \
  --epss-min 0.7 \
  --limit 20 \
  --region us-east-1 \
  --profile <your-dev-validation-profile>
```

Do not add a `latest` fallback if that date is unavailable. Select another known snapshot explicitly.

Record at minimum:

```text
query_execution_id
row_count
data_scanned_bytes
engine_execution_time_ms
total_execution_time_ms
first bounded result rows
```

Also record an intentional failure using a nonexistent explicit partition date or another safe failure case that does not broaden SQL authority.

## Cost

Incremental infrastructure cost: `0`.

The smoke query itself incurs normal Athena data-scanned charges plus the existing S3/Glue costs. The workgroup's 10 MiB cutoff remains the hard query scan bound for this dev slice.

## Gate 6.2 closeout condition

Do not mark Gate 6.2 complete until:

1. CI is green;
2. one real query succeeds in `opslens-dev`;
3. bytes scanned and execution timing are recorded;
4. one intentional safe failure is recorded;
5. no broader AWS service or model authority was introduced.

Bedrock remains outside Gate 6.2.
