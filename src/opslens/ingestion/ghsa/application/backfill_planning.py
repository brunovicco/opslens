"""Plan a bounded GHSA corpus backfill and render the envelopes the lambdas accept.

This is contract logic, not orchestration, so it lives in the package where it can be
tested rather than in the operator script that composes it.

Two subtleties make it worth its own module.

The domain carries **two deliberate serializations** of the same instant, and they are
not interchangeable. `GhsaSyncWindow.canonical_*_at` is the frozen source-query form
used to hash `sync_id`, and renders `+00:00`; the invocation parser requires the `Z`
form and rejects anything else. Sending the hashing form over the wire is a mistake
this module exists to make impossible.

`GhsaSyncWindow.filter_expression` is a **closed** GitHub search range, so abutting
windows would both claim an advisory published exactly on the boundary second. The
domain works at second precision, so a disjoint cover is cut one second apart.

And the two lambdas do not agree on the type of `schema_version`: Bronze requires the
integer `1`, Silver the string `"1"`. Each envelope builder matches the parser it is
sent to, and the tests assert both against those parsers rather than against a shape
written down twice.

```text
hashing serialization != wire serialization
closed range != half-open range
Bronze envelope != Silver envelope
```
"""

import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Final, Protocol, cast

from opslens.ingestion.ghsa.domain.sync import GhsaSyncMode, GhsaSyncWindow

# The two lambdas disagree about the type of this field, and that is not a typo here.
# The Bronze parser requires the integer 1; the Silver parser requires the string "1"
# and rejects anything that is not a non-empty string. Each constant matches the parser
# it is sent to, and the round-trip tests assert both against those parsers directly.
BRONZE_INVOCATION_SCHEMA_VERSION: Final = 1
SILVER_INVOCATION_SCHEMA_VERSION: Final = "1"
# One day under the domain's own 31-day ceiling, so no window can be rejected by
# rounding at a month boundary.
WINDOW_DAYS: Final = 30

# A Silver invocation for a dense window keeps the function busy for ten minutes or
# more while the HTTP connection carries no bytes, and the connection does not always
# survive that. Measured against the live function: the platform report said
# durationMs 630754 and status success while the client raised a read timeout on the
# same call. Raising the client timeout cannot fix a connection that dies mid-wait.
#
#     no response != no result
#
# Both objects below are content-addressed on the same pair, so the Silver coordinate
# is derivable from the Bronze one, and the COMPLETE manifest — not the response — is
# what says whether a window happened.
_BRONZE_MANIFEST_PREFIX: Final = "bronze/ghsa/advisories/mode="
_SILVER_COMPLETION_TEMPLATE: Final = (
    "silver/ghsa/completions/schema_version=1/sync_id={sync_id}"
    "/attempt_id={attempt_id}/manifest.json"
)


class BackfillPlanError(ValueError):
    """Raised when a requested backfill range cannot produce valid windows."""


def invocation_timestamp(value: datetime) -> str:
    """Render one timestamp in the form the invocation envelope requires.

    Args:
        value: A timezone-aware timestamp.

    Returns:
        The `YYYY-MM-DDTHH:MM:SSZ` text the lambdas accept.

    Raises:
        BackfillPlanError: If the timestamp is naive, since a local time would silently
            shift the window.
    """
    if value.tzinfo is None:
        raise BackfillPlanError("backfill timestamps must be timezone aware")
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def plan_sync_windows(
    start: datetime,
    end: datetime,
    mode: GhsaSyncMode,
) -> tuple[GhsaSyncWindow, ...]:
    """Cut a date range into a disjoint cover of windows the domain accepts.

    Args:
        start: Inclusive start.
        end: Exclusive end of the overall range.
        mode: Synchronization mode the lambda filters by.

    Returns:
        Windows covering the range, oldest first, none sharing a boundary second.

    Raises:
        BackfillPlanError: If either bound is naive or the range does not move forward.
    """
    if start.tzinfo is None or end.tzinfo is None:
        raise BackfillPlanError("backfill range bounds must be timezone aware")
    if end <= start:
        raise BackfillPlanError("the backfill range must end after it starts")

    windows: list[GhsaSyncWindow] = []
    cursor = start.astimezone(UTC)
    limit = end.astimezone(UTC)
    while cursor < limit:
        boundary = min(cursor + timedelta(days=WINDOW_DAYS), limit)
        windows.append(GhsaSyncWindow(mode=mode, start_at=cursor, end_at=boundary))
        cursor = boundary + timedelta(seconds=1)
    return tuple(windows)


def build_bronze_invocation(window: GhsaSyncWindow) -> Mapping[str, object]:
    """Render the Bronze envelope for one window.

    Args:
        window: The window to request.

    Returns:
        The exact envelope `GhsaBronzeInvocationParserV1` accepts.
    """
    return {
        "schema_version": BRONZE_INVOCATION_SCHEMA_VERSION,
        "mode": window.mode.value,
        "start_at": invocation_timestamp(window.start_at),
        "end_at": invocation_timestamp(window.end_at),
    }


def build_silver_invocation(manifest_key: str, manifest_version_id: str) -> Mapping[str, object]:
    """Render the Silver envelope for one Bronze leaf manifest.

    Args:
        manifest_key: The Bronze manifest object key.
        manifest_version_id: That object's exact S3 version id.

    Returns:
        The exact envelope `GhsaSilverInvocationParserV1` accepts.

    Raises:
        BackfillPlanError: If either coordinate is blank, since Silver requires an
            exact manifest rather than a prefix.
    """
    if not manifest_key or not manifest_version_id:
        raise BackfillPlanError("Silver promotion requires an exact manifest coordinate")
    return {
        "schema_version": SILVER_INVOCATION_SCHEMA_VERSION,
        "manifest_key": manifest_key,
        "manifest_version_id": manifest_version_id,
    }


__all__ = [
    "BRONZE_INVOCATION_SCHEMA_VERSION",
    "SILVER_INVOCATION_SCHEMA_VERSION",
    "WINDOW_DAYS",
    "BackfillPlanError",
    "build_bronze_invocation",
    "build_silver_invocation",
    "invocation_timestamp",
    "plan_sync_windows",
]


class SilverCompletionStore(Protocol):
    """Only the read needed to settle a Silver invocation that never answered."""

    def get_object(self, *, Bucket: str, Key: str) -> Mapping[str, object]:
        """Read one exact object."""
        ...


class _ObjectBody(Protocol):
    """The streaming body an object read carries."""

    def read(self) -> bytes:
        """Read the whole body."""
        ...


def silver_completion_key(bronze_manifest_key: str) -> str:
    """Derive the Silver COMPLETE key that answers one Bronze leaf.

    Args:
        bronze_manifest_key: The exact Bronze leaf manifest key.

    Returns:
        The Silver completion manifest key for that leaf.

    Raises:
        BackfillPlanError: If the key is not a GHSA Bronze manifest key, or carries no
            complete coordinate.
    """
    if not bronze_manifest_key.startswith(_BRONZE_MANIFEST_PREFIX):
        raise BackfillPlanError(f"unrecognized Bronze manifest key: {bronze_manifest_key}")

    parts = {
        segment.split("=", 1)[0]: segment.split("=", 1)[1]
        for segment in bronze_manifest_key.split("/")
        if "=" in segment
    }
    sync_id = parts.get("sync_id")
    attempt_id = parts.get("attempt_id")
    if not sync_id or not attempt_id:
        raise BackfillPlanError(
            f"Bronze manifest key carries no coordinate: {bronze_manifest_key}"
        )

    return _SILVER_COMPLETION_TEMPLATE.format(sync_id=sync_id, attempt_id=attempt_id)


def read_silver_completion(
    store: SilverCompletionStore, *, bucket: str, key: str
) -> Mapping[str, object] | None:
    """Read one Silver COMPLETE manifest, treating every absence as not yet written.

    Args:
        store: The object store.
        bucket: The bucket holding Silver evidence.
        key: The exact completion manifest key.

    Returns:
        The manifest, or None when it is missing, unreadable or not a JSON object.
    """
    try:
        response = store.get_object(Bucket=bucket, Key=key)
    except Exception:
        return None

    body = response.get("Body")
    if body is None:
        return None
    try:
        raw = cast(_ObjectBody, body).read()
        decoded = cast(object, json.loads(raw.decode("utf-8")))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError, OSError):
        return None
    return cast(Mapping[str, object], decoded) if isinstance(decoded, dict) else None


def completion_settles_window(manifest: Mapping[str, object] | None) -> bool:
    """Decide whether a manifest closes a window.

    Only a manifest that says complete counts. A partial, malformed or absent object
    leaves the window unrecorded, because a ledger that over-records is worse than one
    that under-records: the first skips work that never happened, while the second
    repeats work that is idempotent anyway.

    Args:
        manifest: The manifest read back, if any.

    Returns:
        Whether the window may be recorded as done.
    """
    return manifest is not None and manifest.get("completion_status") == "complete"
