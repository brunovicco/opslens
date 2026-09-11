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

### Gate 19.2 — in progress at the human execution boundary

Gate 19.2 has completed the repository-side pre-live implementation required for one bounded non-public representative measurement. The latest increment was merged through issue #338 / PR #339; protected `main` is `765ecf528f0b7e8dcabb31b40416061ba719dd58` at this checkpoint.

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

The current representative anchor is:

```text
repository:      openedx/mockprock
commit/ref:      18c954d8604df4740c829ba17fa2f3640b92b900
evidence file:  uv.lock
dependency:     webob==1.8.10
GHSA anchor:    GHSA-6hx8-3wjj-gr8g
CVE anchor:     CVE-2026-54770
```

The earlier Requests anchor recorded by the historical Gate 19.2 measurement-contract artifact is intentionally not rewritten. Later threat-admission/preload evidence and the operator runbook carry the current representative coordinates.

The human-only operator entrypoint is:

```text
scripts/run_phase19_gate19_2_live_measurement.py
```

with the reviewed procedure in [`../labs/phase-19-gate-19-2-human-live-measurement-runbook.md`](../labs/phase-19-gate-19-2-human-live-measurement-runbook.md).

CI and ChatGPT must not execute that live command. The next checkpoint is one human-executed read-only/live-provider measurement using existing authority, followed by deterministic review of `labs/evidence/phase-19-gate-19-2-live-measurement-v1.json`.

Runtime selection remains:

```text
DEFERRED_PENDING_MEASUREMENT
```

until that admitted live evidence exists. `ASYNC_SUBMIT_STATUS_RESULT` remains a leading hypothesis, not a selected topology.

Current Gate 19.2 authority remains:

```text
public endpoints:       0
new AWS resources:      0
new IAM roles/policies: 0
third-party code exec:  0
PR #89 modifications:  0
```

## Evidence location rule

Canonical machine-readable artifacts live under `../labs/evidence/`. Human-readable experiment and closeout records live under `../labs/`. ADRs explain why a decision was made; labs/evidence record what was measured, proven, rejected, or intentionally left `UNMEASURED`.

Historical evidence is not rewritten merely to make it look current. Current-facing documents (`current-state.md`, `roadmap.md`, this index, and active runbooks) explain later superseding context while preserving the original evidence lineage.

PR #89 remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency unless explicitly re-evaluated later.
