# OpsLens V1 Completion Checklist

This checklist defines the remaining demonstration-only work required before the first `v1.0.0` release candidate.

## Gate 19.9 — V1 contract and synchronization

- [x] Freeze V1 as a demonstration/architecture lab.
- [x] Preserve `materialized != enabled` for the retained async AWS runtime.
- [x] Record the Gate 19.8 protected merge and post-merge CodeQL evidence.
- [ ] Synchronize active README/current-state/roadmap/architecture views.
- [ ] Exact-head CI/security/CodeQL green.
- [ ] HUMAN protected merge.

## Gate 19.10 — Deterministic demo runner

- [ ] Add one canonical offline command.
- [ ] Reuse existing typed domain/application authorities rather than duplicating risk logic.
- [ ] Emit stable JSON evidence.
- [ ] Emit concise human-readable output.
- [ ] Execute no third-party repository code.
- [ ] Require no AWS credentials for the canonical offline path.

## Gate 19.11 — Curated scenarios and evaluation

- [ ] Material-vulnerability scenario.
- [ ] Controlled-benign scenario.
- [ ] Fail-closed incomplete/ambiguous-evidence scenario.
- [ ] Deterministic scenario manifest/hashes.
- [ ] Regression tests over admitted outputs.

## Gate 19.12 — Local visual demo

- [ ] Local-only demo surface over the same application authority.
- [ ] Scenario selection or bounded input.
- [ ] Risk summary and vulnerability evidence.
- [ ] Provenance/citation projection.
- [ ] AI explanation clearly separated from deterministic authority.
- [ ] No public deployment required.

## Gate 19.13 — Portfolio polish

- [ ] README English/Portuguese current and concise.
- [ ] Final architecture diagram.
- [ ] Deterministic authority vs AI reasoning table.
- [ ] Measured latency/cost evidence summarized without production extrapolation.
- [ ] Security/failure model summarized.
- [ ] Three-to-five-minute demo walkthrough.
- [ ] Screenshots or terminal recording where useful.

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
