# ADR 0081 — Ship OpsLens as an installable package with console entry points

- Status: Accepted
- Date: 2026-09-13
- Supersedes: none
- Related: ADR 0077 (V1 demonstration boundary), ADR 0080 (self-applied supply-chain evidence)

## Context

`pyproject.toml` declared `[project]` metadata but no `[build-system]`, so uv
resolved the repository as a virtual project:

```text
uv.lock:  source = { virtual = "." }
```

A virtual project is a dependency environment, not a distributable. The practical
consequences were all reviewer-facing:

- `pip install .` and `uv tool install` both fail. The only way to run OpsLens is
  to clone it, sync it, and invoke files under `scripts/` with an interpreter.
- Every script needed `_bootstrap.ensure_repository_src_on_path()` to find `src/`,
  because nothing had installed the package.
- `py.typed` was absent, so a consumer of the package — had one been possible —
  would have received no type information from a codebase that is pyright strict
  throughout.

There was a second, quieter problem. `scripts/demo_opslens.py` was a thin shim
delegating to `opslens.demo.cli:main`, but `scripts/demo_opslens_web.py` and
`scripts/evaluate_opslens_demo.py` each carried their **own** argparse layer
inside `scripts/`. That code is outside the package. Two of the three documented
reviewer commands could therefore never be exposed as console entry points
without duplicating their parsers, and any duplicate would be free to drift.

The project description was also stale: "Operational intelligence platform for
software delivery and cloud operations" describes neither what the code does nor
what ADR 0077 says the project is. Published metadata is a claim like any other.

## Decision

**The CLI layer moves inside the package.** `opslens.demo.web_cli` and
`opslens.demo.evaluation_cli` now own the argparse surfaces that lived in
`scripts/`. The two scripts become shims identical in shape to
`scripts/demo_opslens.py`: bootstrap `sys.path`, import `main`, delegate.

**Three console entry points, paired with those shims.**

```toml
[project.scripts]
opslens-demo = "opslens.demo.cli:main"
opslens-demo-evaluate = "opslens.demo.evaluation_cli:main"
opslens-demo-web = "opslens.demo.web_cli:main"
```

`tests/unit/demo/test_console_entry_points.py` asserts that each declared entry
point resolves to a callable inside the shipped package, that each one has a
`scripts/` shim delegating to the *same* module, and that no shim defines a
function, class, or module-level assignment of its own. Logic in `scripts/` is
unreachable from an installed command, so the guard forbids it structurally
rather than by convention. Adding a console script without its shim, or vice
versa, fails the suite.

**`uv_build` is the build backend**, not hatchling or setuptools. uv is already a
hard prerequisite — `[tool.uv] required-version = ">=0.12.3"` — and its backend
ships inside the uv binary, so `uv sync` and `uv build` need no additional build
dependency. A project whose thesis is that dependency risk should be
evidence-backed does not add a build-time dependency it can avoid. `pip install .`
still works: `uv_build` is a normal PEP 517 backend published on PyPI.

**`src/opslens/py.typed` is added**, so the strict typing the repository already
enforces internally is actually delivered to a consumer, and the
`Typing :: Typed` classifier is true rather than aspirational.

**The metadata describes the project honestly.** The description now says what
the code does. The classifiers stop at `Development Status :: 4 - Beta`, which
matches ADR 0077's demonstration boundary; nothing claims production status.

## Consequences

Positive:

- `uv tool install git+https://github.com/brunovicco/opslens` followed by
  `opslens-demo` is a complete reviewer path with no clone and no `PYTHONPATH`.
- The wheel contains only `opslens/` and its `dist-info`: no tests, no `labs/`,
  no `scripts/`. Verified by inspecting the built artifact.
- The evaluation identity produced by the **installed wheel**, run from a
  directory with no checkout on the path, is byte identical to the one produced
  from the repository: `sha256:ed99f385...cee146d3`. That is the strongest
  available evidence that the distributed artifact is the same code.
- Two of three reviewer commands stopped being structurally impossible to install.

Negative:

- `uv.lock` changes `virtual` to `editable`, which moves the self-dependency
  evidence digest from ADR 0080. Expected: that digest is bound to the commit by
  design.
- `uv sync` now performs an editable install of the project, so a stale build
  artifact is one more thing that can go wrong in a developer environment. The
  `scripts/` shims keep working through `_bootstrap` regardless, which is why
  they were kept rather than deleted.
- Declaring a build backend commits the repository to keeping the package
  buildable. That is the point, and `uv build` in CI would make it enforced
  rather than assumed — not done here, and worth doing next.

## Verification

```text
uv build                                            sdist + wheel, wheel built from the sdist
wheel top-level entries                             opslens/, opslens-0.1.0.dist-info/  (nothing else)
py.typed shipped                                    opslens/py.typed
LICENSE shipped                                     dist-info/licenses/LICENSE
installed console scripts                           opslens-demo, opslens-demo-evaluate, opslens-demo-web
opslens-demo --exit-code outcome (material)         1
opslens-demo --exit-code outcome (fail-closed)      2
opslens-demo-evaluate from the installed wheel      sha256:ed99f385...cee146d3  (identical to the repository)
uv.lock                                             source = { editable = "." }
ruff check . / pyright                              clean / 0 errors
pytest                                              full suite green, 6 new entry-point guards
verify_module_imports.py                            559 modules imported
```

```text
installable != production-ready
demonstration readiness != production readiness
```
