# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Surface containers shared by the workspace views."""

import flet as ft

import afanes.ui.theme


class Panel:
    """One inline confirmation panel with a title, body, and actions.

    Parameters
    ----------
    title : str
        Panel heading.
    body : flet.Control
        Main panel content.
    actions : list[flet.Control]
        Buttons shown below the body.
    """

    def __init__(self, title: str, body: ft.Control, actions: list[ft.Control]) -> None:
        """Store the panel parts.

        Parameters
        ----------
        title : str
            Panel heading.
        body : flet.Control
            Main panel content.
        actions : list[flet.Control]
            Buttons shown below the body.
        """
        self._title = title
        self._body = body
        self._actions = actions

    def build(self) -> ft.Container:
        """Build the panel container.

        Returns
        -------
        ft.Container
            Surface container with the title, body, and action row.
        """
        return ft.Container(
            bgcolor=afanes.ui.theme.SURFACE_CONTAINER_COLOR,
            border=ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR),
            border_radius=afanes.ui.theme.SURFACE_RADIUS,
            padding=afanes.ui.theme.ITEM_GAP,
            content=ft.Column(
                controls=[
                    ft.Text(self._title, style=afanes.ui.theme.TEXT_ROLES["title-4"]),
                    self._body,
                    ft.Row(controls=self._actions, spacing=afanes.ui.theme.ITEM_GAP, wrap=True),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
        )


class Card:
    """One surface card that wraps a view's main content.

    Parameters
    ----------
    body : flet.Control
        Content shown inside the card.
    """

    def __init__(self, body: ft.Control) -> None:
        """Store the card content.

        Parameters
        ----------
        body : flet.Control
            Content shown inside the card.
        """
        self._body = body

    def build(self) -> ft.Container:
        """Build the card container.

        Returns
        -------
        ft.Container
            Expanded surface container around the content.
        """
        return ft.Container(
            expand=True,
            padding=afanes.ui.theme.SECTION_GAP,
            bgcolor=afanes.ui.theme.CARD_SURFACE_COLOR,
            border=ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR),
            border_radius=afanes.ui.theme.SURFACE_RADIUS,
            content=self._body,
        )
