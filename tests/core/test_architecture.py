"""Architecture tests for layering and import-graph rules."""

import ast
from ast import Import, ImportFrom
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "afanes"
MODEL_ROOT = SOURCE_ROOT / "models"
CORE_ROOT = SOURCE_ROOT / "core"
UI_ROOT = SOURCE_ROOT / "ui"


def _python_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


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
