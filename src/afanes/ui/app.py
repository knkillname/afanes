# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Flet application shell and first-run routing."""

from pathlib import Path

import flet as ft

import afanes.core.vault
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
            self.page.add(afanes.ui.views.inbox.SessionNotice(self.retry_session).build())
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
                self.page.add(
                    afanes.ui.views.inbox.WelcomeView(
                        on_choose=self.choose_vault,
                        on_create=self.create_vault,
                    ).build(),
                )
            else:
                self.page.add(
                    afanes.ui.views.inbox.WelcomeView(
                        on_open_path=self.open_path,
                        on_create=self.create_vault,
                    ).build(),
                )
        else:
            workspace = afanes.ui.views.workspace.WorkspaceView(
                self.page.update,
                self.choose_vault,
                self.create_vault,
                self.close_vault,
            ).build()
            digest = self._due_digest()
            if digest is None:
                self.page.add(workspace)
            else:
                self.page.add(
                    ft.Column(
                        controls=[digest, workspace],
                        spacing=afanes.ui.theme.SECTION_GAP,
                        expand=True,
                    )
                )
        self.page.update()

    def _due_digest(self) -> ft.Control | None:
        """Build the launch digest of due work, or ``None`` when there is none.

        Returns
        -------
        ft.Control | None
            Digest card with a review action, or ``None`` when no own step is
            due or overdue.

        Notes
        -----
        Building the digest reads the latest scan only. It never creates,
        changes, or removes a note.
        """
        count = self.state.review_due_count
        if count == 0 or self.state.review_session is not None:
            return None
        message = (
            afanes.ui.strings.REVIEW_LAUNCH_DIGEST_ONE
            if count == 1
            else afanes.ui.strings.REVIEW_LAUNCH_DIGEST_MANY.format(count=count)
        )
        return ft.Container(
            key="launch-digest",
            bgcolor=afanes.ui.theme.SURFACE_CONTAINER_COLOR,
            border_radius=afanes.ui.theme.CARD_RADIUS,
            padding=afanes.ui.theme.ITEM_GAP,
            content=ft.Row(
                controls=[
                    ft.Text(message, expand=True, selectable=True),
                    ft.FilledButton(
                        content=afanes.ui.strings.REVIEW_LAUNCH_DIGEST_ACTION,
                        icon=ft.Icons.PLAY_ARROW,
                        on_click=self.start_launch_review,
                        key="launch-digest-start",
                    ),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    async def start_launch_review(self) -> None:
        """Start the guided review from the launch digest and repaint."""
        await self.state.start_review()
        await self.render()

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

    async def create_vault(self) -> None:
        """Open the creation action for this presentation.

        Notes
        -----
        The starter-content form is shown first in both presentations. A
        desktop session reaches the native directory dialog through the form's
        browse action, so the template choice is visible before a folder is
        chosen and never depends on a second modal opening after the native one
        closes.
        """
        await self.show_create_dialog()

    async def close_vault(self) -> None:
        """Close the current vault and show the welcome state.

        Notes
        -----
        The controller saves an open draft and forgets the remembered vault.
        When the page cannot be committed the workspace stays in place and its
        banner reports the reason.
        """
        if await self.state.close_vault():
            await self.render()

    async def show_create_dialog(self) -> None:
        """Ask for the vault path and starter content, then create the vault.

        Notes
        -----
        The catalog is read through the controller, so the package resources
        are not touched on the interface thread. When the catalog cannot be
        read, the dialog explains it and offers a vault without starter
        content instead of failing to open. A desktop session can type the path
        or use the browse action, which opens the native directory dialog.
        """
        summaries = await self.state.template_summaries()
        by_identifier = {summary.identifier: summary for summary in summaries or ()}
        field = ft.TextField(
            label=afanes.ui.strings.NEW_VAULT_PATH_LABEL,
            hint_text=afanes.ui.strings.WELCOME_PATH_HINT,
            value="",
            autofocus=True,
            expand=True,
            key="create-vault-path",
        )

        async def browse() -> None:
            if self.picker is None:
                return
            selected = await self.picker.get_directory_path(dialog_title=afanes.ui.strings.NEW_VAULT_ACTION)
            if selected is None:
                return
            field.value = selected
            self.page.update()

        browse_button = ft.TextButton(
            content=afanes.ui.strings.NEW_VAULT_BROWSE,
            icon=ft.Icons.FOLDER_OPEN,
            on_click=browse,
            visible=self.is_desktop,
            key="create-vault-browse",
        )
        selector = ft.Dropdown(
            label=afanes.ui.strings.NEW_VAULT_TEMPLATE_LABEL,
            options=[
                ft.dropdown.Option(key="", text=afanes.ui.strings.NEW_VAULT_TEMPLATE_NONE),
                *[
                    ft.dropdown.Option(
                        key=summary.identifier,
                        text=afanes.ui.strings.NEW_VAULT_TEMPLATE_OPTION.format(
                            label=summary.label,
                            description=summary.description,
                        ),
                    )
                    for summary in summaries or ()
                ],
            ],
            value="",
            key="create-vault-template",
        )
        unavailable = ft.Text(
            afanes.ui.strings.NEW_VAULT_TEMPLATE_UNAVAILABLE,
            color=afanes.ui.theme.ERROR_COLOR,
            visible=summaries is None,
            key="create-vault-templates-error",
        )
        folders = ", ".join(f"{folder.as_posix()}/" for folder in afanes.core.vault.Vault.default_layout())
        preview = ft.Text(
            afanes.ui.strings.NEW_VAULT_PREVIEW_GUIDE.format(folders=folders),
            size=12,
            color=afanes.ui.theme.MUTED_TEXT_COLOR,
            selectable=True,
            key="create-vault-preview",
        )
        error = ft.Text(
            "",
            color=afanes.ui.theme.ERROR_COLOR,
            visible=False,
            key="create-vault-error",
        )

        def refresh_preview() -> None:
            summary = by_identifier.get(selector.value or "")
            if summary is None:
                preview.value = afanes.ui.strings.NEW_VAULT_PREVIEW_GUIDE.format(folders=folders)
            else:
                preview.value = afanes.ui.strings.NEW_VAULT_PREVIEW_TEMPLATE.format(
                    folders=folders,
                    notes=afanes.ui.strings.note_count(summary.note_count),
                )
            self.page.update()

        selector.on_select = refresh_preview

        async def submit() -> None:
            text = (field.value or "").strip()
            if not text:
                self._show_create_error(error, afanes.ui.strings.VAULT_PATH_REQUIRED)
                return
            if not await self.state.create_vault(Path(text), template=selector.value or None):
                self._show_create_error(error, self.state.message or afanes.ui.strings.VAULT_PATH_REQUIRED)
                return
            self.page.pop_dialog()
            await self.render()

        async def cancel() -> None:
            self.page.pop_dialog()
            self.page.update()

        field.on_submit = submit
        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text(afanes.ui.strings.NEW_VAULT_DIALOG_TITLE),
                content=ft.Column(
                    controls=[
                        ft.Text(afanes.ui.strings.NEW_VAULT_DIALOG_BODY),
                        ft.Row(
                            controls=[field, browse_button],
                            spacing=afanes.ui.theme.ITEM_GAP,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        selector,
                        unavailable,
                        preview,
                        error,
                    ],
                    tight=True,
                ),
                actions=[
                    ft.TextButton(
                        content=afanes.ui.strings.CANCEL_ACTION,
                        on_click=cancel,
                        key="create-vault-cancel",
                    ),
                    ft.FilledButton(
                        content=afanes.ui.strings.NEW_VAULT_CREATE,
                        on_click=submit,
                        key="create-vault-submit",
                    ),
                ],
            ),
        )
        self.page.update()

    def _show_create_error(self, error: ft.Text, message: str) -> None:
        """Show an inline creation error without closing the dialog."""
        error.value = message
        error.visible = True
        self.page.update()

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
