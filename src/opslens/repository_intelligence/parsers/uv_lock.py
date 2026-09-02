"""Deterministically parse verified inert `uv.lock` bytes into typed package evidence."""

from __future__ import annotations

import tomllib
from typing import cast

from opslens.repository_intelligence.domain import (
    ImmutableRepositoryFileEvidence,
    InvalidUvLockError,
    MAX_UV_LOCK_PACKAGE_RECORDS,
    PYPI_SIMPLE_REGISTRY_URL,
    ParsedUvLockEvidence,
    SUPPORTED_UV_LOCK_REVISIONS,
    SUPPORTED_UV_LOCK_SCHEMA_VERSION,
    UV_LOCK_PATH,
    UnsupportedUvLockSchemaError,
    UvLockedPyPIPackageEvidence,
    UvUnsupportedLockedPackageEvidence,
    UvUnsupportedPackageReason,
)


def parse_uv_lock_evidence(
    file_evidence: ImmutableRepositoryFileEvidence,
) -> ParsedUvLockEvidence:
    """Parse one integrity-verified `uv.lock` without executing repository tooling."""
    if file_evidence.path != UV_LOCK_PATH:
        raise InvalidUvLockError("uv.lock parser accepts only verified `uv.lock` evidence.")

    try:
        source_text = file_evidence.content_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidUvLockError("uv.lock content must be valid UTF-8 TOML.") from exc

    try:
        root_object = cast(object, tomllib.loads(source_text))
    except tomllib.TOMLDecodeError as exc:
        raise InvalidUvLockError("uv.lock content is not valid TOML.") from exc

    if not isinstance(root_object, dict):
        raise InvalidUvLockError("uv.lock TOML root must be a table.")
    root = cast(dict[str, object], root_object)

    schema_version = _required_int(root, "version")
    if schema_version != SUPPORTED_UV_LOCK_SCHEMA_VERSION:
        raise UnsupportedUvLockSchemaError(
            f"uv.lock schema version {schema_version} is outside the supported v1 contract."
        )

    revision = _optional_int(root, "revision")
    if revision is not None and revision not in SUPPORTED_UV_LOCK_REVISIONS:
        raise UnsupportedUvLockSchemaError(
            f"uv.lock revision {revision} is outside the supported revision window."
        )

    requires_python = _optional_clean_str(root, "requires-python")
    resolution_markers = _optional_marker_tuple(root, "resolution-markers")
    package_records = _required_package_records(root)

    pypi_packages: list[UvLockedPyPIPackageEvidence] = []
    unsupported_packages: list[UvUnsupportedLockedPackageEvidence] = []

    for record_index, record_object in enumerate(package_records):
        if not isinstance(record_object, dict):
            raise InvalidUvLockError(
                f"uv.lock package record {record_index} must be a TOML table."
            )
        record = cast(dict[str, object], record_object)
        name = _required_clean_str(record, "name", context=f"package[{record_index}]")
        version = _required_clean_str(
            record,
            "version",
            context=f"package[{record_index}]",
        )
        markers = _optional_marker_tuple(
            record,
            "resolution-markers",
            context=f"package[{record_index}]",
        )
        source = _required_source(record, record_index=record_index)
        source_kind, source_value = next(iter(source.items()))

        if source_kind == "registry" and source_value == PYPI_SIMPLE_REGISTRY_URL:
            pypi_packages.append(
                UvLockedPyPIPackageEvidence(
                    record_index=record_index,
                    name_original=name,
                    version_original=version,
                    registry_url=source_value,
                    resolution_markers=markers,
                )
            )
            continue

        unsupported_packages.append(
            UvUnsupportedLockedPackageEvidence(
                record_index=record_index,
                name_original=name,
                version_original=version,
                source_kind=_unsupported_source_kind(source_kind),
                reason_code=_unsupported_reason(source_kind),
                resolution_markers=markers,
            )
        )

    return ParsedUvLockEvidence(
        file_evidence=file_evidence,
        schema_version=schema_version,
        revision=revision,
        requires_python=requires_python,
        resolution_markers=resolution_markers,
        pypi_packages=tuple(pypi_packages),
        unsupported_packages=tuple(unsupported_packages),
    )


def _required_package_records(root: dict[str, object]) -> list[object]:
    """Return a non-empty package array inside the explicit logical-work bound."""
    value = root.get("package")
    if not isinstance(value, list):
        raise InvalidUvLockError("uv.lock must contain a top-level package array.")
    package_records = cast(list[object], value)
    if not package_records:
        raise InvalidUvLockError("uv.lock package array must not be empty.")
    if len(package_records) > MAX_UV_LOCK_PACKAGE_RECORDS:
        raise InvalidUvLockError(
            "uv.lock package array exceeds the 5000-record parser work bound."
        )
    return package_records


def _required_source(
    record: dict[str, object],
    *,
    record_index: int,
) -> dict[str, str]:
    """Return one unambiguous source-kind/value pair without source normalization."""
    source_object = record.get("source")
    if not isinstance(source_object, dict):
        raise InvalidUvLockError(
            f"uv.lock package[{record_index}] must contain a source table."
        )
    source = cast(dict[str, object], source_object)
    if len(source) != 1:
        raise InvalidUvLockError(
            f"uv.lock package[{record_index}] source must contain exactly one source kind."
        )

    source_kind, source_value = next(iter(source.items()))
    if not source_kind or source_kind != source_kind.strip():
        raise InvalidUvLockError(
            f"uv.lock package[{record_index}] source kind must be a clean string."
        )
    if (
        not isinstance(source_value, str)
        or not source_value
        or source_value != source_value.strip()
    ):
        raise InvalidUvLockError(
            f"uv.lock package[{record_index}] source value must be a clean string."
        )
    return {source_kind: source_value}


def _unsupported_source_kind(source_kind: str) -> str:
    """Map unsupported source authority to an explicit stable classification."""
    if source_kind == "registry":
        return "custom_registry"
    if source_kind in {"path", "directory"}:
        return "path"
    return source_kind


def _unsupported_reason(source_kind: str) -> UvUnsupportedPackageReason:
    """Classify why a structurally valid source is outside first-gate PyPI support."""
    if source_kind == "registry":
        return UvUnsupportedPackageReason.UNSUPPORTED_REGISTRY
    if source_kind in {"virtual", "editable", "git", "path", "directory"}:
        return UvUnsupportedPackageReason.UNSUPPORTED_NON_REGISTRY_SOURCE
    return UvUnsupportedPackageReason.UNSUPPORTED_SOURCE_KIND


def _required_int(payload: dict[str, object], field: str) -> int:
    """Return one required TOML integer while rejecting booleans."""
    value = payload.get(field)
    if type(value) is not int:
        raise InvalidUvLockError(f"uv.lock field {field!r} must contain an integer.")
    return value


def _optional_int(payload: dict[str, object], field: str) -> int | None:
    """Return one optional TOML integer while rejecting booleans and other types."""
    if field not in payload:
        return None
    value = payload[field]
    if type(value) is not int:
        raise InvalidUvLockError(f"uv.lock field {field!r} must contain an integer.")
    return value


def _required_clean_str(
    payload: dict[str, object],
    field: str,
    *,
    context: str = "uv.lock",
) -> str:
    """Return one required non-empty string without rewriting source spelling."""
    value = payload.get(field)
    if not isinstance(value, str) or not value or value != value.strip():
        raise InvalidUvLockError(
            f"{context} field {field!r} must contain a non-empty clean string."
        )
    return value


def _optional_clean_str(payload: dict[str, object], field: str) -> str | None:
    """Return one optional non-empty string without rewriting source spelling."""
    if field not in payload:
        return None
    return _required_clean_str(payload, field)


def _optional_marker_tuple(
    payload: dict[str, object],
    field: str,
    *,
    context: str = "uv.lock",
) -> tuple[str, ...]:
    """Preserve ordered resolution-marker strings without evaluating their semantics."""
    if field not in payload:
        return ()
    value = payload[field]
    if not isinstance(value, list):
        raise InvalidUvLockError(f"{context} field {field!r} must contain an array.")

    markers: list[str] = []
    for marker_index, marker in enumerate(cast(list[object], value)):
        if not isinstance(marker, str) or not marker or marker != marker.strip():
            raise InvalidUvLockError(
                f"{context} {field}[{marker_index}] must be a non-empty clean string."
            )
        markers.append(marker)
    return tuple(markers)
