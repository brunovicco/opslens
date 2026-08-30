"""Tests for exact-version historical EPSS Bronze evidence reads."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import pytest

from opslens.transformation.epss.adapters.outbound.s3_history_exact_object import (
    HistoricalEpssS3EvidenceMismatchError,
    S3VersionedHistoricalEpssBronzeObjectReader,
)
from opslens.transformation.epss.history.manifest import (
    HistoricalEpssBronzeManifestParserV1,
    InvalidHistoricalEpssBronzeManifestError,
)
from opslens.transformation.epss.history.models import (
    HistoricalEpssBronzeObjectPayloadV1,
)
from opslens.transformation.epss.history.reader import (
    HistoricalEpssBronzeSourceEvidenceMismatchError,
    ReadHistoricalEpssBronzeEvidence,
)

BUCKET = "opslens-test-data"
COMMIT = "a" * 40
SNAPSHOT_DATE = "2021-04-14"
PREFIX = (
    "bronze/epss-history/schema_version=1/"
    f"archive_commit={COMMIT}/snapshot_date={SNAPSHOT_DATE}"
)
MANIFEST_KEY = f"{PREFIX}/manifest.json"
SOURCE_KEY = f"{PREFIX}/epss_scores.csv.gz"
MANIFEST_VERSION = "manifest-version"
SOURCE_VERSION = "source-version"
SOURCE_BYTES = b"exact-historical-epss-source"


def _git_blob_sha1(payload: bytes) -> str:
    prefix = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(prefix + payload, usedforsecurity=False).hexdigest()


def _manifest_bytes(**overrides: Any) -> bytes:
    value: dict[str, Any] = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "archive_repository": "empiricalsec/epss_scores",
        "archive_commit": COMMIT,
        "archive_path": f"2021/epss_scores-{SNAPSHOT_DATE}.csv.gz",
        "archive_git_blob_sha1": _git_blob_sha1(SOURCE_BYTES),
        "model_era": "v1",
        "source_metadata_present": False,
        "source_object_key": SOURCE_KEY,
        "source_object_version_id": SOURCE_VERSION,
        "source_sha256": hashlib.sha256(SOURCE_BYTES).hexdigest(),
        "compressed_size_bytes": len(SOURCE_BYTES),
    }
    value.update(overrides)
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


@dataclass
class FakeBody:
    payload: bytes
    closed: bool = False

    def read(self) -> bytes:
        return self.payload

    def close(self) -> None:
        self.closed = True


class FakeS3Client:
    def __init__(self, objects: dict[tuple[str, str], bytes]) -> None:
        self.objects = objects
        self.calls: list[dict[str, str]] = []
        self.bodies: list[FakeBody] = []
        self.version_override: str | None = None
        self.content_length_delta = 0

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> dict[str, object]:
        self.calls.append({"Bucket": Bucket, "Key": Key, "VersionId": VersionId})
        payload = self.objects[(Key, VersionId)]
        body = FakeBody(payload)
        self.bodies.append(body)
        return {
            "Body": body,
            "VersionId": self.version_override or VersionId,
            "ContentLength": len(payload) + self.content_length_delta,
        }


def _service(
    *,
    manifest_bytes: bytes | None = None,
    source_bytes: bytes = SOURCE_BYTES,
) -> tuple[ReadHistoricalEpssBronzeEvidence, FakeS3Client]:
    client = FakeS3Client(
        {
            (MANIFEST_KEY, MANIFEST_VERSION): manifest_bytes or _manifest_bytes(),
            (SOURCE_KEY, SOURCE_VERSION): source_bytes,
        }
    )
    reader = S3VersionedHistoricalEpssBronzeObjectReader(
        client=client,
        bucket_name=BUCKET,
    )
    return ReadHistoricalEpssBronzeEvidence(object_reader=reader), client


def test_reads_manifest_and_source_by_exact_version_id() -> None:
    service, client = _service()

    evidence = service.execute(
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION,
    )

    assert evidence.manifest.snapshot_date.isoformat() == SNAPSHOT_DATE
    assert evidence.manifest.manifest_version_id == MANIFEST_VERSION
    assert evidence.source.key == SOURCE_KEY
    assert evidence.source.version_id == SOURCE_VERSION
    assert evidence.source.raw_bytes == SOURCE_BYTES
    assert client.calls == [
        {"Bucket": BUCKET, "Key": MANIFEST_KEY, "VersionId": MANIFEST_VERSION},
        {"Bucket": BUCKET, "Key": SOURCE_KEY, "VersionId": SOURCE_VERSION},
    ]
    assert all(body.closed for body in client.bodies)


def test_rejects_s3_response_version_mismatch_and_closes_body() -> None:
    service, client = _service()
    client.version_override = "wrong-version"

    with pytest.raises(HistoricalEpssS3EvidenceMismatchError, match="VersionId"):
        service.execute(
            manifest_key=MANIFEST_KEY,
            manifest_version_id=MANIFEST_VERSION,
        )

    assert client.bodies[0].closed is True


def test_rejects_s3_content_length_mismatch() -> None:
    service, client = _service()
    client.content_length_delta = 1

    with pytest.raises(HistoricalEpssS3EvidenceMismatchError, match="ContentLength"):
        service.execute(
            manifest_key=MANIFEST_KEY,
            manifest_version_id=MANIFEST_VERSION,
        )


def test_manifest_parser_rejects_extra_authority_field() -> None:
    payload = HistoricalEpssBronzeObjectPayloadV1(
        key=MANIFEST_KEY,
        version_id=MANIFEST_VERSION,
        raw_bytes=_manifest_bytes(unexpected="value"),
    )

    with pytest.raises(InvalidHistoricalEpssBronzeManifestError, match="extra"):
        HistoricalEpssBronzeManifestParserV1().parse(payload)


def test_manifest_parser_rejects_source_key_coordinate_mismatch() -> None:
    payload = HistoricalEpssBronzeObjectPayloadV1(
        key=MANIFEST_KEY,
        version_id=MANIFEST_VERSION,
        raw_bytes=_manifest_bytes(source_object_key="bronze/epss-history/wrong.csv.gz"),
    )

    with pytest.raises(InvalidHistoricalEpssBronzeManifestError, match="source object key"):
        HistoricalEpssBronzeManifestParserV1().parse(payload)


def test_manifest_parser_rejects_model_era_date_mismatch() -> None:
    payload = HistoricalEpssBronzeObjectPayloadV1(
        key=MANIFEST_KEY,
        version_id=MANIFEST_VERSION,
        raw_bytes=_manifest_bytes(model_era="v2", source_metadata_present=True),
    )

    with pytest.raises(InvalidHistoricalEpssBronzeManifestError, match="model_era"):
        HistoricalEpssBronzeManifestParserV1().parse(payload)


def test_rejects_source_sha_mismatch() -> None:
    service, _ = _service(
        manifest_bytes=_manifest_bytes(source_sha256="0" * 64),
    )

    with pytest.raises(HistoricalEpssBronzeSourceEvidenceMismatchError, match="SHA-256"):
        service.execute(
            manifest_key=MANIFEST_KEY,
            manifest_version_id=MANIFEST_VERSION,
        )


def test_rejects_source_git_blob_identity_mismatch() -> None:
    service, _ = _service(
        manifest_bytes=_manifest_bytes(archive_git_blob_sha1="0" * 40),
    )

    with pytest.raises(HistoricalEpssBronzeSourceEvidenceMismatchError, match="Git blob"):
        service.execute(
            manifest_key=MANIFEST_KEY,
            manifest_version_id=MANIFEST_VERSION,
        )
