# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Welcome and session notice views for the application shell.

Both views are presentational. They read the shared application state and
forward user intent to its commands; they never read vault files, parse
Markdown, or write to disk. A single update callback requests a repaint so the
views can be constructed without a live Flet page in tests.
"""

from collections.abc import Awaitable, Callable

import flet as ft

import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
from afanes.ui.components.banner import Banner


class WelcomeView:
    """First-run welcome state.

    Parameters
    ----------
    on_choose : Callable[[], Awaitable[None]] | None
        Command that opens the native folder picker and selects a vault.
        Supplied by the desktop presentation.
    on_open_path : Callable[[str], Awaitable[None]] | None
        Command that opens the vault named by a typed path. Supplied by the
        browser presentation, which has no native directory dialog.
    on_create : Callable[[], Awaitable[None]] | None
        Command that opens the new-vault dialog. Supplied by both
        presentations, because no native dialog can name a folder that does not
        exist yet.

    Raises
    ------
    ValueError
        If neither selection command is supplied. Each presentation must offer
        exactly one way to choose an existing vault.
    """

    def __init__(
        self,
        on_choose: Callable[[], Awaitable[None]] | None = None,
        on_open_path: Callable[[str], Awaitable[None]] | None = None,
        on_create: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Store the vault selection actions for this presentation."""
        if on_choose is None and on_open_path is None:
            message = "The welcome state needs one vault selection command."
            raise ValueError(message)
        self._on_choose = on_choose
        self._on_open_path = on_open_path
        self._on_create = on_create

    def build(self) -> ft.Control:
        """Build the welcome layout.

        Returns
        -------
        ft.Control
            Centered welcome layout with the selection action for this
            presentation and any startup message.
        """
        controls: list[ft.Control] = [
            ft.Text(
                afanes.ui.strings.WELCOME_TITLE,
                style=afanes.ui.theme.TEXT_ROLES["title-1"],
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(afanes.ui.strings.WELCOME_BODY, text_align=ft.TextAlign.CENTER),
        ]
        if self._on_choose is not None:
            controls.append(
                ft.FilledButton(
                    content=afanes.ui.strings.WELCOME_CHOOSE,
                    icon=ft.Icons.FOLDER_OPEN_OUTLINED,
                    on_click=self._on_choose,
                    autofocus=True,
                    key="welcome-choose",
                ),
            )
        if self._on_open_path is not None:
            controls.extend(self._vault_path_entry(self._on_open_path))
        if self._on_create is not None:
            controls.append(
                ft.FilledButton(
                    content=afanes.ui.strings.NEW_VAULT_ACTION,
                    icon=ft.Icons.CREATE_NEW_FOLDER_OUTLINED,
                    on_click=self._on_create,
                    key="welcome-create",
                ),
            )
        controls.append(
            ft.Text(
                afanes.ui.strings.WELCOME_NOTE,
                style=afanes.ui.theme.TEXT_ROLES["caption"],
                text_align=ft.TextAlign.CENTER,
            ),
        )
        message = afanes.ui.state.app_state.status.message
        if message is not None:
            controls.append(Banner(message).build())
        return ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                controls=controls,
                spacing=afanes.ui.theme.SECTION_GAP,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                width=520,
            ),
        )

    @staticmethod
    def _vault_path_entry(on_open_path: Callable[[str], Awaitable[None]]) -> list[ft.Control]:
        """Build the typed-path selection controls for a browser session."""
        field = ft.TextField(
            label=afanes.ui.strings.WELCOME_PATH_LABEL,
            hint_text=afanes.ui.strings.WELCOME_PATH_HINT,
            width=420,
            autofocus=True,
            key="welcome-path",
        )

        async def open_typed_path() -> None:
            await on_open_path(field.value or "")

        field.on_submit = open_typed_path
        button = ft.FilledButton(
            content=afanes.ui.strings.WELCOME_OPEN,
            icon=ft.Icons.FOLDER_OPEN_OUTLINED,
            on_click=open_typed_path,
            key="welcome-open",
        )
        return [field, button]


class SessionNotice:
    """Notice shown when another session already owns the workspace.

    Parameters
    ----------
    on_retry : Callable[[], Awaitable[None]]
        Command that tries to claim the session again.
    """

    def __init__(self, on_retry: Callable[[], Awaitable[None]]) -> None:
        """Store the retry action."""
        self._on_retry = on_retry

    def build(self) -> ft.Control:
        """Build the session notice.

        Returns
        -------
        ft.Control
            Centered notice with a single retry action.
        """
        return ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                controls=[
                    ft.Text(
                        afanes.ui.strings.SESSION_ACTIVE_TITLE,
                        style=afanes.ui.theme.TEXT_ROLES["title-1"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(afanes.ui.strings.SESSION_ACTIVE_BODY, text_align=ft.TextAlign.CENTER),
                    ft.FilledButton(
                        content=afanes.ui.strings.SESSION_RETRY,
                        on_click=self._on_retry,
                        autofocus=True,
                        key="session-retry",
                    ),
                ],
                spacing=afanes.ui.theme.SECTION_GAP,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                width=520,
            ),
        )
