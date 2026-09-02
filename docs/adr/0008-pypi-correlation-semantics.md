# ADR 0008 — Start vulnerability correlation with PyPI semantics

- Status: Accepted
- Date: 2026-09-02
- Phase: 3 — Vulnerability Correlation Engine

## Context

Phase 2 established authoritative source-local threat intelligence from NVD, CISA KEV, FIRST EPSS, and GitHub Security Advisories. Phase 3 must answer a different question deterministically:

> Does one concrete installed package version fall inside a published vulnerable range?

This decision must not be delegated to an LLM. Version ordering and package identity are ecosystem-specific, so a single universal comparator would silently produce incorrect answers across ecosystems.

GitHub-reviewed advisories expose package ecosystem, package name, vulnerable version range, and first patched version when known. GitHub documents the vulnerable-range grammar as basic ordered clauses such as `= 0.2.0`, `<= 1.0.8`, `< 0.1.11`, `>= 4.3.0, < 4.3.5`, and `>= 0.0.1`.

## Decision

The first supported ecosystem is **PyPI / GitHub ecosystem `pip`**.

The first Phase 3 implementation boundary is intentionally narrow:

```text
PyPI package identity + concrete version
        |
        v
canonical package name
PEP 440 version semantics
        |
        v
GitHub reviewed advisory range
        |
        v
typed deterministic range evaluation
        |
        v
affected / not affected / unsupported
        |
        v
reproducible match evidence
```

### Why PyPI first

1. OpsLens itself is Python and the project already has strong Python test/tooling foundations.
2. Several planned repository-analysis targets are Python-heavy, including FastAPI and Python AI tooling.
3. PyPI has a formal and current version-ordering specification (PEP 440 / PyPA Version Specifiers).
4. PyPI project-name normalization is explicitly standardized: lowercase and collapse runs of `.`, `_`, and `-` to `-`.
5. GitHub reviewed advisories support the `pip` ecosystem and expose the package/range/fix evidence Phase 3 needs.
6. Starting with one ecosystem prevents accidental reuse of PEP 440 rules for npm, Maven, Go, Rust, or other incompatible version schemes.

## Frozen PyPI v1 semantics

### Ecosystem identity

Canonical OpsLens ecosystem identifier:

```text
pypi
```

Accepted source alias in the GHSA adapter boundary:

```text
pip -> pypi
```

No other ecosystem alias is accepted by the PyPI evaluator.

### Package-name normalization

For lookup and equality only, PyPI project names are canonicalized according to the PyPA name-normalization specification:

```text
lowercase(name)
replace each run of [-_.]+ with '-'
```

Examples:

```text
Requests        -> requests
zope.interface  -> zope-interface
my__pkg         -> my-pkg
```

The original source/package spelling must remain available in evidence; normalization must not destroy provenance.

### PURL

The canonical package URL shape for this first ecosystem is:

```text
pkg:pypi/<normalized-name>@<normalized-version>
```

Phase 3 v1 supports package-version purls without qualifiers or subpath. Qualifiers/subpaths are not silently discarded; they are unsupported until explicitly modeled.

### Version semantics

PyPI versions use PEP 440 ordering and normalization. The implementation must use a standards-conformant parser/comparator rather than lexical or tuple comparison.

Important consequences include support for:

- epochs;
- release segments;
- pre-releases;
- post-releases;
- development releases;
- normalized alternative spellings;
- local versions where permitted by PEP 440.

Malformed/non-PEP-440 versions fail closed as `unsupported`; they are not coerced into an arbitrary ordering.

### Vulnerable-range representation

The first typed representation supports conjunctions of ordered clauses published by GitHub reviewed advisories:

```text
=  version
<  version
<= version
>  version
>= version
```

Comma means logical AND.

Examples:

```text
= 0.2.0
<= 1.0.8
< 0.1.11
>= 4.3.0, < 4.3.5
>= 0.0.1
```

Phase 3 does not reinterpret arbitrary dependency specifiers as advisory ranges. Operators outside the frozen GHSA range grammar are unsupported until explicitly reviewed.

### Bounds

Each ordered clause is evaluated using PEP 440 comparison semantics.

- `<` and `>` are exclusive.
- `<=` and `>=` are inclusive.
- `=` is exact equality under normalized PEP 440 version identity.
- Missing lower or upper bounds remain open; OpsLens does not invent bounds.

### First patched version

`first_patched_version` is evidence about a known fix and is not a substitute for evaluating the vulnerable range.

Rules:

1. applicability is decided from package identity + concrete version + vulnerable range;
2. a first patched version, when supplied, is preserved as remediation evidence;
3. OpsLens must not infer that every version greater than the first patched version is safe unless the published vulnerable-range evidence establishes that result;
4. missing first patched version means `fix version unknown`, not `no fix exists`.

### Result states

The evaluator returns one of:

```text
affected
not_affected
unsupported
```

`unsupported` is a first-class fail-closed result for malformed versions, malformed ranges, unsupported operators, unsupported purl features, or ecosystem mismatch. It must never be silently converted to `not_affected`.

### Evidence contract

Every result must be reconstructable from deterministic evidence containing at minimum:

```text
ecosystem_original
ecosystem_canonical
package_name_original
package_name_canonical
version_original
version_canonical
purl_original (when supplied)
purl_canonical
advisory_id
vulnerability_ids / aliases
vulnerable_range_original
parsed_clauses
first_patched_version_original (nullable)
result
reason_code
```

Source-local provenance from Phase 2 remains outside this normalized matching contract and must be linked, not replaced.

## Unsupported behavior

The initial PyPI evaluator fails closed for:

- non-PyPI ecosystems;
- invalid PyPI project names;
- invalid PEP 440 versions;
- empty advisory ranges;
- malformed clauses;
- unsupported range operators;
- purl qualifiers or subpaths;
- ambiguous package identity;
- range semantics that cannot be represented by the frozen grammar.

## Alternatives considered

### Start with npm

Rejected for the first slice. npm is valuable for later repository coverage, but SemVer plus npm range syntax introduces a different grammar (`^`, `~`, wildcards, unions) and would widen the first gate unnecessarily.

### Start with Maven

Rejected for the first slice. Maven coordinates and version ordering require group/artifact identity and Maven-specific comparison behavior, adding identity complexity before the core correlation contract is proven.

### Build one universal version comparator

Rejected. Ecosystem version semantics are not interchangeable. A universal comparator would create false positives/negatives and violate the deterministic evidence requirement.

### Let an LLM interpret advisory ranges

Rejected. Applicability is a security-relevant deterministic decision and must be reproducible, testable, and explainable.

## Consequences

Positive:

- small and testable first Phase 3 slice;
- standards-based package/version semantics;
- explicit fail-closed boundary;
- direct path from GHSA package evidence to repository correlation later;
- no AWS resource or runtime cost is added by this first gate.

Trade-offs:

- multi-ecosystem support is deferred;
- PyPI-specific abstractions must remain behind an ecosystem interface so later npm/Maven/Go implementations do not inherit PEP 440 assumptions;
- the benchmark corpus becomes part of the compatibility contract and must evolve deliberately.

## Validation gate

Before Phase 3 expands beyond PyPI, the implementation must demonstrate:

1. project-name normalization cases;
2. PEP 440 version ordering cases, including pre-release and post-release boundaries;
3. inclusive/exclusive/open vulnerable ranges;
4. vulnerable versus fixed-version differentiation;
5. malformed and unsupported evidence failing closed;
6. deterministic result evidence;
7. CVE/GHSA alias reconciliation in a later Phase 3 step without collapsing source-local authority.

## References

- GitHub Docs — Global Security Advisories / `SecurityVulnerability.vulnerableVersionRange` semantics.
- Python Packaging User Guide — Version Specifiers (PEP 440 semantics).
- Python Packaging User Guide — Names and normalization (PyPI project identity).
