# ADR 0011 — Bind `uv.lock` evidence to an exact immutable repository snapshot

- Status: Accepted
- Date: 2026-09-02
- Phase: 4 — Repository Intelligence

## Context

Phase 4 can now resolve one public GitHub repository to an exact immutable commit snapshot and acquire bounded read-only GitHub REST evidence.

The next step is to introduce dependency evidence without violating the permanent security rule:

> **READ, NEVER EXECUTE third-party repository code.**

A dependency parser must never receive content from a moving branch or an unbounded/unverified source. Before any TOML parsing is authorized, OpsLens therefore needs a deterministic contract for one inert dependency file read from the exact commit SHA already established by the repository snapshot.

Phase 3 currently supports deterministic PyPI identity and version semantics. `uv.lock` is a suitable first repository artifact because it records concrete resolved Python package versions while remaining plain data that can be parsed without invoking `uv`, Python imports, package installers, build hooks, or repository code.

## Decision

Phase 4 v1 authorizes exactly one repository dependency-evidence path:

```text
uv.lock
```

No caller-controlled arbitrary path is accepted by this gate.

The acquisition flow is:

```text
ImmutableRepositorySnapshot
  -> exact commit SHA
  -> GET /repos/{owner}/{repo}/contents/uv.lock?ref=<exact-commit-sha>
  -> bounded GitHub content object
  -> strict Base64 decode
  -> size validation
  -> Git blob SHA validation
  -> OpsLens SHA-256 content digest
  -> ImmutableRepositoryFileEvidence
```

The requested branch/tag is never used to acquire file content. The authoritative `snapshot.commit_sha` is always supplied as the Contents API `ref`.

## File evidence contract

One accepted `uv.lock` evidence record contains:

```text
snapshot_id
repository_id
commit_sha
path = uv.lock
blob_sha
size_bytes
content_sha256
content_bytes
```

`content_bytes` is inert input for a later deterministic parser. This ADR does not authorize parsing yet.

### Size bound

The raw decoded file is limited to **1 MiB (1,048,576 bytes)**.

GitHub documents full Contents API behavior for files up to 1 MB; larger files require different media semantics. OpsLens intentionally fails closed instead of broadening acquisition behavior in this gate.

The enclosing JSON/Base64 HTTP response also receives its own explicit transport byte budget because Base64 and JSON framing are larger than the decoded file.

### Git blob identity

GitHub's `sha` field for the file is treated as the Git blob object identity for the current SHA-1 repository object format used by this Phase 4 v1 contract.

OpsLens recomputes the expected Git blob SHA as:

```text
SHA1(b"blob " + decimal_byte_length + b"\0" + content_bytes)
```

The source `sha` must be a full lowercase 40-hex value and must exactly match the recomputed value.

This is separate from the OpsLens content digest.

### OpsLens content digest

OpsLens computes:

```text
sha256(content_bytes)
```

The SHA-256 digest is preserved as deterministic content evidence and does not replace the Git blob identity.

## Source response validation

The GitHub Contents response must satisfy all of the following:

- JSON object response;
- `type == "file"`;
- `path == "uv.lock"` exactly;
- `name == "uv.lock"` exactly;
- `encoding == "base64"`;
- `content` is a non-empty Base64 string for the bounded file;
- `size` is a non-negative integer and equals the decoded byte length;
- `sha` is a full lowercase 40-hex Git blob SHA;
- decoded byte length is at most 1 MiB;
- recomputed Git blob SHA equals source `sha`.

Any mismatch fails closed.

## Unsupported behavior

This gate does not authorize:

- arbitrary repository paths;
- directory traversal or path discovery;
- recursive repository reads;
- `pyproject.toml` parsing;
- `requirements.txt` parsing;
- lockfile parsing;
- `uv lock`, `uv sync`, package installation, import, build, test, or execution against third-party content;
- dependency resolution;
- GitHub SBOM correlation;
- AWS persistence;
- model calls.

## Why `uv.lock` first

Alternatives considered:

### `pyproject.toml` first

Rejected for the first dependency-evidence slice because declared constraints do not necessarily establish one concrete installed/resolved version for deterministic vulnerability applicability.

### GitHub Dependency Graph SBOM first

Deferred because ADR 0009 already established that the repository-scoped SBOM endpoint is not the immutable snapshot authority.

### Clone the repository

Rejected. Cloning broadens acquisition surface unnecessarily and makes it easier for later code to accidentally inspect or execute more repository content than the explicit evidence contract permits.

### Execute `uv` to inspect dependencies

Rejected. Third-party repository code and packaging hooks must remain inert.

## Security properties

This decision preserves:

- exact immutable commit authority;
- one allowlisted dependency-evidence path;
- fixed GitHub API host and GET-only transport inherited from ADR 0010;
- explicit HTTP and decoded-content byte bounds;
- no redirects and no automatic retries;
- no package-manager execution;
- no arbitrary filesystem or URL input;
- independent source-object and OpsLens content hashes;
- fail-closed evidence validation.

## AWS, IAM, cost, and AIP-C01

This gate adds no AWS service, IAM permission, queue, database, Lambda, model call, or persistent runtime resource.

Incremental AWS cost: **$0**.

AIP-C01 learning value is architectural: deterministic evidence acquisition, supply-chain safety, bounded external API consumption, integrity validation, and separation of reasoning from verification.

## Exit criteria

This gate is complete when:

- `uv.lock` is the only authorized repository file path;
- file acquisition always uses the exact snapshot commit SHA;
- raw content is capped at 1 MiB;
- source `size` is checked against decoded bytes;
- Git blob SHA is independently recomputed and verified;
- SHA-256 content evidence is emitted;
- malformed Base64/type/path/name/size/blob identity fail closed;
- no parser or third-party execution is introduced;
- Repository Intelligence Ruff/Pyright/pytest gates pass;
- Phase 3 correlation regression remains green.

## Next gate

After this contract is green, Phase 4 may introduce a deterministic, bounded `uv.lock` TOML parser that consumes only `ImmutableRepositoryFileEvidence.content_bytes` and emits concrete PyPI package/version evidence for the Phase 3 correlation engine.
