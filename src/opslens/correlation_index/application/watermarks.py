"""Ask each source how current it was when the index was built.

A response citing this index says "no known vulnerabilities as of <instant>", and the
instant has to come from the sources rather than from the clock on the machine that ran
the build. A projector that ran at noon over a corpus last ingested three days ago is
three days stale, and only the sources know that.

```text
built at != current through
```

Two tiny queries, deliberately separate from the projection itself. Folding a `max()`
into the projection would make every row carry a column the index does not store, and a
column nothing stores is a column nobody notices going wrong.
"""

from typing import Final

GHSA_WATERMARK_COLUMN: Final = "observed_through"
NVD_WATERMARK_COLUMN: Final = "observed_through"


def ghsa_watermark_sql(database: str, table: str) -> str:
    """Build the query asking how current the GHSA corpus is.

    Args:
        database: The Glue database holding Silver.
        table: The GHSA Silver table.

    Returns:
        The SELECT statement.
    """
    return f'''
SELECT
  coalesce(max(updated_at), '') AS {GHSA_WATERMARK_COLUMN},
  cast(count(*) AS varchar) AS record_count
FROM "{database}"."{table}"
'''.strip()


def nvd_watermark_sql(database: str, table: str) -> str:
    """Build the query asking how current the NVD corpus is.

    Args:
        database: The Glue database holding Silver.
        table: The NVD Silver table.

    Returns:
        The SELECT statement.
    """
    return f'''
SELECT
  coalesce(max(last_modified_at), '') AS {NVD_WATERMARK_COLUMN},
  cast(count(*) AS varchar) AS record_count
FROM "{database}"."{table}"
'''.strip()
