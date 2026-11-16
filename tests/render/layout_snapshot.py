"""Compare rendered control geometry between 100% and 200% text.

The snapshot is text, never an image. Capture data holds keyed control geometry
for every primary view at both scales, the marker keys that identify a rendered
view, and the keys that carry text and must grow with the text scale.
"""

import math

TOLERANCE = 2.0
GROWTH_EPSILON = 0.5

type Geometry = dict[str, float]
type ViewCapture = dict[str, object]
type Report = dict[str, object]
type Snapshot = dict[str, object]


def _views(report: Report) -> dict[str, ViewCapture]:
    views = report.get("views")
    return views if isinstance(views, dict) else {}


def _snapshot_views(snapshot: Snapshot) -> dict[str, ViewCapture]:
    views = snapshot.get("views")
    return views if isinstance(views, dict) else {}


def _geometry(value: object) -> tuple[float, float] | None:
    if not isinstance(value, dict):
        return None
    width = value.get("width")
    height = value.get("height")
    if not isinstance(width, int | float) or not isinstance(height, int | float):
        return None
    return float(width), float(height)


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _controls(view: ViewCapture, scale: str) -> dict[str, Geometry]:
    controls = view.get(scale)
    return controls if isinstance(controls, dict) else {}


def capture_violations(report: Report) -> list[str]:
    """Return views that did not render or whose markers collapsed."""
    violations: list[str] = []
    views = _views(report)
    if not views:
        return ["no primary view was captured"]
    for name, view in views.items():
        markers = _strings(view.get("markers"))
        low = _controls(view, "low")
        high = _controls(view, "high")
        for marker in markers:
            for scale, controls in (("100%", low), ("200%", high)):
                geometry = _geometry(controls.get(marker))
                if geometry is None:
                    violations.append(f"{name}: missing view marker {marker!r} at {scale}")
                elif geometry[0] <= 0 or geometry[1] <= 0:
                    violations.append(f"{name}: view marker {marker!r} collapsed at {scale}")
    return violations


def growth_violations(report: Report) -> list[str]:
    """Return text-bearing controls that did not grow at 200% text."""
    violations: list[str] = []
    for name, view in _views(report).items():
        low = _controls(view, "low")
        high = _controls(view, "high")
        for key in _strings(view.get("text_keys")):
            low_geometry = _geometry(low.get(key))
            high_geometry = _geometry(high.get(key))
            if low_geometry is None or high_geometry is None:
                violations.append(f"{name}: text control {key!r} has no geometry at both scales")
                continue
            if high_geometry[1] <= low_geometry[1] + GROWTH_EPSILON:
                violations.append(
                    f"{name}: text control {key!r} did not grow ({low_geometry[1]:.1f} -> {high_geometry[1]:.1f})"
                )
    return violations


def snapshot_violations(
    report: Report,
    snapshot: Snapshot,
    *,
    tolerance: float = TOLERANCE,
) -> list[str]:
    """Return missing views, missing controls, and geometry outside tolerance."""
    violations: list[str] = []
    current = _views(report)
    expected = _snapshot_views(snapshot)
    violations.extend(f"{name}: missing view in the rendered tour" for name in sorted(set(expected) - set(current)))
    violations.extend(f"{name}: view is not in the committed snapshot" for name in sorted(set(current) - set(expected)))
    for name in sorted(set(current) & set(expected)):
        current_view = current[name]
        expected_view = expected[name]
        for scale in ("low", "high"):
            current_controls = _controls(current_view, scale)
            expected_controls = _controls(expected_view, scale)
            violations.extend(
                f"{name}:{scale}: missing control {key!r}"
                for key in sorted(set(expected_controls) - set(current_controls))
            )
            violations.extend(
                f"{name}:{scale}: control {key!r} is not in the committed snapshot"
                for key in sorted(set(current_controls) - set(expected_controls))
            )
            for key in sorted(set(current_controls) & set(expected_controls)):
                current_geometry = _geometry(current_controls.get(key))
                expected_geometry = _geometry(expected_controls.get(key))
                if current_geometry is None or expected_geometry is None:
                    violations.append(f"{name}:{scale}:{key}: unreadable geometry")
                    continue
                drift = max(
                    abs(current_geometry[0] - expected_geometry[0]),
                    abs(current_geometry[1] - expected_geometry[1]),
                )
                if drift > tolerance:
                    violations.append(
                        f"{name}:{scale}:{key}: geometry {current_geometry} differs from {expected_geometry}"
                    )
        if sorted(_strings(current_view.get("text_keys"))) != sorted(_strings(expected_view.get("text_keys"))):
            violations.append(f"{name}: text-key set differs from the committed snapshot")
    return violations


def rounded(value: float) -> float:
    """Round one measured dimension for a stable text snapshot."""
    return round(float(value) * 2) / 2 if math.isfinite(float(value)) else 0.0
