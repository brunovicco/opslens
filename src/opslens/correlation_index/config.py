"""Where the correlation index lives, resolved once and fixed for the process.

Two components address the same index from opposite ends: the scheduled projector
writes it, the request path reads it. If they disagree about a table name or a key
prefix, nothing fails — the reader simply finds an empty key space and answers "no
known vulnerabilities" for every package. Names are the kind of thing that disagree
quietly, so both sides resolve them from here.

```text
different name != error
empty key space != no advisories
```

Validation is what makes configuration safe rather than dangerous. These values become
DynamoDB table names, an S3 bucket and object keys, so an unchecked environment
variable is a way to point a live reader at a store nobody audited. Each is checked
against a closed character set before it can be used.

```text
configurable at deployment != selectable at request time
```
"""

import os
import re
from dataclasses import dataclass
from typing import Final

GHSA_TABLE_VARIABLE: Final = "OPSLENS_CORRELATION_INDEX_GHSA_TABLE"
NVD_TABLE_VARIABLE: Final = "OPSLENS_CORRELATION_INDEX_NVD_TABLE"
EVIDENCE_BUCKET_VARIABLE: Final = "OPSLENS_DATA_BUCKET"

MANIFEST_PREFIX: Final = "index/correlation/manifests"
POINTER_KEY: Final = "index/correlation/current.json"

_TABLE_NAME: Final = re.compile(r"[A-Za-z0-9_.-]{3,255}")
_BUCKET_NAME: Final = re.compile(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]")


class CorrelationIndexConfigurationError(ValueError):
    """Raised when a configured name could point the index somewhere unaudited."""


@dataclass(frozen=True, slots=True)
class CorrelationIndexCatalog:
    """The exact stores one process addresses the correlation index through.

    Attributes:
        ghsa_table: The GHSA-by-package table.
        nvd_table: The NVD-by-CVE table.
        evidence_bucket: The versioned bucket holding the manifest and the pointer.
    """

    ghsa_table: str
    nvd_table: str
    evidence_bucket: str

    def __post_init__(self) -> None:
        """Reject any name that is not a plain store identifier.

        Raises:
            CorrelationIndexConfigurationError: If a name is malformed.
        """
        for variable, value in (
            (GHSA_TABLE_VARIABLE, self.ghsa_table),
            (NVD_TABLE_VARIABLE, self.nvd_table),
        ):
            if _TABLE_NAME.fullmatch(value) is None:
                raise CorrelationIndexConfigurationError(
                    f"{variable} must be a DynamoDB table name, got {value!r}"
                )

        if _BUCKET_NAME.fullmatch(self.evidence_bucket) is None:
            raise CorrelationIndexConfigurationError(
                f"{EVIDENCE_BUCKET_VARIABLE} must be an S3 bucket name, "
                f"got {self.evidence_bucket!r}"
            )

        if self.ghsa_table == self.nvd_table:
            raise CorrelationIndexConfigurationError(
                "the GHSA and NVD indexes cannot share one table; their keys differ"
            )

    def manifest_key(self, index_id: str) -> str:
        """Return the content-addressed key one manifest is retained under.

        Args:
            index_id: The manifest identity, `<contract>@sha256:<digest>`.

        Returns:
            The object key.

        Raises:
            CorrelationIndexConfigurationError: If the identity carries no digest.
        """
        _, separator, digest = index_id.partition("@sha256:")
        if not separator or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise CorrelationIndexConfigurationError(
                f"{index_id!r} is not a content-addressed index identity"
            )
        return f"{MANIFEST_PREFIX}/{digest}.json"

    @property
    def pointer_key(self) -> str:
        """Return the key of the object naming the live generation."""
        return POINTER_KEY

    @classmethod
    def from_environment(
        cls, environment: dict[str, str] | None = None
    ) -> "CorrelationIndexCatalog":
        """Resolve one catalog from the environment.

        Nothing here has a default. Every value names a live store, and a store name
        defaulting to one environment is how a process writes an index into an
        environment nobody asked it to touch — or reads an empty key space in its own
        and reports no advisories. A missing variable is a deployment that is not
        finished, and it fails as one.

        Args:
            environment: Mapping to read, or None to read `os.environ`.

        Returns:
            A validated catalog.

        Raises:
            CorrelationIndexConfigurationError: If a variable is unset or malformed.
        """
        source = dict(os.environ) if environment is None else environment
        resolved: dict[str, str] = {}
        for variable in (
            GHSA_TABLE_VARIABLE,
            NVD_TABLE_VARIABLE,
            EVIDENCE_BUCKET_VARIABLE,
        ):
            value = source.get(variable, "").strip()
            if not value:
                raise CorrelationIndexConfigurationError(
                    f"{variable} must be set; it names a live store and has no safe default"
                )
            resolved[variable] = value

        return cls(
            ghsa_table=resolved[GHSA_TABLE_VARIABLE],
            nvd_table=resolved[NVD_TABLE_VARIABLE],
            evidence_bucket=resolved[EVIDENCE_BUCKET_VARIABLE],
        )
