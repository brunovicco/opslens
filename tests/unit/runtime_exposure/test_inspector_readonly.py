"""Tests for the bounded Amazon Inspector read-only discovery adapter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from botocore.exceptions import ClientError

from opslens.runtime_exposure.adapters.inspector_readonly import (
    run_readonly_inspector_discovery,
)

_ACCOUNT = "487757851499"
_REGION = "us-east-1"


class FakeInspectorClient:
    """Deterministic fake implementing only the two authorized Inspector APIs."""

    def __init__(
        self,
        *,
        coverage_pages: list[dict[str, object]] | None = None,
        finding_pages: list[dict[str, object]] | None = None,
        coverage_error: ClientError | None = None,
        findings_error: ClientError | None = None,
    ) -> None:
        """Store fake pages and optional API failures."""
        self.coverage_pages = coverage_pages or []
        self.finding_pages = finding_pages or []
        self.coverage_error = coverage_error
        self.findings_error = findings_error
        self.coverage_calls = 0
        self.finding_calls = 0

    def list_coverage(self, **kwargs: object) -> dict[str, object]:
        """Return the next fake coverage page."""
        del kwargs
        self.coverage_calls += 1
        if self.coverage_error is not None:
            raise self.coverage_error
        return self.coverage_pages[self.coverage_calls - 1]

    def list_findings(self, **kwargs: object) -> dict[str, object]:
        """Return the next fake findings page."""
        del kwargs
        self.finding_calls += 1
        if self.findings_error is not None:
            raise self.findings_error
        return self.finding_pages[self.finding_calls - 1]


def _metadata(*, retries: int = 0) -> dict[str, object]:
    """Build minimal botocore response metadata."""
    return {"RetryAttempts": retries}


def _coverage_page(*, next_token: str | None = None) -> dict[str, object]:
    """Build one representative Inspector coverage page."""
    value: dict[str, object] = {
        "coveredResources": [
            {
                "accountId": _ACCOUNT,
                "resourceId": "arn:aws:lambda:us-east-1:487757851499:function:opslens-dev-api",
                "resourceType": "AWS_LAMBDA_FUNCTION",
                "scanType": "PACKAGE",
                "scanStatus": {"statusCode": "ACTIVE", "reason": "SUCCESSFUL"},
                "lastScannedAt": datetime(2026, 9, 9, 20, 0, tzinfo=UTC),
            }
        ],
        "ResponseMetadata": _metadata(retries=1),
    }
    if next_token is not None:
        value["nextToken"] = next_token
    return value


def _findings_page() -> dict[str, object]:
    """Build representative package and EC2 network findings."""
    return {
        "findings": [
            {
                "awsAccountId": _ACCOUNT,
                "findingArn": "arn:aws:inspector2:us-east-1:487757851499:finding/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "type": "PACKAGE_VULNERABILITY",
                "status": "ACTIVE",
                "resources": [
                    {
                        "id": "arn:aws:lambda:us-east-1:487757851499:function:opslens-dev-api",
                        "type": "AWS_LAMBDA_FUNCTION",
                    }
                ],
            },
            {
                "awsAccountId": _ACCOUNT,
                "findingArn": "arn:aws:inspector2:us-east-1:487757851499:finding/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "type": "NETWORK_REACHABILITY",
                "status": "ACTIVE",
                "resources": [{"id": "i-0123456789abcdef0", "type": "AWS_EC2_INSTANCE"}],
            },
        ],
        "ResponseMetadata": _metadata(),
    }


def _client_error(code: str) -> ClientError:
    """Build one deterministic AWS ClientError."""
    return ClientError(
        error_response={"Error": {"Code": code, "Message": "denied"}},
        operation_name="ListCoverage",
    )


def test_discovers_independent_runtime_dimensions() -> None:
    """Count coverage/findings without collapsing their authority classes."""
    client = FakeInspectorClient(
        coverage_pages=[_coverage_page()],
        finding_pages=[_findings_page()],
    )

    evidence = run_readonly_inspector_discovery(
        client=client,
        region=_REGION,
        expected_account_id=_ACCOUNT,
    )

    assert evidence.result == "SUCCESS"
    assert evidence.coverage.record_count == 1
    assert evidence.findings.record_count == 2
    assert evidence.coverage_resource_type_counts == (("AWS_LAMBDA_FUNCTION", 1),)
    assert evidence.finding_resource_type_counts == (
        ("AWS_EC2_INSTANCE", 1),
        ("AWS_LAMBDA_FUNCTION", 1),
    )
    assert evidence.finding_type_counts == (
        ("NETWORK_REACHABILITY", 1),
        ("PACKAGE_VULNERABILITY", 1),
    )
    assert evidence.scan_status_counts == (("ACTIVE", 1),)
    assert evidence.coverage.sdk_retry_count == 1
    assert evidence.aws_mutation_count == 0
    assert evidence.new_iam_count == 0
    assert evidence.model_invocations == 0
    assert evidence.capability_executions == 0


def test_paginates_and_hashes_business_records_only() -> None:
    """Preserve page count/hash evidence without persisting opaque tokens."""
    first = _coverage_page(next_token="opaque-token")
    second = {"coveredResources": [], "ResponseMetadata": _metadata()}
    client = FakeInspectorClient(
        coverage_pages=[first, second],
        finding_pages=[{"findings": [], "ResponseMetadata": _metadata()}],
    )

    evidence = run_readonly_inspector_discovery(
        client=client,
        region=_REGION,
        expected_account_id=_ACCOUNT,
    )

    assert evidence.coverage.page_count == 2
    assert len(evidence.coverage.page_content_sha256) == 2
    assert all(len(value) == 64 for value in evidence.coverage.page_content_sha256)
    assert evidence.coverage.record_count == 1
    assert client.coverage_calls == 2


def test_access_denied_stops_before_second_api() -> None:
    """Treat existing-IAM denial as terminal evidence without widening authority."""
    client = FakeInspectorClient(coverage_error=_client_error("AccessDeniedException"))

    evidence = run_readonly_inspector_discovery(
        client=client,
        region=_REGION,
        expected_account_id=_ACCOUNT,
    )

    assert evidence.result == "BLOCKED_BY_EXISTING_IAM"
    assert evidence.coverage.outcome == "ACCESS_DENIED"
    assert evidence.coverage.error_code == "AccessDeniedException"
    assert evidence.findings.attempted is False
    assert client.finding_calls == 0


def test_findings_access_denied_preserves_coverage_evidence() -> None:
    """Stop after coverage when ListFindings is denied."""
    client = FakeInspectorClient(
        coverage_pages=[_coverage_page()],
        findings_error=_client_error("AccessDenied"),
    )

    evidence = run_readonly_inspector_discovery(
        client=client,
        region=_REGION,
        expected_account_id=_ACCOUNT,
    )

    assert evidence.result == "BLOCKED_BY_EXISTING_IAM"
    assert evidence.coverage.outcome == "SUCCESS"
    assert evidence.findings.outcome == "ACCESS_DENIED"
    assert evidence.coverage_resource_type_counts == (("AWS_LAMBDA_FUNCTION", 1),)


def test_rejects_network_reachability_for_non_ec2_resource() -> None:
    """Fail closed if upstream data violates the frozen EC2-only reachability boundary."""
    invalid = _findings_page()
    findings = invalid["findings"]
    assert isinstance(findings, list)
    network_finding = findings[1]
    assert isinstance(network_finding, dict)
    network_finding["resources"] = [
        {
            "id": "arn:aws:lambda:us-east-1:487757851499:function:unexpected",
            "type": "AWS_LAMBDA_FUNCTION",
        }
    ]
    client = FakeInspectorClient(
        coverage_pages=[_coverage_page()],
        finding_pages=[invalid],
    )

    with pytest.raises(ValueError, match="EC2-only"):
        run_readonly_inspector_discovery(
            client=client,
            region=_REGION,
            expected_account_id=_ACCOUNT,
        )


def test_rejects_cross_account_runtime_evidence() -> None:
    """Reject Inspector evidence outside the expected account boundary."""
    page = _coverage_page()
    records = page["coveredResources"]
    assert isinstance(records, list)
    record = records[0]
    assert isinstance(record, dict)
    record["accountId"] = "000000000000"
    client = FakeInspectorClient(
        coverage_pages=[page],
        finding_pages=[{"findings": [], "ResponseMetadata": _metadata()}],
    )

    with pytest.raises(ValueError, match="expected account"):
        run_readonly_inspector_discovery(
            client=client,
            region=_REGION,
            expected_account_id=_ACCOUNT,
        )
