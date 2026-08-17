"""Parser and minimum-contract validator for CISA KEV JSON catalogs."""

import hashlib
import json
from datetime import datetime
from typing import cast

from opslens.ingestion.kev.domain.errors import InvalidKevCatalogError
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot


class KevCatalogParser:
    """Parse raw CISA KEV JSON while preserving the original Bronze artifact."""

    REQUIRED_TOP_LEVEL_FIELDS = frozenset(
        {
            "catalogVersion",
            "dateReleased",
            "count",
            "vulnerabilities",
        }
    )

    def parse(
        self,
        payload: bytes,
        retrieved_at: datetime,
    ) -> KevCatalogSnapshot:
        """Parse source bytes into a validated KEV catalog observation.

        Bronze validation intentionally checks only the minimum source
        contract. Detailed vulnerability-level validation belongs to the
        Silver transformation.

        Args:
            payload: Original JSON bytes received from CISA.
            retrieved_at: Time when OpsLens observed the source artifact.

        Returns:
            Validated immutable KEV catalog snapshot.

        Raises:
            InvalidKevCatalogError: If the artifact violates the minimum
                Bronze source contract.
        """
        if not payload:
            raise InvalidKevCatalogError("KEV catalog payload is empty.")

        if retrieved_at.tzinfo is None:
            raise InvalidKevCatalogError("KEV retrieved_at must be timezone-aware.")

        document = self._parse_json(payload)

        missing_fields = self.REQUIRED_TOP_LEVEL_FIELDS - document.keys()

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise InvalidKevCatalogError(
                f"KEV catalog is missing required top-level fields: {missing}."
            )

        catalog_version = document["catalogVersion"]

        if not isinstance(catalog_version, str) or not catalog_version.strip():
            raise InvalidKevCatalogError(
                "KEV catalogVersion must be a non-empty string."
            )

        date_released_raw = document["dateReleased"]

        if not isinstance(date_released_raw, str):
            raise InvalidKevCatalogError("KEV dateReleased must be a string.")

        date_released = self._parse_datetime(date_released_raw)

        count = document["count"]

        if type(count) is not int or count <= 0:
            raise InvalidKevCatalogError("KEV count must be a positive integer.")

        vulnerabilities_value = document["vulnerabilities"]

        if not isinstance(vulnerabilities_value, list):
            raise InvalidKevCatalogError(
                "KEV vulnerabilities must be an array."
            )

        vulnerabilities = cast(list[object], vulnerabilities_value)

        if count != len(vulnerabilities):
            raise InvalidKevCatalogError(
                "KEV count does not match the number of vulnerabilities."
            )

        return KevCatalogSnapshot(
            raw_bytes=payload,
            catalog_version=catalog_version.strip(),
            date_released=date_released,
            retrieved_at=retrieved_at,
            sha256=hashlib.sha256(payload).hexdigest(),
            record_count=count,
        )

    @staticmethod
    def _parse_json(payload: bytes) -> dict[str, object]:
        """Decode UTF-8 JSON and require a top-level object."""
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidKevCatalogError(
                "KEV catalog payload is not valid UTF-8."
            ) from exc

        try:
            parsed = cast(object, json.loads(text))
        except json.JSONDecodeError as exc:
            raise InvalidKevCatalogError(
                "KEV catalog payload is not valid JSON."
            ) from exc

        if not isinstance(parsed, dict):
            raise InvalidKevCatalogError(
                "KEV catalog top-level JSON value must be an object."
            )

        return cast(dict[str, object], parsed)

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        """Parse an ISO-8601 source timestamp as timezone-aware datetime."""
        normalized_value = (
            f"{value[:-1]}+00:00"
            if value.endswith("Z")
            else value
        )

        try:
            parsed = datetime.fromisoformat(normalized_value)
        except ValueError as exc:
            raise InvalidKevCatalogError(
                f"Invalid KEV dateReleased value: '{value}'."
            ) from exc

        if parsed.tzinfo is None:
            raise InvalidKevCatalogError(
                "KEV dateReleased must include timezone information."
            )

        return parsed
