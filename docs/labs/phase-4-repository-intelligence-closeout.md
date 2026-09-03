# Phase 4 — Repository Intelligence Closeout

_Date: 2026-09-03_

_Status: COMPLETE_

Implementation closeout checkpoint:

```text
main: 4baa9bddd20d827aa06654fc14f52c7ec5135f2c
PR:   #78 — feat(repository): close Phase 4 with final analysis result
```

## Goal

Analyze a supported public GitHub repository snapshot using inert dependency evidence and the deterministic Phase 3 correlation authority, without executing third-party repository code.

Phase 4 exit fields:

```text
dependency
installed version
vulnerability identifiers
matched vulnerable range
CISA KEV evidence
FIRST EPSS evidence
NVD CVSS evidence
fixed version when published
exact reproducible evidence
```

## Frozen v1 scope

```text
repository provider:    public GitHub
repository evidence:    uv.lock
supported dependency:   canonical PyPI source records
version authority:      PEP 440 / Phase 3
vulnerable-range truth: Phase 3 deterministic evaluator
network boundary:       bounded GitHub REST GET-only
repository execution:   never
runtime-exposure claim: never
```

## Gate history

### Gate 4.1 — Immutable repository snapshot — PR #68

Established:

- typed public GitHub repository identity;
- numeric GitHub repository ID as stable source identity;
- exact commit SHA and tree SHA evidence;
- deterministic immutable `snapshot_id`;
- fail-closed repository/ref validation;
- permanent Repository Intelligence CI slice.

Merge checkpoint:

```text
3f75a4fc2bd22589df0a5ffe98a8442fda81c8d3
```

### Gate 4.2 — Snapshot resolution — PR #69

Established deterministic projection from GitHub repository metadata and commit evidence into the immutable snapshot contract.

Important boundary:

```text
requested ref
 -> canonical repository metadata
 -> exact commit SHA
 -> exact tree SHA
```

No dependency file was read in this gate.

Merge checkpoint:

```text
4e9f1818adf637fbd4ab9200affa5e5bb535862a
```

### Gate 4.3 — Bounded read-only GitHub transport — PR #70

Established:

- fixed GitHub API host;
- GET-only source boundary;
- explicit timeout and response-byte bounds;
- no redirect authority expansion;
- no automatic unbounded retry;
- explicit rate-limit failure semantics.

No repository dependency content was interpreted.

Merge checkpoint:

```text
e9fd556a7809e4fb67b1d2fc12d845fe2b88b0d5
```

### Gate 4.4 — Immutable `uv.lock` evidence — PR #71

Established exact inert dependency-file evidence:

- only `uv.lock` is allowlisted;
- exact immutable commit is used for acquisition;
- GitHub content metadata and Base64 payload are bounded/validated;
- decoded bytes are capped at 1 MiB;
- Git blob SHA-1 is recomputed independently;
- OpsLens SHA-256 is computed independently;
- no TOML parser or package-manager execution yet.

Merge checkpoint:

```text
eaf510b11db540bbe47ea19b888b7f9edf1259c0
```

### Gate 4.5 — Deterministic `uv.lock` parser — PR #72

Established stdlib `tomllib` parsing over already verified bytes.

The parser:

- supports the frozen lock schema/revisions;
- preserves `requires-python` and resolution markers;
- preserves zero-based source record indexes;
- caps logical package records at 5,000;
- classifies exact PyPI source records separately from unsupported source kinds;
- does not execute `uv`, resolve dependencies, or infer deployment truth.

Merge checkpoint:

```text
90e860e7231a327c3358867a9248f2c4678d1687
```

### Gate 4.6 — Phase 3 PyPI normalization bridge — PR #73

Established normalization of supported PyPI lock records exclusively through Phase 3 authority:

```text
raw lock name/version
 -> PyPA package normalization
 -> PEP 440 version normalization
 -> canonical PyPI purl
```

Every PyPI-source record is accounted for exactly once as normalized or unsupported.

Merge checkpoint:

```text
8aa6c8298cf0426bea291342e727d71a50008bdb
```

### Gate 4.7 — Deterministic repository vulnerability findings — PR #74

Established the first repository-risk findings:

```text
normalized locked dependency
 + exact GHSA vulnerability occurrence
 -> canonical package-name join
 -> Phase 3 applicability evaluator
 -> affected | not_affected | unsupported assessment
 -> repository finding for affected only
```

Properties:

- exact GHSA provenance is validated before candidate filtering;
- unsupported evidence never collapses to not affected;
- no dependency × advisory Cartesian product is created;
- marker forks remain distinct by lock record index;
- hard bounds protect GHSA occurrence and candidate evaluation counts;
- affected findings are canonical JSON and content-addressed.

Identity:

```text
repository-finding:v1@sha256:<digest>
```

Merge checkpoint:

```text
439dd29d6298b656374c8a8e053a05b56dff20ec
```

### Gate 4.8 — NVD/CVSS enrichment — PR #75

Added exact NVD and CVSS evidence around already affected findings without changing applicability truth.

Properties:

- exact GHSA occurrence is rebound before recovering the GitHub CVE assertion;
- Phase 3 remains the CVE/GHSA/NVD alias authority;
- zero or one exact NVD observation is supplied per CVE;
- duplicates fail closed instead of selecting `latest`;
- CVSS is re-derived from exact canonical NVD source content;
- every supported CVSS observation is preserved;
- no preferred/highest/merged score is selected;
- `nvd_rejected` remains distinct from normal observation states.

Merge checkpoint:

```text
3bbe875951728094753ef872cfe6b8113d55f147
```

### Gate 4.9 — CISA KEV complete-snapshot enrichment — PR #76

Added deterministic KEV membership evidence from one complete immutable catalog snapshot.

States:

```text
present
absent
cve_unavailable
```

`absent` is produced only after complete snapshot validation and full deterministic transformation.

NVD evidence is not required for KEV lookup; the GitHub-asserted CVE is used when available.

Merge checkpoint:

```text
68194737c1fc8ff25441128ee610e8f565811745
```

### Gate 4.10 — FIRST EPSS exact-snapshot enrichment — PR #77

Added deterministic EPSS evidence from exactly one complete current or historical FIRST snapshot.

States:

```text
score_present
score_absent
cve_unavailable
```

Temporal boundary:

- one explicit snapshot is evaluated per execution;
- no automatic `latest` selection;
- no nearest-date selection;
- no max-score selection;
- no trend calculation;
- no policy weighting.

Legacy EPSS v1 evidence preserves unavailable model metadata/percentile fields instead of inventing modern values.

Merge checkpoint:

```text
bfe823598591d348556284439498df5b84d57cc1
```

### Gate 4.11 — Final Repository Analysis Result — PR #78

Added a consumer-facing projection over the already validated evidence chain.

`RepositoryAnalysisResult` accepts only the final `RepositoryEpssEnrichmentEvidence` and derives all output fields from nested authoritative evidence.

Final identity:

```text
repository-analysis-finding:v1@sha256:<digest>
repository-analysis:v1@sha256:<digest>
```

The final projection exposes no risk score, priority, or runtime-exposure claim.

Merge checkpoint:

```text
4baa9bddd20d827aa06654fc14f52c7ec5135f2c
```

## Final deterministic chain

```text
public GitHub repository
 -> immutable repository snapshot
 -> bounded read-only source acquisition
 -> exact inert uv.lock
 -> deterministic lock parsing
 -> Phase 3 PyPI normalization
 -> exact GHSA applicability
 -> repository finding
 -> CVE/GHSA/NVD reconciliation
 -> NVD/CVSS evidence
 -> complete KEV snapshot evidence
 -> explicit EPSS snapshot evidence
 -> RepositoryAnalysisResult
```

## Final Phase 4 quality evidence

Validated PR #78 head:

```text
8ebf5f6b6717ee4d0ff416637f7ad206e17e0fa4
```

GitHub Actions run:

```text
33804086604
```

Final result:

```text
uv lock --check:                  PASS
uv sync --frozen:                 PASS
Repository Intelligence Ruff:     PASS
Repository Intelligence Pyright:  0 errors / 0 warnings
Repository Intelligence pytest:   174 passed
Correlation Ruff:                 PASS
Correlation Pyright:              0 errors / 0 warnings
Correlation pytest:               116 passed
```

The first closeout CI attempt had one strict Pyright optional-member-access finding in the EPSS snapshot serializer. The generic reflection path was replaced by explicit typed branches for historical versus current EPSS snapshots. No evidence or policy semantics changed.

## Cache/reuse boundary

Phase 4 proved that repository commit identity alone is not a correct cache key.

```text
same repository snapshot
same finding/NVD/KEV evidence
changed EPSS snapshot
 -> changed final analysis_id
```

Threat intelligence is temporal. The future safe reuse coordinate is the complete content-addressed evidence identity.

No DynamoDB, ElastiCache, or other repository-analysis cache backend was introduced because no measured workload yet justified its storage, invalidation, IAM, observability, retention, and cost surface.

## Exit criteria mapping

| Exit criterion | Result |
| --- | --- |
| Supported public repository snapshot is immutable and reproducible | PASS |
| Dependency + installed version are preserved | PASS |
| Vulnerability identifiers are preserved | PASS |
| Vulnerable range match is deterministic | PASS |
| Fixed version is preserved when published | PASS |
| NVD/CVSS evidence is exact and source-preserving | PASS |
| KEV evidence uses a complete explicit snapshot | PASS |
| EPSS evidence uses one explicit snapshot | PASS |
| Exact provenance is available end to end | PASS |
| Repeated identical evidence produces identical content address | PASS |
| Third-party code is never executed | PASS |
| Repository Risk remains distinct from Runtime Exposure | PASS |
| LLM is not required for applicability/findings | PASS |

## Phase 5 boundary

Phase 4 closes on evidence.

Phase 5 may consume the final evidence to create **Risk Policy v1**, but it may not rewrite:

- installed package identity;
- vulnerable-range applicability;
- GHSA/NVD source provenance;
- KEV membership evidence;
- EPSS score evidence;
- CVSS observations;
- runtime-exposure semantics.

The next phase is therefore a policy layer over proven facts, not a replacement for them.
