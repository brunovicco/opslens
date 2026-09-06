"""Gate 7.7 real-runtime orchestration over frozen groundedness cases."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from opslens.knowledge_retrieval.adapters.bedrock_grounded_synthesis import (
    BedrockGroundedSynthesisExecution,
)
from opslens.knowledge_retrieval.adapters.bedrock_synthesis import (
    BedrockSynthesisRuntimeError,
)
from opslens.knowledge_retrieval.application.bedrock_retrieval import (
    BedrockRetrievalProviderError,
    BedrockRetrievalValidationError,
    BedrockRetrieveResult,
)
from opslens.knowledge_retrieval.application.citation_projection import (
    CitationProjectionError,
    project_citation_catalog,
)
from opslens.knowledge_retrieval.application.context_assembly import (
    ContextAssemblyError,
    assemble_retrieval_context,
)
from opslens.knowledge_retrieval.application.grounded_synthesis_prompt import (
    GroundedSynthesisPromptError,
)
from opslens.knowledge_retrieval.application.grounding_contract import (
    GroundedSynthesisOutputError,
    build_grounded_synthesis_request,
)
from opslens.knowledge_retrieval.application.grounding_evaluation import (
    GoldenGroundingCase,
    GoldenGroundingDataset,
    validate_grounding_dataset_catalog,
)
from opslens.knowledge_retrieval.application.retrieval_catalog import (
    CanonicalRetrievalCatalog,
)
from opslens.knowledge_retrieval.application.synthesis_contract import (
    SynthesisAdmissionError,
    SynthesisOutputError,
    build_synthesis_request,
)
from opslens.knowledge_retrieval.domain import (
    DEFAULT_RETRIEVAL_TOP_K,
    AssembledContext,
    CitationCatalog,
    GroundedSynthesisRequest,
    KnowledgeRetrievalValidationError,
    RetrievalRequest,
    SynthesisAuthorityDecision,
)

GroundingEvaluationRetriever = Callable[[RetrievalRequest], BedrockRetrieveResult]
GroundingEvaluationSynthesizer = Callable[
    [GroundedSynthesisRequest],
    BedrockGroundedSynthesisExecution,
]


@dataclass(frozen=True, slots=True)
class GroundingRuntimeCaseExecution:
    """One attempted frozen case with partial evidence preserved on safe failure."""

    case: GoldenGroundingCase
    retrieval: BedrockRetrieveResult | None
    context: AssembledContext | None
    citation_catalog: CitationCatalog | None
    synthesis: BedrockGroundedSynthesisExecution | None
    failure_category: str | None = None

    @property
    def complete(self) -> bool:
        """Return whether retrieval, context, citations, and synthesis all completed."""
        return (
            self.failure_category is None
            and self.retrieval is not None
            and self.context is not None
            and self.citation_catalog is not None
            and self.synthesis is not None
        )


@dataclass(frozen=True, slots=True)
class GroundingRuntimeExecution:
    """First-run runtime observations before semantic support adjudication."""

    dataset_id: str
    attempts: tuple[GroundingRuntimeCaseExecution, ...]
    planned_case_count: int

    @property
    def complete(self) -> bool:
        """Require every frozen case to complete exactly one application attempt."""
        return (
            len(self.attempts) == self.planned_case_count
            and all(attempt.complete for attempt in self.attempts)
        )


def _failure_category(exc: Exception) -> str:
    """Return one content-free application/provider failure category."""
    return type(exc).__name__


def run_grounding_runtime_evaluation(
    retrieve: GroundingEvaluationRetriever,
    synthesize: GroundingEvaluationSynthesizer,
    *,
    dataset: GoldenGroundingDataset,
    catalog: CanonicalRetrievalCatalog,
) -> GroundingRuntimeExecution:
    """Run each frozen case once, stopping after the first failed application attempt."""
    validate_grounding_dataset_catalog(dataset, catalog)
    attempts: list[GroundingRuntimeCaseExecution] = []

    for case in dataset.cases:
        retrieval: BedrockRetrieveResult | None = None
        context: AssembledContext | None = None
        citation_catalog: CitationCatalog | None = None
        grounded_request: GroundedSynthesisRequest | None = None
        synthesis: BedrockGroundedSynthesisExecution | None = None

        try:
            retrieval_request = RetrievalRequest(
                query=case.question,
                top_k=DEFAULT_RETRIEVAL_TOP_K,
            )
            retrieval = retrieve(retrieval_request)
            if retrieval.evidence.request != retrieval_request:
                raise BedrockRetrievalValidationError(
                    "grounding evaluator received evidence for a different request"
                )
            context = assemble_retrieval_context(retrieval.evidence)
            citation_catalog = project_citation_catalog(context)
            synthesis_request = build_synthesis_request(
                question=case.question,
                context=context,
                authority_decision=SynthesisAuthorityDecision.SUPPORTED,
            )
            grounded_request = build_grounded_synthesis_request(
                synthesis_request=synthesis_request,
                citation_catalog=citation_catalog,
            )
            synthesis = synthesize(grounded_request)
            if (
                synthesis.result.grounded_request_sha256
                != grounded_request.grounded_request_sha256
            ):
                raise GroundedSynthesisOutputError(
                    "grounding evaluator received synthesis for a different request"
                )
        except (
            BedrockRetrievalProviderError,
            BedrockRetrievalValidationError,
            BedrockSynthesisRuntimeError,
            CitationProjectionError,
            ContextAssemblyError,
            GroundedSynthesisOutputError,
            GroundedSynthesisPromptError,
            KnowledgeRetrievalValidationError,
            SynthesisAdmissionError,
            SynthesisOutputError,
        ) as exc:
            attempts.append(
                GroundingRuntimeCaseExecution(
                    case=case,
                    retrieval=retrieval,
                    context=context,
                    citation_catalog=citation_catalog,
                    synthesis=synthesis,
                    failure_category=_failure_category(exc),
                )
            )
            break

        attempts.append(
            GroundingRuntimeCaseExecution(
                case=case,
                retrieval=retrieval,
                context=context,
                citation_catalog=citation_catalog,
                synthesis=synthesis,
            )
        )

    return GroundingRuntimeExecution(
        dataset_id=dataset.dataset_id,
        attempts=tuple(attempts),
        planned_case_count=len(dataset.cases),
    )
