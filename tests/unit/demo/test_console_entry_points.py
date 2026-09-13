"""Architecture tests for the installed console scripts and their repository shims.

The project declares three console scripts. Each one must resolve to a callable
inside the shipped package, and each one must be the same code path as the
`scripts/` entry point a reviewer runs from a checkout. If the two can drift,
one of them is untested by definition: the installed command would be dead
weight, or the documented reviewer path would be.
"""

import ast
import importlib
import pathlib
import tomllib
from collections.abc import Mapping
from typing import Final, cast

import pytest

_REPO_ROOT: Final = pathlib.Path(__file__).resolve().parents[3]
_PYPROJECT: Final = _REPO_ROOT / "pyproject.toml"
_SCRIPTS_ROOT: Final = _REPO_ROOT / "scripts"

_SHIM_FOR_CONSOLE_SCRIPT: Final[Mapping[str, str]] = {
    "opslens-demo": "demo_opslens.py",
    "opslens-demo-evaluate": "evaluate_opslens_demo.py",
    "opslens-demo-web": "demo_opslens_web.py",
}


def _pyproject() -> Mapping[str, object]:
    """Read the project manifest."""
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))


def _declared_console_scripts() -> Mapping[str, str]:
    """Return the declared `[project.scripts]` table."""
    project = cast(Mapping[str, object], _pyproject()["project"])
    return cast(Mapping[str, str], project["scripts"])


def _delegated_module(shim: pathlib.Path) -> str:
    """Return the single `opslens.*` module a repository shim delegates to.

    Args:
        shim: The script under `scripts/` to inspect.

    Returns:
        The dotted module name the shim imports `main` from.
    """
    tree = ast.parse(shim.read_text(encoding="utf-8"))
    targets = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("opslens")
        and any(alias.name == "main" for alias in node.names)
    ]
    assert len(targets) == 1, f"{shim.name} delegates to {len(targets)} modules, expected 1"
    return targets[0]


def test_the_project_declares_a_build_system() -> None:
    """Without a build system the project cannot be installed at all."""
    manifest = _pyproject()

    assert "build-system" in manifest, "pyproject declares no [build-system]"
    build_system = cast(Mapping[str, object], manifest["build-system"])
    assert build_system.get("build-backend"), "[build-system] declares no backend"
    assert cast(list[str], build_system["requires"]), "[build-system] requires nothing"


def test_every_declared_console_script_resolves_to_a_shipped_callable() -> None:
    """An entry point that does not resolve is a broken install, not a broken test."""
    for command, target in sorted(_declared_console_scripts().items()):
        module_name, _, attribute = target.partition(":")
        assert module_name.startswith("opslens."), (
            f"{command} points at {module_name}, which is outside the shipped package"
        )
        assert attribute, f"{command} declares no callable in {target}"

        module = importlib.import_module(module_name)
        entry_point = getattr(module, attribute, None)
        assert callable(entry_point), f"{target} is not callable"


def test_every_console_script_has_a_repository_shim_on_the_same_code_path() -> None:
    """The installed command and the documented reviewer command cannot diverge."""
    declared = _declared_console_scripts()
    assert set(declared) == set(_SHIM_FOR_CONSOLE_SCRIPT), (
        "a console script was added or removed without pairing it with a shim"
    )

    for command, target in sorted(declared.items()):
        shim = _SCRIPTS_ROOT / _SHIM_FOR_CONSOLE_SCRIPT[command]
        assert shim.is_file(), f"{command} has no repository shim at {shim}"

        module_name, _, _attribute = target.partition(":")
        assert _delegated_module(shim) == module_name, (
            f"{shim.name} delegates to a different module than the {command} entry point"
        )


@pytest.mark.parametrize("shim_name", sorted(_SHIM_FOR_CONSOLE_SCRIPT.values()))
def test_a_repository_shim_carries_no_logic_of_its_own(shim_name: str) -> None:
    """Logic in `scripts/` is unreachable from the installed command, so none is allowed."""
    tree = ast.parse((_SCRIPTS_ROOT / shim_name).read_text(encoding="utf-8"))

    defined = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    ]
    assert not defined, f"{shim_name} defines {defined}; that belongs inside the package"

    assigned = [node for node in tree.body if isinstance(node, ast.Assign | ast.AnnAssign)]
    assert not assigned, f"{shim_name} declares module state; that belongs inside the package"
