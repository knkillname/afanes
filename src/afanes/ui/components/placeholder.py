# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Symbolic placeholder page for regions that normally hold content."""

import flet as ft

import afanes.ui.theme


class PlaceholderPage:
    """One centered empty-state page with a symbolic icon.

    Parameters
    ----------
    icon : flet.IconData
        Monochrome symbolic glyph shown above the heading.
    title : str
        Heading that names the empty state.
    body : str | None
        Optional guidance line below the heading.
    action : flet.Control | None
        Optional suggested action control.

    Notes
    -----
    The icon is decorative: its semantics subtree is excluded so assistive
    technology reads only the visible heading and guidance. Callers own the copy
    and decide when the empty state applies.
    """

    def __init__(
        self,
        icon: ft.IconData,
        title: str,
        *,
        body: str | None = None,
        action: ft.Control | None = None,
    ) -> None:
        """Store the placeholder parts.

        Parameters
        ----------
        icon : flet.IconData
            Monochrome symbolic glyph shown above the heading.
        title : str
            Heading that names the empty state.
        body : str | None
            Optional guidance line below the heading.
        action : flet.Control | None
            Optional suggested action control.
        """
        self._icon = icon
        self._title = title
        self._body = body
        self._action = action

    def build(self) -> ft.Control:
        """Build the placeholder page.

        Returns
        -------
        flet.Control
            Centered container with the icon, heading, guidance, and optional
            action.
        """
        controls: list[ft.Control] = [
            ft.Semantics(
                content=ft.Icon(
                    self._icon,
                    size=afanes.ui.theme.ICON_SIZE_LARGE,
                    color=afanes.ui.theme.MUTED_TEXT_COLOR,
                ),
                exclude_semantics=True,
            ),
            ft.Text(
                self._title,
                style=afanes.ui.theme.TEXT_ROLES["title-4"],
                text_align=ft.TextAlign.CENTER,
            ),
        ]
        if self._body is not None:
            controls.append(
                ft.Text(
                    self._body,
                    style=afanes.ui.theme.TEXT_ROLES["body"],
                    color=afanes.ui.theme.MUTED_TEXT_COLOR,
                    text_align=ft.TextAlign.CENTER,
                    selectable=True,
                )
            )
        if self._action is not None:
            controls.append(self._action)
        return ft.Container(
            padding=afanes.ui.theme.SECTION_GAP,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                controls=controls,
                spacing=afanes.ui.theme.ITEM_GAP,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            key="placeholder-page",
        )
