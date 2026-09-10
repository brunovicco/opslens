# OpsLens — Incremental Roadmap

_Last updated: 2026-09-10_

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
configured limit != measured utilization
```

### Gate 19.1 — Public Runtime Hypothesis & Launch Contract — COMPLETE

Gate 19.1 froze the first representative public workload, identified the actual composition gaps, and defined the experiment required before runtime topology selection.

Retained workload identity:

```text
public-analysis-workload:v1
```

Retained runtime decision:

```text
DEFERRED_PENDING_MEASUREMENT
```

Leading hypothesis:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

The hypothesis remains non-authoritative. Gate 19.1 did not create SQS, result storage, workers, an async API, public compute, or runtime IAM.

Completed Gate 19.1 outputs include the `PublicAnalysisAdmissionHandoff` pipeline inventory, frozen request/repository/evidence/response workload contract, runtime candidate matrix, public threat/abuse model, responsibility-to-permission IAM matrix, cost/abuse and content-minimized observability contracts, bounded disable/recovery requirements, deterministic verifier/read-only CI, and the exact Gate 19.2 experiment boundary.

### Gate 19.2 — Representative Workload Measurement — IN PROGRESS

Issue: #295. Draft implementation PR: #297.

Purpose: close the measurements that Gate 19.1 correctly classifies as `UNMEASURED` before selecting a public runtime.

The representative experiment remains non-public and must compose or invoke:

```text
public request admission
 -> immutable repository acquisition
 -> dependency evidence
 -> deterministic vulnerability correlation
 -> deterministic risk prioritization
 -> structured evidence when required
 -> semantic evidence when required
 -> bounded model reasoning when required
 -> deterministic final result admission
```

The first implementation slice freezes a provider-neutral measurement harness with the exact ordered stage set and exact resource-accounting contract. It measures:

```text
end-to-end duration
per-stage duration
GitHub HTTP request count
Athena query count + bytes scanned
Bedrock Retrieve count
Bedrock model call count + input/output tokens
retry count
throttle count
serialized admitted-result bytes
```

The measurement layer must not infer usage. Negative counters, stage reordering, incomplete plans, aggregate drift, empty serialized results, or invalid monotonic-clock evidence fail closed.

Current Gate 19.2 authority boundary:

```text
public endpoints:       0
new AWS resources:      0
new IAM roles/policies: 0
third-party code exec:  0
PR #89 modifications:  0
```

Live AWS/model execution remains a human execution boundary.

#### Gate 19.2 next slices

1. Adapt retained repository-intelligence and Risk Policy capabilities into the representative non-public composition without copying business truth into the measurement layer.
2. Adapt the retained structured and semantic retrieval boundaries while preserving route/evidence authority.
3. Adapt bounded synthesis and deterministic result admission.
4. Add deterministic success/failure coverage and exact provider/resource accounting for the composed runner.
5. Prepare and human-execute the smallest reproducible non-public representative live measurement.
6. Record the measurement artifact and decide exactly one of `SYNC`, `ASYNC`, or `DEFERRED_PENDING_MEASUREMENT`.

Decision rule:

```text
SYNC
  only if the complete bounded workload comfortably fits the selected
  synchronous ingress envelope under representative upper-bound/p95 tests

ASYNC
  if latency variability, backpressure, failure isolation, retry safety,
  or timeout evidence makes synchronous coupling unsafe

otherwise
  DEFERRED_PENDING_MEASUREMENT
```

Gate 19.2 must not create a public endpoint merely to benchmark the application workload.

### Later Phase 19 gates — not yet authorized

The exact post-19.2 gates depend on the measured runtime decision. Only after `SYNC` or `ASYNC` is evidence-backed should Phase 19 freeze concrete ingress/compute, least-privilege runtime IAM, abuse controls, persistence/queue topology if applicable, deployment Terraform, operational recovery controls, and a bounded public launch experiment.

Do not introduce API Gateway, Lambda Function URLs, SQS, DynamoDB, Step Functions, ECS/Fargate, WAF, AgentCore, or another service solely because it is a plausible public architecture or appears in AIP-C01.

```text
AIP-C01 topic != product requirement
```
