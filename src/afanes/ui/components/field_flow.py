# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Adaptive multi-column flow for label controls.

The component owns a column of flex rows and distributes visible controls over
the available width. Every visible control expands inside its row, so the
fields stretch to the pane instead of leaving a gutter.
"""

from collections.abc import Sequence

import flet as ft

import afanes.ui.theme


class FieldFlow:
    """Responsive flow that shares the pane width between visible fields.

    Parameters
    ----------
    controls : Sequence[flet.Control]
        Label controls in display order. Visibility is read from each control
        on every layout pass.

    Attributes
    ----------
    controls : list[flet.Control]
        Label controls in their configured display order, including hidden
        controls.
    column : flet.Column
        Column that hosts the computed rows. Each row holds one visible run.
    """

    def __init__(self, controls: Sequence[ft.Control]) -> None:
        """Build the row container for the supplied controls.

        Parameters
        ----------
        controls : Sequence[flet.Control]
            Label controls in display order.
        """
        self.controls = list(controls)
        self.column = ft.Column(
            controls=[],
            spacing=afanes.ui.theme.ITEM_GAP,
        )

    def layout(self, width: float) -> None:
        """Rebuild the rows from the available width.

        Parameters
        ----------
        width : float
            Width available to the flow in logical pixels.

        Notes
        -----
        A non-positive width leaves the current rows untouched. Hidden
        controls are left out, and every visible control expands to fill its
        share of the row.
        """
        if width <= 0:
            return
        visible = [control for control in self.controls if control.visible]
        if not visible:
            self.column.controls = []
            return
        gap = afanes.ui.theme.ITEM_GAP
        capacity = int((width + gap) // (afanes.ui.theme.FIELD_MIN_WIDTH + gap))
        capacity = max(1, min(capacity, len(visible)))
        for control in visible:
            control.expand = True
        self.column.controls = [
            ft.Row(
                controls=visible[start : start + capacity],
                spacing=afanes.ui.theme.ITEM_GAP,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
            for start in range(0, len(visible), capacity)
        ]
