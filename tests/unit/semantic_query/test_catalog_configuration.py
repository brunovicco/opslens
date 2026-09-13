"""Unit tests for semantic-query catalog configuration and its fail-closed validation.

The database, workgroup and table used to be hardcoded to one environment's names.
Configuring them is only safe because every identifier is validated before it can
reach a statement: the relation is interpolated into SQL text, so an unvalidated
environment variable would convert a trusted constant into an injection vector.
"""

import pathlib
from typing import Final

import pytest

from opslens.semantic_query.config import (
    ATHENA_DATABASE_VARIABLE,
    ATHENA_WORKGROUP_VARIABLE,
    DEFAULT_ATHENA_DATABASE,
    DEFAULT_ATHENA_WORKGROUP,
    DEFAULT_EPSS_TABLE,
    EPSS_TABLE_VARIABLE,
    SemanticQueryCatalog,
    SemanticQueryConfigurationError,
)


def test_defaults_reproduce_the_previously_hardcoded_catalog() -> None:
    """Making the catalog configurable changes no existing deployment's behaviour."""
    catalog = SemanticQueryCatalog.from_environment({})

    assert catalog.database == "opslens_dev"
    assert catalog.workgroup == "opslens-dev"
    assert catalog.epss_table == "epss_scores"
    assert catalog.epss_relation == '"opslens_dev"."epss_scores"'


def test_every_coordinate_is_configurable() -> None:
    """No environment name is baked into the package any more."""
    catalog = SemanticQueryCatalog.from_environment(
        {
            ATHENA_DATABASE_VARIABLE: "opslens_prod",
            ATHENA_WORKGROUP_VARIABLE: "opslens-prod",
            EPSS_TABLE_VARIABLE: "epss_scores_v2",
        }
    )

    assert catalog.database == "opslens_prod"
    assert catalog.workgroup == "opslens-prod"
    assert catalog.epss_relation == '"opslens_prod"."epss_scores_v2"'


@pytest.mark.parametrize("value", ["", "   ", "\t"])
def test_a_blank_variable_is_unset_rather_than_an_empty_identifier(value: str) -> None:
    """A blank variable in a deployment template must not produce empty SQL."""
    catalog = SemanticQueryCatalog.from_environment({ATHENA_DATABASE_VARIABLE: value})

    assert catalog.database == DEFAULT_ATHENA_DATABASE


@pytest.mark.parametrize(
    "value",
    [
        'opslens_dev"."other',
        "opslens_dev; DROP TABLE x",
        "opslens_dev--comment",
        "opslens_dev /* comment */",
        "opslens dev",
        "opslens.dev",
        "opslens-dev",
        "1opslens",
        "opslens_dev'",
        "opslens_dev\n",
        "",
    ],
)
def test_an_identifier_that_could_leave_its_position_is_rejected(value: str) -> None:
    """Configuration must not be able to append SQL of its own."""
    with pytest.raises(SemanticQueryConfigurationError):
        SemanticQueryCatalog(
            database=value,
            workgroup=DEFAULT_ATHENA_WORKGROUP,
            epss_table=DEFAULT_EPSS_TABLE,
        )


@pytest.mark.parametrize(
    "value",
    [
        'epss_scores"."other',
        "epss_scores; DROP TABLE x",
        "epss scores",
        "",
    ],
)
def test_the_table_identifier_is_validated_as_strictly_as_the_database(value: str) -> None:
    """Both halves of the relation are interpolated, so both are checked."""
    with pytest.raises(SemanticQueryConfigurationError):
        SemanticQueryCatalog(
            database=DEFAULT_ATHENA_DATABASE,
            workgroup=DEFAULT_ATHENA_WORKGROUP,
            epss_table=value,
        )


@pytest.mark.parametrize("value", ["opslens dev", 'opslens"dev', "opslens;dev", "", "opslens/dev"])
def test_an_unsafe_workgroup_name_is_rejected(value: str) -> None:
    """The workgroup is an API parameter, but a malformed one is still a defect."""
    with pytest.raises(SemanticQueryConfigurationError, match=ATHENA_WORKGROUP_VARIABLE):
        SemanticQueryCatalog(
            database=DEFAULT_ATHENA_DATABASE,
            workgroup=value,
            epss_table=DEFAULT_EPSS_TABLE,
        )


@pytest.mark.parametrize("value", ["opslens-dev", "opslens.dev", "opslens_dev", "primary", "wg-1"])
def test_a_legitimate_workgroup_name_is_admitted(value: str) -> None:
    """Validation narrows the character set without rejecting real Athena names."""
    catalog = SemanticQueryCatalog(
        database=DEFAULT_ATHENA_DATABASE,
        workgroup=value,
        epss_table=DEFAULT_EPSS_TABLE,
    )

    assert catalog.workgroup == value


def test_an_over_long_identifier_is_rejected() -> None:
    """Length is bounded so a configured value cannot become an unbounded payload."""
    with pytest.raises(SemanticQueryConfigurationError, match="exceed"):
        SemanticQueryCatalog(
            database="d" * 129,
            workgroup=DEFAULT_ATHENA_WORKGROUP,
            epss_table=DEFAULT_EPSS_TABLE,
        )


def test_the_catalog_is_immutable_once_resolved() -> None:
    """A catalog is a deployment coordinate, not request-time mutable state."""
    catalog = SemanticQueryCatalog.from_environment({})

    with pytest.raises(AttributeError):
        catalog.database = "other"  # type: ignore[misc]


_PACKAGE_ROOT: Final = pathlib.Path(__file__).resolve().parents[3] / "src" / "opslens"
_CONFIGURATION_MODULE: Final = _PACKAGE_ROOT / "semantic_query" / "config.py"
_ENVIRONMENT_NAMES: Final = ("opslens_dev", "opslens-dev")


def test_no_module_but_the_configuration_one_names_a_deployment_environment() -> None:
    """One module owns the default names, so the next one cannot be hardcoded quietly."""
    offenders = sorted(
        f"{path.relative_to(_PACKAGE_ROOT)}: {name}"
        for path in _PACKAGE_ROOT.rglob("*.py")
        if path != _CONFIGURATION_MODULE
        for name in _ENVIRONMENT_NAMES
        if name in path.read_text(encoding="utf-8")
    )

    assert offenders == [], (
        "a deployment environment name is hardcoded outside "
        f"{_CONFIGURATION_MODULE.name}: {offenders}"
    )
