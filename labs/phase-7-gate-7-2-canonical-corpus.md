# Phase 7 — Gate 7.2: Reproducible Canonical Corpus

_Date: 2026-09-05_

## Purpose

Build a reproducible, content-addressed knowledge corpus from explicitly authorized explanatory and remediation sources before any vector infrastructure exists.

Gate 7.2 is deliberately separate from Gate 7.3. This gate does not create a Bedrock Knowledge Base, vector store, embedding job, IAM role, or paid AWS retrieval/generation call.

## Dependency

Gate 7.1 is complete and squash-merged through PR #93:

```text
main commit: f2e3b72c31d0713707857bc0867a7f59e667b9dd
```

The frozen Gate 7.1 golden fixture defines:

```text
6 unique positive document identities
9 unique positive chunk identities
```

An earlier Gate 7.2 checkpoint incorrectly described the positive set as eight chunks. The checked golden fixture, source registry, and corpus spec all contain nine unique chunk identities; the documentation count is corrected here rather than changing the frozen evaluation contract to fit the earlier prose.

Gate 7.2 materializes those expectations without widening the structured-fact authority boundary.

## Target flow

```text
trusted pinned source registry
 -> bounded GET-only raw-source acquisition
 -> exact source bytes + source_bytes_sha256
 -> deterministic text normalization
 -> exact curated section selection
 -> KnowledgeDocument + content_sha256
 -> canonical chunks + chunk_content_sha256
 -> deterministic hash-only corpus manifest
 -> exact replay verification
```

## Reproducibility decision

The initial Gate 7.2 draft considered fetching mutable human-facing documentation pages directly.

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

## Versioned product inputs

The source registry and canonical corpus spec are product inputs rather than test fixtures:

```text
knowledge/corpus/v1/source_registry.json
knowledge/corpus/v1/corpus_spec.json
```

The golden retrieval dataset remains an evaluation fixture:

```text
tests/fixtures/knowledge_retrieval/golden_retrieval_v1.json
```

The Python CI path filter includes `knowledge/corpus/**`, so a configuration-only change to corpus authority or selection policy cannot bypass the Knowledge Retrieval quality gates.

### Source registry v1

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

The registry is an authorization artifact. Its static `acquisition_status: not_started` means it does not itself claim runtime acquisition evidence; successful materialization evidence belongs in `manifest.json`.

### Corpus spec v1

Spec identity:

```text
knowledge-corpus-spec:v1
```

Frozen normalization policy:

```json
{
  "encoding": "utf-8-strict",
  "newline": "lf",
  "unicode": "preserve",
  "bom": "reject",
  "nul": "reject",
  "selection": "exact-line-aligned-start-inclusive-end-exclusive",
  "document_join": "two-lf"
}
```

The normalizer intentionally does not perform Unicode normalization, Markdown/RST rewriting, semantic cleanup, HTML extraction, or LLM-assisted transformation.

The nine canonical chunks are selected by exact line-aligned start/end sentinels. Marker ambiguity or drift fails closed rather than selecting a nearby section heuristically.

One test-driven refinement tightened matching from arbitrary substring occurrence to line-aligned markers after `## First` was observed to match the synthetic drifted heading `## First changed`. The stricter behavior is now part of the v1 contract.

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

A vendor release note may mention CVEs, severity, or remediation as explanatory evidence. OpsLens structured vulnerability truth continues to come from the deterministic Phase 2–6 authorities.

The `uv-locking:diff-review` golden chunk deserves a specific grounding constraint: the selected uv source documents lockfile checking and targeted locked-version upgrades; it does not prescribe a Git `diff` review procedure. Later synthesis must not attribute such a recommendation to uv unless another admitted source actually supports it.

## Bounded acquisition contract

`BoundedHttpsKnowledgeSource` uses the same narrow network principles already proven by Repository Intelligence:

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

The human-facing `canonical_uri` is provenance only and cannot redirect acquisition authority.

## Raw and canonical identities

Successful acquisition produces typed `AcquiredKnowledgeSource` evidence:

```text
descriptor
body
content_type
byte_count
source_bytes_sha256
```

`source_bytes_sha256` is calculated over the exact admitted HTTP body bytes before decoding or normalization.

Canonical materialization then derives separate identities:

```text
KnowledgeDocument.content_sha256
CanonicalKnowledgeChunk.chunk_content_sha256
```

The separation means upstream byte drift cannot be hidden by normalization, and canonical text drift cannot be hidden by a stable source pin.

## Fail-closed configuration loading

`application/corpus_config.py` loads the checked-in registry/spec through an exact v1 schema:

- unknown or missing keys fail;
- unsupported source types fail;
- the normalization object must exactly match the frozen v1 policy;
- mutable refs/path traversal still fail in the domain contract;
- hidden selector behavior cannot be introduced through an unreviewed JSON field.

## Hash-only corpus manifest

Manifest identity:

```text
knowledge-corpus-manifest:v1
```

The deterministic manifest intentionally contains no third-party source/chunk text and no runtime timestamp.

It records, per document:

```text
document/source identity
source type
canonical URI
immutable acquisition URI
upstream repository + commit + path
source byte count + source_bytes_sha256
canonical title
canonical UTF-8 byte count + content_sha256
ordered chunks:
  chunk_id
  section_path
  canonical UTF-8 byte count
  chunk_content_sha256
```

Serialization is stable JSON with a final LF. Identical pins and identical admitted bytes must therefore produce byte-for-byte identical `manifest.json` content.

A replay that still satisfies the markers but changes admitted content is detected by manifest mismatch.

The first real manifest is checked in at:

```text
knowledge/corpus/v1/manifest.json
```

Real manifest identity:

```text
sha256:98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
documents: 6
chunks:    9
```

The manifest contains exact raw-source byte counts and SHA-256 identities for all six pinned inputs plus canonical document/chunk hashes. It does not vendor the selected third-party text.

## Replay pipeline and CLI

The replay pipeline is serial and bounded. It accepts at most ten documents, while v1 contains six.

The repository uses a `src/` layout without installing the project package into the local environment, so the versioned local replay commands are:

```bash
PYTHONPATH=src uv run python -m opslens.knowledge_retrieval.cli.materialize_corpus --write
PYTHONPATH=src uv run python -m opslens.knowledge_retrieval.cli.materialize_corpus --check
```

`--write`:

- acquires the six pinned official source files serially;
- keeps source text in memory only;
- materializes the nine canonical chunks;
- writes only hash/provenance evidence;
- writes atomically through temp file + flush + fsync + replace.

`--check`:

- performs a fresh replay over the same immutable pins;
- serializes a fresh manifest;
- requires exact equality with the existing manifest;
- returns non-zero on any mismatch and does not overwrite the recorded evidence.

Offline CLI tests replace the real acquirer with a fake transport and prove deterministic write/check behavior and fail-closed drift without using network access in CI.

## Security boundary

Gate 7.2 code proves:

- exact GitHub `owner/repository` syntax;
- full immutable commit SHA required; mutable refs such as `main` rejected;
- clean repository-relative path; traversal segments rejected;
- acquisition host fixed by code, not registry/user input;
- HTTPS standard-library transport only;
- GET only, no redirect following, no automatic retry;
- bounded timeout, document count, and response bytes;
- no cookies or credentials;
- no package manager/build/test/repository-script/source execution;
- canonical source bytes treated as inert untrusted data;
- exact UTF-8 and line-ending policy;
- line-aligned section selectors fail on ambiguity/drift;
- document/source/chunk authority unique;
- source/document/chunk byte counts and hashes fail closed;
- config schema/policy drift fails closed;
- manifest contains hashes/provenance, not vendored third-party text;
- replay mismatch cannot overwrite the existing manifest in `--check` mode.

Pinning a trusted source does not make its text trusted instructions for a model. Later context assembly must still treat retrieved content as untrusted evidence.

## Validation evidence

### Pinned acquisition boundary

```text
workflow: Python CI
run:      33932706357
head:     c2311c1451d0424bc635a987af3530df8d34b65a

Knowledge Retrieval Ruff:     PASS
Knowledge Retrieval Pyright:  0 errors / 0 warnings
Knowledge Retrieval pytest:   25 passed in 0.14s
regression jobs:               PASS
```

### Canonical normalization/materialization

```text
workflow: Python CI
run:      33933268598

Knowledge Retrieval Ruff:     PASS
Knowledge Retrieval Pyright:  0 errors / 0 warnings
Knowledge Retrieval pytest:   34 passed in 0.14s
regression jobs:               PASS
```

That increment exposed and corrected both the line-marker strictness issue and the historical documentation count from eight to nine chunks.

### Final pre-replay implementation

```text
workflow: Python CI
run:      33933873683
head:     8e44652271c6c11d4fb05ce170422e9e4462646d

Knowledge Retrieval Ruff:     PASS
Knowledge Retrieval Pyright:  0 errors / 0 warnings
Knowledge Retrieval pytest:   44 passed in 0.20s

Correlation regression:              PASS
Repository Intelligence regression:  PASS
Risk Policy regression:              PASS
Semantic Query regression:           PASS
```

### Real replay failure evidence

The first real six-source replay intentionally exercised the fail-closed selector contract and stopped on the PyPA version-specifier source:

```text
ERROR: start marker for 'knowledge-chunk:pypa-version-specifiers:constraints:v1'
must occur exactly once; found 2
```

Inspection of the exact pinned RST showed two `Version specifiers` headings: the document title and the later normative section. The contract was not loosened. The selector was made more specific by including the first normative sentence of the intended section.

Correction:

```text
commit: 78bfda9763524b6e36b4c2b543ba9fa3e4f0714a
Python CI run: 33934507567
all five quality-gate jobs: PASS
```

This is useful failure evidence: the real replay detected selector ambiguity before any incorrect corpus evidence could be written.

### Successful real replay and exact verification

The corrected corpus spec was replayed in the single local OpsLens development environment.

```text
write:
  documents:       6
  chunks:          9
  manifest_sha256: 98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418

immediate check:
  documents:       6
  chunks:          9
  manifest_sha256: 98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418

independent local shasum:
  98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

The manifest was then committed without manual edits:

```text
commit: bb61f6766f9c52c167ac7d1a3a8bc734cd1a6307
```

### Final manifest CI

```text
workflow: Python CI
run:      33965739749
head:     bb61f6766f9c52c167ac7d1a3a8bc734cd1a6307

Knowledge Retrieval Ruff:     PASS
Knowledge Retrieval Pyright:  0 errors / 0 warnings / 0 informations
Knowledge Retrieval pytest:   44 passed in 0.25s

Correlation regression:              PASS
Repository Intelligence regression:  PASS
Risk Policy regression:              PASS
Semantic Query regression:           PASS
```

Earlier incremental runs intentionally exposed and resolved lint, strict-typing, marker strictness, and historical chunk-count issues. Runtime behavior was not weakened to satisfy static analysis or real replay failures.

## Why the real replay is local rather than CI

OpsLens uses one real development environment. CI validates deterministic behavior with fake transport and does not become a second corpus-authoring environment.

The first six-source replay was therefore executed from the normal local OpsLens development environment using the versioned CLI. This demonstrates that the checked-in pipeline is sufficient to reconstruct the corpus rather than relying on connector/session-specific behavior.

No third-party source was executed during that replay; the six files were read as inert text only.

## AIP-C01 learning mapping

Gate 7.2 exercises certification-relevant concepts without introducing an AWS service merely for exam coverage:

```text
Security
  immutable allowlisted origins; no credentials; no source execution;
  provenance and fail-closed validation

Reliability
  replayable pinned inputs; deterministic normalization/selection;
  content addressing and exact verification

Operational Excellence
  versioned registry/spec/manifest; scoped CI; diagnosable failure evidence

Cost Optimization
  no AWS resource or paid model/vector/retrieval call in Gate 7.2
```

AWS pricing/IAM additions are not applicable to this gate because no AWS resource was created.

## Gate 7.2 status

**COMPLETE — MERGE PENDING.**

Completed:

- [x] Gate 7.1 merge dependency confirmed;
- [x] six positive golden document identities mapped to explicit official sources;
- [x] nine expected positive chunk identities mapped to those sources;
- [x] official source files pinned by full Git commit SHA;
- [x] human-facing provenance separated from immutable acquisition coordinates;
- [x] source registry/spec promoted to versioned product inputs;
- [x] CI triggers on `knowledge/corpus/**` input changes;
- [x] mutable refs and path traversal fail closed;
- [x] bounded raw-source acquisition contract;
- [x] exact raw source byte identity contract;
- [x] deterministic UTF-8/newline normalization policy frozen;
- [x] exact line-aligned curated section-selection plan frozen;
- [x] canonical `KnowledgeDocument` and chunk content-addressing implemented;
- [x] marker/content-drift failure path covered offline;
- [x] real marker ambiguity detected and corrected without weakening fail-closed semantics;
- [x] fail-closed product config loader implemented;
- [x] deterministic hash-only manifest contract/serializer/verifier implemented;
- [x] serial bounded replay pipeline implemented;
- [x] `--write` / `--check` CLI implemented with offline tests;
- [x] real acquisition of all six pinned official source files;
- [x] real `source_bytes_sha256` and byte counts recorded;
- [x] real canonical document and nine chunk hashes recorded;
- [x] immediate second `--check` proved exact manifest reproducibility;
- [x] independent local manifest SHA-256 matched CLI output;
- [x] checked-in manifest validated by CI;
- [x] final Gate 7.2 CI green;
- [x] deterministic regressions green;
- [x] no AWS resources or paid calls introduced.

Remaining closeout:

- [ ] current-state/architecture/roadmap synchronized;
- [ ] PR #94 ready for review;
- [ ] squash merge.

## Next authorized action

Finish documentation-only closeout, then squash-merge PR #94.

Only after Gate 7.2 is logically merged should Gate 7.3 begin. Gate 7.3 must re-check current official AWS documentation, pricing, IAM requirements, vector-store choices, Knowledge Base modes, embedding options, chunking constraints, observability, and failure behavior before any AWS resource is created.

Do not create Bedrock Knowledge Base, embedding, vector, IAM, retrieval, or synthesis infrastructure as part of Gate 7.2.
