#!/usr/bin/env python3
"""Verify retained Lambda telemetry content-minimization invariants."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src" / "opslens"
POWERTOOLS_PATH = SOURCE_ROOT / "shared" / "observability" / "powertools.py"


class TelemetrySafetyError(RuntimeError):
    """Raised when retained telemetry can silently regain content-bearing capture."""


def _attribute_name(node: ast.expr) -> str | None:
    """Return a dotted attribute/callable name when statically representable."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _attribute_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _literal_false_keyword(call: ast.Call, name: str) -> bool:
    """Return true only for an explicit keyword bound to literal False."""
    for keyword in call.keywords:
        if keyword.arg == name:
            return isinstance(keyword.value, ast.Constant) and keyword.value.value is False
    return False


def _powertools_lambda_files() -> tuple[Path, ...]:
    """Return Python modules that instantiate a Powertools Tracer and define Lambda entrypoints."""
    candidates: list[Path] = []
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "Tracer(" in text and "def lambda_handler(" in text:
            candidates.append(path)
    return tuple(candidates)


def _verify_lambda_decorators(path: Path) -> None:
    """Require event, response, and error auto-capture to be explicitly disabled."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    handlers = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "lambda_handler"
    ]
    if len(handlers) != 1:
        raise TelemetrySafetyError(f"{path}: expected exactly one lambda_handler")

    handler = handlers[0]
    logger_decorator: ast.Call | None = None
    tracer_decorator: ast.Call | None = None

    for decorator in handler.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        name = _attribute_name(decorator.func)
        if name == "logger.inject_lambda_context":
            logger_decorator = decorator
        elif name == "tracer.capture_lambda_handler":
            tracer_decorator = decorator

    if logger_decorator is None:
        raise TelemetrySafetyError(
            f"{path}: Powertools Lambda handler must use logger.inject_lambda_context"
        )
    if not _literal_false_keyword(logger_decorator, "log_event"):
        raise TelemetrySafetyError(
            f"{path}: Lambda event logging must be explicitly disabled with log_event=False"
        )

    if tracer_decorator is None:
        raise TelemetrySafetyError(
            f"{path}: Powertools Lambda handler must use tracer.capture_lambda_handler"
        )
    if not _literal_false_keyword(tracer_decorator, "capture_response"):
        raise TelemetrySafetyError(
            f"{path}: trace response capture must be explicitly disabled"
        )
    if not _literal_false_keyword(tracer_decorator, "capture_error"):
        raise TelemetrySafetyError(
            f"{path}: trace error capture must be explicitly disabled"
        )


def _verify_exception_adapter() -> None:
    """Require shared failure logging to avoid implicit active-exception serialization."""
    tree = ast.parse(
        POWERTOOLS_PATH.read_text(encoding="utf-8"),
        filename=str(POWERTOOLS_PATH),
    )
    telemetry_class = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "PowertoolsTelemetry"
        ),
        None,
    )
    if telemetry_class is None:
        raise TelemetrySafetyError("PowertoolsTelemetry class is missing")

    exception_method = next(
        (
            node
            for node in telemetry_class.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "exception"
        ),
        None,
    )
    if exception_method is None:
        raise TelemetrySafetyError("PowertoolsTelemetry.exception is missing")

    logger_calls: list[str] = []
    for node in ast.walk(exception_method):
        if not isinstance(node, ast.Call):
            continue
        name = _attribute_name(node.func)
        if name is not None and name.startswith("self._logger."):
            logger_calls.append(name)
            if name == "self._logger.exception":
                raise TelemetrySafetyError(
                    "PowertoolsTelemetry.exception must not serialize the active exception/traceback"
                )
            for keyword in node.keywords:
                if keyword.arg in {"exc_info", "stack_info"}:
                    if not (
                        isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is False
                    ):
                        raise TelemetrySafetyError(
                            "failure logging must not enable exc_info or stack_info"
                        )

    if logger_calls != ["self._logger.error"]:
        raise TelemetrySafetyError(
            "PowertoolsTelemetry.exception must emit exactly one content-minimized logger.error call"
        )


def verify() -> int:
    """Run the repository-wide telemetry safety checks and return handler count."""
    handlers = _powertools_lambda_files()
    if not handlers:
        raise TelemetrySafetyError("no Powertools Lambda handlers were discovered")

    for path in handlers:
        _verify_lambda_decorators(path)
    _verify_exception_adapter()
    return len(handlers)


def main() -> None:
    """Run telemetry verification and emit stable machine-readable success evidence."""
    handler_count = verify()
    print(f"telemetry_safety_invariants=PASS handlers={handler_count}")


if __name__ == "__main__":
    main()
