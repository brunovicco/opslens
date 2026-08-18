"""Unit tests for the CISA KEV Bronze-to-Silver transformer."""

import hashlib
import json
from datetime import UTC, datetime

import pytest

from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.transformation.kev.domain.errors import InvalidKevSilverSourceError
from opslens.transformation.kev.domain.models import KevRansomwareUse
from opslens.transformation.kev.domain.transformer import KevSilverTransformer

CATALOG_VERSION = "2026.08.14"
DATE_RELEASED = datetime(2026, 8, 14, 16, 34, 49, 39100, tzinfo=UTC)
RETRIEVED_AT = datetime(2026, 8, 17, 3, 52, 3, 692159, tzinfo=UTC)


def _record(
    cve: str = "CVE-2026-20349",
    **overrides: object,
) -> dict[str, object]:
    """Build one valid CISA KEV vulnerability record."""
    record: dict[str, object] = {
        "cveID": cve,
        "vendorProject": "Cisco",
        "product": "Secure Firewall",
        "vulnerabilityName": "Cisco Secure Firewall Vulnerability",
        "dateAdded": "2026-08-11",
        "shortDescription": "A vulnerability affecting the product.",
        "requiredAction": "Apply mitigations according to vendor guidance.",
        "dueDate": "2026-08-14",
        "knownRansomwareCampaignUse": "Unknown",
        "notes": "https://example.com/security-advisory",
        "cwes": ["CWE-244"],
    }
    record.update(overrides)
    return record


def _build_snapshot(
    *,
    records: tuple[dict[str, object], ...] | None = None,
    snapshot_catalog_version: str = CATALOG_VERSION,
    snapshot_date_released: datetime = DATE_RELEASED,
    snapshot_record_count: int | None = None,
    document_overrides: dict[str, object] | None = None,
) -> KevCatalogSnapshot:
    """Build an in-memory validated-style KEV Bronze snapshot."""
    resolved_records = records if records is not None else (_record(),)

    document: dict[str, object] = {
        "title": "CISA Known Exploited Vulnerabilities Catalog",
        "catalogVersion": CATALOG_VERSION,
        "dateReleased": "2026-08-14T16:34:49.039100Z",
        "count": len(resolved_records),
        "vulnerabilities": list(resolved_records),
    }

    if document_overrides is not None:
        document.update(document_overrides)

    payload = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    return KevCatalogSnapshot(
        raw_bytes=payload,
        catalog_version=snapshot_catalog_version,
        date_released=snapshot_date_released,
        retrieved_at=RETRIEVED_AT,
        sha256=hashlib.sha256(payload).hexdigest(),
        record_count=(
            snapshot_record_count if snapshot_record_count is not None else len(resolved_records)
        ),
    )


def test_transforms_valid_kev_record_and_propagates_provenance() -> None:
    """Transform valid KEV Bronze evidence into a normalized Silver record."""
    snapshot = _build_snapshot()
    transformer = KevSilverTransformer()

    records = list(transformer.iter_records(snapshot))

    assert len(records) == 1

    record = records[0]

    assert record.cve == "CVE-2026-20349"
    assert record.vendor_project == "Cisco"
    assert record.product == "Secure Firewall"
    assert record.date_added.isoformat() == "2026-08-11"
    assert record.due_date.isoformat() == "2026-08-14"
    assert record.cwes == ("CWE-244",)
    assert record.known_ransomware_campaign_use is KevRansomwareUse.UNKNOWN

    assert record.catalog_version == snapshot.catalog_version
    assert record.catalog_date_released == snapshot.date_released
    assert record.source == "cisa-kev"
    assert record.source_sha256 == snapshot.sha256
    assert record.retrieved_at == snapshot.retrieved_at
    assert record.snapshot_date.isoformat() == "2026-08-17"


def test_preserves_source_record_order() -> None:
    """Preserve deterministic vulnerability ordering from the Bronze source."""
    snapshot = _build_snapshot(
        records=(
            _record("CVE-2026-10001"),
            _record("CVE-2026-10002"),
        )
    )

    records = list(KevSilverTransformer().iter_records(snapshot))

    assert [record.cve for record in records] == [
        "CVE-2026-10001",
        "CVE-2026-10002",
    ]


def test_normalizes_outer_whitespace() -> None:
    """Trim source whitespace at field boundaries without rewriting content."""
    snapshot = _build_snapshot(
        records=(
            _record(
                vendorProject=" Cisco ",
                product=" Secure Firewall ",
                vulnerabilityName=" Vulnerability Name ",
                shortDescription=" Description ",
                requiredAction=" Apply mitigation ",
                notes=" https://example.com/advisory ",
                cwes=[" CWE-244 "],
            ),
        )
    )

    record = next(KevSilverTransformer().iter_records(snapshot))

    assert record.vendor_project == "Cisco"
    assert record.product == "Secure Firewall"
    assert record.vulnerability_name == "Vulnerability Name"
    assert record.short_description == "Description"
    assert record.required_action == "Apply mitigation"
    assert record.notes == "https://example.com/advisory"
    assert record.cwes == ("CWE-244",)


def test_accepts_empty_cwe_array() -> None:
    """Represent a source record without CWE assignments as an empty tuple."""
    snapshot = _build_snapshot(records=(_record(cwes=[]),))

    record = next(KevSilverTransformer().iter_records(snapshot))

    assert record.cwes == ()


@pytest.mark.parametrize(
    ("source_value", "expected"),
    [
        ("Known", KevRansomwareUse.KNOWN),
        ("Unknown", KevRansomwareUse.UNKNOWN),
    ],
)
def test_accepts_supported_ransomware_values(
    source_value: str,
    expected: KevRansomwareUse,
) -> None:
    """Preserve the bounded CISA ransomware campaign classification."""
    snapshot = _build_snapshot(
        records=(
            _record(
                knownRansomwareCampaignUse=source_value,
            ),
        )
    )

    record = next(KevSilverTransformer().iter_records(snapshot))

    assert record.known_ransomware_campaign_use is expected


def test_rejects_unknown_ransomware_value() -> None:
    """Fail closed when CISA introduces an unsupported ransomware value."""
    snapshot = _build_snapshot(
        records=(
            _record(
                knownRansomwareCampaignUse="Maybe",
            ),
        )
    )

    with pytest.raises(
        InvalidKevSilverSourceError,
        match=r"Unsupported.*knownRansomwareCampaignUse",
    ):
        list(KevSilverTransformer().iter_records(snapshot))


def test_rejects_invalid_cve() -> None:
    """Reject a vulnerability whose CVE identifier is not canonical."""
    snapshot = _build_snapshot(records=(_record("NOT-A-CVE"),))

    with pytest.raises(
        InvalidKevSilverSourceError,
        match="canonical CVE format",
    ):
        list(KevSilverTransformer().iter_records(snapshot))


def test_rejects_invalid_cwe() -> None:
    """Reject malformed CWE identifiers in the source array."""
    snapshot = _build_snapshot(records=(_record(cwes=["CWE-244", "INVALID-CWE"]),))

    with pytest.raises(
        InvalidKevSilverSourceError,
        match="canonical CWE format",
    ):
        list(KevSilverTransformer().iter_records(snapshot))


@pytest.mark.parametrize(
    "field_name",
    [
        "dateAdded",
        "dueDate",
    ],
)
def test_rejects_invalid_date(field_name: str) -> None:
    """Reject malformed calendar dates in required date fields."""
    snapshot = _build_snapshot(records=(_record(**{field_name: "2026-99-99"}),))

    with pytest.raises(
        InvalidKevSilverSourceError,
        match="invalid ISO date",
    ):
        list(KevSilverTransformer().iter_records(snapshot))


def test_rejects_missing_required_field() -> None:
    """Reject source records that omit a required Silver field."""
    record = _record()
    del record["requiredAction"]

    snapshot = _build_snapshot(records=(record,))

    with pytest.raises(
        InvalidKevSilverSourceError,
        match="missing required fields: requiredAction",
    ):
        list(KevSilverTransformer().iter_records(snapshot))


def test_rejects_wrong_field_type() -> None:
    """Reject source fields whose runtime type violates the Silver contract."""
    snapshot = _build_snapshot(records=(_record(product=123),))

    with pytest.raises(
        InvalidKevSilverSourceError,
        match=r"'product'.*must be a string",
    ):
        list(KevSilverTransformer().iter_records(snapshot))


def test_rejects_duplicate_cves() -> None:
    """Reject multiple KEV records for the same CVE within one snapshot."""
    snapshot = _build_snapshot(
        records=(
            _record("CVE-2026-20349"),
            _record("CVE-2026-20349"),
        )
    )

    with pytest.raises(
        InvalidKevSilverSourceError,
        match=r"duplicate CVE 'CVE-2026-20349'.*record 2",
    ):
        list(KevSilverTransformer().iter_records(snapshot))


def test_rejects_catalog_version_mismatch() -> None:
    """Reject raw catalog metadata inconsistent with Bronze provenance."""
    snapshot = _build_snapshot(
        snapshot_catalog_version="2026.08.13",
    )

    with pytest.raises(
        InvalidKevSilverSourceError,
        match="catalogVersion does not match",
    ):
        list(KevSilverTransformer().iter_records(snapshot))


def test_rejects_catalog_release_timestamp_mismatch() -> None:
    """Reject a source release timestamp inconsistent with Bronze metadata."""
    snapshot = _build_snapshot(
        snapshot_date_released=datetime(
            2026,
            8,
            13,
            16,
            34,
            49,
            tzinfo=UTC,
        ),
    )

    with pytest.raises(
        InvalidKevSilverSourceError,
        match="dateReleased does not match",
    ):
        list(KevSilverTransformer().iter_records(snapshot))


def test_rejects_record_count_mismatch() -> None:
    """Reject catalog counts inconsistent with Bronze snapshot metadata."""
    snapshot = _build_snapshot(
        snapshot_record_count=2,
    )

    with pytest.raises(
        InvalidKevSilverSourceError,
        match="catalog count does not match",
    ):
        list(KevSilverTransformer().iter_records(snapshot))


def test_allows_unknown_additional_source_fields() -> None:
    """Ignore additive source fields that are outside the current Silver contract."""
    snapshot = _build_snapshot(
        records=(
            _record(
                futureCisaField="future-value",
            ),
        )
    )

    records = list(KevSilverTransformer().iter_records(snapshot))

    assert len(records) == 1
    assert records[0].cve == "CVE-2026-20349"
