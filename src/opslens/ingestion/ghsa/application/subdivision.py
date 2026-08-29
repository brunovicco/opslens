"""Deterministic subdivision for oversized GHSA synchronization windows."""

from dataclasses import dataclass
from datetime import timedelta

from opslens.ingestion.ghsa.domain.sync import GhsaSyncWindow


class GhsaWindowCannotSubdivideError(ValueError):
    """Raised when a bounded GHSA window cannot be split without invalid children."""


@dataclass(frozen=True, slots=True)
class GhsaWindowSubdivisionPlanner:
    """Split one inclusive whole-second window into two non-overlapping children."""

    minimum_child_span_seconds: int = 1

    def __post_init__(self) -> None:
        """Validate the minimum child span."""
        if self.minimum_child_span_seconds <= 0:
            raise ValueError("GHSA subdivision minimum child span must be positive.")

    def split(self, window: GhsaSyncWindow) -> tuple[GhsaSyncWindow, GhsaSyncWindow]:
        """Split deterministically while preserving every whole-second boundary once."""
        total_seconds = int((window.end_at - window.start_at).total_seconds())
        minimum_parent_seconds = (2 * self.minimum_child_span_seconds) + 1

        if total_seconds < minimum_parent_seconds:
            raise GhsaWindowCannotSubdivideError(
                "GHSA sync window is too small for deterministic closed-range subdivision."
            )

        left_span_seconds = total_seconds // 2
        left_end = window.start_at + timedelta(seconds=left_span_seconds)
        right_start = left_end + timedelta(seconds=1)

        left = GhsaSyncWindow(
            mode=window.mode,
            start_at=window.start_at,
            end_at=left_end,
        )
        right = GhsaSyncWindow(
            mode=window.mode,
            start_at=right_start,
            end_at=window.end_at,
        )

        return left, right
