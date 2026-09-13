#!/usr/bin/env python3
"""Run the deterministic dependency identity layer over this repository's own lock.

OpsLens reads a public repository's `uv.lock`, parses it without executing
anything, and derives content-addressed PyPI identity from it. This points that
same code at the checkout it is running from, so the identity layer is exercised
on a real lock rather than only on fixtures.

```text
READ, NEVER EXECUTE third-party repository code.
```

**This is dependency identity, not a vulnerability claim.** Correlating these
packages against GHSA, NVD, KEV and EPSS needs a request-time threat evidence
authority, whose only V1 implementation is fixture-backed. Standard SCA runs
separately in the supply-chain workflow and reports that half. What this proves
is narrower and worth stating plainly: given this repository's own locked
dependencies, the deterministic layer produces one stable identity, offline,
with no model and no network.

Git supplies the immutable coordinates the domain requires — commit, tree and
the blob sha of `uv.lock` — so the evidence is bound to an exact checkout.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final, cast

from _bootstrap import ensure_repository_src_on_path

ensure_repository_src_on_path()

from opslens.repository_intelligence.application.pypi_normalization import (  # noqa: E402
    normalize_uv_lock_pypi_dependencies,
)
from opslens.repository_intelligence.domain.file_evidence import (  # noqa: E402
    UV_LOCK_PATH,
    ImmutableRepositoryFileEvidence,
)
from opslens.repository_intelligence.domain.models import (  # noqa: E402
    GitHubRepositoryIdentity,
    ImmutableRepositorySnapshot,
)
from opslens.repository_intelligence.domain.pypi_normalization import (  # noqa: E402
    RepositoryPyPINormalizationInventory,
)
from opslens.repository_intelligence.parsers.uv_lock import (  # noqa: E402
    parse_uv_lock_evidence,
)
from opslens.shared.evidence import canonical_json, canonical_sha256  # noqa: E402

SELF_DEPENDENCY_CONTRACT_VERSION: Final = "opslens-self-dependency-evidence:v1"

_REPOSITORY_FULL_NAME: Final = "brunovicco/opslens"
_REPOSITORY_ID: Final = 1_010_101
"""Placeholder identity. This runs from a checkout and never calls the GitHub API,
so no real numeric repository id is available or needed; the evidence is bound by
commit and blob sha, not by this number."""


class SelfDependencyEvidenceError(RuntimeError):
    """Raised when this repository's own dependency identity cannot be derived."""


def _git(repository_root: Path, *arguments: str) -> str:
    """Return the stripped stdout of one git command, failing closed."""
    process = subprocess.run(
        ["git", *arguments],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        joined = " ".join(arguments)
        raise SelfDependencyEvidenceError(
            f"git {joined} failed\nstderr:\n{process.stderr.strip()}"
        )
    return process.stdout.strip()


def build_self_file_evidence(repository_root: Path) -> ImmutableRepositoryFileEvidence:
    """Bind this checkout's `uv.lock` to its immutable git coordinates.

    Args:
        repository_root: The repository checkout to read.

    Returns:
        Immutable file evidence for `uv.lock` at the current commit.

    Raises:
        SelfDependencyEvidenceError: If git coordinates are unavailable, or the
            working tree copy of the lock differs from the committed blob.
    """
    lock_path = repository_root / UV_LOCK_PATH
    if not lock_path.is_file():
        raise SelfDependencyEvidenceError(f"missing {UV_LOCK_PATH} at {lock_path}")

    commit_sha = _git(repository_root, "rev-parse", "HEAD")
    tree_sha = _git(repository_root, "rev-parse", "HEAD^{tree}")
    blob_sha = _git(repository_root, "rev-parse", f"HEAD:{UV_LOCK_PATH}")

    content_bytes = lock_path.read_bytes()
    committed = subprocess.run(
        ["git", "cat-file", "blob", blob_sha],
        cwd=repository_root,
        check=False,
        capture_output=True,
    )
    if committed.returncode != 0 or committed.stdout != content_bytes:
        raise SelfDependencyEvidenceError(
            f"the working tree {UV_LOCK_PATH} differs from the committed blob; "
            "commit or stash it before deriving evidence"
        )

    snapshot = ImmutableRepositorySnapshot(
        repository=GitHubRepositoryIdentity(
            repository_id=_REPOSITORY_ID,
            owner=_REPOSITORY_FULL_NAME.split("/")[0],
            name=_REPOSITORY_FULL_NAME.split("/")[1],
            full_name=_REPOSITORY_FULL_NAME,
            is_private=False,
        ),
        requested_ref=commit_sha,
        commit_sha=commit_sha,
        tree_sha=tree_sha,
    )
    return ImmutableRepositoryFileEvidence(
        snapshot=snapshot,
        path=UV_LOCK_PATH,
        blob_sha=blob_sha,
        size_bytes=len(content_bytes),
        content_sha256=hashlib.sha256(content_bytes).hexdigest(),
        content_bytes=content_bytes,
    )


def build_self_dependency_payload(
    inventory: RepositoryPyPINormalizationInventory,
) -> dict[str, object]:
    """Project the normalization inventory as a content-addressable payload.

    Args:
        inventory: The normalized PyPI inventory for this repository's lock.

    Returns:
        A JSON-ready payload carrying identity, counts and normalized packages.
    """
    parsed = inventory.parsed_lock
    evidence = parsed.file_evidence
    snapshot = evidence.snapshot
    return {
        "contract_version": SELF_DEPENDENCY_CONTRACT_VERSION,
        "authority": {
            "model_execution": False,
            "network_access": False,
            "repository_code_execution": False,
            "vulnerability_correlation": False,
        },
        "repository": {
            "full_name": snapshot.repository.full_name,
            "commit_sha": snapshot.commit_sha,
            "tree_sha": snapshot.tree_sha,
        },
        "lock": {
            "path": evidence.path,
            "blob_sha": evidence.blob_sha,
            "content_sha256": evidence.content_sha256,
            "size_bytes": evidence.size_bytes,
            "revision": parsed.revision,
            "requires_python": parsed.requires_python,
        },
        "accounting": {
            "package_count": parsed.package_count,
            "pypi_source_record_count": inventory.pypi_source_record_count,
            "normalized_dependency_count": len(inventory.normalized_dependencies),
            "unsupported_package_count": len(parsed.unsupported_packages),
            "unsupported_normalization_count": len(inventory.unsupported_normalization),
        },
        "normalized_dependencies": [
            {
                "name": dependency.package.canonical,
                "version": dependency.version.canonical,
                "purl": dependency.purl,
            }
            for dependency in inventory.normalized_dependencies
        ],
        "unsupported_packages": [
            {
                "name_original": package.name_original,
                "source_kind": package.source_kind,
                "reason_code": package.reason_code,
            }
            for package in parsed.unsupported_packages
        ],
    }


def derive_self_dependency_evidence(repository_root: Path) -> dict[str, object]:
    """Derive this repository's own deterministic dependency identity.

    Args:
        repository_root: The repository checkout to read.

    Returns:
        The payload with its own evidence identity attached.

    Raises:
        SelfDependencyEvidenceError: If the lock cannot be bound or parsed.
    """
    file_evidence = build_self_file_evidence(repository_root)
    inventory = normalize_uv_lock_pypi_dependencies(parse_uv_lock_evidence(file_evidence))
    payload = build_self_dependency_payload(inventory)
    payload["evidence_id"] = (
        f"{SELF_DEPENDENCY_CONTRACT_VERSION}@sha256:{canonical_sha256(payload)}"
    )
    return payload


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Derive deterministic PyPI dependency identity for this repository's own "
            "uv.lock. This is identity, not a vulnerability claim."
        ),
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="reviewer output projection",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="write the canonical JSON evidence to this path as well",
    )
    return parser


def render_text(payload: dict[str, object]) -> str:
    """Render one reviewer-facing summary of the derived evidence."""
    repository = cast(dict[str, object], payload["repository"])
    lock = cast(dict[str, object], payload["lock"])
    accounting = cast(dict[str, object], payload["accounting"])
    return "\n".join(
        (
            "OpsLens deterministic dependency identity over its own lock",
            f"repository: {repository['full_name']}",
            f"commit: {repository['commit_sha']}",
            f"lock: {lock['path']}@{lock['blob_sha']}",
            f"lock sha256: {lock['content_sha256']}",
            f"locked packages: {accounting['package_count']}",
            f"normalized PyPI dependencies: {accounting['normalized_dependency_count']}",
            f"unsupported packages: {accounting['unsupported_package_count']}",
            f"evidence: {payload['evidence_id']}",
            "authority: deterministic identity only; no model, network or correlation",
            "scope: dependency identity != vulnerability finding",
        )
    ) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Derive and render this repository's own dependency identity."""
    namespace = _parser().parse_args(list(argv) if argv is not None else None)
    repository_root = Path(__file__).resolve().parents[1]
    try:
        payload = derive_self_dependency_evidence(repository_root)
    except SelfDependencyEvidenceError as exc:
        print(f"self dependency evidence rejected: {exc}", file=sys.stderr)
        return 2

    output_path = cast(Path | None, namespace.output)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(canonical_json(payload) + b"\n")

    if cast(str, namespace.output_format) == "json":
        sys.stdout.write(json.dumps(json.loads(canonical_json(payload)), indent=2, sort_keys=True))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
