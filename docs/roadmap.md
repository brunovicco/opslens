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

The latest Gate 19.2 human-live CLI increment was merged through PR #339 from exact head `a64995bed02aeadb0b8b1ed1cf4ae85975e552f5`, producing protected-main commit `765ecf528f0b7e8dcabb31b40416061ba719dd58`.

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

Gate 19.1 froze the first representative public workload, identified the composition gaps, and defined the experiment required before runtime topology selection.

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

Purpose: close the measurements that Gate 19.1 correctly classifies as `UNMEASURED` before selecting a public runtime.

#### Pre-live implementation — COMPLETE ENOUGH FOR HUMAN EXECUTION

The non-public representative execution is composed through the exact nine-stage workload:

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

Provider measurement authority is explicit and separate from numeric values. A zero counter does not prove that a provider dimension was observed.

For the retained direct structured-evidence path in `public-analysis-workload:v1`:

```text
athena_query_count:   NOT_APPLICABLE
athena_bytes_scanned: NOT_APPLICABLE
```

`throttle_count` remains `UNMEASURED` unless explicit provider throttle evidence is introduced. Missing instrumentation must never become measured zero.

#### Representative input — CURRENT

The earlier Requests candidate was superseded during read-only pre-live evidence preparation. The current admitted representative anchor is:

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

The historical machine-readable Gate 19.2 measurement-contract artifact intentionally preserves the earlier pre-live slice and its then-frozen Requests anchor. Do not rewrite historical evidence to manufacture post-hoc authority; the current representative coordinates are carried by later threat-admission/preload records and the human live-measurement runbook.

#### Human-run CLI — MERGED

Issue #338 / PR #339 added the fail-closed human-run-only live composition root and artifact path. The driver:

- validates frozen repository/model coordinates before provider execution;
- materializes exact threat authority before measured request-time stages;
- composes measured GitHub transport, direct bounded Bedrock Retrieve, bounded hybrid synthesis, and a monotonic measurement clock;
- invokes the representative workload exactly once;
- builds the live artifact only from admitted execution evidence and explicit run metadata;
- performs byte-exact artifact admission;
- publishes the artifact atomically without overwriting an existing file;
- creates no public endpoint, AWS resource, or IAM authority.

Human entrypoint:

```text
scripts/run_phase19_gate19_2_live_measurement.py
```

Operator runbook:

```text
labs/phase-19-gate-19-2-human-live-measurement-runbook.md
```

Current Gate 19.2 authority boundary:

```text
public endpoints:       0
new AWS resources:      0
new IAM roles/policies: 0
third-party code exec:  0
PR #89 modifications:  0
```

#### Gate 19.2 current boundary — HUMAN LIVE MEASUREMENT

Autonomous repository implementation stops here. The next step is the first point at which live GitHub/AWS/Bedrock execution is intentionally required, and that execution belongs to the human operator.

Required remaining sequence:

1. Check out and verify the exact reviewed protected-main commit intended for the artifact.
2. Run the runbook pre-flight checks locally.
3. Confirm the intended existing AWS identity; missing permission is a stop condition, not authority to expand IAM.
4. Materialize the exact typed GHSA/NVD/KEV/EPSS authority through the retained read-only path before measurement.
5. Human-execute exactly one non-public representative workload using the retained GitHub + Bedrock adapters.
6. Capture `labs/evidence/phase-19-gate-19-2-live-measurement-v1.json` without overwriting prior evidence.
7. Preserve explicit `MEASURED`, `NOT_APPLICABLE`, and `UNMEASURED` semantics for every provider dimension.
8. Evaluate exactly one runtime decision: `SYNC`, `ASYNC`, or `DEFERRED_PENDING_MEASUREMENT`.

Decision rule:

```text
SYNC
  only if the complete bounded workload comfortably fits the selected
  synchronous ingress envelope under representative measured evidence

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
