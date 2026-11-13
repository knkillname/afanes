# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Recovery from stale toolkit freeze markers on an owned control tree.

Flet 1.1.x can mark an imperative control as immutable while reconciling a
keyed update or while a dialog is open. The marker then makes the next
assignment raise ``RuntimeError: Frozen controls cannot be updated.`` A view
owns every control under its root, so a marker there is stale; clearing it is
safe and keeps the interaction responsive.
"""

import dataclasses

import flet as ft


class FrozenControlRecovery:
    """Clear stale ``_frozen`` markers under one owned control tree."""

    @classmethod
    def clear(cls, root: ft.Control) -> None:
        """Clear freeze markers on a root and every descendant.

        Parameters
        ----------
        root : flet.Control
            Top control owned by the calling view.

        Notes
        -----
        Controls outside the root are never visited, so a marker owned by another
        view or by an open dialog is left untouched.
        """
        cls._clear(root, set())

    @classmethod
    def _clear(cls, control: ft.Control, visited: set[int]) -> None:
        """Clear markers on one control and recurse into its fields."""
        if id(control) in visited:
            return
        visited.add(id(control))
        if hasattr(control, "_frozen"):
            object.__delattr__(control, "_frozen")
        for child in cls._control_children(control):
            cls._clear(child, visited)

    @staticmethod
    def _control_children(control: ft.Control) -> list[ft.Control]:
        """Return the direct controls held by one control's fields."""
        if not dataclasses.is_dataclass(control):
            return []
        children: list[ft.Control] = []
        for field in dataclasses.fields(control):
            children.extend(FrozenControlRecovery._controls_in(getattr(control, field.name, None)))
        return children

    @staticmethod
    def _controls_in(value: object) -> list[ft.Control]:
        """Return the controls held directly in one field value."""
        if isinstance(value, ft.Control):
            return [value]
        if isinstance(value, (list, tuple)):
            return [item for item in value if isinstance(item, ft.Control)]
        if isinstance(value, dict):
            return [item for item in value.values() if isinstance(item, ft.Control)]
        return []
