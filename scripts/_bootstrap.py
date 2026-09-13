"""Bootstrap repository-local OpsLens imports for direct script execution.

Every script under ``scripts/`` runs from a checkout rather than from an installed
distribution, so ``src`` has to reach ``sys.path`` before the first ``opslens``
import. Importing this helper and calling it keeps that explicit at each entry
point instead of depending on the caller exporting ``PYTHONPATH=src``.
"""

import sys
from pathlib import Path


def ensure_repository_src_on_path() -> None:
    """Add the checked-out repository's ``src`` directory to ``sys.path`` once."""
    repository_root = Path(__file__).resolve().parents[1]
    src_path = repository_root / "src"
    package_init = src_path / "opslens" / "__init__.py"
    if not package_init.is_file():
        raise RuntimeError(f"OpsLens source package not found at {package_init}")

    src_text = str(src_path)
    if src_text not in sys.path:
        sys.path.insert(0, src_text)
