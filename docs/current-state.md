# OpsLens — Current State

_Last updated: 2026-09-10_

## Authoritative checkpoint

```text
protected main:
ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1

Phase 18 — Evaluation, Cost & Portfolio Readiness
status: COMPLETE
protected closeout PR: #290

Phase 19 — Bounded Public Runtime & Productization
Gate 19.1 — Public Runtime Hypothesis & Launch Contract      COMPLETE
protected merge PR: #292
exact validated head: 484e2b85fc1996b2419b4057c2cf585ab1f675a1
runtime decision: DEFERRED_PENDING_MEASUREMENT
leading hypothesis: ASYNC_SUBMIT_STATUS_RESULT

Gate 19.2 — Representative Workload Measurement              IN PROGRESS
issue: #295
draft PR: #297
branch: feat/phase19-gate19-2-representative-workload-measurement
```

Phases 0–18 remain complete. Gate 19.1 is complete and merged. Gate 19.2 is the active engineering boundary. PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency.

## Retained Phase 17 security lineage

**Gate 17.1** established the evidence-first threat/control-gap inventory. **Gate 17.2** hardened CI/CD and workflow authority and introduced the retained `Repository security invariants` protected-main context. Later Phase 17 controls remain authoritative for dependency/code scanning, adversarial regression, telemetry minimization, and bounded scheduled-ingestion recovery. Phase 19 adds no exception to those controls.

## Phase 18 and Gate 19.1 protected history

Phase 18 was protected-squash-merged through PR #290 at `feca774535b7d83f57c26f4e9fe7da71ce268f0f`.

Gate 19.1 was then protected-squash-merged through PR #292 at `ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1`. Its exact final PR head `484e2b85fc1996b2419b4057c2cf585ab1f675a1` passed the retained exact-head validation chain before merge.

Historical artifacts retain the state they recorded when created. Current-facing documentation is synchronized separately; historical Phase 18/Gate 19.1 evidence is not rewritten to look post-merge.

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

The retained public-analysis application path is real but still stops before a public product runtime:

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

`execute_instrumented_public_analysis` emits bounded operational evidence for the same path and still returns the handoff. There is no retained public HTTP endpoint, public application compute, final public product result, or public result store.

Important adjacent capabilities already exist but are not yet composed downstream of that handoff into one public workload:

```text
deterministic vulnerability correlation
NVD/CVSS + KEV + EPSS enrichment
Risk Policy v1
bounded Athena structured retrieval
Bedrock Knowledge Base Retrieve
bounded grounded/hybrid synthesis
capability execution/result admission
```

Therefore:

```text
rich retained capabilities != executable public product workload
```

## Gate 19.1 retained launch contract

Canonical machine-readable authority:

`labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`

Frozen workload identity:

```text
public-analysis-workload:v1
```

The workload keeps public GitHub only, one repository/request, a 2,048-byte request body limit, a 256-character repository URL limit, immutable resolved commit identity, inert `uv.lock` as the only current repository file read, a 5,000 dependency-record bound, and third-party code execution forbidden.

The retained runtime decision is:

```text
DEFERRED_PENDING_MEASUREMENT
```

with leading design hypothesis:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

That hypothesis is not runtime authority. A concrete topology must follow representative whole-workload evidence.

## Gate 19.2 active implementation

Gate 19.2 closes the whole-request measurements that Gate 19.1 correctly left `UNMEASURED`.

The first implementation slice introduces a provider-neutral, non-public measurement contract and harness. The contract requires the exact ordered representative stages:

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

The harness records only concrete execution observations:

```text
end-to-end duration
per-stage duration
GitHub HTTP request count
Athena query count + bytes scanned
Bedrock Retrieve count
Bedrock model call count
Bedrock input/output tokens
retry count
throttle count
serialized admitted-result bytes
```

It rejects incomplete/reordered stage plans, negative resource observations, aggregate counter drift, empty final serialization, invalid clocks, and clock regression.

Current implementation surface:

```text
issue: #295
draft PR: #297
branch: feat/phase19-gate19-2-representative-workload-measurement
measurement contract: src/opslens/public_analysis/domain/representative_measurement.py
measurement harness:  src/opslens/public_analysis/application/representative_measurement.py
unit tests:            tests/unit/public_analysis/test_representative_measurement.py
```

The first Gate 19.2 code slice performs no live AWS/model calls. Live AWS/model execution, when needed for the representative measurement, remains a human execution boundary.

## Gate 19.2 authority boundary

```text
public endpoints:       0
new AWS resources:      0
new IAM roles/policies: 0
third-party code exec:  0
PR #89 modifications:  0
```

No API Gateway, Function URL, queue, result store, worker fleet, WAF, ECS/Fargate, AgentCore public runtime, or broad runtime role is authorized by the current gate.

## Next checkpoint

Continue composing the provider-neutral harness with retained OpsLens stages without moving authority into the measurement layer. The next engineering slice must inspect and adapt the existing repository-intelligence, Risk Policy, structured-retrieval, semantic-retrieval, synthesis, and result-admission contracts rather than duplicating their business truth.

After deterministic local/CI validation is green, prepare the smallest reproducible non-public live measurement procedure. Any live AWS or model invocation remains explicitly human-executed. Only measured evidence may move the runtime decision from `DEFERRED_PENDING_MEASUREMENT` to `SYNC` or `ASYNC`.
