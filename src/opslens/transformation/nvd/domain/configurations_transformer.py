"""Deterministic validation and preservation of NVD CPE configurations."""

import re
from typing import ClassVar, cast

from opslens.transformation.nvd.domain.canonicalization import (
    canonicalize_json_value,
)
from opslens.transformation.nvd.domain.errors import (
    InvalidNvdCpeConfigurationsError,
)
from opslens.transformation.nvd.domain.models import (
    NvdCpeConfigurations,
)

_MATCH_CRITERIA_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}$"
)


class NvdCpeConfigurationsTransformer:
    """Validate NVD applicability structure while preserving full evidence."""

    _OPERATORS: ClassVar[frozenset[str]] = frozenset(
        {
            "AND",
            "OR",
        }
    )

    _VERSION_BOUND_FIELDS: ClassVar[tuple[str, ...]] = (
        "versionStartExcluding",
        "versionStartIncluding",
        "versionEndExcluding",
        "versionEndIncluding",
    )

    def transform(
        self,
        source_cve: dict[str, object],
    ) -> NvdCpeConfigurations:
        """Validate and preserve one CVE applicability configuration set."""
        if "configurations" not in source_cve:
            return NvdCpeConfigurations(
                configurations_json="[]",
                configuration_count=0,
            )

        value = source_cve["configurations"]

        if not isinstance(value, list):
            raise InvalidNvdCpeConfigurationsError(
                "NVD CVE configurations must be an array when present."
            )

        configurations = cast(
            list[object],
            value,
        )

        for config_index, config_value in enumerate(configurations):
            self._validate_configuration(
                config_value,
                config_index=config_index,
            )

        try:
            configurations_json = canonicalize_json_value(configurations).decode("utf-8")

            return NvdCpeConfigurations(
                configurations_json=configurations_json,
                configuration_count=len(configurations),
            )
        except ValueError as exc:
            raise InvalidNvdCpeConfigurationsError(
                f"Invalid NVD CPE configuration evidence: {exc}"
            ) from exc

    def _validate_configuration(
        self,
        value: object,
        *,
        config_index: int,
    ) -> None:
        """Validate one top-level NVD configuration object."""
        context = f"configurations[{config_index}]"
        config = self._object(
            value,
            context=context,
        )

        self._optional_operator(
            config,
            context=context,
        )
        self._optional_boolean(
            config,
            "negate",
            context=context,
        )

        nodes = self._required_array(
            config,
            "nodes",
            context=context,
        )

        for node_index, node_value in enumerate(nodes):
            self._validate_node(
                node_value,
                context=f"{context}.nodes[{node_index}]",
            )

    def _validate_node(
        self,
        value: object,
        *,
        context: str,
    ) -> None:
        """Validate one NVD applicability node."""
        node = self._object(
            value,
            context=context,
        )

        self._required_operator(
            node,
            context=context,
        )
        self._optional_boolean(
            node,
            "negate",
            context=context,
        )

        matches = self._required_array(
            node,
            "cpeMatch",
            context=context,
        )

        for match_index, match_value in enumerate(matches):
            self._validate_cpe_match(
                match_value,
                context=f"{context}.cpeMatch[{match_index}]",
            )

    def _validate_cpe_match(
        self,
        value: object,
        *,
        context: str,
    ) -> None:
        """Validate one CPE match statement without interpreting its range."""
        match = self._object(
            value,
            context=context,
        )

        self._required_boolean(
            match,
            "vulnerable",
            context=context,
        )
        self._required_string(
            match,
            "criteria",
            context=context,
        )

        match_criteria_id = self._required_string(
            match,
            "matchCriteriaId",
            context=context,
        )

        if _MATCH_CRITERIA_ID_PATTERN.fullmatch(match_criteria_id) is None:
            raise InvalidNvdCpeConfigurationsError(
                f"NVD {context}.matchCriteriaId must use UUID format."
            )

        for field_name in self._VERSION_BOUND_FIELDS:
            self._optional_string(
                match,
                field_name,
                context=context,
            )

    @staticmethod
    def _object(
        value: object,
        *,
        context: str,
    ) -> dict[str, object]:
        """Require one JSON object."""
        if not isinstance(value, dict):
            raise InvalidNvdCpeConfigurationsError(f"NVD {context} must be an object.")

        return cast(
            dict[str, object],
            value,
        )

    @staticmethod
    def _required_array(
        record: dict[str, object],
        field_name: str,
        *,
        context: str,
    ) -> list[object]:
        """Read one required array; empty arrays remain valid."""
        if field_name not in record:
            raise InvalidNvdCpeConfigurationsError(
                f"NVD {context} is missing required field {field_name!r}."
            )

        value = record[field_name]

        if not isinstance(value, list):
            raise InvalidNvdCpeConfigurationsError(f"NVD {context}.{field_name} must be an array.")

        return cast(
            list[object],
            value,
        )

    def _required_operator(
        self,
        record: dict[str, object],
        *,
        context: str,
    ) -> str:
        """Read one required bounded applicability operator."""
        if "operator" not in record:
            raise InvalidNvdCpeConfigurationsError(
                f"NVD {context} is missing required field 'operator'."
            )

        return self._operator(
            record["operator"],
            context=f"{context}.operator",
        )

    def _optional_operator(
        self,
        record: dict[str, object],
        *,
        context: str,
    ) -> str | None:
        """Read one optional bounded applicability operator."""
        if "operator" not in record:
            return None

        return self._operator(
            record["operator"],
            context=f"{context}.operator",
        )

    def _operator(
        self,
        value: object,
        *,
        context: str,
    ) -> str:
        """Validate one AND/OR applicability operator."""
        if not isinstance(value, str):
            raise InvalidNvdCpeConfigurationsError(f"NVD {context} must be a string.")

        if value not in self._OPERATORS:
            raise InvalidNvdCpeConfigurationsError(f"NVD {context} must be 'AND' or 'OR'.")

        return value

    @staticmethod
    def _required_boolean(
        record: dict[str, object],
        field_name: str,
        *,
        context: str,
    ) -> bool:
        """Read one required strict JSON boolean."""
        if field_name not in record:
            raise InvalidNvdCpeConfigurationsError(
                f"NVD {context} is missing required field {field_name!r}."
            )

        value = record[field_name]

        if type(value) is not bool:
            raise InvalidNvdCpeConfigurationsError(f"NVD {context}.{field_name} must be a boolean.")

        return value

    @staticmethod
    def _optional_boolean(
        record: dict[str, object],
        field_name: str,
        *,
        context: str,
    ) -> bool | None:
        """Read one optional strict JSON boolean."""
        if field_name not in record:
            return None

        value = record[field_name]

        if type(value) is not bool:
            raise InvalidNvdCpeConfigurationsError(f"NVD {context}.{field_name} must be a boolean.")

        return value

    @staticmethod
    def _required_string(
        record: dict[str, object],
        field_name: str,
        *,
        context: str,
    ) -> str:
        """Read one required source string without interpreting its semantics."""
        if field_name not in record:
            raise InvalidNvdCpeConfigurationsError(
                f"NVD {context} is missing required field {field_name!r}."
            )

        value = record[field_name]

        if not isinstance(value, str):
            raise InvalidNvdCpeConfigurationsError(f"NVD {context}.{field_name} must be a string.")

        return value

    @staticmethod
    def _optional_string(
        record: dict[str, object],
        field_name: str,
        *,
        context: str,
    ) -> str | None:
        """Read one optional source string without interpreting its semantics."""
        if field_name not in record:
            return None

        value = record[field_name]

        if not isinstance(value, str):
            raise InvalidNvdCpeConfigurationsError(f"NVD {context}.{field_name} must be a string.")

        return value
