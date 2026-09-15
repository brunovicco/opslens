# `scripts/`

Seventy-one entry points, and they are not one kind of thing. The prefix says
which kind, and a `verify_*` name says less than it looks like it does.

Every script is self-bootstrapping: `_bootstrap.ensure_repository_src_on_path()`
puts `src/` on the path, so any of them runs from a checkout with no
`PYTHONPATH`. Since ADR 0081 the three demo entry points also exist as installed
console commands (`opslens-demo`, `opslens-demo-evaluate`, `opslens-demo-web`).

## `verify_*` — two kinds of tool, not one

There are 28. Twenty-three are **standing verifiers**: they take no argument,
assert a repository invariant, and must pass on any change. Five are **evidence
admission tools**: they take a Terraform plan, a published artifact manifest or a
live measurement artifact and admit or reject it. An admission tool cannot pass
on its own and was never meant to.

```text
standing invariant != admitted evidence
a tool that needs input is not a failing gate
```

Nothing in the directory used to say which was which, so running everything read
as "23 of 28 pass" — five apparently broken gates that were in fact a different
kind of tool invoked wrongly.

```bash
uv run python scripts/run_repository_invariants.py --list   # the classification
uv run python scripts/run_repository_invariants.py          # run the standing set
```

The runner owns the registry; `tests/unit/scripts/test_verifier_registry.py`
derives each script's kind from its own argparse definition and fails if the
registry disagrees, so a new verifier cannot be added unclassified. The
`repository-invariants` job in the quality gate runs the standing set on every
change, with no paths filter.

## Everything else

| Prefix | Count | What it does |
| --- | ---: | --- |
| `verify_*` | 28 | Assert an invariant, or admit supplied evidence — see above |
| `build_*` | 15 | Build a deployable artifact (Lambda packages, AgentCore runtime) |
| `run_*` | 14 | Run a bounded experiment, query, replay or the invariant set |
| `publish_*` | 3 | Publish a built artifact. Human-authorized, create-only |
| `demo_*`, `evaluate_*` | 3 | The offline reviewer path, also installed as console commands |
| `probe_*`, `discover_*`, `select_*` | 6 | One-off source investigation retained as provenance |
| `materialize_*`, `seed_*` | 2 | Write a specific piece of retained state, deliberately manual |
| `self_dependency_evidence.py` | 1 | Derive this repository's own dependency identity (ADR 0080) |
| `run_repository_invariants.py` | 1 | Run the standing verifier set — see above |

A `publish_*` or `materialize_*` script never runs from CI. Publication
authority is human-only and create-only by design, which several retained
evidence files record as `publication_authority=HUMAN_ONLY_CREATE_ONLY`.

The `probe_*` and `discover_*` scripts are historical: they answered a question
about an upstream source once, and they are kept because the answer they produced
is cited by retained evidence. They are provenance, not maintained tooling.
