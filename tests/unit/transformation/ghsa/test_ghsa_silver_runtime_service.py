"""Tests for end-to-end exact GHSA Bronze-to-Silver preparation."""

import hashlib
import json
from dataclasses import dataclass

import pytest

from opslens.ingestion.ghsa.application.attempt import (
    GhsaAttemptIdFactory,
)
from opslens.ingestion.ghsa.application.key_factory import (
    GhsaBronzeKeyFactory,
)
from opslens.ingestion.ghsa.application.manifest import (
    GhsaCompleteManifest,
    GhsaCompleteManifestSerializer,
    GhsaStoredPage,
)
from opslens.ingestion.ghsa.domain.api_page import (
    GhsaAdvisoryApiPageParser,
    GhsaAdvisoryPagination,
    GhsaRequestUrlPolicy,
)
from opslens.ingestion.ghsa.domain.sync import (
    GhsaSyncMode,
    GhsaSyncWindow,
)
from opslens.transformation.ghsa.application.record_composer import (
    GhsaSilverRecordComposerV1,
)
from opslens.transformation.ghsa.domain.collections_transformer import (
    GhsaAdvisoryCollectionsTransformer,
)
from opslens.transformation.ghsa.domain.transformer import (
    GhsaAdvisoryCoreTransformer,
)
from opslens.transformation.ghsa.domain.vulnerabilities_transformer import (
    GhsaVulnerabilitiesTransformer,
)
from opslens.transformation.ghsa.runtime.manifest_processor import (
    GhsaBronzeManifestProcessorV1,
)
from opslens.transformation.ghsa.runtime.materializer import (
    GhsaSilverMaterializerV1,
)
from opslens.transformation.ghsa.runtime.object_payload import (
    GhsaBronzeObjectPayloadV1,
)
from opslens.transformation.ghsa.runtime.page_processor import (
    GhsaBronzePageProcessorV1,
)
from opslens.transformation.ghsa.runtime.record_processor import (
    GhsaSilverRecordProcessorV1,
)
from opslens.transformation.ghsa.runtime.service import (
    GhsaSilverRuntimeServiceV1,
)
from opslens.transformation.ghsa.serialization.logical_hash import (
    GhsaLogicalRecordSetHasherV1,
)
from opslens.transformation.ghsa.serialization.parquet import (
    GhsaSilverParquetSerializerV1,
)

MANIFEST_VERSION_ID = "manifest-version"
PAGE_VERSION_ID = "page-version"


@dataclass(frozen=True, slots=True)
class RuntimeFixture:
    """Hold one exact in-memory Bronze attempt."""

    manifest_key: str
    manifest_version_id: str
    page_key: str
    page_version_id: str
    payloads: dict[
        tuple[str, str],
        GhsaBronzeObjectPayloadV1,
    ]


class FakeObjectReader:
    """Return exact objects from an in-memory immutable coordinate map."""

    def __init__(
        self,
        payloads: dict[
            tuple[str, str],
            GhsaBronzeObjectPayloadV1,
        ],
    ) -> None:
        """Initialize exact-object fixtures."""
        self._payloads = payloads
        self.calls: list[tuple[str, str]] = []

    def get(
        self,
        *,
        key: str,
        version_id: str,
    ) -> GhsaBronzeObjectPayloadV1:
        """Return one exact object and record the requested coordinates."""
        self.calls.append((key, version_id))
        return self._payloads[(key, version_id)]


def _window() -> GhsaSyncWindow:
    """Return one bounded published source window."""
    from datetime import UTC, datetime

    return GhsaSyncWindow(
        mode=GhsaSyncMode.PUBLISHED,
        start_at=datetime(
            2026,
            8,
            27,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            28,
            tzinfo=UTC,
        ),
    )


def _source_advisory() -> dict[str, object]:
    """Return one complete reviewed source advisory inside the test window."""
    return {
        "ghsa_id": "GHSA-2345-6789-cfgh",
        "cve_id": "CVE-2026-12345",
        "url": (
            "https://api.github.com/advisories/"
            "GHSA-2345-6789-cfgh"
        ),
        "html_url": (
            "https://github.com/advisories/"
            "GHSA-2345-6789-cfgh"
        ),
        "repository_advisory_url": None,
        "summary": "Example reviewed advisory",
        "description": "Example advisory description.",
        "type": "reviewed",
        "severity": "high",
        "source_code_location": None,
        "published_at": "2026-08-27T10:00:00Z",
        "updated_at": "2026-08-27T11:00:00Z",
        "github_reviewed_at": "2026-08-27T12:00:00Z",
        "nvd_published_at": None,
        "withdrawn_at": None,
        "identifiers": [
            {
                "type": "GHSA",
                "value": "GHSA-2345-6789-cfgh",
            },
            {
                "type": "CVE",
                "value": "CVE-2026-12345",
            },
        ],
        "references": [
            "https://github.com/advisories/"
            "GHSA-2345-6789-cfgh",
        ],
        "cwes": [
            {
                "cwe_id": "CWE-79",
                "name": "Cross-site Scripting",
            },
        ],
        "cvss_severities": {
            "cvss_v3": {
                "vector_string": (
                    "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/"
                    "S:U/C:H/I:H/A:H"
                ),
                "score": 9.8,
            },
        },
        "vulnerabilities": [
            {
                "package": {
                    "ecosystem": "pip",
                    "name": "example-package",
                },
                "vulnerable_version_range": (
                    ">= 1.0.0, < 1.2.0"
                ),
                "first_patched_version": "1.2.0",
                "vulnerable_functions": [
                    "unsafe_load",
                ],
            },
        ],
    }


def _fixture(
    advisories: list[dict[str, object]],
    *,
    manifest_attempt_id: str | None = None,
) -> RuntimeFixture:
    """Build one exact canonical Bronze attempt fixture."""
    window = _window()
    parser = GhsaAdvisoryApiPageParser()
    key_factory = GhsaBronzeKeyFactory()

    page_bytes = json.dumps(
        advisories,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    request_url = GhsaRequestUrlPolicy.build_initial(
        window
    )

    source_page = parser.parse(
        page_bytes,
        request_url=request_url,
        link_header=None,
        window=window,
    )

    pagination = GhsaAdvisoryPagination(
        window=window,
        pages=(source_page,),
    )

    actual_attempt_id = GhsaAttemptIdFactory().build(
        window=window,
        pagination=pagination,
    )

    attempt_id = (
        actual_attempt_id
        if manifest_attempt_id is None
        else manifest_attempt_id
    )

    page_key = key_factory.build_page_key(
        window=window,
        attempt_id=attempt_id,
        page_ordinal=1,
    )

    first_ghsa_id = (
        source_page.ghsa_ids[0]
        if source_page.ghsa_ids
        else None
    )
    last_ghsa_id = (
        source_page.ghsa_ids[-1]
        if source_page.ghsa_ids
        else None
    )

    stored_page = GhsaStoredPage(
        page_ordinal=1,
        key=page_key,
        version_id=PAGE_VERSION_ID,
        size_bytes=len(page_bytes),
        sha256=hashlib.sha256(
            page_bytes
        ).hexdigest(),
        item_count=len(advisories),
        request_url=request_url,
        next_url=None,
        first_ghsa_id=first_ghsa_id,
        last_ghsa_id=last_ghsa_id,
    )

    manifest = GhsaCompleteManifest(
        mode=window.mode,
        sync_id=window.sync_id,
        attempt_id=attempt_id,
        window_start_at=window.start_at,
        window_end_at=window.end_at,
        total_items=len(advisories),
        total_bytes=len(page_bytes),
        pages=(stored_page,),
    )

    manifest_bytes = (
        GhsaCompleteManifestSerializer().serialize(
            manifest
        )
    )

    manifest_key = key_factory.build_manifest_key(
        window=window,
        attempt_id=attempt_id,
    )

    payloads = {
        (
            manifest_key,
            MANIFEST_VERSION_ID,
        ): GhsaBronzeObjectPayloadV1(
            key=manifest_key,
            version_id=MANIFEST_VERSION_ID,
            raw_bytes=manifest_bytes,
        ),
        (
            page_key,
            PAGE_VERSION_ID,
        ): GhsaBronzeObjectPayloadV1(
            key=page_key,
            version_id=PAGE_VERSION_ID,
            raw_bytes=page_bytes,
        ),
    }

    return RuntimeFixture(
        manifest_key=manifest_key,
        manifest_version_id=MANIFEST_VERSION_ID,
        page_key=page_key,
        page_version_id=PAGE_VERSION_ID,
        payloads=payloads,
    )


def _service(
    reader: FakeObjectReader,
) -> GhsaSilverRuntimeServiceV1:
    """Build the complete deterministic GHSA Silver preparation runtime."""
    composer = GhsaSilverRecordComposerV1(
        core_transformer=GhsaAdvisoryCoreTransformer(),
        collections_transformer=(
            GhsaAdvisoryCollectionsTransformer()
        ),
        vulnerabilities_transformer=(
            GhsaVulnerabilitiesTransformer()
        ),
    )

    return GhsaSilverRuntimeServiceV1(
        object_reader=reader,
        manifest_processor=GhsaBronzeManifestProcessorV1(
            key_factory=GhsaBronzeKeyFactory(),
            serializer=GhsaCompleteManifestSerializer(),
        ),
        source_page_parser=GhsaAdvisoryApiPageParser(),
        attempt_id_factory=GhsaAttemptIdFactory(),
        page_processor=GhsaBronzePageProcessorV1(),
        record_processor=GhsaSilverRecordProcessorV1(
            composer=composer,
        ),
        materializer=GhsaSilverMaterializerV1(
            logical_hasher=GhsaLogicalRecordSetHasherV1(),
            parquet_serializer=(
                GhsaSilverParquetSerializerV1()
            ),
        ),
    )


def test_prepares_silver_from_exact_manifest_and_page_versions() -> None:
    """Prepare deterministic Silver using only manifest-authorized objects."""
    fixture = _fixture([_source_advisory()])
    reader = FakeObjectReader(fixture.payloads)

    result = _service(reader).prepare(
        manifest_key=fixture.manifest_key,
        manifest_version_id=fixture.manifest_version_id,
    )

    assert reader.calls == [
        (
            fixture.manifest_key,
            fixture.manifest_version_id,
        ),
        (
            fixture.page_key,
            fixture.page_version_id,
        ),
    ]

    assert result.record_count == 1
    assert len(result.logical_record_set_sha256) == 64

    assert result.parquet_artifact is not None
    assert result.parquet_artifact.row_count == 1
    assert result.parquet_artifact.parquet_bytes.startswith(
        b"PAR1"
    )


def test_rejects_tampered_persisted_page_bytes() -> None:
    """Reject page bytes that disagree with COMPLETE manifest evidence."""
    fixture = _fixture([_source_advisory()])

    payloads = dict(fixture.payloads)

    payloads[
        (
            fixture.page_key,
            fixture.page_version_id,
        )
    ] = GhsaBronzeObjectPayloadV1(
        key=fixture.page_key,
        version_id=fixture.page_version_id,
        raw_bytes=b"[]",
    )

    reader = FakeObjectReader(payloads)

    with pytest.raises(
        ValueError,
        match="SHA-256",
    ):
        _service(reader).prepare(
            manifest_key=fixture.manifest_key,
            manifest_version_id=fixture.manifest_version_id,
        )


def test_rejects_manifest_attempt_id_not_bound_to_exact_pages() -> None:
    """Recompute attempt identity instead of trusting manifest text."""
    fixture = _fixture(
        [_source_advisory()],
        manifest_attempt_id="9" * 64,
    )

    reader = FakeObjectReader(fixture.payloads)

    with pytest.raises(
        ValueError,
        match="attempt_id does not match",
    ):
        _service(reader).prepare(
            manifest_key=fixture.manifest_key,
            manifest_version_id=fixture.manifest_version_id,
        )


def test_rejects_reader_returning_different_version() -> None:
    """Reject a reader that violates exact-object coordinate semantics."""
    fixture = _fixture([_source_advisory()])

    payloads = dict(fixture.payloads)

    payloads[
        (
            fixture.page_key,
            fixture.page_version_id,
        )
    ] = GhsaBronzeObjectPayloadV1(
        key=fixture.page_key,
        version_id="different-version",
        raw_bytes=fixture.payloads[
            (
                fixture.page_key,
                fixture.page_version_id,
            )
        ].raw_bytes,
    )

    reader = FakeObjectReader(payloads)

    with pytest.raises(
        ValueError,
        match="different VersionId",
    ):
        _service(reader).prepare(
            manifest_key=fixture.manifest_key,
            manifest_version_id=fixture.manifest_version_id,
        )


def test_prepares_zero_result_attempt_without_parquet() -> None:
    """Preserve exact empty Bronze attempts without fabricating Parquet."""
    fixture = _fixture([])
    reader = FakeObjectReader(fixture.payloads)

    result = _service(reader).prepare(
        manifest_key=fixture.manifest_key,
        manifest_version_id=fixture.manifest_version_id,
    )

    assert result.record_count == 0
    assert len(result.logical_record_set_sha256) == 64
    assert result.parquet_artifact is None
