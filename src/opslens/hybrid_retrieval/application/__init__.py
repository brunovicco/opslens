"""Application services for deterministic hybrid routing, evidence, and synthesis."""

from opslens.hybrid_retrieval.application.assembly import (
    assemble_hybrid_evidence,
    project_semantic_retrieval_evidence,
)
from opslens.hybrid_retrieval.application.evaluation import (
    evaluate_hybrid_offline,
    load_hybrid_evaluation_dataset,
    parse_hybrid_evaluation_dataset,
)
from opslens.hybrid_retrieval.application.routing import route_evidence_request
from opslens.hybrid_retrieval.application.synthesis import (
    HybridSynthesisOutputError,
    build_hybrid_synthesis_request,
    parse_hybrid_synthesis_output,
    project_deterministic_structured_answer,
)
from opslens.hybrid_retrieval.application.synthesis_prompt import (
    HybridSynthesisPromptEnvelope,
    HybridSynthesisPromptError,
    build_hybrid_synthesis_prompt,
)

__all__ = [
    "HybridSynthesisOutputError",
    "HybridSynthesisPromptEnvelope",
    "HybridSynthesisPromptError",
    "assemble_hybrid_evidence",
    "build_hybrid_synthesis_prompt",
    "build_hybrid_synthesis_request",
    "evaluate_hybrid_offline",
    "load_hybrid_evaluation_dataset",
    "parse_hybrid_evaluation_dataset",
    "parse_hybrid_synthesis_output",
    "project_deterministic_structured_answer",
    "project_semantic_retrieval_evidence",
    "route_evidence_request",
]
