"""Architecture tests for layering, imports, and object ownership.

The ownership gate enforces the end state described in ``AGENTS.md`` section
4.2: every behavior is a method on an owning class. The only allowed
module-level function is ``entrypoint`` in ``__main__.py``, the installed script
target. Callback functions that an external library receives as objects live on
an owning class or as the local Flet entry closure.

Do not add a free function.
"""

import ast
import re
from ast import Import, ImportFrom
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "afanes"
MODEL_ROOT = SOURCE_ROOT / "models"
CORE_ROOT = SOURCE_ROOT / "core"
I18N_ROOT = SOURCE_ROOT / "i18n"
CLI_ROOT = SOURCE_ROOT / "cli"
UI_ROOT = SOURCE_ROOT / "ui"
VIEW_ROOT = UI_ROOT / "views"

# The single callback exception: the installed script resolves this name.
FINAL_FUNCTION_ALLOWLIST: dict[str, frozenset[str]] = {
    "__main__.py": frozenset({"entrypoint"}),
}

# Temporary entries removed phase by phase. The final state is empty.
TEMPORARY_FUNCTION_ALLOWLIST: dict[str, frozenset[str]] = {}

# Temporary exemptions for the duplicate view-helper and field-budget rules.
TEMPORARY_DUPLICATE_HELPER_ALLOWLIST: frozenset[str] = frozenset()
TEMPORARY_FIELD_BUDGET_ALLOWLIST: frozenset[str] = frozenset()

DUPLICATE_VIEW_HELPERS = frozenset({"_banner", "_status_label", "_panel", "_card"})
APP_STATE_FIELD_BUDGET = 10
CORE_SERVICE_METHOD_BUDGET = 20
CORE_MODULE_LINE_BUDGET = 900
VAULT_SIBLING_MODULES = frozenset(
    {
        "afanes.core.vault.naming",
        "afanes.core.vault.pages",
        "afanes.core.vault.processing",
        "afanes.core.vault.steps",
    }
)
SECTION_HEADING_PATTERN = re.compile(r"^#{2,3}\s+(\d+(?:\.\d+)?)\b", re.MULTILINE)
SECTION_CITATION_PATTERN = re.compile(r"[Ss]ections?\s+(\d+(?:\.\d+)?)|(?:see|through)\s+(\d+(?:\.\d+)?)")
APP_STATE_SURFACE_BUDGET = 10
DOMAIN_CONTROLLER_SURFACE_BUDGET = 25
LABEL_KEYS = frozenset({"type", "category", "status", "due_date", "asked_by", "owner", "date"})
LABEL_OWNER_MODULES = frozenset({"core/labels.py", "core/frontmatter.py"})
TEMPLATE_OPTION_HELPERS = frozenset(
    {"_template_options", "_template_option_text", "_reference_template_options", "_reference_template_text"}
)
TEMPLATE_OPTION_OWNER = "ui/components/template_cards.py"


def _state_paths() -> list[Path]:
    package = UI_ROOT / "state"
    if package.is_dir():
        return sorted(package.rglob("*.py"))
    return [UI_ROOT / "state.py"]


def _is_property(member: ast.stmt) -> bool:
    if not isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef):
        return False
    return any(
        (isinstance(decorator, ast.Name) and decorator.id == "property")
        or (isinstance(decorator, ast.Attribute) and decorator.attr == "setter")
        for decorator in member.decorator_list
    )


def _is_frozen_dataclass(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)):
            continue
        if decorator.func.attr != "dataclass":
            continue
        if any(
            keyword.arg == "frozen" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
            for keyword in decorator.keywords
        ):
            return True
    return False


def _class_surface(members: list[ast.stmt]) -> int:
    names = {
        member.name
        for member in members
        if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef)
        and not member.name.startswith("_")
        and not _is_property(member)
    }
    return len(names)


def _class_commands(members: list[ast.stmt]) -> int:
    commands: set[str] = set()
    for member in members:
        if not isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef) or member.name.startswith("_"):
            continue
        if not _is_property(member):
            commands.add(member.name)
    return len(commands)


def _state_shapes() -> list[tuple[Path, str, bool, int]]:
    shapes: list[tuple[Path, str, bool, int]] = []
    for path in _state_paths():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if _is_frozen_dataclass(node):
                continue
            fields = any(isinstance(member, ast.AnnAssign) for member in node.body)
            shapes.append((path, node.name, fields, _class_commands(node.body)))
    return shapes


def _numbered_sections(text: str) -> set[str]:
    return set(SECTION_HEADING_PATTERN.findall(text))


def _section_citations(text: str) -> set[str]:
    citations: set[str] = set()
    for plural, single in SECTION_CITATION_PATTERN.findall(text):
        citations.add(plural or single)
    return citations


def _unresolved_citations(name: str, text: str, sections: set[str]) -> list[str]:
    return [f"{name}: section {number}" for number in sorted(_section_citations(text) - sections)]


def _live_documents() -> list[Path]:
    documents = [REPO_ROOT / "AGENTS.md", REPO_ROOT / "README.md", REPO_ROOT / "CHANGELOG.md"]
    documents.extend(sorted((REPO_ROOT / "openspec" / "specs").rglob("*.md")))
    documents.extend(sorted((REPO_ROOT / "openspec" / "config.yaml").parent.glob("config.yaml")))
    documents.extend(sorted((REPO_ROOT / "src").rglob("*.py")))
    documents.extend(sorted((REPO_ROOT / "tests").rglob("*.py")))
    return [path for path in documents if path.is_file()]


def _state_surfaces() -> list[tuple[Path, str, int]]:
    surfaces: list[tuple[Path, str, int]] = []
    for path in _state_paths():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        surfaces.extend(
            (path, node.name, _class_surface(node.body)) for node in tree.body if isinstance(node, ast.ClassDef)
        )
    return surfaces


def _public_methods(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    counts: list[tuple[str, int]] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        methods = [
            member
            for member in node.body
            if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef) and not member.name.startswith("_")
        ]
        counts.append((node.name, len(methods)))
    return counts


def _python_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _relative_source_path(path: Path) -> str:
    return path.relative_to(SOURCE_ROOT).as_posix()


def _module_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)}


def _defined_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)}


def _subscript_key(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Subscript):
        return None
    if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
        return node.slice.value
    return None


def _label_key_writes(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    writes: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            key = _subscript_key(node)
            if key in LABEL_KEYS:
                writes.append(f"line {node.lineno}: assignment to {key!r}")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "pop"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value in LABEL_KEYS
        ):
            writes.append(f"line {node.lineno}: pop of {node.args[0].value!r}")
    return writes


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

    def test_core_does_not_import_i18n(self) -> None:
        offenders: list[str] = []
        for path in _python_files(CORE_ROOT):
            offenders.extend(
                f"{path.name}: {module}"
                for module in _first_party_imports(path)
                if module == "afanes.i18n" or module.startswith("afanes.i18n.")
            )
        assert offenders == []

    def test_i18n_does_not_import_ui_cli_or_flet(self) -> None:
        forbidden = ("afanes.ui", "afanes.cli")
        offenders: list[str] = []
        for path in _python_files(I18N_ROOT):
            offenders.extend(
                f"{path.name}: {module}" for module in _first_party_imports(path) if module.startswith(forbidden)
            )
            offenders.extend(
                f"{path.name}: {module}"
                for module, level in _imports(path)
                if level == 0 and (module == "flet" or module.startswith("flet."))
            )
        assert offenders == []

    def test_i18n_imports_only_the_standard_library_models_core_and_itself(self) -> None:
        allowed = ("afanes.i18n", "afanes.models", "afanes.core")
        offenders: list[str] = []
        for path in _python_files(I18N_ROOT):
            offenders.extend(
                f"{path.name}: {module}" for module in _first_party_imports(path) if not module.startswith(allowed)
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
        assert "afanes.core.vault.service" not in _first_party_imports(path)

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
    def test_cli_does_not_import_ui_or_the_toolkit(self) -> None:
        offenders: list[str] = []
        for path in _python_files(CLI_ROOT):
            offenders.extend(
                f"{path.name}: {module}" for module in _first_party_imports(path) if module.startswith("afanes.ui")
            )
            offenders.extend(
                f"{path.name}: {module}"
                for module, level in _imports(path)
                if level == 0 and (module == "flet" or module.startswith("flet."))
            )
        assert offenders == []

    def test_ui_does_not_import_cli(self) -> None:
        offenders: list[str] = []
        for path in _python_files(UI_ROOT):
            offenders.extend(
                f"{path.name}: {module}" for module in _first_party_imports(path) if module.startswith("afanes.cli")
            )
        assert offenders == []

    def test_state_does_not_import_views_or_components(self) -> None:
        forbidden = ("afanes.ui.views", "afanes.ui.components")
        offenders: list[str] = []
        for path in _state_paths():
            offenders.extend(
                f"{path.name}: {module}" for module in _first_party_imports(path) if module.startswith(forbidden)
            )
        assert offenders == []

    def test_theme_and_english_catalog_are_import_leaves(self) -> None:
        paths = (UI_ROOT / "theme.py", I18N_ROOT / "ui" / "en.py")
        offenders: list[str] = [f"{path.name}: {module}" for path in paths for module in _first_party_imports(path)]
        assert offenders == []


class TestDocumentationCitations:
    def test_every_live_section_citation_resolves(self) -> None:
        sections = _numbered_sections((REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        offenders: list[str] = []
        for path in _live_documents():
            offenders.extend(
                _unresolved_citations(
                    path.relative_to(REPO_ROOT).as_posix(),
                    path.read_text(encoding="utf-8"),
                    sections,
                )
            )
        assert offenders == []

    def test_a_missing_section_is_reported(self) -> None:
        sections = _numbered_sections("## 1. One\n\n### 1.1 Detail\n")
        missing = "9.9"
        present = "1.1"
        text = f"See section {missing} and section {present}."

        failures = _unresolved_citations("guide.md", text, sections)

        assert failures == [f"guide.md: section {missing}"]


class TestObjectOwnership:
    def test_temporary_allowlists_are_empty(self) -> None:
        assert TEMPORARY_FUNCTION_ALLOWLIST == {}
        assert frozenset() == TEMPORARY_DUPLICATE_HELPER_ALLOWLIST
        assert frozenset() == TEMPORARY_FIELD_BUDGET_ALLOWLIST

    def test_final_allowlist_is_exact(self) -> None:
        assert {
            "__main__.py": frozenset({"entrypoint"}),
        } == FINAL_FUNCTION_ALLOWLIST

    def test_module_functions_are_owned(self) -> None:
        offenders: list[str] = []
        for path in _python_files(SOURCE_ROOT):
            relative = _relative_source_path(path)
            permitted = set(FINAL_FUNCTION_ALLOWLIST.get(relative, frozenset()))
            permitted.update(TEMPORARY_FUNCTION_ALLOWLIST.get(relative, frozenset()))
            offenders.extend(f"{relative}: {name}" for name in sorted(_module_functions(path) - permitted))
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
        path = UI_ROOT / "state" / "controller.py"
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

    def test_core_classes_respect_the_public_method_budget(self) -> None:
        offenders: list[str] = []
        for path in _python_files(CORE_ROOT):
            relative = path.relative_to(SOURCE_ROOT).as_posix()
            offenders.extend(
                f"{relative}: {name} defines {count} public methods"
                for name, count in _public_methods(path)
                if count > CORE_SERVICE_METHOD_BUDGET
            )
        assert offenders == []

    def test_core_modules_respect_the_line_ceiling(self) -> None:
        offenders = [
            f"{path.relative_to(SOURCE_ROOT).as_posix()}: {len(path.read_text(encoding='utf-8').splitlines())} lines"
            for path in _python_files(CORE_ROOT)
            if len(path.read_text(encoding="utf-8").splitlines()) > CORE_MODULE_LINE_BUDGET
        ]
        assert offenders == []

    def test_vault_does_not_import_its_sibling_services(self) -> None:
        path = CORE_ROOT / "vault" / "service.py"
        assert VAULT_SIBLING_MODULES.isdisjoint(_first_party_imports(path))


class TestLabelOwnership:
    def test_label_keys_have_one_writer(self) -> None:
        offenders: list[str] = []
        for path in _python_files(SOURCE_ROOT):
            relative = _relative_source_path(path)
            if relative in LABEL_OWNER_MODULES:
                continue
            offenders.extend(f"{relative}: {write}" for write in _label_key_writes(path))
        assert offenders == []

    def test_a_label_write_outside_the_owner_is_reported(self, tmp_path: Path) -> None:
        path = tmp_path / "writer.py"
        path.write_text(
            'raw = {}\nraw["status"] = "done"\nraw["owner"] = "Ada"\nraw.pop("date", None)\n',
            encoding="utf-8",
        )

        assert _label_key_writes(path) == [
            "line 2: assignment to 'status'",
            "line 3: assignment to 'owner'",
            "line 4: pop of 'date'",
        ]


class TestTemplateOptionOwnership:
    def test_template_option_helpers_have_one_owner(self) -> None:
        offenders: list[str] = []
        for path in _python_files(SOURCE_ROOT):
            relative = _relative_source_path(path)
            if relative == TEMPLATE_OPTION_OWNER:
                continue
            offenders.extend(
                f"{relative}: {name}" for name in sorted(_defined_functions(path) & TEMPLATE_OPTION_HELPERS)
            )
        assert offenders == []

    def test_a_template_option_helper_outside_the_owner_is_reported(self, tmp_path: Path) -> None:
        path = tmp_path / "view.py"
        path.write_text("def _template_options():\n    return []\n", encoding="utf-8")

        assert _defined_functions(path) & TEMPLATE_OPTION_HELPERS == {"_template_options"}


class TestStateSurface:
    def test_state_classes_respect_their_public_surface_budget(self) -> None:
        offenders: list[str] = []
        for _path, class_name, surface in _state_surfaces():
            budget = APP_STATE_SURFACE_BUDGET if class_name == "AppState" else DOMAIN_CONTROLLER_SURFACE_BUDGET
            if surface > budget:
                offenders.append(f"{class_name} defines {surface} public names (budget {budget})")
        assert offenders == []

    def test_state_classes_with_fields_define_a_command(self) -> None:
        offenders: list[str] = []
        for _path, class_name, fields, commands in _state_shapes():
            if fields and commands == 0:
                offenders.append(f"{class_name} declares state fields but no public command")
        assert offenders == []

    def test_app_state_respects_the_combined_facade_budget(self) -> None:
        path = UI_ROOT / "state" / "controller.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        state_class = next(
            (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AppState"),
            None,
        )
        assert state_class is not None
        public_fields = [
            node.target.id
            for node in state_class.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and not node.target.id.startswith("_")
        ]
        commands = _class_commands(state_class.body)
        assert len(public_fields) + commands <= APP_STATE_SURFACE_BUDGET, [
            *public_fields,
            f"{commands} commands",
        ]
