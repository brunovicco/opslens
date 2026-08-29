"""Authorize exact GHSA Bronze COMPLETE manifests for Silver transformation."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from opslens.ingestion.ghsa.application.key_factory import (
    GhsaBronzeKeyFactory,
)
from opslens.ingestion.ghsa.application.manifest import (
    GhsaCompleteManifest,
    GhsaCompleteManifestSerializer,
    GhsaStoredPage,
)
from opslens.ingestion.ghsa.domain.api_page import (
    GhsaRequestUrlPolicy,
)
from opslens.ingestion.ghsa.domain.sync import (
    GhsaSyncMode,
    GhsaSyncWindow,
)
from opslens.transformation.ghsa.runtime.materializer import (
    GhsaSilverAttemptContextV1,
)
from opslens.transformation.ghsa.runtime.page_processor import (
    GhsaBronzePageEvidenceV1,
)

_TOP_LEVEL_FIELDS = frozenset(
    {
        "advisory_type",
        "api_version",
        "attempt_id",
        "completion_status",
        "manifest_version",
        "mode",
        "page_count",
        "pages",
        "source",
        "source_interface",
        "sync_id",
        "total_bytes",
        "total_items",
        "window_end_at",
        "window_start_at",
    }
)

_PAGE_FIELDS = frozenset(
    {
        "first_ghsa_id",
        "item_count",
        "key",
        "last_ghsa_id",
        "next_url",
        "page_ordinal",
        "request_url",
        "sha256",
        "size_bytes",
        "version_id",
    }
)


@dataclass(frozen=True, slots=True)
class GhsaAuthorizedBronzeManifestV1:
    """Bind one exact manifest object version to validated Bronze evidence."""

    manifest_key: str
    manifest_version_id: str
    manifest: GhsaCompleteManifest

    @property
    def attempt_context(self) -> GhsaSilverAttemptContextV1:
        """Return the authorized Bronze attempt context for Silver."""
        return GhsaSilverAttemptContextV1(
            sync_id=self.manifest.sync_id,
            attempt_id=self.manifest.attempt_id,
            manifest_key=self.manifest_key,
            manifest_version_id=self.manifest_version_id,
        )

    @property
    def page_evidences(self) -> tuple[GhsaBronzePageEvidenceV1, ...]:
        """Return exact page evidence authorized by this COMPLETE manifest."""
        return tuple(
            GhsaBronzePageEvidenceV1(
                sync_id=self.manifest.sync_id,
                attempt_id=self.manifest.attempt_id,
                manifest_key=self.manifest_key,
                manifest_version_id=self.manifest_version_id,
                page_ordinal=page.page_ordinal,
                page_key=page.key,
                page_version_id=page.version_id,
                expected_size_bytes=page.size_bytes,
                expected_sha256=page.sha256,
            )
            for page in self.manifest.pages
        )


class GhsaBronzeManifestProcessorV1:
    """Validate exact COMPLETE Bronze evidence before Silver transformation."""

    def __init__(
        self,
        *,
        key_factory: GhsaBronzeKeyFactory,
        serializer: GhsaCompleteManifestSerializer,
    ) -> None:
        """Initialize deterministic Bronze contract dependencies."""
        self._key_factory = key_factory
        self._serializer = serializer

    def process(
        self,
        *,
        manifest_key: str,
        manifest_version_id: str,
        manifest_bytes: bytes,
    ) -> GhsaAuthorizedBronzeManifestV1:
        """Authorize one exact immutable Bronze manifest object version."""
        normalized_key = manifest_key.strip()
        normalized_version_id = manifest_version_id.strip()

        if not normalized_key:
            raise ValueError("GHSA Bronze manifest key cannot be empty.")

        if not normalized_version_id:
            raise ValueError("GHSA Bronze manifest VersionId cannot be empty.")

        document = self._parse_document(manifest_bytes)

        self._require_exact_fields(
            document,
            expected=_TOP_LEVEL_FIELDS,
            context="manifest",
        )

        self._validate_static_contract(document)

        mode_text = self._required_text(document, "mode")

        try:
            mode = GhsaSyncMode(mode_text)
        except ValueError as exc:
            raise ValueError(
                f"Unsupported GHSA Bronze manifest mode: {mode_text!r}."
            ) from exc

        window = GhsaSyncWindow(
            mode=mode,
            start_at=self._required_datetime(
                document,
                "window_start_at",
            ),
            end_at=self._required_datetime(
                document,
                "window_end_at",
            ),
        )

        sync_id = self._required_text(document, "sync_id")

        if sync_id != window.sync_id:
            raise ValueError(
                "GHSA Bronze manifest sync_id does not match "
                "the deterministic synchronization window."
            )

        attempt_id = self._required_text(document, "attempt_id")

        pages = self._parse_pages(document)

        page_count = self._required_int(document, "page_count")

        if page_count != len(pages):
            raise ValueError(
                "GHSA Bronze manifest page_count does not match pages."
            )

        manifest = GhsaCompleteManifest(
            mode=mode,
            sync_id=sync_id,
            attempt_id=attempt_id,
            window_start_at=window.start_at,
            window_end_at=window.end_at,
            total_items=self._required_int(
                document,
                "total_items",
            ),
            total_bytes=self._required_int(
                document,
                "total_bytes",
            ),
            pages=pages,
        )

        self._validate_layout(
            manifest_key=normalized_key,
            window=window,
            manifest=manifest,
        )

        self._validate_cursor_chain(
            window=window,
            manifest=manifest,
        )

        canonical_bytes = self._serializer.serialize(manifest)

        if canonical_bytes != manifest_bytes:
            raise ValueError(
                "GHSA Bronze manifest bytes do not use the canonical "
                "COMPLETE manifest representation."
            )

        return GhsaAuthorizedBronzeManifestV1(
            manifest_key=normalized_key,
            manifest_version_id=normalized_version_id,
            manifest=manifest,
        )

    @staticmethod
    def _parse_document(
        manifest_bytes: bytes,
    ) -> dict[str, object]:
        """Decode strict UTF-8 JSON and reject duplicate object fields."""
        if not manifest_bytes:
            raise ValueError("GHSA Bronze manifest bytes cannot be empty.")

        try:
            text = manifest_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "GHSA Bronze manifest must contain valid UTF-8."
            ) from exc

        try:
            parsed = cast(
                object,
                json.loads(
                    text,
                    object_pairs_hook=(
                        GhsaBronzeManifestProcessorV1
                        ._reject_duplicate_object_pairs
                    ),
                ),
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "GHSA Bronze manifest must contain valid JSON."
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError(
                "GHSA Bronze manifest top-level JSON value must be an object."
            )

        return cast(dict[str, object], parsed)

    @staticmethod
    def _reject_duplicate_object_pairs(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        """Reject duplicate JSON fields at every object nesting level."""
        document: dict[str, object] = {}

        for key, value in pairs:
            if key in document:
                raise ValueError(
                    f"GHSA Bronze manifest contains duplicate JSON "
                    f"object field {key!r}."
                )

            document[key] = value

        return document

    @staticmethod
    def _require_exact_fields(
        document: dict[str, object],
        *,
        expected: frozenset[str],
        context: str,
    ) -> None:
        """Require exactly the schema-v1 field set."""
        actual = set(document)

        missing = expected - actual
        unexpected = actual - expected

        if missing:
            fields = ", ".join(sorted(missing))
            raise ValueError(
                f"GHSA Bronze {context} is missing fields: {fields}."
            )

        if unexpected:
            fields = ", ".join(sorted(unexpected))
            raise ValueError(
                f"GHSA Bronze {context} contains unexpected fields: {fields}."
            )

    @classmethod
    def _validate_static_contract(
        cls,
        document: dict[str, object],
    ) -> None:
        """Require the exact frozen GHSA Bronze COMPLETE contract."""
        expected_values = {
            "advisory_type": GhsaSyncWindow.ADVISORY_TYPE,
            "api_version": GhsaSyncWindow.API_VERSION,
            "completion_status": GhsaCompleteManifest.COMPLETION_STATUS,
            "manifest_version": GhsaCompleteManifest.MANIFEST_VERSION,
            "source": GhsaCompleteManifest.SOURCE,
            "source_interface": GhsaCompleteManifest.SOURCE_INTERFACE,
        }

        for field_name, expected_value in expected_values.items():
            actual = cls._required_text(
                document,
                field_name,
            )

            if actual != expected_value:
                raise ValueError(
                    f"GHSA Bronze manifest {field_name} violates "
                    "the frozen COMPLETE contract."
                )

    @classmethod
    def _parse_pages(
        cls,
        document: dict[str, object],
    ) -> tuple[GhsaStoredPage, ...]:
        """Parse exact page inventory from the COMPLETE manifest."""
        raw_pages = document["pages"]

        if not isinstance(raw_pages, list):
            raise ValueError(
                "GHSA Bronze manifest pages must be an array."
            )

        pages: list[GhsaStoredPage] = []

        for index, raw_page in enumerate(
            cast(list[object], raw_pages)
        ):
            if not isinstance(raw_page, dict):
                raise ValueError(
                    f"GHSA Bronze manifest page[{index}] must be an object."
                )

            page_document = cast(
                dict[str, object],
                raw_page,
            )

            cls._require_exact_fields(
                page_document,
                expected=_PAGE_FIELDS,
                context=f"manifest page[{index}]",
            )

            pages.append(
                GhsaStoredPage(
                    page_ordinal=cls._required_int(
                        page_document,
                        "page_ordinal",
                    ),
                    key=cls._required_text(
                        page_document,
                        "key",
                    ),
                    version_id=cls._required_text(
                        page_document,
                        "version_id",
                    ),
                    size_bytes=cls._required_int(
                        page_document,
                        "size_bytes",
                    ),
                    sha256=cls._required_text(
                        page_document,
                        "sha256",
                    ),
                    item_count=cls._required_int(
                        page_document,
                        "item_count",
                    ),
                    request_url=cls._required_text(
                        page_document,
                        "request_url",
                    ),
                    next_url=cls._optional_text(
                        page_document,
                        "next_url",
                    ),
                    first_ghsa_id=cls._optional_text(
                        page_document,
                        "first_ghsa_id",
                    ),
                    last_ghsa_id=cls._optional_text(
                        page_document,
                        "last_ghsa_id",
                    ),
                )
            )

        return tuple(pages)

    def _validate_layout(
        self,
        *,
        manifest_key: str,
        window: GhsaSyncWindow,
        manifest: GhsaCompleteManifest,
    ) -> None:
        """Require manifest and pages to remain inside one exact attempt."""
        expected_manifest_key = self._key_factory.build_manifest_key(
            window=window,
            attempt_id=manifest.attempt_id,
        )

        if manifest_key != expected_manifest_key:
            raise ValueError(
                "GHSA Bronze manifest key does not match "
                "the deterministic attempt layout."
            )

        for page in manifest.pages:
            expected_page_key = self._key_factory.build_page_key(
                window=window,
                attempt_id=manifest.attempt_id,
                page_ordinal=page.page_ordinal,
            )

            if page.key != expected_page_key:
                raise ValueError(
                    "GHSA Bronze manifest page key does not match "
                    "the deterministic attempt layout."
                )

    @staticmethod
    def _validate_cursor_chain(
        *,
        window: GhsaSyncWindow,
        manifest: GhsaCompleteManifest,
    ) -> None:
        """Revalidate the complete ordered GitHub cursor chain."""
        initial_url = GhsaRequestUrlPolicy.build_initial(window)

        if manifest.pages[0].request_url != initial_url:
            raise ValueError(
                "GHSA Bronze manifest does not start from "
                "the deterministic initial request URL."
            )

        for index, page in enumerate(manifest.pages):
            GhsaRequestUrlPolicy.validate(
                page.request_url,
                window=window,
                require_cursor=index > 0,
            )

            final_page = index == len(manifest.pages) - 1

            if final_page:
                if page.next_url is not None:
                    raise ValueError(
                        "GHSA Bronze manifest final page still "
                        "contains a continuation URL."
                    )
                continue

            if page.next_url is None:
                raise ValueError(
                    "GHSA Bronze manifest cursor chain ends before "
                    "the final page."
                )

            GhsaRequestUrlPolicy.validate(
                page.next_url,
                window=window,
                require_cursor=True,
            )

            if page.next_url != manifest.pages[index + 1].request_url:
                raise ValueError(
                    "GHSA Bronze manifest cursor chain does not "
                    "match the next page request URL."
                )

    @staticmethod
    def _required_text(
        document: dict[str, object],
        field_name: str,
    ) -> str:
        """Read one required non-empty string."""
        value = document[field_name]

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"GHSA Bronze manifest {field_name} must be "
                "a non-empty string."
            )

        return value

    @staticmethod
    def _optional_text(
        document: dict[str, object],
        field_name: str,
    ) -> str | None:
        """Read one nullable non-empty string."""
        value = document[field_name]

        if value is None:
            return None

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"GHSA Bronze manifest {field_name} must be "
                "a non-empty string or null."
            )

        return value

    @staticmethod
    def _required_int(
        document: dict[str, object],
        field_name: str,
    ) -> int:
        """Read one strict JSON integer."""
        value = document[field_name]

        if type(value) is not int:
            raise ValueError(
                f"GHSA Bronze manifest {field_name} must be an integer."
            )

        return value

    @classmethod
    def _required_datetime(
        cls,
        document: dict[str, object],
        field_name: str,
    ) -> datetime:
        """Parse one required ISO-8601 timestamp."""
        value = cls._required_text(
            document,
            field_name,
        )

        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValueError(
                f"GHSA Bronze manifest {field_name} must be ISO-8601."
            ) from exc
