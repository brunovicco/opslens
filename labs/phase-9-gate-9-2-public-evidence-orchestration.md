# Phase 9 — Gate 9.2: Public Repository Evidence Orchestration

_Date: 2026-09-07_

## Status

**IN PROGRESS — offline implementation complete; exact-head PR CI and merge pending.**

Starting point:

```text
main:   a3ae763b7b18178b792ee932bb32d1542193c568
issue:  #125
branch: feat/phase9-public-evidence-orchestration
```

## Goal

Bind the already-admitted Gate 9.1 public request to exact immutable repository dependency evidence without allowing the original user URL to become transport authority.

Gate 9.2 is intentionally narrower than the complete public product path. It stops after verified `uv.lock` parsing and deterministic PyPI normalization.

## Reused architecture decisions

No new AWS or model architecture decision is required for this gate. Gate 9.2 composes already-accepted contracts:

```text
ADR 0009  immutable public repository snapshot
ADR 0010  bounded read-only GitHub REST transport
ADR 0011  immutable uv.lock evidence
ADR 0012  deterministic uv.lock parser
ADR 0013  Phase 3 PyPI normalization bridge
ADR 0029  public repository request -> validated coordinates, not fetch URL
```

A new ADR is therefore not created merely to restate composition.

## Contract

```text
public-repository-evidence:v1
```

Execution shape:

```text
PublicAnalysisRequest
 -> validated owner/name/ref only
 -> resolve_github_repository_snapshot
 -> GitHub source metadata proves public visibility
 -> source-declared default branch or explicit requested ref
 -> exact commit SHA + tree SHA
 -> acquire_uv_lock_evidence at exact commit SHA
 -> parse_uv_lock_evidence
 -> normalize_uv_lock_pypi_dependencies
 -> PublicRepositoryEvidenceExecution
```

The execution is content-addressed from the admitted request identity plus exact source-confirmed repository, snapshot, file, parsed-lock, and normalization evidence.

## Authority preservation

### Raw URL does not return

Gate 9.1 accepted a GitHub web URL only long enough to reduce it to validated coordinates. `PublicAnalysisRequest` contains no arbitrary fetch URL.

Gate 9.2 source calls therefore receive only:

```text
get_repository(owner, name)
get_commit(canonical_owner, canonical_name, ref)
get_uv_lock(canonical_owner, canonical_name, commit_sha)
```

No arbitrary scheme, host, path, query, fragment, or userinfo can re-enter acquisition through the public request.

### Repository rename/canonicalization remains source authority

The initial lookup uses the admitted coordinates. GitHub metadata may then confirm a different canonical owner/name, for example after a repository rename.

Gate 9.2 deliberately preserves the existing Phase 4 rule:

```text
requested coordinates
 -> source metadata
 -> canonical source-confirmed repository identity
 -> later reads use canonical coordinates
```

This avoids making stale user-facing owner/name coordinates stronger than repository source evidence.

### Moving ref is not file authority

For a null public `requested_ref`, the existing resolver uses the source-declared default branch. It does not invent `main`.

For an explicit ref, that ref is used only to resolve an immutable snapshot.

After resolution:

```text
moving/default ref -> provenance
exact commit SHA   -> file acquisition authority
```

`uv.lock` is always acquired against the resolved commit SHA.

### Public admission is still not analysis truth

Gate 9.2 establishes immutable dependency evidence only:

```text
public request admitted
 -> repository proven public
 -> immutable snapshot resolved
 -> inert uv.lock verified
 -> dependency inventory parsed/normalized
```

It still does **not** establish:

```text
vulnerability applicability
NVD/CVSS enrichment
KEV membership
EPSS score
Risk Policy priority
semantic remediation evidence
hybrid synthesis
runtime exposure
```

Those remain downstream authorities and later Phase 9 gates.

## Content-addressed execution identity

`PublicRepositoryEvidenceExecution.canonical_json` binds:

```text
public request ID/SHA
requested lookup coordinates
source-confirmed repository numeric/canonical identity
resolved ref/default-branch provenance
commit SHA
tree SHA
snapshot ID
uv.lock evidence ID/blob SHA/content SHA/size
parser schema/revision/accounting
unsupported package accounting
normalized dependency identities/purls
unsupported normalization accounting
```

The execution ID is:

```text
public-repository-evidence:v1@sha256:<digest>
```

Cross-request, cross-snapshot, cross-file, parsed-lock, or normalization composition drift fails closed before an execution object is admitted.

## External-call budget

CI uses a fake source implementing the existing read-only source protocols.

Successful logical call budget:

```text
get_repository: 1
get_commit:     1
get_uv_lock:    1
```

Gate 9.2 implementation/CI budget:

```text
real GitHub runtime calls: 0
real AWS calls:            0
Athena calls:              0
Bedrock calls:             0
model calls:               0
new AWS resources:         0
new IAM roles:             0
new IAM permissions:       0
```

## Failure behavior

The orchestration preserves existing typed failures rather than collapsing them into a generic public success:

```text
private/non-public repository
 -> fail before commit/file acquisition

malformed source repository/commit evidence
 -> fail before downstream evidence admission

invalid/malformed uv.lock
 -> fail before normalization/public execution

request/resolution coordinate drift
 -> fail PublicRepositoryEvidenceExecution admission

cross-snapshot file evidence
 -> fail PublicRepositoryEvidenceExecution admission
```

There is no fallback to another repository, ref, file, parser, ecosystem, or model.

## Test coverage

The Gate 9.2 regressions prove:

```text
null ref uses source-declared default branch
explicit ref is preserved only through snapshot resolution
file acquisition uses exact commit SHA
source-confirmed repository rename becomes canonical after initial lookup
normalized PyPI identity remains Phase 3 authority
unsupported local package remains explicitly accounted
same request + same evidence -> same execution identity
canonical execution does not contain repository_url fetch authority
private repository fails before commit/file calls
malformed uv.lock fails closed
request/resolution drift is rejected
cross-snapshot file evidence is rejected
```

## CI requirement

The existing Public Analysis Python CI slice owns Gate 9.2:

```text
uv lock --check
Ruff public analysis
Pyright strict public analysis
pytest tests/unit/public_analysis
```

No merge is authorized until the exact PR head is green across the complete repository Python workflow.

## Next boundary

Gate 9.3 may only begin after Gate 9.2 merge.

The next deterministic composition should consume `PublicRepositoryEvidenceExecution` and add existing threat-intelligence/repository-analysis/risk authorities without exposing arbitrary public tool/query authority.

A likely path is:

```text
PublicRepositoryEvidenceExecution
 -> bounded source-selected GHSA/NVD/KEV/EPSS evidence
 -> existing deterministic repository analysis
 -> existing Risk Policy v1
 -> typed public structured-analysis result
```

Semantic/hybrid remediation synthesis should remain a later independently bounded step so structured repository truth is testable before model usage.

## AIP-C01 learning notes

Gate 9.2 demonstrates a core production AI-platform security pattern:

> Resolve mutable user references into immutable source evidence before they can authorize downstream work.

The same principle appears in model/tool systems as:

```text
user tool name -> allowlisted tool identity
user resource URL -> validated coordinates -> immutable resource identity
natural-language query -> typed query -> deterministic compiler
retrieval result -> admitted evidence identity
model citation -> allowlisted canonical evidence ID
```

A moving name/ref is useful provenance, but immutable evidence should own the action boundary whenever the system can establish it.

## Exit checklist

```text
[x] Gate 9.1 request authority reused
[x] raw URL absent from source-call authority
[x] source-confirmed public repository identity preserved
[x] default branch remains source evidence
[x] exact commit owns uv.lock acquisition
[x] existing inert parser reused
[x] existing PyPI normalization authority reused
[x] content-addressed public evidence execution
[x] source rename/canonicalization semantics preserved
[x] bounded fake-source call accounting
[x] no AWS/model/public runtime change
[ ] exact-head PR CI green
[ ] protected squash merge
[ ] issue #125 closed / completed
[ ] authoritative state synchronized to Gate 9.3 NEXT
```
