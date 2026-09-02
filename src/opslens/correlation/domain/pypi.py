"""PyPI package identity, PEP 440 version, and purl semantics for Phase 3."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import quote, unquote_to_bytes

from packaging.version import InvalidVersion, Version

from opslens.correlation.domain.errors import (
    InvalidPackageNameError,
    InvalidPackagePurlError,
    InvalidPackageVersionError,
    UnsupportedEcosystemError,
    UnsupportedPackagePurlFeatureError,
)

_PYPI_NAME_PATTERN = re.compile(
    r"(?:[A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])\Z",
    re.IGNORECASE | re.ASCII,
)
_PYPI_NAME_SEPARATOR_PATTERN = re.compile(r"[-_.]+")
_INVALID_PERCENT_ESCAPE_PATTERN = re.compile(r"%(?![0-9A-Fa-f]{2})")
_PURL_PATTERN = re.compile(
    r"^pkg:(?P<type>[^/]+)/(?P<name>[^/@?#]+)@(?P<version>[^/?#]+)$",
    re.ASCII,
)
_PURL_COMPONENT_SAFE = ".-_~:"


class PyPIEcosystem(StrEnum):
    """Canonical ecosystem identifiers understood by the first Phase 3 evaluator."""

    PYPI = "pypi"


@dataclass(frozen=True, slots=True)
class CanonicalPyPIPackage:
    """Original and canonical PyPI distribution identity."""

    original: str
    canonical: str


@dataclass(frozen=True, slots=True)
class CanonicalPyPIVersion:
    """Original and normalized PEP 440 version identity."""

    original: str
    canonical: str
    parsed: Version = field(repr=False)


@dataclass(frozen=True, slots=True)
class CanonicalPyPIPurl:
    """Canonical Phase 3 v1 package-version purl plus decoded identity."""

    original: str
    canonical: str
    package: CanonicalPyPIPackage
    version: CanonicalPyPIVersion


def canonicalize_pypi_ecosystem(value: str) -> PyPIEcosystem:
    """Map the explicit GHSA `pip` alias and canonical `pypi` value to PyPI."""
    if not value or value != value.strip():
        raise UnsupportedEcosystemError("PyPI ecosystem evidence must be a non-empty token.")
    normalized = value.casefold()
    if normalized not in {"pip", "pypi"}:
        raise UnsupportedEcosystemError(f"Unsupported PyPI ecosystem evidence: {value!r}.")
    return PyPIEcosystem.PYPI


def canonicalize_pypi_package(value: str) -> CanonicalPyPIPackage:
    """Validate and normalize a PyPI distribution name using the PyPA specification."""
    if not value or value != value.strip() or _PYPI_NAME_PATTERN.fullmatch(value) is None:
        raise InvalidPackageNameError(f"Invalid PyPI package name: {value!r}.")
    canonical = _PYPI_NAME_SEPARATOR_PATTERN.sub("-", value).lower()
    return CanonicalPyPIPackage(original=value, canonical=canonical)


def canonicalize_pypi_version(value: str) -> CanonicalPyPIVersion:
    """Parse one concrete package version with PEP 440 ordering and normalization."""
    if not value or value != value.strip():
        raise InvalidPackageVersionError(f"Invalid PyPI version: {value!r}.")
    try:
        parsed = Version(value)
    except InvalidVersion as exc:
        raise InvalidPackageVersionError(f"Invalid PyPI version: {value!r}.") from exc
    return CanonicalPyPIVersion(original=value, canonical=str(parsed), parsed=parsed)


def build_pypi_purl(
    *,
    package: CanonicalPyPIPackage,
    version: CanonicalPyPIVersion,
) -> str:
    """Build the canonical purl for one normalized PyPI package-version identity."""
    encoded_name = quote(package.canonical, safe=_PURL_COMPONENT_SAFE)
    encoded_version = quote(version.canonical, safe=_PURL_COMPONENT_SAFE)
    return f"pkg:pypi/{encoded_name}@{encoded_version}"


def canonicalize_pypi_purl(
    value: str,
    *,
    expected_package: CanonicalPyPIPackage | None = None,
    expected_version: CanonicalPyPIVersion | None = None,
) -> CanonicalPyPIPurl:
    """Validate a narrow package-version PyPI purl and reconstruct its canonical form.

    Phase 3 v1 deliberately rejects qualifiers and subpaths instead of dropping them.
    When expected package/version evidence is supplied, disagreement fails closed.
    """
    if not value or value != value.strip():
        raise InvalidPackagePurlError("PyPI purl must be a non-empty canonicalizable token.")
    if "?" in value or "#" in value:
        raise UnsupportedPackagePurlFeatureError(
            "PyPI purl qualifiers and subpaths are outside the Phase 3 v1 contract."
        )

    match = _PURL_PATTERN.fullmatch(value)
    if match is None:
        raise InvalidPackagePurlError(f"Invalid Phase 3 PyPI purl: {value!r}.")

    raw_type = match.group("type")
    if raw_type.casefold() != PyPIEcosystem.PYPI.value:
        raise UnsupportedEcosystemError(f"Unsupported purl type for PyPI evaluator: {raw_type!r}.")

    decoded_name = _decode_purl_component(match.group("name"), component="name")
    decoded_version = _decode_purl_component(match.group("version"), component="version")
    package = canonicalize_pypi_package(decoded_name)
    version = canonicalize_pypi_version(decoded_version)

    if expected_package is not None and package.canonical != expected_package.canonical:
        raise InvalidPackagePurlError(
            "PyPI purl package does not match the separately supplied package evidence."
        )
    if expected_version is not None and version.parsed != expected_version.parsed:
        raise InvalidPackagePurlError(
            "PyPI purl version does not match the separately supplied version evidence."
        )

    return CanonicalPyPIPurl(
        original=value,
        canonical=build_pypi_purl(package=package, version=version),
        package=package,
        version=version,
    )


def _decode_purl_component(value: str, *, component: str) -> str:
    """Percent-decode one purl component with strict escape and UTF-8 validation."""
    if _INVALID_PERCENT_ESCAPE_PATTERN.search(value) is not None:
        raise InvalidPackagePurlError(f"PyPI purl {component} contains an invalid percent escape.")
    try:
        decoded = unquote_to_bytes(value).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise InvalidPackagePurlError(
            f"PyPI purl {component} is not valid UTF-8 after percent decoding."
        ) from exc
    if not decoded:
        raise InvalidPackagePurlError(f"PyPI purl {component} cannot be empty.")
    return decoded
