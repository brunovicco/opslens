# Phase 19 Gate 19.1 — Public Runtime Hypothesis & Launch Contract

_Status: IN PROGRESS — frozen contract created; exact-head CI still required_

_Source protected main: `feca774535b7d83f57c26f4e9fe7da71ce268f0f`_

_Issue: #291_

## Objective

Freeze the smallest evidence-backed public workload and the decision criteria for its future runtime before any public endpoint, runtime IAM, queue, worker, result store, or new AWS resource exists.

Gate 19.1 is architecture and experiment design only.

```text
AWS mutations          0
IAM mutations          0
new AWS resources      0
model invocations      0
capability executions  0
public endpoints       0
```

PR #89 remains untouched.

## Phase 18 source checkpoint

Protected `main` was independently re-read before this gate.

```text
main                             feca774535b7d83f57c26f4e9fe7da71ce268f0f
PR #290                          MERGED
issue #289                       CLOSED / COMPLETED
Phase 18                         COMPLETE
open PR #89                      DRAFT / DEFERRED / UNTOUCHED
```

The protected Phase 18 merge intentionally contains historical evidence whose status says the closeout is pending protected merge. Those records describe the state when the closeout PR was created and must remain historical.

Current-facing README/current-state/roadmap/architecture text that still treats the merge as pending is post-merge drift and is synchronized in the Phase 19 branch without rewriting the historical closeout artifact or ADR 0075.

## Repository implementation investigation

### Retained public path

The actual application path on `main` is:

```text
raw bytes
 -> admit_public_analysis_request
 -> PublicAnalysisRequest
 -> build_public_repository_evidence
      -> get_repository
      -> get_commit
      -> get_uv_lock
      -> parse_uv_lock_evidence
      -> normalize_uv_lock_pypi_dependencies
 -> PublicRepositoryEvidenceExecution
 -> build_public_semantic_planning_request
 -> injected PublicSemanticPlanner.plan
 -> parse_public_semantic_plan_proposal
 -> deterministic Phase 8 route admission
 -> build_public_analysis_admission_handoff
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

`execute_instrumented_public_analysis` wraps those same stages with content-minimized operational events. Its success result is still `PublicAnalysisAdmissionHandoff`; it does not execute a final product analysis.

### What is real versus only adjacent capability

| Product stage | Current state | Network/AWS behavior |
| --- | --- | --- |
| public request admission | implemented | offline |
| repository metadata + immutable commit | implemented | fixed-host GitHub REST |
| dependency evidence | implemented | exact-commit `uv.lock` only |
| dependency normalization | implemented | offline |
| vulnerability correlation | implemented elsewhere | not composed into public executor |
| NVD/KEV/EPSS enrichment | implemented elsewhere | not composed into public executor |
| Risk Policy v1 | implemented elsewhere | not composed into public executor |
| structured semantic query | implemented | bounded synchronous Athena adapter, not public-composed |
| knowledge retrieval | implemented | one bounded Bedrock KB `Retrieve` call per adapter invocation, not public-composed |
| grounded synthesis | implemented | bounded Bedrock Converse, not public-composed |
| public semantic planner | Protocol + tests/labs | no retained concrete production implementation on `main` |
| hybrid authority | implemented | public path binds to Phase 8 route authority but does not acquire full downstream evidence |
| final public result admission | missing | no final product response |
| HTTP transport | missing | no public endpoint/runtime |

This distinction is the main Gate 19.1 finding:

```text
rich retained capabilities != executable public product workload
```

## GitHub provider call shape

The retained GitHub adapter does not follow redirects and does not implement automatic retries. The success path used by current repository evidence derives four physical HTTP calls:

```text
get_repository          1
get_commit ref resolve  1
get_commit exact object 1
get_uv_lock             1
-------------------------
physical HTTP calls     4
```

Each request has a configured 10-second timeout by default. This does not mean public repository acquisition has a 40-second expected latency; it is a worst-case per-call timeout configuration, not measured utilization.

The adapter fetches from the fixed `api.github.com` host rather than dereferencing a user-supplied URL, preserving the SSRF/source-redirection boundary.

## Existing evidence-backed bounds reused

Gate 19.1 does not invent a new set of attractive round numbers.

| Dimension | Classification | Value |
| --- | --- | ---: |
| public request body | `CONFIGURED_LIMIT` | 2,048 bytes |
| repository URL | `CONFIGURED_LIMIT` | 256 chars |
| repository files read by public evidence path | `CONFIGURED_LIMIT` | 1 (`uv.lock`) |
| parsed dependency records | `CONFIGURED_LIMIT` | 5,000 |
| GHSA occurrences supplied to repository scan | `CONFIGURED_LIMIT` | 50,000 |
| vulnerability candidate evaluations | `CONFIGURED_LIMIT` | 100,000 |
| Athena bytes scanned/query | `CONFIGURED_LIMIT` | 10,485,760 |
| Knowledge Base retrieval `top_k` | `CONFIGURED_LIMIT` | <= 10 |
| admitted knowledge context | `CONFIGURED_LIMIT` | 16,384 UTF-8 bytes |
| knowledge/hybrid synthesis output | `CONFIGURED_LIMIT` | 2,048 tokens |
| GitHub physical calls on current success path | `DERIVED` | 4 |
| public Athena calls/request | `UNMEASURED` | — |
| public Bedrock retrieval calls/request | `UNMEASURED` | — |
| public model calls/request | `UNMEASURED` | — |
| public capability calls/request | `UNMEASURED` | — |
| end-to-end timeout target | `UNMEASURED` | — |
| public result bytes | `UNMEASURED` | — |

`UNMEASURED` is deliberate. It prevents component limits from being laundered into a whole-request budget.

## Frozen workload

Machine-readable authority:

`labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`

Identity:

```text
public-analysis-workload:v1
```

Request:

```json
{
  "repository_url": "https://github.com/owner/repository",
  "requested_ref": "optional"
}
```

The URL is an admission format, not an outbound fetch target. The admitted owner/repository coordinates are resolved through the fixed GitHub adapter and then bound to an immutable commit.

Initial dependency-evidence scope remains PyPI via inert `uv.lock`; no SBOM/tree crawl/fallback manifest expansion is silently added to Gate 19.1.

Required public evidence needs remain exactly:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

with `ALL_REQUIRED` completeness.

## Runtime decision

```text
DEFERRED_PENDING_MEASUREMENT
```

Leading hypothesis:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

This is intentionally not the same as selecting SQS or creating a result database.

### Why the decision is deferred

The first public endpoint must expose the product workload, not only the already-fast admission/handoff slice. Today the repository does not provide one retained execution that measures the complete chain from repository request through findings/risk/evidence/synthesis to admitted final result.

A synchronous decision would therefore be based on partial latency. An asynchronous decision would add state, duplicate-delivery handling, storage, idempotency, and operational complexity without evidence that those costs are necessary.

## Current AWS facts relevant to the decision

These are AWS-documented facts reviewed on 2026-09-10, not OpsLens measurements:

| Fact | Architectural implication |
| --- | --- |
| API Gateway HTTP API maximum integration timeout is 30 seconds and cannot be increased | synchronous HTTP API must fit comfortably inside that bound |
| Regional REST API integration timeout can be increased beyond the default 29-second ceiling, with quota implications | longer REST timeout exists but does not itself justify synchronous coupling |
| Lambda timeout can be configured up to 900 seconds | Lambda compute lifetime is not the same as ingress lifetime |
| Lambda reserved concurrency caps function concurrency and can be set to zero | useful narrow compute/admission control, not a full product quota |
| SQS standard queues are at least once | async worker must be idempotent |
| API Gateway REST usage-plan quotas/throttles are best effort | cannot be the only denial-of-wallet control |
| Athena workgroups support a bytes-scanned cutoff | query-level cost amplification can remain bounded independently |
| Converse requires `bedrock:InvokeModel` | model execution permission stays a separate responsibility |
| Knowledge Base retrieval uses `bedrock:Retrieve` | retrieval and generation permissions can remain separate |

Official references:

- https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-quotas.html
- https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-execution-service-limits-table.html
- https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html
- https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html
- https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html
- https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html
- https://docs.aws.amazon.com/athena/latest/APIReference/API_WorkGroupConfiguration.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/kb-how-retrieval.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html

## Candidate matrix

| Candidate | Gate 19.1 disposition | Reason |
| --- | --- | --- |
| HTTP API + Lambda synchronous | measurement-gated | smallest API surface, but fixed 30s integration ceiling |
| Regional REST API + Lambda synchronous | measurement-gated | can extend timeout, but that is not evidence a long sync request is good product design |
| API ingress + submit/queue/worker/result lifecycle | leading hypothesis | strongest backpressure/failure-isolation option if variability is material |
| Lambda Function URL | not favored | minimal ingress but insufficient by itself for the explicit public product/abuse boundary |
| ECS/Fargate/ALB | deferred | no current requirement for standing container/server process |
| AgentCore as public runtime | deferred | prior evidence retained it as an optional experiment, not default runtime |

## Threat and abuse model

The frozen model covers at minimum:

```text
oversized request
malformed JSON
repository URL abuse
SSRF-style source redirection
repository enumeration
large repository amplification
dependency explosion
GitHub API abuse
prompt injection from repository content
retrieval poisoning
model amplification
Athena scan amplification
Bedrock token amplification
retry amplification
concurrency exhaustion
cost denial-of-wallet
result tampering
identity/replay
telemetry data leakage
```

Existing controls already provide meaningful protection for request size/shape, canonical GitHub-only coordinates, no redirects, no repository execution, one inert file, package/candidate bounds, deterministic evidence authority, and content-minimized telemetry. Public identity/rate/global quota/concurrency/aggregate model-call budgets remain intentionally unresolved until a runtime topology exists.

## IAM responsibility boundary

No runtime role is created.

The future permission decomposition is:

```text
public ingress
repository acquisition
Athena structured retrieval
Bedrock Knowledge Base retrieval
Bedrock model invocation
result persistence (only if justified)
telemetry emission
queue/job coordination (only if async is selected)
```

Repository acquisition currently needs outbound HTTPS but no AWS API action. Athena and Bedrock permissions stay separate. Persistence and queue permissions remain unauthorized because no corresponding runtime responsibility has been selected.

## Cost and abuse measurement contract

The first real runtime experiment must measure rather than infer from unrelated labs:

```text
cost/request
Bedrock input/output tokens
Athena bytes scanned
GitHub request count
runtime duration
queue operations, if applicable
result storage, if applicable
retries
throttles
rejected requests
concurrency
```

No monthly TCO is produced in Gate 19.1.

## Observability contract

Required content-minimized signals:

```text
request_id
trace_id
workload_id
repository_identity_hash
stage
duration_ms
outcome
failure_category
provider/service call count
Bedrock token counts when available
Athena bytes scanned
retry count
throttle count
admission rejection reason
cost attribution identifier when available
```

Forbidden by default:

```text
full prompt
source code
repository file contents
full model response
sensitive tokens
credentials
raw user payload
```

## Disable/recovery semantics

Before a deploy, the selected runtime must prove the exact scope of each applicable control:

```text
ingress disable
new-job admission disable
queue consumer pause
model invocation disable
Athena execution disable
background ingestion pause
```

Phase 17 already proves only the last item for exactly three scheduled ingestion resources. It is not a global kill switch.

## Gate 19.2 minimum experiment

The next experiment is intentionally non-public.

Compose a representative runner that reaches an admitted final product result and records:

```text
end-to-end duration
per-stage duration
GitHub call count
Athena query count + bytes scanned when used
Bedrock Retrieve count + latency when used
Bedrock model calls + tokens + latency when used
retry/throttle counts
serialized result bytes
```

Decision rule:

```text
SYNC
  only if the complete bounded workload comfortably fits the selected
  synchronous ingress envelope under representative upper-bound/p95 tests

ASYNC
  if latency variability, backpressure, failure isolation, or timeout evidence
  makes synchronous coupling unsafe

otherwise
  DEFERRED_PENDING_MEASUREMENT
```

If real AWS calls are needed to collect these measurements, stop at the human boundary and provide the exact manual commands. Gate 19.1 authorizes no AWS mutation and no model/capability execution.

## AIP-C01 learning

This gate directly exercises architectural reasoning behind API integration, sync/async patterns, least-privilege IAM, rate/concurrency controls, monitoring, cost optimization, and troubleshooting.

The reusable rule is:

> Select the integration pattern from workload latency, failure, consistency, and backpressure needs; do not select an AWS service just because it is an exam topic.
