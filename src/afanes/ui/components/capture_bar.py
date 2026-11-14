# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Inbox capture bar shared by the workspace browser."""

from collections.abc import Awaitable, Callable

import flet as ft

import afanes.i18n.ui
import afanes.ui.theme


class CaptureBar:
    """Compose the capture field, its action, and the section label.

    Parameters
    ----------
    on_capture : collections.abc.Callable[[], collections.abc.Awaitable[None]]
        Submit the current capture text.
    on_change : collections.abc.Callable[[], collections.abc.Awaitable[None]]
        Update the capture action availability as the text changes.
    """

    def __init__(
        self,
        on_capture: Callable[[], Awaitable[None]],
        on_change: Callable[[], Awaitable[None]],
        *,
        copy: afanes.i18n.ui.UiCopy | None = None,
    ) -> None:
        """Build the capture controls.

        Parameters
        ----------
        on_capture : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Submit the current capture text.
        on_change : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Update the capture action availability as the text changes.
        """
        self._copy = afanes.i18n.ui.UiCopy.english() if copy is None else copy
        # Flet 1.1.2 ignores a focus request on a field built with
        # shift_enter=True, so the composer keeps Enter for new lines and the
        # Capture button submits.
        self.field = ft.TextField(
            hint_text=self._copy.COMPOSER_HINT,
            multiline=True,
            min_lines=1,
            max_lines=4,
            on_submit=on_capture,
            on_change=on_change,
            key="workspace-capture-field",
        )
        self.button = ft.FilledButton(
            content=self._copy.CAPTURE_ACTION,
            on_click=on_capture,
            disabled=True,
            key="workspace-capture-button",
        )
        self.actions = ft.Row(
            controls=[self.button],
            alignment=ft.MainAxisAlignment.END,
            key="workspace-capture-actions",
        )
        self.label = ft.Text(
            self._copy.COMPOSER_LABEL,
            style=afanes.ui.theme.TEXT_ROLES["caption-heading"],
        )
        self.section = ft.Column(
            controls=[self.label, self.field, self.actions],
            spacing=afanes.ui.theme.ITEM_GAP,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            key="workspace-capture-section",
        )
