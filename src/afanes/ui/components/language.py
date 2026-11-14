# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Language menu shared by the welcome state and the workspace."""

import dataclasses
from collections.abc import Awaitable, Callable

import flet as ft

import afanes.i18n.ui


@dataclasses.dataclass(frozen=True, slots=True)
class LanguageMenu:
    """Offer English, Spanish, and the system language.

    Attributes
    ----------
    copy : afanes.i18n.ui.UiCopy
        Active catalog used for the control label and system choice.
    on_select : collections.abc.Callable[[str | None], collections.abc.Awaitable[None] | None]
        Command that stores the chosen language, or ``None`` for the system
        choice.
    prefix : str
        Control key prefix. The menu and item keys use this prefix.
    """

    copy: afanes.i18n.ui.UiCopy
    on_select: Callable[[str | None], Awaitable[None] | None]
    prefix: str = "language"

    def items(self) -> list[ft.PopupMenuItem]:
        """Return one menu item per supported choice.

        Returns
        -------
        list[flet.PopupMenuItem]
            English, Español, and the system choice, in that order.
        """
        return [
            ft.PopupMenuItem(
                content=self.copy.LANGUAGE_ENGLISH,
                on_click=self._choose_english,
                key=f"{self.prefix}-language-en",
            ),
            ft.PopupMenuItem(
                content=self.copy.LANGUAGE_SPANISH,
                on_click=self._choose_spanish,
                key=f"{self.prefix}-language-es",
            ),
            ft.PopupMenuItem(
                content=self.copy.LANGUAGE_SYSTEM,
                on_click=self._choose_system,
                key=f"{self.prefix}-language-system",
            ),
        ]

    def control(self) -> ft.PopupMenuButton:
        """Return a standalone language menu button.

        Returns
        -------
        flet.PopupMenuButton
            Button that lists the language choices.
        """
        return ft.PopupMenuButton(
            content=ft.Text(self.copy.LANGUAGE_MENU),
            tooltip=self.copy.LANGUAGE_MENU_TITLE,
            items=self.items(),
            key=f"{self.prefix}-language",
        )

    def _choose_english(self) -> Awaitable[None] | None:
        """Store English as the preferred language."""
        return self.on_select("en")

    def _choose_spanish(self) -> Awaitable[None] | None:
        """Store Spanish as the preferred language."""
        return self.on_select("es")

    def _choose_system(self) -> Awaitable[None] | None:
        """Clear the preference and use the system language."""
        return self.on_select(None)
