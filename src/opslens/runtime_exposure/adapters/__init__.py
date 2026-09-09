"""Outbound adapters for independent runtime evidence."""

from opslens.runtime_exposure.adapters.inspector_readonly import (
    InspectorReadClient,
    run_readonly_inspector_discovery,
)

__all__ = ["InspectorReadClient", "run_readonly_inspector_discovery"]
