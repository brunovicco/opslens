# ADR 0031 — Close Phase 9 at the Governed Application Boundary, Not at a Fictional Public Runtime

- Status: Accepted
- Date: 2026-09-07
- Phase: 9 — Public Analyze Your Repository
- Gate: 9.4 — Phase 9 Closeout

## Context

Phase 9 established a public-analysis **application boundary** in three executable gates:

```text
Gate 9.1  public-analysis-request:v1
Gate 9.2  public-repository-evidence:v1
Gate 9.3  public-semantic-planning:v1 + public-analysis-handoff:v1
```

The resulting path is:

```text
untrusted public request bytes
 -> deterministic request admission
 -> source-confirmed public repository metadata
 -> immutable commit/tree snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic parser + PyPI normalization
 -> content-addressed PublicRepositoryEvidenceExecution
 -> bounded metadata-only semantic planning proposal
 -> deterministic exact public-v1 scope admission
 -> existing Phase 8 hybrid route authority
 -> content-addressed PublicAnalysisAdmissionHandoff
 -> STOP
```

No Phase 9 gate deployed a public HTTP endpoint, runtime compute principal, public runtime IAM policy, rate limiter, abuse-protection service, concurrency controller, or production telemetry plane. Gate 9.3 also intentionally used injected fake repository/planner ports and made no real runtime GitHub, Athena, Bedrock, or model call.

Closing Phase 9 by declaring a production-ready public service would therefore be false. Conversely, forcing deployment into the closeout would combine architecture closure with a new runtime/security scope and weaken the incremental engineering loop.

## Decision

Phase 9 closes at the **governed application boundary**.

The following contracts are frozen as the Phase 9 baseline:

```text
public-analysis-request:v1
public-repository-evidence:v1
public-semantic-planning:v1
public-analysis-handoff:v1
```

Phase 9 does **not** claim that a public service has been deployed.

A future public runtime must be introduced as a separately scoped, measured implementation step with a concrete compute identity and least-privilege permissions.

## Frozen authority model

Deterministic code owns:

```text
public request admission
GitHub URL -> validated owner/name/ref coordinates
repository visibility and source-confirmed canonical identity
immutable commit/tree resolution
exact-commit file evidence admission
uv.lock parsing and PyPI normalization
public-v1 required evidence scope
semantic-plan proposal admission
hybrid route authority
request/source/proposal/handoff identity binding
failure/admission decisions
```

Models may propose within bounded contracts. They do not own repository truth, vulnerability/risk truth, runtime exposure, SQL authority, route authority, provider/model selection, evidence completeness, or execution authority.

Permanent distinctions remain:

```text
public request admitted != repository proven public != repository analyzed
planner proposal != execution authority
repository evidence != runtime exposure
semantic planning != SQL authority
application boundary validated != public runtime deployed
```

## Frozen Phase 9 budgets

Already-proven application bounds:

```text
public request body:              <= 2048 bytes
repository URL:                   <= Gate 9.1 bounded URL contract
semantic planning request:        <= 2048 UTF-8 bytes
semantic planner response:        <= 1024 bytes
planner invocations/orchestration <= 1
application adaptive retries:     0
```

Gate 9.2 repository acquisition remains bounded, GET-only, and exact-commit for admitted inert evidence. Third-party repository code is never executed.

These are application-contract bounds, not public infrastructure quotas.

## Failure taxonomy

Phase 9 fail-closed categories include:

```text
transport/request byte admission failure
UTF-8 / JSON / duplicate-key / unknown-field failure
repository URL grammar/admission failure
repository metadata/visibility failure
requested-ref/default-branch resolution failure
immutable commit/tree resolution failure
exact-commit file evidence failure
file/parser/normalization provenance mismatch
semantic planning request identity mismatch
planner invocation failure
planner output size/UTF-8/JSON/schema failure
unknown/duplicate/out-of-authority evidence need
under-scoped public-v1 proposal
runtime_exposure proposal
proposal replay/request-hash mismatch
source-execution rebinding
Phase 8 route/completeness/class disagreement
handoff identity mismatch
```

Any failed stage produces no later authority object. Gate 9.3 performs no adaptive re-prompting.

## Runtime and IAM decision

No speculative public runtime role, endpoint, or permission set is created in Gate 9.4.

This is intentional least privilege:

```text
no concrete compute principal
 -> no runtime role
 -> no speculative permissions
```

Before a public runtime exists, its exact responsibilities must be known. The future role must be derived from those responsibilities and from already-proven service boundaries, not from broad Phase 9 aspirations.

Potential service permissions already evidenced elsewhere in OpsLens — such as bounded GitHub transport, read-only Athena, direct Bedrock Retrieve, and approved model invocation — remain separate responsibilities and must not be automatically aggregated into one public role.

## Launch prerequisites intentionally deferred

Before a real public launch, the project still requires a concrete design and measured validation for:

```text
public HTTP compute / endpoint
runtime identity and least-privilege IAM
request timeout budget
concurrency limits
rate limiting
abuse controls
quota enforcement
cache policy if justified
kill switch / disable path
cost guardrails and attribution
request-level telemetry
production error/latency distributions
workload-derived SLOs and alerts
operational rollback / incident procedures
```

These prerequisites are not waived by Phase 9 completion.

## Cost boundary

Phase 9 does not invent a full per-request cost.

Current cost evidence remains stage-specific:

```text
Athena bytes/scans where executed
S3 Vectors / retrieval units where executed
model input/output tokens where executed
provider/request latency where executed
```

Gate 9.3 executed no real provider/model path. Therefore Phase 9 closeout adds no synthetic model/runtime cost estimate.

Any future public-runtime USD estimate requires a versioned pricing contract or bill-level reconciliation and must include infrastructure and abuse/concurrency assumptions.

## Observability boundary

Phase 9 currently preserves deterministic IDs, hashes, provenance, route/admission decisions, failure categories, and test evidence.

It does not claim:

```text
public-user traces
production request volume
production p95/p99 latency
production error rates
production throttling behavior
production cost/request
production SLO compliance
```

Future telemetry should prefer content-free metadata, hashes, stage IDs, and bounded diagnostics over automatic logging of user/source/model content.

## Phase 10 entry criteria

Phase 10 — Observability & Operational Excellence may begin after Phase 9 closes with these invariants preserved:

1. `public-analysis-request:v1`, `public-repository-evidence:v1`, `public-semantic-planning:v1`, and `public-analysis-handoff:v1` remain versioned boundaries.
2. Public input never becomes arbitrary fetch, SQL, tool, model, or execution authority.
3. Third-party repository code is never executed.
4. Repository risk remains distinct from runtime exposure.
5. Phase 8 remains hybrid route/evidence authority.
6. Semantic planning remains proposal-only and content-minimized.
7. Failure at any admission stage prevents downstream execution.
8. No speculative IAM expansion occurs before a concrete runtime identity exists.
9. Production SLOs/alerts require deployed workload evidence.
10. Observability work must not weaken existing privacy/provenance boundaries.
11. New runtime/provider/retrieval changes require their own measured hypotheses and exact-head CI.
12. Long-lived Governed LLM Gateway PR #89 remains deferred until separately re-evaluated against the then-current architecture.

## Consequences

### Positive

- Phase 9 closes with claims supported by real repository evidence and CI rather than aspirational deployment language.
- Least privilege is preserved by refusing to create an unused runtime principal.
- Runtime security and operational controls remain explicit work rather than implicit assumptions.
- Phase 10 receives stable application contracts on which to design telemetry.
- The portfolio demonstrates that architecture completion and production deployment are deliberately different milestones.

### Trade-offs

The repository still does not expose the intended public demo over HTTP. That is an explicit deferred implementation gap, not hidden debt.

Phase 10 may need a small concrete runtime slice before some observability dimensions can be measured. If so, that runtime slice must be scoped as observable infrastructure, not silently backfilled into Phase 9.

## Alternatives rejected

### Declare Phase 9 production-ready

Rejected because no public runtime has been deployed or measured.

### Add a broad public runtime role during closeout

Rejected because no concrete compute principal exists and broad permissions would violate least privilege.

### Deploy HTTP compute inside Gate 9.4

Rejected because deployment, abuse controls, IAM, and production telemetry are a new implementation surface rather than closeout documentation.

### Treat fake-port CI as production evidence

Rejected because deterministic application tests prove contracts, not production workload behavior.

## Security properties

```text
Agents reason. Code verifies evidence.
READ, NEVER EXECUTE third-party repository code.
Repository Risk != Runtime Exposure.
Intent classification != execution authority.
No unrestricted text-to-SQL.
application boundary validated != public runtime deployed
```

## AIP-C01 learning notes

This closeout illustrates production GenAI architecture principles relevant to AIP-C01:

- build deterministic authorization/admission around model proposals;
- minimize model context and output surface;
- preserve provenance across asynchronous/external boundaries;
- create IAM only for concrete workloads;
- distinguish evaluation evidence from production observability;
- measure cost from real service/runtime evidence rather than invented blended estimates;
- use staged architecture gates so provider/runtime complexity is introduced only when justified.
