# ADR 0020 — Reject unrestricted text-to-SQL in the Semantic Query Layer

- Status: Accepted
- Date: 2026-09-03
- Phase: 6 — Semantic Query Layer

## Context

Phase 5 closes with deterministic, content-addressed repository-risk evidence. Phase 6 introduces natural-language planning over structured OpsLens data, but a model must not gain authority to generate arbitrary SQL for Athena.

The permanent project guardrail is:

> **No unrestricted text-to-SQL.**

The model may later answer the question "what did the user mean?" by proposing a typed semantic query. Deterministic application code remains responsible for deciding whether that query is supported and for producing the only SQL that may be sent to Athena.

The first implementation must therefore establish the semantic contract and compiler boundary before Bedrock or Athena runtime integration.

## Decision

Create a separate `opslens.semantic_query` package with a deliberately narrow Phase 6.1 contract over the existing Glue table:

```text
opslens_dev.epss_scores
```

The first factual question is:

> Which CVEs have EPSS of at least 0.7 on 2026-09-03?

The frozen initial semantic surface is:

```text
metric
  epss_score

dimension
  cve

filters
  snapshot_date      required explicit calendar date
  minimum_score      optional finite number in [0.0, 1.0]

order
  epss_score asc | desc

limit
  integer from 1 through 100
  default 20
```

The compiler maps only that contract to fixed identifiers:

```text
database       opslens_dev
table          epss_scores
columns        cve, epss
partition      snapshot_date
order columns  epss, then cve as a stable tie breaker
```

No database, table, column, SQL operator, SQL fragment, or order expression is accepted as free-form user/model text.

## Temporal semantics

`snapshot_date` is mandatory for the first slice.

Phase 6.1 does not support semantic values such as:

```text
latest
current
most recent
now
```

The model is therefore unable to choose a temporal snapshot implicitly. A later application rule may resolve such language only after its semantics are separately frozen and tested.

## Athena parameterization boundary

Current Amazon Athena documentation was verified before this decision. Athena execution parameters use positional `?` placeholders in supported DML queries, and parameter values are supplied sequentially. Named parameters are not supported.

Phase 6.1 therefore compiles filter values to positional Athena execution parameters while keeping identifiers and SQL structure entirely compiler-owned.

For the current Glue schema, `snapshot_date` is a string partition, so the compiler renders its already-validated `date` value as an Athena string execution parameter. EPSS thresholds are rendered only from already-validated finite numeric values.

The bounded `LIMIT` is compiler-rendered from a validated integer in `[1, 100]`; it is never free-form text.

Official references checked on 2026-09-03:

- https://docs.aws.amazon.com/athena/latest/ug/querying-with-prepared-statements.html
- https://docs.aws.amazon.com/athena/latest/ug/querying-with-prepared-statements-querying-using-execution-parameters.html
- https://docs.aws.amazon.com/athena/latest/APIReference/API_StartQueryExecution.html

## Compiler boundary

```text
future natural-language planner
        |
        v
Typed SemanticQuery
        |
        v
runtime/domain validation
        |
        v
allowlisted deterministic compiler
        |
        v
CompiledAthenaQuery
  SQL owned by code
  positional literal parameters
        |
        v
future read-only Athena executor
```

The planner is not part of Gate 6.1.

The compiler must fail closed when a typed query requests a combination for which no explicit compiler branch exists. Merely constructing a structurally valid object does not grant query authority.

## Failure semantics

The contract rejects before Athena execution:

```text
unknown metric
unknown dimension
unknown order field
unknown sort direction
non-calendar snapshot value
non-numeric EPSS threshold
non-finite or out-of-range EPSS threshold
non-integer or out-of-range limit
unsupported metric/dimension combinations
```

Missing or unsupported semantics do not receive guessed defaults.

The only initial defaults are part of the frozen contract itself:

```text
order_by        epss_score
order_direction desc
limit           20
```

No default snapshot exists.

## Security properties

The first slice is intentionally resistant to SQL-authority escalation:

- semantic concepts are enums, not identifiers supplied by the model;
- filters are strongly typed before compilation;
- SQL identifiers are constants in application code;
- filter values occupy positional parameter locations only;
- sort direction is compiled from an enum to a fixed keyword;
- row count is bounded by a validated integer;
- unsupported typed combinations fail closed;
- no repository, model, or user input can append a SQL fragment.

Parameterized values are defense in depth, not a substitute for the semantic allowlist. Athena parameterization does not make arbitrary table or column selection acceptable.

## AWS, IAM, cost, and observability

Gate 6.1 introduces:

```text
new AWS resources:     0
new IAM permissions:   0
Athena executions:     0
Bedrock model calls:   0
incremental AWS cost:  $0
```

The repository already contains the `opslens_dev.epss_scores` Glue table and an Athena workgroup with an existing dev bytes-scanned cutoff. Runtime IAM and execution telemetry will be designed only when the Athena executor is introduced.

The later executor must remain read-only and workgroup-bounded. The later Bedrock planner must emit data that is validated into this semantic contract; it must not emit executable SQL.

## Consequences

### Positive

- model behavior is separated from query authority;
- SQL generation is deterministic and unit-testable without AWS;
- unknown semantics fail before cost or data access occurs;
- the first query surface is small enough to reason about exhaustively;
- partition date is explicit, which supports Athena partition pruning;
- the contract can later become the target schema for structured Bedrock output.

### Trade-offs

- Phase 6.1 supports only one metric/dimension family;
- users cannot ask arbitrary analytics questions yet;
- a new semantic concept requires an explicit contract and compiler change;
- the initial compiler is intentionally coupled to one proven Glue relation.

These restrictions are intentional. Query flexibility will expand only after deterministic evidence, security behavior, tests, and cost bounds are proven for each new surface.

## Next boundary

After Gate 6.1 quality gates pass, the next small gate should execute the compiled EPSS query through the existing read-only Athena boundary and record real result/scan evidence. Bedrock planning should remain downstream of the deterministic contract and should not be introduced merely to prove SQL generation.
