"""Tests for Phase 9 bounded semantic planning proposal and admission handoff."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from hashlib import sha256

import pytest

from opslens.hybrid_retrieval.domain import (
    CompletenessSemantics,
    EvidenceClass,
    EvidenceNeed,
    HybridRoute,
)
from opslens.public_analysis.application import (
    MAX_PUBLIC_SEMANTIC_PLAN_RESPONSE_BYTES,
    PublicSemanticPlanAdmissionError,
    admit_public_analysis_request,
    admit_public_semantic_plan,
    build_public_repository_evidence,
    build_public_semantic_planning_request,
    parse_public_semantic_plan_proposal,
    plan_public_analysis_handoff,
)
from opslens.public_analysis.domain import (
    MAX_PUBLIC_SEMANTIC_PLANNING_REQUEST_BYTES,
    PUBLIC_ANALYSIS_HANDOFF_CONTRACT_VERSION,
    PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS,
    PUBLIC_SEMANTIC_PLANNING_CONTRACT_VERSION,
    PublicAnalysisRequest,
    PublicRepositoryEvidenceExecution,
)
from opslens.repository_intelligence.domain import compute_git_blob_sha1

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "3f75a4fc2bd22589df0a5ffe98a8442fda81c8d3"
_TREE_SHA = "01ac6fe03f1db867ef29c6652311ee43b1f63afb"


def _request(*, requested_ref: str | None = None) -> PublicAnalysisRequest:
    """Admit one request through the real Gate 9.1 boundary."""
    ref_json = "null" if requested_ref is None else f'"{requested_ref}"'
    raw = (
        '{"repository_url":"https://github.com/brunovicco/opslens",'
        f'"requested_ref":{ref_json}}}'
    ).encode()
    return admit_public_analysis_request(raw).request


def _uv_lock_content() -> bytes:
    """Return small inert dependency evidence that must never enter planner input."""
    return (
        b"version = 1\n"
        b"revision = 3\n"
        b'[[package]]\n'
        b'name = "Requests"\n'
        b'version = "2.31.0"\n'
        b'source = { registry = "https://pypi.org/simple" }\n'
    )


def _uv_lock_payload() -> dict[str, object]:
    """Build the exact GitHub Contents shape admitted by Phase 4."""
    content = _uv_lock_content()
    return {
        "type": "file",
        "path": "uv.lock",
        "name": "uv.lock",
        "encoding": "base64",
        "size": len(content),
        "sha": compute_git_blob_sha1(content),
        "content": base64.encodebytes(content).decode("ascii"),
    }


@dataclass(slots=True)
class FakeRepositorySource:
    """Provide deterministic Gate 9.2 source evidence without network calls."""

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        """Return one public repository metadata response."""
        assert (owner, name) == ("brunovicco", "opslens")
        return {
            "id": _REPOSITORY_ID,
            "name": "opslens",
            "full_name": "brunovicco/opslens",
            "private": False,
            "visibility": "public",
            "default_branch": "main",
            "owner": {"login": "brunovicco"},
        }

    def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
        """Return one immutable commit/tree response."""
        assert (owner, name, ref) == ("brunovicco", "opslens", "main")
        return {
            "sha": _COMMIT_SHA,
            "commit": {"tree": {"sha": _TREE_SHA}},
        }

    def get_uv_lock(
        self,
        owner: str,
        name: str,
        commit_sha: str,
    ) -> dict[str, object]:
        """Return exact-commit inert lock evidence."""
        assert (owner, name, commit_sha) == (
            "brunovicco",
            "opslens",
            _COMMIT_SHA,
        )
        return _uv_lock_payload()


def _execution(*, requested_ref: str | None = None) -> PublicRepositoryEvidenceExecution:
    """Build one verified Gate 9.2 execution entirely from fake source evidence."""
    return build_public_repository_evidence(
        _request(requested_ref=requested_ref),
        FakeRepositorySource(),
    )


def _required_need_values() -> tuple[str, ...]:
    """Return the exact public v1 planner-output values."""
    return tuple(need.value for need in PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS)


@dataclass(slots=True)
class FakeSemanticPlanner:
    """Return one configurable untrusted proposal and record exact call count/input."""

    evidence_needs: tuple[str, ...] = field(default_factory=_required_need_values)
    raw_response: bytes | None = None
    fail: bool = False
    calls: list[bytes] = field(default_factory=lambda: list[bytes]())

    def plan(self, request_json: bytes) -> bytes:
        """Produce one proposal bound to the exact serialized planning request."""
        self.calls.append(request_json)
        if self.fail:
            raise RuntimeError("fake planner unavailable")
        if self.raw_response is not None:
            return self.raw_response
        payload: dict[str, object] = {
            "planning_request_sha256": sha256(request_json).hexdigest(),
            "evidence_needs": list(self.evidence_needs),
        }
        return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def test_successful_plan_is_content_free_and_routes_through_phase8_authority() -> None:
    """One admitted proposal yields a HYBRID/ALL_REQUIRED handoff and nothing more."""
    execution = _execution()
    planner = FakeSemanticPlanner()

    handoff = plan_public_analysis_handoff(execution, planner)

    assert len(planner.calls) == 1
    planner_input = planner.calls[0]
    assert b"https://github.com/" not in planner_input
    assert b"Requests" not in planner_input
    assert b"2.31.0" not in planner_input
    assert b"source =" not in planner_input
    assert len(planner_input) <= MAX_PUBLIC_SEMANTIC_PLANNING_REQUEST_BYTES

    decoded = json.loads(planner_input)
    assert decoded["contract_version"] == PUBLIC_SEMANTIC_PLANNING_CONTRACT_VERSION
    assert decoded["operation"] == "analyze_public_repository"
    assert decoded["allowed_evidence_needs"] == list(_required_need_values())
    assert decoded["source"]["normalized_dependency_count"] == 1
    assert decoded["source"]["file_evidence_id"] == execution.file_evidence_id

    assert handoff.source_execution is execution
    assert handoff.proposal.evidence_needs == PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS
    assert handoff.route_decision.route is HybridRoute.HYBRID
    assert handoff.route_decision.completeness is CompletenessSemantics.ALL_REQUIRED
    assert handoff.route_decision.required_evidence_classes == (
        EvidenceClass.STRUCTURED,
        EvidenceClass.SEMANTIC,
    )
    assert handoff.handoff_id.startswith(
        f"{PUBLIC_ANALYSIS_HANDOFF_CONTRACT_VERSION}@sha256:"
    )
    assert b"Requests" not in handoff.canonical_json
    assert b"uv.lock" not in handoff.canonical_json


def test_equivalent_evidence_and_plan_produce_same_handoff_identity() -> None:
    """Handoff identity is content-addressed rather than object-identity based."""
    first = plan_public_analysis_handoff(_execution(), FakeSemanticPlanner())
    second = plan_public_analysis_handoff(_execution(), FakeSemanticPlanner())

    assert first.handoff_sha256 == second.handoff_sha256
    assert first.handoff_id == second.handoff_id


@pytest.mark.parametrize(
    "needs",
    [
        (EvidenceNeed.VULNERABILITY_FACTS.value, EvidenceNeed.REMEDIATION_GUIDANCE.value),
        (
            EvidenceNeed.VULNERABILITY_FACTS.value,
            EvidenceNeed.RISK_PRIORITY.value,
            EvidenceNeed.RUNTIME_EXPOSURE.value,
        ),
    ],
)
def test_under_scoped_or_out_of_authority_plan_fails_closed(
    needs: tuple[str, ...],
) -> None:
    """The planner cannot remove mandatory risk work or add runtime-exposure authority."""
    planner = FakeSemanticPlanner(evidence_needs=needs)

    with pytest.raises(PublicSemanticPlanAdmissionError):
        plan_public_analysis_handoff(_execution(), planner)

    assert len(planner.calls) == 1


@pytest.mark.parametrize(
    "needs",
    [
        ("not_a_known_need",),
        (
            EvidenceNeed.VULNERABILITY_FACTS.value,
            EvidenceNeed.VULNERABILITY_FACTS.value,
        ),
    ],
)
def test_unknown_or_duplicate_evidence_need_fails_structural_admission(
    needs: tuple[str, ...],
) -> None:
    """Malformed proposal semantics fail before deterministic route authority is invoked."""
    planner = FakeSemanticPlanner(evidence_needs=needs)

    with pytest.raises(PublicSemanticPlanAdmissionError):
        plan_public_analysis_handoff(_execution(), planner)

    assert len(planner.calls) == 1


@pytest.mark.parametrize(
    "raw_response",
    [
        b"not-json",
        b"[]",
        b'{"planning_request_sha256":"x"}',
        b'{"planning_request_sha256":"x","evidence_needs":[],"extra":true}',
        b'{"planning_request_sha256":"x","evidence_needs":[],"evidence_needs":[]}',
    ],
)
def test_malformed_planner_output_fails_closed(raw_response: bytes) -> None:
    """JSON and exact-shape violations cannot become semantic plan proposals."""
    planner = FakeSemanticPlanner(raw_response=raw_response)

    with pytest.raises(PublicSemanticPlanAdmissionError):
        plan_public_analysis_handoff(_execution(), planner)

    assert len(planner.calls) == 1


def test_proposal_for_another_planning_request_is_rejected() -> None:
    """A structurally plausible proposal cannot be replayed against another execution."""
    execution = _execution()
    planning_request = build_public_semantic_planning_request(execution)
    raw = json.dumps(
        {
            "planning_request_sha256": "0" * 64,
            "evidence_needs": list(_required_need_values()),
        }
    ).encode()

    with pytest.raises(PublicSemanticPlanAdmissionError):
        parse_public_semantic_plan_proposal(
            raw,
            planning_request=planning_request,
        )


def test_proposal_cannot_be_admitted_against_another_source_execution() -> None:
    """A valid proposal/request pair cannot be rebound to another Gate 9.2 execution."""
    first_execution = _execution()
    planning_request = build_public_semantic_planning_request(first_execution)
    planner = FakeSemanticPlanner()
    raw_response = planner.plan(planning_request.canonical_json)
    proposal = parse_public_semantic_plan_proposal(
        raw_response,
        planning_request=planning_request,
    )
    different_execution = _execution(requested_ref="main")

    assert different_execution.execution_id != first_execution.execution_id
    with pytest.raises(PublicSemanticPlanAdmissionError):
        admit_public_semantic_plan(
            proposal,
            planning_request=planning_request,
            source_execution=different_execution,
        )


def test_oversized_planner_output_fails_before_json_decode() -> None:
    """The planner cannot force unbounded response parsing."""
    execution = _execution()
    planning_request = build_public_semantic_planning_request(execution)

    with pytest.raises(PublicSemanticPlanAdmissionError):
        parse_public_semantic_plan_proposal(
            b"x" * (MAX_PUBLIC_SEMANTIC_PLAN_RESPONSE_BYTES + 1),
            planning_request=planning_request,
        )


def test_planner_failure_is_not_retried_or_converted_into_a_handoff() -> None:
    """Application orchestration performs no adaptive retry after planner failure."""
    planner = FakeSemanticPlanner(fail=True)

    with pytest.raises(RuntimeError, match="fake planner unavailable"):
        plan_public_analysis_handoff(_execution(), planner)

    assert len(planner.calls) == 1


def test_planning_request_is_bound_to_gate9_2_execution_accounting() -> None:
    """The metadata-only request preserves exact source identity and dependency accounting."""
    execution = _execution()
    request = build_public_semantic_planning_request(execution)

    assert request.source_execution_id == execution.execution_id
    assert request.source_execution_sha256 == execution.evidence_sha256
    assert request.public_request_id == execution.request.request_id
    assert request.snapshot_id == execution.snapshot_id
    assert request.file_evidence_id == execution.file_evidence_id
    assert request.normalized_dependency_count == 1
    assert request.unsupported_package_count == 0
    assert request.unsupported_normalization_count == 0
