"""Tests that the watermark statements match the schema they run against.

The first version of these queries passed every offline check and failed on the live
table:

```text
TYPE_MISMATCH: All COALESCE operands must be the same type or coercible to a common
type. Cannot find common type between timestamp(3) and varchar(0)
```

Both source columns are Glue `timestamp`, and the statements were only ever compared
against a shape — "does it mention max()" — never against the types they address. A
query that builds is not a query that runs.

```text
statement builds != statement runs
```

So the casts are asserted here, against the column types declared in the Glue tables,
and the source columns are named so a schema change that renames them fails a test
rather than a build.
"""

import pathlib
import re
from typing import Final

import pytest

from opslens.correlation_index.application.watermarks import (
    ghsa_watermark_sql,
    nvd_watermark_sql,
)

_REPOSITORY_ROOT: Final = pathlib.Path(__file__).resolve().parents[4]
_GLUE_ROOT: Final = _REPOSITORY_ROOT / "infra" / "environments" / "dev"


def _declared_type(glue_file: str, column: str) -> str:
    """Read one column's declared Glue type.

    Args:
        glue_file: The Terraform file declaring the table.
        column: The column name.

    Returns:
        The declared type.
    """
    text = (_GLUE_ROOT / glue_file).read_text(encoding="utf-8")
    match = re.search(
        rf'name\s*=\s*"{re.escape(column)}"\s*\n\s*type\s*=\s*"([^"]+)"', text
    )
    assert match is not None, f"{column} is not declared in {glue_file}"
    return match.group(1)


@pytest.mark.parametrize(
    ("glue_file", "column"),
    [
        ("analytics_ghsa_glue.tf", "updated_at"),
        ("analytics_glue.tf", "last_modified_at"),
    ],
)
def test_the_watermark_columns_are_still_timestamps(glue_file: str, column: str) -> None:
    """If a source column stops being a timestamp, the cast below needs revisiting."""
    assert _declared_type(glue_file, column) == "timestamp"


@pytest.mark.parametrize(
    ("statement", "column"),
    [
        (ghsa_watermark_sql("db", "ghsa"), "updated_at"),
        (nvd_watermark_sql("db", "nvd"), "last_modified_at"),
    ],
)
def test_the_maximum_is_cast_before_being_coalesced(statement: str, column: str) -> None:
    """Athena refuses to coalesce a timestamp with a string; this is that bug, frozen."""
    assert f"coalesce(cast(max({column}) AS varchar), '')" in statement


@pytest.mark.parametrize(
    "statement", [ghsa_watermark_sql("db", "t"), nvd_watermark_sql("db", "t")]
)
def test_a_watermark_asks_for_its_own_record_count(statement: str) -> None:
    """The manifest records how many source records the freshness was read from."""
    assert "AS record_count" in statement


@pytest.mark.parametrize(
    "statement", [ghsa_watermark_sql("db", "t"), nvd_watermark_sql("db", "t")]
)
def test_a_watermark_returns_exactly_one_row(statement: str) -> None:
    """An aggregate with no GROUP BY returns one row, which is what the reader assumes."""
    assert "GROUP BY" not in statement.upper()
