"""Deterministic normalization of NVD CVE collection fields."""

from typing import cast

from opslens.transformation.nvd.domain.errors import (
    InvalidNvdCveCollectionsError,
)
from opslens.transformation.nvd.domain.models import (
    NvdCveCollections,
    NvdCveTag,
    NvdLocalizedText,
    NvdReference,
    NvdWeakness,
)


class NvdCveCollectionsTransformer:
    """Normalize NVD descriptions, tags, weaknesses, and references."""

    def transform(
        self,
        source_cve: dict[str, object],
    ) -> NvdCveCollections:
        """Transform one NVD CVE collection-field set."""
        descriptions = tuple(
            self._localized_text(
                value,
                context=f"description[{index}]",
            )
            for index, value in enumerate(
                self._required_array(
                    source_cve,
                    "descriptions",
                )
            )
        )

        cve_tags = tuple(
            self._cve_tag(
                value,
                index=index,
            )
            for index, value in enumerate(
                self._optional_array(
                    source_cve,
                    "cveTags",
                )
            )
        )

        weaknesses = tuple(
            self._weakness(
                value,
                index=index,
            )
            for index, value in enumerate(
                self._optional_array(
                    source_cve,
                    "weaknesses",
                )
            )
        )

        references = tuple(
            self._reference(
                value,
                index=index,
            )
            for index, value in enumerate(
                self._required_array(
                    source_cve,
                    "references",
                )
            )
        )

        try:
            return NvdCveCollections(
                descriptions=descriptions,
                cve_tags=cve_tags,
                weaknesses=weaknesses,
                references=references,
            )
        except ValueError as exc:
            raise InvalidNvdCveCollectionsError(
                f"Invalid NVD CVE collection fields: {exc}"
            ) from exc

    def _localized_text(
        self,
        value: object,
        *,
        context: str,
    ) -> NvdLocalizedText:
        """Normalize one localized NVD text object."""
        record = self._object(
            value,
            context=context,
        )

        try:
            return NvdLocalizedText(
                lang=self._required_text(
                    record,
                    "lang",
                    context=context,
                ),
                value=self._required_text(
                    record,
                    "value",
                    context=context,
                ),
            )
        except ValueError as exc:
            raise InvalidNvdCveCollectionsError(f"Invalid NVD {context}: {exc}") from exc

    def _cve_tag(
        self,
        value: object,
        *,
        index: int,
    ) -> NvdCveTag:
        """Normalize one source-qualified CVE tag group."""
        context = f"cveTags[{index}]"
        record = self._object(
            value,
            context=context,
        )

        tags = self._string_array(
            record,
            "tags",
            context=context,
            required=True,
        )

        try:
            return NvdCveTag(
                source_identifier=self._required_text(
                    record,
                    "sourceIdentifier",
                    context=context,
                ),
                tags=tags,
            )
        except ValueError as exc:
            raise InvalidNvdCveCollectionsError(f"Invalid NVD {context}: {exc}") from exc

    def _weakness(
        self,
        value: object,
        *,
        index: int,
    ) -> NvdWeakness:
        """Normalize one source-qualified weakness observation."""
        context = f"weaknesses[{index}]"
        record = self._object(
            value,
            context=context,
        )

        descriptions = tuple(
            self._localized_text(
                description,
                context=f"{context}.description[{description_index}]",
            )
            for description_index, description in enumerate(
                self._required_array(
                    record,
                    "description",
                    context=context,
                )
            )
        )

        try:
            return NvdWeakness(
                source=self._required_text(
                    record,
                    "source",
                    context=context,
                ),
                type=self._required_text(
                    record,
                    "type",
                    context=context,
                ),
                descriptions=descriptions,
            )
        except ValueError as exc:
            raise InvalidNvdCveCollectionsError(f"Invalid NVD {context}: {exc}") from exc

    def _reference(
        self,
        value: object,
        *,
        index: int,
    ) -> NvdReference:
        """Normalize one NVD reference without fetching its URL."""
        context = f"references[{index}]"
        record = self._object(
            value,
            context=context,
        )

        tags = self._string_array(
            record,
            "tags",
            context=context,
            required=False,
        )

        try:
            return NvdReference(
                url=self._required_text(
                    record,
                    "url",
                    context=context,
                ),
                source=self._required_text(
                    record,
                    "source",
                    context=context,
                ),
                tags=tags,
            )
        except ValueError as exc:
            raise InvalidNvdCveCollectionsError(f"Invalid NVD {context}: {exc}") from exc

    @staticmethod
    def _object(
        value: object,
        *,
        context: str,
    ) -> dict[str, object]:
        """Require one source JSON object."""
        if not isinstance(value, dict):
            raise InvalidNvdCveCollectionsError(f"NVD {context} must be an object.")

        return cast(dict[str, object], value)

    @staticmethod
    def _required_text(
        record: dict[str, object],
        field_name: str,
        *,
        context: str,
    ) -> str:
        """Read one required non-empty text value without rewriting it."""
        value = record.get(field_name)

        if not isinstance(value, str):
            raise InvalidNvdCveCollectionsError(f"NVD {context}.{field_name} must be a string.")

        if not value.strip():
            raise InvalidNvdCveCollectionsError(f"NVD {context}.{field_name} cannot be empty.")

        return value

    @staticmethod
    def _required_array(
        record: dict[str, object],
        field_name: str,
        *,
        context: str = "CVE",
    ) -> list[object]:
        """Read one required non-empty JSON array."""
        if field_name not in record:
            raise InvalidNvdCveCollectionsError(
                f"NVD {context} is missing required field {field_name!r}."
            )

        value = record[field_name]

        if not isinstance(value, list):
            raise InvalidNvdCveCollectionsError(f"NVD {context}.{field_name} must be an array.")

        items = cast(list[object], value)

        if not items:
            raise InvalidNvdCveCollectionsError(f"NVD {context}.{field_name} cannot be empty.")

        return items

    @staticmethod
    def _optional_array(
        record: dict[str, object],
        field_name: str,
    ) -> list[object]:
        """Read one optional JSON array, defaulting absence to empty."""
        if field_name not in record:
            return []

        value = record[field_name]

        if not isinstance(value, list):
            raise InvalidNvdCveCollectionsError(
                f"NVD CVE.{field_name} must be an array when present."
            )

        return cast(list[object], value)

    @staticmethod
    def _string_array(
        record: dict[str, object],
        field_name: str,
        *,
        context: str,
        required: bool,
    ) -> tuple[str, ...]:
        """Read a source-order-preserving array of non-empty strings."""
        if field_name not in record:
            if required:
                raise InvalidNvdCveCollectionsError(
                    f"NVD {context} is missing required field {field_name!r}."
                )

            return ()

        value = record[field_name]

        if not isinstance(value, list):
            raise InvalidNvdCveCollectionsError(f"NVD {context}.{field_name} must be an array.")

        items = cast(list[object], value)

        if required and not items:
            raise InvalidNvdCveCollectionsError(f"NVD {context}.{field_name} cannot be empty.")

        result: list[str] = []

        for index, item in enumerate(items):
            if not isinstance(item, str):
                raise InvalidNvdCveCollectionsError(
                    f"NVD {context}.{field_name}[{index}] must be a string."
                )

            if not item.strip():
                raise InvalidNvdCveCollectionsError(
                    f"NVD {context}.{field_name}[{index}] cannot be empty."
                )

            result.append(item)

        return tuple(result)
