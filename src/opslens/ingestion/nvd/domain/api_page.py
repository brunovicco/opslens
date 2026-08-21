"""Contracts for deterministic NVD CVE API pages and pagination."""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import cast

from opslens.ingestion.nvd.domain.errors import (
    InvalidNvdCveApiPageError,
    InvalidNvdCveApiPaginationError,
)

_CVE_ID_PATTERN = re.compile(r"^CVE-[0-9]{4}-[0-9]{4,}$")

MAX_RESULTS_PER_PAGE = 2_000


@dataclass(frozen=True, slots=True)
class NvdCveApiPage:
    """Represent one validated immutable NVD CVE API response page.

    Attributes:
        raw_bytes: Exact UTF-8 JSON bytes received from NVD.
        sha256: SHA-256 calculated over the exact response bytes.
        results_per_page: Number of CVE records contained in this page.
        start_index: Zero-based source pagination index.
        total_results: Total result count declared by NVD for the query.
        source_format: NVD response format identifier.
        source_version: NVD response schema/API version identifier.
        source_timestamp: Source response timestamp preserved as supplied.
        cve_ids: Canonical CVE identifiers observed in this page.
    """

    raw_bytes: bytes
    sha256: str
    results_per_page: int
    start_index: int
    total_results: int
    source_format: str
    source_version: str
    source_timestamp: str
    cve_ids: tuple[str, ...]

    @property
    def next_start_index(self) -> int:
        """Return the next contiguous source pagination index."""
        return self.start_index + self.results_per_page

    @property
    def is_final_page(self) -> bool:
        """Return whether this page reaches the declared result boundary."""
        return self.next_start_index == self.total_results


class NvdCveApiPageParser:
    """Parse and validate the minimum NVD CVE API Bronze page contract."""

    REQUIRED_TOP_LEVEL_FIELDS = frozenset(
        {
            "resultsPerPage",
            "startIndex",
            "totalResults",
            "format",
            "version",
            "timestamp",
            "vulnerabilities",
        }
    )

    def parse(self, payload: bytes) -> NvdCveApiPage:
        """Parse exact NVD CVE API response bytes.

        Validation intentionally covers pagination metadata and required
        vulnerability identity only. Detailed CVSS, CWE, CPE, and record-level
        semantic normalization belongs to later Silver processing.

        Args:
            payload: Exact JSON response bytes received from NVD.

        Returns:
            Validated immutable API page.

        Raises:
            InvalidNvdCveApiPageError: If the response violates the minimum
                incremental Bronze contract.
        """
        if not payload:
            raise InvalidNvdCveApiPageError("NVD CVE API payload is empty.")

        document = self._parse_json(payload)

        missing_fields = self.REQUIRED_TOP_LEVEL_FIELDS - document.keys()

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise InvalidNvdCveApiPageError(
                f"NVD CVE API response is missing required top-level fields: {missing}."
            )

        results_per_page = self._require_integer(
            document,
            "resultsPerPage",
        )
        start_index = self._require_integer(
            document,
            "startIndex",
        )
        total_results = self._require_integer(
            document,
            "totalResults",
        )

        if results_per_page > MAX_RESULTS_PER_PAGE:
            raise InvalidNvdCveApiPageError("NVD CVE API resultsPerPage must not exceed 2000.")

        source_format = self._require_string(
            document,
            "format",
        )
        source_version = self._require_string(
            document,
            "version",
        )
        source_timestamp = self._require_string(
            document,
            "timestamp",
        )

        if source_format != "NVD_CVE":
            raise InvalidNvdCveApiPageError("NVD CVE API format must be 'NVD_CVE'.")

        if source_version != "2.0":
            raise InvalidNvdCveApiPageError("NVD CVE API version must be '2.0'.")

        vulnerabilities_value = document["vulnerabilities"]

        if not isinstance(
            vulnerabilities_value,
            list,
        ):
            raise InvalidNvdCveApiPageError("NVD CVE API vulnerabilities must be an array.")

        vulnerabilities = cast(
            list[object],
            vulnerabilities_value,
        )

        if len(vulnerabilities) != results_per_page:
            raise InvalidNvdCveApiPageError(
                "NVD CVE API resultsPerPage does not match the number of vulnerabilities."
            )

        self._validate_page_bounds(
            results_per_page=results_per_page,
            start_index=start_index,
            total_results=total_results,
        )

        cve_ids = tuple(self._extract_cve_id(vulnerability) for vulnerability in vulnerabilities)

        if len(set(cve_ids)) != len(cve_ids):
            raise InvalidNvdCveApiPageError("NVD CVE API page contains duplicate CVE identifiers.")

        return NvdCveApiPage(
            raw_bytes=payload,
            sha256=hashlib.sha256(payload).hexdigest(),
            results_per_page=results_per_page,
            start_index=start_index,
            total_results=total_results,
            source_format=source_format,
            source_version=source_version,
            source_timestamp=source_timestamp,
            cve_ids=cve_ids,
        )

    @staticmethod
    def _parse_json(
        payload: bytes,
    ) -> dict[str, object]:
        """Decode UTF-8 JSON and require a top-level object."""
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidNvdCveApiPageError("NVD CVE API payload is not valid UTF-8.") from exc

        try:
            parsed = cast(
                object,
                json.loads(text),
            )
        except json.JSONDecodeError as exc:
            raise InvalidNvdCveApiPageError("NVD CVE API payload is not valid JSON.") from exc

        if not isinstance(parsed, dict):
            raise InvalidNvdCveApiPageError("NVD CVE API top-level JSON value must be an object.")

        return cast(
            dict[str, object],
            parsed,
        )

    @staticmethod
    def _require_integer(
        document: dict[str, object],
        field_name: str,
    ) -> int:
        """Read one required non-negative integer response field."""
        value = document[field_name]

        if type(value) is not int:
            raise InvalidNvdCveApiPageError(f"NVD CVE API {field_name} must be an integer.")

        if value < 0:
            raise InvalidNvdCveApiPageError(f"NVD CVE API {field_name} must not be negative.")

        return value

    @staticmethod
    def _require_string(
        document: dict[str, object],
        field_name: str,
    ) -> str:
        """Read one required non-empty string response field."""
        value = document[field_name]

        if not isinstance(value, str):
            raise InvalidNvdCveApiPageError(f"NVD CVE API {field_name} must be a string.")

        normalized = value.strip()

        if not normalized:
            raise InvalidNvdCveApiPageError(f"NVD CVE API {field_name} must not be empty.")

        return normalized

    @staticmethod
    def _validate_page_bounds(
        *,
        results_per_page: int,
        start_index: int,
        total_results: int,
    ) -> None:
        """Validate one page against its declared result boundary."""
        if total_results == 0:
            if start_index != 0 or results_per_page != 0:
                raise InvalidNvdCveApiPageError(
                    "An empty NVD CVE API result must use startIndex=0 and resultsPerPage=0."
                )

            return

        if results_per_page == 0:
            raise InvalidNvdCveApiPageError(
                "A non-empty NVD CVE API result cannot contain an empty page."
            )

        if start_index >= total_results:
            raise InvalidNvdCveApiPageError("NVD CVE API startIndex must be below totalResults.")

        if start_index + results_per_page > total_results:
            raise InvalidNvdCveApiPageError("NVD CVE API page exceeds totalResults.")

    @staticmethod
    def _extract_cve_id(
        vulnerability: object,
    ) -> str:
        """Extract and validate one required CVE identifier."""
        if not isinstance(
            vulnerability,
            dict,
        ):
            raise InvalidNvdCveApiPageError("NVD CVE API vulnerability entry must be an object.")

        vulnerability_document = cast(
            dict[str, object],
            vulnerability,
        )

        cve_value = vulnerability_document.get("cve")

        if not isinstance(
            cve_value,
            dict,
        ):
            raise InvalidNvdCveApiPageError("NVD CVE API vulnerability must contain a CVE object.")

        cve_document = cast(
            dict[str, object],
            cve_value,
        )
        cve_id = cve_document.get("id")

        if not isinstance(cve_id, str):
            raise InvalidNvdCveApiPageError("NVD CVE API CVE id must be a string.")

        if not _CVE_ID_PATTERN.fullmatch(cve_id):
            raise InvalidNvdCveApiPageError(f"Invalid NVD CVE identifier: '{cve_id}'.")

        return cve_id


@dataclass(frozen=True, slots=True)
class NvdCveApiPagination:
    """Represent one complete deterministic NVD CVE API page sequence."""

    pages: tuple[NvdCveApiPage, ...]

    def __post_init__(self) -> None:
        """Validate completeness and cross-page consistency."""
        if not self.pages:
            raise InvalidNvdCveApiPaginationError(
                "NVD CVE API pagination must contain at least one page."
            )

        first_page = self.pages[0]

        if first_page.total_results == 0 and len(self.pages) != 1:
            raise InvalidNvdCveApiPaginationError(
                "An empty NVD CVE API result must contain exactly one page."
            )

        expected_start_index = 0
        expected_total_results = first_page.total_results
        seen_cve_ids: set[str] = set()

        for page in self.pages:
            if page.total_results != expected_total_results:
                raise InvalidNvdCveApiPaginationError(
                    "NVD CVE API totalResults changed between pages."
                )

            if page.start_index != expected_start_index:
                raise InvalidNvdCveApiPaginationError(
                    "NVD CVE API pagination contains a gap, overlap, or out-of-order page."
                )

            duplicate_ids = seen_cve_ids.intersection(page.cve_ids)

            if duplicate_ids:
                duplicates = ", ".join(sorted(duplicate_ids))
                raise InvalidNvdCveApiPaginationError(
                    f"NVD CVE API pagination contains duplicate CVE identifiers: {duplicates}."
                )

            seen_cve_ids.update(page.cve_ids)
            expected_start_index = page.next_start_index

        if expected_start_index != expected_total_results:
            raise InvalidNvdCveApiPaginationError("NVD CVE API pagination is incomplete.")

    @property
    def total_results(self) -> int:
        """Return the validated total number of CVE records."""
        return self.pages[0].total_results

    @property
    def page_count(self) -> int:
        """Return the number of validated pages."""
        return len(self.pages)

    @property
    def cve_ids(self) -> tuple[str, ...]:
        """Return all CVE identifiers in source pagination order."""
        return tuple(cve_id for page in self.pages for cve_id in page.cve_ids)
