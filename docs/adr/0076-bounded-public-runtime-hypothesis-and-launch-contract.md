# ADR 0076 — Bounded Public Runtime Hypothesis and Launch Contract

- Status: Accepted for Gate 19.1
- Date: 2026-09-10
- Phase: 19 — Bounded Public Runtime & Productization
- Gate: 19.1 — Public Runtime Hypothesis & Launch Contract
- Issue: #291
- Source main: `feca774535b7d83f57c26f4e9fe7da71ce268f0f`

## Context

OpsLens has an evidence-backed application boundary for public repository analysis, but it does not retain a public HTTP runtime.

The current public orchestration path is:

```text
untrusted JSON
 -> request admission
 -> immutable GitHub repository evidence
 -> metadata-only semantic planning
 -> deterministic hybrid-route admission
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

The repository also contains independently validated deterministic vulnerability correlation, Risk Policy v1, bounded Athena execution, Bedrock Knowledge Base retrieval, grounded synthesis, capability admission, and result-admission building blocks. Those capabilities are not composed downstream of `PublicAnalysisAdmissionHandoff` into one executable public product workload.

Choosing API Gateway + Lambda, Lambda Function URL, an asynchronous queue, ECS/Fargate, or AgentCore before measuring that composition would invert the architecture process: technology preference would define the workload rather than the workload defining the runtime.

## Decision

Gate 19.1 freezes:

```text
runtime decision = DEFERRED_PENDING_MEASUREMENT
leading hypothesis = ASYNC_SUBMIT_STATUS_RESULT
```

`ASYNC_SUBMIT_STATUS_RESULT` is a hypothesis, not standing architecture authority.

The sync/async decision remains deferred because the repository does not yet provide representative end-to-end measurements for:

- public repository acquisition plus downstream deterministic analysis;
- structured and semantic evidence acquisition actually required by public v1;
- bounded model reasoning actually required by public v1;
- aggregate provider retries/throttles;
- serialized final result size;
- end-to-end p50/p95 and upper-bound latency.

No public runtime or runtime IAM is created in Gate 19.1.

## Frozen public workload

The machine-readable authority is:

`labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`

with:

```text
workload_id = public-analysis-workload:v1
operation   = analyze_public_repository
provider    = github
visibility  = public_only
repository/request = 1
third-party code execution = FORBIDDEN
```

Existing evidence-backed bounds are reused instead of being replaced by round numbers. Important examples include the 2,048-byte public request body cutoff, one `uv.lock` file, 5,000 dependency records, 10 MiB Athena scan cutoff per query, retrieval `top_k <= 10`, and bounded synthesis output.

Where the full public composition does not prove a value, Gate 19.1 records `UNMEASURED` rather than inventing a public budget.

## Why not freeze SYNC now?

A synchronous path has the smallest operational surface, but the relevant AWS transport limit depends on the selected API type and must be evaluated against the complete workload rather than one component.

Current AWS documentation states:

- API Gateway HTTP APIs have a maximum integration timeout of 30 seconds and that quota cannot be increased;
- Regional REST API integration timeouts can be increased beyond the default 29-second ceiling, with potential account-level throttle quota implications;
- Lambda itself can run for up to 900 seconds.

Therefore `Lambda can run for 15 minutes` does **not** imply that a public synchronous HTTP request should be held open for 15 minutes.

References:

- https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-quotas.html
- https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-execution-service-limits-table.html
- https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html

## Why async is only the leading hypothesis

The public workload has multiple potentially variable boundaries: GitHub network I/O, deterministic candidate evaluation, optional/required Athena, Knowledge Base retrieval, Bedrock inference, and retries/throttles. An asynchronous job model can isolate those latencies, provide backpressure, and decouple public request lifetime from worker lifetime.

However, an async topology introduces its own authority and operational cost:

```text
submit admission
 -> queue
 -> idempotent worker
 -> persisted status/result
 -> result retrieval
```

That means more IAM responsibilities, duplicate-delivery handling, lifecycle state, result storage, cancellation semantics, and observability. SQS standard queues use at-least-once delivery, so idempotency cannot be optional if this path is selected.

Reference:

- https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html

## Function URL position

Lambda Function URLs remain technically possible but are not favored for the first public product surface.

AWS currently exposes `AWS_IAM` and `NONE` authentication modes. `NONE` can expose unauthenticated invocation when the function resource policy grants it. Reserved concurrency can cap Lambda concurrency, but this is not equivalent to the complete request validation, identity, abuse, quota, cost, and product contract needed by OpsLens.

References:

- https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html
- https://docs.aws.amazon.com/lambda/latest/dg/urls-configuration.html

## API usage plans are not a hard cost boundary

If REST API usage plans are evaluated later, their throttling and quotas must not be treated as deterministic denial-of-wallet controls. AWS documents them as best-effort and explicitly advises not to rely on them alone for cost control or access blocking.

Reference:

- https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html

## IAM decision

Gate 19.1 creates a responsibility-to-permission matrix, not a role.

The rule is:

```text
concrete runtime responsibility
 -> required service action
 -> exact resource
 -> IAM statement
```

and never:

```text
future feature aspiration
 -> broad runtime role
```

Examples already supported by current AWS documentation and repository adapters include:

- Athena execution: `athena:StartQueryExecution`, `athena:GetQueryExecution`, `athena:GetQueryResults`, and `athena:StopQueryExecution` scoped to the retained workgroup, plus only the exact Glue/S3 access the query path requires;
- Bedrock Knowledge Base retrieval: `bedrock:Retrieve` on the approved Knowledge Base;
- non-streaming Bedrock Converse: `bedrock:InvokeModel` on the selected inference target/profile resources.

No IAM mutation is authorized by this ADR.

References:

- https://docs.aws.amazon.com/service-authorization/latest/reference/list_athena.html
- https://docs.aws.amazon.com/athena/latest/APIReference/API_GetQueryResults.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/kb-how-retrieval.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html

## Cost decision

Gate 19.1 keeps the Phase 18 evidence vocabulary:

```text
MEASURED
DERIVED
UNMEASURED
NOT_APPLICABLE
CONFIGURED_LIMIT
```

Configured limits are not utilization. Component lab costs are not public workload costs. No monthly TCO is derived.

Athena continues to have a workgroup scan cutoff. AWS documents on-demand SQL pricing as data-scanned based, and the current pricing model includes a 10 MB minimum per query. The exact public query count is still `UNMEASURED` because the public composition is missing.

References:

- https://docs.aws.amazon.com/athena/latest/APIReference/API_WorkGroupConfiguration.html
- https://aws.amazon.com/athena/pricing/

## Observability decision

The future runtime must emit content-minimized operational evidence before any public deployment is accepted. Required categories include request/trace/workload identities, repository identity hash, stage duration/outcome/failure category, provider call counts, Bedrock tokens when available, Athena bytes scanned, retries, throttles, rejection reasons, and cost attribution identifiers when available.

Full prompts, source code, repository contents, raw payloads, credentials, sensitive tokens, and full model responses are forbidden by default.

This preserves Phase 17 telemetry hardening.

## Disable and recovery decision

A future public runtime must have narrowly named controls with proven scope. Gate 19.1 distinguishes:

```text
ingress disable
new-job admission disable
queue consumer pause
model invocation disable
Athena execution disable
background ingestion pause
```

The existing Phase 17 `scheduled_ingestion_enabled=false` mechanism controls exactly three recurring EventBridge Scheduler resources. It is not and must not be renamed into a global kill switch.

## Security invariants

The public runtime must preserve:

```text
READ, NEVER EXECUTE third-party repository code.
Repository Risk != Runtime Exposure.
retrieved content != instruction authority
model proposal != authorization
tool/protocol success != business truth
```

The Gate 19.1 artifact freezes explicit abuse paths including request/repository amplification, SSRF-style source redirection, GitHub abuse, prompt/retrieval poisoning, model/Athena/token/retry amplification, concurrency exhaustion, denial-of-wallet, replay/result tampering, and telemetry leakage.

## Gate 19.2 experiment boundary

The smallest next experiment is **not** a public deployment.

Gate 19.2 should compose or invoke a representative non-public runner through the complete product stages and collect stage/end-to-end timings, provider-call counts, token counts, Athena bytes when used, retry/throttle evidence, and final serialized result size.

If real AWS calls are required for those measurements, they remain a human execution boundary. Gate 19.1 does not authorize ChatGPT to mutate AWS or invoke paid model/capability paths.

Only after those measurements may the project promote the decision to `SYNC` or `ASYNC`.

## Consequences

Positive:

- runtime topology follows evidence rather than preference;
- missing public workload data remains visible as `UNMEASURED`;
- IAM is decomposed by responsibility before roles exist;
- denial-of-wallet controls become part of launch design;
- historical Phase 18 evidence remains immutable;
- the first deploy experiment stays intentionally small.

Costs/trade-offs:

- Phase 19 does not immediately produce a public URL;
- one additional measurement gate is required before infrastructure selection;
- async remains attractive but cannot yet be advertised as the selected architecture.

## AIP-C01 relation

This decision exercises enterprise integration, FM API integration, synchronous versus asynchronous patterns, IAM, API safety, cost controls, observability, performance measurement, and troubleshooting. Those topics reinforce AIP-C01, but they do not independently justify adding API Gateway, SQS, Step Functions, WAF, AgentCore, or any other AWS service.

```text
AIP-C01 topic != product requirement
```
