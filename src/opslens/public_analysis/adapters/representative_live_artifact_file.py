"""Persist one already-admitted Gate 19.2 artifact without overwriting evidence."""

from __future__ import annotations

import os
from pathlib import Path


class RepresentativeLiveArtifactFileError(RuntimeError):
    """Reject unsafe, partial, or overwriting artifact publication attempts."""


def write_new_representative_live_artifact(path: Path, payload: bytes) -> None:
    """Publish complete bytes atomically through a same-directory hard-link commit.

    The temporary inode is fully written and fsynced before the final path is linked.
    ``os.link`` provides create-without-replace semantics, so an existing or concurrently
    created evidence artifact is never overwritten.
    """
    if type(path) is not Path:
        raise TypeError("path must be pathlib.Path")
    if type(payload) is not bytes or not payload:
        raise RepresentativeLiveArtifactFileError(
            "artifact payload must be non-empty admitted bytes"
        )
    if not path.parent.is_dir():
        raise RepresentativeLiveArtifactFileError(
            "artifact parent directory must already exist"
        )
    if path.exists():
        raise RepresentativeLiveArtifactFileError(
            "artifact already exists; refusing to overwrite evidence"
        )

    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise RepresentativeLiveArtifactFileError(
                "artifact appeared concurrently; refusing to overwrite evidence"
            ) from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


__all__ = [
    "RepresentativeLiveArtifactFileError",
    "write_new_representative_live_artifact",
]
