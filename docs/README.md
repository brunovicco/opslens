# OpsLens Documentation

_Last updated: 2026-09-12_

This directory contains the retained architecture, operational state, decisions, learning maps, runbooks, and V1 demonstration guidance for OpsLens.

## Start here

- [`current-state.md`](current-state.md) — authoritative current project state and active authority boundary.
- [`roadmap.md`](roadmap.md) — evidence-gated phase/gate progression through V1 closeout.
- [`v1-demonstration-scope.md`](v1-demonstration-scope.md) — explicit V1 demonstration/product boundary.
- [`v1-completion-checklist.md`](v1-completion-checklist.md) — remaining work before the first V1 release candidate.
- [`demo/README.md`](demo/README.md) — canonical demo area and upcoming runner contract.
- [`post-v1-backlog.md`](post-v1-backlog.md) — intentionally deferred production/runtime experiments.
- [`architecture.md`](architecture.md) — accumulated architecture and authority boundaries.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture view.
- [`portfolio-evidence.md`](portfolio-evidence.md) — recruiter/architect-facing evidence projection.
- [`aip-c01-learning-map.md`](aip-c01-learning-map.md) — AIP-C01 task-to-evidence learning map.
- [`adr/README.md`](adr/README.md) — Architecture Decision Record index.
- [`runbooks/`](runbooks/) — bounded operational procedures.

## Current checkpoint

```text
protected main: e538fa3e96c29cf76dd3aa83a9967e090587b6fb
Gate 19.8: COMPLETE
protected merge: PR #375
post-merge CodeQL: 34713360403 / run #393 / success
Gate 19.9 issue: #376
Gate 19.9: IN PROGRESS
```

Phases 0–18 are complete. Phase 19 is the final active V1 closeout phase.

## Retained security lineage

Gate 17.1 — evidence-first threat/control-gap inventory — COMPLETE.  
Gate 17.2 — CI/CD and workflow authority hardening — COMPLETE.

Their security and workflow-authority controls remain active invariants for all later V1 work.

## V1 intent

OpsLens V1 is a **demonstration and architecture lab**, not a production SaaS.

The canonical reviewer target is:

```text
clone
 -> setup
 -> one deterministic offline demo command
 -> evidence-backed result
```

V1 is designed to demonstrate:

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
demonstration readiness != production readiness
```

## Remaining V1 sequence

```text
Gate 19.9   V1 demonstration contract + current-state synchronization
Gate 19.10  deterministic end-to-end demo runner
Gate 19.11  curated demo scenarios + deterministic evaluation
Gate 19.12  minimal local visual demo
Gate 19.13  portfolio/readme/architecture polish
Gate 19.14  V1 closeout + release readiness
```

## Gate 19.8 retained authority

Gate 19.8 introduced the provider-neutral request-time threat authority contract:

```text
PublicRepositoryEvidenceExecution
 -> PublicThreatEvidenceScope
 -> PublicThreatEvidenceRequest
 -> PublicThreatEvidenceAuthority
 -> PublicRepositoryThreatEvidence
 -> retained deterministic correlation/enrichment
```

The physical provider adapter remains deliberately deferred. It is now a Post-V1 experiment rather than a V1 blocker because the canonical V1 path is offline-first and deterministic.

Canonical Gate 19.8 records:

- [`../labs/phase-19-gate-19-8-threat-evidence-authority.md`](../labs/phase-19-gate-19-8-threat-evidence-authority.md)
- [`../labs/evidence/phase-19-gate-19-8-threat-evidence-authority-v1.json`](../labs/evidence/phase-19-gate-19-8-threat-evidence-authority-v1.json)
- [`../scripts/verify_phase19_gate19_8_threat_evidence_authority.py`](../scripts/verify_phase19_gate19_8_threat_evidence_authority.py)

## Gate 19.9 records

- [`../labs/phase-19-gate-19-9-v1-demonstration-contract.md`](../labs/phase-19-gate-19-9-v1-demonstration-contract.md)
- [`../labs/evidence/phase-19-gate-19-9-v1-demonstration-contract-v1.json`](../labs/evidence/phase-19-gate-19-9-v1-demonstration-contract-v1.json)
- [`../scripts/verify_phase19_gate19_9_v1_demonstration_contract.py`](../scripts/verify_phase19_gate19_9_v1_demonstration_contract.py)
- [`adr/0077-phase19-v1-demonstration-boundary.md`](adr/0077-phase19-v1-demonstration-boundary.md)

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

Those concerns are tracked in [`post-v1-backlog.md`](post-v1-backlog.md) and do not inherit standing implementation authority.
