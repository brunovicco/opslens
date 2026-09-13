"""Architecture tests keeping the verifier registry honest about what each script is.

`scripts/` holds 28 files named `verify_*.py` and they are two different kinds of
tool. Standing verifiers take no required argument and must pass on any change.
Evidence admission tools take a plan, manifest or measurement artifact and admit or
reject it; they cannot pass on their own and were never meant to.

The registry in `scripts/run_repository_invariants.py` declares which is which. A
declaration nobody checks is a comment, so these tests derive the answer from each
script's own argparse definition and require the registry to agree.

```text
standing invariant != admitted evidence
```
"""

import ast
import pathlib
from typing import Final

import pytest

_REPOSITORY_ROOT: Final = pathlib.Path(__file__).resolve().parents[3]
_SCRIPTS_ROOT: Final = _REPOSITORY_ROOT / "scripts"
_RUNNER: Final = _SCRIPTS_ROOT / "run_repository_invariants.py"


def _registry(name: str) -> tuple[str, ...]:
    """Read one declared tuple out of the runner without importing it.

    Args:
        name: The module-level tuple to read.

    Returns:
        The declared file names.
    """
    tree = ast.parse(_RUNNER.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign | ast.Assign):
            continue
        target = node.target if isinstance(node, ast.AnnAssign) else node.targets[0]
        if not (isinstance(target, ast.Name) and target.id == name):
            continue
        value = node.value
        if not isinstance(value, ast.Tuple):
            break
        return tuple(
            element.value
            for element in value.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        )
    raise AssertionError(f"{_RUNNER.name} declares no tuple named {name}")


def _required_arguments(path: pathlib.Path) -> tuple[str, ...]:
    """Return the argparse arguments a script cannot run without.

    Positional arguments and `required=True` flags both count. Everything else is
    optional and therefore does not stop the script from running bare.

    Args:
        path: The script to inspect.

    Returns:
        The names of the required arguments, in source order.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    required: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "add_argument":
            continue
        names = [
            argument.value
            for argument in node.args
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
        ]
        is_positional = bool(names) and not names[0].startswith("-")
        is_explicitly_required = any(
            keyword.arg == "required"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in node.keywords
        )
        if is_positional or is_explicitly_required:
            required.append(names[0] if names else "<unnamed>")
    return tuple(required)


_VERIFIERS: Final = tuple(sorted(path.name for path in _SCRIPTS_ROOT.glob("verify_*.py")))
_STANDING: Final = _registry("STANDING_VERIFIERS")
_ADMISSION: Final = _registry("EVIDENCE_ADMISSION_TOOLS")


def test_there_are_verifiers_to_classify() -> None:
    """A glob that silently matches nothing would make every test below vacuous."""
    assert len(_VERIFIERS) >= 20


def test_every_verifier_is_classified_exactly_once() -> None:
    """A new verifier cannot be added without saying which kind of tool it is."""
    assert sorted(set(_STANDING) | set(_ADMISSION)) == list(_VERIFIERS)
    assert set(_STANDING) & set(_ADMISSION) == set()


def test_the_registry_names_no_script_that_does_not_exist() -> None:
    """A renamed or deleted verifier must not linger in the registry."""
    assert set(_STANDING) | set(_ADMISSION) <= set(_VERIFIERS)


def test_the_registry_has_no_duplicate_entries() -> None:
    """A duplicated entry would run one verifier twice and miscount the total."""
    assert len(_STANDING) == len(set(_STANDING))
    assert len(_ADMISSION) == len(set(_ADMISSION))


@pytest.mark.parametrize("name", _STANDING)
def test_a_standing_verifier_runs_with_no_arguments(name: str) -> None:
    """Classified as standing means the runner can invoke it bare — so it must be able to."""
    required = _required_arguments(_SCRIPTS_ROOT / name)

    assert required == (), (
        f"{name} is registered as a standing verifier but requires {list(required)}; "
        "register it as an evidence admission tool instead"
    )


@pytest.mark.parametrize("name", _ADMISSION)
def test_an_evidence_admission_tool_requires_its_input(name: str) -> None:
    """A tool with no required input is a standing verifier hiding in the wrong list."""
    required = _required_arguments(_SCRIPTS_ROOT / name)

    assert required, (
        f"{name} is registered as an evidence admission tool but requires no "
        "argument; register it as a standing verifier so it actually runs in CI"
    )
