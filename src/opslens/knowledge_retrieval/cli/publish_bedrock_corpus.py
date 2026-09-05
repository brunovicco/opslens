"""Publish the frozen Phase 7 corpus to the bounded Bedrock S3 source prefix."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from opslens.knowledge_retrieval.adapters.http_source import (
    BoundedHttpsKnowledgeSource,
    KnowledgeSourceAcquisitionError,
)
from opslens.knowledge_retrieval.adapters.s3_publication import (
    BoundedS3PublicationStore,
    S3PublicationClient,
    S3PublicationStoreError,
    S3PublicationTarget,
)
from opslens.knowledge_retrieval.application.bedrock_publication import (
    BedrockPublicationError,
    build_bedrock_publication_plan,
)
from opslens.knowledge_retrieval.application.corpus_config import (
    CorpusConfigError,
    load_corpus_spec,
    load_source_registry,
)
from opslens.knowledge_retrieval.application.corpus_manifest import CorpusManifestError
from opslens.knowledge_retrieval.application.corpus_materialization import (
    CanonicalSourceTextError,
)
from opslens.knowledge_retrieval.application.corpus_pipeline import (
    CorpusPipelineError,
    materialize_corpus_documents,
)
from opslens.knowledge_retrieval.application.s3_publication import (
    S3PublicationEvidence,
    S3PublicationValidationError,
    publish_bedrock_plan,
)

_DEFAULT_REGISTRY = Path("knowledge/corpus/v1/source_registry.json")
_DEFAULT_SPEC = Path("knowledge/corpus/v1/corpus_spec.json")
_DEFAULT_MANIFEST = Path("knowledge/corpus/v1/manifest.json")
_REQUIRED_REGION = "us-east-1"


class PublicationCliError(ValueError):
    """Raised when CLI inputs cannot authorize one bounded publication run."""


def _parser() -> argparse.ArgumentParser:
    """Build the explicit real-publication CLI contract."""
    parser = argparse.ArgumentParser(
        description=(
            "Replay the frozen official corpus as inert text, require exact checked-manifest "
            "equality, publish exactly the admitted Bedrock S3 objects, and emit hash-only "
            "verification evidence."
        )
    )
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--expected-bucket-owner", required=True)
    parser.add_argument("--region", default=_REQUIRED_REGION)
    parser.add_argument("--registry", type=Path, default=_DEFAULT_REGISTRY)
    parser.add_argument("--spec", type=Path, default=_DEFAULT_SPEC)
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    return parser


def _read_expected_manifest(path: Path) -> str:
    """Read the checked hash-only corpus manifest without normalization."""
    try:
        value = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PublicationCliError(f"could not read expected manifest {path}") from exc
    if not value:
        raise PublicationCliError("expected manifest must not be empty")
    return value


def require_publication_region(value: object) -> str:
    """Require the single frozen Gate 7.3 AWS region."""
    if not isinstance(value, str) or value != _REQUIRED_REGION:
        raise PublicationCliError(
            f"region must equal the frozen Gate 7.3 region {_REQUIRED_REGION!r}"
        )
    return value


def _evidence_to_dict(
    evidence: S3PublicationEvidence,
    *,
    bucket: str,
    expected_bucket_owner: str,
    region: str,
) -> dict[str, object]:
    """Project verified remote state to hash-only evidence without source text."""
    return {
        "bucket": bucket,
        "expected_bucket_owner": expected_bucket_owner,
        "region": region,
        "prefix": evidence.prefix,
        "source_manifest_sha256": evidence.source_manifest_sha256,
        "payload_count": evidence.payload_count,
        "total_byte_count": evidence.total_byte_count,
        "objects": [
            {
                "key": item.key,
                "byte_count": item.byte_count,
                "checksum_sha256": item.checksum_sha256,
                "content_type": item.content_type,
            }
            for item in evidence.objects
        ],
    }


def serialize_publication_evidence(
    evidence: S3PublicationEvidence,
    *,
    bucket: str,
    expected_bucket_owner: str,
    region: str,
) -> str:
    """Serialize verified publication evidence deterministically."""
    return json.dumps(
        _evidence_to_dict(
            evidence,
            bucket=bucket,
            expected_bucket_owner=expected_bucket_owner,
            region=region,
        ),
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Replay, publish, and verify one exact bounded dev corpus publication."""
    args = _parser().parse_args(argv)
    bucket = cast(str, args.bucket)
    expected_bucket_owner = cast(str, args.expected_bucket_owner)
    registry_path = cast(Path, args.registry)
    spec_path = cast(Path, args.spec)
    manifest_path = cast(Path, args.manifest)

    try:
        region = require_publication_region(args.region)
        registry = load_source_registry(registry_path)
        spec = load_corpus_spec(spec_path)
        expected_manifest_text = _read_expected_manifest(manifest_path)
        materialized = materialize_corpus_documents(
            registry,
            spec,
            BoundedHttpsKnowledgeSource(),
        )
        plan = build_bedrock_publication_plan(
            registry,
            spec,
            materialized,
            expected_manifest_text=expected_manifest_text,
        )

        raw_client: object = boto3.client(
            "s3",
            region_name=region,
            config=Config(
                connect_timeout=5,
                read_timeout=30,
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
        client = cast(S3PublicationClient, raw_client)
        target = S3PublicationTarget(
            bucket_name=bucket,
            expected_bucket_owner=expected_bucket_owner,
        )
        evidence = publish_bedrock_plan(
            plan,
            BoundedS3PublicationStore(client, target),
        )
    except (
        BedrockPublicationError,
        BotoCoreError,
        CanonicalSourceTextError,
        ClientError,
        CorpusConfigError,
        CorpusManifestError,
        CorpusPipelineError,
        KnowledgeSourceAcquisitionError,
        PublicationCliError,
        S3PublicationStoreError,
        S3PublicationValidationError,
        OSError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        serialize_publication_evidence(
            evidence,
            bucket=bucket,
            expected_bucket_owner=expected_bucket_owner,
            region=region,
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
