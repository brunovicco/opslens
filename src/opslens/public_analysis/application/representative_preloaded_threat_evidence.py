"""Release pre-admitted threat evidence to the measured representative workload."""

import re
from dataclasses import dataclass

from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryThreatEvidence,
)
from opslens.public_analysis.application.representative_workload_execution import (
    RepresentativeThreatEvidenceLoad,
)
from opslens.public_analysis.domain import PublicRepositoryEvidenceExecution

_GIT_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.ASCII)


class RepresentativePreloadedThreatEvidenceError(ValueError):
    """Reject repository drift before releasing pre-admitted threat evidence."""


@dataclass(frozen=True, slots=True)
class PreloadedRepresentativeThreatEvidenceLoader:
    """Bind pre-admitted threat evidence to one immutable repository anchor.

    Source-authority materialization happens before the measured Gate 19.2
    workload. This callable performs no provider I/O and therefore contributes
    no request-time provider usage of its own.
    """

    evidence: RepresentativeRepositoryThreatEvidence
    expected_repository_url: str
    expected_commit_sha: str

    def __post_init__(self) -> None:
        """Validate immutable preload coordinates at composition time."""
        if type(self.evidence) is not RepresentativeRepositoryThreatEvidence:
            raise TypeError("evidence must be RepresentativeRepositoryThreatEvidence")
        if (
            type(self.expected_repository_url) is not str
            or not self.expected_repository_url
            or self.expected_repository_url != self.expected_repository_url.strip()
            or not self.expected_repository_url.startswith("https://github.com/")
        ):
            raise RepresentativePreloadedThreatEvidenceError(
                "expected_repository_url must be one trimmed canonical GitHub URL"
            )
        if (
            type(self.expected_commit_sha) is not str
            or _GIT_COMMIT_SHA_RE.fullmatch(self.expected_commit_sha) is None
        ):
            raise RepresentativePreloadedThreatEvidenceError(
                "expected_commit_sha must be one lowercase 40-hex Git commit SHA"
            )

    def __call__(
        self,
        execution: PublicRepositoryEvidenceExecution,
    ) -> RepresentativeThreatEvidenceLoad:
        """Release preload only when the measured repository identity matches exactly."""
        if type(execution) is not PublicRepositoryEvidenceExecution:
            raise TypeError("execution must be PublicRepositoryEvidenceExecution")

        repository_url = execution.request.target.canonical_repository_url
        if repository_url != self.expected_repository_url:
            raise RepresentativePreloadedThreatEvidenceError(
                "representative repository URL does not match the preloaded threat authority"
            )

        commit_sha = execution.snapshot_resolution.snapshot.commit_sha
        if commit_sha != self.expected_commit_sha:
            raise RepresentativePreloadedThreatEvidenceError(
                "representative commit SHA does not match the preloaded threat authority"
            )

        return RepresentativeThreatEvidenceLoad(evidence=self.evidence)


__all__ = [
    "PreloadedRepresentativeThreatEvidenceLoader",
    "RepresentativePreloadedThreatEvidenceError",
]
