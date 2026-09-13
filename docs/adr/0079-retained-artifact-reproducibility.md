# ADR 0079 — Rebuild retained artifacts from their pinned tree, not from HEAD

- Status: Accepted
- Date: 2026-09-13
- Supersedes: none
- Related: ADR 0011 (immutable uv.lock evidence), Gate 19.5, Gate 19.6, Gate 19.7

## Context

`verify_phase19_gate19_5_async_artifact_build.py` rebuilt the async Lambda
artifacts from the **working tree** and compared the result against the frozen
prepublication manifest in `labs/evidence/`.

That comparison asserts "HEAD reproduces the retained artifact". It has two
problems.

**It proves nothing about the retained evidence.** The retained artifact was
built from a specific tree. Whether a later HEAD happens to reproduce it is a
statement about HEAD, not about whether the evidence is sound.

**It makes every later change to packaged source a gate failure.** Any edit
under `src/opslens/public_analysis` — or anything it imports — moves artifact
bytes and fails the gate, regardless of merit. Two ordinary changes hit this
immediately:

```text
uncompressed_bytes   26.156.069 -> 26.155.563   (api)
artifact_sha256      99477676... -> 32c2ef09...
```

Re-freezing the manifest was not an option. Those digests are referenced by nine
retained evidence files, including `phase-19-gate-19-6-plan-input-v1.tfvars.json`
and the Gate 19.7 admission evidence for a Terraform apply that materialized 21
real AWS resources. Re-freezing would claim a plan and an apply had run against
artifacts that did not exist at the time — falsifying history to make a gate
green, which is the opposite of what this repository is for.

One further discovery while pinning the rebuild: `source_main_sha` in the
manifest is **not** the tree that was packaged. It records
`a5067e05` (Gate 19.4, PR #351), the main commit the Gate 19.5 work branched
from. `src/` changed between that commit and `61749bf` (PR #353), which
introduced both the builder and the manifest. Building from `a5067e05` does not
reproduce the retained digests; building from `61749bf` reproduces them exactly.

## Decision

The gate proves:

> the retained artifact is deterministically reproducible from the tree that
> produced it, using the builder that ships today

The rebuild runs inside a `git worktree` pinned at `_PINNED_BUILD_COMMIT`
(`61749bf`), fetched on demand so a shallow CI clone works. Determinism is still
checked by building twice and requiring byte-identical output.

**The builder is today's, not the pinned tree's.** It is copied into the
worktree before the rebuild, so the gate exercises current build tooling against
the recorded source. This is what keeps the freed constraint honest: packaged
source may now move freely, but a builder change that stops reproducing the
retained digests fails here, while one that does not affect packaging passes.

Comparing the two builders byte for byte was tried first and rejected. It fails
on changes that cannot affect an artifact — removing a `__future__` import from
the builder tripped it immediately — so it tests text where the property of
interest is behaviour.

The builder's safety controls (`--require-hashes`, `--no-deps`, the fixed ZIP
timestamp, the human-only publication authority) stay checked against the
working tree, because that assertion is about the builder as it stands today.

The pinned tree carries its own `[tool.uv] required-version`. That setting never
reaches a packaged artifact, so the rebuild runs with `UV_NO_CONFIG=1` and stays
reproducible under whichever uv the caller has installed. Verified: builds with
and without project configuration produce the identical manifest.

## Consequences

Positive:

- The gate now asserts something that stays true. It cannot be invalidated by
  unrelated work, and it fails loudly if the retained evidence stops being
  reproducible or the builder drifts.
- Changes to `public_analysis` and everything it imports are no longer blocked
  by evidence describing an older artifact.
- The distinction between `source_main_sha` (what the work branched from) and
  the packaged tree is now explicit in the code rather than assumed.

Negative:

- The gate needs the pinned commit. A shallow clone triggers one extra
  `git fetch --depth 1`; a clone with no access to that commit fails with a
  named error rather than a confusing digest mismatch.
- The rebuild writes today's builder into the temporary worktree. That worktree
  is discarded afterwards and nothing in it is packaged except `src/`.
- Re-freezing the manifest is now a two-part change — new evidence plus a moved
  pin. That is deliberate: it makes re-freezing visible in review rather than a
  side effect of editing a JSON file.
- `_PINNED_BUILD_COMMIT` is a second pin next to `_EXPECTED_SOURCE_MAIN`. They
  mean different things and both are asserted, so the comment explains which is
  which.

## Verification

```text
verify_phase19_gate19_5_async_artifact_build.py     PASS
rebuilt_from_pinned_tree                            61749bfac7b7bc9d032567e0b1870f8c1f7dedd4
api_sha256                                          99477676...cfcd876e   (retained digest)
worker_sha256                                       0d04b472...f6ecbdc9   (retained digest)
canonical_prepublication_manifest                   PASS
```

```text
retained artifact identity != current source identity
historical evidence != standing authority
plan != apply
```
