# OpsLens — Current State

_Last updated: 2026-09-12_

## Authoritative protected checkpoint

```text
protected main SHA: 68a135a0c80dacb8cf0b668022796b159878637e
protected merge: PR #377 — Gate 19.9 V1 demonstration closeout contract
post-merge CodeQL: 34715722016 / run #414 / success
Gate 19.9 issue: #376 / closed completed
```

## Retained Phase 18 closeout checkpoint

The historical Phase 18 closeout remains immutable and current-facing documentation retains its protected checkpoint explicitly:

```text
Phase 18 — Evaluation, Cost & Portfolio Readiness
status: COMPLETE
protected closeout SHA: feca774535b7d83f57c26f4e9fe7da71ce268f0f
Phase 19 — Bounded Public Runtime & Productization
```

Phases 0–18 are complete. Phase 19 remains the only active phase.

## Retained Phase 17 security lineage

Gate 17.1 — evidence-first threat/control-gap inventory — COMPLETE.  
Gate 17.2 — CI/CD and workflow authority hardening — COMPLETE.

Both remain authoritative. The Phase 19 V1 demonstration closeout adds no exception to their workflow, IAM, least-privilege, telemetry, or protected-main controls.

## Phase 19 status

```text
19.1  Public Runtime Hypothesis & Launch Contract              COMPLETE
19.2  Representative Workload Measurement                     COMPLETE
19.3  Concrete Async Topology Contract                         COMPLETE
19.4  Disabled Async Runtime Implementation                    COMPLETE
19.5  Immutable Async Deployment Artifacts                     COMPLETE
19.6  Exact Terraform Plan & Offline Admission                 COMPLETE
19.7  Controlled Disabled Runtime Materialization              COMPLETE
19.8  Request-time Threat Evidence Authority Contract          COMPLETE
19.9  V1 Demonstration Closeout Contract                       COMPLETE
19.10 Deterministic End-to-End Demo Runner                     IN PROGRESS
19.11 Curated Demo Scenarios + Deterministic Evaluation        PLANNED
19.12 Minimal Local Visual Demo                                PLANNED
19.13 Portfolio / README / Architecture Polish                 PLANNED
19.14 V1 Closeout + Release Readiness                          PLANNED
```

## Retained Gate 19.1/19.2 historical decision markers

These strings are retained deliberately because later gates must not rewrite the evidence that selected and then measured the async hypothesis:

```text
Gate 19.1
historical runtime decision: DEFERRED_PENDING_MEASUREMENT
PublicAnalysisAdmissionHandoff -> STOP
Gate 19.2 — Representative Workload Measurement              COMPLETE
ASYNC_SUBMIT_STATUS_RESULT
```

## Retained Gate 19.7/19.8 source lineage

Gate 19.8 was developed from the final Gate 19.7 protected checkpoint, so that historical source remains explicit even though protected `main` has advanced:

```text
Gate 19.8 source protected main: 8700478c7fca230e5984c3ce034194ea3bd337e4
Gate 19.7 final post-merge CodeQL: 34711607099 / run #382 / success
Gate 19.8 issue: #374
physical access decision: DEFERRED_PENDING_BOUNDED_RUNTIME_ADAPTER_EVIDENCE
```

Gate 19.9 source issue: #376.  
Gate 19.9 source protected main: `e538fa3e96c29cf76dd3aa83a9967e090587b6fb`.  
Gate 19.9 protected merge: PR #377 / `68a135a0c80dacb8cf0b668022796b159878637e`.  
Gate 19.9 post-merge CodeQL: `34715722016` / run #414 / success.

Gate 19.10 source issue: #378.  
Gate 19.10 source protected main: `68a135a0c80dacb8cf0b668022796b159878637e`.  
Gate 19.10 implementation PR: #379 / draft while exact-head evidence is verified.

## V1 product boundary

OpsLens V1 is intentionally a **demonstration and architecture lab**, not a production SaaS.

The canonical V1 reviewer experience is:

```text
clone
 -> setup
 -> one deterministic offline demo command
 -> evidence-backed result
```

The canonical authority chain remains:

```text
public repository evidence
 -> inert dependency evidence
 -> structured threat evidence
 -> deterministic applicability/correlation
 -> deterministic risk prioritization
 -> bounded retrieval/reasoning where appropriate
 -> evidence-backed result
```

V1 completion optimizes for reproducibility, provenance, architectural clarity, meaningful failure paths, and portfolio presentation. Production operations are not a V1 completion requirement.

See:

- [`v1-demonstration-scope.md`](v1-demonstration-scope.md)
- [`v1-completion-checklist.md`](v1-completion-checklist.md)
- [`post-v1-backlog.md`](post-v1-backlog.md)
- [`demo/README.md`](demo/README.md)
- [`../labs/phase-19-gate-19-9-v1-demonstration-contract.md`](../labs/phase-19-gate-19-9-v1-demonstration-contract.md)
- [`../labs/phase-19-gate-19-10-demo-runner.md`](../labs/phase-19-gate-19-10-demo-runner.md)

## Gate 19.8 retained result

Gate 19.8 closed the provider-neutral application authority required to express request-time threat evidence without choosing a physical provider adapter by preference.

```text
PublicRepositoryEvidenceExecution
 -> PublicThreatEvidenceScope
 -> PublicThreatEvidenceRequest
 -> PublicThreatEvidenceAuthority
 -> PublicRepositoryThreatEvidence
 -> retained deterministic Phase 3/4 correlation/enrichment
```

Retained semantics:

```text
scope derives only from admitted repository evidence
incomplete PyPI normalization -> fail closed
out-of-scope GHSA evidence -> reject
unrelated NVD evidence -> reject
latest_complete = deterministic selection policy, not provenance
selected KEV/EPSS evidence retains exact snapshot date + SHA-256
model authority for source truth/applicability = none
```

The physical provider adapter remains intentionally deferred. It is no longer a V1 blocker because V1 uses an offline-first deterministic demo path. A provider-backed arbitrary request-time adapter is now a Post-V1 experiment unless a future concrete requirement promotes it.

## Gate 19.10 current implementation slice

Gate 19.10 turns the V1 reviewer contract into one executable, provider-free path while preserving the same deterministic business authority used elsewhere in OpsLens.

Canonical command:

```bash
uv sync --frozen
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
```

Machine-readable projection:

```bash
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format json
```

Current admitted scenario:

```text
scenario: material-vulnerability
fixture: synthetic / inert / offline
repository code execution: NO
live provider calls: NO
model execution: NO
expected finding count: 1
expected deterministic Risk Policy v1 result: 90 / P0
```

The synthetic fixture is demonstration evidence only and does not claim to describe or scan a live repository. Gate 19.11 owns the additional controlled-benign and fail-closed incomplete/ambiguous scenario classes.

## Retained AWS runtime truth

Gate 19.7 materialized the selected async topology in AWS and then proved convergence without enabling public/provider-heavy execution.

```text
selected topology: HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
public async runtime resources materialized: 21 managed resources
Terraform state lineage: 6c958ab2-4cc6-7f96-a528-89535504f65c
Terraform state serial: 117
public endpoint enabled: NO
submit path enabled: NO
worker enabled: NO
SQS -> worker event-source mapping enabled: NO
custom public domain: absent
provider-heavy public executions: 0
third-party repository code executions: 0
```

The materialized runtime remains architecture evidence only.

```text
materialized != enabled
```

## Retained measured evidence

The representative Gate 19.2 execution remains the main Phase 19 live provider measurement:

```text
end_to_end_duration_ms: 17748
serialized_result_bytes: 5285
GitHub physical HTTP requests: 4 MEASURED
Athena query count: 0 NOT_APPLICABLE
Bedrock Retrieve count: 1 MEASURED
Bedrock Retrieve client elapsed ms: 4148 MEASURED
Bedrock model call count: 1 MEASURED
Bedrock input tokens: 5936 MEASURED
Bedrock output tokens: 408 MEASURED
Bedrock model client elapsed ms: 8901 MEASURED
Bedrock provider latency ms: 7772 MEASURED
retry count: 0 MEASURED
throttle count: 0 UNMEASURED
```

That run supports an architectural latency/cost discussion. It is not a production SLO or production TCO claim.

## V1 explicit non-goals

The following are not required for the first release:

```text
Internet-facing production runtime
authentication / OIDC / Cognito
multi-tenancy
commercial quotas or billing
custom public domain
WAF or production abuse controls
24x7 operations or on-call
production SLO/SLA
HA/DR program
production TCO claim
public worker enablement
event-source enablement
provider-backed arbitrary request-time threat adapter
```

## Current authority boundary

Gate 19.10 is repository-only and offline-only.

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
model execution for demo:              NOT AUTHORIZED
custom public domain publication:      NOT AUTHORIZED
```

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work and is not part of the V1 closeout path.

## Next implementation slice

Gate 19.10 is the active slice. It closes only after exact-head CI/security/CodeQL, HUMAN protected merge, and post-merge verification.

After Gate 19.10 closes, Gate 19.11 will add the remaining two canonical scenario classes and deterministic evaluation over the same runner boundary.

## Permanent invariants

```text
Agents reason. Code verifies evidence.
Not every question is a RAG problem.
Structured facts use structured retrieval.
No unrestricted text-to-SQL.
READ, NEVER EXECUTE third-party repository code.
Repository Risk != Runtime Exposure.
retrieved content != instruction authority
model proposal != authorization
tool/protocol success != business truth
historical evidence != standing authority
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
