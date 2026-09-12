# OpsLens Documentation

_Last updated: 2026-09-12_

This directory contains the retained architecture, operational state, decisions, learning maps, runbooks, and V1 demonstration guidance for OpsLens.

## Start here

- [`current-state.md`](current-state.md) — authoritative current project state and active authority boundary.
- [`roadmap.md`](roadmap.md) — evidence-gated phase/gate progression through V1 closeout.
- [`architecture.md`](architecture.md) — final V1 architecture, authority table, security/failure model, and retained AWS runtime evidence.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture view.
- [`portfolio-evidence.md`](portfolio-evidence.md) — recruiter/architect-facing evidence projection and explicit non-claims.
- [`v1-demonstration-scope.md`](v1-demonstration-scope.md) — explicit V1 demonstration/product boundary.
- [`v1-completion-checklist.md`](v1-completion-checklist.md) — remaining work before the first V1 release candidate.
- [`demo/README.md`](demo/README.md) — canonical CLI and localhost demo entry point.
- [`demo/WALKTHROUGH.md`](demo/WALKTHROUGH.md) — three-to-five-minute reviewer walkthrough.
- [`demo/PORTFOLIO_CAPTURE.md`](demo/PORTFOLIO_CAPTURE.md) — reproducible screenshot/terminal capture guidance.
- [`post-v1-backlog.md`](post-v1-backlog.md) — intentionally deferred production/runtime experiments.
- [`aip-c01-learning-map.md`](aip-c01-learning-map.md) — AIP-C01 task-to-evidence learning map.
- [`adr/README.md`](adr/README.md) — Architecture Decision Record index.
- [`runbooks/`](runbooks/) — bounded operational procedures.

## Current checkpoint

```text
protected main: 4d001ba33e157c48891ccff3d5189263877f22b1
Gate 19.12: COMPLETE
protected merge: PR #383
post-merge CodeQL: 34719883927 / run #430 / success
Gate 19.12 issue: #382 / closed completed
Gate 19.13: IN PROGRESS / issue #384
```

Phases 0–18 are complete. Phase 19 remains the final active V1 closeout phase.

## Canonical V1 reviewer path

```bash
uv sync --frozen
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
uv run python scripts/demo_opslens_web.py
```

Open `http://127.0.0.1:8765/` for the local visual viewer.

The demo is synthetic, inert, deterministic, provider/model free, and never executes third-party repository code.

## Retained historical Phase 19 decision path

```text
Gate 19.1 — complete
runtime decision: DEFERRED_PENDING_MEASUREMENT
Gate 19.2 — complete
ASYNC_SUBMIT_STATUS_RESULT
```

These markers preserve the historical launch-contract and measurement decisions without implying that the old pending-measurement state is still current.

## Retained security lineage

Gate 17.1 — evidence-first threat/control-gap inventory — COMPLETE.  
Gate 17.2 — CI/CD and workflow authority hardening — COMPLETE.

Their security and workflow-authority controls remain active invariants for all later V1 work.

## V1 intent

OpsLens V1 is a **demonstration and architecture lab**, not a production SaaS.

The canonical authority chain is:

```text
public repository evidence
 -> inert dependency evidence
 -> structured threat evidence
 -> deterministic applicability/correlation
 -> deterministic risk prioritization
 -> bounded retrieval/reasoning where appropriate
 -> evidence-backed result
```

The retained async AWS runtime is materialized but disabled. It remains valid evidence of topology, IAM separation, idempotency, retry, queue/state authority, immutable deployment artifacts, exact Terraform planning, controlled materialization, and convergence. V1 does not require that runtime to become an Internet-facing production service.

```text
materialized != enabled
visual projection != business authority
demonstration readiness != production readiness
```

## Phase 19 V1 closeout sequence

```text
Gate 19.9   V1 demonstration contract + current-state synchronization  COMPLETE
Gate 19.10  deterministic end-to-end demo runner                       COMPLETE
Gate 19.11  curated demo scenarios + deterministic evaluation          COMPLETE
Gate 19.12  minimal local visual demo                                  COMPLETE
Gate 19.13  portfolio/readme/architecture polish                       IN PROGRESS
Gate 19.14  V1 closeout + release readiness                            PLANNED
```

## Evidence semantics

Historical artifacts preserve the state that existed when they were created. Current-facing documents carry later protected-main truth without rewriting historical evidence.

```text
Agents reason. Code verifies evidence.
READ, NEVER EXECUTE third-party repository code.
Repository Risk != Runtime Exposure.
Structured facts use structured retrieval.
retrieved content != instruction authority
model proposal != authorization
tool/protocol success != business truth
missing evidence != benign evidence
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
artifact hash != S3 VersionId
publication success != deployment authorization
plan != apply
materialized != enabled
visual projection != business authority
localhost demo != public service
demonstration readiness != production readiness
AIP-C01 topic != product requirement
```

## V1 production non-goals

The first release does not require:

```text
Internet-facing production runtime
authentication / OIDC
multi-tenancy
commercial quotas or billing
WAF/custom domain
24x7 operations
production SLO/SLA
HA/DR
production TCO
public worker/event-source enablement
```

Those concerns remain in [`post-v1-backlog.md`](post-v1-backlog.md) and do not inherit standing implementation authority.
