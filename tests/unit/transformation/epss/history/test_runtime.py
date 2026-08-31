"""Unit tests for historical EPSS runtime boundary discovery."""

from datetime import date
from typing import cast

import pytest

from opslens.transformation.epss.history.runtime import (
    HistoricalEpssForwardListClient,
    S3HistoricalEpssForwardBoundaryReader,
)


class FakeListClient:
    """Return configured S3 ListObjectsV2 pages."""

    def __init__(self, *, pages: list[dict[str, object]]) -> None:
        """Initialize deterministic page sequence."""
        self._pages = pages
        self.requests: list[dict[str, object]] = []

    def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
        """Return the next configured page and capture request parameters."""
        self.requests.append(dict(kwargs))
        if not self._pages:
            raise AssertionError("Unexpected ListObjectsV2 request.")
        return self._pages.pop(0)


def _reader(client: FakeListClient) -> S3HistoricalEpssForwardBoundaryReader:
    """Build a boundary reader from one typed fake client."""
    return S3HistoricalEpssForwardBoundaryReader(
        client=cast(HistoricalEpssForwardListClient, client),
        bucket_name="opslens-test-data",
    )


def test_discovers_earliest_forward_snapshot_across_paginated_listing() -> None:
    """Use every S3 page and return the earliest canonical forward authority date."""
    client = FakeListClient(
        pages=[
            {
                "Contents": [
                    {
                        "Key": (
                            "bronze/epss/snapshot_date=2026-08-16/epss_scores.csv.gz"
                        )
                    }
                ],
                "IsTruncated": True,
                "NextContinuationToken": "next-page",
            },
            {
                "Contents": [
                    {
                        "Key": (
                            "bronze/epss/snapshot_date=2026-08-15/epss_scores.csv.gz"
                        )
                    },
                    {
                        "Key": (
                            "bronze/epss/snapshot_date=2026-08-17/epss_scores.csv.gz"
                        )
                    },
                ],
                "IsTruncated": False,
            },
        ]
    )

    result = _reader(client).discover()

    assert result == date(2026, 8, 15)
    assert client.requests == [
        {"Bucket": "opslens-test-data", "Prefix": "bronze/epss/"},
        {
            "Bucket": "opslens-test-data",
            "Prefix": "bronze/epss/",
            "ContinuationToken": "next-page",
        },
    ]


def test_ignores_noncanonical_or_unrelated_forward_keys() -> None:
    """Do not treat unrelated objects as forward-authority evidence."""
    client = FakeListClient(
        pages=[
            {
                "Contents": [
                    {"Key": "bronze/epss/readme.txt"},
                    {"Key": "bronze/epss-history/snapshot_date=2021-04-14/source.csv.gz"},
                    {
                        "Key": (
                            "bronze/epss/snapshot_date=2026-08-15/epss_scores.csv.gz"
                        )
                    },
                ]
            }
        ]
    )

    assert _reader(client).discover() == date(2026, 8, 15)


def test_fails_closed_when_no_canonical_forward_snapshot_exists() -> None:
    """Require real target-environment forward authority before history mutation."""
    client = FakeListClient(
        pages=[{"Contents": [{"Key": "bronze/epss/readme.txt"}]}]
    )

    with pytest.raises(ValueError, match="No canonical forward EPSS snapshot"):
        _reader(client).discover()


def test_rejects_truncated_listing_without_continuation_token() -> None:
    """Fail rather than accept an incomplete forward-boundary listing."""
    client = FakeListClient(pages=[{"Contents": [], "IsTruncated": True}])

    with pytest.raises(ValueError, match="continuation token"):
        _reader(client).discover()
