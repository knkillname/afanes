"""Architecture tests for layering, imports, and object ownership.

The ownership gate enforces the end state described in ``AGENTS.md`` section
4.3. During ``refactor-object-ownership`` the gate carries a temporary
allowlist; each phase removes its entries until only the final entries remain:

- ``core/names.py`` (name and filename policy)
- ``core/atomic.py`` (the atomic write primitive)
- ``ui/strings.py`` (user-facing copy)
- the ``main`` callbacks in ``ui/app.py`` and ``__main__.py`` plus the
  ``argparse`` callback ``_port_number``

The migration order is policy and gate, leaf value objects, vault ownership,
page and draft unions, query services, shared UI components, the ``AppState``
facade split, remaining public functions, then final verification. Do not add a
temporary entry without an approved change, and delete each entry when its
phase passes.
"""

import ast
from ast import Import, ImportFrom
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "afanes"
MODEL_ROOT = SOURCE_ROOT / "models"
CORE_ROOT = SOURCE_ROOT / "core"
UI_ROOT = SOURCE_ROOT / "ui"
VIEW_ROOT = UI_ROOT / "views"

# Final state: ``None`` allows every module-level function in that file.
FINAL_FUNCTION_ALLOWLIST: dict[str, frozenset[str] | None] = {
    "core/names.py": None,
    "core/atomic.py": None,
    "ui/strings.py": None,
    "ui/app.py": frozenset({"main"}),
    "__main__.py": frozenset({"main", "_port_number"}),
}

# Temporary entries removed phase by phase. The final state is empty.
TEMPORARY_FUNCTION_ALLOWLIST: dict[str, frozenset[str] | None] = {}

# Temporary exemptions for the duplicate view-helper and field-budget rules.
TEMPORARY_DUPLICATE_HELPER_ALLOWLIST: frozenset[str] = frozenset()
TEMPORARY_FIELD_BUDGET_ALLOWLIST: frozenset[str] = frozenset()

DUPLICATE_VIEW_HELPERS = frozenset({"_banner", "_status_label", "_panel", "_card"})
APP_STATE_FIELD_BUDGET = 10


def _python_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _relative_source_path(path: Path) -> str:
    return path.relative_to(SOURCE_ROOT).as_posix()


def _module_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)}


def _module_name(path: Path) -> str:
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = relative.parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(("afanes", *parts))


def _imports(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, Import):
            found.extend((alias.name, 0) for alias in node.names)
        elif isinstance(node, ImportFrom):
            found.append((node.module or "", node.level))
    return found


def _first_party_imports(path: Path) -> set[str]:
    modules: set[str] = set()
    for module, level in _imports(path):
        if level != 0:
            continue
        if module == "afanes" or module.startswith("afanes."):
            modules.add(module)
    return modules


class TestImportBoundaries:
    def test_models_import_only_the_standard_library(self) -> None:
        offenders: list[str] = []
        for path in _python_files(MODEL_ROOT):
            for module, level in _imports(path):
                if level != 0 or module == "afanes" or module.startswith("afanes."):
                    offenders.append(f"{path.name}: {module or '<relative>'}")
        assert offenders == []

    def test_models_do_not_import_core_ui_or_cli(self) -> None:
        forbidden = ("afanes.core", "afanes.ui", "afanes.cli")
        offenders: list[str] = []
        for path in _python_files(MODEL_ROOT):
            offenders.extend(
                f"{path.name}: {module}" for module in _first_party_imports(path) if module.startswith(forbidden)
            )
        assert offenders == []

    def test_core_does_not_import_ui_or_cli(self) -> None:
        forbidden = ("afanes.ui", "afanes.cli")
        offenders: list[str] = []
        for path in _python_files(CORE_ROOT):
            offenders.extend(
                f"{path.name}: {module}" for module in _first_party_imports(path) if module.startswith(forbidden)
            )
        assert offenders == []

    def test_names_module_is_a_standard_library_leaf(self) -> None:
        path = CORE_ROOT / "names.py"
        assert path.is_file()
        for module, level in _imports(path):
            assert level == 0
            assert module != "afanes"
            assert not module.startswith("afanes.")

    def test_note_vocabulary_module_is_a_standard_library_leaf(self) -> None:
        path = MODEL_ROOT / "note.py"
        assert path.is_file()
        for module, level in _imports(path):
            assert level == 0
            assert module != "afanes"
            assert not module.startswith("afanes.")

    def test_no_module_imports_a_person_model(self) -> None:
        assert all("afanes.models.person" not in _first_party_imports(path) for path in _python_files(SOURCE_ROOT))

    def test_atomic_module_imports_only_the_standard_library_and_errors(self) -> None:
        path = CORE_ROOT / "atomic.py"
        assert path.is_file()
        for module, level in _imports(path):
            assert level == 0
            if module == "afanes.core.errors":
                continue
            assert module != "afanes"
            assert not module.startswith("afanes.")

    def test_settings_does_not_import_the_vault_module(self) -> None:
        path = CORE_ROOT / "settings.py"
        assert path.is_file()
        assert "afanes.core.vault" not in _first_party_imports(path)

    def test_models_do_not_import_the_names_module(self) -> None:
        assert all("afanes.core.names" not in _first_party_imports(path) for path in _python_files(MODEL_ROOT))

    def test_source_uses_no_relative_imports(self) -> None:
        offenders: list[str] = []
        for path in _python_files(SOURCE_ROOT):
            for module, level in _imports(path):
                if level != 0:
                    offenders.append(f"{path.name}: level {level} {module}")
        assert offenders == []

    def test_import_graph_is_acyclic(self) -> None:
        graph: dict[str, set[str]] = {}
        for path in _python_files(SOURCE_ROOT):
            graph[_module_name(path)] = _first_party_imports(path)

        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(node: str) -> None:
            if node in visited:
                return
            assert node not in visiting, f"import cycle at {node}"
            visiting.add(node)
            for dependency in graph.get(node, set()):
                if dependency in graph:
                    visit(dependency)
            visiting.remove(node)
            visited.add(node)

        for module in graph:
            visit(module)


class TestUiLayering:
    def test_ui_does_not_import_cli(self) -> None:
        offenders: list[str] = []
        for path in _python_files(UI_ROOT):
            offenders.extend(
                f"{path.name}: {module}" for module in _first_party_imports(path) if module.startswith("afanes.cli")
            )
        assert offenders == []

    def test_state_does_not_import_views_or_components(self) -> None:
        path = UI_ROOT / "state.py"
        forbidden = ("afanes.ui.views", "afanes.ui.components")
        offenders = [module for module in _first_party_imports(path) if module.startswith(forbidden)]
        assert offenders == []

    def test_theme_and_strings_are_import_leaves(self) -> None:
        offenders: list[str] = []
        for name in ("theme.py", "strings.py"):
            path = UI_ROOT / name
            offenders.extend(f"{path.name}: {module}" for module in _first_party_imports(path))
        assert offenders == []


class TestObjectOwnership:
    def test_temporary_allowlists_are_empty(self) -> None:
        assert TEMPORARY_FUNCTION_ALLOWLIST == {}
        assert frozenset() == TEMPORARY_DUPLICATE_HELPER_ALLOWLIST
        assert frozenset() == TEMPORARY_FIELD_BUDGET_ALLOWLIST

    def test_final_allowlist_is_exact(self) -> None:
        assert {
            "core/names.py": None,
            "core/atomic.py": None,
            "ui/strings.py": None,
            "ui/app.py": frozenset({"main"}),
            "__main__.py": frozenset({"main", "_port_number"}),
        } == FINAL_FUNCTION_ALLOWLIST

    def test_module_functions_are_owned(self) -> None:
        offenders: list[str] = []
        for path in _python_files(SOURCE_ROOT):
            relative = _relative_source_path(path)
            allowed = FINAL_FUNCTION_ALLOWLIST.get(relative)
            temporary = TEMPORARY_FUNCTION_ALLOWLIST.get(relative)
            functions = _module_functions(path)
            if allowed is None and relative in FINAL_FUNCTION_ALLOWLIST:
                continue
            if temporary is None and relative in TEMPORARY_FUNCTION_ALLOWLIST:
                continue
            permitted = set() if allowed is None else set(allowed)
            if temporary is not None:
                permitted.update(temporary)
            offenders.extend(f"{relative}: {name}" for name in sorted(functions - permitted))
        assert offenders == []

    def test_views_do_not_define_duplicate_helpers(self) -> None:
        offenders: list[str] = []
        for path in _python_files(VIEW_ROOT):
            relative = _relative_source_path(path)
            if relative in TEMPORARY_DUPLICATE_HELPER_ALLOWLIST:
                continue
            offenders.extend(f"{relative}: {name}" for name in sorted(_module_functions(path) & DUPLICATE_VIEW_HELPERS))
        assert offenders == []

    def test_app_state_respects_its_field_budget(self) -> None:
        relative = "ui/state.py"
        if relative in TEMPORARY_FIELD_BUDGET_ALLOWLIST:
            return
        path = UI_ROOT / "state.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        state_class = next(
            (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AppState"),
            None,
        )
        assert state_class is not None
        fields = [
            node.target
            for node in state_class.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        ]
        assert len(fields) <= APP_STATE_FIELD_BUDGET, [field.id for field in fields]
