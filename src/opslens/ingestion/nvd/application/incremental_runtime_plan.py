"""Plan one NVD incremental runtime window from authoritative state."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from opslens.ingestion.nvd.domain.incremental import NvdIncrementalWindow


def _require_aware_datetime(
    field_name: str,
    value: object,
) -> datetime:
    """Validate and normalize one timezone-aware datetime."""
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")

    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class NvdIncrementalRuntimeRequestV1:
    """Represent caller-controlled input for one incremental runtime attempt."""

    target_end_at: datetime

    def __post_init__(self) -> None:
        """Normalize the requested target boundary to UTC."""
        object.__setattr__(
            self,
            "target_end_at",
            _require_aware_datetime(
                "NVD incremental runtime target_end_at",
                self.target_end_at,
            ),
        )


class NvdIncrementalRuntimePlanStatus(StrEnum):
    """Classify the result of authoritative window planning."""

    WINDOW_READY = "window_ready"
    NOOP_ALREADY_CURRENT = "noop_already_current"


@dataclass(frozen=True, slots=True)
class NvdIncrementalRuntimePlanV1:
    """Describe one deterministic incremental runtime decision."""

    status: NvdIncrementalRuntimePlanStatus
    committed_through_at: datetime
    requested_target_end_at: datetime
    window: NvdIncrementalWindow | None

    def __post_init__(self) -> None:
        """Enforce consistency between status and planned window."""
        committed_through_at = _require_aware_datetime(
            "NVD committed_through_at",
            self.committed_through_at,
        )
        requested_target_end_at = _require_aware_datetime(
            "NVD requested_target_end_at",
            self.requested_target_end_at,
        )

        object.__setattr__(
            self,
            "committed_through_at",
            committed_through_at,
        )
        object.__setattr__(
            self,
            "requested_target_end_at",
            requested_target_end_at,
        )

        if (
            self.status
            is NvdIncrementalRuntimePlanStatus.NOOP_ALREADY_CURRENT
        ):
            if self.window is not None:
                raise ValueError(
                    "NVD incremental NOOP plan must not contain a window."
                )

            if requested_target_end_at > committed_through_at:
                raise ValueError(
                    "NVD incremental NOOP plan requires target_end_at "
                    "not after committed_through_at."
                )

            return

        if (
            self.status
            is NvdIncrementalRuntimePlanStatus.WINDOW_READY
        ):
            if self.window is None:
                raise ValueError(
                    "NVD incremental WINDOW_READY plan requires a window."
                )

            if self.window.start_at != committed_through_at:
                raise ValueError(
                    "NVD incremental planned window must start exactly at "
                    "committed_through_at."
                )

            if self.window.end_at > requested_target_end_at:
                raise ValueError(
                    "NVD incremental planned window must not exceed "
                    "requested target_end_at."
                )

            return

        raise ValueError(
            "Unsupported NVD incremental runtime plan status."
        )


class NvdIncrementalRuntimePlannerV1:
    """Derive one bounded NVD update window from authoritative state."""

    def plan(
        self,
        *,
        committed_through_at: datetime,
        request: NvdIncrementalRuntimeRequestV1,
    ) -> NvdIncrementalRuntimePlanV1:
        """Plan at most one incremental window."""
        committed_at = _require_aware_datetime(
            "NVD committed_through_at",
            committed_through_at,
        )

        target_end_at = request.target_end_at

        if target_end_at <= committed_at:
            return NvdIncrementalRuntimePlanV1(
                status=(
                    NvdIncrementalRuntimePlanStatus.NOOP_ALREADY_CURRENT
                ),
                committed_through_at=committed_at,
                requested_target_end_at=target_end_at,
                window=None,
            )

        maximum_end_at = committed_at + NvdIncrementalWindow.MAX_SPAN
        effective_end_at = min(
            target_end_at,
            maximum_end_at,
        )

        return NvdIncrementalRuntimePlanV1(
            status=NvdIncrementalRuntimePlanStatus.WINDOW_READY,
            committed_through_at=committed_at,
            requested_target_end_at=target_end_at,
            window=NvdIncrementalWindow(
                start_at=committed_at,
                end_at=effective_end_at,
            ),
        )
