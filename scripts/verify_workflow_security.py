#!/usr/bin/env python3
"""Verify repository-wide GitHub Actions and OIDC security invariants."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = PROJECT_ROOT / ".github" / "workflows"
INFRA_DIR = PROJECT_ROOT / "infra"

_FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.ASCII)
_USES_RE = re.compile(r"^\s*uses:\s*([^\s#]+)", re.ASCII)
_CHECKOUT_RE = re.compile(r"^\s*uses:\s*actions/checkout@([0-9a-f]{40})(?:\s+#.*)?$", re.ASCII)

EXPECTED_OIDC_AUDIENCE = 'values   = ["sts.amazonaws.com"]'
EXPECTED_OIDC_SUBJECT = (
    '"repo:brunovicco@38844444/opslens@1333092779:ref:refs/heads/main"'
)

REQUIRED_AGENTCORE_RETIRED_MARKER = "AGENTCORE_RUNTIME_EXPERIMENT_RETIRED"
DEPENDENCY_REVIEW_ACTION_SHA = "a1d282b36b6f3519aa1f3fc636f609c47dddb294"
CODEQL_ACTION_SHA = "b96794f015dfd88f77b49b1c93e0fa7110f94c63"


class WorkflowSecurityError(RuntimeError):
    """Raised when a repository workflow security invariant is violated."""


def _workflow_paths() -> tuple[Path, ...]:
    """Return every retained YAML workflow in deterministic order."""
    return tuple(sorted((*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml"))))


def _without_comment(line: str) -> str:
    """Remove ordinary YAML comments for exact textual checks."""
    return line.split("#", maxsplit=1)[0].rstrip()


def _verify_external_action_pins(path: Path, lines: list[str]) -> None:
    """Require external GitHub Actions references to use full commit SHAs."""
    for line_number, line in enumerate(lines, start=1):
        match = _USES_RE.match(_without_comment(line))
        if match is None:
            continue
        target = match.group(1)
        if target.startswith("./"):
            continue
        if "@" not in target:
            raise WorkflowSecurityError(
                f"{path}:{line_number}: external uses reference has no immutable ref"
            )
        action, ref = target.rsplit("@", maxsplit=1)
        if not action or _FULL_SHA_RE.fullmatch(ref) is None:
            raise WorkflowSecurityError(
                f"{path}:{line_number}: external action must be pinned to one full 40-hex SHA"
            )


def _verify_checkout_credentials(path: Path, lines: list[str]) -> None:
    """Require every checkout step to remove its transient Git credential after fetch."""
    for index, line in enumerate(lines):
        if _CHECKOUT_RE.match(line) is None:
            continue
        indent = len(line) - len(line.lstrip())
        step_lines: list[str] = []
        for candidate in lines[index + 1 :]:
            stripped = candidate.lstrip()
            candidate_indent = len(candidate) - len(stripped)
            if stripped.startswith("- ") and candidate_indent <= indent:
                break
            step_lines.append(candidate)
        if not any(
            re.fullmatch(r"\s*persist-credentials:\s*false\s*", _without_comment(value))
            for value in step_lines
        ):
            raise WorkflowSecurityError(
                f"{path}:{index + 1}: actions/checkout must set persist-credentials: false"
            )


def _verify_trigger_and_permission_bounds(path: Path, lines: list[str]) -> None:
    """Reject high-risk event triggers and broad repository write permissions."""
    privileged_trigger_keys = {
        "pull_request_" + "target:",
        "workflow_" + "run:",
    }
    for line_number, line in enumerate(lines, start=1):
        stripped = _without_comment(line).strip()
        if stripped in privileged_trigger_keys:
            raise WorkflowSecurityError(
                f"{path}:{line_number}: privileged workflow trigger is not authorized"
            )
        if stripped == "write-all":
            raise WorkflowSecurityError(
                f"{path}:{line_number}: write-all workflow permission is forbidden"
            )
        if re.fullmatch(r"contents:\s*write", stripped) is not None:
            raise WorkflowSecurityError(
                f"{path}:{line_number}: contents: write requires a separate security decision"
            )


def _verify_agentcore_retirement(path: Path, text: str) -> None:
    """Keep the retired AgentCore lab workflow unable to obtain AWS mutation authority."""
    if path.name != "agentcore-runtime-experiment.yml":
        return
    required = (
        REQUIRED_AGENTCORE_RETIRED_MARKER,
        "workflow_dispatch:",
        "exit 1",
    )
    missing = [fragment for fragment in required if fragment not in text]
    if missing:
        raise WorkflowSecurityError(
            "retired AgentCore workflow lost fail-closed markers: " + ", ".join(missing)
        )
    forbidden = (
        "id-token: write",
        "configure-aws-credentials",
        "role-to-assume:",
        "OpsLensGitHubDeployRole",
        "terraform apply",
        "aws bedrock-agentcore",
    )
    present = [fragment for fragment in forbidden if fragment in text]
    if present:
        raise WorkflowSecurityError(
            "retired AgentCore workflow regained AWS/mutation authority: " + ", ".join(present)
        )


def _verify_epss_history_authority() -> None:
    """Require read-only planning identity and execution-only coordinator authority."""
    canary = (WORKFLOW_DIR / "epss-history-canary.yml").read_text(encoding="utf-8")
    backfill = (WORKFLOW_DIR / "epss-history-backfill.yml").read_text(encoding="utf-8")

    common_required = (
        "Configure read-only plan credentials",
        "if: ${{ !inputs.execute }}",
        "role/OpsLensEpssHistoryEvidenceRole",
        "Configure bounded coordinator credentials",
        "if: ${{ inputs.execute }}",
        "role/OpsLensEpssHistoryCoordinatorRole",
    )
    for name, text in (("canary", canary), ("backfill", backfill)):
        missing = [fragment for fragment in common_required if fragment not in text]
        if missing:
            raise WorkflowSecurityError(
                f"EPSS history {name} workflow lost plan/execution authority separation: "
                + ", ".join(missing)
            )

    if "role-duration-seconds: 21600" in canary:
        raise WorkflowSecurityError("EPSS canary must not request a six-hour coordinator session")

    duration_index = backfill.find("role-duration-seconds: 21600")
    execution_role_index = backfill.find("role/OpsLensEpssHistoryCoordinatorRole")
    plan_role_index = backfill.find("role/OpsLensEpssHistoryEvidenceRole")
    if min(duration_index, execution_role_index, plan_role_index) < 0:
        raise WorkflowSecurityError("EPSS backfill session/role evidence is incomplete")
    if not plan_role_index < execution_role_index <= duration_index:
        raise WorkflowSecurityError(
            "EPSS backfill six-hour session must belong only to the execution coordinator role"
        )


def _verify_supply_chain_scanners() -> None:
    """Freeze the bounded Gate 17.3 dependency-review and CodeQL workflow contracts."""
    dependency_review = (WORKFLOW_DIR / "dependency-review.yml").read_text(encoding="utf-8")
    codeql = (WORKFLOW_DIR / "codeql.yml").read_text(encoding="utf-8")

    dependency_required = (
        "pull_request:",
        "contents: read",
        f"actions/dependency-review-action@{DEPENDENCY_REVIEW_ACTION_SHA}",
        "fail-on-severity: high",
        "persist-credentials: false",
    )
    dependency_missing = [
        fragment for fragment in dependency_required if fragment not in dependency_review
    ]
    if dependency_missing:
        raise WorkflowSecurityError(
            "dependency-review workflow lost the frozen Gate 17.3 contract: "
            + ", ".join(dependency_missing)
        )

    dependency_forbidden = (
        "id-token: write",
        "security-events: write",
        "pull-requests: write",
        "configure-aws-credentials",
        "role-to-assume:",
    )
    dependency_present = [
        fragment for fragment in dependency_forbidden if fragment in dependency_review
    ]
    if dependency_present:
        raise WorkflowSecurityError(
            "dependency-review workflow gained unnecessary authority: "
            + ", ".join(dependency_present)
        )

    codeql_required = (
        "push:",
        "pull_request:",
        "schedule:",
        "workflow_dispatch:",
        "contents: read",
        "security-events: write",
        f"github/codeql-action/init@{CODEQL_ACTION_SHA}",
        f"github/codeql-action/analyze@{CODEQL_ACTION_SHA}",
        "languages: python",
        "persist-credentials: false",
    )
    codeql_missing = [fragment for fragment in codeql_required if fragment not in codeql]
    if codeql_missing:
        raise WorkflowSecurityError(
            "CodeQL workflow lost the frozen Gate 17.3 contract: " + ", ".join(codeql_missing)
        )

    codeql_forbidden = (
        "id-token: write",
        "contents: write",
        "pull-requests: write",
        "configure-aws-credentials",
        "role-to-assume:",
    )
    codeql_present = [fragment for fragment in codeql_forbidden if fragment in codeql]
    if codeql_present:
        raise WorkflowSecurityError(
            "CodeQL workflow gained unrelated mutation authority: " + ", ".join(codeql_present)
        )


def _verify_github_oidc_trust() -> None:
    """Require every GitHub OIDC trust policy to retain the frozen aud/sub boundary."""
    observed = 0
    for path in sorted(INFRA_DIR.rglob("*.tf")):
        text = path.read_text(encoding="utf-8")
        if "sts:AssumeRoleWithWebIdentity" not in text:
            continue
        if "token.actions.githubusercontent.com" not in text:
            continue
        observed += 1
        if EXPECTED_OIDC_AUDIENCE not in text or EXPECTED_OIDC_SUBJECT not in text:
            raise WorkflowSecurityError(
                f"{path}: GitHub OIDC trust must use the frozen audience and immutable main subject"
            )
    if observed < 3:
        raise WorkflowSecurityError(
            "Expected at least the retained deploy, EPSS evidence, and EPSS coordinator OIDC trusts"
        )


def _capture(errors: list[str], check: Callable[[], None]) -> None:
    """Capture one deterministic invariant failure so CI reports all observed drift at once."""
    try:
        check()
    except WorkflowSecurityError as exc:
        errors.append(str(exc))


def verify() -> None:
    """Run all deterministic repository security checks."""
    workflows = _workflow_paths()
    if not workflows:
        raise WorkflowSecurityError("No GitHub Actions workflows were found")

    errors: list[str] = []
    for path in workflows:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        _capture(errors, lambda path=path, lines=lines: _verify_external_action_pins(path, lines))
        _capture(errors, lambda path=path, lines=lines: _verify_checkout_credentials(path, lines))
        _capture(
            errors,
            lambda path=path, lines=lines: _verify_trigger_and_permission_bounds(path, lines),
        )
        _capture(errors, lambda path=path, text=text: _verify_agentcore_retirement(path, text))

    _capture(errors, _verify_epss_history_authority)
    _capture(errors, _verify_supply_chain_scanners)
    _capture(errors, _verify_github_oidc_trust)

    if errors:
        raise WorkflowSecurityError("\n".join(errors))


def main() -> None:
    """Run repository security verification and emit one stable success marker."""
    verify()
    print("workflow_security_invariants=PASS")


if __name__ == "__main__":
    main()
