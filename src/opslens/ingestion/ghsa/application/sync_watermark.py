"""Where the GHSA corpus has actually been observed through.

The planner decides what window to run next; this is the thing it reads. One value, one
object, advanced only by a window that completed — which is what makes a missed or failed
run cost nothing but time.

It is deliberately simpler than the NVD watermark, and the reason is a property of the
source rather than a shortcut. NVD has two interfaces with a boundary between them — a
yearly feed bootstrap and an incremental API — so its watermark has to record which one
committed a value and refuse to mix their semantics. GHSA has one interface and one window
type, so the only question is whether a value came from a completed window or from a seed.

```text
one source interface != one source
```

**A committed watermark cannot claim more than its window covered.** The invariant is
checked rather than trusted: if the basis is a window, `observed_through_at` must equal
that window's `end_at` exactly. A watermark that advanced past what was read is the
failure this whole pattern exists to prevent, and it would be invisible — the corpus would
simply be missing whatever fell in the gap, with nothing anywhere recording that a gap
occurred.

```text
a window attempted != a window observed
advanced != observed
```

**A seed is marked as a seed.** The first value cannot come from a window, because no
window has run. Recording it as a seed keeps "we read up to here" and "someone asserted we
had read up to here" from being the same claim, which matters the first time anyone asks
why the corpus starts where it does.

```text
asserted boundary != observed boundary
```
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar, Final, cast

from opslens.ingestion.ghsa.domain.sync import GhsaSyncMode, GhsaSyncWindow

GHSA_SYNC_WATERMARK_CONTRACT_VERSION: Final = "opslens-ghsa-sync-watermark:v1"

_TIMESTAMP_FORMAT: Final = "%Y-%m-%dT%H:%M:%SZ"


class InvalidGhsaSyncWatermarkError(ValueError):
    """Raised when a watermark could not describe a real observation boundary."""


def _require_instant(value: object, *, field: str) -> datetime:
    """Normalize one aware instant to UTC at second precision.

    Args:
        value: The candidate instant.
        field: The field name, for the message.

    Returns:
        The normalized instant.

    Raises:
        InvalidGhsaSyncWatermarkError: If it is not an aware instant, or carries
            sub-second precision the window contract cannot express.
    """
    if type(value) is not datetime or value.tzinfo is None:
        raise InvalidGhsaSyncWatermarkError(f"{field} must be one timezone-aware instant")
    normalized = value.astimezone(UTC)
    if normalized.microsecond:
        raise InvalidGhsaSyncWatermarkError(
            f"{field} carries sub-second precision the sync window cannot express"
        )
    return normalized


@dataclass(frozen=True, slots=True)
class GhsaWatermarkSeed:
    """The first boundary, asserted by an operator because no window has run.

    Attributes:
        note: Why this boundary was chosen, in the operator's words.
    """

    note: str

    def __post_init__(self) -> None:
        """Reject a seed that explains nothing.

        Raises:
            InvalidGhsaSyncWatermarkError: If the note is empty or padded.
        """
        if type(self.note) is not str or not self.note or self.note.strip() != self.note:
            raise InvalidGhsaSyncWatermarkError(
                "a seeded watermark must record why its boundary was chosen"
            )


@dataclass(frozen=True, slots=True)
class GhsaWatermarkCommittedWindow:
    """The boundary a completed window established.

    Attributes:
        window: The window that completed.
    """

    window: GhsaSyncWindow

    def __post_init__(self) -> None:
        """Reject a basis that is not a window.

        Raises:
            InvalidGhsaSyncWatermarkError: If the window is not typed.
        """
        if type(self.window) is not GhsaSyncWindow:
            raise InvalidGhsaSyncWatermarkError(
                "a committed watermark basis must be one typed sync window"
            )


type GhsaWatermarkBasis = GhsaWatermarkSeed | GhsaWatermarkCommittedWindow


@dataclass(frozen=True, slots=True)
class GhsaSyncWatermarkV1:
    """The single authoritative GHSA observation boundary.

    Attributes:
        observed_through_at: Every advisory modified at or before this instant has been
            observed.
        basis: What established that boundary.
    """

    WATERMARK_VERSION: ClassVar[str] = "1"
    SOURCE: ClassVar[str] = "github-security-advisories"
    SOURCE_INTERFACE: ClassVar[str] = "advisories-rest"

    observed_through_at: datetime
    basis: GhsaWatermarkBasis

    def __post_init__(self) -> None:
        """Reject a watermark claiming more than its basis supports.

        Raises:
            InvalidGhsaSyncWatermarkError: If the boundary is malformed, or if a
                committed window does not end exactly at the boundary it established.
        """
        object.__setattr__(
            self,
            "observed_through_at",
            _require_instant(self.observed_through_at, field="observed_through_at"),
        )

        if type(self.basis) not in {GhsaWatermarkSeed, GhsaWatermarkCommittedWindow}:
            raise InvalidGhsaSyncWatermarkError(
                "a watermark must record whether it was seeded or committed by a window"
            )

        if (
            isinstance(self.basis, GhsaWatermarkCommittedWindow)
            and self.basis.window.end_at != self.observed_through_at
        ):
            raise InvalidGhsaSyncWatermarkError(
                "a committed watermark must stand exactly where its window ended; "
                "advancing past what was read loses whatever fell in the gap"
            )

    @property
    def seeded(self) -> bool:
        """Return whether this boundary was asserted rather than observed."""
        return isinstance(self.basis, GhsaWatermarkSeed)

    @property
    def payload(self) -> dict[str, object]:
        """Project the retained document."""
        document: dict[str, object] = {
            "contract_version": GHSA_SYNC_WATERMARK_CONTRACT_VERSION,
            "observed_through_at": self.observed_through_at.strftime(_TIMESTAMP_FORMAT),
            "source": self.SOURCE,
            "source_interface": self.SOURCE_INTERFACE,
            "watermark_version": self.WATERMARK_VERSION,
        }
        if isinstance(self.basis, GhsaWatermarkSeed):
            document["basis"] = {"kind": "seed", "note": self.basis.note}
        else:
            window = self.basis.window
            document["basis"] = {
                "kind": "committed_window",
                "mode": window.mode.value,
                "start_at": window.start_at.strftime(_TIMESTAMP_FORMAT),
                "end_at": window.end_at.strftime(_TIMESTAMP_FORMAT),
            }
        return document


def serialize_watermark(watermark: GhsaSyncWatermarkV1) -> bytes:
    """Render one watermark as the exact bytes retained.

    Args:
        watermark: The watermark to render.

    Returns:
        UTF-8 JSON with sorted keys and compact separators.
    """
    return json.dumps(
        watermark.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def parse_watermark(payload: bytes) -> GhsaSyncWatermarkV1:
    """Read one retained watermark back.

    Args:
        payload: The retained bytes.

    Returns:
        The watermark.

    Raises:
        InvalidGhsaSyncWatermarkError: If the document is malformed, of another contract,
            or describes a boundary its basis does not support.
    """
    try:
        parsed = cast(object, json.loads(payload.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidGhsaSyncWatermarkError(
            "a retained watermark must be valid UTF-8 JSON"
        ) from exc
    if not isinstance(parsed, dict):
        raise InvalidGhsaSyncWatermarkError("a retained watermark must be a JSON object")
    document = cast(Mapping[str, object], parsed)

    if document.get("contract_version") != GHSA_SYNC_WATERMARK_CONTRACT_VERSION:
        raise InvalidGhsaSyncWatermarkError(
            "a retained watermark from another contract version cannot be read as this one"
        )

    observed = _parse_instant(document.get("observed_through_at"), field="observed_through_at")

    raw_basis = document.get("basis")
    if not isinstance(raw_basis, dict):
        raise InvalidGhsaSyncWatermarkError("a retained watermark must record its basis")
    basis_document = cast(Mapping[str, object], raw_basis)

    kind = basis_document.get("kind")
    if kind == "seed":
        note = basis_document.get("note")
        if not isinstance(note, str):
            raise InvalidGhsaSyncWatermarkError("a seeded watermark must record its note")
        basis: GhsaWatermarkBasis = GhsaWatermarkSeed(note=note)
    elif kind == "committed_window":
        mode_value = basis_document.get("mode")
        if not isinstance(mode_value, str):
            raise InvalidGhsaSyncWatermarkError("a committed watermark must record its mode")
        try:
            mode = GhsaSyncMode(mode_value)
        except ValueError as exc:
            raise InvalidGhsaSyncWatermarkError(
                f"{mode_value!r} is not a GHSA sync mode"
            ) from exc
        basis = GhsaWatermarkCommittedWindow(
            window=GhsaSyncWindow(
                mode=mode,
                start_at=_parse_instant(basis_document.get("start_at"), field="start_at"),
                end_at=_parse_instant(basis_document.get("end_at"), field="end_at"),
            )
        )
    else:
        raise InvalidGhsaSyncWatermarkError(
            "a retained watermark basis must be a seed or a committed window"
        )

    return GhsaSyncWatermarkV1(observed_through_at=observed, basis=basis)


def _parse_instant(value: object, *, field: str) -> datetime:
    """Read one retained instant in the watermark's single form.

    Args:
        value: The retained value.
        field: The field name, for the message.

    Returns:
        The instant.

    Raises:
        InvalidGhsaSyncWatermarkError: If it is not that form.
    """
    if not isinstance(value, str):
        raise InvalidGhsaSyncWatermarkError(f"{field} must be a retained instant")
    try:
        return datetime.strptime(value, _TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    except ValueError as exc:
        raise InvalidGhsaSyncWatermarkError(
            f"{field} must use {_TIMESTAMP_FORMAT}"
        ) from exc


__all__ = [
    "GHSA_SYNC_WATERMARK_CONTRACT_VERSION",
    "GhsaSyncWatermarkV1",
    "GhsaWatermarkBasis",
    "GhsaWatermarkCommittedWindow",
    "GhsaWatermarkSeed",
    "InvalidGhsaSyncWatermarkError",
    "parse_watermark",
    "serialize_watermark",
]
