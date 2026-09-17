"""What a schedule may send, which is one instant and nothing else.

The Bronze v1 contract takes an explicit closed window, and that is right for a backfill:
an operator replaying 2017 says so in the request, and the request is auditable on its
own. A schedule cannot do that. It fires, and the window it should cover depends on where
the last complete window ended, which the schedule does not know.

Two ways to bridge that, and only one of them is safe.

The tempting one is a relative window — "the last 48 hours" — computed from the runtime's
own clock. It needs no state and it loses advisories the first time a run is missed,
silently, because the interval the missed run would have covered is simply never asked
for.

```text
a relative window != a resumable window
```

So the schedule sends the instant it fired, and the run reads its own watermark for the
other edge. A missed firing costs the next run a longer window, not the corpus a gap.

The event is therefore one field plus a version, and unknown fields are refused rather
than ignored. A schedule that starts sending something this contract does not understand
is a schedule whose intent has changed, and accepting the parts that parse would run the
old behaviour under a new name.

```text
an ignored field != an absent field
```
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import ClassVar, Final

_TIMESTAMP_FORMATS: Final = (
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%fZ",
)


class InvalidGhsaIncrementalInvocationError(ValueError):
    """Raised when a scheduled invocation does not match the v1 contract exactly."""


class GhsaIncrementalInvocationParserV1:
    """Parse one scheduled GHSA synchronization request."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    REQUIRED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"schema_version", "target_end_at"}
    )

    def parse(self, event: Mapping[str, object]) -> datetime:
        """Return the instant the schedule fired.

        Args:
            event: The scheduler's payload.

        Returns:
            The target edge, normalized to UTC at second precision.

        Raises:
            InvalidGhsaIncrementalInvocationError: If the event is not exactly this
                contract.
        """
        fields = set(event)
        missing = self.REQUIRED_FIELDS - fields
        unknown = fields - self.REQUIRED_FIELDS

        if missing:
            formatted = ", ".join(sorted(missing))
            raise InvalidGhsaIncrementalInvocationError(
                f"GHSA scheduled invocation is missing required fields: {formatted}."
            )
        if unknown:
            formatted = ", ".join(sorted(unknown))
            raise InvalidGhsaIncrementalInvocationError(
                f"GHSA scheduled invocation contains unsupported fields: {formatted}."
            )

        schema_version = event["schema_version"]
        if schema_version != self.SCHEMA_VERSION:
            raise InvalidGhsaIncrementalInvocationError(
                f"GHSA scheduled invocation schema_version must equal "
                f"{self.SCHEMA_VERSION!r}."
            )

        return self._parse_target(event["target_end_at"])

    def _parse_target(self, value: object) -> datetime:
        """Read the fired instant.

        EventBridge Scheduler substitutes `<aws.scheduler.scheduled-time>`, and the
        format it produces is the service's to choose rather than this contract's. Both
        renderings it is known to use are accepted, and sub-second precision is truncated
        because the sync window carries seconds — truncating toward the past, so the
        target never claims an instant the schedule had not yet reached.

        ```text
        rounded forward != observed
        ```

        Args:
            value: The retained value.

        Returns:
            The instant, normalized to UTC at second precision.

        Raises:
            InvalidGhsaIncrementalInvocationError: If it is not an instant this contract
                can read.
        """
        if not isinstance(value, str):
            raise InvalidGhsaIncrementalInvocationError(
                "GHSA scheduled invocation target_end_at must be a string."
            )
        text = value.strip()
        if text.endswith("+00:00"):
            text = f"{text[: -len('+00:00')]}Z"

        for candidate in _TIMESTAMP_FORMATS:
            try:
                parsed = datetime.strptime(text, candidate).replace(tzinfo=UTC)
            except ValueError:
                continue
            return parsed.replace(microsecond=0)

        raise InvalidGhsaIncrementalInvocationError(
            "GHSA scheduled invocation target_end_at must be one UTC instant."
        )


__all__ = [
    "GhsaIncrementalInvocationParserV1",
    "InvalidGhsaIncrementalInvocationError",
]
