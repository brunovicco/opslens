"""Materialize or verify the pinned Phase 7 canonical corpus manifest."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import Sequence, cast

from opslens.knowledge_retrieval.adapters.http_source import (
    BoundedHttpsKnowledgeSource,
    KnowledgeSourceAcquisitionError,
)
from opslens.knowledge_retrieval.application.corpus_config import (
    CorpusConfigError,
    load_corpus_spec,
    load_source_registry,
)
from opslens.knowledge_retrieval.application.corpus_manifest import (
    CorpusManifestError,
    serialize_corpus_manifest,
)
from opslens.knowledge_retrieval.application.corpus_materialization import (
    CanonicalSourceTextError,
)
from opslens.knowledge_retrieval.application.corpus_pipeline import (
    CorpusPipelineError,
    materialize_corpus,
)

_DEFAULT_REGISTRY = Path("knowledge/corpus/v1/source_registry.json")
_DEFAULT_SPEC = Path("knowledge/corpus/v1/corpus_spec.json")
_DEFAULT_MANIFEST = Path("knowledge/corpus/v1/manifest.json")


class ManifestFileError(ValueError):
    """Raised when a generated manifest cannot match the requested file operation."""


def _parser() -> argparse.ArgumentParser:
    """Build the explicit write-or-check CLI contract."""
    parser = argparse.ArgumentParser(
        description=(
            "Replay pinned official source files as inert text and produce a deterministic "
            "hash-only knowledge corpus manifest."
        )
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write",
        action="store_true",
        help="Atomically write the generated deterministic manifest.",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Require the generated manifest to exactly match the existing file.",
    )
    parser.add_argument("--registry", type=Path, default=_DEFAULT_REGISTRY)
    parser.add_argument("--spec", type=Path, default=_DEFAULT_SPEC)
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    return parser


def _write_atomic(path: Path, content: str) -> None:
    """Replace the manifest atomically without persisting third-party source text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _check_exact(path: Path, expected: str) -> None:
    """Fail closed unless the checked-in manifest exactly matches the fresh replay."""
    try:
        actual = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestFileError(f"could not read expected manifest {path}") from exc
    if actual != expected:
        raise ManifestFileError(
            "existing manifest does not exactly match the fresh pinned-source replay"
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Run one bounded serial corpus replay and write or verify only hash evidence."""
    args = _parser().parse_args(argv)
    registry_path = cast(Path, args.registry)
    spec_path = cast(Path, args.spec)
    manifest_path = cast(Path, args.manifest)
    write_mode = cast(bool, args.write)

    try:
        registry = load_source_registry(registry_path)
        spec = load_corpus_spec(spec_path)
        manifest = materialize_corpus(
            registry,
            spec,
            BoundedHttpsKnowledgeSource(),
        )
        serialized = serialize_corpus_manifest(manifest)
        if write_mode:
            _write_atomic(manifest_path, serialized)
            operation = "wrote"
        else:
            _check_exact(manifest_path, serialized)
            operation = "verified"
    except (
        CanonicalSourceTextError,
        CorpusConfigError,
        CorpusManifestError,
        CorpusPipelineError,
        KnowledgeSourceAcquisitionError,
        ManifestFileError,
        OSError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    document_count = len(manifest.documents)
    chunk_count = sum(len(document.chunks) for document in manifest.documents)
    manifest_sha256 = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    print(
        f"{operation} {manifest_path}: documents={document_count} "
        f"chunks={chunk_count} manifest_sha256={manifest_sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
