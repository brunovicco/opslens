"""Read CVE observations from already-verified NVD Bronze payloads."""

import gzip
import json
from dataclasses import dataclass
from typing import cast

from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectPayloadV1,
    NvdBronzeObjectReferenceV1,
    NvdBronzeObjectRole,
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)


class NvdSilverSourceReadError(RuntimeError):
    """Raised when verified Bronze payloads cannot be read as NVD CVEs."""


@dataclass(frozen=True, slots=True)
class NvdSilverSourceRecordV1:
    """Bind one source CVE to its exact Bronze object occurrence."""

    bronze_object_key: str
    record_index: int
    source_cve: dict[str, object]

    def __post_init__(self) -> None:
        """Validate source-record coordinates."""
        if not self.bronze_object_key.strip():
            raise ValueError("NVD Silver source record object key cannot be empty.")

        if self.record_index < 0:
            raise ValueError("NVD Silver source record index cannot be negative.")


class NvdSilverSourceBatchReaderV1:
    """Extract CVE objects from verified bootstrap or incremental Bronze."""

    def read(
        self,
        *,
        evidence: VerifiedNvdBronzeEvidenceV1,
        object_payloads: tuple[NvdBronzeObjectPayloadV1, ...],
    ) -> tuple[NvdSilverSourceRecordV1, ...]:
        """Read one verified Bronze source batch without establishing trust."""
        payloads = self._payload_inventory(
            evidence=evidence,
            object_payloads=object_payloads,
        )

        if evidence.source_kind is NvdSilverSourceKind.BOOTSTRAP:
            return self._read_bootstrap(
                evidence=evidence,
                payloads=payloads,
            )

        if evidence.source_kind is NvdSilverSourceKind.INCREMENTAL:
            return self._read_incremental(
                evidence=evidence,
                payloads=payloads,
            )

        raise NvdSilverSourceReadError(
            f"Unsupported NVD Silver source kind {evidence.source_kind!r}."
        )

    def _read_bootstrap(
        self,
        *,
        evidence: VerifiedNvdBronzeEvidenceV1,
        payloads: dict[str, NvdBronzeObjectPayloadV1],
    ) -> tuple[NvdSilverSourceRecordV1, ...]:
        """Read CVEs from one verified yearly-feed gzip object."""
        feed_references = tuple(
            reference
            for reference in evidence.objects
            if reference.role is NvdBronzeObjectRole.FEED
        )

        if len(feed_references) != 1:
            raise NvdSilverSourceReadError(
                "Verified bootstrap evidence must contain exactly one feed object."
            )

        feed_reference = feed_references[0]
        feed_payload = payloads[feed_reference.key]

        try:
            source_bytes = gzip.decompress(feed_payload.raw_bytes)
        except (OSError, EOFError) as exc:
            raise NvdSilverSourceReadError(
                "Verified NVD bootstrap feed is not valid gzip."
            ) from exc

        return self._records_from_json(
            raw_bytes=source_bytes,
            bronze_object_key=feed_reference.key,
        )

    def _read_incremental(
        self,
        *,
        evidence: VerifiedNvdBronzeEvidenceV1,
        payloads: dict[str, NvdBronzeObjectPayloadV1],
    ) -> tuple[NvdSilverSourceRecordV1, ...]:
        """Read CVEs from ordered verified incremental page objects."""
        total_results = evidence.incremental_total_results

        if type(total_results) is not int or total_results < 0:
            raise NvdSilverSourceReadError(
                "Verified incremental evidence lacks valid total_results."
            )

        records: list[NvdSilverSourceRecordV1] = []
        references = evidence.objects

        for reference_index, reference in enumerate(references):
            if reference.role is not NvdBronzeObjectRole.PAGE:
                raise NvdSilverSourceReadError(
                    "Verified incremental evidence may contain only page objects."
                )

            page_start = reference.page_start

            if page_start is None:
                raise NvdSilverSourceReadError("Verified incremental page lacks page_start.")

            page_records = self._records_from_json(
                raw_bytes=payloads[reference.key].raw_bytes,
                bronze_object_key=reference.key,
            )

            expected_count = self._expected_incremental_page_count(
                references=references,
                reference_index=reference_index,
                page_start=page_start,
                total_results=total_results,
            )

            if len(page_records) != expected_count:
                raise NvdSilverSourceReadError(
                    "NVD incremental page CVE count does not match "
                    "verified Bronze pagination evidence."
                )

            records.extend(page_records)

        if len(records) != total_results:
            raise NvdSilverSourceReadError(
                "NVD incremental source record count does not match verified Bronze total_results."
            )

        return tuple(records)

    @staticmethod
    def _expected_incremental_page_count(
        *,
        references: tuple[NvdBronzeObjectReferenceV1, ...],
        reference_index: int,
        page_start: int,
        total_results: int,
    ) -> int:
        """Derive one page cardinality from verified contiguous page starts."""
        next_index = reference_index + 1

        if next_index < len(references):
            next_start = references[next_index].page_start

            if next_start is None or next_start < page_start:
                raise NvdSilverSourceReadError("Verified incremental page ordering is invalid.")

            return next_start - page_start

        if total_results < page_start:
            raise NvdSilverSourceReadError("Verified incremental final page exceeds total_results.")

        return total_results - page_start

    @staticmethod
    def _payload_inventory(
        *,
        evidence: VerifiedNvdBronzeEvidenceV1,
        object_payloads: tuple[NvdBronzeObjectPayloadV1, ...],
    ) -> dict[str, NvdBronzeObjectPayloadV1]:
        """Resolve the exact payload inventory already accepted by the verifier."""
        payloads: dict[str, NvdBronzeObjectPayloadV1] = {}

        for payload in object_payloads:
            if payload.key in payloads:
                raise NvdSilverSourceReadError(
                    "Duplicate NVD Bronze payload supplied to source reader."
                )

            payloads[payload.key] = payload

        expected_keys = {reference.key for reference in evidence.objects}

        if set(payloads) != expected_keys:
            raise NvdSilverSourceReadError(
                "NVD Silver source reader payload inventory "
                "does not match verified Bronze evidence."
            )

        for reference in evidence.objects:
            payload = payloads[reference.key]

            if payload.version_id != reference.version_id:
                raise NvdSilverSourceReadError(
                    "NVD Silver source reader payload VersionId "
                    "does not match verified Bronze evidence."
                )

        return payloads

    @classmethod
    def _records_from_json(
        cls,
        *,
        raw_bytes: bytes,
        bronze_object_key: str,
    ) -> tuple[NvdSilverSourceRecordV1, ...]:
        """Extract wrapped CVE objects from one NVD JSON 2.0 payload."""
        document = cls._parse_json(raw_bytes)

        vulnerabilities_value = document.get("vulnerabilities")

        if not isinstance(vulnerabilities_value, list):
            raise NvdSilverSourceReadError("NVD source payload vulnerabilities must be an array.")

        vulnerabilities = cast(
            list[object],
            vulnerabilities_value,
        )

        records: list[NvdSilverSourceRecordV1] = []

        for record_index, vulnerability_value in enumerate(vulnerabilities):
            if not isinstance(vulnerability_value, dict):
                raise NvdSilverSourceReadError("NVD vulnerability entry must be an object.")

            vulnerability = cast(
                dict[str, object],
                vulnerability_value,
            )

            cve_value = vulnerability.get("cve")

            if not isinstance(cve_value, dict):
                raise NvdSilverSourceReadError("NVD vulnerability entry must contain a CVE object.")

            source_cve = cast(
                dict[str, object],
                cve_value,
            )

            records.append(
                NvdSilverSourceRecordV1(
                    bronze_object_key=bronze_object_key,
                    record_index=record_index,
                    source_cve=source_cve,
                )
            )

        return tuple(records)

    @staticmethod
    def _parse_json(
        raw_bytes: bytes,
    ) -> dict[str, object]:
        """Decode one NVD JSON payload and require a top-level object."""
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise NvdSilverSourceReadError("NVD source payload must be UTF-8.") from exc

        try:
            parsed = cast(
                object,
                json.loads(text),
            )
        except json.JSONDecodeError as exc:
            raise NvdSilverSourceReadError("NVD source payload contains invalid JSON.") from exc

        if not isinstance(parsed, dict):
            raise NvdSilverSourceReadError("NVD source payload must contain a JSON object.")

        return cast(
            dict[str, object],
            parsed,
        )
