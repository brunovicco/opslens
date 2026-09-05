"""Bounded Bedrock Agent ingestion adapter for Gate 7.3 corpus indexing."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast

from opslens.knowledge_retrieval.application.bedrock_ingestion import IngestionJobEvidence


class BedrockIngestionClient(Protocol):
    """Minimal dynamic Bedrock Agent client surface used by the adapter."""

    def start_ingestion_job(self, **kwargs: object) -> object:
        """Start one Knowledge Base ingestion job."""
        ...

    def get_ingestion_job(self, **kwargs: object) -> object:
        """Read one exact ingestion job."""
        ...


class BedrockIngestionAdapterError(RuntimeError):
    """Raised when Bedrock transport or response evidence is invalid."""


def _require_mapping(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise BedrockIngestionAdapterError(f"{field} must be an object")
    raw = cast(Mapping[object, object], value)
    if any(not isinstance(key, str) for key in raw):
        raise BedrockIngestionAdapterError(f"{field} keys must be strings")
    return dict(cast(Mapping[str, object], raw))


def _require_trimmed(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise BedrockIngestionAdapterError(f"{field} must be one trimmed non-empty string")
    return value


def _optional_statistics(value: object) -> dict[str, int]:
    if value is None:
        return {}
    parsed = _require_mapping(value, field="statistics")
    result: dict[str, int] = {}
    for key, raw_value in parsed.items():
        if type(raw_value) is not int or raw_value < 0:
            raise BedrockIngestionAdapterError(
                f"statistics.{key} must be a non-negative integer"
            )
        result[key] = raw_value
    return result


def _optional_failure_reasons(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise BedrockIngestionAdapterError("failureReasons must be a list")
    raw = cast(list[object], value)
    return tuple(
        _require_trimmed(item, field=f"failureReasons[{index}]")
        for index, item in enumerate(raw)
    )


def _parse_job(response: object) -> IngestionJobEvidence:
    parsed = _require_mapping(response, field="Bedrock response")
    job = _require_mapping(parsed.get("ingestionJob"), field="ingestionJob")
    return IngestionJobEvidence(
        knowledge_base_id=_require_trimmed(
            job.get("knowledgeBaseId"), field="knowledgeBaseId"
        ),
        data_source_id=_require_trimmed(job.get("dataSourceId"), field="dataSourceId"),
        ingestion_job_id=_require_trimmed(
            job.get("ingestionJobId"), field="ingestionJobId"
        ),
        status=_require_trimmed(job.get("status"), field="status"),
        statistics=_optional_statistics(job.get("statistics")),
        failure_reasons=_optional_failure_reasons(job.get("failureReasons")),
    )


class BoundedBedrockIngestionControl:
    """Start and inspect exactly one Knowledge Base ingestion job at a time."""

    def __init__(self, client: BedrockIngestionClient) -> None:
        """Bind one injected dynamic client to the bounded adapter surface."""
        self._client = client

    def start(self, *, knowledge_base_id: str, data_source_id: str) -> IngestionJobEvidence:
        """Start one ingestion job using only the exact supplied target identifiers."""
        try:
            response = self._client.start_ingestion_job(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id,
                description="OpsLens Gate 7.3 canonical corpus ingestion",
            )
        except Exception as exc:
            raise BedrockIngestionAdapterError("Bedrock StartIngestionJob failed") from exc
        return _parse_job(response)

    def get(
        self,
        *,
        knowledge_base_id: str,
        data_source_id: str,
        ingestion_job_id: str,
    ) -> IngestionJobEvidence:
        """Read one exact ingestion job without list/discovery permissions."""
        try:
            response = self._client.get_ingestion_job(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id,
                ingestionJobId=ingestion_job_id,
            )
        except Exception as exc:
            raise BedrockIngestionAdapterError("Bedrock GetIngestionJob failed") from exc
        return _parse_job(response)
