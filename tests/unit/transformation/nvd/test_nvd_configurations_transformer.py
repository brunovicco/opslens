"""Tests for deterministic NVD CPE configuration preservation."""

import json

import pytest

from opslens.transformation.nvd.domain.configurations_transformer import (
    NvdCpeConfigurationsTransformer,
)
from opslens.transformation.nvd.domain.errors import (
    InvalidNvdCpeConfigurationsError,
)
from opslens.transformation.nvd.domain.models import (
    NvdCpeConfigurations,
)


def _match() -> dict[str, object]:
    """Return one representative NVD CPE match object."""
    return {
        "vulnerable": True,
        "criteria": "cpe:2.3:a:example:product:*:*:*:*:*:*:*:*",
        "matchCriteriaId": "12345678-1234-1234-1234-123456789abc",
        "versionStartIncluding": "1.0",
        "versionEndExcluding": "2.0",
    }


def _configurations() -> list[object]:
    """Return one representative NVD applicability configuration tree."""
    return [
        {
            "operator": "AND",
            "negate": False,
            "nodes": [
                {
                    "operator": "OR",
                    "negate": False,
                    "cpeMatch": [
                        _match(),
                    ],
                }
            ],
        }
    ]


def test_absent_configurations_are_valid_and_empty() -> None:
    """Represent an absent optional configurations field as empty evidence."""
    result = NvdCpeConfigurationsTransformer().transform({})

    assert result.configuration_count == 0
    assert result.configurations_json == "[]"


def test_empty_configurations_array_is_valid() -> None:
    """Accept the schema-defined empty configurations array."""
    result = NvdCpeConfigurationsTransformer().transform(
        {
            "configurations": [],
        }
    )

    assert result.configuration_count == 0
    assert result.configurations_json == "[]"


def test_complete_configuration_tree_is_preserved_canonically() -> None:
    """Preserve operators, negation, CPE criteria, and version boundaries."""
    result = NvdCpeConfigurationsTransformer().transform(
        {
            "configurations": _configurations(),
        }
    )

    assert result.configuration_count == 1

    parsed = json.loads(result.configurations_json)

    assert parsed[0]["operator"] == "AND"
    assert parsed[0]["negate"] is False
    assert parsed[0]["nodes"][0]["operator"] == "OR"

    cpe_match = parsed[0]["nodes"][0]["cpeMatch"][0]

    assert cpe_match["vulnerable"] is True
    assert cpe_match["criteria"] == "cpe:2.3:a:example:product:*:*:*:*:*:*:*:*"
    assert cpe_match["versionStartIncluding"] == "1.0"
    assert cpe_match["versionEndExcluding"] == "2.0"

    assert " " not in result.configurations_json


def test_top_level_configuration_operator_is_optional() -> None:
    """Accept a configuration without its optional top-level operator."""
    configurations = _configurations()
    config = configurations[0]
    assert isinstance(config, dict)
    del config["operator"]

    result = NvdCpeConfigurationsTransformer().transform(
        {
            "configurations": configurations,
        }
    )

    assert result.configuration_count == 1


def test_invalid_top_level_operator_fails_closed() -> None:
    """Reject an unsupported top-level configuration operator."""
    configurations = _configurations()
    config = configurations[0]
    assert isinstance(config, dict)
    config["operator"] = "XOR"

    with pytest.raises(
        InvalidNvdCpeConfigurationsError,
        match="'AND' or 'OR'",
    ):
        NvdCpeConfigurationsTransformer().transform(
            {
                "configurations": configurations,
            }
        )


def test_configuration_negate_must_be_boolean() -> None:
    """Reject non-boolean configuration negation values."""
    configurations = _configurations()
    config = configurations[0]
    assert isinstance(config, dict)
    config["negate"] = 0

    with pytest.raises(
        InvalidNvdCpeConfigurationsError,
        match="negate must be a boolean",
    ):
        NvdCpeConfigurationsTransformer().transform(
            {
                "configurations": configurations,
            }
        )


def test_configuration_requires_nodes() -> None:
    """Reject a configuration without its required nodes array."""
    configurations: list[object] = [
        {
            "operator": "OR",
        }
    ]

    with pytest.raises(
        InvalidNvdCpeConfigurationsError,
        match="nodes",
    ):
        NvdCpeConfigurationsTransformer().transform(
            {
                "configurations": configurations,
            }
        )


def test_empty_nodes_array_is_valid() -> None:
    """Accept a required nodes array containing zero nodes."""
    result = NvdCpeConfigurationsTransformer().transform(
        {
            "configurations": [
                {
                    "nodes": [],
                }
            ]
        }
    )

    assert result.configuration_count == 1


@pytest.mark.parametrize(
    "missing_field",
    [
        "operator",
        "cpeMatch",
    ],
)
def test_node_requires_schema_fields(missing_field: str) -> None:
    """Reject nodes missing either required schema field."""
    node: dict[str, object] = {
        "operator": "OR",
        "cpeMatch": [],
    }
    del node[missing_field]

    source: dict[str, object] = {
        "configurations": [
            {
                "nodes": [
                    node,
                ],
            }
        ]
    }

    with pytest.raises(
        InvalidNvdCpeConfigurationsError,
        match=missing_field,
    ):
        NvdCpeConfigurationsTransformer().transform(source)


def test_invalid_node_operator_fails_closed() -> None:
    """Reject a node using an operator outside AND/OR."""
    source: dict[str, object] = {
        "configurations": [
            {
                "nodes": [
                    {
                        "operator": "NOT",
                        "cpeMatch": [],
                    }
                ],
            }
        ]
    }

    with pytest.raises(
        InvalidNvdCpeConfigurationsError,
        match="'AND' or 'OR'",
    ):
        NvdCpeConfigurationsTransformer().transform(source)


def test_empty_cpe_match_array_is_valid() -> None:
    """Accept a required cpeMatch array containing zero matches."""
    source: dict[str, object] = {
        "configurations": [
            {
                "nodes": [
                    {
                        "operator": "OR",
                        "cpeMatch": [],
                    }
                ],
            }
        ]
    }

    result = NvdCpeConfigurationsTransformer().transform(source)

    assert result.configuration_count == 1


@pytest.mark.parametrize(
    "missing_field",
    [
        "vulnerable",
        "criteria",
        "matchCriteriaId",
    ],
)
def test_cpe_match_requires_schema_fields(missing_field: str) -> None:
    """Reject CPE matches missing one of their required schema fields."""
    cpe_match = _match()
    del cpe_match[missing_field]

    source: dict[str, object] = {
        "configurations": [
            {
                "nodes": [
                    {
                        "operator": "OR",
                        "cpeMatch": [
                            cpe_match,
                        ],
                    }
                ],
            }
        ]
    }

    with pytest.raises(
        InvalidNvdCpeConfigurationsError,
        match=missing_field,
    ):
        NvdCpeConfigurationsTransformer().transform(source)


def test_vulnerable_requires_strict_boolean() -> None:
    """Reject integer values from the JSON boolean vulnerable field."""
    cpe_match = _match()
    cpe_match["vulnerable"] = 1

    source: dict[str, object] = {
        "configurations": [
            {
                "nodes": [
                    {
                        "operator": "OR",
                        "cpeMatch": [
                            cpe_match,
                        ],
                    }
                ],
            }
        ]
    }

    with pytest.raises(
        InvalidNvdCpeConfigurationsError,
        match="vulnerable must be a boolean",
    ):
        NvdCpeConfigurationsTransformer().transform(source)


def test_match_criteria_id_must_use_uuid_format() -> None:
    """Reject malformed NVD match criteria identifiers."""
    cpe_match = _match()
    cpe_match["matchCriteriaId"] = "not-a-uuid"

    source: dict[str, object] = {
        "configurations": [
            {
                "nodes": [
                    {
                        "operator": "OR",
                        "cpeMatch": [
                            cpe_match,
                        ],
                    }
                ],
            }
        ]
    }

    with pytest.raises(
        InvalidNvdCpeConfigurationsError,
        match="UUID format",
    ):
        NvdCpeConfigurationsTransformer().transform(source)


def test_version_bound_must_be_string_when_present() -> None:
    """Reject non-string version range boundaries."""
    cpe_match = _match()
    cpe_match["versionEndIncluding"] = 2

    source: dict[str, object] = {
        "configurations": [
            {
                "nodes": [
                    {
                        "operator": "OR",
                        "cpeMatch": [
                            cpe_match,
                        ],
                    }
                ],
            }
        ]
    }

    with pytest.raises(
        InvalidNvdCpeConfigurationsError,
        match="versionEndIncluding must be a string",
    ):
        NvdCpeConfigurationsTransformer().transform(source)


def test_additive_source_fields_are_preserved() -> None:
    """Preserve unknown additive source evidence without interpreting it."""
    configurations = _configurations()
    config = configurations[0]
    assert isinstance(config, dict)
    config["futureConfigurationField"] = {
        "opaque": True,
    }

    result = NvdCpeConfigurationsTransformer().transform(
        {
            "configurations": configurations,
        }
    )

    parsed = json.loads(result.configurations_json)

    assert parsed[0]["futureConfigurationField"] == {
        "opaque": True,
    }


def test_source_array_order_is_preserved() -> None:
    """Preserve CPE match order as observed instead of sorting the array."""
    first = _match()
    first["matchCriteriaId"] = "11111111-1111-1111-1111-111111111111"
    first["criteria"] = "first"

    second = _match()
    second["matchCriteriaId"] = "22222222-2222-2222-2222-222222222222"
    second["criteria"] = "second"

    source: dict[str, object] = {
        "configurations": [
            {
                "nodes": [
                    {
                        "operator": "OR",
                        "cpeMatch": [
                            first,
                            second,
                        ],
                    }
                ],
            }
        ]
    }

    result = NvdCpeConfigurationsTransformer().transform(source)
    parsed = json.loads(result.configurations_json)
    matches = parsed[0]["nodes"][0]["cpeMatch"]

    assert matches[0]["criteria"] == "first"
    assert matches[1]["criteria"] == "second"


def test_direct_model_rejects_noncanonical_configuration_json() -> None:
    """Reject stored configuration evidence that is not canonical JSON."""
    noncanonical = '[{"nodes": []}]'

    with pytest.raises(
        ValueError,
        match="Canonical JSON v1",
    ):
        NvdCpeConfigurations(
            configurations_json=noncanonical,
            configuration_count=1,
        )
