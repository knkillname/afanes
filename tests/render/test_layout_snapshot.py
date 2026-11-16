"""Tests for the rendered layout snapshot comparator."""

import copy
import typing

from tests.render import layout_snapshot

WINDOW = {"width": 1024, "height": 600}


def _report(
    *,
    low_height: float = 48,
    high_height: float = 96,
) -> dict[str, typing.Any]:
    return {
        "schema": 1,
        "platform": "linux",
        "window": WINDOW,
        "views": {
            "inbox": {
                "markers": ["browser-list"],
                "low": {
                    "browser-list": {"width": 320, "height": 400},
                    "workspace-capture-field": {"width": 320, "height": low_height},
                    "workspace-capture-button": {"width": 96, "height": low_height},
                },
                "high": {
                    "browser-list": {"width": 320, "height": 400},
                    "workspace-capture-field": {"width": 320, "height": high_height},
                    "workspace-capture-button": {"width": 96, "height": high_height},
                },
                "text_keys": ["workspace-capture-field", "workspace-capture-button"],
            }
        },
    }


def test_a_matching_snapshot_passes() -> None:
    report = _report()

    assert layout_snapshot.capture_violations(report) == []
    assert layout_snapshot.growth_violations(report) == []
    assert layout_snapshot.snapshot_violations(report, copy.deepcopy(report)) == []


def test_a_non_growing_text_control_fails() -> None:
    report = _report(high_height=48)

    violations = layout_snapshot.growth_violations(report)

    assert violations == [
        "inbox: text control 'workspace-capture-field' did not grow (48.0 -> 48.0)",
        "inbox: text control 'workspace-capture-button' did not grow (48.0 -> 48.0)",
    ]


def test_a_missing_view_fails() -> None:
    report = _report()
    snapshot = copy.deepcopy(report)
    snapshot["views"] = typing.cast("dict[str, typing.Any]", {})

    assert layout_snapshot.snapshot_violations(report, snapshot) == ["inbox: view is not in the committed snapshot"]


def test_a_missing_view_marker_fails() -> None:
    report = _report()
    report["views"]["inbox"]["high"] = {}

    violations = layout_snapshot.capture_violations(report)

    assert violations == ["inbox: missing view marker 'browser-list' at 200%"]


def test_geometry_within_tolerance_passes() -> None:
    report = _report()
    snapshot = copy.deepcopy(report)
    snapshot["views"]["inbox"]["high"]["browser-list"]["height"] = 401.5

    assert layout_snapshot.snapshot_violations(report, snapshot) == []


def test_geometry_outside_tolerance_fails() -> None:
    report = _report()
    snapshot = copy.deepcopy(report)
    snapshot["views"]["inbox"]["high"]["browser-list"]["height"] = 410

    violations = layout_snapshot.snapshot_violations(report, snapshot)

    assert violations == ["inbox:high:browser-list: geometry (320.0, 400.0) differs from (320.0, 410.0)"]


def test_a_missing_control_fails() -> None:
    report = _report()
    snapshot = copy.deepcopy(report)
    del snapshot["views"]["inbox"]["high"]["workspace-capture-button"]

    violations = layout_snapshot.snapshot_violations(report, snapshot)

    assert violations == ["inbox:high: control 'workspace-capture-button' is not in the committed snapshot"]
