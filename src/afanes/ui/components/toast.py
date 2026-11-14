# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Transient toast presenter backed by the Flet SnackBar control."""

from collections.abc import Awaitable, Callable

import flet as ft

import afanes.i18n.ui
import afanes.ui.theme
from afanes.ui.state.status import Notice, NoticeAction


class ToastPresenter:
    """Show one transient notice at a time.

    Parameters
    ----------
    page : flet.Page
        Page that owns the dialog stack.
    on_action : collections.abc.Callable[[NoticeAction], collections.abc.Awaitable[None]] | None
        Command run when the user selects the notice action, or ``None`` when
        the presenter only displays messages.

    Notes
    -----
    The presenter owns one snackbar reference. It closes only that control and
    never pops the dialog stack, so a vault or reference dialog remains open
    when a toast is replaced.
    """

    def __init__(
        self,
        page: ft.Page,
        on_action: Callable[[NoticeAction], Awaitable[None]] | None = None,
        *,
        copy: afanes.i18n.ui.UiCopy | None = None,
    ) -> None:
        """Store the page and the optional action command.

        Parameters
        ----------
        page : flet.Page
            Page that owns the dialog stack.
        on_action : collections.abc.Callable[[NoticeAction], collections.abc.Awaitable[None]] | None
            Command run when the user selects the notice action.
        """
        self._copy = afanes.i18n.ui.UiCopy.english() if copy is None else copy
        self._page = page
        self._on_action = on_action
        self.current: ft.SnackBar | None = None

    def show(self, notice: Notice) -> None:
        """Show a notice, replacing the current toast.

        Parameters
        ----------
        notice : afanes.ui.state.status.Notice
            Message and optional reversible action to show.

        Notes
        -----
        A second notice closes the previous snackbar by setting its ``open``
        flag, then attaches the new one. The previous control is never popped
        from the dialog stack because that stack may also hold a modal dialog.
        """
        self.close()
        snackbar = ft.SnackBar(
            content=ft.Text(
                notice.message,
                color=afanes.ui.theme.TOAST_TEXT_COLOR,
                selectable=True,
            ),
            behavior=ft.SnackBarBehavior.FLOATING,
            show_close_icon=True,
            close_icon_color=afanes.ui.theme.TOAST_ACTION_COLOR,
            bgcolor=afanes.ui.theme.TOAST_SURFACE_COLOR,
            duration=afanes.ui.theme.TOAST_DURATION_MS,
            margin=afanes.ui.theme.TOAST_MARGIN,
            padding=afanes.ui.theme.TOAST_PADDING,
            key="feedback-toast",
        )
        snackbar.on_dismiss = self._dismiss_handler(snackbar)
        if notice.action is not None:
            snackbar.action = ft.SnackBarAction(
                label=self._copy.UNDO_ACTION,
                text_color=afanes.ui.theme.TOAST_ACTION_COLOR,
                on_click=self._action_handler(snackbar, notice.action),
            )
        self.current = snackbar
        self._page.show_dialog(snackbar)
        self._page.update()

    def close(self) -> None:
        """Close the toast this presenter owns, if any.

        Notes
        -----
        Only the retained snackbar is closed. No other dialog is popped, so a
        modal surface that is still open stays open.
        """
        current = self.current
        self.current = None
        if current is None:
            return
        current.open = False
        self._page.update()

    def _dismiss_handler(self, snackbar: ft.SnackBar) -> Callable[..., None]:
        """Return the handler that forgets one dismissed snackbar."""

        def handle(_event: object = None) -> None:
            if self.current is snackbar:
                self.current = None

        return handle

    def _action_handler(
        self,
        snackbar: ft.SnackBar,
        action: NoticeAction,
    ) -> Callable[..., Awaitable[None]]:
        """Return the handler that runs one notice action."""

        async def handle(_event: object = None) -> None:
            if self._on_action is not None:
                await self._on_action(action)
            if self.current is snackbar:
                self.close()

        return handle
