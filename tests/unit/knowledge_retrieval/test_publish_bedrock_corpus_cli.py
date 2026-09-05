"""Tests for the bounded real Bedrock corpus publication CLI."""

import json

import pytest

from opslens.knowledge_retrieval.application.s3_publication import (
    RemoteObjectEvidence,
    S3PublicationEvidence,
)
from opslens.knowledge_retrieval.cli.publish_bedrock_corpus import (
    PublicationCliError,
    require_publication_region,
    serialize_publication_evidence,
)


def test_require_region_accepts_only_frozen_dev_region() -> None:
    """Publication must not silently move the frozen Gate 7.3 workload to another region."""
    assert require_publication_region("us-east-1") == "us-east-1"

    with pytest.raises(PublicationCliError, match=r"frozen Gate 7\.3 region"):
        require_publication_region("us-west-2")


def test_serialize_evidence_is_hash_only_and_deterministic() -> None:
    """CLI output must contain remote verification evidence but never source text."""
    source_text = "DO-NOT-EMIT-THIRD-PARTY-SOURCE-TEXT"
    evidence = S3PublicationEvidence(
        prefix="knowledge/corpus/v1/bedrock",
        source_manifest_sha256="a" * 64,
        payload_count=2,
        total_byte_count=42,
        objects=(
            RemoteObjectEvidence(
                key="knowledge/corpus/v1/bedrock/chunks/abc.txt",
                byte_count=30,
                checksum_sha256="b" * 64,
                content_type="text/plain; charset=utf-8",
            ),
            RemoteObjectEvidence(
                key="knowledge/corpus/v1/bedrock/chunks/abc.txt.metadata.json",
                byte_count=12,
                checksum_sha256="c" * 64,
                content_type="application/json",
            ),
        ),
    )

    first = serialize_publication_evidence(
        evidence,
        bucket="opslens-dev-data-487757851499-us-east-1",
        expected_bucket_owner="487757851499",
        region="us-east-1",
    )
    second = serialize_publication_evidence(
        evidence,
        bucket="opslens-dev-data-487757851499-us-east-1",
        expected_bucket_owner="487757851499",
        region="us-east-1",
    )

    assert first == second
    assert source_text not in first
    parsed = json.loads(first)
    assert parsed["payload_count"] == 2
    assert parsed["total_byte_count"] == 42
    assert parsed["source_manifest_sha256"] == "a" * 64
    assert [item["checksum_sha256"] for item in parsed["objects"]] == ["b" * 64, "c" * 64]
