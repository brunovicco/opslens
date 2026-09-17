"""Tests for resolving where the correlation index lives.

The projector writes the index and the request path reads it. If they disagree about a
name, nothing raises: the reader finds an empty key space and answers "no known
vulnerabilities" for every package it is asked about.

```text
different name != error
empty key space != no advisories
```

So the names come from one place, and the values that could point a live reader at an
unaudited store are checked rather than trusted.
"""

import pytest

from opslens.correlation_index.config import (
    EVIDENCE_BUCKET_VARIABLE,
    GHSA_TABLE_VARIABLE,
    NVD_TABLE_VARIABLE,
    CorrelationIndexCatalog,
    CorrelationIndexConfigurationError,
)

_DIGEST = "3e8f5bff0551f7533a34c40a9a944832e9a01d258049d908e179b24da872431c"
_BUCKET = "opslens-example-data-000000000000-us-east-1"
_GHSA_TABLE = "opslens-example-correlation-index-ghsa"
_NVD_TABLE = "opslens-example-correlation-index-nvd"
_ENVIRONMENT = {
    EVIDENCE_BUCKET_VARIABLE: _BUCKET,
    GHSA_TABLE_VARIABLE: _GHSA_TABLE,
    NVD_TABLE_VARIABLE: _NVD_TABLE,
}


def test_a_complete_environment_resolves() -> None:
    """The happy case exists so the refusals below mean something."""
    catalog = CorrelationIndexCatalog.from_environment(dict(_ENVIRONMENT))
    assert catalog.ghsa_table == _GHSA_TABLE
    assert catalog.nvd_table == _NVD_TABLE
    assert catalog.evidence_bucket == _BUCKET


@pytest.mark.parametrize(
    "variable", [EVIDENCE_BUCKET_VARIABLE, GHSA_TABLE_VARIABLE, NVD_TABLE_VARIABLE]
)
def test_an_unset_variable_is_refused(variable: str) -> None:
    """Every value names a live store, so none of them may default to an environment."""
    environment = dict(_ENVIRONMENT)
    del environment[variable]
    with pytest.raises(CorrelationIndexConfigurationError):
        CorrelationIndexCatalog.from_environment(environment)


@pytest.mark.parametrize(
    "variable", [EVIDENCE_BUCKET_VARIABLE, GHSA_TABLE_VARIABLE, NVD_TABLE_VARIABLE]
)
def test_a_blank_variable_is_treated_as_unset(variable: str) -> None:
    """An empty variable is how a half-finished deployment looks."""
    environment = dict(_ENVIRONMENT)
    environment[variable] = "   "
    with pytest.raises(CorrelationIndexConfigurationError):
        CorrelationIndexCatalog.from_environment(environment)


@pytest.mark.parametrize("name", ["", "ab", "has space", "has/slash", "x" * 256])
def test_a_malformed_table_name_is_refused(name: str) -> None:
    """These names reach a live store, so they are checked rather than trusted."""
    with pytest.raises(CorrelationIndexConfigurationError):
        CorrelationIndexCatalog(
            ghsa_table=name, nvd_table=_NVD_TABLE, evidence_bucket=_BUCKET
        )


@pytest.mark.parametrize("bucket", ["", "UPPER", "a", "has_underscore", "x" * 64])
def test_a_malformed_bucket_name_is_refused(bucket: str) -> None:
    """An unchecked bucket name is a way to point a reader at an unaudited store."""
    with pytest.raises(CorrelationIndexConfigurationError):
        CorrelationIndexCatalog(
            ghsa_table=_GHSA_TABLE,
            nvd_table=_NVD_TABLE,
            evidence_bucket=bucket,
        )


def test_one_table_cannot_serve_both_indexes() -> None:
    """Their keys differ, so sharing a table would make one of them unreadable."""
    with pytest.raises(CorrelationIndexConfigurationError):
        CorrelationIndexCatalog(
            ghsa_table=_GHSA_TABLE,
            nvd_table=_GHSA_TABLE,
            evidence_bucket=_BUCKET,
        )


def test_the_manifest_key_is_content_addressed() -> None:
    """Retaining by digest means a manifest can never be overwritten by another."""
    catalog = CorrelationIndexCatalog.from_environment(dict(_ENVIRONMENT))
    assert catalog.manifest_key(f"opslens-correlation-index:v1@sha256:{_DIGEST}") == (
        f"index/correlation/manifests/{_DIGEST}.json"
    )


@pytest.mark.parametrize(
    "identity", ["", "opslens-correlation-index:v1", "x@sha256:short"]
)
def test_a_manifest_key_needs_a_real_digest(identity: str) -> None:
    """A key built from a non-content identity could collide with another build's."""
    catalog = CorrelationIndexCatalog.from_environment(dict(_ENVIRONMENT))
    with pytest.raises(CorrelationIndexConfigurationError):
        catalog.manifest_key(identity)


def test_the_pointer_key_is_one_fixed_object() -> None:
    """The swap is one write; a pointer whose key varies is not a pointer."""
    catalog = CorrelationIndexCatalog.from_environment(dict(_ENVIRONMENT))
    assert catalog.pointer_key == "index/correlation/current.json"
