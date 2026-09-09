"""Code-owned in-memory resolution for the bounded A2A reference experiment."""

from __future__ import annotations

from opslens.a2a_boundary.domain.errors import (
    A2ABoundaryValidationError,
    A2AReferenceNotFoundError,
)
from opslens.a2a_boundary.domain.reference import A2AReference, create_a2a_reference
from opslens.multi_agent.domain.handoff import SpecialistAgentTask


class A2AReferenceRegistry:
    """Lab-only registry of pre-admitted specialist tasks keyed by content identity."""

    def __init__(self) -> None:
        """Initialize an empty reference registry."""
        self._tasks_by_reference: dict[str, SpecialistAgentTask] = {}

    def register(self, *, specialist_task: SpecialistAgentTask) -> A2AReference:
        """Register one trusted specialist task and return its deterministic reference."""
        if type(specialist_task) is not SpecialistAgentTask:
            raise A2ABoundaryValidationError(
                "specialist_task must be one admitted SpecialistAgentTask"
            )
        reference = create_a2a_reference(specialist_task=specialist_task)
        existing = self._tasks_by_reference.get(reference.reference_sha256)
        if existing is not None and existing != specialist_task:
            raise A2ABoundaryValidationError(
                "A2A reference digest is already bound to different specialist state"
            )
        self._tasks_by_reference[reference.reference_sha256] = specialist_task
        return reference

    def resolve(self, *, reference: A2AReference) -> SpecialistAgentTask:
        """Resolve one reference and re-bind it to the original admitted task."""
        if type(reference) is not A2AReference:
            raise A2ABoundaryValidationError("reference must be one admitted A2AReference")
        specialist_task = self._tasks_by_reference.get(reference.reference_sha256)
        if specialist_task is None:
            raise A2AReferenceNotFoundError("A2A specialist reference is not registered")

        expected = create_a2a_reference(specialist_task=specialist_task)
        if expected != reference:
            raise A2ABoundaryValidationError(
                "A2A reference does not match the registered specialist task"
            )
        return specialist_task


__all__ = ["A2AReferenceRegistry"]
