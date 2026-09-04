# Phase 6 — Gate 6.4: Real Bedrock Planner Invocation

Date: 2026-09-04

Status: implementation and real `dev` evidence complete; final repository CI/PR validation pending.

## Goal

Prove the frozen Gate 6.3 planner contract against a real Amazon Bedrock model without transferring SQL or execution authority to the model.

Permanent boundary:

> **No unrestricted text-to-SQL.**

The real path is:

```text
natural-language question
 -> BedrockSemanticPlanner
 -> Amazon Bedrock Converse
 -> structured planner proposal
 -> deterministic planner-output parser
 -> typed SemanticQuery | unsupported
 -> ExecuteNaturalLanguageSemanticQuery
 -> deterministic SQL compiler (supported only)
 -> exact compiler-shape admission
 -> bounded AthenaQueryExecutor
 -> structured evidence
```

The model proposes bounded semantics only. Application code remains authoritative for parsing, validation, SQL generation, Athena execution, and evidence validation.

## Selected Bedrock runtime boundary

Model / inference profile:

```text
model_id: us.anthropic.claude-haiku-4-5-20251001-v1:0
Region used by client: us-east-1
inference mode: US Geographic system-defined inference profile
streaming: disabled
tools: disabled
temperature: 0.0
maxTokens: 256
```

The base foundation model advertises inference through an inference profile. The US Geographic profile was selected instead of Global so the routing set is explicitly bounded to the documented US destinations.

No new AWS resource was created for this gate.

## Runtime adapter

`BedrockSemanticPlanner` is an outbound adapter over an injected `BedrockConverseClient` Protocol. The adapter does not construct credentials or a boto3 session internally.

Responsibilities:

```text
build frozen Converse payload
invoke Converse once
require the expected non-streaming text response shape
reparse model text through parse_planner_json()
capture metadata-only invocation evidence
return BedrockPlannerResult
```

The typed invocation evidence records observed runtime facts:

```text
model_id
region
request_id
stop_reason
input_tokens
output_tokens
total_tokens
cache_read_input_tokens
cache_write_input_tokens
bedrock_latency_ms
client_elapsed_ms
retry_attempts
```

Estimated USD cost is intentionally not part of the runtime evidence contract because pricing is external and time-varying. Cost is derived in documentation from observed token counts and the rate card verified for the experiment.

## Offline adapter validation

Fake-client tests prove:

- supported planner output becomes a typed `SemanticQuery`;
- unsupported output remains a typed fail-closed decision;
- the Bedrock client is invoked exactly once with the frozen model/inference configuration;
- multiple/non-text content cannot cross the adapter boundary;
- missing runtime evidence fails closed;
- inconsistent token evidence fails closed;
- invalid local timing fails closed;
- SDK/provider invocation failures are wrapped at the Bedrock adapter boundary while preserving the original exception as the cause;
- unsupported planner decisions do not reach compiler/Athena execution in the application composition.

Targeted validation before the real execution reached:

```text
pytest: 35 passed
Ruff: PASS
Pyright: 0 errors / 0 warnings / 0 informations
```

Additional adapter/error-boundary changes made after the first credential-expiry observation require the final repository validation before merge.

## Real supported E2E evidence

Question:

```text
Which CVEs have EPSS of at least 0.7 on 2026-09-03?
```

Planner decision:

```text
decision: semantic_query
metric: epss_score
dimensions: [cve]
snapshot_date: 2026-09-03
minimum_score: 0.7
order_by: epss_score
order_direction: desc
limit: 20
```

Bedrock evidence:

```text
request_id:                    7588abbc-003f-433f-8308-00fa4f14ec08
stop_reason:                   end_turn
input_tokens:                  942
output_tokens:                 79
total_tokens:                  1021
cache_read_input_tokens:       0
cache_write_input_tokens:      0
bedrock_latency_ms:            1632
client_elapsed_ms:             2894
retry_attempts:                0
```

The model output was reparsed into the existing typed `SemanticQuery`; model-generated SQL was never accepted or executed.

Athena evidence from the same versioned entrypoint:

```text
query_execution_id:            09a32501-a06c-4437-809c-ebcaf350cd1d
row_count:                     20
data_scanned_bytes:            3,785,003 (~3.61 MiB)
engine_execution_time_ms:      994
total_execution_time_ms:       1,192
workgroup scan cutoff:         10 MiB
```

All returned rows had EPSS `0.99999`. The deterministic secondary `cve ASC` tie-break is visible in the result ordering.

This proves the versioned path:

```text
natural language
 -> real Bedrock model
 -> structured proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic compiler
 -> bounded Athena executor
 -> real EPSS rows
```

## Cost evidence

The Bedrock rate card verified for this experiment was:

```text
input:  $1.10 / 1M tokens
output: $5.50 / 1M tokens
```

Supported invocation estimate:

```text
942 input  -> $0.0010362
79 output  -> $0.0004345
-----------------------
planner    -> $0.0014707 (~$0.00147)
```

This is an experiment-time estimate, not immutable runtime evidence.

Athena scanned only ~3.61 MiB and remained below the enforced 10 MiB workgroup cutoff.

## Real fail-closed semantic evidence

Question intentionally omitted the required explicit snapshot date:

```text
Which CVEs have EPSS of at least 0.7?
```

Result:

```text
decision:       unsupported
reason:         missing_explicit_snapshot_date
athena_invoked: false
```

Bedrock evidence:

```text
request_id:                    0ec60e96-30e6-47cf-935b-19a6bfa6f0a4
stop_reason:                   end_turn
input_tokens:                  933
output_tokens:                 23
total_tokens:                  956
cache_read_input_tokens:       0
cache_write_input_tokens:      0
bedrock_latency_ms:            878
client_elapsed_ms:             2145
retry_attempts:                0
```

Estimated planner cost:

```text
933 input  -> $0.0010263
23 output  -> $0.0001265
-----------------------
planner    -> $0.0011528 (~$0.00115)
```

The important property is not merely that the model said `unsupported`; the deterministic application path granted no Athena execution authority.

## Real operational failure evidence

Before the successful E2E run, the local IAM Identity Center session had expired.

Observed failure:

```text
botocore.exceptions.TokenRetrievalError
Error when retrieving token from sso: Token has expired and refresh failed
```

The request failed during credential retrieval/signing before Bedrock invocation, so Athena was not reached. The session was renewed with the existing local Identity Center profile and the same versioned entrypoint then succeeded.

This is a local lab/bootstrap authentication failure, not evidence of a Bedrock model or inference-profile failure.

The bootstrap/admin Identity Center profile used here is **not** the final deployed runtime IAM boundary.

## Security and authority conclusions

Gate 6.4 preserves the architecture established in Gates 6.1–6.3:

```text
LLM authority
  natural-language interpretation
  bounded structured semantic proposal

Deterministic authority
  planner-output parsing
  semantic validation
  database/table/column selection
  SQL compilation
  execution parameters
  LIMIT
  Athena admission
  polling/result bounds
  evidence validation
```

The Bedrock adapter receives no tool capability and no Athena client. The natural-language application service invokes Athena only after a `PlannedSemanticQuery` has reentered the typed deterministic boundary.

## IAM note

The final runtime least-privilege criterion is deferred until OpsLens has a deployed runtime identity. Creating a synthetic deployed runtime solely to satisfy this checkbox would add infrastructure without a current execution need.

When that runtime exists, it must receive only the Bedrock inference-profile/foundation-model resources required for the selected geographic profile plus the already-bounded Athena/data permissions required by the query path.

## Gate 6.4 exit state

Demonstrated:

- [x] real Bedrock Converse invocation;
- [x] US Geographic inference profile works from `us-east-1`;
- [x] structured planner output works with the frozen contract;
- [x] real output reenters the deterministic parser and typed `SemanticQuery`;
- [x] versioned supported natural-language E2E path reaches bounded Athena;
- [x] token, latency, request, retry, and cache-use evidence is captured;
- [x] experiment-time planner cost is derived from observed token counts;
- [x] versioned missing-date question fails closed before Athena;
- [x] a real local authentication failure was diagnosed;
- [x] no unrestricted SQL, arbitrary identifiers, tools, streaming, RAG, agents, MCP, or AgentCore were introduced;
- [x] final runtime IAM boundary explicitly deferred until a deployed runtime identity exists.

Remaining before merge/closeout:

```text
remove temporary marketplace-offer material if still present locally
run final targeted + regression CI validation
update current-state / roadmap
open PR and merge only after green CI
```
