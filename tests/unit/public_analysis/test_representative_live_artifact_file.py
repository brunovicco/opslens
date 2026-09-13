"""Tests for atomic no-overwrite persistence of admitted Gate 19.2 evidence."""

from pathlib import Path

import pytest

from opslens.public_analysis.adapters.representative_live_artifact_file import (
    RepresentativeLiveArtifactFileError,
    write_new_representative_live_artifact,
)


def test_writes_complete_artifact_once_without_temporary_file(tmp_path: Path) -> None:
    """Publish complete admitted bytes and remove the staging inode name."""
    target = tmp_path / "measurement.json"
    payload = b'{"artifact_type":"test"}\n'

    write_new_representative_live_artifact(target, payload)

    assert target.read_bytes() == payload
    assert tuple(tmp_path.glob(".measurement.json.*.tmp")) == ()


def test_refuses_to_overwrite_existing_evidence(tmp_path: Path) -> None:
    """Preserve the first artifact exactly when a second publication is attempted."""
    target = tmp_path / "measurement.json"
    original = b'{"artifact_type":"first"}\n'
    target.write_bytes(original)

    with pytest.raises(RepresentativeLiveArtifactFileError, match="refusing to overwrite"):
        write_new_representative_live_artifact(
            target,
            b'{"artifact_type":"second"}\n',
        )

    assert target.read_bytes() == original
