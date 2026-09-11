# OpsLens — Current State

_Last updated: 2026-09-11_

## Authoritative checkpoint

```text
protected main:
765ecf528f0b7e8dcabb31b40416061ba719dd58

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
latest completed issue: #338
latest merged PR: #339
exact final PR head: a64995bed02aeadb0b8b1ed1cf4ae85975e552f5
protected main merge: 765ecf528f0b7e8dcabb31b40416061ba719dd58
active boundary: HUMAN LIVE MEASUREMENT
```

Phases 0–18 remain complete. Gate 19.1 is complete and merged. Gate 19.2 remains the active engineering boundary, but its pre-live implementation is now merged far enough for the next step to be one explicit human-executed representative live measurement. PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency.

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

Gate 19.2 composes a **non-public representative execution** downstream of the retained handoff solely to measure the workload before runtime selection. That composition is not public runtime authority.

## Gate 19.1 retained launch contract

Canonical machine-readable authority:

`labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`

Frozen workload identity:

```text
public-analysis-workload:v1
```

The retained runtime decision remains:

```text
DEFERRED_PENDING_MEASUREMENT
```

with leading design hypothesis:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

That hypothesis is not runtime authority. A concrete topology must follow representative whole-workload evidence.

## Gate 19.2 merged pre-live surface

Gate 19.2 has the complete nine-stage non-public representative composition:

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

PR #339 completed the human-run-only live composition root/CLI. It composes measured GitHub transport, preloaded admitted threat evidence, direct bounded Bedrock Retrieve, bounded hybrid Bedrock synthesis, a real monotonic clock, one exact representative workload invocation, byte-exact live-artifact admission, and atomic create-without-replace persistence. Construction remains inert with respect to provider I/O.

The human entrypoint is:

```text
scripts/run_phase19_gate19_2_live_measurement.py
```

The checked implementation lives under:

```text
src/opslens/public_analysis/cli/run_live_measurement.py
```

The operator runbook is:

```text
labs/phase-19-gate-19-2-human-live-measurement-runbook.md
```

## Current representative anchor

The earlier Requests candidate was superseded during read-only pre-live threat-evidence preparation because its advisory was not materialized in the current analytical GHSA state. The admitted current representative anchor is:

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

The human driver reuses only existing resources:

```text
region:             us-east-1
knowledge base id:  BTVJ2PBR2A
data source id:     IEL1LBE026
source/data bucket: opslens-dev-data-487757851499-us-east-1
synthesis model:    us.anthropic.claude-haiku-4-5-20251001-v1:0
```

No new Knowledge Base, vector index, model deployment, IAM role/policy, endpoint, bucket, data source, queue, or result store is authorized by Gate 19.2.

## Measurement contract

The representative measurement records:

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

Measurement authority is explicit per metric. Numeric zero does not prove observation. For the current direct structured-evidence path, Athena query count and bytes scanned are `NOT_APPLICABLE`; they are not represented as measured zero. `throttle_count` remains `UNMEASURED` unless explicit provider throttle evidence is introduced.

Provider latency remains sourced from retained invocation evidence rather than inferred from stage duration.

The historical design artifact `labs/evidence/phase-19-gate-19-2-measurement-contract-v1.json` intentionally preserves the earlier pre-live slice, including its then-frozen Requests anchor. It is historical evidence, not the current representative-coordinate authority. The current anchor and operator procedure are carried by the later threat-admission/preload records and the human live-measurement runbook.

## Gate 19.2 authority boundary

```text
public endpoints:       0
new AWS resources:      0
new IAM roles/policies: 0
third-party code exec:  0
PR #89 modifications:  0
```

No API Gateway, Function URL, queue, result store, worker fleet, WAF, ECS/Fargate, AgentCore public runtime, or broad runtime role is authorized by the current gate.

## Validation state

PR #339 merged from exact head `a64995bed02aeadb0b8b1ed1cf4ae85975e552f5` into protected `main` as `765ecf528f0b7e8dcabb31b40416061ba719dd58`. The merged increment includes offline coverage for inert live composition, one-shot execution/admission, failure propagation, atomic no-overwrite artifact persistence, lint/type checks, and the retained public-analysis verification chain.

No live GitHub/AWS/Bedrock representative workload was executed by CI or ChatGPT as part of that merge.

## Next checkpoint — human execution boundary

Autonomous repository implementation stops at the intended authority boundary. The next meaningful step is **not** public deployment and is not another synthetic benchmark.

The operator should now:

1. check out and verify the exact reviewed protected-main commit intended for the evidence artifact;
2. run the runbook pre-flight checks locally;
3. confirm the intended existing AWS identity without changing IAM;
4. materialize the exact typed GHSA/NVD/KEV/EPSS authority through the retained read-only path before measurement;
5. human-execute exactly one non-public representative workload with the retained GitHub and Bedrock adapters;
6. preserve the admitted artifact at `labs/evidence/phase-19-gate-19-2-live-measurement-v1.json`;
7. review measurement classifications without coercing `UNMEASURED` or `NOT_APPLICABLE` into zero;
8. only then evaluate `SYNC`, `ASYNC`, or retain `DEFERRED_PENDING_MEASUREMENT` from the measured evidence.

Live AWS/model execution remains explicitly human-executed. Missing permission or provenance is a stop condition, not authority to expand IAM or fall back to another provider/input.
