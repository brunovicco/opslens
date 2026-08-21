"""Tests for deterministic NVD CVE collection-field normalization."""

import pytest

from opslens.transformation.nvd.domain.collections_transformer import (
    NvdCveCollectionsTransformer,
)
from opslens.transformation.nvd.domain.errors import (
    InvalidNvdCveCollectionsError,
)


def _source_cve() -> dict[str, object]:
    """Return representative NVD collection fields."""
    return {
        "descriptions": [
            {
                "lang": "en",
                "value": "Example vulnerability.",
            },
            {
                "lang": "es",
                "value": "Vulnerabilidad de ejemplo.",
            },
        ],
        "cveTags": [
            {
                "sourceIdentifier": "cna@example.com",
                "tags": [
                    "disputed",
                    "unsupported-when-assigned",
                ],
            }
        ],
        "weaknesses": [
            {
                "source": "nvd@nist.gov",
                "type": "Primary",
                "description": [
                    {
                        "lang": "en",
                        "value": "CWE-79",
                    },
                    {
                        "lang": "en",
                        "value": "NVD-CWE-Other",
                    },
                ],
            },
            {
                "source": "cna@example.com",
                "type": "Secondary",
                "description": [
                    {
                        "lang": "en",
                        "value": "CWE-79",
                    },
                    {
                        "lang": "en",
                        "value": "CWE-89",
                    },
                ],
            },
        ],
        "references": [
            {
                "url": "https://example.com/advisory",
                "source": "cna@example.com",
                "tags": [
                    "Vendor Advisory",
                    "Patch",
                ],
            },
            {
                "url": "https://example.com/details",
                "source": "nvd@nist.gov",
            },
        ],
    }


def test_collections_are_normalized_without_losing_source_structure() -> None:
    """Preserve descriptions, tags, weaknesses, and references."""
    collections = NvdCveCollectionsTransformer().transform(_source_cve())

    assert tuple((item.lang, item.value) for item in collections.descriptions) == (
        ("en", "Example vulnerability."),
        ("es", "Vulnerabilidad de ejemplo."),
    )

    assert collections.cve_tags[0].source_identifier == "cna@example.com"
    assert collections.cve_tags[0].tags == (
        "disputed",
        "unsupported-when-assigned",
    )

    assert collections.weaknesses[0].source == "nvd@nist.gov"
    assert collections.weaknesses[0].type == "Primary"

    assert collections.references[0].tags == (
        "Vendor Advisory",
        "Patch",
    )
    assert collections.references[1].tags == ()


def test_canonical_cwe_ids_are_derived_stably() -> None:
    """Extract unique canonical CWE IDs while preserving first occurrence."""
    collections = NvdCveCollectionsTransformer().transform(_source_cve())

    assert collections.cwe_ids == (
        "CWE-79",
        "CWE-89",
    )


def test_cwe_placeholders_remain_in_weaknesses() -> None:
    """Preserve NVD placeholder weakness values without treating them as CWE IDs."""
    collections = NvdCveCollectionsTransformer().transform(_source_cve())

    values = tuple(
        description.value
        for weakness in collections.weaknesses
        for description in weakness.descriptions
    )

    assert "NVD-CWE-Other" in values
    assert "NVD-CWE-Other" not in collections.cwe_ids


def test_absent_cve_tags_are_valid_and_become_empty() -> None:
    """Treat absent optional cveTags as an empty collection."""
    source = _source_cve()
    del source["cveTags"]

    collections = NvdCveCollectionsTransformer().transform(source)

    assert collections.cve_tags == ()


def test_absent_weaknesses_are_valid_and_become_empty() -> None:
    """Allow weakness absence for lifecycle states where NVD omits them."""
    source = _source_cve()
    del source["weaknesses"]

    collections = NvdCveCollectionsTransformer().transform(source)

    assert collections.weaknesses == ()
    assert collections.cwe_ids == ()


def test_source_array_order_is_preserved() -> None:
    """Preserve source ordering rather than sorting collection values."""
    collections = NvdCveCollectionsTransformer().transform(_source_cve())

    assert tuple(description.lang for description in collections.descriptions) == ("en", "es")

    assert tuple(reference.url for reference in collections.references) == (
        "https://example.com/advisory",
        "https://example.com/details",
    )


def test_missing_descriptions_fails_closed() -> None:
    """Reject a CVE without its required descriptions collection."""
    source = _source_cve()
    del source["descriptions"]

    with pytest.raises(
        InvalidNvdCveCollectionsError,
        match="descriptions",
    ):
        NvdCveCollectionsTransformer().transform(source)


def test_empty_descriptions_fails_closed() -> None:
    """Reject an empty required descriptions collection."""
    source = _source_cve()
    source["descriptions"] = []

    with pytest.raises(
        InvalidNvdCveCollectionsError,
        match="descriptions cannot be empty",
    ):
        NvdCveCollectionsTransformer().transform(source)


def test_malformed_description_fails_closed() -> None:
    """Reject malformed localized description objects."""
    source = _source_cve()
    source["descriptions"] = [
        {
            "lang": "en",
        }
    ]

    with pytest.raises(
        InvalidNvdCveCollectionsError,
        match="value",
    ):
        NvdCveCollectionsTransformer().transform(source)


def test_present_cve_tags_must_be_an_array() -> None:
    """Reject a malformed optional cveTags field when it is present."""
    source = _source_cve()
    source["cveTags"] = "disputed"

    with pytest.raises(
        InvalidNvdCveCollectionsError,
        match="cveTags must be an array",
    ):
        NvdCveCollectionsTransformer().transform(source)


def test_weakness_requires_descriptions() -> None:
    """Reject a weakness without its required description collection."""
    source = _source_cve()
    source["weaknesses"] = [
        {
            "source": "nvd@nist.gov",
            "type": "Primary",
        }
    ]

    with pytest.raises(
        InvalidNvdCveCollectionsError,
        match="description",
    ):
        NvdCveCollectionsTransformer().transform(source)


def test_missing_references_fails_closed() -> None:
    """Reject a CVE without the required references collection."""
    source = _source_cve()
    del source["references"]

    with pytest.raises(
        InvalidNvdCveCollectionsError,
        match="references",
    ):
        NvdCveCollectionsTransformer().transform(source)


def test_empty_references_fails_closed() -> None:
    """Reject an empty required references collection."""
    source = _source_cve()
    source["references"] = []

    with pytest.raises(
        InvalidNvdCveCollectionsError,
        match="references cannot be empty",
    ):
        NvdCveCollectionsTransformer().transform(source)


def test_reference_tags_are_optional() -> None:
    """Represent an absent reference tags array as an empty tuple."""
    source = _source_cve()
    references = source["references"]
    assert isinstance(references, list)

    references[0] = {
        "url": "https://example.com/advisory",
        "source": "cna@example.com",
    }

    collections = NvdCveCollectionsTransformer().transform(source)

    assert collections.references[0].tags == ()


def test_malformed_reference_fails_closed() -> None:
    """Reject a reference without its required URL."""
    source = _source_cve()
    source["references"] = [
        {
            "source": "cna@example.com",
        }
    ]

    with pytest.raises(
        InvalidNvdCveCollectionsError,
        match="url",
    ):
        NvdCveCollectionsTransformer().transform(source)
