# OpsLens — Incremental Roadmap

_Last updated: 2026-09-12_

The roadmap is evidence-gated. Later work does not rewrite earlier evidence or inherit standing mutation authority. Certification topics do not automatically become product requirements.

## Phase status

```text
Phase 0   AWS Foundation                                      COMPLETE
Phase 1   EPSS Vertical Slice                                 COMPLETE
Phase 2   Threat Intelligence Data Lake                       COMPLETE
Phase 3   Vulnerability Correlation Engine                    COMPLETE
Phase 4   Repository Intelligence                             COMPLETE
Phase 5   Risk Prioritization Engine                          COMPLETE
Phase 6   Semantic Query Layer                                COMPLETE
Phase 7   Knowledge Retrieval with Bedrock                    COMPLETE
Phase 8   Hybrid Retrieval                                    COMPLETE
Phase 9   Public Analyze Your Repository application boundary COMPLETE
Phase 10  Observability & Operational Excellence              COMPLETE
Phase 11  Single-Agent Baseline                               COMPLETE
Phase 12  Multi-Agent Architecture                            COMPLETE
Phase 13  MCP                                                 COMPLETE
Phase 14  Amazon Bedrock AgentCore                            COMPLETE
Phase 15  A2A                                                 COMPLETE
Phase 16  Runtime Exposure with Amazon Inspector              COMPLETE
Phase 17  Security Hardening                                  COMPLETE
Phase 18  Evaluation, Cost & Portfolio Readiness              COMPLETE
Phase 19  Bounded Public Runtime & V1 Demonstration Closeout  IN PROGRESS
```

## Phase 19 protected lineage

```text
19.1  PR #292  ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1  COMPLETE
19.2  PR #347  71eda2650889d3047259d37be226862ed2a09092  COMPLETE
19.3  PR #349  18d31c03d27448c88a6ffcba16683f3875a5ba15  COMPLETE
19.4  PR #351  a5067e05fda74aad4d95d7f1a875110fb676304a  COMPLETE
19.5  PR #353  61749bfac7b7bc9d032567e0b1870f8c1f7dedd4  COMPLETE
19.6  PR #360  c76432dfcd97110ca43d91d77084f4367b9a89fd  COMPLETE
19.7  PR #372  21a5930fd770eddf26a5c7425ffcaddfdfa6d357  COMPLETE
      current-state sync PR #373 / 8700478c7fca230e5984c3ce034194ea3bd337e4
19.8  PR #375  e538fa3e96c29cf76dd3aa83a9967e090587b6fb  COMPLETE
      post-merge CodeQL 34713360403 / run #393 / success
19.9  issue #376                                              IN PROGRESS
```

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work. Phase 19 does not rebase, merge, modify, or depend on it.

## V1 decision

OpsLens V1 is a **demonstration and architecture lab**, not a production SaaS.

The project is considered V1-ready when a reviewer can understand and reproduce the core authority path quickly:

```text
clone
 -> setup
 -> one deterministic offline demo command
 -> evidence-backed result
```

The core demonstration chain is:

```text
public repository evidence
 -> inert dependency evidence
 -> structured threat evidence
 -> deterministic applicability/correlation
 -> deterministic risk prioritization
 -> bounded retrieval/reasoning where appropriate
 -> evidence-backed result
```

V1 does not require Internet-facing production runtime operations, authentication, multi-tenancy, WAF, commercial quotas/billing, production SLO/SLA, HA/DR, production TCO, or public worker enablement.

See [`v1-demonstration-scope.md`](v1-demonstration-scope.md).

## Completed Phase 19 evidence gates

### Gate 19.1 — Public Runtime Hypothesis & Launch Contract — COMPLETE

Froze `public-analysis-workload:v1` and deferred topology selection until representative evidence existed.

### Gate 19.2 — Representative Workload Measurement — COMPLETE

One bounded live representative workload measured:

```text
end_to_end_duration_ms: 17748
GitHub physical HTTP requests: 4 MEASURED
Bedrock Retrieve count: 1 MEASURED
Bedrock Retrieve client elapsed ms: 4148 MEASURED
Bedrock model call count: 1 MEASURED
Bedrock input/output tokens: 5936 / 408 MEASURED
Bedrock model client elapsed ms: 8901 MEASURED
Bedrock provider latency ms: 7772 MEASURED
```

Selected interaction pattern: `ASYNC_SUBMIT_STATUS_RESULT`.

### Gate 19.3 — Concrete Async Topology Contract — COMPLETE

Selected:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
```

### Gate 19.4 — Disabled Async Runtime Implementation — COMPLETE

Implemented typed application/adapters/Terraform behind fail-closed disabled defaults.

### Gate 19.5 — Immutable Async Deployment Artifacts — COMPLETE

Produced and human-published two immutable content-addressed Lambda artifacts with exact S3 VersionIds.

### Gate 19.6 — Exact Terraform Plan & Offline Admission — COMPLETE

Admitted an exact plan before mutation and preserved `plan != apply`.

### Gate 19.7 — Controlled Disabled Runtime Materialization — COMPLETE

Materialized 21 managed resources, recovered from one bounded Lambda concurrency constraint, and proved final Terraform convergence:

```text
0 add
0 change
0 destroy
0 replacement
```

Runtime remained disabled and non-public.

### Gate 19.8 — Request-time Threat Evidence Authority Contract — COMPLETE

Protected merge: PR #375 at `e538fa3e96c29cf76dd3aa83a9967e090587b6fb`.  
Post-merge CodeQL: `34713360403` / run #393 / success.  
Issue #374: closed completed.

Gate 19.8 added the provider-neutral authority chain:

```text
PublicRepositoryEvidenceExecution
 -> PublicThreatEvidenceScope
 -> PublicThreatEvidenceRequest
 -> PublicThreatEvidenceAuthority
 -> exact GHSA/NVD/KEV/EPSS evidence + provenance
 -> retained deterministic correlation/enrichment
```

It deliberately deferred the physical provider adapter. That provider-backed arbitrary request-time path is no longer a V1 blocker because the canonical V1 demonstration is offline-first. It remains available as a Post-V1 experiment.

## Remaining V1 completion gates

### Gate 19.9 — V1 Demonstration Contract + Current-State Synchronization — IN PROGRESS

Source issue: #376.

Goals:

- freeze V1 as demonstration/architecture lab;
- synchronize current-facing state with Gate 19.8 completion;
- add explicit `demonstration readiness != production readiness` semantics;
- record the remaining V1 completion sequence;
- keep AWS/Terraform/IAM/provider authority at zero.

No AWS or Terraform mutation is authorized.

### Gate 19.10 — Deterministic End-to-End Demo Runner — PLANNED

Implement one canonical offline runner that reuses existing typed OpsLens authorities rather than duplicating business logic.

Target command shape:

```bash
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
```

Required characteristics:

```text
AWS credentials required: NO
network required after setup: NO
third-party repository code execution: NO
stable JSON output: YES
human-readable output: YES
```

### Gate 19.11 — Curated Demo Scenarios + Deterministic Evaluation — PLANNED

Exactly three canonical scenario classes:

1. material vulnerability;
2. controlled benign;
3. fail-closed incomplete/ambiguous evidence.

Each scenario must be inert, content-addressed, reproducible, and regression-tested.

### Gate 19.12 — Minimal Local Visual Demo — PLANNED

Add a local-only presentation surface over the same admitted application contract.

It should show:

- scenario/repository identity;
- dependency evidence;
- vulnerability/risk findings;
- source provenance;
- AI explanation clearly separated from deterministic authority.

No public deployment is required.

### Gate 19.13 — Portfolio / README / Architecture Polish — PLANNED

Synchronize final public-facing material:

- README English and Portuguese;
- architecture diagram and narrative;
- deterministic authority vs AI reasoning table;
- measured latency/cost summary without production extrapolation;
- security/failure model;
- screenshots/terminal recording;
- three-to-five-minute demo walkthrough.

### Gate 19.14 — V1 Closeout + Release Readiness — PLANNED

Final requirements:

```text
clean-environment quickstart verified
full CI/security/CodeQL green
Phase 19 closeout evidence persisted
Phase 19 status COMPLETE
remaining ideas moved to Post-V1 backlog
HUMAN-reviewed v1.0.0 tag/release
```

## Post-V1 / experiments

The following may be explored later but are not blockers for V1:

- provider-backed request-time threat adapter;
- S3 vs Glue/Athena request-time comparison;
- public worker/API enablement;
- authentication and multi-tenancy;
- WAF/abuse controls/quotas;
- custom domain;
- production SLO/HA/DR;
- public MCP/A2A runtimes;
- AgentCore revisit if a concrete hosting requirement appears.

See [`post-v1-backlog.md`](post-v1-backlog.md).

## Current authority boundary

Until a separately reviewed gate changes the boundary:

```text
terraform plan/replan:                NOT AUTHORIZED
terraform apply:                       NOT AUTHORIZED
terraform destroy/replacement:         NOT AUTHORIZED
terraform import/state mutation:       NOT AUTHORIZED
AWS mutation:                          NOT AUTHORIZED
IAM mutation:                          NOT AUTHORIZED
artifact publication:                  NOT AUTHORIZED
public endpoint enablement:            NOT AUTHORIZED
submit enablement:                     NOT AUTHORIZED
worker enablement:                     NOT AUTHORIZED
event-source enablement:               NOT AUTHORIZED
provider-heavy live execution:         NOT AUTHORIZED
custom public domain publication:      NOT AUTHORIZED
```

## Controlling invariants

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
