"""Tests for the Gate 7.2 materialize-or-check CLI without network access."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from opslens.knowledge_retrieval.adapters.http_source import AcquiredKnowledgeSource
from opslens.knowledge_retrieval.cli import materialize_corpus as cli_module
from opslens.knowledge_retrieval.domain import KnowledgeSourceDescriptor

_NORMALIZATION = {
    "encoding": "utf-8-strict",
    "newline": "lf",
    "unicode": "preserve",
    "bom": "reject",
    "nul": "reject",
    "selection": "exact-line-aligned-start-inclusive-end-exclusive",
    "document_join": "two-lf",
}


class _FakeAcquirer:
    """Return deterministic inert bytes for one authorized descriptor."""

    def __init__(self, body: bytes) -> None:
        self.body = body
        self.document_ids: list[str] = []

    def acquire(self, descriptor: KnowledgeSourceDescriptor) -> AcquiredKnowledgeSource:
        """Record serial acquisition order and wrap the configured source bytes."""
        self.document_ids.append(descriptor.document_id)
        return AcquiredKnowledgeSource.from_body(
            descriptor=descriptor,
            body=self.body,
            content_type="text/plain; charset=utf-8",
        )


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Write one minimal valid registry/spec pair for CLI tests."""
    registry_path = tmp_path / "source_registry.json"
    spec_path = tmp_path / "corpus_spec.json"
    manifest_path = tmp_path / "manifest.json"
    registry = {
        "registry_id": "knowledge-source-registry:v1",
        "purpose": "CLI test registry",
        "authority_boundary": "explanatory/remediation only",
        "acquisition_status": "not_started",
        "entries": [
            {
                "document_id": "knowledge-doc:test:v1",
                "source_id": "example:test",
                "source_type": "maintainer_documentation",
                "canonical_uri": "https://example.com/guide/",
                "upstream_repository": "example/docs",
                "upstream_commit_sha": "a" * 40,
                "upstream_path": "guide.md",
                "expected_chunk_ids": ["knowledge-chunk:test:first:v1"],
            }
        ],
    }
    spec = {
        "spec_id": "knowledge-corpus-spec:v1",
        "source_registry_id": "knowledge-source-registry:v1",
        "normalization": _NORMALIZATION,
        "documents": [
            {
                "document_id": "knowledge-doc:test:v1",
                "title": "Test Guide",
                "selections": [
                    {
                        "chunk_id": "knowledge-chunk:test:first:v1",
                        "section_path": ["Guide", "First"],
                        "start_marker": "## First",
                        "end_marker": "## End",
                    }
                ],
            }
        ],
    }
    registry_path.write_text(
        json.dumps(registry, indent=2) + "\n",
        encoding="utf-8",
    )
    spec_path.write_text(
        json.dumps(spec, indent=2) + "\n",
        encoding="utf-8",
    )
    return registry_path, spec_path, manifest_path


def _args(mode: str, registry: Path, spec: Path, manifest: Path) -> list[str]:
    """Build one explicit CLI argument vector."""
    return [
        mode,
        "--registry",
        str(registry),
        "--spec",
        str(spec),
        "--manifest",
        str(manifest),
    ]


def test_cli_write_then_check_is_deterministic_and_text_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Write/check succeeds without persisting source or chunk text in the manifest."""
    registry, spec, manifest = _write_inputs(tmp_path)
    acquirer = _FakeAcquirer(b"# Guide\n\n## First\nalpha\n\n## End\nignored\n")
    monkeypatch.setattr(cli_module, "BoundedHttpsKnowledgeSource", lambda: acquirer)

    assert cli_module.main(_args("--write", registry, spec, manifest)) == 0
    first_bytes = manifest.read_bytes()
    assert b"alpha" not in first_bytes
    assert b"ignored" not in first_bytes
    assert acquirer.document_ids == ["knowledge-doc:test:v1"]

    acquirer.document_ids.clear()
    assert cli_module.main(_args("--check", registry, spec, manifest)) == 0
    assert manifest.read_bytes() == first_bytes
    assert acquirer.document_ids == ["knowledge-doc:test:v1"]

    output = capsys.readouterr().out
    assert "documents=1 chunks=1 manifest_sha256=" in output


def test_cli_check_fails_closed_on_replayed_content_drift_without_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Fresh source drift returns non-zero and preserves the previously recorded manifest."""
    registry, spec, manifest = _write_inputs(tmp_path)
    initial = _FakeAcquirer(b"## First\nalpha\n## End\n")
    monkeypatch.setattr(cli_module, "BoundedHttpsKnowledgeSource", lambda: initial)
    assert cli_module.main(_args("--write", registry, spec, manifest)) == 0
    recorded = manifest.read_bytes()

    drifted = _FakeAcquirer(b"## First\nalpha changed\n## End\n")
    monkeypatch.setattr(cli_module, "BoundedHttpsKnowledgeSource", lambda: drifted)
    assert cli_module.main(_args("--check", registry, spec, manifest)) == 1
    assert manifest.read_bytes() == recorded
    assert "does not exactly match" in capsys.readouterr().err
