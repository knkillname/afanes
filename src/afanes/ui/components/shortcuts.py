# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Grouped keyboard shortcut reference sheet.

The sheet is presentational: it renders the active catalog and reports that the
user asked to close it. The application shell owns the dialog lifetime.
"""

from collections.abc import Callable

import flet as ft

import afanes.i18n.ui
import afanes.ui.theme

GROUP_SHORTCUTS: dict[str, tuple[str, ...]] = {
    "general": ("search", "capture", "shortcuts", "close"),
    "calendar": ("day", "week", "month", "week_bounds", "open_day"),
    "navigation": ("next_control", "previous_control"),
}


class ShortcutSheet:
    """One grouped keyboard shortcut sheet.

    Parameters
    ----------
    on_close : collections.abc.Callable[[], None] | None
        Called when the user closes the sheet with the Close action, or
        ``None`` when the host only needs the control tree.
    copy : afanes.i18n.ui.UiCopy | None
        Active interface catalog. English is used when omitted.
    """

    def __init__(
        self,
        on_close: Callable[[], None] | None = None,
        *,
        copy: afanes.i18n.ui.UiCopy | None = None,
    ) -> None:
        """Store the close command and build the sheet."""
        self._copy = afanes.i18n.ui.UiCopy.english() if copy is None else copy
        self._on_close = on_close
        self.sections = tuple(
            (group, self._copy.mapping("SHORTCUT_GROUP_LABELS")[group], GROUP_SHORTCUTS[group])
            for group in ("general", "calendar", "navigation")
        )
        self.close_button = ft.TextButton(
            content=self._copy.CLOSE_ACTION,
            on_click=self._close,
            autofocus=True,
            key="shortcuts-close",
        )
        self.dialog = ft.AlertDialog(
            title=ft.Text(self._copy.SHORTCUTS_TITLE),
            content=ft.Column(
                controls=[self._section(group, heading, shortcuts) for group, heading, shortcuts in self.sections],
                spacing=afanes.ui.theme.SECTION_GAP,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[self.close_button],
            key="shortcuts-dialog",
        )

    def build(self) -> ft.AlertDialog:
        """Return the prepared shortcut dialog.

        Returns
        -------
        ft.AlertDialog
            Dialog with the three grouped sections and the Close action.
        """
        return self.dialog

    def _section(self, group: str, heading: str, shortcuts: tuple[str, ...]) -> ft.Control:
        """Build one heading and its shortcut rows."""
        keys = self._copy.mapping("SHORTCUT_KEYS")
        labels = self._copy.mapping("SHORTCUT_LABELS")
        return ft.Column(
            controls=[
                ft.Text(heading, style=afanes.ui.theme.TEXT_ROLES["title-4"]),
                *[self._row(keys[shortcut], labels[shortcut]) for shortcut in shortcuts],
            ],
            spacing=afanes.ui.theme.ROW_GAP,
            key=f"shortcuts-group-{group}",
        )

    @staticmethod
    def _row(keys: str, label: str) -> ft.Control:
        """Build one key-label and description row."""
        return ft.Row(
            controls=[
                ft.Container(
                    min_width=afanes.ui.theme.SHORTCUT_KEYS_MIN_WIDTH,
                    content=ft.Text(keys, style=afanes.ui.theme.TEXT_ROLES["heading"]),
                ),
                ft.Text(label, style=afanes.ui.theme.TEXT_ROLES["body"], expand=True),
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def _close(self, _event: object = None) -> None:
        """Report that the user asked to close the sheet."""
        if self._on_close is not None:
            self._on_close()
