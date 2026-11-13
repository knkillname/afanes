"""Helpers for inspecting a built Flet control tree in UI tests."""

import flet as ft

import afanes.ui.theme

_CHILD_ATTRIBUTES = (
    "controls",
    "content",
    "leading",
    "title",
    "subtitle",
    "trailing",
    "actions",
    "items",
)


def _children(control: ft.Control) -> list[ft.Control]:
    """Return the direct child controls of one control."""
    children: list[ft.Control] = []
    for name in _CHILD_ATTRIBUTES:
        value = getattr(control, name, None)
        if isinstance(value, ft.Control):
            children.append(value)
        elif isinstance(value, list):
            children.extend(item for item in value if isinstance(item, ft.Control))
    return children


def visible_controls(root: ft.Control) -> list[ft.Control]:
    """Return the root and every descendant that is visible with it."""
    result: list[ft.Control] = []
    stack: list[tuple[ft.Control, bool]] = [(root, True)]
    while stack:
        control, parent_visible = stack.pop()
        visible = parent_visible and getattr(control, "visible", True) is not False
        if visible:
            result.append(control)
        stack.extend((child, visible) for child in _children(control))
    return result


def emphasis_controls(root: ft.Control) -> list[ft.Control]:
    """Return the visible controls using a suggested or destructive style."""
    return [control for control in visible_controls(root) if _is_emphasis(control)]


def _is_emphasis(control: ft.Control) -> bool:
    """Return whether one control uses the suggested or destructive fill."""
    if isinstance(control, ft.FilledButton):
        return True
    style = getattr(control, "style", None)
    return isinstance(style, ft.ButtonStyle) and style.bgcolor == afanes.ui.theme.DESTRUCTIVE
