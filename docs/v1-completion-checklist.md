# OpsLens V1 Completion Checklist

This checklist defines the remaining demonstration-only work required before the first `v1.0.0` release candidate.

## Gate 19.9 — V1 contract and synchronization — COMPLETE

- [x] Freeze V1 as a demonstration/architecture lab.
- [x] Preserve `materialized != enabled` for the retained async AWS runtime.
- [x] Record the Gate 19.8 protected merge and post-merge CodeQL evidence.
- [x] Synchronize active README/current-state/roadmap/architecture views.
- [x] Exact-head CI/security/CodeQL green.
- [x] HUMAN protected merge.

## Gate 19.10 — Deterministic demo runner — COMPLETE

- [x] Add one canonical offline command.
- [x] Reuse existing typed domain/application authorities rather than duplicating risk logic.
- [x] Emit stable JSON evidence.
- [x] Emit concise human-readable output.
- [x] Execute no third-party repository code.
- [x] Require no AWS credentials for the canonical offline path.

## Gate 19.11 — Curated scenarios and evaluation — COMPLETE

- [x] Material-vulnerability scenario.
- [x] Controlled-benign scenario.
- [x] Fail-closed incomplete-evidence scenario.
- [x] Deterministic scenario identities and byte-stable outputs.
- [x] Regression tests over admitted outputs.
- [x] Cross-scenario deterministic evaluation.

## Gate 19.12 — Local visual demo — COMPLETE

- [x] Local-only demo surface over the same application authority.
- [x] Exactly three allowlisted scenarios.
- [x] Risk summary and vulnerability evidence.
- [x] Provenance/content-addressed result projection.
- [x] AI explanation explicitly disabled and separated from deterministic authority.
- [x] Loopback-only bind with no external host option.
- [x] Unknown/query-string routes fail closed.
- [x] No public deployment required.

## Gate 19.13 — Portfolio polish — IN PROGRESS

- [x] README English/Portuguese current, concise, and reviewer-first.
- [x] Final GitHub-rendered architecture diagram.
- [x] Deterministic authority vs AI reasoning table.
- [x] Measured latency/cost evidence summarized without production extrapolation.
- [x] Security/failure model summarized.
- [x] Three-to-five-minute demo walkthrough.
- [x] Reproducible screenshot/terminal-recording capture guide.
- [x] Portfolio evidence wording aligned to the V1 demonstration boundary.
- [ ] Exact-head CI/security/CodeQL green.
- [ ] HUMAN protected merge.

Binary screenshots/recordings are optional presentation artifacts. The source-of-truth remains the reproducible deterministic demo and the checked-in capture procedure.

## Gate 19.14 — V1 closeout

- [ ] Clean-environment quickstart verification.
- [ ] Full CI/security/CodeQL green.
- [ ] `labs/phase-19-closeout.md` and machine-readable closeout evidence.
- [ ] Phase 19 marked COMPLETE.
- [ ] Remaining ideas moved to Post-V1 / Experiments backlog.
- [ ] HUMAN-reviewed `v1.0.0` tag/release.

## V1 explicitly does not require

```text
Internet-facing production runtime
authentication / OIDC
multi-tenancy
commercial quotas or billing
WAF/custom domain
production SLO/SLA
24x7 operations
HA/DR program
production TCO
public worker/event-source enablement
```
