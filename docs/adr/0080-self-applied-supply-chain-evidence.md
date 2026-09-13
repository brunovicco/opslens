# ADR 0080 — Apply the supply-chain argument to this repository, scoped honestly

- Status: Accepted
- Date: 2026-09-13
- Supersedes: none
- Related: ADR 0008 (PyPI correlation semantics), ADR 0011 (immutable uv.lock evidence), ADR 0078 (canonical serialization)

## Context

OpsLens argues that dependency risk should be evidence-backed, that identity must
be content-addressed, and that missing evidence is not benign evidence. Until now
the repository made that argument only about *other* repositories. Its own
dependencies were unwatched, unaudited, and had no SBOM, and the deterministic
identity layer ran exclusively on fixtures.

That is the one place the argument does not apply to itself, and it is the first
thing a reviewer notices.

The tempting version of fixing it is the dishonest one: run the repository's own
pipeline over its own lock and present the result as "OpsLens found no
vulnerabilities in OpsLens". That claim is not available. Correlating packages
against GHSA, NVD, KEV and EPSS requires the request-time threat evidence
authority, whose only V1 implementation is fixture-backed. Presenting an identity
derivation as a vulnerability verdict would be exactly the conversion this
repository exists to forbid:

```text
missing evidence != benign evidence
dependency identity != vulnerability finding
```

## Decision

Three separate mechanisms, each answering one question, none substituting for
another.

**`scripts/self_dependency_evidence.py` — deterministic identity.** Runs the
repository's own `parse_uv_lock_evidence` and
`normalize_uv_lock_pypi_dependencies` over its own `uv.lock`, binding the result
to git's immutable coordinates: commit sha, tree sha, and the blob sha of the
lock. The run is refused when the working-tree lock differs from the committed
blob, so the evidence can never describe a tree that was not committed. The
payload carries an explicit `authority` block recording what did *not* happen —
no model execution, no network, no repository-code execution, no vulnerability
correlation — and its identity is a `canonical_sha256` under ADR 0078.

Because the payload binds the commit, the digest moves with every commit. That is
intended. The asserted property is determinism at a given checkout, not a fixed
number, and the workflow proves it by deriving twice and comparing bytes.

**`.github/workflows/supply-chain.yml` — conventional scanning, kept separate.**
`pip-audit --strict` over `uv export --frozen` output answers the
known-vulnerable question that the deterministic layer cannot. `--strict` makes an
audit *error* a failure rather than reporting an incomplete result as a clean one.
A CycloneDX SBOM is built twice with `--output-reproducible` and compared byte for
byte before being published, because an SBOM that cannot be rebuilt to the same
bytes cannot carry a content-addressed identity. The job runs weekly as well as
on change: the lock does not move, but the advisory database does, so
known-vulnerable is a claim with an expiry date.

**`.github/dependabot.yml` — watching.** uv and github-actions, weekly, grouped
so a routine bump arrives as one reviewable pull request rather than a dozen that
each re-run the full quality gate. Security updates are their own group so they
are never batched behind a version bump.

The scoping note is part of the deliverable, not a caveat bolted on: both READMEs
and the script's own docstring state what this proves and what it does not.

## Consequences

Positive:

- The repository's central claim now applies to the repository. The identity
  layer is exercised against a real lock instead of only fixtures, and a
  regression in it fails CI on real input.
- The three questions stay separable in review. A reviewer can see that identity
  is offline and deterministic, that scanning is conventional and dated, and that
  neither is being passed off as the other.
- The SBOM is a publishable artifact with a stable digest, which is what a
  content-addressed supply-chain argument needs to exist at all.

Negative:

- The self-identity digest changes on every commit, so it cannot be quoted as a
  stable figure in documentation. The READMEs show the shape, not the value.
- `_REPOSITORY_ID` in the script is a placeholder. The domain requires a numeric
  GitHub repository id; the script never calls the GitHub API, so no real one is
  available. The evidence is bound by commit and blob sha, not by that number,
  and the docstring says so.
- The weekly scheduled audit can fail on a day nothing in the repository changed.
  That is the correct behaviour and it will read as noise until it is read
  correctly.

## Verification

```text
scripts/self_dependency_evidence.py                 PASS
locked packages                                     55
normalized PyPI dependencies                        54
unsupported packages                                1
two runs at one commit                              byte identical
pip-audit --strict over the exported lock           No known vulnerabilities found
cyclonedx --output-reproducible built twice         byte identical, 54 components
demo suite evaluation identity                      sha256:ed99f385...cee146d3  (unchanged)
```

```text
dependency identity != vulnerability finding
deterministic identity != standing safety claim
```
