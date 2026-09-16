"""Deployment artifact identity shared by the publish tooling."""

from opslens.shared.deployment.lambda_artifacts import (
    PUBLISHABLE_TARGETS,
    LambdaArtifactTarget,
    UnknownArtifactTargetError,
    artifact_key,
    render_terraform_locals,
    resolve_target,
)

__all__ = [
    "PUBLISHABLE_TARGETS",
    "LambdaArtifactTarget",
    "UnknownArtifactTargetError",
    "artifact_key",
    "render_terraform_locals",
    "resolve_target",
]
