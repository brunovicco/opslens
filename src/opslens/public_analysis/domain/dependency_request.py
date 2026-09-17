"""One dependency a caller asserts, admitted before anything is looked up.

Gate 21.4 gives the endpoint two input shapes. A repository is `owner/repo[@ref]`, and
answering it costs a GitHub snapshot, a lock read, a parse and an inventory. A single
dependency is `name==version`, and answering it costs one index lookup. The second shape
is not a reduced version of the first; it is a different question with a different
warrant, and the difference has to survive into the answer.

```text
observed evidence != asserted evidence
```

For a repository, OpsLens read the lock itself, at a commit it pinned, and can prove what
it read. For a dependency, the caller typed a name and a version. Nothing here verifies
that anything installs it, that the version exists on PyPI, or that the caller has the
package they think they have. The verdict is sound — the advisories that apply to that
name at that version — and it is a verdict about a claim, not about a system.

An envelope that presented the two identically would let a dependency answer be shown as
a repository audit, which is why the request type is separate rather than a flag.

The request is content-addressed so a cache and a response can name it, and so two
callers asking the same question in different spellings — `Requests==2.31.0` and
`requests==2.31.0` — are asking one question.
"""

import re
from dataclasses import dataclass
from typing import Final

from opslens.correlation.domain.errors import CorrelationContractError
from opslens.correlation.domain.pypi import (
    build_pypi_purl,
    canonicalize_pypi_package,
    canonicalize_pypi_version,
)
from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.shared.evidence import canonical_json, evidence_id

PUBLIC_DEPENDENCY_REQUEST_CONTRACT_VERSION: Final = "public-dependency-request:v1"

# The whole accepted grammar. `==` only: a range is a question about many versions, and
# this shape answers about one.
_SPECIFIER_RE: Final = re.compile(r"\A(?P<name>[^=\s]+)==(?P<version>[^=\s]+)\Z")

MAX_DEPENDENCY_SPECIFIER_LENGTH: Final = 256


@dataclass(frozen=True, slots=True)
class PublicDependencyRequest:
    """One canonical PyPI dependency a caller asked about.

    Attributes:
        package_name_original: The name exactly as the caller spelled it.
        version_original: The version exactly as the caller spelled it.
        package_name_canonical: The name the index is keyed by.
        version_canonical: The normalized version applicability is decided on.
        purl: The canonical package URL for the pair.
    """

    package_name_original: str
    version_original: str
    package_name_canonical: str
    version_canonical: str
    purl: str

    def __post_init__(self) -> None:
        """Reject a request that does not carry both spellings of one dependency.

        Raises:
            PublicAnalysisValidationError: If any field is empty or padded.
        """
        for field, value in (
            ("package_name_original", self.package_name_original),
            ("version_original", self.version_original),
            ("package_name_canonical", self.package_name_canonical),
            ("version_canonical", self.version_canonical),
            ("purl", self.purl),
        ):
            if type(value) is not str or not value or value.strip() != value:
                raise PublicAnalysisValidationError(
                    f"public dependency request {field} must be non-empty and unpadded"
                )

    @property
    def canonical_payload(self) -> dict[str, object]:
        """Project the payload this request's identity is taken over.

        Only the canonical pair. Two callers spelling the same dependency differently
        asked one question, and a cache keyed on the spelling would answer it twice.
        """
        return {
            "contract_version": PUBLIC_DEPENDENCY_REQUEST_CONTRACT_VERSION,
            "package_name_canonical": self.package_name_canonical,
            "version_canonical": self.version_canonical,
        }

    @property
    def canonical_json(self) -> bytes:
        """Return the exact bytes this request's identity is taken over."""
        return canonical_json(self.canonical_payload)

    @property
    def request_id(self) -> str:
        """Return one content-addressed identity for this question."""
        return evidence_id(
            PUBLIC_DEPENDENCY_REQUEST_CONTRACT_VERSION, self.canonical_payload
        )


def admit_public_dependency_request(specifier: str) -> PublicDependencyRequest:
    """Admit one `name==version` specifier, or refuse it with a reason.

    The grammar is deliberately one operator wide. `requests>=2.0` asks about a range of
    versions, and a range has no single answer to "is this affected"; accepting it would
    mean picking a version on the caller's behalf and reporting the result as theirs.

    Args:
        specifier: The caller's input, exactly as received.

    Returns:
        The admitted request.

    Raises:
        PublicAnalysisValidationError: If the specifier is malformed, too long, or names
            a package or version PyPI identity cannot be derived from.
    """
    if type(specifier) is not str or not specifier:
        raise PublicAnalysisValidationError("a dependency specifier is required")
    if len(specifier) > MAX_DEPENDENCY_SPECIFIER_LENGTH:
        raise PublicAnalysisValidationError(
            "dependency specifier exceeds "
            f"{MAX_DEPENDENCY_SPECIFIER_LENGTH} characters"
        )

    matched = _SPECIFIER_RE.match(specifier.strip())
    if matched is None:
        raise PublicAnalysisValidationError(
            "a dependency specifier must be exactly one name==version pair"
        )

    name = matched.group("name")
    version = matched.group("version")
    try:
        package = canonicalize_pypi_package(name)
        canonical_version = canonicalize_pypi_version(version)
        purl = build_pypi_purl(package=package, version=canonical_version)
    except CorrelationContractError as exc:
        raise PublicAnalysisValidationError(
            f"dependency specifier is not a PyPI identity: {exc.reason_code}"
        ) from exc

    return PublicDependencyRequest(
        package_name_original=name,
        version_original=version,
        package_name_canonical=package.canonical,
        version_canonical=canonical_version.canonical,
        purl=purl,
    )


__all__ = [
    "MAX_DEPENDENCY_SPECIFIER_LENGTH",
    "PUBLIC_DEPENDENCY_REQUEST_CONTRACT_VERSION",
    "PublicDependencyRequest",
    "admit_public_dependency_request",
]
