"""Tests for bounded Gate 7.3 Bedrock ingestion orchestration and adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from opslens.knowledge_retrieval.adapters.bedrock_ingestion import (
    BedrockIngestionClient,
    BoundedBedrockIngestionControl,
)
from opslens.knowledge_retrieval.application.bedrock_ingestion import (
    BedrockIngestionFailed,
    BedrockIngestionTimeout,
    BedrockIngestionValidationError,
    IngestionJobEvidence,
    run_bounded_ingestion,
)
from opslens.knowledge_retrieval.cli.run_bedrock_ingestion import (
    IngestionCliError,
    require_ingestion_region,
    serialize_ingestion_evidence,
)

KB_ID = "BTVJ2PBR2A"
DS_ID = "IEL1LBE026"
JOB_ID = "JOB1234567"


def _evidence(status: str, *, failed: int = 0) -> IngestionJobEvidence:
    return IngestionJobEvidence(
        knowledge_base_id=KB_ID,
        data_source_id=DS_ID,
        ingestion_job_id=JOB_ID,
        status=status,
        statistics={
            "numberOfDocumentsScanned": 9,
            "numberOfNewDocumentsIndexed": 9 if status == "COMPLETE" else 0,
            "numberOfDocumentsFailed": failed,
        },
        failure_reasons=("synthetic failure",) if status == "FAILED" else (),
    )


@dataclass
class FakeControl:
    """Deterministic provider-neutral ingestion control for orchestration tests."""

    states: list[IngestionJobEvidence]
    get_calls: int = 0

    def start(self, *, knowledge_base_id: str, data_source_id: str) -> IngestionJobEvidence:
        assert knowledge_base_id == KB_ID
        assert data_source_id == DS_ID
        return self.states[0]

    def get(
        self,
        *,
        knowledge_base_id: str,
        data_source_id: str,
        ingestion_job_id: str,
    ) -> IngestionJobEvidence:
        assert knowledge_base_id == KB_ID
        assert data_source_id == DS_ID
        assert ingestion_job_id == JOB_ID
        self.get_calls += 1
        return self.states[self.get_calls]


def test_run_bounded_ingestion_reaches_complete_without_unbounded_polling() -> None:
    control = FakeControl([_evidence("STARTING"), _evidence("IN_PROGRESS"), _evidence("COMPLETE")])
    sleeps: list[float] = []

    result = run_bounded_ingestion(
        control,
        knowledge_base_id=KB_ID,
        data_source_id=DS_ID,
        max_polls=3,
        poll_interval_seconds=0.25,
        sleeper=sleeps.append,
    )

    assert result.status == "COMPLETE"
    assert result.statistics["numberOfNewDocumentsIndexed"] == 9
    assert control.get_calls == 2
    assert sleeps == [0.25, 0.25]


def test_run_bounded_ingestion_fails_closed_on_failed_terminal_state() -> None:
    control = FakeControl([_evidence("FAILED", failed=1)])

    with pytest.raises(BedrockIngestionFailed, match="synthetic failure"):
        run_bounded_ingestion(
            control,
            knowledge_base_id=KB_ID,
            data_source_id=DS_ID,
            poll_interval_seconds=0,
        )


def test_run_bounded_ingestion_times_out_after_exact_poll_budget() -> None:
    control = FakeControl([_evidence("STARTING"), _evidence("IN_PROGRESS")])

    with pytest.raises(BedrockIngestionTimeout, match="after 1 polls"):
        run_bounded_ingestion(
            control,
            knowledge_base_id=KB_ID,
            data_source_id=DS_ID,
            max_polls=1,
            poll_interval_seconds=0,
        )

    assert control.get_calls == 1


def test_ingestion_evidence_rejects_unknown_statistics() -> None:
    with pytest.raises(BedrockIngestionValidationError, match="unsupported fields"):
        IngestionJobEvidence(
            knowledge_base_id=KB_ID,
            data_source_id=DS_ID,
            ingestion_job_id=JOB_ID,
            status="COMPLETE",
            statistics={"providerInventedCounter": 1},
        )


@dataclass
class FakeBedrockClient:
    """Small dynamic-client fake preserving exact Bedrock request arguments."""

    calls: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    def start_ingestion_job(self, **kwargs: object) -> object:
        self.calls.append(("start", dict(kwargs)))
        return {
            "ingestionJob": {
                "knowledgeBaseId": KB_ID,
                "dataSourceId": DS_ID,
                "ingestionJobId": JOB_ID,
                "status": "STARTING",
                "statistics": {"numberOfDocumentsScanned": 0},
            }
        }

    def get_ingestion_job(self, **kwargs: object) -> object:
        self.calls.append(("get", dict(kwargs)))
        return {
            "ingestionJob": {
                "knowledgeBaseId": KB_ID,
                "dataSourceId": DS_ID,
                "ingestionJobId": JOB_ID,
                "status": "COMPLETE",
                "statistics": {
                    "numberOfDocumentsScanned": 9,
                    "numberOfNewDocumentsIndexed": 9,
                    "numberOfModifiedDocumentsIndexed": 0,
                    "numberOfDocumentsDeleted": 0,
                    "numberOfDocumentsFailed": 0,
                },
            }
        }


def test_bedrock_adapter_uses_exact_identifiers_without_discovery_calls() -> None:
    raw_client = FakeBedrockClient()
    client: BedrockIngestionClient = raw_client
    control = BoundedBedrockIngestionControl(client)

    started = control.start(knowledge_base_id=KB_ID, data_source_id=DS_ID)
    completed = control.get(
        knowledge_base_id=KB_ID,
        data_source_id=DS_ID,
        ingestion_job_id=started.ingestion_job_id,
    )

    assert completed.status == "COMPLETE"
    assert raw_client.calls[0] == (
        "start",
        {
            "knowledgeBaseId": KB_ID,
            "dataSourceId": DS_ID,
            "description": "OpsLens Gate 7.3 canonical corpus ingestion",
        },
    )
    assert raw_client.calls[1] == (
        "get",
        {
            "knowledgeBaseId": KB_ID,
            "dataSourceId": DS_ID,
            "ingestionJobId": JOB_ID,
        },
    )


def test_ingestion_cli_evidence_is_bounded_and_content_free() -> None:
    serialized = serialize_ingestion_evidence(_evidence("COMPLETE"), region="us-east-1")
    parsed = json.loads(serialized)

    assert parsed == {
        "data_source_id": DS_ID,
        "failure_reasons": [],
        "ingestion_job_id": JOB_ID,
        "knowledge_base_id": KB_ID,
        "region": "us-east-1",
        "statistics": {
            "numberOfDocumentsFailed": 0,
            "numberOfDocumentsScanned": 9,
            "numberOfNewDocumentsIndexed": 9,
        },
        "status": "COMPLETE",
    }
    assert "content" not in serialized.lower()


def test_ingestion_cli_requires_frozen_region() -> None:
    assert require_ingestion_region("us-east-1") == "us-east-1"
    with pytest.raises(IngestionCliError, match="frozen Gate 7.3 region"):
        require_ingestion_region("us-west-2")
