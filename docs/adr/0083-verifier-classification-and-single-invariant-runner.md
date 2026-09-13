# ADR 0083 — Classify the verifiers, and run the standing set from one place

- Status: Accepted
- Date: 2026-09-13
- Supersedes: none
- Related: ADR 0079 (retained artifact reproducibility), ADR 0081 (installable package)

## Context

`scripts/` holds 28 files named `verify_*.py`. The audit finding called this
clutter. Looking properly, the problem was not the count.

**They are two different kinds of tool wearing one name.** Twenty-three take no
argument, assert a repository invariant, and must pass on any change. Five take a
Terraform plan, a published artifact manifest or a live measurement artifact and
admit or reject it:

```text
verify_phase19_gate19_2_live_measurement.py     --expected-opslens-commit-sha
verify_phase19_gate19_5_artifact_publication.py --prepublication --publication
verify_phase19_gate19_6_exact_plan.py           --plan-json
verify_phase19_gate19_7_fresh_plan.py           --plan-json --plan-binary --expected-source-head
verify_phase19_gate19_7_recovery_plan.py        --plan-json --plan-binary --expected-source-head
```

An admission tool cannot pass on its own and was never meant to. But nothing said
so, so running everything produced "23 of 28 pass" — which reads as five broken
gates rather than as five tools invoked without their inputs. That misreading is
the actual defect, and it is the kind a reviewer makes in the first ten minutes.

**No single place knew the standing set.** A verifier ran in CI only if some
per-slice workflow happened to name it. Two did not:
`verify_phase19_gate19_7_untaint_contract.py` and
`verify_phase19_gate19_7_recovery_plan.py` were referenced by **no workflow at
all**. The first is a standing verifier that ran nowhere; neither was linted or
type-checked anywhere, in a repository that is otherwise ruff-clean and pyright
strict throughout.

**The lists were written three times each.** `public-runtime-readiness-ci.yml`
named the same thirteen verifier paths in its `paths:` filter, its ruff step and
its pyright step. All three had to be edited together for a new verifier to be
covered, and they had already drifted: the list covered 12 of the 19 phase-19
verifiers on disk.

Deleting or relocating any of these was never an option. They are cited by
retained gate evidence, and moving them would leave the runbooks in `labs/`
describing commands that no longer exist — falsifying the record to tidy a
directory.

## Decision

**One registry, derived from behaviour, not asserted by comment.**
`scripts/run_repository_invariants.py` declares `STANDING_VERIFIERS` (23) and
`EVIDENCE_ADMISSION_TOOLS` (5), runs the standing set, prints one result line each
with timing, and reports the admission tools as deliberately not run. It refuses
to start if the registry does not match the files on disk.

`tests/unit/scripts/test_verifier_registry.py` makes the classification
self-enforcing: it parses each script's own argparse definition and requires that
every verifier registered as standing has **no** required argument, and every
verifier registered as an admission tool has **at least one**. A new verifier
cannot be added unclassified, and one cannot be filed under the wrong kind. The
static classification was checked against 28 bare invocations and agrees exactly.

**The standing set runs with no paths filter.** A `repository-invariants` job in
the quality gate runs the runner, and lints and strictly types all 28 verifiers
plus the runner — coverage the hand-written per-slice lists never had.

**Globs replace the hand-written lists.** The three repetitions in
`public-runtime-readiness-ci.yml` become `scripts/verify_phase19_*.py`, and the
five names in `evaluation-readiness-ci.yml` become `scripts/verify_phase18_*.py`.
A list that must be edited in three places to stay correct is a list that will be
wrong; a glob cannot drift. Net: 35 fewer lines across the two workflows, and
seven previously uncovered phase-19 verifiers now covered.

**`scripts/README.md` says what the directory is.** Seventy-one entry points
classified by prefix, with the verifier taxonomy stated first, and an explicit note
that `probe_*` and `discover_*` are retained provenance rather than maintained
tooling.

**Branch cleanup stays manual, and deliberately so.** Ten remote branches exist
besides `main`. Exactly one — `docs/phase19-gate19-6-plan-admission-closeout` — is
a strict ancestor of `main` and provably safe to delete. For the rest, this
repository squash-merges, which destroys patch lineage: a local clone cannot tell
a merged-and-stale branch from abandoned work with unique commits. Three are live
Dependabot pull requests and `feat/governed-gateway-semantic-planner` is PR #89,
deferred rather than abandoned. So no branch is deleted by this change. The
operator prunes with a script that reads each branch's pull-request state from
GitHub and never guesses.

## Consequences

Positive:

- "23 of 28" stops being a number that needs explaining. The runner says 23/23 and
  names the five tools it did not run and why.
- Two verifiers that ran nowhere now run, and all 28 are linted and strictly typed.
- The classification cannot rot. It is derived from each script's argparse surface
  and checked in the test suite, not maintained as prose.
- The workflows lost their triple-listing, which is the only reason they had drifted.

Negative:

- The runner duplicates work in two places: `verify_module_imports.py` also runs in
  the `import-smoke` job. Two seconds, and `import-smoke` keeps a named CI signal
  whose comment explains a non-obvious invariant, so the overlap is deliberate.
- `repository-invariants` needs `fetch-depth: 0`, because the Gate 19.5 verifier
  rebuilds from a pinned commit. Cheaper than the extra fetch it would otherwise do.
- The registry is a second place that lists verifier names. It is the only place,
  the test proves it complete, and the runner refuses to start when it drifts.
- The directory still holds 28 `verify_*` files. That is the right outcome: they are
  cited by retained evidence, and relocating them would break the runbooks that
  reference them.

## Verification

```text
run_repository_invariants.py                         23/23 standing verifiers passed in 9.3s
                                                     5 admission tools not run, by design
static classification vs 28 bare invocations         identical
tests/unit/scripts/test_verifier_registry.py         32 tests
ruff check scripts/verify_*.py + the runner          All checks passed
pyright scripts/verify_*.py + the runner             0 errors, 0 warnings
verify_workflow_security.py                          PASS (after the workflow edits)
phase19 glob                                         19 files  (hand-list covered 12)
phase18 glob                                         5 files
verifiers referenced by no workflow before            2 -> 0
workflow lines removed                                35
demo suite evaluation identity                        sha256:ed99f385...cee146d3  (unchanged)
```

```text
standing invariant != admitted evidence
historical evidence != standing authority
```
