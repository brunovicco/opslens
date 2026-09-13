"""Tests for exact EPSS authority decoding."""

import gzip
import hashlib
from dataclasses import dataclass, field

import pytest

from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.public_analysis.adapters.exact_epss_authority import (
    ExactEpssAuthorityError,
    ExactEpssAuthorityReader,
)
from opslens.public_analysis.adapters.exact_s3_authority_object import (
    ExactS3AuthorityObject,
)

_OBJECT_KEY = "bronze/epss/2026/09/10/epss_scores-current.csv.gz"
_VERSION_ID = "epss-version-1"
_SCORE_DATE = "2026-09-10T12:00:00Z"
_SNAPSHOT_DATE = "2026-09-10"
_MODEL_VERSION = "v2026.06.15"


def _payload() -> bytes:
    text = (
        f"#model_version:{_MODEL_VERSION},score_date:{_SCORE_DATE}\n"
        "cve,epss,percentile\n"
        "CVE-2026-54770,0.00339,0.26988\n"
    )
    return gzip.compress(text.encode("utf-8"), mtime=0)


def _metadata(payload: bytes) -> tuple[tuple[str, str], ...]:
    return (
        ("model_version", _MODEL_VERSION),
        ("score_date", _SCORE_DATE),
        ("sha256", hashlib.sha256(payload).hexdigest()),
        ("source", "first-epss"),
    )


def _empty_calls() -> list[tuple[str, str]]:
    """Return a precisely typed empty exact-read call log."""
    return []


@dataclass
class FakeExactObjectReader:
    """Return one configured immutable object and record exact read coordinates."""

    result: ExactS3AuthorityObject
    calls: list[tuple[str, str]] = field(default_factory=_empty_calls)

    def read(self, *, object_key: str, version_id: str) -> ExactS3AuthorityObject:
        """Record and satisfy one exact object-version read."""
        self.calls.append((object_key, version_id))
        return self.result


def _reader(
    *,
    payload: bytes | None = None,
    metadata: tuple[tuple[str, str], ...] | None = None,
) -> tuple[ExactEpssAuthorityReader, FakeExactObjectReader]:
    exact_payload = _payload() if payload is None else payload
    object_reader = FakeExactObjectReader(
        ExactS3AuthorityObject(
            object_key=_OBJECT_KEY,
            version_id=_VERSION_ID,
            payload=exact_payload,
            metadata=_metadata(exact_payload) if metadata is None else metadata,
        )
    )
    return (
        ExactEpssAuthorityReader(
            object_reader=object_reader,
            parser=EpssSnapshotParser(),
        ),
        object_reader,
    )


def test_decodes_complete_exact_epss_snapshot() -> None:
    """Reconstruct complete EPSS authority from one exact immutable object."""
    reader, object_reader = _reader()

    snapshot = reader.read(
        object_key=_OBJECT_KEY,
        version_id=_VERSION_ID,
        snapshot_date=_SNAPSHOT_DATE,
    )

    assert snapshot.snapshot_date == _SNAPSHOT_DATE
    assert snapshot.model_version == _MODEL_VERSION
    assert snapshot.row_count == 1
    assert object_reader.calls == [(_OBJECT_KEY, _VERSION_ID)]


def test_rejects_missing_or_extra_metadata() -> None:
    """Reject incomplete or expanded metadata authority before admission."""
    payload = _payload()
    base = dict(_metadata(payload))

    for changed in (
        tuple((key, value) for key, value in base.items() if key != "sha256"),
        (*base.items(), ("unexpected", "value")),
    ):
        reader, _ = _reader(payload=payload, metadata=changed)
        with pytest.raises(ExactEpssAuthorityError, match="exactly the required"):
            reader.read(
                object_key=_OBJECT_KEY,
                version_id=_VERSION_ID,
                snapshot_date=_SNAPSHOT_DATE,
            )


def test_rejects_source_or_digest_drift() -> None:
    """Reject source identity and payload digest contradictions."""
    payload = _payload()
    base = dict(_metadata(payload))

    source_drift = {**base, "source": "other"}
    reader, _ = _reader(payload=payload, metadata=tuple(source_drift.items()))
    with pytest.raises(ExactEpssAuthorityError, match="first-epss"):
        reader.read(
            object_key=_OBJECT_KEY,
            version_id=_VERSION_ID,
            snapshot_date=_SNAPSHOT_DATE,
        )

    digest_drift = {**base, "sha256": "0" * 64}
    reader, _ = _reader(payload=payload, metadata=tuple(digest_drift.items()))
    with pytest.raises(ExactEpssAuthorityError, match="sha256 mismatch"):
        reader.read(
            object_key=_OBJECT_KEY,
            version_id=_VERSION_ID,
            snapshot_date=_SNAPSHOT_DATE,
        )


def test_rejects_model_timestamp_or_snapshot_drift() -> None:
    """Reject contradictions in model, score timestamp, or logical snapshot date."""
    payload = _payload()
    base = dict(_metadata(payload))

    model_drift = {**base, "model_version": "v-other"}
    reader, _ = _reader(payload=payload, metadata=tuple(model_drift.items()))
    with pytest.raises(ExactEpssAuthorityError, match="model version mismatch"):
        reader.read(
            object_key=_OBJECT_KEY,
            version_id=_VERSION_ID,
            snapshot_date=_SNAPSHOT_DATE,
        )

    timestamp_drift = {**base, "score_date": "2026-09-10T13:00:00Z"}
    reader, _ = _reader(payload=payload, metadata=tuple(timestamp_drift.items()))
    with pytest.raises(ExactEpssAuthorityError, match="score timestamp mismatch"):
        reader.read(
            object_key=_OBJECT_KEY,
            version_id=_VERSION_ID,
            snapshot_date=_SNAPSHOT_DATE,
        )

    reader, _ = _reader(payload=payload)
    with pytest.raises(ExactEpssAuthorityError, match="snapshot date mismatch"):
        reader.read(
            object_key=_OBJECT_KEY,
            version_id=_VERSION_ID,
            snapshot_date="2026-09-09",
        )


def test_rejects_naive_metadata_timestamp() -> None:
    """Reject EPSS metadata timestamps that omit timezone information."""
    payload = _payload()
    metadata = dict(_metadata(payload))
    metadata["score_date"] = "2026-09-10T12:00:00"
    reader, _ = _reader(payload=payload, metadata=tuple(metadata.items()))

    with pytest.raises(ExactEpssAuthorityError, match="timezone information"):
        reader.read(
            object_key=_OBJECT_KEY,
            version_id=_VERSION_ID,
            snapshot_date=_SNAPSHOT_DATE,
        )
