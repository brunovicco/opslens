# ADR 0082 — Configure the semantic-query catalog at deployment, never at request time

- Status: Accepted
- Date: 2026-09-13
- Supersedes: none
- Related: ADR 0003 (AWS regional strategy), ADR 0016 (typed semantic query compilation), Gate 6.1

## Context

The semantic-query slice had one environment's identifiers written into its code:

```python
# adapters/outbound/athena.py
ATHENA_DATABASE = "opslens_dev"
ATHENA_WORKGROUP = "opslens-dev"
_EPSS_RELATION = '"opslens_dev"."epss_scores"'

# application/compiler.py
_EPSS_TABLE = '"opslens_dev"."epss_scores"'
```

Three problems, in ascending order of seriousness.

The slice cannot address any environment other than `dev`. Promoting it requires
editing source, which is the definition of configuration that is not
configuration.

A development environment's name ships inside the distributable package. As of
ADR 0081 that package is actually published, so the leak is no longer theoretical.

The same relation is spelled out twice, in two layers, as two separate string
literals. The adapter's grammar guard compares compiled SQL against its own copy.
Those two literals agreeing is load-bearing for the security model and nothing
enforced it: edit one and the guard starts rejecting every legitimate query, or —
worse, if the mismatch went the other way — stops describing what it verifies.

The obvious fix is the wrong one. Accepting a database or table from a request
would destroy the property the slice exists to hold: the compiler owns the entire
statement and the model receives no SQL authority whatsoever.

## Decision

One validated value object, resolved once, injected explicitly.

```text
configurable at deployment != selectable at request time
```

`SemanticQueryCatalog` (frozen, slots) carries `database`, `workgroup` and
`epss_table`, exposes `epss_relation` as the single renderer of the quoted
relation, and is resolved from the environment at the composition root:

| Variable | Default |
| --- | --- |
| `OPSLENS_ATHENA_DATABASE` | `opslens_dev` |
| `OPSLENS_ATHENA_WORKGROUP` | `opslens-dev` |
| `OPSLENS_ATHENA_EPSS_TABLE` | `epss_scores` |

The defaults are exactly the names the `dev` Terraform root creates, so no
existing deployment changes behaviour. `compile_semantic_query` and
`AthenaQueryExecutor` both take the catalog as a required argument — no default,
no module-level singleton, no environment read inside application code. The two
composition scripts resolve it and inject it.

**Validation is what makes configuration safe rather than dangerous.** The
relation is interpolated into SQL text, so an unvalidated variable would convert a
trusted constant into an injection vector. Identifiers must match
`[A-Za-z_][A-Za-z0-9_]*` — deliberately narrower than Athena permits, so no quote,
dot, semicolon, whitespace or comment marker can survive — and the workgroup must
match `[A-Za-z0-9._-]+`. Both are length-bounded. A blank variable is treated as
unset rather than as an empty identifier, because a half-rendered deployment
template must not produce `""."epss_scores"`.

**The duplication becomes a fail-closed check instead of a silent coupling.** The
adapter validates compiled SQL against *its own* catalog's relation. A compiler
and an adapter wired to different catalogs now reject before any Athena call
rather than querying the wrong environment. A test asserts exactly that, including
that no `StartQueryExecution` call is made.

**A guard keeps the next name from being hardcoded quietly.** A test walks the
whole package and fails if `opslens_dev` or `opslens-dev` appears in any module
other than the configuration one.

**The pinned `us-east-1` constants are deliberately left alone.** They are not the
same defect. ADR 0003 makes the Region part of the infrastructure contract, and
the `_REQUIRED_REGION` constants in the Bedrock CLI paths are assertions that the
operator is in the contracted Region, not configuration that was forgotten. A
reviewer reading `us-east-1` in the tree after this change should read it as a
decision, which is why this ADR says so explicitly.

## Consequences

Positive:

- The slice can address another environment without a code change, and the package
  no longer carries a development environment's name.
- One module owns the relation's rendering. The two-literal coupling that the
  security guard silently depended on is gone.
- Mismatched composition is a rejected query rather than a query against the wrong
  database. That failure mode did not previously exist as a check.
- The configured values are validated more strictly than the hardcoded constants
  ever were, so the slice is harder to misuse after this change than before it.

Negative:

- `compile_semantic_query` and `AthenaQueryExecutor` both gained a required
  argument, so every construction site had to be updated. Deliberate: a default
  would reintroduce a hidden global and let a caller forget the catalog entirely.
- Composition roots now have one more responsibility. Two scripts, one line each.
- The defaults still name `dev`. They have to, to keep current behaviour, and they
  are now in one documented place instead of four literals across two layers.
- Terraform is untouched. The names it creates remain the source of truth, and an
  operator copies them into the three variables. Emitting them as Terraform
  outputs would be more convenient but would disturb a root with retained plan and
  apply evidence for no functional gain.

## Verification

```text
ruff check . / pyright                              clean / 0 errors
pytest                                              full suite green, 34 new tests
verify_module_imports.py                            560 modules imported
grep for opslens_dev / opslens-dev under src/       only semantic_query/config.py
unconfigured catalog                                "opslens_dev"."epss_scores"   (unchanged)
configured catalog reaches Database, WorkGroup, SQL  asserted
compiler and executor on different catalogs          rejected, zero Athena calls
identifier carrying a quote, dot, semicolon,
comment marker, space or leading digit               rejected
demo suite evaluation identity                       sha256:ed99f385...cee146d3  (unchanged)
```

```text
configurable at deployment != selectable at request time
compiler-owned SQL != model-selectable SQL
```
