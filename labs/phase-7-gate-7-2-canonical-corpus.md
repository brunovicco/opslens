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
trusted source registry
 -> bounded exact acquisition
 -> exact source bytes + source_bytes_sha256
 -> deterministic normalization
 -> KnowledgeDocument + content_sha256
 -> deterministic chunk materialization
 -> canonical corpus manifest
```

The first increment stops at the source registry:

```text
golden expected document/chunk IDs
 -> explicit trusted source mapping
 -> exact HTTPS host allowlist
 -> typed KnowledgeSourceDescriptor
 -> typed KnowledgeSourceRegistry
```

No source page is fetched by OpsLens in this increment.

## Source registry v1

Registry identity:

```text
knowledge-source-registry:v1
```

Authorized sources:

| Document ID | Role | Canonical source |
| --- | --- | --- |
| `knowledge-doc:pypa-dependency-management:v1` | dependency resolution, upgrades, transitive dependencies | `https://pip.pypa.io/en/stable/topics/dependency-resolution/` |
| `knowledge-doc:uv-locking:v1` | lock update/check/dry-run workflow | `https://docs.astral.sh/uv/reference/cli/#uv-lock` |
| `knowledge-doc:pypa-secure-installs:v1` | hash-checked Python package installation | `https://pip.pypa.io/en/stable/topics/secure-installs/` |
| `knowledge-doc:vendor-advisory-reading:v1` | real maintainer advisory example with affected versions and resolution | `https://www.djangoproject.com/weblog/2026/aug/04/security-releases/` |
| `knowledge-doc:dependency-remediation-validation:v1` | remediation in a testing environment and post-change validation | `https://cheatsheetseries.owasp.org/cheatsheets/Vulnerable_Dependency_Management_Cheat_Sheet.html` |
| `knowledge-doc:pypa-version-specifiers:v1` | Python dependency version constraints | `https://packaging.python.org/en/latest/specifications/version-specifiers/` |

The registry is a pre-acquisition authorization boundary, not a content manifest. It intentionally contains no source-content hash because no source bytes have been acquired yet.

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

A vendor advisory may mention CVEs or fixed releases as explanatory evidence, but OpsLens structured vulnerability truth continues to come from the deterministic Phase 2–6 authorities.

## Security boundary

The first increment freezes future acquisition origins before implementing network access:

- HTTPS only;
- exact canonical URI;
- exact hostname allowlist per source;
- no caller-provided arbitrary URL;
- no source execution;
- no package-manager/build/test execution;
- registry document/source/chunk identities are unique;
- a canonical URI cannot silently point to a different host.

Later acquisition must still treat all returned HTML/text as untrusted data. Host authorization does not make retrieved content safe for model instructions.

## Why source registry and corpus manifest are separate

The two artifacts answer different questions:

```text
source registry
  Which inputs is OpsLens allowed to acquire?

corpus manifest
  Which exact bytes/text did OpsLens acquire and normalize?
```

The later manifest is expected to record at least exact source-byte identity and normalized document identity separately. This prevents a normalized text hash from hiding upstream byte changes or normalization drift.

## First-increment implementation

Added:

```text
KnowledgeSourceDescriptor
KnowledgeSourceRegistry
SOURCE_REGISTRY_ID
```

Fixture:

```text
tests/fixtures/knowledge_retrieval/source_registry_v1.json
```

Tests prove:

- registry version and pre-acquisition status;
- exact coverage of positive golden document IDs;
- exact coverage of positive golden chunk IDs;
- source-type agreement with the golden fixture;
- exact HTTPS hostname binding;
- fail-closed host mismatch/non-HTTPS URI;
- duplicate document/chunk authority rejection.

## Gate 7.2 status

**IN PROGRESS.**

Completed in this increment:

- [x] Gate 7.1 merge dependency confirmed;
- [x] six positive golden document identities mapped to explicit sources;
- [x] eight expected chunk identities mapped to those sources;
- [x] exact source-host authorization frozen;
- [x] typed source registry contract added;
- [x] source registry fixture added;
- [x] deterministic structural/failure tests added;
- [x] no AWS resources or paid calls introduced.

Still required before Gate 7.2 can close:

- [ ] bounded source acquisition contract;
- [ ] exact acquired source bytes preserved or reproducibly represented;
- [ ] `source_bytes_sha256` recorded;
- [ ] deterministic normalization policy frozen;
- [ ] canonical `KnowledgeDocument.content_sha256` generated;
- [ ] deterministic expected chunks materialized from admitted text;
- [ ] corpus manifest generated and validated;
- [ ] upstream/content-drift failure path demonstrated;
- [ ] Ruff/Pyright/pytest green for the final Gate 7.2 slice;
- [ ] current-state/architecture/roadmap closeout;
- [ ] logical PR + merge.

## Next authorized increment

Implement bounded acquisition and raw-content identity for the six allowlisted sources.

Do not create Bedrock Knowledge Base, embedding, vector, IAM, retrieval, or synthesis infrastructure yet.
