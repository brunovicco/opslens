"""Tests for holding the GHSA observation boundary in S3.

Every case is a way two runs, or one careless run, could undo work already done. The
boundary is read-modify-write on a single object and the schedule does not wait for a slow
run to finish, so "last write wins" is a corpus losing a window nobody records losing.

```text
two runs != two windows
last write wins != last write is right
a valid precondition != a correct value
```
"""

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from botocore.exceptions import ClientError

from opslens.ingestion.ghsa.adapters.outbound.s3_sync_watermark import (
    GhsaSyncWatermarkAlreadyExistsError,
    GhsaSyncWatermarkNotAdvancingError,
    GhsaSyncWatermarkNotFoundError,
    GhsaSyncWatermarkPreconditionFailedError,
    GhsaSyncWatermarkStoreError,
    PersistedGhsaSyncWatermark,
    S3GhsaSyncWatermarkStore,
)
from opslens.ingestion.ghsa.application.sync_watermark import (
    GhsaSyncWatermarkV1,
    GhsaWatermarkCommittedWindow,
    GhsaWatermarkSeed,
    serialize_watermark,
)
from opslens.ingestion.ghsa.domain.sync import GhsaSyncMode, GhsaSyncWindow

_MARK = datetime(2026, 9, 16, 18, 56, 22, tzinfo=UTC)
_BUCKET = "opslens-dev-data"
_KEY = "state/ghsa/sync-watermark.json"


def _seed(at: datetime = _MARK) -> GhsaSyncWatermarkV1:
    """Build one seeded boundary."""
    return GhsaSyncWatermarkV1(
        observed_through_at=at, basis=GhsaWatermarkSeed(note="corpus backfill")
    )


def _committed(at: datetime) -> GhsaSyncWatermarkV1:
    """Build one boundary committed by a window ending there."""
    return GhsaSyncWatermarkV1(
        observed_through_at=at,
        basis=GhsaWatermarkCommittedWindow(
            window=GhsaSyncWindow(
                mode=GhsaSyncMode.MODIFIED, start_at=at - timedelta(hours=6), end_at=at
            )
        ),
    )


class _Body:
    """A streaming body that records whether it was closed."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.closed = False

    def read(self, amt: int | None = None) -> bytes:
        """Return the whole object."""
        del amt
        return self._payload

    def close(self) -> None:
        """Record the close."""
        self.closed = True


def _client_error(status: int) -> ClientError:
    """Build one Botocore error carrying that HTTP status."""
    response: Any = {
        "Error": {"Code": "Conditional", "Message": "conditional"},
        "ResponseMetadata": {"HTTPStatusCode": status},
    }
    return ClientError(response, "PutObject")


class _Client:
    """One canned S3 object, with recorded calls."""

    def __init__(
        self,
        payload: bytes | None = None,
        get_error: ClientError | None = None,
        put_error: ClientError | None = None,
    ) -> None:
        self._payload = payload
        self._get_error = get_error
        self._put_error = put_error
        self.puts: list[Mapping[str, object]] = []
        self.body: _Body | None = None

    def get_object(self, **kwargs: object) -> Mapping[str, object]:
        """Return the canned object."""
        del kwargs
        if self._get_error is not None:
            raise self._get_error
        assert self._payload is not None
        self.body = _Body(self._payload)
        return {"Body": self.body, "ETag": '"abc123"'}

    def put_object(self, **kwargs: object) -> Mapping[str, object]:
        """Record and answer the write."""
        self.puts.append(kwargs)
        if self._put_error is not None:
            raise self._put_error
        return {"ETag": '"def456"'}


def _store(client: _Client) -> S3GhsaSyncWatermarkStore:
    """Build the store over that client."""
    return S3GhsaSyncWatermarkStore(
        client=client, bucket_name=_BUCKET, object_key=_KEY
    )


def _persisted(at: datetime = _MARK) -> PersistedGhsaSyncWatermark:
    """Build one previously-read state."""
    payload = serialize_watermark(_seed(at))
    return PersistedGhsaSyncWatermark(
        watermark=_seed(at), etag='"abc123"', sha256=hashlib.sha256(payload).hexdigest()
    )


class TestLoad:
    """Not knowing the boundary is a distinct outcome from there being none."""

    def test_it_reads_the_boundary_and_its_token(self) -> None:
        """The token is what makes the later write conditional."""
        client = _Client(payload=serialize_watermark(_seed()))
        persisted = _store(client).load()
        assert persisted.watermark == _seed()
        assert persisted.etag == '"abc123"'

    def test_it_closes_the_stream(self) -> None:
        """A leaked connection in a warm Lambda outlives the request that made it."""
        client = _Client(payload=serialize_watermark(_seed()))
        _store(client).load()
        assert client.body is not None
        assert client.body.closed

    def test_an_absent_boundary_is_its_own_error(self) -> None:
        """Never established and could not be read must not look the same."""
        client = _Client(get_error=_client_error(404))
        with pytest.raises(GhsaSyncWatermarkNotFoundError):
            _store(client).load()

    def test_an_unreadable_boundary_is_not_an_absent_one(self) -> None:
        """A permissions failure must not start the corpus over from a seed."""
        client = _Client(get_error=_client_error(403))
        with pytest.raises(GhsaSyncWatermarkStoreError, match="could not be read"):
            _store(client).load()


class TestInitialize:
    """A seed must never reset a corpus that has been advancing."""

    def test_it_creates_with_a_create_only_precondition(self) -> None:
        """IfNoneMatch is what makes a second seed fail instead of overwrite."""
        client = _Client()
        _store(client).initialize(_seed())
        assert client.puts[0]["IfNoneMatch"] == "*"

    def test_seeding_over_an_existing_boundary_is_refused(self) -> None:
        """Months of advancing must not be undone by re-running a bootstrap step."""
        client = _Client(put_error=_client_error(412))
        with pytest.raises(GhsaSyncWatermarkAlreadyExistsError, match="already exists"):
            _store(client).initialize(_seed())


class TestAdvance:
    """The race is real: a catch-up run takes minutes and the schedule does not wait."""

    def test_it_writes_conditional_on_the_token_it_read(self) -> None:
        """Without IfMatch, the loser of a race silently discards the winner's window."""
        client = _Client()
        _store(client).advance(
            previous=_persisted(), watermark=_committed(_MARK + timedelta(hours=6))
        )
        assert client.puts[0]["IfMatch"] == '"abc123"'

    def test_losing_the_race_is_reported_as_losing_the_race(self) -> None:
        """The window was not committed, so it is simply run again."""
        client = _Client(put_error=_client_error(412))
        with pytest.raises(
            GhsaSyncWatermarkPreconditionFailedError, match="advanced the GHSA boundary first"
        ):
            _store(client).advance(
                previous=_persisted(), watermark=_committed(_MARK + timedelta(hours=6))
            )

    def test_moving_the_boundary_backwards_is_refused_before_the_write(self) -> None:
        """A valid token proves nobody else wrote, not that this write is progress."""
        client = _Client()
        with pytest.raises(GhsaSyncWatermarkNotAdvancingError, match="not move forward"):
            _store(client).advance(
                previous=_persisted(), watermark=_committed(_MARK - timedelta(hours=1))
            )
        assert client.puts == []

    def test_standing_still_is_refused(self) -> None:
        """Rewriting the same instant spends a write and proves nothing."""
        client = _Client()
        with pytest.raises(GhsaSyncWatermarkNotAdvancingError):
            _store(client).advance(previous=_persisted(), watermark=_seed(_MARK))
        assert client.puts == []

    def test_a_boundary_that_disappears_mid_run_is_its_own_error(self) -> None:
        """Deleted underneath a run is not the same as never having existed."""
        client = _Client(put_error=_client_error(404))
        with pytest.raises(GhsaSyncWatermarkNotFoundError, match="disappeared"):
            _store(client).advance(
                previous=_persisted(), watermark=_committed(_MARK + timedelta(hours=6))
            )


class TestPersistedState:
    """State that cannot support a conditional write is not usable state."""

    def test_state_without_a_token_is_refused(self) -> None:
        """It could only ever be written unconditionally."""
        with pytest.raises(GhsaSyncWatermarkStoreError, match="ETag"):
            PersistedGhsaSyncWatermark(watermark=_seed(), etag="  ", sha256="a" * 64)

    def test_state_without_a_digest_is_refused(self) -> None:
        """The digest is what lets a later reader check it got the same bytes."""
        with pytest.raises(GhsaSyncWatermarkStoreError, match="digest"):
            PersistedGhsaSyncWatermark(watermark=_seed(), etag='"x"', sha256="short")


class TestStoreCoordinates:
    """A store pointed at nothing would fail per request rather than at composition."""

    @pytest.mark.parametrize(("bucket", "key"), [("", _KEY), (_BUCKET, "  ")])
    def test_an_empty_coordinate_is_refused(self, bucket: str, key: str) -> None:
        """Fail where it is cheap to notice."""
        with pytest.raises(GhsaSyncWatermarkStoreError, match="bucket and an object key"):
            S3GhsaSyncWatermarkStore(
                client=_Client(), bucket_name=bucket, object_key=key
            )
