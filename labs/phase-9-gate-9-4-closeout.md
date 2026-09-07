# Phase 9 — Gate 9.4: Public Analysis Closeout

_Date: 2026-09-07_

## Status

**CLOSEOUT IMPLEMENTED — protected merge pending.**

Starting main:

```text
6e0c595d5d2437dabd94365e1eeb88800a5bcab4
```

Tracking:

```text
issue:  #131
branch: docs/phase9-closeout
```

## Goal

Close Phase 9 at the application boundary that was actually implemented and validated across Gates 9.1–9.3.

The closeout does not claim a public production runtime, endpoint, IAM role, workload distribution, SLO, or cost profile that does not exist.

## Frozen Phase 9 contracts

```text
Gate 9.1  public-analysis-request:v1
Gate 9.2  public-repository-evidence:v1
Gate 9.3  public-semantic-planning:v1
          public-analysis-handoff:v1
```

Combined governed boundary:

```text
untrusted public JSON
 -> strict bounded request admission
 -> validated GitHub owner/name/ref coordinates
 -> source-confirmed public repository identity
 -> immutable commit/tree snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic parser + PyPI normalization
 -> PublicRepositoryEvidenceExecution
 -> bounded metadata-only semantic planning proposal
 -> deterministic exact public-v1 scope admission
 -> existing Phase 8 hybrid route authority
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

## Gate evidence

Gate 9.1:

```text
PR #123 head:                    26f0d2b5275284d891ee99a7f8276d41cc4f0753
Python CI #346 / run 34079446683: PASS
Public Analysis pytest:          33 passed
merge SHA:                       5540d7b508c71aa65d826786618690b7ddc9d433
issue #122:                      CLOSED / COMPLETED
```

Gate 9.2:

```text
PR #126 head:                    0fdc6c435c0f2891b6730f61bd73ad7f32ca8213
Python CI #349 / run 34080376506: PASS
Public Analysis pytest:          41 passed
merge SHA:                       b152a21bf9d0807ac40083c609ea434f32ccb671
issue #125:                      CLOSED / COMPLETED
```

Gate 9.3:

```text
PR #129 head:                    34cea42a0ce37cbfa06b33d57f081403edba2552
Python CI #358 / run 34082791753: PASS
Public Analysis Ruff:            PASS
Public Analysis Pyright strict:  PASS — 0 errors, 0 warnings, 0 informations
Public Analysis pytest:          57 passed
merge SHA:                       6f53537c227cade688091187eac1074645e11bf0
issue #128:                      CLOSED / COMPLETED
```

## Public v1 scope and budgets

```text
operation: analyze_public_repository
required needs:
  remediation_guidance
  risk_priority
  vulnerability_facts
```

Successful admission must agree with Phase 8 authority:

```text
HYBRID
ALL_REQUIRED
STRUCTURED + SEMANTIC
```

Already-proven application bounds:

```text
public request body:              <= 2048 bytes
semantic planning request:        <= 2048 UTF-8 bytes
semantic planner response:        <= 1024 bytes
planner calls per orchestration:  <= 1
adaptive application retries:     0
```

These are application bounds, not public runtime rate/concurrency/timeout/quota controls.

## Authority and failure taxonomy

Deterministic code owns public request admission, GitHub coordinate grammar, source-confirmed repository identity, immutable snapshot/file evidence, `uv.lock` parsing, PyPI normalization, public-v1 evidence scope, planner-output admission, Phase 8 route authority, request/source/proposal/handoff binding, and fail-closed execution admission.

Models may propose or synthesize only inside bounded contracts. They do not own structured truth, product scope, repository truth, vulnerability/risk truth, runtime exposure, SQL, route, provider/model selection, evidence completeness, or execution authority.

Fail-closed classes include:

```text
request byte/UTF-8/JSON/field failure
repository URL grammar failure
repository metadata/visibility failure
ref/default-branch resolution failure
commit/tree/file evidence failure
file/parser/normalization provenance mismatch
planner request binding/invocation failure
planner response size/UTF-8/JSON/schema failure
unknown/duplicate/out-of-authority evidence need
under-scoped public-v1 proposal
runtime_exposure proposal
proposal replay/request-hash mismatch
source-execution rebinding
Phase 8 route/completeness/class mismatch
handoff identity mismatch
```

A failed stage never creates a later authority object.

## Runtime / IAM closeout decision

```text
public HTTP compute:      NOT DEPLOYED
public endpoint:          NOT DEPLOYED
public runtime principal: DOES NOT EXIST
new Phase 9.4 IAM:        NONE
new Phase 9.4 AWS:        NONE
```

This is intentional least privilege:

```text
no concrete compute principal
 -> no runtime role
 -> no speculative permission aggregation
```

## Cost and observability boundary

Phase 9 adds no synthetic public-request cost. Current cost evidence is stage-local only when the stage actually runs. Gate 9.3 made zero real provider/model calls.

Phase 9 evidence includes content-addressed IDs/hashes, provenance, admission/route identities, bounded failure categories, and exact-head CI. It does not claim public request volume, production traces, p95/p99, production error/throttle rates, production request cost, or production SLO compliance.

Future telemetry should prefer content-free IDs/hashes/stage metadata over automatic user/source/model-content logging.

## Public-launch prerequisites

Still required before a real public launch:

```text
concrete HTTP compute + endpoint
runtime identity + least-privilege IAM
timeout budget
concurrency limits
rate limiting
abuse protection
quota enforcement
cache policy only if measured/justified
kill switch / disable path
deployment rollback
cost guardrails + attribution
production telemetry
workload-derived SLOs + alerts
incident / operational playbook
```

Phase 9 completion does not waive these requirements.

## Phase 10 entry criteria

Phase 10 — Observability & Operational Excellence may begin only with these constraints frozen:

1. Phase 9 contracts remain versioned boundaries.
2. Public input never becomes arbitrary fetch, SQL, tool, provider/model, or execution authority.
3. Third-party repository code is never executed.
4. Repository risk remains distinct from runtime exposure.
5. Phase 8 remains hybrid route/evidence authority.
6. Semantic planning remains proposal-only and content-minimized.
7. Failure at any admission stage prevents downstream execution.
8. IAM is introduced only for a concrete runtime identity.
9. Production SLO/alert claims require deployed workload evidence.
10. Observability cannot weaken privacy, provenance, or content-minimization boundaries.
11. New runtime/provider/retrieval changes require separately versioned hypotheses and exact-head validation.
12. Governed LLM Gateway PR #89 remains deferred until separately re-evaluated.

## Deferred decisions

```text
public compute runtime
runtime cache
reranking
keyword + vector hybrid search
alternative embeddings/vector store
agents
MCP
AgentCore
A2A
runtime exposure / Inspector integration
Governed LLM Gateway merge
```

## AIP-C01 learning notes

```text
application contract != production deployment
LLM proposal != authorization
schema validity != semantic authorization
least privilege means no role before a workload exists
provenance binding prevents replay/rebinding
evaluation CI != production observability
cost estimates require measured/versioned assumptions
```

## Architecture records

```text
ADR 0029  public repository request admission
ADR 0030  public semantic planning is proposal-only
ADR 0031  Phase 9 closes at governed application boundary
```

## Exit checklist

```text
[x] Phase 9 contracts consolidated
[x] authority taxonomy frozen
[x] fail-closed taxonomy frozen
[x] runtime/IAM decision frozen
[x] application budgets frozen
[x] cost boundary frozen
[x] observability boundary frozen
[x] launch prerequisites explicit
[x] Phase 10 entry criteria explicit
[x] ADR 0031 recorded
[x] closeout lab recorded
[x] README EN/PT-BR synchronized
[x] architecture EN/PT-BR synchronized
[x] docs/ADR indexes synchronized
[x] current-state/roadmap synchronized for Phase 9 closeout
[ ] closeout PR reviewed/mergeable
[ ] protected squash merge
[ ] issue #131 CLOSED / COMPLETED
```

## Next authorized step

After the protected closeout merge:

```text
Phase 10 — Observability & Operational Excellence
```
