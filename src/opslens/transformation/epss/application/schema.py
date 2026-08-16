"""Physical schema contract for EPSS Silver datasets."""

from dataclasses import dataclass
from enum import StrEnum


class SilverPhysicalType(StrEnum):
    """Represent storage-neutral physical types used by the Silver contract."""

    STRING = "string"
    FLOAT64 = "float64"
    TIMESTAMP_UTC_MICROS = "timestamp_utc_micros"


@dataclass(frozen=True, slots=True)
class SilverColumn:
    """Describe one physical column stored in an EPSS Silver data file.

    Attributes:
        name: Stable physical column name.
        physical_type: Storage-neutral physical data type.
        nullable: Whether the physical dataset permits null values.
    """

    name: str
    physical_type: SilverPhysicalType
    nullable: bool = False


EPSS_SILVER_SCHEMA_VERSION = 1

EPSS_SILVER_DATA_COLUMNS: tuple[SilverColumn, ...] = (
    SilverColumn("cve", SilverPhysicalType.STRING),
    SilverColumn("epss", SilverPhysicalType.FLOAT64),
    SilverColumn("percentile", SilverPhysicalType.FLOAT64),
    SilverColumn("model_version", SilverPhysicalType.STRING),
    SilverColumn("score_timestamp", SilverPhysicalType.TIMESTAMP_UTC_MICROS),
    SilverColumn("source", SilverPhysicalType.STRING),
    SilverColumn("source_sha256", SilverPhysicalType.STRING),
)

EPSS_SILVER_PARTITION_COLUMNS: tuple[str, ...] = ("snapshot_date",)
