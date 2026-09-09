"""Domain contracts for bounded A2A interoperability."""

from opslens.a2a_boundary.domain.errors import (
    A2ABoundaryError,
    A2ABoundaryValidationError,
    A2AReferenceNotFoundError,
    A2AReplayError,
)
from opslens.a2a_boundary.domain.reference import (
    A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION,
    A2AReference,
    create_a2a_reference,
)

__all__ = [
    "A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION",
    "A2ABoundaryError",
    "A2ABoundaryValidationError",
    "A2AReference",
    "A2AReferenceNotFoundError",
    "A2AReplayError",
    "create_a2a_reference",
]
