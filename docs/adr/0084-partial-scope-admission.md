# ADR 0084 — Admit a partially identified dependency scope, and put coverage inside its identity

- Status: Accepted
- Date: 2026-09-13
- Supersedes: part of Gate 19.8 (`public-threat-evidence-scope:v1`)
- Related: ADR 0077 (V1 demonstration boundary), ADR 0078 (canonical serialization), ADR 0079 (retained artifact reproducibility)

## Context

Phase 20 makes request-time correlation real so a caller can submit a dependency or a
repository and get an actual verdict. Reading the Gate 19.8 contract closely before
building anything turned up a blocker that would have surfaced on the first real input.

`build_public_threat_evidence_scope` refused outright:

```python
if inventory.unsupported_normalization:
    raise PublicAnalysisValidationError(
        "public threat scope refuses incomplete PyPI normalization evidence"
    )
```

This is correct fail-closed behaviour, and it was written for a world where the input
was one curated repository. Pointed at arbitrary public repositories it becomes the
dominant outcome. **OpsLens's own lock has one non-PyPI package out of 55**, so the
endpoint would reject the repository it ships from. Any project with a git dependency,
a local path, or a private index hits the same wall.

That leaves two genuinely different products. Keep refusing, and the endpoint stays
maximally strict while answering "rejected" to most real inputs — defensible, but it
demonstrates refusal rather than analysis. Or admit what could be identified and carry
what could not, so the verdict is explicitly scoped to the identity that was
established.

A tool that refuses most real inputs teaches a reviewer nothing. Coverage accounting is
also precisely the discipline this repository argues for, provided the count sits beside
the verdict rather than in a footnote.

## Decision

The scope admits partial coverage, and coverage is **part of the scope's identity**.

`PublicThreatUnidentifiedDependency` carries each unidentifiable record as the lock
spelled it — `name_original`, `version_original`, the normalizer's `reason_code`, and
every source record index it accounts for. No canonical identity is invented for a
record that has none. These entries are grouped, canonically ordered, and serialized
into `canonical_json` alongside a `coverage` block, so:

- two locks differing only in what was identifiable are different scopes;
- a retained v1 digest can never silently match a v2 scope derived from the same lock,
  which is why `public-threat-evidence-scope` moves to **v2**;
- the authority request identity moves with it, so a cached result for a differently
  covered scope cannot answer a new request.

The request contract does **not** move. Its shape is unchanged; only the scope id it
references differs, and that id carries its own version.

Three invariants keep partial admission from becoming overstated admission.

**A scope must carry at least one identified dependency.** A lock in which nothing can
be identified still fails closed rather than correlating nothing and reporting nothing.
Partial coverage is admissible; zero coverage is not.

**Every source record is accounted for exactly once across the two halves.** An index
appearing in both is rejected by name, so coverage cannot be inflated by double
counting. The normalization inventory already guarantees exactly-once accounting of
every PyPI-source record, so grouping the unsupported half cannot invent or lose
coverage.

**Unidentified records are canonically ordered.** Scope identity cannot depend on the
order the normalizer happened to reject in.

```text
partial scope != complete scope
scoped verdict != repository verdict
coverage in the identity != coverage in a footnote
```

## Consequences

**The third demo scenario keeps its meaning and changes its reason.**
`fail-closed-incomplete-evidence` is built on this refusal. Its fixture is a lock with a
single unnormalizable package — zero identifiable records — so it still fails closed,
now because nothing could be identified rather than because something could not. The
outcome stays `REJECTED_INCOMPLETE_EVIDENCE`; the reason code becomes
`UNIDENTIFIABLE_PYPI_NORMALIZATION`, because `INCOMPLETE_PYPI_NORMALIZATION` would now
contradict a contract that admits incomplete normalization. A reviewer who read the old
code would have caught that contradiction.

**The suite evaluation identity moved, deliberately.**

```text
before  opslens-demo-suite-evaluation:v1@sha256:ed99f385...cee146d3
after   opslens-demo-suite-evaluation:v1@sha256:deac5a84...1346d3a9
```

All three scenario outcomes are unchanged — `MATERIAL_FINDING` at P0 90/100,
`NO_MATERIAL_FINDING`, `REJECTED_INCOMPLETE_EVIDENCE`. Only the rejection reason moved,
and the digest moved with it. That is content addressing working: the identity changes
when behaviour changes.

The old digest is referenced by ADRs 0078 and 0080 through 0083. Those references are
**not** updated. Each records what was verified at the time, and rewriting them would
falsify the record to make a number consistent. The two live assertions in
`quality-gate.yml` are re-frozen, because those assert what is true now. No retained
evidence under `labs/evidence/` references the digest, so nothing historical is touched.

**The Gate 19.8 verifier follows the contract forward.** It mixed two kinds of
assertion: the retained evidence artifact's frozen identity, and markers for what the
source must contain today. The retained artifact still asserts
`public-threat-evidence-scope:v1`, correctly and permanently. The source markers move to
v2 and gain the new invariants, with the supersession stated in the verifier's own
docstring, following the precedent ADR 0079 set — re-pinning is a deliberate two-part
change, visible in review, never a silent edit.

Negative:

- A verdict can never again be read without reading its coverage. That is the cost of
  the decision and the reason coverage lives in the identity rather than beside it.
- `unidentified` defaults to an empty tuple, so a construction site that forgets it
  silently claims complete coverage. Mitigated by the builder being the only production
  path and by the zero-coverage invariant, but it is a real sharp edge.
- Two contract versions of the same concept now exist in the tree's history. The
  retained artifact pins one and the source pins the other, on purpose.

## Verification

```text
ruff check . / pyright                                clean / 0 errors
pytest                                                2521 passed
run_repository_invariants.py                          23/23 standing verifiers
verify_phase19_gate19_8_threat_evidence_authority.py  PASS
scope identity, complete vs partial                   different digests
request identity, complete vs partial                 different digests
lock with zero identifiable records                   rejected by name
one index in both halves                              rejected by name
unidentified records out of canonical order           rejected
blank or padded originals                             rejected
demo scenario outcomes                                unchanged (3 of 3)
suite evaluation identity                             re-frozen, deliberately
```

```text
partial scope != complete scope
historical evidence != standing authority
superseded contract != falsified record
```
