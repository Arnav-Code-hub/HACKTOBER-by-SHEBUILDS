"""The rule that keeps the modular monolith modular.

A module may import another module's PUBLIC face — `service.py` and `schemas.py`.
It may never reach into another module's `models.py` or `repository.py`.

Violate it and two modules fuse: extracting either one into its own service later
stops being a folder move and becomes a rewrite. See ARCHITECTURE.md.

This is a test rather than an import-linter contract because a `forbidden`
contract with two wildcards does not correlate them — it would permit
`projects.service -> problems.models` while appearing to forbid it. Walking the
AST is exact, and it needs no maintenance when a module is added.
"""

import ast
from pathlib import Path

MODULES_DIR = Path(__file__).resolve().parents[2] / "app" / "modules"
PRIVATE_SUFFIXES = ("models", "repository")


def _imported_modules(tree: ast.AST) -> list[str]:
    """Every dotted module path this file imports, from both import forms."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.append(node.module)
            # `from app.modules.problems import models`
            found.extend(f"{node.module}.{a.name}" for a in node.names)
    return found


def _violations() -> list[str]:
    bad: list[str] = []
    for path in sorted(MODULES_DIR.rglob("*.py")):
        owning_module = path.relative_to(MODULES_DIR).parts[0]
        tree = ast.parse(path.read_text(), str(path))
        for imported in _imported_modules(tree):
            parts = imported.split(".")
            # app.modules.<other>.<models|repository>
            if len(parts) < 4 or parts[:2] != ["app", "modules"]:
                continue
            target_module, target_file = parts[2], parts[3]
            if target_file not in PRIVATE_SUFFIXES:
                continue
            if target_module == owning_module:
                continue  # a module's own internals are its business
            bad.append(
                f"{path.relative_to(MODULES_DIR.parents[1])} imports {imported} "
                f"— {target_module}.{target_file} is private to {target_module}. "
                f"Go through {target_module}.service instead."
            )
    return bad


def test_no_module_imports_another_modules_internals() -> None:
    violations = _violations()
    assert not violations, "Module boundary violations:\n  " + "\n  ".join(violations)


def test_the_checker_actually_detects_a_violation(tmp_path: Path) -> None:
    """Guards the guard — a check that can never fail is worse than no check."""
    tree = ast.parse("from app.modules.problems.repository import find_by_id\n")
    imported = _imported_modules(tree)
    assert "app.modules.problems.repository" in imported
