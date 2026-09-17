"""Tests for the GHSA observation boundary and the contract a schedule may send.

The watermark's one load-bearing invariant is that a committed value cannot stand past
the window that committed it. Violating it loses advisories with nothing anywhere
recording that a gap occurred — the corpus is simply missing whatever fell in it.

```text
advanced != observed
a relative window != a resumable window
an ignored field != an absent field
```
"""

from datetime import UTC, datetime, timedelta

import pytest

from opslens.ingestion.ghsa.adapters.inbound.incremental_invocation import (
    GhsaIncrementalInvocationParserV1,
    InvalidGhsaIncrementalInvocationError,
)
from opslens.ingestion.ghsa.application.sync_watermark import (
    GHSA_SYNC_WATERMARK_CONTRACT_VERSION,
    GhsaSyncWatermarkV1,
    GhsaWatermarkCommittedWindow,
    GhsaWatermarkSeed,
    InvalidGhsaSyncWatermarkError,
    parse_watermark,
    serialize_watermark,
)
from opslens.ingestion.ghsa.domain.sync import GhsaSyncMode, GhsaSyncWindow

_MARK = datetime(2026, 9, 16, 18, 56, 22, tzinfo=UTC)


def _window(end_at: datetime = _MARK) -> GhsaSyncWindow:
    """Build one window ending where the watermark stands."""
    return GhsaSyncWindow(
        mode=GhsaSyncMode.MODIFIED, start_at=end_at - timedelta(hours=6), end_at=end_at
    )


class TestTheCommittedInvariant:
    """A watermark past its window is a gap nothing records."""

    def test_a_watermark_at_its_window_end_is_accepted(self) -> None:
        """The happy case."""
        watermark = GhsaSyncWatermarkV1(
            observed_through_at=_MARK,
            basis=GhsaWatermarkCommittedWindow(window=_window()),
        )
        assert not watermark.seeded
        assert watermark.observed_through_at == _MARK

    def test_a_watermark_past_its_window_end_is_refused(self) -> None:
        """One second past the window is one second of advisories nobody read."""
        with pytest.raises(InvalidGhsaSyncWatermarkError, match="exactly where its window"):
            GhsaSyncWatermarkV1(
                observed_through_at=_MARK + timedelta(seconds=1),
                basis=GhsaWatermarkCommittedWindow(window=_window()),
            )

    def test_a_watermark_behind_its_window_end_is_refused(self) -> None:
        """Understating is also a contradiction, and would repeat work forever."""
        with pytest.raises(InvalidGhsaSyncWatermarkError, match="exactly where its window"):
            GhsaSyncWatermarkV1(
                observed_through_at=_MARK - timedelta(seconds=1),
                basis=GhsaWatermarkCommittedWindow(window=_window()),
            )


class TestSeeding:
    """The first boundary is asserted, and says so."""

    def test_a_seed_is_marked_as_one(self) -> None:
        """"We read up to here" and "someone said we had" are different claims."""
        watermark = GhsaSyncWatermarkV1(
            observed_through_at=_MARK,
            basis=GhsaWatermarkSeed(note="corpus backfill completed 2026-09-16"),
        )
        assert watermark.seeded

    def test_a_seed_without_a_reason_is_refused(self) -> None:
        """The first reader who asks why the corpus starts here deserves an answer."""
        with pytest.raises(InvalidGhsaSyncWatermarkError, match="why its boundary"):
            GhsaWatermarkSeed(note="")


class TestBoundaryHygiene:
    """A boundary the window contract cannot express is not a boundary."""

    def test_a_naive_instant_is_refused(self) -> None:
        """A boundary with no zone cannot bound a source in UTC."""
        with pytest.raises(InvalidGhsaSyncWatermarkError, match="timezone-aware"):
            GhsaSyncWatermarkV1(
                observed_through_at=datetime(2026, 9, 16, 18, 56, 22),  # noqa: DTZ001
                basis=GhsaWatermarkSeed(note="seed"),
            )

    def test_sub_second_precision_is_refused(self) -> None:
        """The window carries seconds; a millisecond boundary would round somewhere."""
        with pytest.raises(InvalidGhsaSyncWatermarkError, match="sub-second"):
            GhsaSyncWatermarkV1(
                observed_through_at=_MARK.replace(microsecond=500_000),
                basis=GhsaWatermarkSeed(note="seed"),
            )


class TestRetention:
    """What is written must read back as the same claim."""

    def test_a_committed_watermark_round_trips(self) -> None:
        """Including the window, so the invariant is re-checked on read."""
        watermark = GhsaSyncWatermarkV1(
            observed_through_at=_MARK,
            basis=GhsaWatermarkCommittedWindow(window=_window()),
        )
        assert parse_watermark(serialize_watermark(watermark)) == watermark

    def test_a_seeded_watermark_round_trips(self) -> None:
        """A seed must not read back as a committed window."""
        watermark = GhsaSyncWatermarkV1(
            observed_through_at=_MARK, basis=GhsaWatermarkSeed(note="backfill")
        )
        restored = parse_watermark(serialize_watermark(watermark))
        assert restored == watermark
        assert restored.seeded

    def test_the_retained_document_names_its_contract(self) -> None:
        """A watermark from another contract must not be read as this one."""
        watermark = GhsaSyncWatermarkV1(
            observed_through_at=_MARK, basis=GhsaWatermarkSeed(note="backfill")
        )
        assert watermark.payload["contract_version"] == (
            GHSA_SYNC_WATERMARK_CONTRACT_VERSION
        )

    def test_another_contract_version_is_refused(self) -> None:
        """Reading it anyway would apply this contract's rules to another's data."""
        with pytest.raises(InvalidGhsaSyncWatermarkError, match="another contract"):
            parse_watermark(b'{"contract_version":"something-else:v9"}')

    @pytest.mark.parametrize(
        "payload",
        [b"not json", b"[]", b'{"contract_version":"opslens-ghsa-sync-watermark:v1"}'],
    )
    def test_a_malformed_document_is_refused(self, payload: bytes) -> None:
        """A watermark that cannot be read must not default to anything."""
        with pytest.raises(InvalidGhsaSyncWatermarkError):
            parse_watermark(payload)


class TestTheScheduledInvocation:
    """One instant and nothing else."""

    def test_it_reads_the_fired_instant(self) -> None:
        """The happy case, in the rendering the scheduler substitutes."""
        parser = GhsaIncrementalInvocationParserV1()
        assert parser.parse(
            {"schema_version": "1", "target_end_at": "2026-09-17T12:00:00Z"}
        ) == datetime(2026, 9, 17, 12, 0, tzinfo=UTC)

    def test_it_accepts_the_sub_second_rendering_and_truncates_toward_the_past(
        self,
    ) -> None:
        """Rounding forward would claim an instant the schedule had not reached."""
        parser = GhsaIncrementalInvocationParserV1()
        assert parser.parse(
            {"schema_version": "1", "target_end_at": "2026-09-17T12:00:00.987Z"}
        ) == datetime(2026, 9, 17, 12, 0, tzinfo=UTC)

    def test_it_accepts_an_explicit_utc_offset(self) -> None:
        """The rendering is the service's choice, not this contract's."""
        parser = GhsaIncrementalInvocationParserV1()
        assert parser.parse(
            {"schema_version": "1", "target_end_at": "2026-09-17T12:00:00+00:00"}
        ) == datetime(2026, 9, 17, 12, 0, tzinfo=UTC)

    def test_an_unknown_field_is_refused_rather_than_ignored(self) -> None:
        """A schedule sending something new is a schedule whose intent changed."""
        parser = GhsaIncrementalInvocationParserV1()
        with pytest.raises(InvalidGhsaIncrementalInvocationError, match="unsupported"):
            parser.parse(
                {
                    "schema_version": "1",
                    "target_end_at": "2026-09-17T12:00:00Z",
                    "lookback_hours": 48,
                }
            )

    def test_a_missing_field_is_refused(self) -> None:
        """There is no default target; not knowing when is not a window."""
        parser = GhsaIncrementalInvocationParserV1()
        with pytest.raises(InvalidGhsaIncrementalInvocationError, match="missing"):
            parser.parse({"schema_version": "1"})

    def test_another_schema_version_is_refused(self) -> None:
        """The Bronze v1 contract takes a window; this one takes an instant."""
        parser = GhsaIncrementalInvocationParserV1()
        with pytest.raises(InvalidGhsaIncrementalInvocationError, match="schema_version"):
            parser.parse({"schema_version": 1, "target_end_at": "2026-09-17T12:00:00Z"})

    @pytest.mark.parametrize(
        "value", ["2026-09-17", "yesterday", "", "2026-09-17T12:00:00-03:00"]
    )
    def test_an_unreadable_target_is_refused(self, value: str) -> None:
        """A local-offset instant is refused rather than assumed to mean UTC."""
        parser = GhsaIncrementalInvocationParserV1()
        with pytest.raises(InvalidGhsaIncrementalInvocationError, match="one UTC instant"):
            parser.parse({"schema_version": "1", "target_end_at": value})
