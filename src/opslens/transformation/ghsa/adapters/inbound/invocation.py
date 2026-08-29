"""Strict explicit invocation envelope for GHSA Silver runtime."""

from collections.abc import Mapping

from opslens.transformation.ghsa.application.runtime_models import (
    GhsaSilverRuntimeRequestV1,
)


class InvalidGhsaSilverInvocationError(ValueError):
    """Raised when a GHSA Silver explicit invocation envelope is invalid."""


class GhsaSilverInvocationParserV1:
    """Parse one strict versioned GHSA Silver invocation envelope."""

    REQUIRED_FIELDS = frozenset(
        {
            "schema_version",
            "manifest_key",
            "manifest_version_id",
        }
    )
    BRONZE_PREFIX = "bronze/ghsa/advisories/"

    def parse(
        self,
        event: Mapping[str, object],
    ) -> GhsaSilverRuntimeRequestV1:
        """Parse and validate one exact GHSA Bronze manifest coordinate."""
        actual_fields = frozenset(event)
        missing = self.REQUIRED_FIELDS - actual_fields
        unexpected = actual_fields - self.REQUIRED_FIELDS

        if missing:
            formatted = ", ".join(sorted(missing))
            raise InvalidGhsaSilverInvocationError(
                "GHSA Silver invocation is missing required fields: "
                f"{formatted}."
            )

        if unexpected:
            formatted = ", ".join(sorted(unexpected))
            raise InvalidGhsaSilverInvocationError(
                "GHSA Silver invocation contains unsupported fields: "
                f"{formatted}."
            )

        schema_version = self._required_string(
            event,
            "schema_version",
        )

        if schema_version != "1":
            raise InvalidGhsaSilverInvocationError(
                "GHSA Silver invocation schema_version must be '1'."
            )

        manifest_key = self._required_string(
            event,
            "manifest_key",
        )
        manifest_version_id = self._required_string(
            event,
            "manifest_version_id",
        )

        self._validate_manifest_key(manifest_key)

        return GhsaSilverRuntimeRequestV1(
            manifest_key=manifest_key,
            manifest_version_id=manifest_version_id,
        )

    @staticmethod
    def _required_string(
        event: Mapping[str, object],
        field_name: str,
    ) -> str:
        """Read one required non-empty invocation string."""
        value = event.get(field_name)

        if not isinstance(value, str) or not value.strip():
            raise InvalidGhsaSilverInvocationError(
                f"GHSA Silver invocation {field_name} must be a non-empty string."
            )

        return value

    @classmethod
    def _validate_manifest_key(cls, manifest_key: str) -> None:
        """Restrict explicit invocation to the GHSA Bronze manifest namespace."""
        if not manifest_key.startswith(cls.BRONZE_PREFIX):
            raise InvalidGhsaSilverInvocationError(
                "GHSA Silver invocation manifest key must use the GHSA Bronze "
                "advisories namespace."
            )

        if not manifest_key.endswith("/manifest.json"):
            raise InvalidGhsaSilverInvocationError(
                "GHSA Silver invocation must reference a manifest.json object."
            )

        if "//" in manifest_key or "/../" in manifest_key or "/./" in manifest_key:
            raise InvalidGhsaSilverInvocationError(
                "GHSA Silver invocation manifest key is not canonical."
            )
