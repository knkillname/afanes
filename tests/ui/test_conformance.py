"""Conformance gate for the interface standard.

The gate scans ``src/afanes/ui`` and compares every measured violation with the
embedded baseline. A count above its baseline entry is a new violation and
fails; a baseline entry above the measured count is stale and also fails, so the
ledger can only shrink.

Value rules count per module. Button rules count within each class scope, so a
module that holds several dialogs is measured per view rather than as one
undifferentiated module.
"""

import ast
import re
from collections.abc import Callable
from pathlib import Path

import flet as ft

import afanes.ui.theme

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "afanes" / "ui"
PALETTE_MODULE = "theme.py"
SURFACE_ROLE_COUNT = 4
SRGB_LINEAR_THRESHOLD = 0.04045

LAYOUT_KEYWORDS = frozenset(
    {
        "width",
        "height",
        "size",
        "spacing",
        "padding",
        "margin",
        "border_radius",
        "top",
        "bottom",
        "left",
        "right",
        "min_lines",
        "max_lines",
        "radius",
        "gap",
        "indent",
        "alignment",
        "expand",
        "thickness",
    }
)
LABEL_KEYWORDS = frozenset({"content", "text", "label"})
BUTTON_NAMES = frozenset({"FilledButton", "TextButton", "OutlinedButton", "ElevatedButton"})
HEADER_ACTION_KEYS = frozenset({"page-edit-action", "page-done-action", "process-note"})
TEXT_CONTROL_NAMES = frozenset({"Text", "TextSpan", "TextStyle"})
FONT_SUFFIXES = frozenset({".ttf", ".otf", ".ttc", ".woff", ".woff2"})
ICON_SUFFIXES = frozenset({".svg"})
HEX_COLOR = re.compile(r"#(?:[0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b")
OUTLINE_SUFFIXES = ("_OUTLINE", "_OUTLINED")

BASELINE: dict[str, dict[str, int]] = {
    "color_literals": {},
    "hardcoded_font_sizes": {},
    "material_text_roles": {},
    "icon_size_literals": {},
    "filled_icon_glyphs": {},
    "numeric_layout_literals": {
        "components/calendar.py": 16,
        "components/log_tree.py": 4,
        "views/inbox.py": 3,
        "views/page.py": 5,
        "views/processing.py": 10,
        "views/project_body.py": 2,
        "views/projects.py": 2,
        "views/review.py": 1,
        "views/workspace.py": 11,
    },
    "suggested_or_destructive_buttons": {
        "app.py::_Shell": 6,
        "components/role_name.py::RoleNameDialog": 1,
        "components/role_reference.py::RoleReferenceDialog": 1,
        "views/inbox.py::SessionNotice": 1,
        "views/inbox.py::WelcomeView": 2,
        "views/page.py::PageView": 9,
        "views/processing.py::ProcessingView": 3,
        "views/review.py::ReviewView": 7,
        "views/workspace.py::WorkspaceView": 1,
    },
    "icon_and_label_buttons": {},
    "dense_rows": {},
}


def _sources(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if path.name != PALETTE_MODULE)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _module_trees(root: Path) -> list[tuple[str, ast.Module]]:
    return [
        (_relative(path, root), ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        for path in _sources(root)
    ]


def _class_scopes(root: Path) -> list[tuple[str, ast.ClassDef]]:
    scopes: list[tuple[str, ast.ClassDef]] = []
    for relative, tree in _module_trees(root):
        scopes.extend((f"{relative}::{node.name}", node) for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    return scopes


def _is_flet_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "ft"
    )


def _numeric_literals(node: ast.Call) -> list[float]:
    values: list[float] = []
    for keyword in node.keywords:
        value = keyword.value
        if (
            keyword.arg in LAYOUT_KEYWORDS
            and isinstance(value, ast.Constant)
            and isinstance(value.value, int | float)
            and not isinstance(value.value, bool)
        ):
            values.append(value.value)
    return values


def _count_modules(root: Path, measure: Callable[[ast.AST], bool]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relative, tree in _module_trees(root):
        total = sum(1 for node in ast.walk(tree) if measure(node))
        if total:
            counts[relative] = total
    return counts


def _count_scopes(root: Path, measure: Callable[[ast.AST], bool]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, node in _class_scopes(root):
        total = sum(1 for child in ast.walk(node) if measure(child))
        if total:
            counts[key] = total
    return counts


def _has_destructive_style(node: ast.Call) -> bool:
    for keyword in node.keywords:
        if (
            keyword.arg == "style"
            and isinstance(keyword.value, ast.Attribute)
            and keyword.value.attr == "DESTRUCTIVE_BUTTON_STYLE"
        ):
            return True
    return False


def _is_filled_button(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and _is_flet_call(node)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "FilledButton"
    )


def _is_suggested_or_destructive(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and _is_flet_call(node)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in BUTTON_NAMES
        and (_is_filled_button(node) or _has_destructive_style(node))
    )


def _has_icon_and_label(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call) or not _is_flet_call(node):
        return False
    if not isinstance(node.func, ast.Attribute) or node.func.attr not in BUTTON_NAMES:
        return False
    keywords = {keyword.arg for keyword in node.keywords}
    return "icon" in keywords and bool(keywords & LABEL_KEYWORDS)


def _key_of(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    for keyword in node.keywords:
        if keyword.arg == "key" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            return keyword.value.value
    return None


def _is_icon_and_label(node: ast.AST) -> bool:
    return _has_icon_and_label(node) and _key_of(node) not in HEADER_ACTION_KEYS


def _assigned_calls(tree: ast.Module) -> dict[str, ast.Call]:
    assigned: dict[str, ast.Call] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
            and isinstance(node.value, ast.Call)
        ):
            continue
        assigned[target.attr] = node.value
    return assigned


def _module_header_action_keys(tree: ast.Module) -> set[str]:
    assigned = _assigned_calls(tree)
    header = assigned.get("header")
    if header is None:
        return set()
    controls = next((keyword.value for keyword in header.keywords if keyword.arg == "controls"), None)
    if controls is None:
        return set()
    keys: set[str] = set()
    for control in ast.walk(controls):
        if not (
            isinstance(control, ast.Attribute)
            and isinstance(control.value, ast.Name)
            and control.value.id == "self"
            and control.attr in assigned
        ):
            continue
        call = assigned[control.attr]
        if _has_icon_and_label(call):
            key = _key_of(call)
            if key is not None:
                keys.add(key)
    return keys


def _header_action_keys(root: Path) -> set[str]:
    keys: set[str] = set()
    for _relative, tree in _module_trees(root):
        keys.update(_module_header_action_keys(tree))
    return keys


def _is_dense_row(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and _is_flet_call(node)
        and any(
            keyword.arg == "dense" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
            for keyword in node.keywords
        )
    )


def _layout_literal_count(node: ast.AST) -> int:
    return len(_numeric_literals(node)) if isinstance(node, ast.Call) and _is_flet_call(node) else 0


def _scan_counts(root: Path, rule: str) -> dict[str, int]:
    if rule == "numeric_layout_literals":
        return _sum_modules(root, _layout_literal_count)
    if rule == "suggested_or_destructive_buttons":
        return _count_scopes(root, _is_suggested_or_destructive)
    if rule == "icon_and_label_buttons":
        return _count_scopes(root, _is_icon_and_label)
    return _count_modules(root, _is_dense_row)


def _sum_modules(root: Path, measure: Callable[[ast.AST], int]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relative, tree in _module_trees(root):
        total = sum(measure(node) for node in ast.walk(tree))
        if total:
            counts[relative] = total
    return counts


def _scan_color_literals(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relative, tree in _module_trees(root):
        total = 0
        for node in ast.walk(tree):
            hex_literal = (
                isinstance(node, ast.Constant) and isinstance(node.value, str) and bool(HEX_COLOR.search(node.value))
            )
            named_color = (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "Colors"
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "ft"
            )
            if hex_literal or named_color:
                total += 1
        if total:
            counts[relative] = total
    return counts


def _scan_font_sizes(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relative, tree in _module_trees(root):
        total = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            text_control = (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "ft"
                and node.func.attr in TEXT_CONTROL_NAMES
            )
            for keyword in node.keywords:
                if keyword.arg == "font_size" or (text_control and keyword.arg == "size"):
                    total += 1
        if total:
            counts[relative] = total
    return counts


def _scan_material_text_roles(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relative, tree in _module_trees(root):
        total = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            if not isinstance(node.value, ast.Attribute):
                continue
            if not isinstance(node.value.value, ast.Name):
                continue
            if node.value.value.id == "ft" and node.value.attr == "TextThemeStyle":
                total += 1
        if total:
            counts[relative] = total
    return counts


def _scan_icon_size_literals(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relative, tree in _module_trees(root):
        total = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_flet_call(node):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != "Icon":
                continue
            for keyword in node.keywords:
                if (
                    keyword.arg == "size"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, int | float)
                    and not isinstance(keyword.value.value, bool)
                ):
                    total += 1
        if total:
            counts[relative] = total
    return counts


def _scan_filled_icon_glyphs(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relative, tree in _module_trees(root):
        total = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            if not isinstance(node.value, ast.Attribute):
                continue
            if not isinstance(node.value.value, ast.Name):
                continue
            if node.value.value.id != "ft" or node.value.attr != "Icons":
                continue
            name = node.attr
            if name.endswith(OUTLINE_SUFFIXES):
                continue
            if hasattr(ft.Icons, f"{name}_OUTLINED"):
                total += 1
        if total:
            counts[relative] = total
    return counts


def _actual(root: Path) -> dict[str, dict[str, int]]:
    return {
        "color_literals": _scan_color_literals(root),
        "hardcoded_font_sizes": _scan_font_sizes(root),
        "material_text_roles": _scan_material_text_roles(root),
        "icon_size_literals": _scan_icon_size_literals(root),
        "filled_icon_glyphs": _scan_filled_icon_glyphs(root),
        "numeric_layout_literals": _scan_counts(root, "numeric_layout_literals"),
        "suggested_or_destructive_buttons": _scan_counts(root, "suggested_or_destructive_buttons"),
        "icon_and_label_buttons": _scan_counts(root, "icon_and_label_buttons"),
        "dense_rows": _scan_counts(root, "dense_rows"),
    }


def _differences(actual: dict[str, int], baseline: dict[str, int]) -> list[str]:
    findings: list[str] = []
    for path in sorted(set(actual) | set(baseline)):
        measured = actual.get(path, 0)
        allowed = baseline.get(path, 0)
        if measured > allowed:
            findings.append(f"new violation: {path} has {measured}, baseline allows {allowed}")
        elif allowed > measured:
            findings.append(f"stale baseline: {path} allows {allowed}, measured {measured}")
    return findings


def _asset_violations(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in FONT_SUFFIXES:
            findings.append(f"font asset: {_relative(path, root)}")
        elif suffix in ICON_SUFFIXES:
            findings.append(f"icon asset: {_relative(path, root)}")
    return findings


def _luminance(color: str) -> float:
    digits = color.lstrip("#")

    def channel(value: int) -> float:
        scaled = value / 255
        return scaled / 12.92 if scaled <= SRGB_LINEAR_THRESHOLD else ((scaled + 0.055) / 1.055) ** 2.4

    red, green, blue = (int(digits[index : index + 2], 16) for index in (0, 2, 4))
    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)


class TestConformanceRatchet:
    def test_the_tree_matches_the_baseline(self) -> None:
        findings: list[str] = []
        for rule, counts in _actual(SOURCE_ROOT).items():
            findings.extend(f"{rule}: {finding}" for finding in _differences(counts, BASELINE[rule]))

        assert findings == []


class TestBaselineDirections:
    def test_a_count_above_the_baseline_fails(self) -> None:
        findings = _differences({"views/page.py": 3}, {"views/page.py": 2})

        assert findings == ["new violation: views/page.py has 3, baseline allows 2"]

    def test_a_count_below_the_baseline_is_stale(self) -> None:
        findings = _differences({"views/page.py": 1}, {"views/page.py": 2})

        assert findings == ["stale baseline: views/page.py allows 2, measured 1"]

    def test_a_file_outside_the_baseline_is_a_new_violation(self) -> None:
        findings = _differences({"views/new.py": 1}, {})

        assert findings == ["new violation: views/new.py has 1, baseline allows 0"]


class TestAssetGate:
    def test_no_font_or_icon_asset_ships(self) -> None:
        assert _asset_violations(SOURCE_ROOT) == []

    def test_asset_check_detects_shipped_files(self, tmp_path: Path) -> None:
        (tmp_path / "icons").mkdir()
        (tmp_path / "icons" / "open.svg").write_text("<svg />", encoding="utf-8")
        (tmp_path / "Custom.ttf").write_bytes(b"\x00")

        findings = _asset_violations(tmp_path)

        assert findings == ["font asset: Custom.ttf", "icon asset: icons/open.svg"]


class TestSurfaceDepth:
    def test_the_four_surface_roles_resolve_to_distinct_values(self) -> None:
        for theme in (afanes.ui.theme.LIGHT_THEME, afanes.ui.theme.DARK_THEME):
            scheme = theme.color_scheme
            assert scheme is not None
            values = {
                scheme.surface,
                scheme.surface_container,
                scheme.surface_container_low,
                scheme.surface_container_lowest,
            }
            assert len(values) == SURFACE_ROLE_COUNT

    def test_light_depth_raises_the_note_canvas(self) -> None:
        scheme = afanes.ui.theme.LIGHT_THEME.color_scheme

        assert scheme is not None
        assert scheme.surface is not None
        assert scheme.surface_container is not None
        assert scheme.surface_container_lowest is not None
        assert _luminance(scheme.surface_container_lowest) > _luminance(scheme.surface)
        assert _luminance(scheme.surface) > _luminance(scheme.surface_container)

    def test_dark_depth_recesses_the_note_canvas(self) -> None:
        scheme = afanes.ui.theme.DARK_THEME.color_scheme

        assert scheme is not None
        assert scheme.surface is not None
        assert scheme.surface_container is not None
        assert scheme.surface_container_lowest is not None
        assert _luminance(scheme.surface_container_lowest) < _luminance(scheme.surface)
        assert _luminance(scheme.surface) < _luminance(scheme.surface_container)


class TestHardcodedFontSizes:
    def test_no_font_size_is_set_outside_the_theme(self) -> None:
        assert _scan_font_sizes(SOURCE_ROOT) == {}

    def test_a_hardcoded_size_is_detected(self, tmp_path: Path) -> None:
        (tmp_path / "view.py").write_text(
            "import flet as ft\n\nft.Text('x', style=ft.TextStyle(size=13))\n",
            encoding="utf-8",
        )

        assert _scan_font_sizes(tmp_path) == {"view.py": 1}

    def test_a_font_size_keyword_is_detected(self, tmp_path: Path) -> None:
        (tmp_path / "view.py").write_text(
            "import flet as ft\n\nft.Text('x', font_size=13)\n",
            encoding="utf-8",
        )

        assert _scan_font_sizes(tmp_path) == {"view.py": 1}


class TestMaterialTextRoles:
    def test_no_material_text_role_is_used(self) -> None:
        assert _scan_material_text_roles(SOURCE_ROOT) == {}

    def test_a_material_role_is_detected(self, tmp_path: Path) -> None:
        (tmp_path / "view.py").write_text(
            "import flet as ft\n\nft.Text('x', theme_style=ft.TextThemeStyle.BODY_SMALL)\n",
            encoding="utf-8",
        )

        assert _scan_material_text_roles(tmp_path) == {"view.py": 1}


class TestIconStyle:
    def test_every_outlined_variant_is_used(self) -> None:
        assert _scan_filled_icon_glyphs(SOURCE_ROOT) == {}

    def test_a_filled_icon_is_detected(self, tmp_path: Path) -> None:
        (tmp_path / "view.py").write_text(
            "import flet as ft\n\nft.Icon(ft.Icons.ADD)\n",
            encoding="utf-8",
        )

        assert _scan_filled_icon_glyphs(tmp_path) == {"view.py": 1}

    def test_an_outlined_icon_is_allowed(self, tmp_path: Path) -> None:
        (tmp_path / "view.py").write_text(
            "import flet as ft\n\nft.Icon(ft.Icons.ADD_OUTLINED)\n",
            encoding="utf-8",
        )

        assert _scan_filled_icon_glyphs(tmp_path) == {}

    def test_no_icon_size_literal_is_used(self) -> None:
        assert _scan_icon_size_literals(SOURCE_ROOT) == {}

    def test_an_icon_size_literal_is_detected(self, tmp_path: Path) -> None:
        (tmp_path / "view.py").write_text(
            "import flet as ft\n\nft.Icon(ft.Icons.ADD_OUTLINED, size=18)\n",
            encoding="utf-8",
        )

        assert _scan_icon_size_literals(tmp_path) == {"view.py": 1}


class TestViewScope:
    def test_button_counts_are_scoped_to_the_view_class(self, tmp_path: Path) -> None:
        (tmp_path / "view.py").write_text(
            "import flet as ft\n\n"
            "class FirstView:\n"
            "    def build(self):\n"
            "        return ft.FilledButton('One')\n\n"
            "class SecondView:\n"
            "    def build(self):\n"
            "        return ft.FilledButton('Two')\n",
            encoding="utf-8",
        )

        assert _count_scopes(tmp_path, _is_suggested_or_destructive) == {
            "view.py::FirstView": 1,
            "view.py::SecondView": 1,
        }


class TestHeaderActions:
    def test_a_header_action_is_not_counted(self, tmp_path: Path) -> None:
        (tmp_path / "view.py").write_text(
            "import flet as ft\n\n"
            "class View:\n"
            "    def __init__(self):\n"
            "        self.edit = ft.FilledButton(\n"
            "            content='Edit', icon=ft.Icons.EDIT_OUTLINED, key='page-edit-action'\n"
            "        )\n",
            encoding="utf-8",
        )

        assert _count_scopes(tmp_path, _is_icon_and_label) == {}

    def test_a_non_header_action_is_counted(self, tmp_path: Path) -> None:
        (tmp_path / "view.py").write_text(
            "import flet as ft\n\n"
            "class View:\n"
            "    def __init__(self):\n"
            "        self.save = ft.FilledButton(\n"
            "            content='Save', icon=ft.Icons.CHECK_OUTLINED, key='other-action'\n"
            "        )\n",
            encoding="utf-8",
        )

        assert _count_scopes(tmp_path, _is_icon_and_label) == {"view.py::View": 1}

    def test_a_header_action_without_a_key_is_counted(self, tmp_path: Path) -> None:
        (tmp_path / "view.py").write_text(
            "import flet as ft\n\n"
            "class View:\n"
            "    def __init__(self):\n"
            "        self.edit = ft.FilledButton(content='Edit', icon=ft.Icons.EDIT_OUTLINED)\n",
            encoding="utf-8",
        )

        assert _count_scopes(tmp_path, _is_icon_and_label) == {"view.py::View": 1}

    def test_the_allowlist_matches_the_page_toolbar(self) -> None:
        assert _header_action_keys(SOURCE_ROOT) == HEADER_ACTION_KEYS

    def test_a_missing_header_key_breaks_the_allowlist(self, tmp_path: Path) -> None:
        (tmp_path / "view.py").write_text(
            "import flet as ft\n\n"
            "class View:\n"
            "    def __init__(self):\n"
            "        self.edit = ft.FilledButton(content='Edit', icon=ft.Icons.EDIT_OUTLINED)\n"
            "        self.header = ft.Row(controls=[self.edit])\n",
            encoding="utf-8",
        )

        assert _header_action_keys(tmp_path) == set()

    def test_an_unlisted_header_key_is_reported(self, tmp_path: Path) -> None:
        (tmp_path / "view.py").write_text(
            "import flet as ft\n\n"
            "class View:\n"
            "    def __init__(self):\n"
            "        self.edit = ft.FilledButton(\n"
            "            content='Edit', icon=ft.Icons.EDIT_OUTLINED, key='other-action'\n"
            "        )\n"
            "        self.header = ft.Row(controls=[self.edit])\n",
            encoding="utf-8",
        )

        assert _header_action_keys(tmp_path) == {"other-action"}
