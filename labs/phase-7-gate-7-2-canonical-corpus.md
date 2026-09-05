# Phase 7 — Gate 7.2: Reproducible Canonical Corpus

_Date: 2026-09-04_

## Purpose

Build a reproducible, content-addressed knowledge corpus from explicitly authorized explanatory and remediation sources before any vector infrastructure exists.

Gate 7.2 is deliberately separate from Gate 7.3. This gate does not create a Bedrock Knowledge Base, vector store, embedding job, IAM role, or paid AWS retrieval/generation call.

## Dependency

Gate 7.1 is complete and squash-merged through PR #93:

```text
main commit: f2e3b72c31d0713707857bc0867a7f59e667b9dd
```

The frozen Gate 7.1 golden fixture defines six positive document identities and eight expected chunk identities. Gate 7.2 must materialize those expectations without widening the structured-fact authority boundary.

## Target flow

```text
trusted pinned source registry
 -> bounded GET-only raw-source acquisition
 -> exact source bytes + source_bytes_sha256
 -> deterministic text normalization
 -> curated deterministic section selection
 -> KnowledgeDocument + content_sha256
 -> canonical chunks + chunk_content_sha256
 -> canonical corpus manifest
```

## Important design refinement

The initial Gate 7.2 draft considered fetching the mutable human-facing documentation pages directly.

That design was rejected before corpus materialization because hashing a mutable `latest` page detects drift but does not guarantee that the same corpus can be reconstructed after the site changes.

Gate 7.2 v1 therefore separates two identities:

```text
canonical_uri
  human-facing published documentation/advisory URL

upstream_repository + upstream_commit_sha + upstream_path
  immutable official source file used to build the corpus
```

The actual acquisition URI is not caller-controlled. It is derived deterministically from the pinned source coordinates and always uses:

```text
https://raw.githubusercontent.com/<owner>/<repo>/<40-hex-commit>/<path>
```

This keeps public provenance readable while making corpus construction replayable.

## Source registry v1

Registry identity:

```text
knowledge-source-registry:v1
```

Pinned authorized inputs:

| Document ID | Published provenance | Immutable source |
| --- | --- | --- |
| `knowledge-doc:pypa-dependency-management:v1` | pip Dependency Resolution | `pypa/pip@173eb9b...:docs/html/topics/dependency-resolution.md` |
| `knowledge-doc:uv-locking:v1` | uv Locking and syncing | `astral-sh/uv@3c979ab...:docs/concepts/projects/sync.md` |
| `knowledge-doc:pypa-secure-installs:v1` | pip Secure installs | `pypa/pip@173eb9b...:docs/html/topics/secure-installs.md` |
| `knowledge-doc:vendor-advisory-reading:v1` | Django 6.0.8 release notes | `django/django@b3f4d83...:docs/releases/6.0.8.txt` |
| `knowledge-doc:dependency-remediation-validation:v1` | OWASP Vulnerable Dependency Management | `OWASP/CheatSheetSeries@8c3ce8e...:cheatsheets/Vulnerable_Dependency_Management_Cheat_Sheet.md` |
| `knowledge-doc:pypa-version-specifiers:v1` | PyPA Version specifiers | `pypa/packaging.python.org@cee95c2...:source/specifications/version-specifiers.rst` |

Every commit is stored as a full lowercase 40-hex SHA in the checked-in registry. Abbreviations above are documentation only.

The source registry is an authorization artifact, not the corpus manifest. It intentionally does not claim that source bytes have already been acquired.

## Authority boundary

These sources are authorized only for explanatory/remediation knowledge.

They do not become authoritative structured sources for:

```text
NVD/CVE observations
CISA KEV membership
FIRST EPSS scores
CVSS observations
GHSA vulnerable-range applicability
repository dependency versions
runtime exposure/reachability
Risk Policy scores
```

A vendor release note may mention CVEs, severity, or a remediation as explanatory evidence. OpsLens structured vulnerability truth continues to come from the deterministic Phase 2–6 authorities.

## Bounded acquisition contract

Implemented `BoundedHttpsKnowledgeSource` using the same narrow network principles already proven by Repository Intelligence:

```text
fixed host:       raw.githubusercontent.com
method:           GET only
source target:    derived from repository + full commit SHA + path
timeout:          10 s default; <= 30 s
response budget:  2 MiB default; <= 8 MiB configurable
redirects:        not followed
automatic retry:  none
credentials:      none
Accept-Encoding:  identity
accepted media:   text/plain or text/markdown
```

The adapter reads at most `max_response_bytes + 1`, rejects declared or observed oversized responses, rejects non-200 status, unexpected media type, compressed content, and empty bodies, and always closes the connection.

The human-facing `canonical_uri` is provenance only. Changing its query/fragment/path cannot change the acquisition target.

## Raw source identity

Successful acquisition produces typed `AcquiredKnowledgeSource` evidence:

```text
descriptor
body
content_type
byte_count
source_bytes_sha256
```

`source_bytes_sha256` is calculated over the exact admitted HTTP body bytes before decoding or normalization.

This identity is intentionally distinct from the later:

```text
KnowledgeDocument.content_sha256
```

The first answers which upstream bytes were observed. The second answers which normalized/curated document text entered the canonical corpus.

## Why source registry and corpus manifest are separate

```text
source registry
  Which immutable official inputs is OpsLens authorized to acquire?

corpus manifest
  Which exact bytes were acquired and which normalized documents/chunks were produced?
```

This separation prevents a normalized text hash from hiding upstream byte changes or normalization drift.

## Security boundary

Gate 7.2 currently proves:

- exact GitHub `owner/repository` syntax;
- full immutable commit SHA required; mutable refs such as `main` rejected;
- clean repository-relative path; traversal segments rejected;
- acquisition host fixed by code, not registry/user input;
- HTTPS standard-library transport only;
- GET only, no redirect following, no automatic retry;
- bounded timeout and response bytes;
- no cookies, credentials, package manager, builds, tests, repository scripts, or source execution;
- canonical source bytes treated as inert untrusted data;
- document/source/chunk authority unique within the registry;
- raw byte count/hash fail closed when tampered.

Pinning a trusted source does not make its text trusted instructions for a model. Later context assembly must still treat retrieved content as untrusted evidence.

## Validation evidence

Final CI for the pinned-registry + bounded-acquisition increment:

```text
workflow: Python CI
run:      33932706357
head:     c2311c1451d0424bc635a987af3530df8d34b65a

Knowledge Retrieval Ruff:     PASS
Knowledge Retrieval Pyright:  0 errors / 0 warnings
Knowledge Retrieval pytest:   25 passed in 0.14s

Correlation regression:              PASS
Repository Intelligence regression:  PASS
Risk Policy regression:              PASS
Semantic Query regression:           PASS
```

Earlier incremental CI was intentionally used to isolate failures. The first registry run exposed two Ruff `D105` findings; those were fixed before the acquisition boundary was added. The final pinned-source design above is the currently validated design.

## Gate 7.2 status

**IN PROGRESS.**

Completed:

- [x] Gate 7.1 merge dependency confirmed;
- [x] six positive golden document identities mapped to explicit official sources;
- [x] eight expected chunk identities mapped to those sources;
- [x] official source files pinned by full Git commit SHA;
- [x] human-facing provenance separated from immutable acquisition coordinates;
- [x] typed source registry contract and fixture;
- [x] mutable refs and path traversal fail closed;
- [x] bounded raw-source acquisition contract;
- [x] exact raw source byte identity contract;
- [x] redirect, media type, encoding, oversize, and tampered-hash failure tests;
- [x] final increment Ruff/Pyright/pytest green;
- [x] deterministic regressions green;
- [x] no AWS resources or paid calls introduced.

Still required before Gate 7.2 can close:

- [ ] deterministic UTF-8/newline normalization policy frozen;
- [ ] deterministic curated section-selection plan frozen;
- [ ] canonical `KnowledgeDocument.content_sha256` generated;
- [ ] eight expected chunks materialized with exact hashes;
- [ ] corpus manifest generated and validated;
- [ ] real acquisition of the six pinned source files demonstrated;
- [ ] real source-byte hashes/byte counts recorded;
- [ ] marker/content-drift failure path demonstrated;
- [ ] final Gate 7.2 Ruff/Pyright/pytest + regressions green;
- [ ] current-state/architecture/roadmap closeout;
- [ ] logical PR + squash merge.

## Next authorized increment

Freeze deterministic normalization and exact section selection for the six pinned source files.

The source inspection already confirms useful stable sections for:

- pip upgrade and transitive-dependency/constraint guidance;
- uv lock checking/refresh and locked-version upgrade behavior;
- pip hash-checking mode;
- Django 6.0.8 security remediation evidence;
- OWASP testing-environment and post-change validation guidance;
- PyPA version-specifier semantics.

Only after that transformation is independently tested should the first real six-source acquisition/materialization run occur.

Do not create Bedrock Knowledge Base, embedding, vector, IAM, retrieval, or synthesis infrastructure yet.
