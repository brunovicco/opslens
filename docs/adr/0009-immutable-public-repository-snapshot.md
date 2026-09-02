# ADR 0009 — Use exact GitHub commit identity for repository snapshots

- Status: Accepted
- Date: 2026-09-02
- Phase: 4 — Repository Intelligence

## Context

Phase 4 must analyze real public GitHub repositories without executing third-party code.
The result must be reproducible for one immutable repository snapshot and later feed deterministic dependency evidence into the Phase 3 correlation engine.

The GitHub dependency graph can export SPDX SBOM data, but the repository SBOM endpoint is repository-scoped and does not expose a commit/ref parameter. GitHub's repository contents API, by contrast, accepts an explicit `ref` and can therefore read inert files from an exact resolved commit.

The permanent security rule is:

> **READ, NEVER EXECUTE third-party repository code.**

## Decision

Phase 4 v1 defines an immutable repository snapshot from GitHub repository identity plus one exact full commit SHA.

```text
public GitHub repository
  -> validated repository identity
  -> requested ref/default branch
  -> exact resolved commit SHA
  -> immutable repository snapshot
  -> inert evidence reads at that SHA
```

### Repository identity

The authoritative repository identity contains:

```text
provider = github
repository_id = positive GitHub numeric repository id
owner
name
full_name = owner/name
visibility = public only
```

The numeric repository id is the stable source identity. `owner/name` remains human-readable provenance and must agree with the component fields.

Private repositories are outside the Phase 4 v1 contract and fail closed.

### Snapshot identity

The authoritative snapshot identity is:

```text
github:<repository_id>@<full-commit-sha>
```

The requested branch/tag/ref is provenance, not snapshot authority. A moving branch name must first resolve to an exact commit SHA.

Phase 4 v1 accepts only a full lowercase 40-hex Git commit SHA. Abbreviated SHAs do not establish an immutable snapshot contract.

The resolved Git tree SHA is preserved as additional evidence but does not replace the commit as the snapshot identity.

### Dependency evidence

Repository content must be acquired as inert data at the exact commit SHA. No package manager, build tool, test runner, install hook, import, compiler, container build, repository script, or dependency resolver may be executed against third-party repository code merely to discover dependencies.

The first dependency parser will be selected in a later gate. This ADR does not authorize dependency parsing yet.

### GitHub SBOM

GitHub's SPDX SBOM remains useful supplemental evidence, especially for dependency-graph relationships and ecosystem coverage. It is not the Phase 4 v1 immutable snapshot authority because its repository endpoint is not bound by an explicit commit/ref parameter.

A future gate may bind SBOM evidence to an immutable snapshot only if the acquisition semantics can be proven rather than assumed.

## Fail-closed behavior

The initial contract rejects:

- non-GitHub providers;
- non-positive or boolean repository ids;
- malformed owner/name/full_name identity;
- private repositories;
- empty or dirty requested refs;
- abbreviated, uppercase, malformed, or non-40-hex commit SHA values;
- malformed tree SHA values;
- disagreement between repository identity components.

Unsupported input is not silently normalized into a different repository or snapshot.

## AWS and cost boundary

This gate adds no AWS resource, IAM permission, queue, cache, Lambda, or model call.

AWS runtime/cache decisions remain deferred until real acquisition and repeat-analysis measurements justify them.

## Consequences

Positive:

- moving branches cannot silently redefine prior analysis;
- evidence can be keyed by immutable repository snapshot;
- third-party code remains data rather than executable input;
- repeated analysis can later reuse evidence by snapshot id;
- no AWS/runtime cost is introduced by this contract gate.

Trade-offs:

- dependency-graph SBOM cannot be treated as exact commit authority in v1;
- the first implementation supports public GitHub only;
- Git object-format expansion beyond the frozen 40-hex SHA contract requires an explicit contract version change.

## Validation gate

Before dependency parsing begins, tests must prove:

1. valid public repository identity;
2. private repository rejection;
3. repository component mismatch rejection;
4. exact full commit SHA requirement;
5. requested-ref provenance does not define snapshot identity;
6. deterministic snapshot id for identical repository id + commit SHA;
7. changed commit SHA changes snapshot identity;
8. malformed evidence fails closed.

## References

- GitHub Docs — REST API endpoints for repository contents (`ref` query parameter).
- GitHub Docs — REST API endpoints for commits (`ref` may be a commit SHA, branch, or tag).
- GitHub Docs — REST API endpoints for software bill of materials (SBOM).