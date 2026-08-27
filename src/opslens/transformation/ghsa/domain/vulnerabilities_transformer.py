"""Deterministic normalization of GHSA package/range/fix evidence."""

from typing import cast

from opslens.transformation.ghsa.domain.canonicalization import (
    canonicalize_json_object,
    sha256_hex,
)
from opslens.transformation.ghsa.domain.errors import (
    InvalidGhsaVulnerabilityEntriesError,
)
from opslens.transformation.ghsa.domain.models import (
    ObservedGhsaAdvisoryVersion,
)
from opslens.transformation.ghsa.domain.vulnerability_models import (
    GhsaPackageEcosystem,
    GhsaPackageIdentity,
    GhsaVulnerabilityEntry,
    GhsaVulnerabilitySet,
)


class GhsaVulnerabilitiesTransformer:
    """Normalize one-to-many package/range/fix evidence without applicability logic."""

    def transform(self, source_advisory: dict[str, object]) -> GhsaVulnerabilitySet:
        """Preserve every vulnerability source-array occurrence deterministically."""
        if "vulnerabilities" not in source_advisory:
            raise InvalidGhsaVulnerabilityEntriesError(
                "GitHub advisory is missing required field 'vulnerabilities'."
            )

        value = source_advisory["vulnerabilities"]

        if not isinstance(value, list):
            raise InvalidGhsaVulnerabilityEntriesError(
                "GitHub advisory field 'vulnerabilities' must be an array."
            )

        observed_version = ObservedGhsaAdvisoryVersion.from_source(source_advisory)
        entries: list[GhsaVulnerabilityEntry] = []

        for index, item in enumerate(cast(list[object], value)):
            try:
                entries.append(
                    self._entry(
                        item,
                        source_index=index,
                        observed_version=observed_version,
                    )
                )
            except ValueError as exc:
                raise InvalidGhsaVulnerabilityEntriesError(
                    f"Invalid GitHub advisory vulnerabilities[{index}]: {exc}"
                ) from exc

        try:
            return GhsaVulnerabilitySet(
                observed_version=observed_version,
                entries=tuple(entries),
            )
        except ValueError as exc:
            raise InvalidGhsaVulnerabilityEntriesError(
                f"Invalid GitHub advisory vulnerability set: {exc}"
            ) from exc

    def _entry(
        self,
        value: object,
        *,
        source_index: int,
        observed_version: ObservedGhsaAdvisoryVersion,
    ) -> GhsaVulnerabilityEntry:
        """Normalize one exact vulnerability source object."""
        mapping = self._require_object(value, path="vulnerability entry")
        missing = {
            "package",
            "vulnerable_version_range",
            "first_patched_version",
            "vulnerable_functions",
        } - mapping.keys()

        if missing:
            raise InvalidGhsaVulnerabilityEntriesError(
                f"entry is missing fields: {', '.join(sorted(missing))}."
            )

        package_mapping = self._require_object(mapping["package"], path="package")
        package_missing = {"ecosystem", "name"} - package_mapping.keys()

        if package_missing:
            raise InvalidGhsaVulnerabilityEntriesError(
                f"package is missing fields: {', '.join(sorted(package_missing))}."
            )

        ecosystem_text = self._required_mapping_text(
            package_mapping,
            "ecosystem",
            path="package",
        )

        try:
            ecosystem = GhsaPackageEcosystem(ecosystem_text)
        except ValueError as exc:
            raise InvalidGhsaVulnerabilityEntriesError(
                f"unsupported package ecosystem: {ecosystem_text!r}."
            ) from exc

        vulnerable_functions_value = mapping["vulnerable_functions"]

        if not isinstance(vulnerable_functions_value, list):
            raise InvalidGhsaVulnerabilityEntriesError(
                "vulnerable_functions must be an array."
            )

        vulnerable_functions: list[str] = []

        for function_index, function_name in enumerate(
            cast(list[object], vulnerable_functions_value)
        ):
            if not isinstance(function_name, str) or not function_name.strip():
                raise InvalidGhsaVulnerabilityEntriesError(
                    "vulnerable_functions"
                    f"[{function_index}] must be a non-empty string."
                )

            vulnerable_functions.append(function_name)

        canonical_json = canonicalize_json_object(mapping).decode("utf-8")

        return GhsaVulnerabilityEntry(
            observed_advisory_version_id=(
                observed_version.observed_advisory_version_id
            ),
            source_index=source_index,
            package=GhsaPackageIdentity(
                ecosystem=ecosystem,
                name=self._required_mapping_text(
                    package_mapping,
                    "name",
                    path="package",
                ),
            ),
            vulnerable_version_range=self._required_mapping_text(
                mapping,
                "vulnerable_version_range",
                path="vulnerability entry",
            ),
            first_patched_version=self._optional_mapping_text(
                mapping,
                "first_patched_version",
                path="vulnerability entry",
            ),
            vulnerable_functions=tuple(vulnerable_functions),
            source_entry_json=canonical_json,
            source_entry_sha256=sha256_hex(canonical_json.encode("utf-8")),
        )

    @staticmethod
    def _require_object(value: object, *, path: str) -> dict[str, object]:
        """Require one nested source object."""
        if not isinstance(value, dict):
            raise InvalidGhsaVulnerabilityEntriesError(
                f"GitHub advisory {path} must be an object."
            )

        return cast(dict[str, object], value)

    @staticmethod
    def _required_mapping_text(
        mapping: dict[str, object],
        field_name: str,
        *,
        path: str,
    ) -> str:
        """Read one required non-empty nested string."""
        value = mapping[field_name]

        if not isinstance(value, str) or not value.strip():
            raise InvalidGhsaVulnerabilityEntriesError(
                f"GitHub advisory {path}.{field_name} must be a non-empty string."
            )

        return value

    @staticmethod
    def _optional_mapping_text(
        mapping: dict[str, object],
        field_name: str,
        *,
        path: str,
    ) -> str | None:
        """Read one nullable nested string."""
        value = mapping[field_name]

        if value is None:
            return None

        if not isinstance(value, str) or not value.strip():
            raise InvalidGhsaVulnerabilityEntriesError(
                f"GitHub advisory {path}.{field_name} must be a non-empty string or null."
            )

        return value
