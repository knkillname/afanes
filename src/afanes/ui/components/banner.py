# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Accessible warning banner shared by every view."""

import flet as ft

import afanes.ui.theme


class Banner:
    """One accessible warning banner.

    Parameters
    ----------
    message : str
        Warning text shown to the user.
    """

    def __init__(self, message: str) -> None:
        """Store the warning text.

        Parameters
        ----------
        message : str
            Warning text shown to the user.
        """
        self._message = message

    def build(self) -> ft.Control:
        """Build the banner control.

        Returns
        -------
        ft.Control
            Container with an error icon and selectable warning text.
        """
        return ft.Container(
            bgcolor=afanes.ui.theme.ERROR_CONTAINER_COLOR,
            padding=afanes.ui.theme.BANNER_PADDING,
            border_radius=afanes.ui.theme.SURFACE_RADIUS,
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=afanes.ui.theme.ERROR_TEXT_COLOR),
                    ft.Text(
                        self._message,
                        color=afanes.ui.theme.ERROR_TEXT_COLOR,
                        selectable=True,
                        expand=True,
                    ),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        )
