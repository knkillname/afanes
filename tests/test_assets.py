"""Tests for the bundled application identity assets."""

import re
from collections.abc import Callable
from pathlib import Path
from xml.etree import ElementTree as ET

ASSET_ROOT = Path(__file__).resolve().parents[1] / "src" / "assets"
ICON_PATH = ASSET_ROOT / "icon.svg"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
FORBIDDEN_ELEMENTS = frozenset({"text", "tspan", "textPath", "script", "image", "foreignObject"})
EXTERNAL_SCHEMES = ("http://", "https://", "//", "data:")
REFERENCE_ATTRIBUTES = frozenset({"href", "src"})
VIEW_BOX_PARTS = 4
SAFE_MIN = 12.0
SAFE_MAX = 116.0
GRID_STEP = 2.0
MIN_DETAIL_CONTRAST = 3.0
LUMINANCE_THRESHOLD = 0.04045
SHORT_HEX_LENGTH = 4
LONG_HEX_LENGTH = 7
COLOR_ATTRIBUTES = ("fill", "stroke", "stop-color")
NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
PALETTE_COLORS = frozenset(
    {
        "#99c1f1",
        "#62a0ea",
        "#3584e4",
        "#1c71d8",
        "#1a5fb4",
        "#8ff0a4",
        "#57e389",
        "#33d17a",
        "#2ec27e",
        "#26a269",
        "#f9f06b",
        "#f8e45c",
        "#f6d32d",
        "#f5c211",
        "#e5a50a",
        "#ffbe6f",
        "#ffa348",
        "#ff7800",
        "#e66100",
        "#c64600",
        "#f66151",
        "#ed333b",
        "#e01b24",
        "#c01c28",
        "#a51d2d",
        "#dc8add",
        "#c061cb",
        "#9141ac",
        "#813d9c",
        "#613583",
        "#cdab8f",
        "#b5835a",
        "#986a44",
        "#865e3c",
        "#63452c",
        "#ffffff",
        "#f6f5f4",
        "#deddda",
        "#c0bfbc",
        "#9a9996",
        "#77767b",
        "#5e5c64",
        "#3d3846",
        "#241f31",
        "#000000",
    }
)


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1]


def _attribute_violations(element: ET.Element) -> list[str]:
    violations: list[str] = []
    for name, value in element.attrib.items():
        local = _local_name(name)
        if local in REFERENCE_ATTRIBUTES and not value.startswith("#"):
            violations.append(f"external reference {value!r}")
        if any(scheme in value for scheme in EXTERNAL_SCHEMES):
            violations.append(f"external data {value!r}")
    return violations


def svg_violations(source: str) -> list[str]:
    """Return self-containment and scalability violations in one SVG source.

    Parameters
    ----------
    source : str
        SVG document to inspect.

    Returns
    -------
    list[str]
        Violation descriptions, empty when the icon is self-contained.
    """
    if "<!DOCTYPE" in source or "<!ENTITY" in source:
        return ["external document type or entity declaration"]
    try:
        root = ET.fromstring(source)  # noqa: S314 - the source is a tracked project asset
    except ET.ParseError as error:
        return [f"invalid SVG: {error}"]
    violations: list[str] = []
    if _local_name(root.tag) != "svg" or root.tag not in ("svg", f"{{{SVG_NAMESPACE}}}svg"):
        violations.append(f"root element is not SVG: {root.tag!r}")
    view_box = root.get("viewBox")
    if view_box is None:
        violations.append("missing viewBox")
    else:
        parts = view_box.replace(",", " ").split()
        if len(parts) != VIEW_BOX_PARTS or any(
            not part.replace(".", "", 1).replace("-", "", 1).isdigit() for part in parts
        ):
            violations.append(f"invalid viewBox {view_box!r}")
    for element in root.iter():
        local = _local_name(element.tag)
        if local in FORBIDDEN_ELEMENTS:
            violations.append(f"forbidden element {local!r}")
        violations.extend(f"{local}: {violation}" for violation in _attribute_violations(element))
    return violations


def _element_label(element: ET.Element) -> str:
    local = _local_name(element.tag)
    identifier = element.get("id")
    return f"{local} {identifier}" if identifier else local


def _numbers(value: str) -> list[float]:
    return [float(match) for match in NUMBER_PATTERN.findall(value)]


def _number_violations(label: str, values: list[float]) -> list[str]:
    violations: list[str] = []
    for value in values:
        if value % GRID_STEP != 0:
            violations.append(f"{label}: {value:g} is not on the 2 px grid")
        if value < SAFE_MIN or value > SAFE_MAX:
            violations.append(f"{label}: {value:g} is outside the 12..116 safe area")
    return violations


def _rect_violations(element: ET.Element) -> list[str]:
    x = float(element.get("x", "0"))
    y = float(element.get("y", "0"))
    width = float(element.get("width", "0"))
    height = float(element.get("height", "0"))
    return _number_violations(_element_label(element), [x, y, x + width, y + height])


def _path_violations(element: ET.Element) -> list[str]:
    return _number_violations(_element_label(element), _numbers(element.get("d", "")))


def _polygon_violations(element: ET.Element) -> list[str]:
    return _number_violations(_element_label(element), _numbers(element.get("points", "")))


def _line_violations(element: ET.Element) -> list[str]:
    values = [float(element.get(name, "0")) for name in ("x1", "y1", "x2", "y2")]
    return _number_violations(_element_label(element), values)


def _circle_violations(element: ET.Element) -> list[str]:
    cx = float(element.get("cx", "0"))
    cy = float(element.get("cy", "0"))
    radius = float(element.get("r", "0"))
    return _number_violations(
        _element_label(element),
        [cx - radius, cx + radius, cy - radius, cy + radius],
    )


GEOMETRY_HANDLERS: dict[str, Callable[[ET.Element], list[str]]] = {
    "rect": _rect_violations,
    "path": _path_violations,
    "polygon": _polygon_violations,
    "line": _line_violations,
    "circle": _circle_violations,
}


def _geometry_violations(root: ET.Element) -> list[str]:
    violations: list[str] = []
    for element in root.iter():
        handler = GEOMETRY_HANDLERS.get(_local_name(element.tag))
        if handler is not None:
            violations.extend(handler(element))
    return violations


def _normalize_color(value: str) -> str | None:
    normalized = value.strip().lower()
    if normalized in ("none", "transparent"):
        return normalized
    if normalized.startswith("#") and len(normalized) == SHORT_HEX_LENGTH:
        normalized = "#" + "".join(character * 2 for character in normalized[1:])
    if (
        normalized.startswith("#")
        and len(normalized) == LONG_HEX_LENGTH
        and all(character in "0123456789abcdef" for character in normalized[1:])
    ):
        return normalized
    return None


def _color_violations(root: ET.Element) -> list[str]:
    violations: list[str] = []
    for element in root.iter():
        label = _element_label(element)
        for attribute in COLOR_ATTRIBUTES:
            value = element.get(attribute)
            if value is None:
                continue
            normalized = _normalize_color(value)
            if normalized is None:
                violations.append(f"{label}: color {value!r} is not a hex color")
            elif normalized not in ("none", "transparent") and normalized not in PALETTE_COLORS:
                violations.append(f"{label}: color {value!r} is not in the GNOME palette")
    return violations


def _element_by_id(root: ET.Element, identifier: str) -> ET.Element | None:
    for element in root.iter():
        if element.get("id") == identifier:
            return element
    return None


def _color_value(element: ET.Element, attribute: str) -> str | None:
    value = element.get(attribute)
    if value is None:
        return None
    normalized = _normalize_color(value)
    if normalized is None or normalized in ("none", "transparent"):
        return None
    return normalized


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= LUMINANCE_THRESHOLD else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def _canvas_violations(root: ET.Element) -> list[str]:
    view_box = " ".join((root.get("viewBox") or "").replace(",", " ").split())
    if view_box != "0 0 128 128":
        return [f"viewBox is {view_box!r}, expected '0 0 128 128'"]
    return []


def _depth_violations(root: ET.Element) -> list[str]:
    top = _element_by_id(root, "top")
    front = _element_by_id(root, "front")
    if top is None or front is None:
        return ["missing top or front element"]
    top_color = _color_value(top, "fill")
    front_color = _color_value(front, "fill")
    if top_color is None or front_color is None:
        return ["top or front element has no palette fill"]
    if _relative_luminance(front_color) >= _relative_luminance(top_color):
        return ["front profile is not darker than the top surface"]
    return []


def _contrast_violations(root: ET.Element) -> list[str]:
    page = _element_by_id(root, "page")
    fold = _element_by_id(root, "fold")
    check = _element_by_id(root, "check")
    if page is None or fold is None or check is None:
        return ["missing page, fold, or check element"]
    page_color = _color_value(page, "fill")
    fold_color = _color_value(fold, "fill")
    check_color = _color_value(check, "stroke")
    if page_color is None or fold_color is None or check_color is None:
        return ["page, fold, or check has no palette color"]
    violations: list[str] = []
    for name, color in (("fold", fold_color), ("check", check_color)):
        ratio = _contrast_ratio(color, page_color)
        if ratio < MIN_DETAIL_CONTRAST:
            violations.append(f"{name} contrast {ratio:.2f}:1 is below 3:1")
    return violations


def icon_violations(source: str) -> list[str]:
    """Return every HIG app-icon contract violation in one SVG source.

    Parameters
    ----------
    source : str
        SVG document to inspect.

    Returns
    -------
    list[str]
        Violation descriptions, empty when the icon meets the contract.
    """
    violations = svg_violations(source)
    if violations:
        return violations
    root = ET.fromstring(source)  # noqa: S314 - the source is a tracked project asset
    violations.extend(_canvas_violations(root))
    violations.extend(_geometry_violations(root))
    violations.extend(_color_violations(root))
    violations.extend(_depth_violations(root))
    violations.extend(_contrast_violations(root))
    return violations


class TestApplicationIcon:
    def test_the_shipped_icon_is_self_contained(self) -> None:
        assert ICON_PATH.is_file()
        assert svg_violations(ICON_PATH.read_text(encoding="utf-8")) == []

    def test_the_shipped_icon_meets_the_hig_contract(self) -> None:
        assert icon_violations(ICON_PATH.read_text(encoding="utf-8")) == []

    def test_an_external_reference_fails_the_gate(self) -> None:
        source = f'<svg xmlns="{SVG_NAMESPACE}" viewBox="0 0 16 16"><use href="https://example.test/icon.svg"/></svg>'

        assert any("external reference" in finding for finding in svg_violations(source))

    def test_an_embedded_raster_fails_the_gate(self) -> None:
        source = f'<svg xmlns="{SVG_NAMESPACE}" viewBox="0 0 16 16"><image href="#pixels"/></svg>'

        assert svg_violations(source) == ["forbidden element 'image'"]

    def test_missing_scalable_geometry_fails_the_gate(self) -> None:
        source = f'<svg xmlns="{SVG_NAMESPACE}"><rect width="16" height="16"/></svg>'

        assert svg_violations(source) == ["missing viewBox"]

    def test_text_content_fails_the_gate(self) -> None:
        source = f'<svg xmlns="{SVG_NAMESPACE}" viewBox="0 0 16 16"><text>Afanes</text></svg>'

        assert svg_violations(source) == ["forbidden element 'text'"]

    def test_the_icon_sits_in_the_flet_assets_directory(self) -> None:
        assert ICON_PATH.parent == ASSET_ROOT

    def test_a_wrong_canvas_fails_the_gate(self) -> None:
        source = ICON_PATH.read_text(encoding="utf-8").replace('viewBox="0 0 128 128"', 'viewBox="0 0 256 256"')

        assert any("viewBox" in finding for finding in icon_violations(source))

    def test_a_full_bleed_tile_fails_the_safe_area(self) -> None:
        source = (
            f'<svg xmlns="{SVG_NAMESPACE}" viewBox="0 0 128 128">'
            '<rect id="top" x="0" y="0" width="128" height="128" fill="#1C71D8"/>'
            "</svg>"
        )

        assert any("safe area" in finding for finding in icon_violations(source))

    def test_an_odd_coordinate_fails_the_grid(self) -> None:
        source = ICON_PATH.read_text(encoding="utf-8").replace('x="12"', 'x="13"')

        assert any("2 px grid" in finding for finding in icon_violations(source))

    def test_a_non_palette_color_fails_the_gate(self) -> None:
        source = ICON_PATH.read_text(encoding="utf-8").replace("#1C71D8", "#123456")

        assert any("GNOME palette" in finding for finding in icon_violations(source))

    def test_a_too_light_fold_fails_the_contrast(self) -> None:
        source = ICON_PATH.read_text(encoding="utf-8").replace("#3584E4", "#FFFFFF")

        assert any("fold contrast" in finding for finding in icon_violations(source))

    def test_a_front_that_is_not_darker_fails_the_depth(self) -> None:
        source = ICON_PATH.read_text(encoding="utf-8").replace("#1A5FB4", "#1C71D8")

        assert any("front profile" in finding for finding in icon_violations(source))
