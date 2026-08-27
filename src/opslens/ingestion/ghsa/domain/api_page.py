"""Validated GitHub advisory REST pages and cursor-pagination contracts."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar, cast
from urllib.parse import parse_qsl, urlencode, urlsplit

from opslens.ingestion.ghsa.domain.errors import (
    InvalidGhsaApiPageError,
    InvalidGhsaPaginationError,
    InvalidGhsaRequestUrlError,
)
from opslens.ingestion.ghsa.domain.sync import (
    GhsaSyncMode,
    GhsaSyncWindow,
)

_GHSA_PATTERN = re.compile(r"^GHSA(?:-[23456789cfghjmpqrvwx]{4}){3}$")
_CURSOR_KEYS = frozenset({"after", "before"})


class GhsaRequestUrlPolicy:
    """Build and validate the allowlisted GitHub advisory collection URL."""

    SCHEME: ClassVar[str] = "https"
    HOST: ClassVar[str] = "api.github.com"
    PATH: ClassVar[str] = "/advisories"

    @classmethod
    def build_initial(cls, window: GhsaSyncWindow) -> str:
        """Build the deterministic first request URL for one logical window."""
        query = urlencode(
            [
                ("type", window.ADVISORY_TYPE),
                (window.mode.value, window.filter_expression),
                ("sort", window.SORT_FIELD),
                ("direction", window.DIRECTION),
                ("per_page", str(window.PER_PAGE)),
            ]
        )
        return f"{cls.SCHEME}://{cls.HOST}{cls.PATH}?{query}"

    @classmethod
    def validate(
        cls,
        url: str,
        *,
        window: GhsaSyncWindow,
        require_cursor: bool | None = None,
    ) -> None:
        """Reject pagination URLs outside the exact source-query allowlist."""
        if not url.strip():
            raise InvalidGhsaRequestUrlError("GHSA request URL cannot be empty.")

        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError as exc:
            raise InvalidGhsaRequestUrlError("GHSA request URL is malformed.") from exc

        if parsed.scheme != cls.SCHEME:
            raise InvalidGhsaRequestUrlError("GHSA request URL must use HTTPS.")

        if parsed.hostname != cls.HOST:
            raise InvalidGhsaRequestUrlError(
                "GHSA request URL host must be api.github.com."
            )

        if port not in (None, 443):
            raise InvalidGhsaRequestUrlError(
                "GHSA request URL cannot use a non-HTTPS port."
            )

        if parsed.username is not None or parsed.password is not None:
            raise InvalidGhsaRequestUrlError(
                "GHSA request URL cannot contain user information."
            )

        if parsed.path != cls.PATH:
            raise InvalidGhsaRequestUrlError(
                "GHSA request URL path must be /advisories."
            )

        if parsed.fragment:
            raise InvalidGhsaRequestUrlError(
                "GHSA request URL cannot contain a fragment."
            )

        pairs = parse_qsl(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
        )
        keys = tuple(key for key, _value in pairs)

        if len(keys) != len(set(keys)):
            raise InvalidGhsaRequestUrlError(
                "GHSA request URL cannot contain duplicate query parameters."
            )

        query = dict(pairs)
        expected: dict[str, str] = {
            "type": window.ADVISORY_TYPE,
            window.mode.value: window.filter_expression,
            "sort": window.SORT_FIELD,
            "direction": window.DIRECTION,
            "per_page": str(window.PER_PAGE),
        }
        allowed_keys = set(expected) | set(_CURSOR_KEYS)

        if set(query) - allowed_keys:
            raise InvalidGhsaRequestUrlError(
                "GHSA request URL contains an unsupported query parameter."
            )

        other_mode = (
            GhsaSyncMode.MODIFIED.value
            if window.mode is GhsaSyncMode.PUBLISHED
            else GhsaSyncMode.PUBLISHED.value
        )

        if other_mode in query:
            raise InvalidGhsaRequestUrlError(
                "GHSA request URL cannot mix synchronization filters."
            )

        for key, expected_value in expected.items():
            if query.get(key) != expected_value:
                raise InvalidGhsaRequestUrlError(
                    f"GHSA request URL parameter {key!r} violates the source contract."
                )

        cursor_keys = tuple(key for key in _CURSOR_KEYS if key in query)

        if len(cursor_keys) > 1:
            raise InvalidGhsaRequestUrlError(
                "GHSA request URL cannot contain both before and after cursors."
            )

        if cursor_keys and not query[cursor_keys[0]]:
            raise InvalidGhsaRequestUrlError(
                "GHSA pagination cursor cannot be empty."
            )

        if require_cursor is True and len(cursor_keys) != 1:
            raise InvalidGhsaRequestUrlError(
                "GHSA continuation URL must contain exactly one cursor."
            )

        if require_cursor is False and cursor_keys:
            raise InvalidGhsaRequestUrlError(
                "GHSA first request URL cannot contain a cursor."
            )


class GhsaLinkHeaderParser:
    """Extract one exact allowlisted `rel=next` continuation URL."""

    @classmethod
    def next_url(
        cls,
        link_header: str | None,
        *,
        window: GhsaSyncWindow,
    ) -> str | None:
        """Return the exact next URL or None when pagination is complete."""
        if link_header is None:
            return None

        if not link_header.strip():
            raise InvalidGhsaApiPageError(
                "GHSA Link header cannot be empty when present."
            )

        next_urls: list[str] = []

        for raw_entry in link_header.split(","):
            parts = [part.strip() for part in raw_entry.strip().split(";")]

            if not parts or not parts[0].startswith("<") or not parts[0].endswith(">"):
                raise InvalidGhsaApiPageError("GHSA Link header entry is malformed.")

            target = parts[0][1:-1]
            rel_tokens: set[str] = set()

            for parameter in parts[1:]:
                name, separator, value = parameter.partition("=")

                if not separator or not name.strip() or not value.strip():
                    raise InvalidGhsaApiPageError(
                        "GHSA Link header parameter is malformed."
                    )

                if name.strip().lower() != "rel":
                    continue

                normalized = value.strip().strip('"')
                rel_tokens.update(normalized.split())

            if "next" in rel_tokens:
                next_urls.append(target)

        if len(next_urls) > 1:
            raise InvalidGhsaApiPageError(
                "GHSA Link header contains multiple rel=next URLs."
            )

        if not next_urls:
            return None

        next_url = next_urls[0]

        try:
            GhsaRequestUrlPolicy.validate(
                next_url,
                window=window,
                require_cursor=True,
            )
        except InvalidGhsaRequestUrlError as exc:
            raise InvalidGhsaApiPageError(
                f"Invalid GHSA rel=next URL: {exc}"
            ) from exc

        return next_url


@dataclass(frozen=True, slots=True)
class GhsaAdvisoryApiPage:
    """Represent one validated immutable GitHub advisory REST response page."""

    raw_bytes: bytes
    sha256: str
    request_url: str
    next_url: str | None
    ghsa_ids: tuple[str, ...]
    published_at: tuple[datetime, ...]
    updated_at: tuple[datetime, ...]

    @property
    def item_count(self) -> int:
        """Return the number of advisories in the exact page."""
        return len(self.ghsa_ids)

    @property
    def size_bytes(self) -> int:
        """Return the exact response body size."""
        return len(self.raw_bytes)


class GhsaAdvisoryApiPageParser:
    """Parse and validate the minimum GHSA Bronze response-page contract."""

    MAX_PAGE_BYTES: ClassVar[int] = 8 * 1024 * 1024

    def parse(
        self,
        payload: bytes,
        *,
        request_url: str,
        link_header: str | None,
        window: GhsaSyncWindow,
    ) -> GhsaAdvisoryApiPage:
        """Validate exact response bytes plus pagination continuation evidence."""
        if not payload:
            raise InvalidGhsaApiPageError("GHSA API payload is empty.")

        if len(payload) > self.MAX_PAGE_BYTES:
            raise InvalidGhsaApiPageError(
                "GHSA API payload exceeds the 8 MiB per-page safety cap."
            )

        try:
            GhsaRequestUrlPolicy.validate(
                request_url,
                window=window,
                require_cursor=None,
            )
        except InvalidGhsaRequestUrlError as exc:
            raise InvalidGhsaApiPageError(
                f"Invalid GHSA request URL: {exc}"
            ) from exc

        items = self._parse_json_array(payload)

        if len(items) > window.PER_PAGE:
            raise InvalidGhsaApiPageError(
                "GHSA API page exceeds the requested per_page limit."
            )

        ghsa_ids: list[str] = []
        published_values: list[datetime] = []
        updated_values: list[datetime] = []

        for index, item in enumerate(items):
            document = self._require_object(item, index=index)
            ghsa_id = self._required_text(document, "ghsa_id", index=index)

            if _GHSA_PATTERN.fullmatch(ghsa_id) is None:
                raise InvalidGhsaApiPageError(
                    f"GHSA API item[{index}] contains an invalid ghsa_id."
                )

            advisory_type = self._required_text(document, "type", index=index)

            if advisory_type != window.ADVISORY_TYPE:
                raise InvalidGhsaApiPageError(
                    f"GHSA API item[{index}] is outside the reviewed-only scope."
                )

            published_at = self._source_timestamp(
                document,
                "published_at",
                index=index,
            )
            updated_at = self._source_timestamp(
                document,
                "updated_at",
                index=index,
            )

            self._validate_window_membership(
                window=window,
                published_at=published_at,
                updated_at=updated_at,
                index=index,
            )

            ghsa_ids.append(ghsa_id)
            published_values.append(published_at)
            updated_values.append(updated_at)

        if len(ghsa_ids) != len(set(ghsa_ids)):
            raise InvalidGhsaApiPageError(
                "GHSA API page contains duplicate advisory identifiers."
            )

        if published_values != sorted(published_values):
            raise InvalidGhsaApiPageError(
                "GHSA API page violates sort=published,direction=asc."
            )

        next_url = GhsaLinkHeaderParser.next_url(
            link_header,
            window=window,
        )

        if next_url is not None and not items:
            raise InvalidGhsaApiPageError(
                "An empty GHSA page cannot advertise a continuation cursor."
            )

        return GhsaAdvisoryApiPage(
            raw_bytes=payload,
            sha256=hashlib.sha256(payload).hexdigest(),
            request_url=request_url,
            next_url=next_url,
            ghsa_ids=tuple(ghsa_ids),
            published_at=tuple(published_values),
            updated_at=tuple(updated_values),
        )

    @staticmethod
    def _parse_json_array(payload: bytes) -> list[object]:
        """Decode one UTF-8 top-level JSON array."""
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidGhsaApiPageError(
                "GHSA API payload is not valid UTF-8."
            ) from exc

        try:
            parsed = cast(object, json.loads(text))
        except json.JSONDecodeError as exc:
            raise InvalidGhsaApiPageError(
                "GHSA API payload is not valid JSON."
            ) from exc

        if not isinstance(parsed, list):
            raise InvalidGhsaApiPageError(
                "GHSA API top-level JSON value must be an array."
            )

        return cast(list[object], parsed)

    @staticmethod
    def _require_object(value: object, *, index: int) -> dict[str, object]:
        """Require one advisory entry object."""
        if not isinstance(value, dict):
            raise InvalidGhsaApiPageError(
                f"GHSA API item[{index}] must be an object."
            )

        return cast(dict[str, object], value)

    @staticmethod
    def _required_text(
        document: dict[str, object],
        field_name: str,
        *,
        index: int,
    ) -> str:
        """Read one required non-empty advisory string."""
        value = document.get(field_name)

        if not isinstance(value, str) or not value.strip():
            raise InvalidGhsaApiPageError(
                f"GHSA API item[{index}].{field_name} must be a non-empty string."
            )

        return value

    @classmethod
    def _source_timestamp(
        cls,
        document: dict[str, object],
        field_name: str,
        *,
        index: int,
    ) -> datetime:
        """Parse one required timezone-aware UTC source timestamp."""
        value = cls._required_text(document, field_name, index=index)

        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise InvalidGhsaApiPageError(
                f"GHSA API item[{index}].{field_name} is not ISO-8601."
            ) from exc

        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise InvalidGhsaApiPageError(
                f"GHSA API item[{index}].{field_name} must be timezone-aware."
            )

        offset = parsed.utcoffset()

        if offset is None or offset.total_seconds() != 0:
            raise InvalidGhsaApiPageError(
                f"GHSA API item[{index}].{field_name} must be UTC."
            )

        return parsed.astimezone(UTC)

    @staticmethod
    def _validate_window_membership(
        *,
        window: GhsaSyncWindow,
        published_at: datetime,
        updated_at: datetime,
        index: int,
    ) -> None:
        """Require source timestamps to satisfy the selected GitHub filter."""
        published_matches = window.start_at <= published_at <= window.end_at
        updated_matches = window.start_at <= updated_at <= window.end_at

        if window.mode is GhsaSyncMode.PUBLISHED:
            if not published_matches:
                raise InvalidGhsaApiPageError(
                    f"GHSA API item[{index}] is outside the published window."
                )
            return

        if not (published_matches or updated_matches):
            raise InvalidGhsaApiPageError(
                f"GHSA API item[{index}] is outside the modified window."
            )


@dataclass(frozen=True, slots=True)
class GhsaAdvisoryPagination:
    """Represent one complete bounded exact GitHub cursor-page sequence."""

    MAX_PAGES: ClassVar[int] = 64
    MAX_TOTAL_BYTES: ClassVar[int] = 64 * 1024 * 1024

    window: GhsaSyncWindow
    pages: tuple[GhsaAdvisoryApiPage, ...]

    def __post_init__(self) -> None:
        """Validate exact continuation, uniqueness, ordering, and safety caps."""
        if not self.pages:
            raise InvalidGhsaPaginationError(
                "GHSA pagination must contain at least one response page."
            )

        if len(self.pages) > self.MAX_PAGES:
            raise InvalidGhsaPaginationError(
                "GHSA pagination exceeds the 64-page safety cap."
            )

        total_bytes = sum(page.size_bytes for page in self.pages)

        if total_bytes > self.MAX_TOTAL_BYTES:
            raise InvalidGhsaPaginationError(
                "GHSA pagination exceeds the 64 MiB safety cap."
            )

        initial_url = GhsaRequestUrlPolicy.build_initial(self.window)

        if self.pages[0].request_url != initial_url:
            raise InvalidGhsaPaginationError(
                "GHSA pagination does not start from the deterministic initial URL."
            )

        seen_request_urls: set[str] = set()
        seen_ghsa_ids: set[str] = set()
        previous_published_at: datetime | None = None

        for index, page in enumerate(self.pages):
            try:
                GhsaRequestUrlPolicy.validate(
                    page.request_url,
                    window=self.window,
                    require_cursor=index > 0,
                )
            except InvalidGhsaRequestUrlError as exc:
                raise InvalidGhsaPaginationError(
                    f"Invalid GHSA pagination request URL: {exc}"
                ) from exc

            if page.request_url in seen_request_urls:
                raise InvalidGhsaPaginationError(
                    "GHSA pagination contains a cursor loop."
                )
            seen_request_urls.add(page.request_url)

            duplicate_ids = seen_ghsa_ids.intersection(page.ghsa_ids)

            if duplicate_ids:
                duplicates = ", ".join(sorted(duplicate_ids))
                raise InvalidGhsaPaginationError(
                    f"GHSA pagination contains duplicate advisory identifiers: {duplicates}."
                )
            seen_ghsa_ids.update(page.ghsa_ids)

            if page.published_at:
                first_published_at = page.published_at[0]

                if (
                    previous_published_at is not None
                    and first_published_at < previous_published_at
                ):
                    raise InvalidGhsaPaginationError(
                        "GHSA pagination violates cross-page published ordering."
                    )

                previous_published_at = page.published_at[-1]

            is_final = index == len(self.pages) - 1

            if is_final:
                if page.next_url is not None:
                    raise InvalidGhsaPaginationError(
                        "GHSA pagination is incomplete: final page still has rel=next."
                    )
                continue

            if page.next_url is None:
                raise InvalidGhsaPaginationError(
                    "GHSA pagination ended before the supplied page inventory."
                )

            if page.next_url != self.pages[index + 1].request_url:
                raise InvalidGhsaPaginationError(
                    "GHSA pagination did not follow the exact rel=next URL."
                )

    @property
    def total_items(self) -> int:
        """Return the number of unique advisories in the complete page sequence."""
        return sum(page.item_count for page in self.pages)

    @property
    def total_bytes(self) -> int:
        """Return the total exact response bytes across all pages."""
        return sum(page.size_bytes for page in self.pages)
