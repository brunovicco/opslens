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

Gate 19.2 composes a **non-public representative execution** downstream of the retained handoff solely to measure the workload before runtime selection. That composition is not yet public runtime authority.

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

Gate 19.2 now has the complete nine-stage non-public representative composition implemented under draft PR #297:

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

The measurement contract records:

```text
end-to-end duration
per-stage duration
GitHub physical HTTP request count
Athena query count + bytes scanned
Bedrock Retrieve count
Bedrock Retrieve client elapsed milliseconds
Bedrock model call count
Bedrock input/output tokens
Bedrock model client elapsed milliseconds
Bedrock provider latency milliseconds
retry count
throttle count
serialized admitted-result bytes
```

Measurement authority is explicit per metric. Numeric zero does not prove observation. For the current direct structured-evidence path, Athena query count and bytes scanned are `NOT_APPLICABLE`; they are not represented as measured zero. `throttle_count` remains `UNMEASURED` unless the complete concrete live provider path can prove it.

Provider latency is retained from provider invocation evidence rather than derived from stage duration:

```text
Bedrock Retrieve:
  BedrockRetrieveInvocationEvidence.client_elapsed_ms

Bedrock model:
  BedrockHybridSynthesisInvocationEvidence.client_elapsed_ms
  BedrockHybridSynthesisInvocationEvidence.bedrock_latency_ms
```

Current implementation surface includes:

```text
measurement domain contract:
  src/opslens/public_analysis/domain/representative_measurement.py

measurement harness:
  src/opslens/public_analysis/application/representative_measurement.py

complete nine-stage runner:
  src/opslens/public_analysis/application/representative_workload_execution.py

repository analysis composition:
  src/opslens/public_analysis/application/representative_repository_analysis.py

structured evidence:
  src/opslens/public_analysis/application/representative_structured_evidence.py

semantic evidence:
  src/opslens/public_analysis/application/representative_semantic_evidence.py

hybrid evidence:
  src/opslens/public_analysis/application/representative_hybrid_evidence.py

model reasoning:
  src/opslens/public_analysis/application/representative_model_reasoning.py

result admission:
  src/opslens/public_analysis/domain/representative_result.py

GitHub physical transport measurement:
  src/opslens/public_analysis/adapters/github_measurement.py

human live-measurement runbook:
  labs/phase-19-gate-19-2-human-live-measurement-runbook.md
```

The representative input is frozen for reproducibility at:

```text
repository:      whotracksme/whotracks.me
commit/ref:      468f6e211a307f5f20d1d95c478ddd89efdb9b6b
evidence file:  uv.lock
dependency:     requests==2.31.0
GHSA anchor:    GHSA-9wx4-h78v-vm56
CVE anchor:     CVE-2024-35195
patched from:   2.32.0
```

These identifiers do not grant vulnerability authority by themselves. Before the live representative run, the exact typed `RepresentativeRepositoryThreatEvidence` bundle must be materialized from retained authoritative evidence contracts. Missing source evidence must remain unavailable/unsupported rather than being fabricated.

## Gate 19.2 authority boundary

```text
public endpoints:       0
new AWS resources:      0
new IAM roles/policies: 0
third-party code exec:  0
PR #89 modifications:  0
```

No API Gateway, Function URL, queue, result store, worker fleet, WAF, ECS/Fargate, AgentCore public runtime, or broad runtime role is authorized by the current gate.

## Current validation state

The composed workload has deterministic offline coverage for the complete stage order, repository/risk authority chain, semantic evidence, hybrid evidence, model reasoning, final result serialization, provider accounting, measurement classification, malformed measurement rejection, GitHub physical-call counting, and rate-limit observation.

An exact-head CI checkpoint at `bbe678c2702e0e1f69dc56f461025e19cde5689f` passed all eight retained workflows before the human runbook/current-state synchronization commits. The current PR head must independently pass the same validation chain before it becomes the next exact validated checkpoint.

## Next checkpoint — human execution boundary

Pre-live composition is complete enough to stop autonomous execution at the intended authority boundary.

The next meaningful step is **not** public deployment. It is to:

1. materialize the exact GHSA/NVD/KEV/EPSS threat-evidence bundle through retained authoritative source/transform contracts;
2. human-execute exactly one non-public representative workload with the retained GitHub and Bedrock adapters;
3. capture the live measurement as immutable evidence under `labs/evidence/`;
4. validate measurement classifications without coercing `UNMEASURED` or `NOT_APPLICABLE` into zero;
5. evaluate `SYNC`, `ASYNC`, or retain `DEFERRED_PENDING_MEASUREMENT` only from the measured evidence.

Live AWS/model execution remains explicitly human-executed. No AWS/IAM/public runtime mutation is authorized by this step.
