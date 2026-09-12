# OpsLens Portfolio Evidence

_Last updated: 2026-09-12_

This document is the recruiter/architect-facing entry point for evidence OpsLens can actually prove. It is a projection of retained artifacts, not a new source of technical truth.

> **Agents reason. Code verifies evidence.**

> **Portfolio claim != new evidence authority.**

## What the project demonstrates

OpsLens is a demonstration and architecture lab for verifiable software-supply-chain intelligence and GenAI on AWS. The retained platform combines deterministic vulnerability authority, Amazon Bedrock knowledge retrieval, hybrid structured/semantic evidence, bounded agent reasoning, MCP/A2A interoperability experiments, observability, security hardening, runtime-evidence boundaries, and cost/evaluation controls.

The architectural theme is consistent: probabilistic reasoning may propose or synthesize, while deterministic code owns scope, authorization, evidence admission, structured business truth, cost/tool limits, and failure behavior.

## V1 reviewer evidence

Gates 19.10–19.12 make the core authority chain reproducible without provider access:

```text
uv sync --frozen
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
uv run python scripts/demo_opslens_web.py
```

Canonical demo proof:

| Scenario / surface | Deterministic evidence | Provider/model execution |
| --- | --- | ---: |
| `material-vulnerability` | 1 finding; Risk Policy v1 = 90 / P0 | 0 |
| `controlled-benign` | 0 findings with complete scoped fixture evidence | 0 |
| `fail-closed-incomplete-evidence` | rejected before analysis/risk; no benign conclusion | 0 |
| Suite evaluator | byte-stable cross-scenario assertions | 0 |
| Local visual viewer | presentation over retained results; loopback only | 0 |

The scenarios are synthetic, inert fixtures. They demonstrate authority behavior and do not claim that a live repository is safe, vulnerable, or runtime-exposed.

## Headline retained evaluation evidence

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

The canonical Phase 18 machine-readable projection is `labs/evidence/phase-18-gate-18-4-portfolio-evidence-pack-v1.json`. Numeric values above are bound to Gate 18.2 and Gate 18.3 evidence by deterministic validation.

## Phase 19 representative workload evidence

The retained representative workload measured the complete bounded public-analysis path before the V1 scope was narrowed to offline demonstration:

| Metric | Classification / value |
| --- | ---: |
| End-to-end duration | 17,748 ms MEASURED |
| Serialized result | 5,285 bytes MEASURED |
| GitHub physical HTTP requests | 4 MEASURED |
| Athena query count | 0 NOT_APPLICABLE |
| Bedrock Retrieve | 1 call MEASURED |
| Bedrock Retrieve client elapsed | 4,148 ms MEASURED |
| Bedrock model | 1 call MEASURED |
| Bedrock input / output tokens | 5,936 / 408 MEASURED |
| Bedrock model client elapsed | 8,901 ms MEASURED |
| Bedrock provider latency | 7,772 ms MEASURED |
| Retry count | 0 MEASURED |
| Throttle count | UNMEASURED |

This supports architectural latency/cost reasoning. It is not a production SLO, capacity benchmark, monthly run-rate, or production TCO claim.

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

Gate 18.3 prevents cross-component cost summation, alternative-workload summation, and monthly extrapolation without a frozen workload.

## Decisions where simpler or safer won

Portfolio evidence includes rejected defaults and negative signals rather than only successful demonstrations:

- Phase 7 preserved an isolation-grounding failure found by human review instead of hiding unsupported claims.
- Phase 12 rejected the two-model topology as the default because it added calls, tokens, latency, and derived cost without quality lift over the 6/6 single-agent baseline.
- Phase 14 retained AgentCore as an optional lab target, not the default reasoning runtime.
- Phase 16 retained a successful Inspector read boundary with zero returned records without converting that result into a claim of zero runtime exposure.
- Gate 19.7 materialized the async topology but kept it disabled; `materialized != enabled`.
- Gate 19.11 explicitly distinguishes complete-evidence no-finding from incomplete-evidence rejection; `missing evidence != benign evidence`.
- Gate 19.12 keeps the browser viewer presentation-only; `visual projection != business authority`.

## Security / failure evidence

Retained controls include:

```text
READ, NEVER EXECUTE third-party repository code.
strict repository/source identity admission
immutable snapshot and content-addressed evidence
fail-closed package/version normalization
scoped GHSA/NVD/KEV/EPSS/CVSS evidence
no unrestricted text-to-SQL
deterministic capability/tool authorization
bounded token / scan / retry / time budgets
content-minimized telemetry
full-SHA GitHub Actions pinning
Dependency Review
CodeQL
adversarial authority regression
least-privilege IAM evidence
HUMAN protected-merge boundaries
```

## Retained AWS deployment evidence

Phase 19 retains evidence for an async topology:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
```

Gate 19.5 produced immutable API/worker artifacts, Gate 19.6 admitted the exact Terraform plan, and Gate 19.7 materialized 21 managed resources and proved convergence. The public endpoint, submit path, worker, and event-source mapping remain disabled.

This demonstrates deployment/runtime engineering without claiming an Internet-facing V1 service.

## What is not claimed

OpsLens does **not** claim:

- a public HTTP production runtime;
- production SLO/SLA from bounded lab measurements;
- production TCO or monthly run rate;
- public MCP or A2A runtimes;
- AgentCore as the default runtime;
- zero runtime exposure from a zero-record Inspector read;
- a live-repository safety claim from the controlled-benign fixture;
- arbitrary repository execution;
- model authority over vulnerability applicability or risk;
- configured limits as measured utilization;
- certification readiness/pass probability.

## Reviewer path

1. Start with the root `README.md` or `README.pt-br.md`.
2. Run the deterministic CLI and inspect the three scenarios.
3. Launch the localhost visual viewer.
4. Read `docs/architecture.md` for the authority diagram and failure model.
5. Use `docs/demo/WALKTHROUGH.md` for a three-to-five-minute interview/demo flow.
6. Use `docs/demo/PORTFOLIO_CAPTURE.md` for reproducible screenshots or terminal capture.
7. Inspect `docs/current-state.md`, ADRs, labs, and machine-readable evidence for source truth.

Historical experiment artifacts remain immutable. Current-facing documents summarize them without rewriting or upgrading the underlying evidence class.
