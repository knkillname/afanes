# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Adaptive multi-column flow for label controls.

The component owns a single responsive row and distributes visible controls
over the available width. Each run of controls fills all twelve virtual
columns, so the fields stretch to the pane instead of leaving a gutter.
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
    row : flet.ResponsiveRow
        Row that hosts the controls and receives the computed column spans.
    """

    def __init__(self, controls: Sequence[ft.Control]) -> None:
        """Build the responsive row for the supplied controls.

        Parameters
        ----------
        controls : Sequence[flet.Control]
            Label controls in display order.
        """
        self._controls = list(controls)
        self.row = ft.ResponsiveRow(
            controls=self._controls,
            columns=afanes.ui.theme.FIELD_FLOW_COLUMNS,
            spacing=afanes.ui.theme.ITEM_GAP,
            run_spacing=afanes.ui.theme.ITEM_GAP,
        )

    def layout(self, width: float) -> None:
        """Assign column spans from the available width.

        Parameters
        ----------
        width : float
            Width available to the row in logical pixels.

        Notes
        -----
        A non-positive width leaves the current spans untouched. Hidden
        controls take no span, and each visible run sums to the full column
        count so no lateral gutter remains.
        """
        if width <= 0:
            return
        visible = [control for control in self._controls if control.visible]
        if not visible:
            return
        gap = afanes.ui.theme.ITEM_GAP
        capacity = int((width + gap) // (afanes.ui.theme.FIELD_MIN_WIDTH + gap))
        capacity = max(1, min(capacity, len(visible), afanes.ui.theme.FIELD_FLOW_COLUMNS))
        self._assign_spans(visible, capacity)

    def _assign_spans(self, visible: Sequence[ft.Control], capacity: int) -> None:
        """Fill each visible run with the full column count.

        Parameters
        ----------
        visible : Sequence[flet.Control]
            Controls that currently take part in the flow.
        capacity : int
            Maximum number of controls in one run.
        """
        for start in range(0, len(visible), capacity):
            run = visible[start : start + capacity]
            base, extra = divmod(afanes.ui.theme.FIELD_FLOW_COLUMNS, len(run))
            for index, control in enumerate(run):
                control.col = base + (1 if index < extra else 0)
