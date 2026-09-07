# Phase 9 — Gate 9.3: Bounded Semantic Planning + Admission Handoff

_Date: 2026-09-07_

## Status

**IMPLEMENTED — final exact-head CI and protected merge pending.**

Starting main:

```text
ec09b8c17741aaf1b0e6c6710be15d3cc142c07d
```

Tracking:

```text
issue:  #128
PR:     #129
branch: feat/phase9-bounded-semantic-planning
```

## Goal

Freeze the public semantic-planning boundary over the verified Gate 9.2 repository evidence before any downstream public analysis execution exists.

Gate 9.3 is offline/fake-planner first. It introduces no public HTTP compute, new IAM, Athena call, Bedrock call, model call, retrieval, synthesis, or vulnerability/risk execution.

## Product-scope decision

The public v1 request contains no arbitrary natural-language question. Its operation is fixed:

```text
analyze_public_repository
```

Therefore the planner cannot define what the product operation means.

Deterministic public v1 policy owns the required evidence set:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

The tuple is canonicalized by existing Phase 8 evidence-need ordering. A planner proposal must contain the exact complete set.

This is intentionally stricter than accepting any syntactically valid `EvidenceNeed` combination.

## Contracts

```text
public-semantic-planning:v1
public-analysis-handoff:v1
```

Request bounds:

```text
planning request <= 2048 UTF-8 bytes
planner response <= 1024 bytes
planner calls per orchestration <= 1
application adaptive retries = 0
```

## Execution path

```text
PublicRepositoryEvidenceExecution
 -> build_public_semantic_planning_request
 -> bounded metadata-only JSON
 -> injected PublicSemanticPlanner.plan(...)
 -> untrusted response bytes
 -> strict JSON/output parsing
 -> exact public-v1 evidence-need admission
 -> HybridRoutingRequest
 -> existing route_evidence_request
 -> HYBRID + ALL_REQUIRED + STRUCTURED/SEMANTIC
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

There is no downstream evidence execution in this gate.

## Planner input minimization

Authorized planning metadata:

```text
contract / operation IDs
source execution ID + SHA-256
public request ID
immutable snapshot ID
immutable file evidence ID
normalized dependency count
unsupported package count
unsupported normalization count
allowed evidence-need catalog
```

Excluded:

```text
raw repository URL
uv.lock bytes
dependency names and versions
arbitrary repository text
repository instructions/prompts
executable repository content
credentials/secrets
SQL
provider/model/tool selection
```

The immutable file evidence ID can contain the allowlisted path name `uv.lock`. That is provenance identity, not file content. The initial test incorrectly treated the path substring itself as content leakage; the regression was corrected to test for actual dependency/file-content material instead.

## Deterministic admission

Planner JSON top-level keys are exact:

```json
{
  "planning_request_sha256": "...",
  "evidence_needs": ["..."]
}
```

Fail-closed conditions include:

```text
invalid UTF-8
invalid/non-object JSON
duplicate keys
missing/unknown keys
response over byte bound
wrong planning-request hash/replay
empty need set
non-string need
unknown EvidenceNeed
duplicate EvidenceNeed
missing mandatory public-v1 need
runtime_exposure proposal
source-execution rebinding
route/need disagreement
route != HYBRID
completeness != ALL_REQUIRED
required classes != STRUCTURED + SEMANTIC
planner exception
```

Planner exceptions are not retried by application orchestration.

## Handoff identity

`PublicAnalysisAdmissionHandoff` binds:

```text
source execution identity/hash
planning request identity
parsed proposal identity
deterministic Phase 8 route-decision identity
```

The handoff canonical representation contains identities only, not repository content.

## Regression coverage

Gate 9.3 tests prove:

- the full Gate 9.1 -> Gate 9.2 fake-source path can feed the planner boundary;
- successful v1 proposals resolve only through the existing Phase 8 route authority;
- planner input excludes raw repository URL and lockfile dependency content;
- equivalent evidence/proposals produce deterministic handoff identity;
- under-scoped plans fail closed;
- runtime-exposure plans fail closed;
- unknown/duplicate needs fail closed;
- malformed/oversized output fails closed;
- cross-request proposal replay fails closed;
- valid proposal/request pairs cannot be rebound to another Gate 9.2 execution;
- planner failure is called once and not adaptively retried.

## CI observations

Earlier branch CI observations were test-quality-only and did not change authority contracts:

1. Ruff required sorted `__all__` exports.
2. A test incorrectly asserted that the literal path name `uv.lock` could not appear inside immutable file-evidence identity. The test was corrected to distinguish provenance identity from repository content.

Before the final documentation/test commits, Python CI #355 / run `34082518433` passed all seven repository jobs; Public Analysis reported:

```text
Ruff:            PASS
Pyright strict:  PASS — 0 errors, 0 warnings, 0 informations
pytest:          PASS — 56 passed
```

A new exact-head CI is required because the source-execution regression and this documentation changed the branch head.

## AWS / provider changes

```text
real runtime GitHub calls: 0
AWS calls:                 0
Athena calls:              0
Bedrock calls:             0
model calls:               0
new AWS resources:         0
new IAM roles/policies:    0
```

The GitHub connector is used only to develop and review the repository, not by Gate 9.3 runtime/application tests.

## Architecture conclusion

The semantic planner exists to establish a future proposal boundary, not to invent authority that the fixed public v1 product does not need.

```text
model can propose
code defines public scope
Phase 8 code owns route
verified evidence owns repository identity
no admitted handoff means no downstream execution
```

ADR: `docs/adr/0030-public-semantic-planning-authority.md`.

## AIP-C01 learning notes

Gate 9.3 demonstrates:

```text
model output must be validated like untrusted input
context minimization is a security control
schema validity != semantic authorization
proposal != authorization
provenance binding prevents replay/rebinding
provider calls are not required to validate deterministic architecture boundaries
```

## Exit checklist

```text
[x] bounded metadata-only planner request
[x] bounded strict planner-output parser
[x] exact deterministic public-v1 need admission
[x] existing Phase 8 router remains route authority
[x] HYBRID + ALL_REQUIRED handoff invariant
[x] content-addressed handoff
[x] fail-closed malformed/under-scoped/runtime-exposure cases
[x] cross-execution rebinding regression
[x] planner failure no-retry regression
[x] ADR recorded
[x] lab recorded
[ ] final exact-head Python CI green
[ ] PR #129 ready for review
[ ] protected squash merge
[ ] issue #128 closed completed
[ ] postmerge current-state/roadmap sync
```
