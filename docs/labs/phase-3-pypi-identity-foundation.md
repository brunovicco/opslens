# Phase 3 — PyPI Identity Foundation

## Goal

Establish deterministic package identity before implementing vulnerable-range evaluation.

The first Phase 3 slice owns only:

```text
GHSA `pip` / canonical `pypi`
 -> PyPI project-name validation and normalization
 -> PEP 440 concrete-version parsing and normalization
 -> narrow package-version purl validation
 -> canonical identity
```

It does not yet decide `affected` versus `not_affected`.

## Standards checked

The implementation was checked against current source specifications on 2026-09-02:

- PyPA Names and normalization: valid distribution names use ASCII letters/numbers plus `.`, `_`, `-`, must begin/end with alphanumeric characters, and comparison normalization lowercases and collapses runs of `[-_.]+` to `-`.
- PyPA Version Specifiers / PEP 440: concrete versions are parsed and normalized with ecosystem-specific ordering; alternative spellings such as `1.0RC1` normalize to `1.0rc1`.
- Package-URL ECMA-427 / registered PyPI type: `pypi` has no namespace, package name is required, version is optional in the general PURL specification, and version is an opaque percent-encoded component at the PURL layer.

OpsLens Phase 3 v1 deliberately narrows the general PURL contract further: a correlation identity requires both package and version and rejects qualifiers/subpaths until explicitly modeled.

## Why `packaging.version.Version`

PEP 440 ordering contains semantics that must not be reimplemented with lexical strings or hand-written tuples, including pre-releases, post-releases, development releases, epochs, and accepted normalized spellings.

The repository lock already contains `packaging` because pytest depends on it. Before this correlation module becomes a deployable runtime dependency, `packaging` must also be promoted to an explicit OpsLens project/runtime dependency and the lockfile regenerated. The current branch intentionally keeps that dependency-wiring change separate from the identity semantics so the lockfile remains authoritative during this gate.

## Failure behavior

Identity evidence fails closed for:

- unknown ecosystem;
- surrounding whitespace in ecosystem/package/version tokens;
- invalid PyPI project names;
- invalid PEP 440 concrete versions;
- malformed purls;
- invalid percent escapes;
- purl/package or purl/version disagreement;
- qualifiers/subpaths in the Phase 3 v1 purl contract.

None of these states is converted to `not_affected`.

## PURL detail

Canonical PURL construction percent-encodes component data according to the PURL standard. This matters for valid PEP 440 syntax that uses characters outside the PURL canonical unencoded set.

Examples:

```text
1!2.0       -> pkg:pypi/demo-package@1%212.0
1.0+cpu.1   -> pkg:pypi/demo-package@1.0%2Bcpu.1
```

## Validation

Local isolated validation of the new identity code completed with:

```text
28 passed
```

A reusable pull-request Python CI workflow is added in the same branch to run:

```text
uv lock --check
uv sync --frozen
ruff check src tests
pyright
pytest
```

The draft PR remains the authoritative CI validation before merge.

## Next gate

Only after this identity layer and CI are green:

```text
GitHub vulnerable_version_range
 -> strict clause parser
 -> typed comparison operator
 -> PEP 440 bound version
 -> conjunction evaluator
 -> affected / not_affected / unsupported
 -> deterministic evidence
```
