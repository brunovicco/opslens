# OpsLens Portfolio Evidence

_Last updated: 2026-09-10_

This document is the recruiter/architect-facing entry point for evidence that OpsLens can actually prove. It is a projection of retained artifacts, not a new source of technical truth.

> **Agents reason. Code verifies evidence.**

> **Portfolio claim != new evidence authority.**

## What the project demonstrates

OpsLens is a production-oriented GenAI and software-supply-chain architecture lab on AWS. The retained platform combines deterministic vulnerability authority, Amazon Bedrock knowledge retrieval, hybrid structured/semantic evidence, bounded agent reasoning, MCP/A2A interoperability experiments, observability, security hardening, runtime-evidence boundaries, and cost/evaluation controls.

The architectural theme is consistent across the project: probabilistic reasoning may propose or synthesize, while deterministic code owns scope, authorization, evidence admission, structured business truth, cost/tool limits, and failure behavior.

## Headline evidence

| Evidence | Classification | Value | Scope |
| --- | --- | ---: | --- |
| Phase 7 claim supportedness | DERIVED | 11/13 = 0.8461538461538461 | First frozen human-reviewed claim/citation run |
| Phase 11 reasoning quality | MEASURED | 6/6 cases | Retained direct Bedrock reasoning reference |
| Phase 11 provider latency median | MEASURED | 809.5 ms | Six direct reasoning calls |
| Phase 11 token volume | MEASURED | 3,395 tokens | Six-case reasoning reference |
| Phase 11 inference cost | DERIVED | USD 0.0041921 | Six-case estimate; not an invoice |
| Phase 12 two-model quality | MEASURED | 6/6 cases | Bounded comparison topology |
| Phase 12 provider latency median | DERIVED | 1,694 ms | Per-case comparison metric |
| Phase 12 token volume | MEASURED | 5,982 tokens | Triage + specialist calls |
| Phase 12 inference cost | DERIVED | USD 0.0074338 | Six-case estimate |
| Phase 14 AgentCore replay | MEASURED | 6/6 cases | Bounded authenticated runtime replay |
| Phase 14 experiment total | DERIVED | USD 0.006572445136128483 | Bounded experiment; not monthly production cost |

The canonical machine-readable projection is `labs/evidence/phase-18-gate-18-4-portfolio-evidence-pack-v1.json`. Every numeric value above is bound to Gate 18.2 and Gate 18.3 evidence by deterministic validation.

## Retained budget envelopes

The following are **configured limits**, not measured utilization:

```text
semantic planner output tokens        256
single-agent output tokens             96
multi-agent triage output tokens       64
knowledge synthesis output tokens    2048
Athena bytes scanned/query        10485760
Scheduler maximum event age          3600 seconds
Scheduler maximum retry attempts         2
```

Gate 18.3 prevents cross-component cost summation, alternative-workload summation, and monthly extrapolation without a frozen workload. OpsLens therefore does not manufacture a production TCO from unrelated experiments.

## Decisions where simpler or safer won

Portfolio evidence includes negative and rejected-default signals rather than only successful demonstrations:

- Phase 7 preserved an isolation-grounding failure found by human review instead of hiding unsupported claims.
- Phase 12 rejected the two-model topology as the default because it added calls, tokens, latency, and derived cost without quality lift over the 6/6 single-agent baseline.
- Phase 14 retained AgentCore as an optional lab target, not the default reasoning runtime.
- Phase 16 retained a successful Inspector read boundary with zero returned records without converting that result into a claim of zero runtime exposure.

These signals are frozen in `labs/evidence/phase-18-gate-18-2-decision-signals-v1.json`.

## What is not claimed

OpsLens does **not** claim a public HTTP production runtime, production SLOs from bounded lab measurements, production TCO/monthly run rate, public MCP or A2A runtime, AgentCore as the default runtime, zero runtime exposure from a zero-record Inspector read, a global platform kill switch, configured limits as measured utilization, or a certification readiness/pass-probability score.

## Architecture evidence trail

Start with `docs/architecture.md`, `docs/current-state.md`, `docs/adr/README.md`, the Gate 18.1 evidence inventory, the Gate 18.2 consolidated view, the Gate 18.3 cost-accounting artifact, and `docs/aip-c01-learning-map.md`.
