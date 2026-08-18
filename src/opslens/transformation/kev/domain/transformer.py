"""Deterministic transformation of CISA KEV Bronze evidence to Silver records."""

import json
from collections.abc import Iterator
from datetime import date, datetime
from typing import cast

from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.transformation.kev.domain.errors import (
    InvalidKevSilverSourceError,
)
from opslens.transformation.kev.domain.models import (
    KevRansomwareUse,
    SilverKevRecord,
)


class KevSilverTransformer:
    """Transform validated CISA KEV Bronze snapshots into Silver records."""

    SOURCE = "cisa-kev"

    REQUIRED_RECORD_FIELDS = frozenset(
        {
            "cveID",
            "vendorProject",
            "product",
            "vulnerabilityName",
            "dateAdded",
            "shortDescription",
            "requiredAction",
            "dueDate",
            "knownRansomwareCampaignUse",
            "notes",
            "cwes",
        }
    )

    def iter_records(
        self,
        snapshot: KevCatalogSnapshot,
    ) -> Iterator[SilverKevRecord]:
        """Yield normalized records from one immutable KEV Bronze snapshot.

        Args:
            snapshot: Validated immutable CISA KEV Bronze observation.

        Yields:
            Normalized KEV Silver records in source order.

        Raises:
            InvalidKevSilverSourceError: If any vulnerability violates the
                Silver source contract.
        """
        document = self._parse_document(snapshot.raw_bytes)
        vulnerabilities = self._validate_catalog(
            document=document,
            snapshot=snapshot,
        )

        seen_cves: set[str] = set()
        emitted_count = 0

        for record_number, value in enumerate(vulnerabilities, start=1):
            record = self._build_record(
                value=value,
                record_number=record_number,
                snapshot=snapshot,
            )

            if record.cve in seen_cves:
                raise InvalidKevSilverSourceError(
                    f"KEV source contains duplicate CVE {record.cve!r} "
                    f"at vulnerability record {record_number}."
                )

            seen_cves.add(record.cve)
            emitted_count += 1
            yield record

        if emitted_count != snapshot.record_count:
            raise InvalidKevSilverSourceError(
                "KEV transformed record count does not match Bronze "
                f"snapshot metadata: expected {snapshot.record_count}, "
                f"emitted {emitted_count}."
            )

    @staticmethod
    def _parse_document(payload: bytes) -> dict[str, object]:
        """Decode the preserved Bronze artifact as a JSON object."""
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidKevSilverSourceError("KEV Bronze payload is not valid UTF-8.") from exc

        try:
            parsed = cast(object, json.loads(text))
        except json.JSONDecodeError as exc:
            raise InvalidKevSilverSourceError("KEV Bronze payload is not valid JSON.") from exc

        if not isinstance(parsed, dict):
            raise InvalidKevSilverSourceError(
                "KEV Bronze payload must contain a top-level JSON object."
            )

        return cast(dict[str, object], parsed)

    def _validate_catalog(
        self,
        *,
        document: dict[str, object],
        snapshot: KevCatalogSnapshot,
    ) -> list[object]:
        """Ensure raw catalog metadata agrees with Bronze snapshot metadata."""
        catalog_version = document.get("catalogVersion")

        if (
            not isinstance(catalog_version, str)
            or catalog_version.strip() != snapshot.catalog_version
        ):
            raise InvalidKevSilverSourceError(
                "KEV catalogVersion does not match Bronze snapshot metadata."
            )

        count = document.get("count")

        if type(count) is not int or count != snapshot.record_count:
            raise InvalidKevSilverSourceError(
                "KEV catalog count does not match Bronze snapshot metadata."
            )

        date_released = document.get("dateReleased")

        if not isinstance(date_released, str):
            raise InvalidKevSilverSourceError("KEV dateReleased must be a string.")

        parsed_date_released = self._parse_datetime(
            date_released,
            field_name="dateReleased",
        )

        if parsed_date_released != snapshot.date_released:
            raise InvalidKevSilverSourceError(
                "KEV dateReleased does not match Bronze snapshot metadata."
            )

        vulnerabilities_value = document.get("vulnerabilities")

        if not isinstance(vulnerabilities_value, list):
            raise InvalidKevSilverSourceError("KEV vulnerabilities must be an array.")

        vulnerabilities = cast(list[object], vulnerabilities_value)

        if len(vulnerabilities) != snapshot.record_count:
            raise InvalidKevSilverSourceError(
                "KEV vulnerability count does not match Bronze snapshot metadata."
            )

        return vulnerabilities

    def _build_record(
        self,
        *,
        value: object,
        record_number: int,
        snapshot: KevCatalogSnapshot,
    ) -> SilverKevRecord:
        """Normalize one source vulnerability into a Silver domain record."""
        if not isinstance(value, dict):
            raise InvalidKevSilverSourceError(
                f"KEV vulnerability record {record_number} must be an object."
            )

        source_record = cast(dict[str, object], value)

        missing_fields = self.REQUIRED_RECORD_FIELDS - source_record.keys()

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise InvalidKevSilverSourceError(
                f"KEV vulnerability record {record_number} is missing required fields: {missing}."
            )

        cve = self._text(source_record, "cveID", record_number)
        cwes = self._cwes(source_record["cwes"], record_number)

        try:
            return SilverKevRecord(
                cve=cve,
                vendor_project=self._text(
                    source_record,
                    "vendorProject",
                    record_number,
                ),
                product=self._text(
                    source_record,
                    "product",
                    record_number,
                ),
                vulnerability_name=self._text(
                    source_record,
                    "vulnerabilityName",
                    record_number,
                ),
                date_added=self._date(
                    source_record,
                    "dateAdded",
                    record_number,
                ),
                short_description=self._text(
                    source_record,
                    "shortDescription",
                    record_number,
                ),
                required_action=self._text(
                    source_record,
                    "requiredAction",
                    record_number,
                ),
                due_date=self._date(
                    source_record,
                    "dueDate",
                    record_number,
                ),
                known_ransomware_campaign_use=self._ransomware_use(
                    source_record["knownRansomwareCampaignUse"],
                    record_number,
                ),
                notes=self._text(
                    source_record,
                    "notes",
                    record_number,
                ),
                cwes=cwes,
                catalog_version=snapshot.catalog_version,
                catalog_date_released=snapshot.date_released,
                source=self.SOURCE,
                source_sha256=snapshot.sha256,
                retrieved_at=snapshot.retrieved_at,
                snapshot_date=date.fromisoformat(snapshot.snapshot_date),
            )
        except ValueError as exc:
            raise InvalidKevSilverSourceError(
                f"Invalid KEV vulnerability record {record_number} ({cve!r}): {exc}"
            ) from exc

    @staticmethod
    def _text(
        record: dict[str, object],
        field_name: str,
        record_number: int,
    ) -> str:
        """Read and trim one required non-empty source string."""
        value = record[field_name]

        if not isinstance(value, str):
            raise InvalidKevSilverSourceError(
                f"KEV field {field_name!r} in record {record_number} must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise InvalidKevSilverSourceError(
                f"KEV field {field_name!r} in record {record_number} cannot be empty."
            )

        return normalized

    @staticmethod
    def _date(
        record: dict[str, object],
        field_name: str,
        record_number: int,
    ) -> date:
        """Parse one required ISO-8601 calendar date."""
        value = record[field_name]

        if not isinstance(value, str):
            raise InvalidKevSilverSourceError(
                f"KEV field {field_name!r} in record {record_number} must be a string."
            )

        try:
            return date.fromisoformat(value.strip())
        except ValueError as exc:
            raise InvalidKevSilverSourceError(
                f"KEV field {field_name!r} in record {record_number} "
                f"contains an invalid ISO date: {value!r}."
            ) from exc

    @staticmethod
    def _ransomware_use(
        value: object,
        record_number: int,
    ) -> KevRansomwareUse:
        """Parse the bounded CISA ransomware campaign classification."""
        if not isinstance(value, str):
            raise InvalidKevSilverSourceError(
                f"KEV knownRansomwareCampaignUse in record {record_number} must be a string."
            )

        try:
            return KevRansomwareUse(value.strip())
        except ValueError as exc:
            raise InvalidKevSilverSourceError(
                "Unsupported KEV knownRansomwareCampaignUse value "
                f"in record {record_number}: {value!r}."
            ) from exc

    @staticmethod
    def _cwes(
        value: object,
        record_number: int,
    ) -> tuple[str, ...]:
        """Normalize the source CWE array while preserving source order."""
        if not isinstance(value, list):
            raise InvalidKevSilverSourceError(
                f"KEV cwes in record {record_number} must be an array."
            )

        normalized: list[str] = []

        for cwe in cast(list[object], value):
            if not isinstance(cwe, str):
                raise InvalidKevSilverSourceError(
                    f"KEV cwes in record {record_number} must contain only strings."
                )

            stripped = cwe.strip()

            if not stripped:
                raise InvalidKevSilverSourceError(
                    f"KEV cwes in record {record_number} cannot contain empty values."
                )

            normalized.append(stripped)

        return tuple(normalized)

    @staticmethod
    def _parse_datetime(
        value: str,
        *,
        field_name: str,
    ) -> datetime:
        """Parse one ISO-8601 timezone-aware timestamp."""
        normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise InvalidKevSilverSourceError(
                f"Invalid KEV {field_name} timestamp: {value!r}."
            ) from exc

        if parsed.tzinfo is None:
            raise InvalidKevSilverSourceError(f"KEV {field_name} must be timezone-aware.")

        return parsed
