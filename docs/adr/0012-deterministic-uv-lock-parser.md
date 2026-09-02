# ADR 0012 — Parse verified `uv.lock` evidence deterministically

- Status: Accepted
- Date: 2026-09-02
- Phase: 4 — Repository Intelligence

## Context

ADR 0011 established immutable inert `uv.lock` evidence bound to an exact public GitHub commit snapshot. The file bytes are already bounded and integrity-verified before this parser receives them.

Phase 4 now needs concrete dependency/version evidence that can later feed the deterministic Phase 3 PyPI correlation engine without executing third-party repository code.

The permanent rule remains:

> **READ, NEVER EXECUTE third-party repository code.**

uv documents `uv.lock` as a human-readable TOML lockfile containing exact resolved package versions. It is also universal/cross-platform: a single lockfile may represent packages across multiple Python/environment marker branches. Therefore a locked package record is repository resolution evidence, not proof that the package is currently loaded or deployed at runtime.

## Decision

Phase 4 v1 parses only `ImmutableRepositoryFileEvidence` whose path is the already allowlisted `uv.lock`.

The parser uses Python's standard-library `tomllib` directly on verified inert bytes. No `uv` process, Python import from the repository, package manager, resolver, build hook, virtual environment, or repository script is invoked.

```text
ImmutableRepositoryFileEvidence
  -> strict TOML parse with tomllib
  -> validate supported uv.lock schema
  -> validate bounded package records
  -> classify package source
  -> PyPI locked-package evidence
     + explicit unsupported package evidence
```

## Supported lockfile schema

Phase 4 v1 supports:

```text
version = 1
revision absent, or revision in {1, 2, 3}
```

A missing `revision` is preserved as `None`; it is not rewritten to an invented revision number. Historical schema-v1 lockfiles exist without the field.

A greater or otherwise unsupported schema/revision fails closed at the lockfile level. Future uv-compatible changes must be reviewed before OpsLens silently accepts them.

The parser requires a top-level `package` array and limits it to **5,000 package records**, even though ADR 0011 already caps the entire raw file at 1 MiB. This adds an explicit logical-work bound independent of byte size.

## Lockfile-level provenance

The parser preserves:

```text
source file evidence id
schema version
revision (nullable)
requires-python (nullable)
top-level resolution-markers (ordered tuple)
```

`requires-python` and resolution markers are provenance only in this gate. OpsLens does not evaluate them to infer runtime exposure.

## Package record semantics

Every package record preserves its original zero-based array position. Records are never deduplicated by package name or version because universal lockfiles can contain distinct marker-specific resolutions.

For every record, `name`, `version`, and `source` are required and validated structurally before source classification.

### Supported PyPI source

A package is eligible for the first Phase 3 normalization integration only when:

```toml
source = { registry = "https://pypi.org/simple" }
```

The registry URL must match exactly. OpsLens does not assume a mirror, custom registry, TestPyPI, direct URL, Git repository, editable project, virtual workspace member, or local path is PyPI evidence.

A supported PyPI record emits:

```text
record_index
name_original
version_original
registry_url
resolution_markers
```

Package-level `resolution-markers`, when present, are preserved as an ordered tuple of strings. They are not evaluated by this gate.

### Explicit unsupported package evidence

Structurally valid non-PyPI source records do not disappear silently. They emit explicit unsupported evidence with:

```text
record_index
name_original
version_original
source_kind
reason_code
resolution_markers
```

Initial source/reason classifications are:

```text
registry != canonical PyPI -> custom_registry / unsupported_registry
virtual                   -> virtual / unsupported_non_registry_source
editable                  -> editable / unsupported_non_registry_source
git                       -> git / unsupported_non_registry_source
path or directory         -> path / unsupported_non_registry_source
other single source key   -> <key> / unsupported_source_kind
```

If the `source` value is malformed, empty, contains multiple competing source-kind keys, or a supported registry record lacks a valid name/version, the entire lockfile parse fails closed rather than guessing intent.

## Version semantics

This gate does not interpret PEP 440 and does not normalize names or versions. It preserves the raw lockfile strings.

Phase 3 already owns canonical PyPI package/version semantics. A later integration gate will pass supported PyPI locked-package evidence through that existing deterministic domain contract rather than duplicating normalization here.

## Runtime boundary

A universal `uv.lock` can represent alternative marker branches. Therefore this parser may establish:

> repository lock evidence contains package X at version Y for one or more supported resolution contexts.

It does **not** establish:

> the currently deployed/runtime workload is executing package X at version Y.

Repository risk and runtime exposure remain separate concepts.

## Fail-closed behavior

Reject the lockfile when any of these occur:

- input is not verified `uv.lock` evidence;
- bytes are not valid TOML;
- TOML root is not a table;
- schema `version` is missing, boolean, non-integer, or not `1`;
- `revision` is present but boolean/non-integer/outside `{1,2,3}`;
- `requires-python` is present but not a non-empty string;
- top-level `resolution-markers` is present but not a list of non-empty strings;
- `package` is missing/not an array/empty;
- more than 5,000 package records exist;
- any package record is not a table;
- required package name/version/source is malformed;
- package-level `resolution-markers` is malformed;
- source classification is structurally ambiguous.

Structurally valid but unsupported source kinds remain explicit unsupported package evidence rather than causing false PyPI attribution.

## Security, AWS, IAM, and cost

This gate adds no network operation beyond the already completed acquisition gate and no AWS service, IAM permission, cache, queue, database, model call, or third-party executable.

Incremental AWS cost: **$0**.

The bounded work is local TOML parsing of at most 1 MiB and at most 5,000 package records.

## Alternatives considered

### Execute `uv tree` or `uv export`

Rejected. It violates the inert-evidence boundary and may invoke dependency/resolution behavior against third-party project input.

### Regex package extraction

Rejected. TOML has a real grammar and uv's lockfile contains marker forks and structured sources. Regex extraction would silently lose structure and increase false attribution risk.

### Treat all `registry` sources as PyPI

Rejected. uv supports custom package indexes; doing so would conflate package identity authority across registries.

### Normalize package/version inside the parser

Rejected. Phase 3 already owns canonical PyPI semantics. Duplicating them would create competing authorities.

## Exit criteria

This gate is complete when:

- only verified `uv.lock` file evidence can be parsed;
- schema v1 and the explicit revision support window are enforced;
- parsing uses stdlib `tomllib` only;
- package processing has an explicit logical count bound;
- exact PyPI registry records are emitted as typed evidence;
- custom/local/Git/virtual/editable sources remain explicit unsupported evidence;
- marker provenance is preserved without runtime claims;
- malformed/ambiguous structures fail closed;
- duplicate name/version records are preserved by record index;
- no package-manager/repository code execution occurs;
- Repository Intelligence Ruff/Pyright/pytest gates pass;
- Phase 3 correlation regression remains green.

## Next gate

Pass supported PyPI locked-package evidence through the existing Phase 3 canonical package/version/purl contract and produce normalized repository dependency evidence without yet performing vulnerability lookup.
