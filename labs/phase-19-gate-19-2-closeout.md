# Phase 19 Gate 19.2 — Representative Workload Measurement Closeout

_Status: CLOSEOUT IN REVIEW_

_Source protected main: `e45ba419414e6dd77ecad68f4d2312e9123c2223`_

_Source issue: #295_

_Closeout issue: #346_

## Decision

Gate 19.2 selects the interaction pattern:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

This is an evidence-backed interaction-pattern decision only. It does **not** select API Gateway, Lambda, SQS, DynamoDB, Step Functions, ECS/Fargate, AgentCore, or any other concrete AWS service topology.

No public endpoint, AWS resource, IAM role/policy, queue, worker, or result store is authorized by this closeout.

## Canonical live evidence

The human-operated non-public representative run produced:

```text
artifact: labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
artifact SHA-256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id: gate19.2-live-20260911T131121Z
OpsLens commit: e45ba419414e6dd77ecad68f4d2312e9123c2223
outcome: SUCCESS
```

The persisted-artifact verifier returned `PASS` with `topology_evaluation_allowed=true`.

Canonical closeout evidence:

```text
labs/evidence/phase-19-gate-19-2-closeout-v1.json
```

## Measured workload

The exact retained representative workload completed in:

```text
end_to_end_duration_ms = 17748
serialized_result_bytes = 5285
```

Stage measurements:

| Stage | Measured ms | Share of E2E |
| --- | ---: | ---: |
| public request admission | 0 | 0.00% |
| repository acquisition | 1,159 | 6.53% |
| dependency evidence | 540 | 3.04% |
| vulnerability correlation | 2,888 | 16.27% |
| risk prioritization | 7 | 0.04% |
| structured evidence | 9 | 0.05% |
| semantic evidence | 4,160 | 23.44% |
| model reasoning | 8,938 | 50.36% |
| result admission | 29 | 0.16% |

The two Bedrock-facing stages account for `13,098 ms`, or `73.80%` of the measured end-to-end duration.

Provider measurements:

```text
GitHub physical HTTP requests           4       MEASURED
Athena query count                      0       NOT_APPLICABLE
Athena bytes scanned                    0       NOT_APPLICABLE
Bedrock Retrieve count                  1       MEASURED
Bedrock Retrieve client elapsed ms      4148    MEASURED
Bedrock model call count                1       MEASURED
Bedrock input tokens                    5936    MEASURED
Bedrock output tokens                   408     MEASURED
Bedrock model client elapsed ms         8901    MEASURED
Bedrock provider latency ms             7772    MEASURED
retry count                             0       MEASURED
throttle count                          0       UNMEASURED
```

`UNMEASURED != zero` remains mandatory. The numeric throttle counter does not establish throttle measurement authority.

## Why SYNC is not selected

The successful measured baseline of `17,748 ms` does not itself exceed the retained 30-second HTTP API integration envelope. Therefore this closeout does **not** claim that the successful run timed out.

The deciding factor is retry safety plus provider-latency coupling.

Using only measured client elapsed values to construct explicit derived retry-safety scenarios:

```text
MEASURED baseline                                              17,748 ms
DERIVED + one model-equivalent client attempt                  26,649 ms
DERIVED + one Retrieve-equivalent + one model-equivalent       30,797 ms
retained HTTP API reference envelope                           30,000 ms
```

The derived `30,797 ms` scenario crosses that envelope before adding ingress/runtime overhead. The retained Bedrock clients also intentionally use bounded retry policies. A synchronous ingress would therefore couple the external request lifetime directly to provider retry/failure behavior.

These values preserve the evidence distinction:

```text
17,748 ms  = MEASURED
26,649 ms  = DERIVED
30,797 ms  = DERIVED
```

No derived scenario is relabeled as measured evidence.

## Why ASYNC is selected

`ASYNC_SUBMIT_STATUS_RESULT` provides the stronger boundary for the measured workload because it separates:

- request admission from provider execution latency;
- client connection lifetime from Bedrock retry/failure behavior;
- job backpressure from ingress concurrency;
- bounded job retry from user-facing HTTP timeout;
- result publication from long-running provider work.

This decision is based on the actual measured composition, where semantic evidence and model reasoning dominate the request lifetime, not on a preference for any particular AWS service.

## Safety invariants

The admitted live artifact preserves:

```text
public_endpoint_count                         0
new_aws_resource_count                        0
new_iam_role_policy_count                     0
third_party_repository_code_execution_count   0
```

PR #89 remains untouched.

The retained principles remain:

```text
Agents reason. Code verifies evidence.
READ, NEVER EXECUTE third-party repository code.
Repository Risk != Runtime Exposure.
retrieved content != instruction authority
model proposal != authorization
tool/protocol success != business truth
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
```

## Next boundary

The next Gate may now freeze the smallest concrete async runtime design, including ingress/job/result lifecycle, least-privilege runtime IAM, idempotency, backpressure, retries, abuse controls, cost attribution, observability, and disable/recovery semantics.

That next gate must still design before deploying. Gate 19.2 does not authorize runtime infrastructure creation.
