"""Tests for content-addressed A2A reference registration and resolution."""

from dataclasses import replace

import pytest

from opslens.a2a_boundary.application.registry import A2AReferenceRegistry
from opslens.a2a_boundary.domain.errors import (
    A2ABoundaryValidationError,
    A2AReferenceNotFoundError,
)
from opslens.a2a_boundary.domain.reference import (
    A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION,
    create_a2a_reference,
)
from opslens.multi_agent.domain.handoff import SpecialistAgentTask


def test_reference_is_deterministic_and_binds_retained_handoff(
    specialist_task: SpecialistAgentTask,
) -> None:
    """Reference identity must derive only from already-admitted handoff/task identity."""
    first = create_a2a_reference(specialist_task=specialist_task)
    second = create_a2a_reference(specialist_task=specialist_task)

    assert first == second
    assert first.handoff_id == specialist_task.handoff.handoff_id
    assert first.specialist_task_id == specialist_task.task.task_id
    assert first.reference_id == (
        f"{A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION}:reference:"
        f"{first.reference_sha256}"
    )


def test_reference_rejects_tampered_handoff_identity(
    specialist_task: SpecialistAgentTask,
    second_specialist_task: SpecialistAgentTask,
) -> None:
    """Changing one retained identity without recomputing the digest must fail closed."""
    reference = create_a2a_reference(specialist_task=specialist_task)

    with pytest.raises(
        A2ABoundaryValidationError,
        match="reference_sha256 must match canonical",
    ):
        replace(
            reference,
            handoff_id=second_specialist_task.handoff.handoff_id,
        )


def test_registry_registration_is_idempotent_for_identical_content(
    specialist_task: SpecialistAgentTask,
) -> None:
    """Exact re-registration is safe because reference identity is content-addressed."""
    registry = A2AReferenceRegistry()

    first = registry.register(specialist_task=specialist_task)
    second = registry.register(specialist_task=specialist_task)

    assert first == second
    assert registry.resolve(reference=first) == specialist_task


def test_registry_rejects_unregistered_reference(
    specialist_task: SpecialistAgentTask,
    second_specialist_task: SpecialistAgentTask,
) -> None:
    """A valid but unknown reference cannot acquire peer authority."""
    registry = A2AReferenceRegistry()
    registry.register(specialist_task=specialist_task)
    unknown = create_a2a_reference(specialist_task=second_specialist_task)

    with pytest.raises(A2AReferenceNotFoundError, match="not registered"):
        registry.resolve(reference=unknown)
