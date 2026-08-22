"""Load exact NVD Bronze object versions into a Silver transform request."""

import json
from dataclasses import dataclass
from typing import cast

from opslens.transformation.nvd.application.models import (
    NvdSilverTransformRequestV1,
)
from opslens.transformation.nvd.application.ports import (
    NvdBronzeObjectVersionReader,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectPayloadV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)


class NvdSilverRequestLoadError(RuntimeError):
    """Raised when an untrusted Bronze manifest cannot be loaded safely."""


@dataclass(frozen=True, slots=True)
class NvdBronzeObjectCoordinateV1:
    """Represent one exact object coordinate discovered from a manifest."""

    key: str
    version_id: str

    def __post_init__(self) -> None:
        """Validate one discovered exact-version coordinate."""
        if not self.key.strip():
            raise ValueError("NVD Bronze discovered object key cannot be empty.")

        if not self.version_id.strip():
            raise ValueError("NVD Bronze discovered object VersionId cannot be empty.")


class NvdSilverTransformRequestLoaderV1:
    """Load manifest-declared exact Bronze objects without establishing trust."""

    def __init__(
        self,
        *,
        object_reader: NvdBronzeObjectVersionReader,
    ) -> None:
        """Initialize the loader with one exact-version object reader."""
        self._object_reader = object_reader

    def load(
        self,
        *,
        source_kind: NvdSilverSourceKind,
        manifest_key: str,
        manifest_version_id: str,
    ) -> NvdSilverTransformRequestV1:
        """Load one manifest and all exact objects it declares."""
        manifest_payload = self._read_exact(
            key=manifest_key,
            version_id=manifest_version_id,
        )

        document = self._parse_manifest(
            manifest_payload.raw_bytes,
        )

        coordinates = self._discover_coordinates(
            source_kind=source_kind,
            manifest_key=manifest_key,
            document=document,
        )

        object_payloads = tuple(
            self._read_exact(
                key=coordinate.key,
                version_id=coordinate.version_id,
            )
            for coordinate in coordinates
        )

        return NvdSilverTransformRequestV1(
            source_kind=source_kind,
            manifest_key=manifest_payload.key,
            manifest_version_id=manifest_payload.version_id,
            manifest_bytes=manifest_payload.raw_bytes,
            object_payloads=object_payloads,
        )

    def _read_exact(
        self,
        *,
        key: str,
        version_id: str,
    ) -> NvdBronzeObjectPayloadV1:
        """Read one exact object and enforce the reader port contract."""
        payload = self._object_reader.get(
            key=key,
            version_id=version_id,
        )

        if payload.key != key:
            raise NvdSilverRequestLoadError("NVD Bronze object reader returned a different key.")

        if payload.version_id != version_id:
            raise NvdSilverRequestLoadError(
                "NVD Bronze object reader returned a different VersionId."
            )

        return payload

    def _discover_coordinates(
        self,
        *,
        source_kind: NvdSilverSourceKind,
        manifest_key: str,
        document: dict[str, object],
    ) -> tuple[NvdBronzeObjectCoordinateV1, ...]:
        """Discover exact object coordinates from an untrusted manifest."""
        if source_kind is NvdSilverSourceKind.BOOTSTRAP:
            coordinates = (
                self._stored_object_coordinate(
                    document=document,
                    field_name="feed_object",
                ),
                self._stored_object_coordinate(
                    document=document,
                    field_name="meta_object",
                ),
            )
        elif source_kind is NvdSilverSourceKind.INCREMENTAL:
            coordinates = self._incremental_page_coordinates(
                document,
            )
        else:
            raise NvdSilverRequestLoadError(f"Unsupported NVD Silver source kind {source_kind!r}.")

        self._validate_safe_batch_scope(
            manifest_key=manifest_key,
            coordinates=coordinates,
        )

        self._validate_unique_coordinates(
            coordinates,
        )

        return coordinates

    @classmethod
    def _incremental_page_coordinates(
        cls,
        document: dict[str, object],
    ) -> tuple[NvdBronzeObjectCoordinateV1, ...]:
        """Read page coordinates from one incremental manifest."""
        pages_value = document.get("pages")

        if not isinstance(pages_value, list):
            raise NvdSilverRequestLoadError(
                "NVD incremental Bronze manifest pages must be an array."
            )

        pages = cast(
            list[object],
            pages_value,
        )

        if not pages:
            raise NvdSilverRequestLoadError(
                "NVD incremental Bronze manifest pages cannot be empty."
            )

        coordinates: list[NvdBronzeObjectCoordinateV1] = []

        for index, page_value in enumerate(pages):
            if not isinstance(page_value, dict):
                raise NvdSilverRequestLoadError(
                    f"NVD incremental manifest pages[{index}] must be an object."
                )

            page = cast(
                dict[str, object],
                page_value,
            )

            coordinates.append(
                cls._coordinate_from_object(
                    page,
                    context=f"pages[{index}]",
                )
            )

        return tuple(coordinates)

    @classmethod
    def _stored_object_coordinate(
        cls,
        *,
        document: dict[str, object],
        field_name: str,
    ) -> NvdBronzeObjectCoordinateV1:
        """Read one bootstrap stored-object coordinate."""
        value = document.get(field_name)

        if not isinstance(value, dict):
            raise NvdSilverRequestLoadError(f"NVD Bronze manifest {field_name} must be an object.")

        stored = cast(
            dict[str, object],
            value,
        )

        return cls._coordinate_from_object(
            stored,
            context=field_name,
        )

    @staticmethod
    def _coordinate_from_object(
        document: dict[str, object],
        *,
        context: str,
    ) -> NvdBronzeObjectCoordinateV1:
        """Extract one exact key and VersionId from an untrusted object."""
        key = document.get("key")
        version_id = document.get("version_id")

        if not isinstance(key, str) or not key.strip():
            raise NvdSilverRequestLoadError(f"NVD Bronze {context}.key must be a non-empty string.")

        if not isinstance(version_id, str) or not version_id.strip():
            raise NvdSilverRequestLoadError(
                f"NVD Bronze {context}.version_id must be a non-empty string."
            )

        return NvdBronzeObjectCoordinateV1(
            key=key,
            version_id=version_id,
        )

    @staticmethod
    def _validate_safe_batch_scope(
        *,
        manifest_key: str,
        coordinates: tuple[NvdBronzeObjectCoordinateV1, ...],
    ) -> None:
        """Prevent an untrusted manifest from escaping its own batch prefix."""
        suffix = "/manifest.json"

        if not manifest_key.endswith(suffix):
            raise NvdSilverRequestLoadError(
                "NVD Bronze manifest key must end with '/manifest.json'."
            )

        batch_prefix = manifest_key.removesuffix(suffix)

        if not batch_prefix:
            raise NvdSilverRequestLoadError("NVD Bronze manifest batch prefix cannot be empty.")

        expected_prefix = f"{batch_prefix}/"

        for coordinate in coordinates:
            if not coordinate.key.startswith(expected_prefix):
                raise NvdSilverRequestLoadError(
                    "NVD Bronze manifest references an object outside its own source batch."
                )

            if coordinate.key == manifest_key:
                raise NvdSilverRequestLoadError(
                    "NVD Bronze manifest cannot reference itself as source data."
                )

    @staticmethod
    def _validate_unique_coordinates(
        coordinates: tuple[NvdBronzeObjectCoordinateV1, ...],
    ) -> None:
        """Reject duplicate object keys before issuing repeated S3 reads."""
        seen: set[str] = set()

        for coordinate in coordinates:
            if coordinate.key in seen:
                raise NvdSilverRequestLoadError(
                    "NVD Bronze manifest contains duplicate object keys."
                )

            seen.add(coordinate.key)

    @staticmethod
    def _parse_manifest(
        raw_bytes: bytes,
    ) -> dict[str, object]:
        """Parse an untrusted manifest without declaring it canonical."""
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise NvdSilverRequestLoadError("NVD Bronze manifest must be UTF-8.") from exc

        def reject_constant(value: str) -> object:
            raise ValueError(f"Non-finite JSON constant {value!r} is not allowed.")

        def unique_object(
            pairs: list[tuple[str, object]],
        ) -> dict[str, object]:
            result: dict[str, object] = {}

            for key, value in pairs:
                if key in result:
                    raise ValueError(f"Duplicate JSON key {key!r}.")

                result[key] = value

            return result

        try:
            parsed = cast(
                object,
                json.loads(
                    text,
                    parse_constant=reject_constant,
                    object_pairs_hook=unique_object,
                ),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise NvdSilverRequestLoadError("NVD Bronze manifest contains invalid JSON.") from exc

        if not isinstance(parsed, dict):
            raise NvdSilverRequestLoadError("NVD Bronze manifest must contain a JSON object.")

        return cast(
            dict[str, object],
            parsed,
        )
