# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Flet application shell and first-run routing."""

from pathlib import Path

import flet as ft

import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
import afanes.ui.views.inbox
import afanes.ui.views.workspace


class _Shell:
    """Own one page's presentation setup and first-run routing.

    Parameters
    ----------
    page : flet.Page
        Page created by :func:`flet.run`.
    launch_vault : pathlib.Path | None
        Vault supplied when the process started, or ``None`` to use the
        remembered vault.

    Notes
    -----
    The shell reads :attr:`flet.Page.web` once to decide which vault selection
    action the welcome state offers and whether the native window can be
    configured. A browser session shows a typed-path field because a browser
    file dialog cannot return a directory path. Only one session may drive the
    workspace; a second one gets a notice and no vault access.
    """

    def __init__(self, page: ft.Page, launch_vault: Path | None) -> None:
        self.page = page
        self.launch_vault = launch_vault
        self.state = afanes.ui.state.app_state
        self.is_desktop = not page.web
        self.picker: ft.FilePicker | None = None

    async def start(self) -> None:
        """Configure the page, claim the session, and open the first state."""
        self._configure()
        if not self.state.begin_session():
            self.page.add(afanes.ui.views.inbox.build_session_notice(self.retry_session))
            self.page.update()
            return
        await self._start_workspace()

    def _configure(self) -> None:
        """Apply page chrome and create the native picker when available."""
        self.page.title = afanes.ui.strings.APP_TITLE
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.padding = afanes.ui.theme.PAGE_PADDING
        self.page.on_disconnect = afanes.ui.state.app_state.release_session
        if not self.is_desktop:
            return
        self.page.window.width = 1100
        self.page.window.height = 760
        self.page.window.min_width = afanes.ui.theme.WINDOW_MIN_WIDTH
        self.page.window.min_height = afanes.ui.theme.WINDOW_MIN_HEIGHT
        self.picker = ft.FilePicker()
        self.page.services.append(self.picker)

    async def _start_workspace(self) -> None:
        """Open the launch or remembered vault and render the result."""
        if self.launch_vault is None:
            await self.state.start()
        else:
            await self.state.open_vault_for_run(self.launch_vault)
        await self.render()

    async def retry_session(self) -> None:
        """Try to claim the session again after another window disconnects."""
        if not self.state.begin_session():
            self.page.update()
            return
        await self._start_workspace()

    async def render(self) -> None:
        """Render the welcome state or the workspace for the current session."""
        self.page.controls.clear()
        if self.state.vault_root is None:
            if self.is_desktop:
                self.page.add(afanes.ui.views.inbox.build_welcome(on_choose=self.choose_vault))
            else:
                self.page.add(afanes.ui.views.inbox.build_welcome(on_open_path=self.open_path))
        else:
            self.page.add(afanes.ui.views.workspace.build_workspace(self.page.update, self.choose_vault))
        self.page.update()

    async def open_path(self, text: str) -> None:
        """Open the vault named by typed text and repaint."""
        await self.state.open_vault_path(text)
        await self.render()

    async def choose_vault(self) -> None:
        """Open the vault selection action for this presentation."""
        if not self.is_desktop:
            self.show_vault_dialog()
            return
        if self.picker is None:
            return
        selected = await self.picker.get_directory_path(dialog_title=afanes.ui.strings.WELCOME_CHOOSE)
        if selected is None:
            return
        path = Path(selected)
        if self.state.vault_root is None:
            await self.state.choose_vault(path)
        else:
            await self.state.change_vault(path)
        await self.render()

    def show_vault_dialog(self) -> None:
        """Ask for a vault path in a dialog, for a browser session."""
        field = ft.TextField(
            label=afanes.ui.strings.WELCOME_PATH_LABEL,
            hint_text=afanes.ui.strings.WELCOME_PATH_HINT,
            value="" if self.state.vault_root is None else str(self.state.vault_root),
            autofocus=True,
            key="change-vault-path",
        )

        async def submit() -> None:
            self.page.pop_dialog()
            await self.open_path(field.value or "")

        async def cancel() -> None:
            self.page.pop_dialog()
            self.page.update()

        field.on_submit = submit
        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text(afanes.ui.strings.CHANGE_VAULT_DIALOG_TITLE),
                content=ft.Column(
                    controls=[
                        ft.Text(afanes.ui.strings.CHANGE_VAULT_DIALOG_BODY),
                        field,
                    ],
                    tight=True,
                ),
                actions=[
                    ft.TextButton(
                        content=afanes.ui.strings.CANCEL_ACTION,
                        on_click=cancel,
                        key="change-vault-cancel",
                    ),
                    ft.FilledButton(
                        content=afanes.ui.strings.WELCOME_OPEN,
                        on_click=submit,
                        key="change-vault-open",
                    ),
                ],
            ),
        )
        self.page.update()


async def main(page: ft.Page, launch_vault: Path | None = None) -> None:
    """Start the Afanes interface in the presentation Flet chose.

    Parameters
    ----------
    page : ft.Page
        Page created by :func:`flet.run`.
    launch_vault : pathlib.Path | None
        Vault supplied when the process started. It takes precedence over the
        remembered vault and is never written to the settings file.

    Notes
    -----
    The shell performs no network I/O. The first development run may provision
    the Flet desktop client; that provisioning is an environment step, not
    product behavior.
    """
    await _Shell(page, launch_vault).start()
