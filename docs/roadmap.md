# OpsLens — Incremental Roadmap

_Last updated: 2026-09-11_

The roadmap is evidence-gated. A later phase does not invalidate earlier authority boundaries, and certification topics do not automatically become product requirements.

## Phase status

```text
Phase 0   AWS Foundation                                      COMPLETE
Phase 1   EPSS Vertical Slice                                 COMPLETE
Phase 2   Threat Intelligence Data Lake                       COMPLETE
Phase 3   Vulnerability Correlation Engine                    COMPLETE
Phase 4   Repository Intelligence                             COMPLETE
Phase 5   Risk Prioritization Engine                          COMPLETE
Phase 6   Semantic Query Layer                                COMPLETE
Phase 7   Knowledge Retrieval with Bedrock                    COMPLETE
Phase 8   Hybrid Retrieval                                    COMPLETE
Phase 9   Public Analyze Your Repository application boundary COMPLETE
Phase 10  Observability & Operational Excellence              COMPLETE
Phase 11  Single-Agent Baseline                               COMPLETE
Phase 12  Multi-Agent Architecture                            COMPLETE
Phase 13  MCP                                                 COMPLETE
Phase 14  Amazon Bedrock AgentCore                            COMPLETE
Phase 15  A2A                                                 COMPLETE
Phase 16  Runtime Exposure with Amazon Inspector              COMPLETE
Phase 17  Security Hardening                                  COMPLETE
Phase 18  Evaluation, Cost & Portfolio Readiness              COMPLETE
Phase 19  Bounded Public Runtime & Productization             IN PROGRESS
```

### Retained Phase 17 security lineage

**Gate 17.1** established the evidence-first threat/control-gap inventory. **Gate 17.2** hardened CI/CD and workflow authority and introduced the retained `Repository security invariants` protected-main context. Later Phase 17 gates added dependency/code scanning, adversarial regression, telemetry hardening, and the bounded scheduled-ingestion pause without weakening those controls.

Phase 18 was protected-squash-merged through PR #290 at `feca774535b7d83f57c26f4e9fe7da71ce268f0f`. Its historical pre-merge closeout artifacts remain immutable evidence.

Gate 19.1 was protected-squash-merged through PR #292 at `ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1` after exact-head validation at `484e2b85fc1996b2419b4057c2cf585ab1f675a1`.

Gate 19.2 live-measurement support was incrementally merged through PRs including #339 and the NVD admission fix #345. The successful human-operated representative measurement was executed from protected main `e45ba419414e6dd77ecad68f4d2312e9123c2223`. Closeout is tracked by issue #346 and draft PR #347.

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work. Phase 19 does not rebase, merge, modify, or depend on it.

## Phase 19 — Bounded Public Runtime & Productization

### Goal

Move from the retained Phase 9 application boundary toward the smallest safe, measurable public product surface without selecting infrastructure before the workload justifies it.

Retained starting point:

```text
untrusted request
 -> governed repository admission/evidence
 -> bounded semantic planning
 -> deterministic hybrid route admission
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

Phase 19 must preserve:

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

### Gate 19.1 — Public Runtime Hypothesis & Launch Contract — COMPLETE

Gate 19.1 froze the first representative public workload, identified the composition gaps, and defined the experiment required before runtime interaction-pattern selection.

Retained workload identity:

```text
public-analysis-workload:v1
```

Historical Gate 19.1 decision:

```text
DEFERRED_PENDING_MEASUREMENT
```

Leading hypothesis at that time:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

Gate 19.1 deliberately did not create SQS, result storage, workers, an async API, public compute, or runtime IAM.

Completed Gate 19.1 outputs include the `PublicAnalysisAdmissionHandoff` pipeline inventory, frozen request/repository/evidence/response workload contract, runtime candidate matrix, public threat/abuse model, responsibility-to-permission IAM matrix, cost/abuse and content-minimized observability contracts, bounded disable/recovery requirements, deterministic verifier/read-only CI, and the exact Gate 19.2 experiment boundary.

### Gate 19.2 — Representative Workload Measurement — CLOSEOUT IN REVIEW

Purpose: close the whole-workload measurements Gate 19.1 correctly classified as `UNMEASURED` and select exactly one interaction pattern without deploying a public runtime.

#### Representative execution

The non-public representative execution uses the exact nine-stage workload:

```text
public request admission
 -> immutable repository acquisition
 -> dependency evidence
 -> deterministic vulnerability correlation
 -> deterministic risk prioritization
 -> structured evidence
 -> semantic evidence
 -> bounded model reasoning
 -> deterministic final result admission
```

The composed runner reuses retained OpsLens authority:

```text
repository evidence
 -> retained GHSA applicability
 -> retained NVD enrichment
 -> retained KEV enrichment
 -> retained EPSS enrichment
 -> RepositoryAnalysisResult
 -> Risk Policy v1
 -> deterministic structured evidence
 -> bounded Bedrock Knowledge Base Retrieve
 -> deterministic hybrid evidence assembly
 -> bounded Bedrock hybrid synthesis
 -> deterministic final result admission
```

The measurement surface includes:

```text
end-to-end duration
per-stage duration
GitHub physical HTTP request count
Athena query count + bytes scanned
Bedrock Retrieve count
Bedrock Retrieve client elapsed milliseconds
Bedrock model call count + input/output tokens
Bedrock model client elapsed milliseconds
Bedrock provider latency milliseconds
retry count
throttle count
serialized admitted-result bytes
```

Provider measurement authority remains explicit and separate from numeric values. A zero counter does not prove that a provider dimension was observed.

For the retained direct structured-evidence path in `public-analysis-workload:v1`:

```text
athena_query_count:   NOT_APPLICABLE
athena_bytes_scanned: NOT_APPLICABLE
throttle_count:       UNMEASURED
```

#### Representative input

The admitted representative anchor is:

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

This identity freezes reproducibility only. It does not prove repository runtime exposure.

The historical machine-readable Gate 19.2 measurement-contract artifact intentionally preserves the earlier pre-live slice and its then-frozen Requests anchor. It is not rewritten post hoc.

#### Human live measurement — COMPLETE

The human-only run was executed exactly once from protected main `e45ba419414e6dd77ecad68f4d2312e9123c2223`.

Canonical live evidence:

```text
artifact: labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
artifact SHA-256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id: gate19.2-live-20260911T131121Z
outcome: SUCCESS
```

Measured values:

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

Measured stage concentration:

```text
semantic evidence   4160 ms
model reasoning     8938 ms
combined           13098 ms / 73.80% of end-to-end
```

The persisted-artifact verifier passed and admitted the evidence for topology evaluation.

#### Gate 19.2 decision

Selected interaction pattern:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

The measured success path itself completed below the retained 30-second HTTP API reference envelope. Gate 19.2 therefore does not claim a measured timeout.

The async decision is based on provider-latency coupling, retry safety, backpressure, and failure isolation. Explicit `DERIVED` retry-safety scenarios are kept separate from measurement:

```text
baseline measured E2E                                      17748 ms   MEASURED
+ one additional model-equivalent client elapsed           26649 ms   DERIVED
+ one additional Retrieve-equivalent and model-equivalent  30797 ms   DERIVED
reference synchronous envelope                             30000 ms   RETAINED FACT
```

The derived scenarios are not additional live measurements. They show why the observed success path does not provide enough synchronous safety margin once provider retry/failure behavior is considered.

Canonical closeout evidence:

```text
labs/phase-19-gate-19-2-closeout.md
labs/evidence/phase-19-gate-19-2-closeout-v1.json
scripts/verify_phase19_gate19_2_closeout.py
```

Current Gate 19.2 authority boundary remains:

```text
public endpoints:       0
new AWS resources:      0
new IAM roles/policies: 0
third-party code exec:  0
PR #89 modifications:  0
```

Gate 19.2 selects an interaction pattern, not a concrete AWS topology.

### Next Phase 19 gate — concrete async topology contract

After Gate 19.2 is protected-merged and post-merge verified, the next gate should freeze the smallest concrete async ingress/job/result architecture before any deployment.

Required design authority should include:

```text
ingress admission + public identity/rate boundary
job identity + idempotency + duplicate-delivery semantics
retry ownership + backpressure
worker responsibility + failure isolation
status/result lifecycle + retention
least-privilege IAM by responsibility
concurrency + model-call + cost-amplification controls
content-minimized observability
disable/recovery boundaries
Terraform/resource plan only after topology review
```

Candidate AWS services remain **unselected**. The next gate must compare only the minimum credible combinations needed to implement the selected async interaction pattern. It must not introduce API Gateway, Lambda, SQS, DynamoDB, Step Functions, ECS/Fargate, WAF, AgentCore, or another service simply because the service is plausible or appears in AIP-C01.

```text
AIP-C01 topic != product requirement
```
