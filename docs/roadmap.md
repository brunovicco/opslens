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

Phase 18 was protected-squash-merged through PR #290 at `feca774535b7d83f57c26f4e9fe7da71ce268f0f`. Its historical pre-merge closeout artifacts remain immutable evidence.

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

### Gate 19.1 — Public Runtime Hypothesis & Launch Contract — IN PROGRESS

Purpose: freeze the first representative public workload, identify actual composition gaps, and define the experiment that can justify runtime topology before creating AWS resources.

Frozen workload identity:

```text
public-analysis-workload:v1
```

Current runtime decision:

```text
DEFERRED_PENDING_MEASUREMENT
```

Leading hypothesis:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

The hypothesis is not authorization to create SQS, result storage, workers, or an async API.

Gate 19.1 deliverables:

- exact post-Phase-18 repository checkpoint;
- current-facing documentation synchronization without rewriting historical Phase 18 evidence;
- real `PublicAnalysisAdmissionHandoff` pipeline inventory;
- frozen request/repository/evidence/response workload contract;
- explicit `SYNC | ASYNC | DEFERRED_PENDING_MEASUREMENT` decision;
- runtime candidate matrix grounded in current AWS documentation;
- public threat/abuse model;
- responsibility-to-permission IAM matrix with no role creation;
- cost/abuse measurement contract;
- content-minimized observability contract;
- narrowly scoped disable/recovery requirements;
- deterministic artifact verifier and read-only CI;
- exact Gate 19.2 experiment boundary.

Gate 19.1 AWS boundary:

```text
AWS mutations:          0
IAM mutations:          0
new AWS resources:      0
model invocations:      0
capability executions:  0
public endpoints:       0
```

Exit criteria:

1. `public-analysis-workload:v1` is versioned and deterministic where evidence exists.
2. Missing whole-request limits remain explicit `UNMEASURED` rather than invented.
3. The retained public path and all disconnected downstream capabilities are separately identified.
4. Runtime selection is explicit and evidence-bound.
5. Threat/abuse, IAM responsibility, cost, observability, retry/idempotency, and recovery contracts are frozen.
6. Historical Phase 18 closeout evidence remains unchanged.
7. Gate-specific read-only verification passes on the exact PR head.
8. No public runtime or runtime IAM exists.
9. PR #89 remains untouched.
10. The smallest authorized Gate 19.2 experiment is explicit.

### Gate 19.2 — Representative Workload Measurement — PENDING

Purpose: close the measurements that Gate 19.1 correctly classifies as `UNMEASURED` before selecting a public runtime.

The experiment must be non-public first and compose or invoke the representative product stages:

```text
public-analysis request contract
 -> immutable repository acquisition
 -> deterministic vulnerability/risk result
 -> required structured/semantic evidence
 -> bounded synthesis where authorized
 -> deterministic final result admission
```

Measure at minimum:

```text
end-to-end duration
per-stage duration
GitHub request count
Athena query count + bytes scanned when used
Bedrock Retrieve count + latency when used
Bedrock model calls + input/output tokens + latency when used
retry/throttle count by provider
serialized result bytes
```

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

Live AWS/model execution, if required by this measurement, remains a human execution boundary. Gate 19.2 must not create a public endpoint merely to benchmark the application workload.

### Later Phase 19 gates — not yet authorized

The exact post-19.2 gates depend on the measured runtime decision. Only after `SYNC` or `ASYNC` is evidence-backed should Phase 19 freeze concrete ingress/compute, least-privilege runtime IAM, abuse controls, persistence/queue topology if applicable, deployment Terraform, operational recovery controls, and a bounded public launch experiment.

Do not introduce API Gateway, Lambda Function URLs, SQS, DynamoDB, Step Functions, ECS/Fargate, WAF, AgentCore, or another service solely because it is a plausible public architecture or appears in AIP-C01.

```text
AIP-C01 topic != product requirement
```
