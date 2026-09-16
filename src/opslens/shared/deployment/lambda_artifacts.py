"""Name and pin a Lambda deployment artifact, for every lambda that has one.

Three near-identical publish scripts existed before this module, one per lambda, each
carrying its own copy of the key prefix and — in one case — its own copy of the
Terraform locals block it printed. A fourth was needed. Copying it again would have put
the same decision in four places, and the decision is not cosmetic: the key prefix
names where bytes land, and the locals block is what Terraform pins the function to.

So the targets are a registry rather than a command-line string. A free-form prefix
would let a typo publish real bytes to a path nothing reads, and the publish is
create-only, so those bytes would then be permanent.

```text
unknown target != guess a prefix
published artifact != pinned artifact
```
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

_COMPONENT_PATTERN: Final = "abcdefghijklmnopqrstuvwxyz0123456789-"


class UnknownArtifactTargetError(KeyError):
    """Raised when a publish is requested for a target the registry does not declare."""


@dataclass(frozen=True, slots=True)
class LambdaArtifactTarget:
    """One publishable lambda artifact and the Terraform pins it feeds.

    Attributes:
        component: The S3 key segment and metadata component name.
        artifact_filename: The deterministic ZIP the build script writes into `dist/`.
        locals_prefix: The Terraform locals prefix, without the trailing field name.
        terraform_file: The file whose locals block this target pins, for the operator
            message; this module never edits it.
    """

    component: str
    artifact_filename: str
    locals_prefix: str
    terraform_file: str

    def __post_init__(self) -> None:
        """Reject a target that could name an object nothing reads.

        Raises:
            ValueError: If any field is empty, or the component is not a lowercase
                key-safe segment.
        """
        for name, value in (
            ("component", self.component),
            ("artifact_filename", self.artifact_filename),
            ("locals_prefix", self.locals_prefix),
            ("terraform_file", self.terraform_file),
        ):
            if not value or value.strip() != value:
                raise ValueError(f"{name} must be a non-empty unpadded string")

        if any(character not in _COMPONENT_PATTERN for character in self.component):
            raise ValueError(
                f"component {self.component!r} must be lowercase letters, digits or hyphens"
            )


PUBLISHABLE_TARGETS: Final[Mapping[str, LambdaArtifactTarget]] = {
    "ghsa-silver": LambdaArtifactTarget(
        component="ghsa-silver",
        artifact_filename="opslens-ghsa-silver.zip",
        locals_prefix="ghsa_silver_lambda_artifact",
        terraform_file="infra/environments/dev/ghsa_silver_lambda.tf",
    ),
    "epss-history-transformer": LambdaArtifactTarget(
        component="epss-history-transformer",
        artifact_filename="opslens-epss-history-transformer.zip",
        locals_prefix="epss_history_transformer_artifact",
        terraform_file="infra/environments/dev/epss_history_transformer_lambda.tf",
    ),
    "nvd-incremental": LambdaArtifactTarget(
        component="nvd-incremental",
        artifact_filename="opslens-nvd-incremental.zip",
        locals_prefix="nvd_incremental_lambda_artifact",
        terraform_file="infra/environments/dev/nvd_incremental_lambda.tf",
    ),
}


def resolve_target(name: str) -> LambdaArtifactTarget:
    """Return the declared target, refusing anything the registry does not carry.

    Args:
        name: The requested target name.

    Returns:
        The declared target.

    Raises:
        UnknownArtifactTargetError: If the registry does not declare that name.
    """
    try:
        return PUBLISHABLE_TARGETS[name]
    except KeyError as exc:
        known = ", ".join(sorted(PUBLISHABLE_TARGETS))
        raise UnknownArtifactTargetError(
            f"unknown publish target {name!r}; declared targets are {known}"
        ) from exc


def artifact_key(target: LambdaArtifactTarget, sha256: str) -> str:
    """Build the content-addressed S3 key for one artifact.

    Args:
        target: The publishable target.
        sha256: Hex digest of the artifact bytes.

    Returns:
        The object key.

    Raises:
        ValueError: If the digest is not 64 lowercase hex characters.
    """
    if len(sha256) != 64 or any(character not in "0123456789abcdef" for character in sha256):
        raise ValueError(f"{sha256!r} is not a lowercase sha-256 hex digest")
    return f"lambda/{target.component}/{sha256}.zip"


def render_terraform_locals(
    target: LambdaArtifactTarget,
    *,
    sha256: str,
    sha256_base64: str,
    version_id: str,
) -> str:
    """Render the exact locals block the target's Terraform file requires.

    Copying three values by hand is where a mistake silently pins the wrong bytes, and
    the pin is the control that stops a function running code nobody admitted.

    Args:
        target: The publishable target.
        sha256: Hex digest of the artifact.
        sha256_base64: Base64 of the raw digest bytes, which Lambda compares as
            `source_code_hash`.
        version_id: The published S3 object version id.

    Returns:
        The block to paste, formatted as the files already format it.

    Raises:
        ValueError: If the digest is malformed or the version id is empty.
    """
    # Validate the digest through the same rule the key uses, so a block can never
    # name a key the publish would refuse.
    artifact_key(target, sha256)
    if not version_id.strip():
        raise ValueError("a published artifact always carries a version id")

    prefix = target.locals_prefix
    return f'''locals {{
  {prefix}_sha256 = (
    "{sha256}"
  )

  {prefix}_sha256_base64 = (
    "{sha256_base64}"
  )

  {prefix}_version = (
    "{version_id}"
  )

  {prefix}_key = (
    "lambda/{target.component}/${{local.{prefix}_sha256}}.zip"
  )
}}'''
