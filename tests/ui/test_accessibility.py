"""Clean-sheet accessible-name gate for interactive Flet controls.

The gate reads the interface source and requires every interactive control to
carry a name from visible content, a tooltip, or an explicit semantics label. A
container with a click handler is pointer-only and fails. The gate has no
baseline and no exception ledger.
"""

import ast
from pathlib import Path

UI_ROOT = Path(__file__).resolve().parents[2] / "src" / "afanes" / "ui"

NAME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "TextButton": ("content",),
    "FilledButton": ("content",),
    "OutlinedButton": ("content",),
    "ElevatedButton": ("content",),
    "IconButton": ("tooltip", "semantics_label"),
    "PopupMenuButton": ("tooltip", "semantics_label"),
    "PopupMenuItem": ("content",),
    "ListTile": ("title",),
    "TextField": ("label", "hint_text"),
    "Dropdown": ("label", "hint_text"),
    "Checkbox": ("label", "semantics_label"),
    "Switch": ("label", "semantics_label"),
}

POINTER_ONLY_CONTAINERS = frozenset({"Container", "GestureDetector"})
TAP_KEYWORDS = frozenset({"on_tap", "on_long_press"})


def _call_name(node: ast.Call) -> str:
    function = node.func
    if isinstance(function, ast.Attribute):
        return function.attr
    if isinstance(function, ast.Name):
        return function.id
    return ""


def _keywords(node: ast.Call) -> set[str]:
    return {keyword.arg for keyword in node.keywords if keyword.arg is not None}


def _has_positional_name(node: ast.Call) -> bool:
    return bool(node.args) and not (
        len(node.args) == 1 and isinstance(node.args[0], ast.Constant) and node.args[0].value is None
    )


def accessibility_violations(source: str, filename: str = "synthetic.py") -> list[str]:
    """Return unnamed interactive controls in one Python source string."""
    tree = ast.parse(source)
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        keywords = _keywords(node)
        if name in POINTER_ONLY_CONTAINERS and "on_click" in keywords:
            violations.append(f"{filename}:{node.lineno}: {name} is pointer-only and has no accessible name")
            continue
        if name == "Semantics" and TAP_KEYWORDS & keywords and "label" not in keywords:
            violations.append(f"{filename}:{node.lineno}: Semantics has no accessible name")
            continue
        names = NAME_KEYWORDS.get(name)
        if names is None:
            continue
        if not any(keyword in keywords for keyword in names) and not _has_positional_name(node):
            violations.append(f"{filename}:{node.lineno}: {name} has no accessible name")
    return violations


def _source_files() -> list[Path]:
    return sorted(UI_ROOT.rglob("*.py"))


def test_every_interactive_control_has_an_accessible_name() -> None:
    violations = [
        violation
        for path in _source_files()
        for violation in accessibility_violations(path.read_text(encoding="utf-8"), path.as_posix())
    ]

    assert violations == []


def test_an_unnamed_icon_action_fails_the_gate() -> None:
    source = "import flet as ft\ncontrol = ft.IconButton(icon=ft.Icons.ADD)\n"

    assert accessibility_violations(source) == ["synthetic.py:2: IconButton has no accessible name"]


def test_a_named_icon_action_passes_the_gate() -> None:
    source = "import flet as ft\ncontrol = ft.IconButton(icon=ft.Icons.ADD, tooltip='Add')\n"

    assert accessibility_violations(source) == []


def test_a_pointer_only_container_fails_the_gate() -> None:
    source = "import flet as ft\ncontrol = ft.Container(on_click=handler)\n"

    assert accessibility_violations(source) == ["synthetic.py:2: Container is pointer-only and has no accessible name"]


def test_the_gate_offers_no_exception_ledger() -> None:
    assert "BASELINE" not in globals()
    assert "ALLOWED_VIOLATIONS" not in globals()
