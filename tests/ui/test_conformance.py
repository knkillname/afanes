"""Conformance gate for the interface standard.

The gate scans ``src/afanes/ui`` and compares every measured violation with the
embedded baseline. A count above its baseline entry is a new violation and
fails; a baseline entry above the measured count is stale and also fails, so the
ledger can only shrink.

Counting is per module. Each view module holds one view class today, so the
module count is a faithful proxy for the per-view count required by the spec.
"""

import ast
import re
from collections.abc import Callable
from pathlib import Path

import afanes.ui.theme

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "afanes" / "ui"
PALETTE_MODULE = "theme.py"
SURFACE_ROLE_COUNT = 3
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
FONT_SUFFIXES = frozenset({".ttf", ".otf", ".ttc", ".woff", ".woff2"})
ICON_SUFFIXES = frozenset({".svg"})
HEX_COLOR = re.compile(r"#(?:[0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b")

BASELINE: dict[str, dict[str, int]] = {
    "color_literals": {},
    "hardcoded_font_sizes": {},
    "numeric_layout_literals": {
        "components/banner.py": 1,
        "components/calendar.py": 16,
        "components/log_tree.py": 4,
        "views/inbox.py": 3,
        "views/page.py": 5,
        "views/processing.py": 10,
        "views/project_body.py": 2,
        "views/projects.py": 2,
        "views/review.py": 1,
        "views/workspace.py": 12,
    },
    "filled_buttons": {
        "app.py": 6,
        "components/role_name.py": 1,
        "components/role_reference.py": 1,
        "views/inbox.py": 4,
        "views/page.py": 12,
        "views/processing.py": 3,
        "views/review.py": 7,
        "views/workspace.py": 3,
    },
    "icon_and_label_buttons": {
        "app.py": 2,
        "views/inbox.py": 3,
        "views/page.py": 15,
        "views/processing.py": 2,
        "views/review.py": 11,
        "views/workspace.py": 4,
    },
    "dense_rows": {
        "components/log_tree.py": 1,
        "views/page.py": 2,
        "views/processing.py": 2,
        "views/project_body.py": 2,
        "views/projects.py": 2,
        "views/workspace.py": 5,
    },
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


def _is_filled_button(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and _is_flet_call(node)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "FilledButton"
    )


def _is_icon_and_label(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call) or not _is_flet_call(node):
        return False
    keywords = {keyword.arg for keyword in node.keywords}
    return "icon" in keywords and bool(keywords & LABEL_KEYWORDS)


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
    if rule == "filled_buttons":
        return _count_modules(root, _is_filled_button)
    if rule == "icon_and_label_buttons":
        return _count_modules(root, _is_icon_and_label)
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
                and node.func.attr in {"Text", "TextSpan", "TextStyle"}
            )
            for keyword in node.keywords:
                if keyword.arg == "font_size" or (text_control and keyword.arg == "size"):
                    total += 1
        if total:
            counts[relative] = total
    return counts


def _actual(root: Path) -> dict[str, dict[str, int]]:
    return {
        "color_literals": _scan_color_literals(root),
        "hardcoded_font_sizes": _scan_font_sizes(root),
        "numeric_layout_literals": _scan_counts(root, "numeric_layout_literals"),
        "filled_buttons": _scan_counts(root, "filled_buttons"),
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
    def test_the_three_surface_roles_resolve_to_distinct_values(self) -> None:
        for theme in (afanes.ui.theme.LIGHT_THEME, afanes.ui.theme.DARK_THEME):
            scheme = theme.color_scheme
            assert scheme is not None
            values = {
                scheme.surface,
                scheme.surface_container,
                scheme.surface_container_lowest,
            }
            assert len(values) == SURFACE_ROLE_COUNT

    def test_the_note_canvas_is_the_brightest_light_surface(self) -> None:
        scheme = afanes.ui.theme.LIGHT_THEME.color_scheme

        assert scheme is not None
        assert scheme.surface is not None
        assert scheme.surface_container is not None
        assert scheme.surface_container_lowest is not None
        assert _luminance(scheme.surface_container_lowest) > _luminance(scheme.surface)
        assert _luminance(scheme.surface) > _luminance(scheme.surface_container)


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
