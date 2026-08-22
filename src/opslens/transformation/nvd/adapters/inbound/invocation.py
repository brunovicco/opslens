"""Strict explicit invocation envelope for NVD Silver runtime."""

from collections.abc import Mapping

from opslens.transformation.nvd.application.runtime_models import (
    NvdSilverRuntimeRequestV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)


class InvalidNvdSilverInvocationError(ValueError):
    """Raised when an NVD Silver explicit invocation envelope is invalid."""


class NvdSilverInvocationParserV1:
    """Parse one strict versioned NVD Silver invocation envelope."""

    REQUIRED_FIELDS = frozenset(
        {
            "schema_version",
            "source_kind",
            "manifest_key",
            "manifest_version_id",
        }
    )

    def parse(
        self,
        event: Mapping[str, object],
    ) -> NvdSilverRuntimeRequestV1:
        """Parse and validate one explicit NVD Silver invocation."""
        actual_fields = frozenset(event)

        missing = self.REQUIRED_FIELDS - actual_fields
        unexpected = actual_fields - self.REQUIRED_FIELDS

        if missing:
            formatted = ", ".join(sorted(missing))
            raise InvalidNvdSilverInvocationError(
                f"NVD Silver invocation is missing required fields: {formatted}."
            )

        if unexpected:
            formatted = ", ".join(sorted(unexpected))
            raise InvalidNvdSilverInvocationError(
                f"NVD Silver invocation contains unsupported fields: {formatted}."
            )

        schema_version = self._required_string(
            event,
            "schema_version",
        )

        if schema_version != "1":
            raise InvalidNvdSilverInvocationError(
                "NVD Silver invocation schema_version must be '1'."
            )

        source_kind_text = self._required_string(
            event,
            "source_kind",
        )

        try:
            source_kind = NvdSilverSourceKind(source_kind_text)
        except ValueError as exc:
            raise InvalidNvdSilverInvocationError(
                "NVD Silver invocation source_kind is unsupported."
            ) from exc

        manifest_key = self._required_string(
            event,
            "manifest_key",
        )
        manifest_version_id = self._required_string(
            event,
            "manifest_version_id",
        )

        self._validate_manifest_key(
            source_kind=source_kind,
            manifest_key=manifest_key,
        )

        return NvdSilverRuntimeRequestV1(
            source_kind=source_kind,
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
            raise InvalidNvdSilverInvocationError(
                f"NVD Silver invocation {field_name} must be a non-empty string."
            )

        return value

    @staticmethod
    def _validate_manifest_key(
        *,
        source_kind: NvdSilverSourceKind,
        manifest_key: str,
    ) -> None:
        """Restrict invocation coordinates to valid NVD Bronze namespaces."""
        if not manifest_key.endswith("/manifest.json"):
            raise InvalidNvdSilverInvocationError(
                "NVD Silver invocation must reference a manifest.json object."
            )

        if source_kind is NvdSilverSourceKind.BOOTSTRAP:
            expected_prefix = "bronze/nvd/cve/bootstrap/"
        else:
            expected_prefix = "bronze/nvd/cve/updates/"

        if not manifest_key.startswith(expected_prefix):
            raise InvalidNvdSilverInvocationError(
                "NVD Silver invocation manifest key does not match the declared source_kind."
            )
