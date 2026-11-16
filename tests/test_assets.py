"""Tests for the bundled application identity assets."""

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


class TestApplicationIcon:
    def test_the_shipped_icon_is_self_contained(self) -> None:
        assert ICON_PATH.is_file()
        assert svg_violations(ICON_PATH.read_text(encoding="utf-8")) == []

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
