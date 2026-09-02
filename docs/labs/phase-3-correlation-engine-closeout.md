# Phase 3 — Vulnerability Correlation Engine Closeout

Status: **COMPLETE — PHASE 3 CLOSED; PHASE 4 NEXT**

## Purpose

This document is the status authority for the completed Phase 3 — Vulnerability Correlation Engine.

Phase 3 implemented deterministic package/version-to-vulnerability matching for the first explicitly supported ecosystem: **PyPI**.

The permanent rule remained:

> **No LLM decides vulnerability applicability.**

Other ecosystems remain unsupported until their own identity, version and range semantics are explicitly designed and tested.

## Completed deterministic path

```text
installed ecosystem + package + version + optional purl
  -> PyPI identity normalization
  -> PEP 440 concrete-version semantics
  -> canonical package-version purl
  -> exact GHSA package/range/fix evidence
  -> strict vulnerable-range parser
  -> typed clause evaluation
  -> affected / not_affected / unsupported
  -> source-preserving CVE/GHSA-to-NVD alias evidence
  -> canonical JSON evidence
  -> SHA-256 content-addressed correlation record
```

Phase 3 does not use a model for package identity, version ordering, range evaluation, alias reconciliation or result generation. It also added no AWS runtime, infrastructure or IAM surface.

## Merge checkpoints

```text
Gate 1 — PyPI identity foundation
PR #62  -> 223848b07fa796e279df98220338e3ef14c5153f

Gate 2 — PyPI vulnerable-range evaluator
PR #63  -> 7c71a3f604a42640685f0e825cc25e650fa5fb9a

Gate 3 — GHSA PyPI evidence bridge
PR #64  -> c1abe980e8305bc9bceb57a1ad924dd07a75fad8

Gate 4 — CVE/GHSA alias reconciliation with NVD
PR #65  -> 864e1a6c65d8def026e68a6a6dd18379e174e0cd

Gate 5 — canonical Phase 3 evidence record
PR #66  -> 263b31fa3413de98ff2fa2ebde989f5637d3cb74
```

Draft PR #61 was an early Gate 1 checkpoint and was superseded by merged PR #62.

## Frozen PyPI v1 contract

Canonical ecosystem: `pypi`; explicit GHSA alias: `pip -> pypi`.

Package names are validated and normalized for comparison by lowercasing and collapsing runs of `.`, `_` and `-` to `-`. Original evidence remains preserved.

Concrete versions use PEP 440 through the explicit runtime dependency `packaging>=26.3`.

Supported vulnerable-range operators are only:

```text
=  <  <=  >  >=
```

Comma represents logical AND. Operators outside the frozen grammar and malformed ranges fail closed.

`first_patched_version` is remediation evidence. It never replaces evaluation of the published vulnerable range.

## Source authority

The GHSA bridge preserves exact advisory-version and vulnerability-entry coordinates, source hashes, GitHub identifiers, package evidence, vulnerable range and first patched version.

A GitHub CVE assertion is not silently treated as independent NVD confirmation.

CVE alias reconciliation uses explicit states:

```text
no_github_cve
github_asserted_only
nvd_observed
nvd_rejected
```

`nvd=None` means no NVD evidence was supplied to the reconciliation call; it is not proof that NVD lacks the CVE. A matching NVD `Rejected` record remains a distinct rejected state. Different CVE identifiers cannot be linked as the same alias.

## Reproducible evidence

The final application-layer evidence record contains:

```text
installed ecosystem/package/version/purl evidence
exact GHSA source coordinates and identifiers
source package/range/fix evidence
source-preserving NVD alias evidence
affected status + reason code
package identity result
parsed range-clause evidence
first patched version evidence
```

Canonical JSON is deterministic: UTF-8, sorted keys, compact separators and NaN forbidden. The bytes are SHA-256 addressed as:

```text
correlation:v1@sha256:<evidence_sha256>
```

The record validates its content hash, canonical encoding, schema, engine and internal result consistency. Alias and applicability evidence must refer to the same exact GHSA occurrence.

## Benchmark and validation

The frozen PyPI contract fixture contains 15 benchmark cases covering normalization, inclusive/exclusive/open ranges, pre/post releases, epochs, fixed-version independence, invalid versions, unsupported operators and malformed ranges.

The accumulated correlation suite also covers purl consistency, source binding, package non-match, unsupported ecosystems, NVD lifecycle states, rejected CVEs, canonical byte stability and tamper detection.

Final PR #66 validation:

```text
uv lock --check                                           PASS
uv sync --frozen                                          PASS
ruff check src/opslens/correlation tests/unit/correlation PASS
pyright src/opslens/correlation tests/unit/correlation    0 errors / 0 warnings
pytest tests/unit/correlation                             116 passed
```

Validated PR head: `5718400ac2fec21c96d303e88ec26509797faf92`.

Final merge: `263b31fa3413de98ff2fa2ebde989f5637d3cb74`.

## Failure-path evidence

The first Phase 3 CI attempt exposed 51 pre-existing repository-wide Ruff findings outside the Phase 3 surface, primarily historical EPSS files. That unrelated debt was not mixed into the correlation implementation; the permanent gate was bounded to the correlation package and tests.

PR #66 also produced a useful strict-type failure: the serializer attempted `.value` on `PyPIClauseEvidence.operator`, which is already the stable string evidence representation. The serializer was corrected without relaxing Pyright. The next run passed with zero type errors and 116 tests.

## Roadmap exit criteria

| Exit criterion | Evidence | Status |
|---|---|---|
| Typed normalization for supported ecosystems | PyPI ecosystem, package, PEP 440 version and purl contracts | PASS |
| Vulnerable and fixed versions differentiated | Range decides applicability; fixed version remains remediation evidence | PASS |
| CVE/GHSA aliases deterministic | Explicit source-preserving alias states and mismatch rejection | PASS |
| Edge cases tested | Boundary, version, purl, malformed, source-binding, NVD and tamper tests | PASS |
| Deterministic evidence emitted | Canonical JSON + SHA-256 correlation record | PASS |
| Benchmark/test corpus exists | Frozen 15-case fixture + 116 correlation tests | PASS |
| Unsupported semantics fail closed | Explicit unsupported/error reason codes | PASS |
| No model required for truth | All applicability and evidence decisions are deterministic code | PASS |

All Phase 3 Roadmap exit criteria are satisfied for the explicitly supported PyPI v1 scope.

## Final status

```text
PyPI identity foundation                    COMPLETE
PyPI vulnerable-range evaluator             COMPLETE
GHSA PyPI evidence bridge                   COMPLETE
CVE/GHSA alias reconciliation               COMPLETE
canonical reproducible evidence             COMPLETE
benchmark and edge-case validation          COMPLETE
fail-closed unsupported semantics           COMPLETE
model-free applicability truth              COMPLETE

Phase 3 — Vulnerability Correlation Engine
  COMPLETE / CLOSED
```

Earlier Phase 3 lab notes and ADR 0008 remain historical decision evidence. Their embedded `NEXT` statements are checkpoints; this closeout document is the current Phase 3 status authority.

## AWS and cost boundary

```text
new AWS resources:      0
new IAM permissions:    0
new Lambda functions:   0
new persistence stores: 0
model calls:            0
incremental AWS runtime cost from Phase 3 implementation: $0
```

Future runtime or persistence for correlation evidence requires a separate bounded design and cost/IAM review.

## Next authorized phase — Phase 4 Repository Intelligence

Phase 4 may now begin with a contract-first gate.

The intended handoff is:

```text
public repository
  -> immutable repository snapshot
  -> inert dependency evidence / SPDX-oriented inventory
  -> normalized package identity
  -> Phase 3 correlation engine
  -> repository findings
```

The first Phase 4 gate must freeze repository identity, safe read-only acquisition, supported manifest/lockfile evidence, source provenance, normalization handoff, finding evidence and any future AWS/IAM/cost boundary before a broad scanner is implemented.
