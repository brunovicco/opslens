"""Tests for naming and pinning a Lambda deployment artifact.

Three near-identical publish scripts each carried their own copy of a key prefix, and a
fourth lambda needed the same thing. The registry holds that decision once. What it
must never do is accept a name it does not declare: the publish is create-only, so
bytes written to a guessed prefix are permanent and unread.

```text
unknown target != guess a prefix
```

The rendered block is asserted against the shape the Terraform files actually carry,
including the interpolation that keeps the key derived from the digest rather than
written down a second time.
"""

import pytest

from opslens.shared.deployment import (
    PUBLISHABLE_TARGETS,
    LambdaArtifactTarget,
    UnknownArtifactTargetError,
    artifact_key,
    render_terraform_locals,
    resolve_target,
)

_DIGEST = "f5c492ee31261bb3de53fad353738ee71fa18cb488d4d0382b79ecc8b0f61577"
_BASE64 = "9cSS7jEmG7PeU/rTU3OO5x+hjLSI1NA4K3nsyLD2FXc="
_VERSION = "oMs9fDsFdLUNaNT2IQXFgMzzFrOZGfJq"


def test_every_declared_target_is_keyed_by_its_own_component() -> None:
    """A registry whose key and component disagree would publish under the wrong name."""
    for name, target in PUBLISHABLE_TARGETS.items():
        assert name == target.component


def test_an_undeclared_target_is_refused() -> None:
    """A name the registry does not carry must not resolve to a guessed prefix."""
    with pytest.raises(UnknownArtifactTargetError):
        resolve_target("kev-silver")


def test_the_key_matches_the_one_already_published() -> None:
    """The derived key equals the key the GHSA Silver artifact actually occupies."""
    key = artifact_key(resolve_target("ghsa-silver"), _DIGEST)
    assert key == f"lambda/ghsa-silver/{_DIGEST}.zip"


@pytest.mark.parametrize("digest", ["", "abc", _DIGEST.upper(), _DIGEST + "0"])
def test_a_malformed_digest_cannot_name_a_key(digest: str) -> None:
    """Anything that is not a lowercase sha-256 hex digest is refused."""
    with pytest.raises(ValueError):
        artifact_key(resolve_target("ghsa-silver"), digest)


def test_the_rendered_block_carries_all_four_locals() -> None:
    """Terraform needs the digest, its base64 form, the version id and the key."""
    block = render_terraform_locals(
        resolve_target("epss-history-transformer"),
        sha256=_DIGEST,
        sha256_base64=_BASE64,
        version_id=_VERSION,
    )
    assert "epss_history_transformer_artifact_sha256 = (" in block
    assert "epss_history_transformer_artifact_sha256_base64 = (" in block
    assert "epss_history_transformer_artifact_version = (" in block
    assert _VERSION in block


def test_the_rendered_key_stays_derived_from_the_digest() -> None:
    """Writing the digest into the key twice is how the two drift apart."""
    block = render_terraform_locals(
        resolve_target("nvd-incremental"),
        sha256=_DIGEST,
        sha256_base64=_BASE64,
        version_id=_VERSION,
    )
    assert (
        '"lambda/nvd-incremental/${local.nvd_incremental_lambda_artifact_sha256}.zip"'
        in block
    )
    assert block.count(_DIGEST) == 1


def test_an_artifact_without_a_version_id_cannot_be_pinned() -> None:
    """A pin without a version id names a key whose bytes may later differ."""
    with pytest.raises(ValueError):
        render_terraform_locals(
            resolve_target("ghsa-silver"),
            sha256=_DIGEST,
            sha256_base64=_BASE64,
            version_id="   ",
        )


def test_a_target_with_an_unsafe_component_is_refused() -> None:
    """A component that is not key-safe would name an object nothing reads."""
    with pytest.raises(ValueError):
        LambdaArtifactTarget(
            component="GHSA Silver",
            artifact_filename="x.zip",
            locals_prefix="x",
            terraform_file="x.tf",
        )
