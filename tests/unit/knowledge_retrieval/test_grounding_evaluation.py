"""Unit tests for Gate 7.7 frozen citation/groundedness evaluation semantics."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from opslens.knowledge_retrieval.application.citation_projection import (
    project_citation_catalog,
)
from opslens.knowledge_retrieval.application.context_assembly import (
    assemble_retrieval_context,
)
from opslens.knowledge_retrieval.application.corpus_config import (
    load_corpus_manifest,
)
from opslens.knowledge_retrieval.application.grounding_contract import (
    build_grounded_synthesis_request,
    parse_grounded_synthesis_output,
)
from opslens.knowledge_retrieval.application.grounding_evaluation import (
    ClaimCitationSupportJudgment,
    GoldenGroundingCase,
    GoldenGroundingDataset,
    GroundingCaseObservation,
    GroundingEvaluationError,
    GroundingSupportJudgmentSource,
    evaluate_grounding_case,
    evaluate_grounding_dataset,
    load_golden_grounding_dataset,
    validate_grounding_dataset_catalog,
)
from opslens.knowledge_retrieval.application.retrieval_catalog import (
    build_retrieval_catalog,
)
from opslens.knowledge_retrieval.application.synthesis_contract import (
    build_synthesis_request,
)
from opslens.knowledge_retrieval.domain import (
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
    SynthesisAuthorityDecision,
    SynthesisDecision,
)

_REPO_ROOT = Path(__file__).parents[3]
FIXTURE = (
    _REPO_ROOT
    / "tests"
    / "fixtures"
    / "knowledge_retrieval"
    / "golden_grounding_v1.json"
)
_MANIFEST = _REPO_ROOT / "knowledge" / "corpus" / "v1" / "manifest.json"
QUESTION = "How should I verify dependency artifacts?"


def _question_sha256(question: str) -> str:
    """Return deterministic question identity for one observation."""
    return sha256(question.encode("utf-8")).hexdigest()


def _request(
    *,
    chunk_ids: tuple[str, ...] = (
        "knowledge-chunk:test:grounding:one:v1",
        "knowledge-chunk:test:grounding:two:v1",
        "knowledge-chunk:test:grounding:three:v1",
    ),
):
    """Build one offline grounded request with deterministic citation IDs."""
    chunks = tuple(
        RetrievedChunk.from_text(
            chunk_id=chunk_id,
            document_id=f"knowledge-doc:test:grounding:{index}:v1",
            source_id=f"source:test:grounding:{index}",
            source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
            canonical_uri=f"https://example.com/grounding/{index}",
            document_content_sha256=str(index) * 64,
            text=f"Grounding evidence block {index}.",
            rank=index,
            relevance_score=1.0 - (index / 10),
            title=f"Grounding block {index}",
            section_path=(f"Section {index}",),
        )
        for index, chunk_id in enumerate(chunk_ids, start=1)
    )
    evidence = RetrievalEvidence(
        retrieval_id="retrieval:gate-7-7c:test",
        request=RetrievalRequest(query=QUESTION, top_k=len(chunks)),
        chunks=chunks,
        backend=RetrievalBackend.OFFLINE_GOLDEN,
    )
    context = assemble_retrieval_context(evidence)
    synthesis_request = build_synthesis_request(
        question=QUESTION,
        context=context,
        authority_decision=SynthesisAuthorityDecision.SUPPORTED,
    )
    return build_grounded_synthesis_request(
        synthesis_request=synthesis_request,
        citation_catalog=project_citation_catalog(context),
    )


def _answer_observation(
    *,
    case_id: str,
    claims: list[dict[str, object]],
    supports: tuple[bool, ...],
    chunk_ids: tuple[str, ...] = (
        "knowledge-chunk:test:grounding:one:v1",
        "knowledge-chunk:test:grounding:two:v1",
        "knowledge-chunk:test:grounding:three:v1",
    ),
) -> GroundingCaseObservation:
    """Build one answer observation with pair judgments in emitted pair order."""
    request = _request(chunk_ids=chunk_ids)
    result = parse_grounded_synthesis_output(
        json.dumps({"decision": "answer", "claims": claims}),
        request=request,
    )
    pairs = tuple(
        (claim.claim_sha256, citation_id)
        for claim in result.claims
        for citation_id in claim.citation_ids
    )
    assert len(pairs) == len(supports)
    judgments = tuple(
        ClaimCitationSupportJudgment.create(
            claim_sha256=claim_sha256,
            citation_id=citation_id,
            supports_claim=supported,
        )
        for (claim_sha256, citation_id), supported in zip(
            pairs,
            supports,
            strict=True,
        )
    )
    return GroundingCaseObservation(
        case_id=case_id,
        question_sha256=_question_sha256(QUESTION),
        citation_catalog=request.citation_catalog,
        result=result,
        support_judgments=judgments,
    )


def _abstention_observation(*, case_id: str) -> GroundingCaseObservation:
    """Build one clean zero-claim insufficient-evidence observation."""
    request = _request()
    result = parse_grounded_synthesis_output(
        json.dumps(
            {"decision": "insufficient_evidence", "claims": []}
        ),
        request=request,
    )
    return GroundingCaseObservation(
        case_id=case_id,
        question_sha256=_question_sha256(QUESTION),
        citation_catalog=request.citation_catalog,
        result=result,
        support_judgments=(),
    )


def test_checked_grounding_fixture_is_frozen_before_provider_changes() -> None:
    """The v1 fixture fixes case count, decision split, and target cardinality."""
    dataset = load_golden_grounding_dataset(FIXTURE)
    catalog = build_retrieval_catalog(load_corpus_manifest(_MANIFEST))

    validate_grounding_dataset_catalog(dataset, catalog)

    assert dataset.dataset_id == "knowledge-grounding-golden:v1"
    assert len(dataset.cases) == 4
    assert sum(
        case.expected_decision is SynthesisDecision.ANSWER
        for case in dataset.cases
    ) == 3
    assert sum(
        case.expected_decision is SynthesisDecision.INSUFFICIENT_EVIDENCE
        for case in dataset.cases
    ) == 1
    assert dataset.cases[1].expected_citation_chunk_ids == (
        "knowledge-chunk:pypa-dependency-management:transitive-review:v1",
        "knowledge-chunk:uv-locking:diff-review:v1",
    )


def test_target_quality_and_semantic_support_are_separate_metrics() -> None:
    """Correct targets do not imply every attached citation semantically supports."""
    case = GoldenGroundingCase(
        case_id="case-target-semantics",
        question=QUESTION,
        authority_decision="supported",
        expected_decision=SynthesisDecision.ANSWER,
        expected_citation_chunk_ids=(
            "knowledge-chunk:test:grounding:one:v1",
            "knowledge-chunk:test:grounding:two:v1",
        ),
    )
    observation = _answer_observation(
        case_id=case.case_id,
        claims=[
            {
                "text": "Use the first evidence item.",
                "citation_ids": ["C1", "C3"],
            },
            {
                "text": "Use the second evidence item.",
                "citation_ids": ["C2"],
            },
        ],
        supports=(True, False, True),
    )

    metrics = evaluate_grounding_case(case, observation)

    assert metrics.citation_target_precision == pytest.approx(2 / 3)
    assert metrics.citation_target_recall == 1.0
    assert metrics.claim_supportedness_rate == 1.0
    assert metrics.unsupported_claim_rate == 0.0
    assert metrics.citation_correctness_rate == pytest.approx(2 / 3)


def test_valid_target_can_still_support_zero_claims() -> None:
    """Syntactically valid and target-correct C1 can still fail groundedness."""
    case = GoldenGroundingCase(
        case_id="case-valid-but-unsupported",
        question=QUESTION,
        authority_decision="supported",
        expected_decision=SynthesisDecision.ANSWER,
        expected_citation_chunk_ids=(
            "knowledge-chunk:test:grounding:one:v1",
        ),
    )
    observation = _answer_observation(
        case_id=case.case_id,
        claims=[
            {
                "text": "An unsupported statement attached to C1.",
                "citation_ids": ["C1"],
            }
        ],
        supports=(False,),
    )

    metrics = evaluate_grounding_case(case, observation)

    assert metrics.citation_target_precision == 1.0
    assert metrics.citation_target_recall == 1.0
    assert metrics.claim_supportedness_rate == 0.0
    assert metrics.unsupported_claim_rate == 1.0
    assert metrics.citation_correctness_rate == 0.0


def test_observation_requires_complete_pair_level_judgments() -> None:
    """Human support labels must cover every emitted claim/citation pair exactly."""
    request = _request()
    result = parse_grounded_synthesis_output(
        json.dumps(
            {
                "decision": "answer",
                "claims": [
                    {
                        "text": "One claim with two citations.",
                        "citation_ids": ["C1", "C2"],
                    }
                ],
            }
        ),
        request=request,
    )
    incomplete = (
        ClaimCitationSupportJudgment.create(
            claim_sha256=result.claims[0].claim_sha256,
            citation_id="C1",
            supports_claim=True,
            source=GroundingSupportJudgmentSource.HUMAN_REVIEWED,
        ),
    )

    with pytest.raises(
        GroundingEvaluationError,
        match="cover every and only emitted",
    ):
        GroundingCaseObservation(
            case_id="case-incomplete",
            question_sha256=_question_sha256(QUESTION),
            citation_catalog=request.citation_catalog,
            result=result,
            support_judgments=incomplete,
        )


def test_clean_abstention_has_no_fake_groundedness_rate() -> None:
    """Zero-claim abstention is correct without inventing a 100% grounded score."""
    case = GoldenGroundingCase(
        case_id="case-abstention",
        question=QUESTION,
        authority_decision="supported",
        expected_decision=SynthesisDecision.INSUFFICIENT_EVIDENCE,
        expected_citation_chunk_ids=(),
    )
    observation = _abstention_observation(case_id=case.case_id)

    metrics = evaluate_grounding_case(case, observation)

    assert metrics.decision_correct is True
    assert metrics.claim_count == 0
    assert metrics.citation_target_precision is None
    assert metrics.citation_target_recall is None
    assert metrics.claim_supportedness_rate is None
    assert metrics.unsupported_claim_rate is None
    assert metrics.citation_correctness_rate is None


def test_aggregate_metrics_are_micro_counted_and_abstention_is_explicit() -> None:
    """Aggregate target, claim, pair, and abstention metrics keep distinct denominators."""
    cases = (
        GoldenGroundingCase(
            case_id="aggregate-answer-one",
            question=QUESTION,
            authority_decision="supported",
            expected_decision=SynthesisDecision.ANSWER,
            expected_citation_chunk_ids=(
                "knowledge-chunk:test:grounding:one:v1",
            ),
        ),
        GoldenGroundingCase(
            case_id="aggregate-answer-two",
            question=QUESTION,
            authority_decision="supported",
            expected_decision=SynthesisDecision.ANSWER,
            expected_citation_chunk_ids=(
                "knowledge-chunk:test:grounding:one:v1",
                "knowledge-chunk:test:grounding:two:v1",
            ),
        ),
        GoldenGroundingCase(
            case_id="aggregate-answer-three",
            question=QUESTION,
            authority_decision="supported",
            expected_decision=SynthesisDecision.ANSWER,
            expected_citation_chunk_ids=(
                "knowledge-chunk:test:grounding:three:v1",
            ),
        ),
        GoldenGroundingCase(
            case_id="aggregate-abstain",
            question=QUESTION,
            authority_decision="supported",
            expected_decision=SynthesisDecision.INSUFFICIENT_EVIDENCE,
            expected_citation_chunk_ids=(),
        ),
    )
    dataset = GoldenGroundingDataset(
        dataset_id="knowledge-grounding-golden:v1",
        cases=cases,
    )
    observations = (
        _answer_observation(
            case_id="aggregate-answer-one",
            claims=[{"text": "Claim one.", "citation_ids": ["C1"]}],
            supports=(True,),
        ),
        _answer_observation(
            case_id="aggregate-answer-two",
            claims=[{"text": "Claim two.", "citation_ids": ["C1"]}],
            supports=(True,),
        ),
        _answer_observation(
            case_id="aggregate-answer-three",
            claims=[{"text": "Claim three.", "citation_ids": ["C2"]}],
            supports=(False,),
        ),
        _abstention_observation(case_id="aggregate-abstain"),
    )

    report = evaluate_grounding_dataset(dataset, observations)
    summary = report.summary

    assert summary.decision_accuracy == 1.0
    assert summary.citation_target_selected_count == 3
    assert summary.citation_target_expected_count == 4
    assert summary.citation_target_correct_count == 2
    assert summary.citation_target_precision == pytest.approx(2 / 3)
    assert summary.citation_target_recall == 0.5
    assert summary.claim_count == 3
    assert summary.claim_supportedness_rate == pytest.approx(2 / 3)
    assert summary.unsupported_claim_rate == pytest.approx(1 / 3)
    assert summary.citation_correctness_rate == pytest.approx(2 / 3)
    assert summary.abstention_precision == 1.0
    assert summary.abstention_recall == 1.0


def test_case_observation_is_bound_to_frozen_question_identity() -> None:
    """A grounded result cannot be scored under a different fixture question."""
    case = GoldenGroundingCase(
        case_id="case-question-binding",
        question="A different question",
        authority_decision="supported",
        expected_decision=SynthesisDecision.ANSWER,
        expected_citation_chunk_ids=(
            "knowledge-chunk:test:grounding:one:v1",
        ),
    )
    observation = _answer_observation(
        case_id=case.case_id,
        claims=[{"text": "Claim.", "citation_ids": ["C1"]}],
        supports=(True,),
    )

    with pytest.raises(
        GroundingEvaluationError,
        match="question identity",
    ):
        evaluate_grounding_case(case, observation)
