"""Physical schema contract for CISA KEV Silver datasets."""

from dataclasses import dataclass
from enum import StrEnum


class KevSilverPhysicalType(StrEnum):
    """Represent storage-neutral types used by the KEV Silver contract."""

    STRING = "string"
    DATE32 = "date32"
    TIMESTAMP_UTC_MICROS = "timestamp_utc_micros"
    LIST_STRING = "list_string"


@dataclass(frozen=True, slots=True)
class KevSilverColumn:
    """Describe one physical column in a KEV Silver data file.

    Attributes:
        name: Stable physical column name.
        physical_type: Storage-neutral physical type.
        nullable: Whether null values are permitted.
    """

    name: str
    physical_type: KevSilverPhysicalType
    nullable: bool = False


KEV_SILVER_SCHEMA_VERSION = 1

KEV_SILVER_DATA_COLUMNS: tuple[KevSilverColumn, ...] = (
    KevSilverColumn("cve", KevSilverPhysicalType.STRING),
    KevSilverColumn("vendor_project", KevSilverPhysicalType.STRING),
    KevSilverColumn("product", KevSilverPhysicalType.STRING),
    KevSilverColumn("vulnerability_name", KevSilverPhysicalType.STRING),
    KevSilverColumn("date_added", KevSilverPhysicalType.DATE32),
    KevSilverColumn("short_description", KevSilverPhysicalType.STRING),
    KevSilverColumn("required_action", KevSilverPhysicalType.STRING),
    KevSilverColumn("due_date", KevSilverPhysicalType.DATE32),
    KevSilverColumn(
        "known_ransomware_campaign_use",
        KevSilverPhysicalType.STRING,
    ),
    KevSilverColumn("notes", KevSilverPhysicalType.STRING),
    KevSilverColumn("cwes", KevSilverPhysicalType.LIST_STRING),
    KevSilverColumn("catalog_version", KevSilverPhysicalType.STRING),
    KevSilverColumn(
        "catalog_date_released",
        KevSilverPhysicalType.TIMESTAMP_UTC_MICROS,
    ),
    KevSilverColumn("source", KevSilverPhysicalType.STRING),
    KevSilverColumn("source_sha256", KevSilverPhysicalType.STRING),
    KevSilverColumn(
        "retrieved_at",
        KevSilverPhysicalType.TIMESTAMP_UTC_MICROS,
    ),
)

KEV_SILVER_PARTITION_COLUMNS: tuple[str, ...] = ("snapshot_date",)
