"""Environment-based configuration for the bounded semantic-query Athena slice.

The Glue database, Athena workgroup and EPSS table were hardcoded to one
environment's names (`opslens_dev`, `opslens-dev`). That made the slice
unusable outside that environment and shipped a development identifier inside
the package.

Configuring them does not relax the security model, and the distinction matters:

```text
configurable at deployment != selectable at request time
```

One catalog is resolved once, at composition, and then fixed for the process.
Nothing reaching the compiler or the executor at request time can choose a
database, workgroup, table, column or SQL fragment — the compiler still owns the
whole statement and the executor still refuses any SQL that does not match the
catalog it was constructed with.

Validation is what makes configuration safe rather than dangerous. The relation
is interpolated into SQL text, so an unvalidated environment variable would turn
a trusted constant into an injection vector. Every identifier is therefore
checked against a closed character set before it can reach a query.
"""

import os
import re
from dataclasses import dataclass
from typing import Final

DEFAULT_ATHENA_DATABASE: Final = "opslens_dev"
DEFAULT_ATHENA_WORKGROUP: Final = "opslens-dev"
DEFAULT_EPSS_TABLE: Final = "epss_scores"

ATHENA_DATABASE_VARIABLE: Final = "OPSLENS_ATHENA_DATABASE"
ATHENA_WORKGROUP_VARIABLE: Final = "OPSLENS_ATHENA_WORKGROUP"
EPSS_TABLE_VARIABLE: Final = "OPSLENS_ATHENA_EPSS_TABLE"

# Unquoted SQL identifier shape. Deliberately narrower than Athena permits: no
# quotes, dots, whitespace, semicolons or comment markers can survive it, so a
# configured value cannot close an identifier and append SQL of its own.
_SQL_IDENTIFIER: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# Athena workgroup names allow a wider set, but never a quote or whitespace.
_WORKGROUP_NAME: Final = re.compile(r"[A-Za-z0-9._-]+")
_MAX_IDENTIFIER_LENGTH: Final = 128


class SemanticQueryConfigurationError(RuntimeError):
    """Raised when semantic-query catalog configuration is missing or unsafe."""


@dataclass(frozen=True, slots=True)
class SemanticQueryCatalog:
    """Represent the one fixed data catalog a semantic-query composition may reach.

    Attributes:
        database: Glue database holding the semantic-query relations.
        workgroup: Athena workgroup the executor submits to.
        epss_table: Table backing the EPSS score slice.
    """

    database: str
    workgroup: str
    epss_table: str

    def __post_init__(self) -> None:
        """Reject any identifier that could leave its position in a SQL statement.

        Raises:
            SemanticQueryConfigurationError: If an identifier is empty, too long,
                or contains a character outside the permitted set.
        """
        _assert_sql_identifier(self.database, variable=ATHENA_DATABASE_VARIABLE)
        _assert_sql_identifier(self.epss_table, variable=EPSS_TABLE_VARIABLE)
        _assert_workgroup_name(self.workgroup)

    @property
    def epss_relation(self) -> str:
        """Render the fully qualified, quoted EPSS relation for compiler-owned SQL."""
        return f'"{self.database}"."{self.epss_table}"'

    @classmethod
    def from_environment(
        cls,
        environment: dict[str, str] | None = None,
    ) -> "SemanticQueryCatalog":
        """Resolve one catalog from the environment, falling back to the dev names.

        Args:
            environment: Mapping to read, or None to read `os.environ`.

        Returns:
            A validated catalog.

        Raises:
            SemanticQueryConfigurationError: If a supplied identifier is unsafe.
        """
        source = dict(os.environ) if environment is None else environment
        return cls(
            database=_resolve(source, ATHENA_DATABASE_VARIABLE, DEFAULT_ATHENA_DATABASE),
            workgroup=_resolve(source, ATHENA_WORKGROUP_VARIABLE, DEFAULT_ATHENA_WORKGROUP),
            epss_table=_resolve(source, EPSS_TABLE_VARIABLE, DEFAULT_EPSS_TABLE),
        )


def _resolve(environment: dict[str, str], variable: str, default: str) -> str:
    """Read one optional environment variable, treating blank as unset."""
    value = environment.get(variable, "").strip()
    return value or default


def _assert_sql_identifier(value: str, *, variable: str) -> None:
    """Require one unquoted SQL identifier from a closed character set.

    Args:
        value: The configured identifier.
        variable: The environment variable the value came from, for the message.

    Raises:
        SemanticQueryConfigurationError: If the identifier is empty, too long, or
            contains a character outside `[A-Za-z0-9_]` after an initial letter
            or underscore.
    """
    if not value:
        raise SemanticQueryConfigurationError(f"{variable} cannot be empty.")
    if len(value) > _MAX_IDENTIFIER_LENGTH:
        raise SemanticQueryConfigurationError(
            f"{variable} cannot exceed {_MAX_IDENTIFIER_LENGTH} characters."
        )
    if _SQL_IDENTIFIER.fullmatch(value) is None:
        raise SemanticQueryConfigurationError(
            f"{variable} must be an unquoted SQL identifier "
            "matching [A-Za-z_][A-Za-z0-9_]*."
        )


def _assert_workgroup_name(value: str) -> None:
    """Require one Athena workgroup name without quoting or whitespace.

    Args:
        value: The configured workgroup name.

    Raises:
        SemanticQueryConfigurationError: If the name is empty, too long, or
            contains a character outside `[A-Za-z0-9._-]`.
    """
    if not value:
        raise SemanticQueryConfigurationError(f"{ATHENA_WORKGROUP_VARIABLE} cannot be empty.")
    if len(value) > _MAX_IDENTIFIER_LENGTH:
        raise SemanticQueryConfigurationError(
            f"{ATHENA_WORKGROUP_VARIABLE} cannot exceed {_MAX_IDENTIFIER_LENGTH} characters."
        )
    if _WORKGROUP_NAME.fullmatch(value) is None:
        raise SemanticQueryConfigurationError(
            f"{ATHENA_WORKGROUP_VARIABLE} must match [A-Za-z0-9._-]+."
        )


__all__ = [
    "ATHENA_DATABASE_VARIABLE",
    "ATHENA_WORKGROUP_VARIABLE",
    "DEFAULT_ATHENA_DATABASE",
    "DEFAULT_ATHENA_WORKGROUP",
    "DEFAULT_EPSS_TABLE",
    "EPSS_TABLE_VARIABLE",
    "SemanticQueryCatalog",
    "SemanticQueryConfigurationError",
]
