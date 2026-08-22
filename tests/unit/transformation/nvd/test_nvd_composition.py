"""Tests for NVD Silver runtime composition."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from typing import cast

import pytest

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.nvd.adapters.outbound.s3_exact_object import (
    S3GetObjectVersionClient,
)
from opslens.transformation.nvd.adapters.outbound.s3_silver_completion import (
    S3NvdSilverCompletionClient,
)
from opslens.transformation.nvd.adapters.outbound.s3_silver_parquet import (
    S3PutNvdSilverObjectClient,
)
from opslens.transformation.nvd.adapters.outbound.s3_silver_replay import (
    S3NvdSilverReplayClient,
)
from opslens.transformation.nvd.composition import (
    compose_runtime_dependencies,
)
from opslens.transformation.nvd.config import (
    NvdSilverTransformationSettings,
)
from opslens.transformation.nvd.runtime import (
    NvdSilverRuntimeProcessor,
)


class NoIoClient:
    """Represent one physical S3 client that must not be called while composing."""


class RecordingTelemetry:
    """Provide no-op operational telemetry for composition tests."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept one informational event."""

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept one exception event."""

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Accept one metric sample."""

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Return one no-op tracing context."""
        return nullcontext(object())


def test_composes_runtime_without_performing_s3_io() -> None:
    """Build the complete application graph without invoking infrastructure."""
    raw_client = NoIoClient()

    dependencies = compose_runtime_dependencies(
        settings=NvdSilverTransformationSettings(
            data_bucket="opslens-dev-data",
        ),
        telemetry=cast(
            OperationalTelemetry,
            RecordingTelemetry(),
        ),
        bronze_client=cast(
            S3GetObjectVersionClient,
            raw_client,
        ),
        parquet_write_client=cast(
            S3PutNvdSilverObjectClient,
            raw_client,
        ),
        parquet_replay_client=cast(
            S3NvdSilverReplayClient,
            raw_client,
        ),
        completion_client=cast(
            S3NvdSilverCompletionClient,
            raw_client,
        ),
    )

    assert isinstance(
        dependencies.processor,
        NvdSilverRuntimeProcessor,
    )


def test_rejects_empty_bucket_during_composition() -> None:
    """Fail before runtime when infrastructure coordinates are invalid."""
    raw_client = NoIoClient()

    with pytest.raises(
        ValueError,
        match="bucket",
    ):
        compose_runtime_dependencies(
            settings=NvdSilverTransformationSettings(
                data_bucket=" ",
            ),
            telemetry=cast(
                OperationalTelemetry,
                RecordingTelemetry(),
            ),
            bronze_client=cast(
                S3GetObjectVersionClient,
                raw_client,
            ),
            parquet_write_client=cast(
                S3PutNvdSilverObjectClient,
                raw_client,
            ),
            parquet_replay_client=cast(
                S3NvdSilverReplayClient,
                raw_client,
            ),
            completion_client=cast(
                S3NvdSilverCompletionClient,
                raw_client,
            ),
        )
