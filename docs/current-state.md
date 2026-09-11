# OpsLens — Current State

_Last updated: 2026-09-11_

## Authoritative checkpoint

```text
protected main:
e45ba419414e6dd77ecad68f4d2312e9123c2223

Phase 18 — Evaluation, Cost & Portfolio Readiness
status: COMPLETE
protected closeout PR: #290

Phase 19 — Bounded Public Runtime & Productization
Gate 19.1 — Public Runtime Hypothesis & Launch Contract      COMPLETE
protected merge PR: #292
exact validated head: 484e2b85fc1996b2419b4057c2cf585ab1f675a1
original runtime decision: DEFERRED_PENDING_MEASUREMENT
leading hypothesis: ASYNC_SUBMIT_STATUS_RESULT

Gate 19.2 — Representative Workload Measurement              CLOSEOUT IN REVIEW
source protected main: e45ba419414e6dd77ecad68f4d2312e9123c2223
source issue: #295
closeout issue: #346
closeout PR: #347 (DRAFT)
selected interaction pattern: ASYNC_SUBMIT_STATUS_RESULT
concrete AWS topology selected: NO
```

Phases 0–18 remain complete. Gate 19.1 is complete and merged. Gate 19.2 has crossed its explicit human-only measurement boundary exactly once, persisted canonical live evidence, passed deterministic offline review, and selected the async submit/status/result interaction pattern. PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency.

## Retained Phase 17 security lineage

**Gate 17.1** established the evidence-first threat/control-gap inventory. **Gate 17.2** hardened CI/CD and workflow authority and introduced the retained `Repository security invariants` protected-main context. Later Phase 17 controls remain authoritative for dependency/code scanning, adversarial regression, telemetry minimization, and bounded scheduled-ingestion recovery. Phase 19 adds no exception to those controls.

## Phase 18 and Gate 19.1 protected history

Phase 18 was protected-squash-merged through PR #290 at `feca774535b7d83f57c26f4e9fe7da71ce268f0f`.

Gate 19.1 was then protected-squash-merged through PR #292 at `ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1`. Its exact final PR head `484e2b85fc1996b2419b4057c2cf585ab1f675a1` passed the retained exact-head validation chain before merge.

Historical artifacts retain the state they recorded when created. Current-facing documentation is synchronized separately; historical Phase 18/Gate 19.1 evidence and earlier Gate 19.2 measurement-contract evidence are not rewritten to look post-merge.

## Retained platform architecture

OpsLens retains one AWS `dev` environment in `us-east-1`, source-preserving threat intelligence, deterministic vulnerability applicability and repository correlation, Risk Policy v1, bounded semantic planning with compiler-owned Athena SQL, Amazon Bedrock Knowledge Bases with Amazon S3 Vectors, deterministic hybrid evidence composition, bounded Bedrock synthesis, agent/capability authority contracts, offline MCP/A2A interoperability, optional-lab AgentCore evidence, bounded Inspector read contracts, content-minimized observability, Phase 17 security/recovery controls, and the Phase 18 evaluation/cost/portfolio evidence chain.

Permanent boundaries remain:

```text
Agents reason. Code verifies evidence.
Not every question is a RAG problem.
Structured facts use structured retrieval.
No unrestricted text-to-SQL.
READ, NEVER EXECUTE third-party repository code.
Repository Risk != Runtime Exposure.
Intent classification != execution authority.
retrieved content != instruction authority
model proposal != authorization
tool/protocol success != business truth
historical evidence != standing authority
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
AIP-C01 topic != product requirement
```

## Retained public-analysis boundary

The protected-main public-analysis application path still stops before a public product runtime:

```text
untrusted JSON
 -> strict request admission
 -> validated GitHub coordinates
 -> immutable repository snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic dependency normalization
 -> bounded metadata-only semantic planning
 -> deterministic Phase 8 route admission
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

`execute_instrumented_public_analysis` emits bounded operational evidence for that retained protected-main path and still returns the handoff. There is no protected public HTTP endpoint, public application compute, or public result store.

Gate 19.2 composed a **non-public representative execution** downstream of the retained handoff solely to measure the complete bounded workload before runtime selection. That composition does not itself create public runtime authority.

## Gate 19.1 retained launch contract

Canonical machine-readable authority:

`labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`

Frozen workload identity:

```text
public-analysis-workload:v1
```

Gate 19.1 retained the runtime decision:

```text
DEFERRED_PENDING_MEASUREMENT
```

with leading design hypothesis:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

That historical decision remains valid as Gate 19.1 evidence. Gate 19.2 has now supplied the representative whole-workload evidence required to move beyond it.

## Gate 19.2 representative live evidence

The exact nine-stage non-public representative composition is:

```text
public_request_admission
repository_acquisition
dependency_evidence
vulnerability_correlation
risk_prioritization
structured_evidence
semantic_evidence
model_reasoning
result_admission
```

The composition reuses retained OpsLens authority rather than copying business truth. Repository applicability continues through the retained GHSA/NVD/KEV/EPSS chain; risk continues through Risk Policy v1; structured evidence is projected deterministically; semantic remediation evidence uses the retained bounded Knowledge Base Retrieve path; model reasoning uses the retained bounded hybrid synthesis path; and final result admission remains deterministic.

The human-operated run used source protected main `e45ba419414e6dd77ecad68f4d2312e9123c2223` and produced:

```text
artifact: labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
artifact SHA-256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id: gate19.2-live-20260911T131121Z
outcome: SUCCESS
```

The deterministic persisted-artifact reviewer passed with `topology_evaluation_allowed=true`.

Measured whole-workload evidence:

```text
end_to_end_duration_ms                  17748
serialized_result_bytes                 5285
GitHub physical HTTP requests              4     MEASURED
Athena query count                         0     NOT_APPLICABLE
Athena bytes scanned                       0     NOT_APPLICABLE
Bedrock Retrieve count                     1     MEASURED
Bedrock Retrieve client elapsed ms      4148     MEASURED
Bedrock model call count                   1     MEASURED
Bedrock input tokens                    5936     MEASURED
Bedrock output tokens                    408     MEASURED
Bedrock model client elapsed ms         8901     MEASURED
Bedrock provider latency ms             7772     MEASURED
retry count                                0     MEASURED
throttle count                             0     UNMEASURED
```

Stage concentration:

```text
semantic_evidence = 4160 ms
model_reasoning   = 8938 ms
combined          = 13098 ms / 73.80% of measured end-to-end
```

`UNMEASURED != zero` remains mandatory. The numeric throttle counter does not establish throttle measurement authority. Athena request-time metrics remain `NOT_APPLICABLE` for the retained direct structured-evidence path.

## Gate 19.2 interaction-pattern decision

Gate 19.2 selects:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

The successful baseline of `17,748 ms` did not exceed the retained 30-second HTTP API reference envelope. The closeout therefore does **not** claim a measured timeout.

The decision is based on provider-latency coupling, retry safety, backpressure, and failure isolation. Explicit derived scenarios use the measured Bedrock client latencies without relabeling them as measurements:

```text
baseline measured E2E                                      17748 ms   MEASURED
+ one additional model-equivalent client elapsed           26649 ms   DERIVED
+ one additional Retrieve-equivalent and model-equivalent  30797 ms   DERIVED
reference synchronous envelope                             30000 ms   RETAINED FACT
```

Those derived scenarios are not additional live executions. They demonstrate that the observed success path leaves insufficient safety margin for a synchronous public interaction pattern once retry/failure behavior is considered.

Canonical closeout evidence:

```text
labs/phase-19-gate-19-2-closeout.md
labs/evidence/phase-19-gate-19-2-closeout-v1.json
scripts/verify_phase19_gate19_2_closeout.py
```

## Current representative anchor

The admitted representative anchor remains:

```text
repository:      openedx/mockprock
repository URL:  https://github.com/openedx/mockprock
commit/ref:      18c954d8604df4740c829ba17fa2f3640b92b900
evidence file:  uv.lock
dependency:     webob==1.8.10
GHSA anchor:    GHSA-6hx8-3wjj-gr8g
CVE anchor:     CVE-2026-54770
affected range: < 1.8.11
patched from:   1.8.11
```

Frozen threat coordinates:

```text
NVD observations: 1
KEV snapshot:     2026-09-10
KEV membership:   absent in that complete snapshot
EPSS snapshot:    2026-09-10
EPSS score:       0.00339
EPSS percentile:  0.26988
```

These coordinates establish reproducibility, not repository runtime exposure.

## Retained live provider coordinates

The human run reused only existing resources:

```text
region:             us-east-1
knowledge base id:  BTVJ2PBR2A
data source id:     IEL1LBE026
source/data bucket: opslens-dev-data-487757851499-us-east-1
synthesis model:    us.anthropic.claude-haiku-4-5-20251001-v1:0
```

No new Knowledge Base, vector index, model deployment, IAM role/policy, endpoint, bucket, data source, queue, worker, or result store was created or authorized by Gate 19.2.

## Gate 19.2 safety boundary

```text
public endpoints:       0
new AWS resources:      0
new IAM roles/policies: 0
third-party code exec:  0
PR #89 modifications:  0
```

The persisted live artifact records all four counters as exactly zero.

## Validation state

PR #345 fixed the NVD timestamp-admission contract and was protected-merged into `main` as `e45ba419414e6dd77ecad68f4d2312e9123c2223`. From that exact commit, the human pre-flight passed lockfile validation, Ruff, Pyright, 189 public-analysis unit tests, and the Gate 19.2 measurement-contract verifier.

The deterministic pre-live fail-closed test rejected a non-frozen repository ref before provider client construction and created no artifact. The single human live execution then succeeded, and the offline persisted-artifact verifier passed.

Draft PR #347 now persists the exact artifact bytes, the closeout decision, the deterministic closeout verifier, CI coverage, and current-facing documentation. Gate 19.2 is not considered protected-merged until that PR lands and post-merge verification completes.

## Next checkpoint — concrete async topology freeze

The next Phase 19 boundary is no longer another representative measurement. It is to freeze the smallest concrete async ingress/job/result architecture consistent with the selected interaction pattern.

That next gate must define, before deployment:

1. ingress admission and public identity/rate/abuse boundaries;
2. job identity, idempotency, retry ownership, and duplicate-delivery semantics;
3. worker responsibility and failure isolation;
4. result persistence/status lifecycle and retention;
5. least-privilege IAM responsibility decomposition;
6. concurrency, model-call, and cost-amplification controls;
7. observability, disable/recovery, and kill boundaries;
8. exact Terraform/resource plan only after the topology contract is reviewed.

Gate 19.2 does **not** authorize API Gateway, Lambda, SQS, DynamoDB, Step Functions, ECS/Fargate, WAF, AgentCore, or any other concrete AWS service merely because the interaction pattern is async.
