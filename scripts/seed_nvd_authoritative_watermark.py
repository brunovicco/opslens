"""Seed the initial authoritative NVD watermark from audited Bootstrap evidence."""

import json
import os
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from datetime import datetime
from typing import cast

from boto3.session import Session

from opslens.ingestion.nvd.adapters.outbound.s3_authoritative_watermark import (
    S3NvdAuthoritativeWatermarkClient,
    S3NvdAuthoritativeWatermarkStore,
)
from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdWatermarkEvidenceObjectV1,
)
from opslens.ingestion.nvd.application.authoritative_watermark_seed import (
    NvdBootstrapRecoverySeedEvidenceV1,
    SeedNvdAuthoritativeWatermarkV1,
)

DEFAULT_WATERMARK_KEY = "control/nvd/cve/incremental/watermark.json"


class AdminConsoleTelemetry:
    """Emit lightweight JSON-lines telemetry for the one-time admin operation."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Emit one informational event."""
        print(
            json.dumps(
                {
                    "level": "INFO",
                    "message": message,
                    **dict(fields or {}),
                },
                sort_keys=True,
            )
        )

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Emit one failure event."""
        print(
            json.dumps(
                {
                    "level": "ERROR",
                    "message": message,
                    **dict(fields or {}),
                },
                sort_keys=True,
            )
        )

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Emit one operational metric observation."""
        print(
            json.dumps(
                {
                    "metric": name,
                    "unit": unit,
                    "value": value,
                },
                sort_keys=True,
            )
        )

    @contextmanager
    def span(
        self,
        name: str,
    ) -> Generator[object]:
        """Provide a no-op local tracing span."""
        yield object()


def _required_env(name: str) -> str:
    """Return one required non-empty environment variable."""
    value = os.environ.get(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Required environment variable {name} is not set."
        )

    return value


def _parse_timestamp(value: str) -> datetime:
    """Parse one explicit ISO-8601 recovery timestamp."""
    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise RuntimeError(
            "NVD_RECOVERY_T0 must be a valid ISO-8601 timestamp."
        ) from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeError(
            "NVD_RECOVERY_T0 must contain an explicit timezone."
        )

    return parsed


def main() -> None:
    """Execute one safe seed attempt."""
    bucket = _required_env("NVD_BUCKET")
    region = _required_env("AWS_REGION")
    bootstrap_manifest_key = _required_env(
        "NVD_BOOTSTRAP_MANIFEST_KEY"
    )
    bootstrap_manifest_version_id = _required_env(
        "NVD_BOOTSTRAP_MANIFEST_VERSION_ID"
    )
    bootstrap_manifest_sha256 = _required_env(
        "NVD_BOOTSTRAP_MANIFEST_SHA256"
    )
    recovery_t0 = _parse_timestamp(
        _required_env("NVD_RECOVERY_T0")
    )

    watermark_key = os.environ.get(
        "NVD_WATERMARK_KEY",
        DEFAULT_WATERMARK_KEY,
    ).strip()

    if not watermark_key:
        raise RuntimeError(
            "NVD_WATERMARK_KEY cannot be empty."
        )

    session = Session(
        region_name=region,
    )

    raw_client = session.client(  # pyright: ignore[reportUnknownMemberType]
        "s3"
    )

    client = cast(
        S3NvdAuthoritativeWatermarkClient,
        raw_client,
    )

    store = S3NvdAuthoritativeWatermarkStore(
        client=client,
        bucket_name=bucket,
        object_key=watermark_key,
        telemetry=AdminConsoleTelemetry(),
    )

    evidence = NvdBootstrapRecoverySeedEvidenceV1(
        source_revision_at=recovery_t0,
        bootstrap_manifest=NvdWatermarkEvidenceObjectV1(
            key=bootstrap_manifest_key,
            version_id=bootstrap_manifest_version_id,
            sha256=bootstrap_manifest_sha256,
        ),
    )

    result = SeedNvdAuthoritativeWatermarkV1(
        store=store,
    ).execute(
        evidence=evidence,
    )

    print(
        json.dumps(
            {
                "bucket": bucket,
                "committed_through_at": (
                    result.persisted.watermark.canonical_committed_through_at
                ),
                "etag": result.persisted.etag,
                "object_key": watermark_key,
                "sha256": result.persisted.sha256,
                "size_bytes": result.persisted.size_bytes,
                "status": result.status.value,
                "version_id": result.persisted.version_id,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
