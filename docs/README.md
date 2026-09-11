# OpsLens Documentation

_Last updated: 2026-09-11_

This directory contains the retained architecture, operational state, decisions, learning maps, and runbooks for OpsLens.

## Start here

- [`current-state.md`](current-state.md) — authoritative current project state and next decision boundary.
- [`roadmap.md`](roadmap.md) — evidence-gated phase/gate progression.
- [`architecture.md`](architecture.md) — retained architecture and authority boundaries.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture view.
- [`portfolio-evidence.md`](portfolio-evidence.md) — recruiter/architect-facing evidence projection.
- [`aip-c01-learning-map.md`](aip-c01-learning-map.md) — current AIP-C01 task-to-evidence learning map.
- [`adr/README.md`](adr/README.md) — Architecture Decision Record index.
- [`runbooks/`](runbooks/) — bounded operational procedures.

## Retained security lineage

Phase 19 remains downstream of the Phase 17 security controls and the Phase 18 evidence closeout. **Gate 17.1** established the evidence-first threat/control-gap inventory, and **Gate 17.2** hardened CI/CD and workflow authority. The `Repository security invariants` protected-main context, full-SHA external actions, Dependency Review, CodeQL, adversarial authority regression, content-minimized Lambda telemetry, and the narrowly scoped scheduled-ingestion pause remain part of the retained platform authority chain.

## Phase 18 closeout

Phase 18 is complete. Its protected closeout was squash-merged through PR #290 at:

```text
feca774535b7d83f57c26f4e9fe7da71ce268f0f
```

The historical Phase 18 closeout artifacts intentionally preserve the state that existed before their protected merge:

- [`../labs/phase-18-closeout.md`](../labs/phase-18-closeout.md)
- [`../labs/evidence/phase-18-closeout-v1.json`](../labs/evidence/phase-18-closeout-v1.json)
- [`adr/0075-phase18-evaluation-cost-portfolio-closeout.md`](adr/0075-phase18-evaluation-cost-portfolio-closeout.md)

Do not rewrite those historical artifacts to make them look post-merge. Current-facing documents carry the post-merge state instead.

The retained Phase 18 evidence semantics remain:

```text
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
lab measurement != production SLO
cost evidence != production TCO
portfolio claim != new evidence authority
AIP-C01 topic != product requirement
AIP-C01 coverage != certification guarantee
historical experiment != standing authority
```

## Phase 19 — Bounded Public Runtime & Productization

### Gate 19.1 — complete

Gate 19.1 was protected-squash-merged through PR #292 at `ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1` after exact-head validation at `484e2b85fc1996b2419b4057c2cf585ab1f675a1`.

Its retained launch contract is:

```text
public-analysis-workload:v1
runtime decision: DEFERRED_PENDING_MEASUREMENT
leading hypothesis: ASYNC_SUBMIT_STATUS_RESULT
AWS mutations: 0
IAM mutations: 0
new AWS resources: 0
public endpoints: 0
model/capability executions: 0
```

The Gate 19.1 human-readable lab is [`../labs/phase-19-gate-19-1-public-runtime-hypothesis.md`](../labs/phase-19-gate-19-1-public-runtime-hypothesis.md). Its machine-readable contract is [`../labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`](../labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json), with architecture decision rationale in [`adr/0076-bounded-public-runtime-hypothesis-and-launch-contract.md`](adr/0076-bounded-public-runtime-hypothesis-and-launch-contract.md).

Gate 19.1 created no API Gateway, Lambda Function URL, public Lambda compute, SQS queue, result store, WAF, ECS/Fargate, AgentCore runtime, or runtime IAM.

### Gate 19.2 — closeout in review

Gate 19.2 completed the repository-side measurement harness, the human-only pre-flight/fail-closed checks, one successful representative live execution, deterministic persisted-artifact review, and the interaction-pattern decision.

Source protected main for the successful live run:

```text
e45ba419414e6dd77ecad68f4d2312e9123c2223
```

The exact measurement surface includes:

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

The retained representative anchor is:

```text
repository:      openedx/mockprock
commit/ref:      18c954d8604df4740c829ba17fa2f3640b92b900
evidence file:  uv.lock
dependency:     webob==1.8.10
GHSA anchor:    GHSA-6hx8-3wjj-gr8g
CVE anchor:     CVE-2026-54770
```

The earlier Requests anchor recorded by the historical Gate 19.2 measurement-contract artifact is intentionally not rewritten. Later threat-admission/preload evidence and the human runbook carry the current representative coordinates.

Canonical live artifact:

- [`../labs/evidence/phase-19-gate-19-2-live-measurement-v1.json`](../labs/evidence/phase-19-gate-19-2-live-measurement-v1.json)
- SHA-256 `04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114`
- run id `gate19.2-live-20260911T131121Z`
- outcome `SUCCESS`

Measured evidence includes:

```text
end-to-end duration                    17,748 ms
GitHub physical requests                     4  MEASURED
Bedrock Retrieve client elapsed         4,148 ms  MEASURED
Bedrock model client elapsed            8,901 ms  MEASURED
Bedrock provider model latency          7,772 ms  MEASURED
Bedrock input/output tokens        5,936 / 408  MEASURED
retry count                                  0  MEASURED
throttle count                               0  UNMEASURED
Athena query count / bytes                    0  NOT_APPLICABLE
serialized admitted result              5,285 bytes
```

The Bedrock-facing stages consumed `13,098 ms`, or `73.80%` of measured end-to-end duration.

Gate 19.2 selects the interaction pattern:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

This is not a claim that the successful baseline timed out; it completed below the retained 30-second HTTP API reference envelope. The async decision is based on provider-latency coupling, retry safety, backpressure, and failure isolation. Explicit retry-safety scenarios are classified `DERIVED`, never relabeled as measured evidence.

Canonical closeout records:

- [`../labs/phase-19-gate-19-2-closeout.md`](../labs/phase-19-gate-19-2-closeout.md)
- [`../labs/evidence/phase-19-gate-19-2-closeout-v1.json`](../labs/evidence/phase-19-gate-19-2-closeout-v1.json)
- [`../scripts/verify_phase19_gate19_2_closeout.py`](../scripts/verify_phase19_gate19_2_closeout.py)

Gate 19.2 authority remains:

```text
public endpoints:       0
new AWS resources:      0
new IAM roles/policies: 0
third-party code exec:  0
PR #89 modifications:  0
```

The interaction pattern is selected, but the concrete AWS topology remains unselected. The next Phase 19 boundary is to freeze the smallest async ingress/job/result topology, lifecycle semantics, least-privilege IAM responsibilities, abuse/backpressure controls, and disable/recovery boundaries before any deployment.

## Evidence location rule

Canonical machine-readable artifacts live under `../labs/evidence/`. Human-readable experiment and closeout records live under `../labs/`. ADRs explain why a decision was made; labs/evidence record what was measured, proven, rejected, or intentionally left `UNMEASURED`.

Historical evidence is not rewritten merely to make it look current. Current-facing documents (`current-state.md`, `roadmap.md`, this index, and active runbooks) explain later superseding context while preserving the original evidence lineage.

PR #89 remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency unless explicitly re-evaluated later.
