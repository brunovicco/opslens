"""Tests for settling a Silver invocation whose response never arrived.

A dense GHSA window keeps the Lambda busy for ten minutes or more, and the HTTP
connection carries no bytes for that whole time. Measured against the live function:
the platform report said `durationMs 630754` and `status success` while the client
raised a read timeout on the same call. The window was complete in S3 and the ledger
recorded nothing, twice.

Raising the client timeout cannot fix that, because the connection does not survive
the wait. So the client stops being the authority and the content-addressed COMPLETE
manifest becomes it.

```text
no response != no result
absent manifest != failed window
```

The key derivation is asserted against a real observed pair, read back from S3, rather
than against a format string that could agree with a wrong implementation.
"""

from collections.abc import Mapping
from typing import Final

import pytest

from opslens.ingestion.ghsa.application.backfill_planning import (
    BackfillPlanError,
    completion_settles_window,
    read_silver_completion,
    silver_completion_key,
)

# Both keys below were read back from the live dev bucket for the same window.
_OBSERVED_SYNC: Final = "93cfff9389accfc6d209dd064fb248c25670136ec7b2bee5f89357f56ce6ff6d"
_OBSERVED_ATTEMPT: Final = "68969019b6ad36df028ffe8560d680832c6c797fc12fc3cb4f2da22800488bdb"
_OBSERVED_BRONZE: Final = (
    f"bronze/ghsa/advisories/mode=published/sync_id={_OBSERVED_SYNC}"
    f"/attempt_id={_OBSERVED_ATTEMPT}/manifest.json"
)
_OBSERVED_SILVER: Final = (
    f"silver/ghsa/completions/schema_version=1/sync_id={_OBSERVED_SYNC}"
    f"/attempt_id={_OBSERVED_ATTEMPT}/manifest.json"
)


class _Stream:
    """A minimal streaming body."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        """Return the whole payload."""
        return self._payload


class _StubStore:
    """An S3 client that serves a scripted sequence of reads."""

    def __init__(self, outcome: bytes | Exception) -> None:
        self._outcome = outcome

    def get_object(self, *, Bucket: str, Key: str) -> Mapping[str, object]:
        """Return the scripted response."""
        del Bucket, Key
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return {"Body": _Stream(self._outcome)}


def test_completion_key_matches_the_observed_pair() -> None:
    """The derived Silver key equals the one the live run actually wrote."""
    assert silver_completion_key(_OBSERVED_BRONZE) == _OBSERVED_SILVER


def test_completion_key_refuses_a_foreign_key() -> None:
    """A key from another dataset is refused rather than silently reshaped."""
    with pytest.raises(BackfillPlanError):
        silver_completion_key("bronze/kev/entries/sync_id=a/attempt_id=b/manifest.json")


def test_completion_key_refuses_a_key_without_a_coordinate() -> None:
    """A Bronze key missing a partition component cannot name a Silver object."""
    with pytest.raises(BackfillPlanError):
        silver_completion_key(
            f"bronze/ghsa/advisories/mode=published/sync_id={_OBSERVED_SYNC}/manifest.json"
        )


def test_a_complete_manifest_settles_the_window() -> None:
    """A COMPLETE manifest is accepted as the answer the response failed to carry."""
    store = _StubStore(b'{"completion_status": "complete", "record_count": 4795}')
    manifest = read_silver_completion(store, bucket="bucket", key=_OBSERVED_SILVER)
    assert manifest is not None
    assert manifest["record_count"] == 4795
    assert completion_settles_window(manifest)


def test_an_absent_manifest_leaves_the_window_unrecorded() -> None:
    """Silence in S3 is not success: the window stays out of the ledger."""
    store = _StubStore(KeyError("NoSuchKey"))
    assert read_silver_completion(store, bucket="bucket", key=_OBSERVED_SILVER) is None
    assert not completion_settles_window(None)


def test_an_incomplete_manifest_is_not_accepted() -> None:
    """A manifest that does not say complete cannot close a window."""
    store = _StubStore(b'{"completion_status": "partial"}')
    manifest = read_silver_completion(store, bucket="bucket", key=_OBSERVED_SILVER)
    assert not completion_settles_window(manifest)


def test_a_malformed_manifest_is_not_accepted() -> None:
    """Unparseable bytes are absence, not a result."""
    store = _StubStore(b"not json")
    assert read_silver_completion(store, bucket="bucket", key=_OBSERVED_SILVER) is None
