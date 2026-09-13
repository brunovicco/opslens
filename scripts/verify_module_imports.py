#!/usr/bin/env python3
"""Import every ``opslens`` module and fail closed on the first broken module.

Annotations in this repository are evaluated at runtime — ``TID251`` bans
``from __future__ import annotations`` — so an unquoted forward reference, a
``TYPE_CHECKING``-only name used in a runtime annotation, or a circular import
raises at import time rather than at first use. Walking every module turns that
class of defect into a single deterministic gate.
"""

import importlib
import pkgutil
import sys

from _demo_bootstrap import ensure_repository_src_on_path

ensure_repository_src_on_path()

import opslens  # noqa: E402


class ModuleImportError(RuntimeError):
    """Raised when at least one repository module fails to import."""


def _walk_module_names() -> tuple[str, ...]:
    """Return every importable module name below the ``opslens`` package."""
    discovery_failures: list[str] = []

    def _record(name: str) -> None:
        discovery_failures.append(name)

    names = tuple(
        module.name
        for module in pkgutil.walk_packages(opslens.__path__, "opslens.", onerror=_record)
    )
    if discovery_failures:
        joined = ", ".join(sorted(discovery_failures))
        raise ModuleImportError(f"package discovery failed for: {joined}")
    return names


def verify_module_imports() -> int:
    """Import every module and return the count, raising on any failure."""
    names = _walk_module_names()
    failures: list[str] = []
    for name in names:
        try:
            importlib.import_module(name)
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    if failures:
        joined = "\n  ".join(failures)
        raise ModuleImportError(f"{len(failures)} module(s) failed to import:\n  {joined}")
    return len(names)


def main() -> int:
    """Report the imported module count or the failing modules."""
    try:
        imported = verify_module_imports()
    except ModuleImportError as exc:
        print(f"module import verification FAILED\n{exc}", file=sys.stderr)
        return 1
    print(f"module import verification PASSED: {imported} modules imported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
