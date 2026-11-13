# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Flet application shell and first-run routing."""

import asyncio
import contextlib
import datetime
from pathlib import Path

import flet as ft

import afanes.__about__
import afanes.core.vault.service
import afanes.ui.components.toast
import afanes.ui.state
import afanes.ui.state.status
import afanes.ui.strings
import afanes.ui.theme
import afanes.ui.views.inbox
import afanes.ui.views.workspace
from afanes.core.template_cards import TemplateCardListing
from afanes.models.link import ReferenceScheme
from afanes.models.note import CategoryLabel, NoteDate, NoteType
from afanes.ui.components.panel import Panel
from afanes.ui.components.role_name import RoleNameDialog
from afanes.ui.components.role_reference import RoleReferenceDialog
from afanes.ui.components.template_cards import TemplateCardContext, TemplateCardPicker

# Public task name so the shell can be observed without exposing its fields.
REFRESH_TASK_NAME = "workspace-refresh"


class AppShell:
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

    @classmethod
    async def main(cls, page: ft.Page, launch_vault: Path | None = None) -> None:
        """Start the Afanes interface in the presentation Flet chose.

        Parameters
        ----------
        page : ft.Page
            Page created by :func:`flet.run`.
        launch_vault : pathlib.Path | None
            Vault supplied when the process started. It takes precedence over
            the remembered vault and is never written to the settings file.

        Notes
        -----
        The shell performs no network I/O. The first development run may
        provision the Flet desktop client; that provisioning is an environment
        step, not product behavior.
        """
        await cls(page, launch_vault).start()

    def __init__(self, page: ft.Page, launch_vault: Path | None) -> None:
        self.page = page
        self.launch_vault = launch_vault
        self.state = afanes.ui.state.app_state
        self.is_desktop = not page.web
        self.picker: ft.FilePicker | None = None
        self.workspace: afanes.ui.views.workspace.WorkspaceView | None = None
        self.toast = afanes.ui.components.toast.ToastPresenter(page, self._handle_notice_action)
        self.refresh_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Configure the page, claim the session, and open the first state."""
        self._configure()
        if not self.state.status.begin_session():
            self.page.add(afanes.ui.views.inbox.SessionNotice(self.retry_session).build())
            self.page.update()
            return
        await self._start_workspace()

    def _configure(self) -> None:
        """Apply page chrome and create the native picker when available."""
        self.page.title = afanes.ui.strings.APP_TITLE
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.theme = afanes.ui.theme.LIGHT_THEME
        self.page.dark_theme = afanes.ui.theme.DARK_THEME
        self.page.bgcolor = afanes.ui.theme.PAGE_SURFACE_COLOR
        self.page.padding = afanes.ui.theme.PAGE_PADDING
        self.page.on_disconnect = self.release_session
        self.page.on_resize = self._on_resize
        self.page.on_keyboard_event = self._on_keyboard
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
            await self.state.workspace.start()
        else:
            await self.state.workspace.open_vault_for_run(self.launch_vault)
        await self.render()

    async def retry_session(self) -> None:
        """Try to claim the session again after another window disconnects."""
        if not self.state.status.begin_session():
            self.page.update()
            return
        await self._start_workspace()

    def release_session(self) -> None:
        """Release the session and stop the background refresh loop.

        Notes
        -----
        Flet calls this when the page disconnects. The loop is cancelled before
        the session marker is released so a new session never inherits the old
        task.
        """
        self._cancel_refresh_loop()
        self.state.status.release_session()

    def _start_refresh_loop(self) -> None:
        """Start the single background refresh loop when none is running."""
        if self.refresh_task is not None and not self.refresh_task.done():
            return
        self.refresh_task = asyncio.create_task(self._refresh_loop(), name=REFRESH_TASK_NAME)

    def _cancel_refresh_loop(self) -> None:
        """Cancel the refresh loop without waiting for it."""
        task = self.refresh_task
        self.refresh_task = None
        if task is not None and not task.done():
            task.cancel()

    async def _stop_refresh_loop(self) -> None:
        """Cancel and await the refresh loop before replacing the workspace."""
        task = self.refresh_task
        self.refresh_task = None
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _refresh_loop(self) -> None:
        """Apply external vault changes on the fixed background interval.

        Notes
        -----
        The loop reads only :data:`afanes.ui.state.session.REFRESH_SECONDS`. Each tick
        asks the controller for a changed scan and repaints only when one was
        applied. Cancellation closes the loop on vault close, session release,
        and workspace replacement.
        """
        while True:
            await asyncio.sleep(afanes.ui.state.session.REFRESH_SECONDS)
            if await self.state.workspace.refresh_workspace() and self.workspace is not None:
                self.workspace.refresh()

    def _refresh_current_workspace(self) -> None:
        """Refresh the retained workspace after a dialog command."""
        if self.workspace is not None:
            self.workspace.refresh()

    @staticmethod
    def _has_text(value: str | None) -> bool:
        """Return whether a field holds non-blank text."""
        return bool((value or "").strip())

    def _refresh_dialog_submit(self, field: ft.TextField, button: ft.FilledButton) -> None:
        """Enable a dialog action when its field has text."""
        button.disabled = not self._has_text(field.value)
        self.page.update()

    def _viewport_width(self) -> int:
        """Return the current viewport width in logical pixels.

        Returns
        -------
        int
            Page width when the client reports one, otherwise the configured
            window width, otherwise the default three-region width.
        """
        width = getattr(self.page, "width", None)
        if isinstance(width, int | float) and width > 0:
            return int(width)
        window_width = self.page.window.width
        if isinstance(window_width, int | float) and window_width > 0:
            return int(window_width)
        return afanes.ui.theme.SHELL_WIDE_MIN

    def _on_resize(self, _event: object = None) -> None:
        """Apply the viewport width to the retained workspace."""
        if self.workspace is None:
            return
        self.workspace.resize(self._viewport_width())

    async def _on_keyboard(self, event: ft.KeyboardEvent) -> None:
        """Route the workspace shortcuts from the page keyboard event."""
        key = (event.key or "").upper()
        if key == "ESCAPE":
            if self.workspace is not None:
                if await self.workspace.clear_search():
                    return
                self.workspace.close_drawer()
            return
        if not event.ctrl or self.workspace is None:
            return
        if key == "F":
            await self.workspace.focus_search()
        elif key == "N":
            await self.workspace.start_capture()

    async def show_about_dialog(self) -> None:
        """Show the application name, version, and license."""

        async def close() -> None:
            self.page.pop_dialog()
            self.page.update()

        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text(afanes.ui.strings.ABOUT_TITLE),
                content=ft.Column(
                    controls=[
                        ft.Text(
                            afanes.ui.strings.ABOUT_VERSION.format(version=afanes.__about__.__version__),
                            selectable=True,
                        ),
                        ft.Text(afanes.ui.strings.ABOUT_LICENSE, selectable=True),
                    ],
                    tight=True,
                ),
                actions=[
                    ft.TextButton(
                        content=afanes.ui.strings.CLOSE_ACTION,
                        on_click=close,
                        key="about-close",
                    ),
                ],
            ),
        )
        self.page.update()

    async def _handle_notice_action(self, _action: afanes.ui.state.status.NoticeAction) -> None:
        """Run the reversible command carried by a toast action.

        Parameters
        ----------
        _action : afanes.ui.state.status.NoticeAction
            Action selected in the toast.
        """
        self._refresh_current_workspace()

    async def render(self) -> None:
        """Render the welcome state or the workspace for the current session."""
        await self._stop_refresh_loop()
        self.toast.close()
        self.workspace = None
        self.page.controls.clear()
        if self.state.session.adoption_target is not None:
            self.page.add(self._adoption_panel())
        if self.state.session.vault_root is None:
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
                afanes.ui.views.workspace.WorkspaceActions(
                    self.page.update,
                    self.choose_vault,
                    self.create_vault,
                    self.close_vault,
                    on_new_reference=self.show_new_reference_dialog,
                    pick_date=self.pick_date,
                    on_log_entry=self.show_log_entry_dialog,
                    on_missing_role=self.show_role_reference_dialog,
                    pick_role=self.pick_role,
                    on_about=self.show_about_dialog,
                    on_notice=self.toast.show,
                )
            )
            self.workspace = workspace
            workspace.resize(self._viewport_width())
            digest = self._due_digest()
            if digest is None:
                self.page.add(workspace.build())
            else:
                self.page.add(
                    ft.Column(
                        controls=[digest, workspace.build()],
                        spacing=afanes.ui.theme.SECTION_GAP,
                        expand=True,
                    )
                )
        self.page.update()
        if self.state.session.vault_root is not None:
            self._start_refresh_loop()

    def _adoption_panel(self) -> ft.Control:
        """Build the pending adoption offer above the current screen.

        Returns
        -------
        flet.Control
            Shared panel with the explanation and the confirm and cancel
            actions.

        Notes
        -----
        The panel reads the pending target from the session and performs no
        file I/O. Confirming delegates the write to the workspace controller;
        cancelling clears the offer.
        """
        target = self.state.session.adoption_target
        if target is None:
            return ft.Container(visible=False)
        body = ft.Text(
            afanes.ui.strings.VAULT_SCHEMA_ADOPT_BODY.format(path=target),
            selectable=True,
        )
        actions: list[ft.Control] = [
            ft.TextButton(
                content=afanes.ui.strings.CANCEL_ACTION,
                on_click=self.cancel_adoption,
                key="adoption-cancel",
            ),
            ft.FilledButton(
                content=afanes.ui.strings.VAULT_SCHEMA_ADOPT_ACTION,
                on_click=self.adopt_vault,
                key="adoption-confirm",
            ),
        ]
        panel = Panel(
            afanes.ui.strings.VAULT_SCHEMA_ADOPT_TITLE,
            body,
            actions,
        ).build()
        return ft.Container(
            key="adoption-panel",
            content=panel,
            margin=ft.Margin.only(bottom=afanes.ui.theme.ADOPTION_PANEL_GAP),
        )

    async def adopt_vault(self) -> None:
        """Adopt the pending folder, open it, and repaint."""
        await self.state.workspace.adopt_vault()
        await self.render()

    async def cancel_adoption(self) -> None:
        """Dismiss the adoption offer and repaint without writing."""
        self.state.workspace.cancel_adoption()
        await self.render()

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
        count = self.state.browser.due_count()
        if count == 0 or self.state.review.review_session is not None:
            return None
        message = (
            afanes.ui.strings.REVIEW_LAUNCH_DIGEST_ONE
            if count == 1
            else afanes.ui.strings.REVIEW_LAUNCH_DIGEST_MANY.format(count=count)
        )
        return ft.Container(
            key="launch-digest",
            bgcolor=afanes.ui.theme.NOTICE_SURFACE_COLOR,
            border=ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.NOTICE_BORDER_COLOR),
            border_radius=afanes.ui.theme.SURFACE_RADIUS,
            padding=afanes.ui.theme.ITEM_GAP,
            content=ft.Row(
                controls=[
                    ft.Text(message, expand=True, selectable=True),
                    ft.FilledButton(
                        content=afanes.ui.strings.REVIEW_LAUNCH_DIGEST_ACTION,
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
        await self.state.review.start()
        await self.render()

    async def open_path(self, text: str) -> None:
        """Open the vault named by typed text and repaint."""
        await self.state.workspace.open_vault_path(text)
        await self.render()

    async def choose_vault(self) -> None:
        """Open the vault selection action for this presentation."""
        if not self.is_desktop:
            self.show_vault_dialog()
            return
        if self.picker is None:
            return
        selected = await self.picker.get_directory_path(dialog_title=afanes.ui.strings.WELCOME_PICKER_TITLE)
        if selected is None:
            return
        path = Path(selected)
        if self.state.session.vault_root is None:
            await self.state.workspace.choose_vault(path)
        else:
            await self.state.workspace.change_vault(path)
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
        await self._stop_refresh_loop()
        if await self.state.workspace.close_vault():
            await self.render()
        elif self.state.session.vault_root is not None:
            self._start_refresh_loop()

    async def pick_date(self, current: datetime.date | None) -> datetime.date | None:
        """Ask for a calendar date and return it, or ``None`` when cancelled.

        Parameters
        ----------
        current : datetime.date | None
            Date to show in the picker, or ``None`` for no preselect.

        Returns
        -------
        datetime.date | None
            Chosen date, or ``None`` when the picker was dismissed.
        """
        loop = asyncio.get_running_loop()
        result: asyncio.Future[datetime.date | None] = loop.create_future()

        def settle(value: datetime.date | None) -> None:
            if not result.done():
                result.set_result(value)

        def on_change(_event: object = None) -> None:
            value = picker.value
            if isinstance(value, datetime.datetime):
                value = value.date()
            settle(value if isinstance(value, datetime.date) else None)

        def on_dismiss(_event: object = None) -> None:
            settle(None)

        picker = ft.DatePicker(
            value=current,
            first_date=datetime.date(1900, 1, 1),
            last_date=datetime.date(2100, 12, 31),
            on_change=on_change,
            on_dismiss=on_dismiss,
        )
        self.page.show_dialog(picker)
        self.page.update()
        return await result

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
        summaries = await self.state.session.template_summaries()
        by_identifier = {summary.identifier: summary for summary in summaries or ()}
        field = ft.TextField(
            label=afanes.ui.strings.NEW_VAULT_PATH_LABEL,
            hint_text=afanes.ui.strings.WELCOME_PATH_HINT,
            value="",
            autofocus=True,
            expand=True,
            key="create-vault-path",
        )
        submit_button = ft.FilledButton(
            content=afanes.ui.strings.NEW_VAULT_CREATE,
            disabled=True,
            key="create-vault-submit",
        )

        async def browse() -> None:
            if self.picker is None:
                return
            selected = await self.picker.get_directory_path(dialog_title=afanes.ui.strings.NEW_VAULT_PICKER_TITLE)
            if selected is None:
                return
            field.value = selected
            self._refresh_dialog_submit(field, submit_button)

        browse_button = ft.TextButton(
            content=afanes.ui.strings.NEW_VAULT_BROWSE,
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
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            visible=summaries is None,
            key="create-vault-templates-error",
        )
        folders = ", ".join(f"{folder.as_posix()}/" for folder in afanes.core.vault.service.Vault.default_layout())
        preview = ft.Text(
            afanes.ui.strings.NEW_VAULT_PREVIEW_GUIDE.format(folders=folders),
            style=afanes.ui.theme.TEXT_ROLES["caption"],
            selectable=True,
            key="create-vault-preview",
        )
        error = ft.Text(
            "",
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
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
                    notes=afanes.ui.strings.CopyFormatter.note_count(summary.note_count),
                )
            self.page.update()

        selector.on_select = refresh_preview

        async def submit() -> None:
            text = (field.value or "").strip()
            if not text:
                self._show_create_error(error, afanes.ui.strings.VAULT_PATH_REQUIRED)
                return
            if not await self.state.workspace.create_vault(Path(text), template=selector.value or None):
                self._show_create_error(error, self.state.status.message or afanes.ui.strings.VAULT_PATH_REQUIRED)
                return
            self.page.pop_dialog()
            await self.render()

        async def cancel() -> None:
            self.page.pop_dialog()
            self.page.update()

        submit_button.on_click = submit
        field.on_change = lambda: self._refresh_dialog_submit(field, submit_button)
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
                    submit_button,
                ],
            ),
        )
        self.page.update()

    def _show_create_error(self, error: ft.Text, message: str) -> None:
        """Show an inline creation error without closing the dialog."""
        error.value = message
        error.visible = True
        self.page.update()

    async def show_new_reference_dialog(self) -> None:
        """Ask for a name and template card, then create the reference.

        Notes
        -----
        The card catalog is read through the controller, so the package
        resources and vault folder are not touched on the interface thread. The
        dialog holds no application state: the chosen card is passed straight to
        the navigation command, which writes the note and opens it in edit mode.
        A blank name or a collision is reported inline and the dialog stays open.
        """
        listing = await self.state.session.template_cards()
        if listing is None:
            listing = TemplateCardListing(cards=(), issues=())
        picker = TemplateCardPicker(TemplateCardContext.REFERENCE, "new-reference", self.page.update)
        picker.refresh(listing.for_type(NoteType.REFERENCE), listing.issues)
        name_field = ft.TextField(
            label=afanes.ui.strings.BROWSER_NAME_LABEL,
            autofocus=True,
            key="new-reference-name",
        )
        submit_button = ft.FilledButton(
            content=afanes.ui.strings.BROWSER_CREATE_ACTION,
            disabled=True,
            key="new-reference-submit",
        )
        error = ft.Text(
            "",
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            visible=False,
            key="new-reference-error",
        )

        async def submit() -> None:
            name = (name_field.value or "").strip()
            if not name:
                self._show_create_error(error, afanes.ui.strings.BROWSER_NAME_REQUIRED)
                return
            card = picker.selected_card
            category = card.category if card is not None and card.category is not None else CategoryLabel("general")
            scaffold = card.body if card is not None and card.body.strip() else None
            if not await self.state.navigation.create_reference(name, category, scaffold):
                self._show_create_error(error, self.state.status.message or afanes.ui.strings.BROWSER_NAME_REQUIRED)
                return
            self.page.pop_dialog()
            self.page.update()
            self._refresh_current_workspace()

        async def cancel() -> None:
            self.page.pop_dialog()
            self.page.update()

        submit_button.on_click = submit
        name_field.on_change = lambda: self._refresh_dialog_submit(name_field, submit_button)
        name_field.on_submit = submit
        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text(afanes.ui.strings.BROWSER_NEW_REFERENCE_TITLE),
                content=ft.Column(
                    controls=[
                        ft.Text(afanes.ui.strings.BROWSER_NEW_REFERENCE_BODY),
                        name_field,
                        picker.dropdown,
                        picker.description,
                        picker.warning,
                        error,
                    ],
                    tight=True,
                ),
                actions=[
                    ft.TextButton(
                        content=afanes.ui.strings.CANCEL_ACTION,
                        on_click=cancel,
                        key="new-reference-cancel",
                    ),
                    submit_button,
                ],
            ),
        )
        self.page.update()

    async def show_role_reference_dialog(self, name: str) -> None:
        """Ask where to file a reference created from a missing role name.

        Parameters
        ----------
        name : str
            Written owner, requester, or step owner name.

        Notes
        -----
        Existing reference categories are offered as suggestions, and a free
        typed label or no category is accepted. Confirming creates the note
        atomically through the navigation command and opens it in edit mode.
        Cancelling writes nothing.
        """

        async def confirm(category: CategoryLabel | None) -> None:
            if not await self.state.navigation.create_role_reference(name, category):
                return
            self.page.pop_dialog()
            self.page.update()
            self._refresh_current_workspace()

        async def cancel() -> None:
            self.page.pop_dialog()
            self.page.update()

        ordered = await self.state.browser.role_categories()
        dialog = RoleReferenceDialog(name, ordered, confirm, cancel)
        self.page.show_dialog(dialog.dialog)
        self.page.update()

    async def pick_role(self, role: str, current: str | None) -> str | None:
        """Ask for an owner or requester name from read mode.

        Parameters
        ----------
        role : str
            ``owner`` or ``asked_by``; selects the dialog title.
        current : str | None
            Current written name, or ``None`` when the role is empty.

        Returns
        -------
        str | None
            Selected or typed name, an empty string when the role is cleared,
            or ``None`` when the dialog was cancelled.

        Notes
        -----
        The dialog offers every note name in the ``note:`` namespace as a
        suggestion and accepts a new name. It writes nothing itself; the page
        view saves the returned value.
        """
        loop = asyncio.get_running_loop()
        result: asyncio.Future[str | None] = loop.create_future()

        def settle(value: str | None) -> None:
            if not result.done():
                result.set_result(value)

        async def save(text: str) -> None:
            settle(text)

        async def cancel() -> None:
            settle(None)

        async def dismiss(_event: object = None) -> None:
            settle(None)

        names = [note.name for note in self.state.session.assignment_candidates(ReferenceScheme.NOTE, "")]
        title = (
            afanes.ui.strings.ROLE_NAME_OWNER_TITLE if role == "owner" else afanes.ui.strings.ROLE_NAME_ASKED_BY_TITLE
        )
        dialog = RoleNameDialog(title, current, names, save, cancel)
        dialog.dialog.on_dismiss = dismiss
        self.page.show_dialog(dialog.dialog)
        self.page.update()
        try:
            return await result
        finally:
            self.page.pop_dialog()
            self.page.update()

    async def show_log_entry_dialog(self, date: NoteDate) -> None:
        """Open or create the log entry for one date.

        Parameters
        ----------
        date : NoteDate
            Entry date selected in the Log calendar or date tree.

        Notes
        -----
        An occupied date opens its entry without showing a form. An empty date
        shows a title-and-card form, writes the entry through the navigation
        command, and opens it in edit mode. A blank title or a write failure is
        reported inline and the dialog stays open.
        """
        snapshot = self.state.session.snapshot
        existing = snapshot.log_entry(date) if snapshot is not None else None
        if existing is not None:
            await self.state.navigation.open_or_create_log_entry(date, "", None)
            await self.render()
            return

        listing = await self.state.session.template_cards()
        if listing is None:
            listing = TemplateCardListing(cards=(), issues=())
        picker = TemplateCardPicker(TemplateCardContext.LOG, "new-log", self.page.update)
        picker.refresh(listing.for_type(NoteType.LOG), listing.issues)
        title_field = ft.TextField(
            label=afanes.ui.strings.LOG_TITLE_LABEL,
            autofocus=True,
            key="new-log-title",
        )
        error = ft.Text(
            "",
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            visible=False,
            key="new-log-error",
        )

        async def submit() -> None:
            title = (title_field.value or "").strip()
            if not title:
                self._show_create_error(error, afanes.ui.strings.LOG_TITLE_REQUIRED)
                return
            card = picker.selected_card
            scaffold = card.body if card is not None and card.body.strip() else None
            if not await self.state.navigation.open_or_create_log_entry(date, title, scaffold):
                self._show_create_error(
                    error,
                    self.state.status.message or afanes.ui.strings.LOG_TITLE_REQUIRED,
                )
                return
            self.page.pop_dialog()
            self.page.update()
            self._refresh_current_workspace()

        async def cancel() -> None:
            self.page.pop_dialog()
            self.page.update()

        title_field.on_submit = submit
        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text(afanes.ui.strings.LOG_ENTRY_TITLE),
                content=ft.Column(
                    controls=[
                        ft.Text(afanes.ui.strings.LOG_ENTRY_BODY.format(date=date.text)),
                        title_field,
                        picker.dropdown,
                        picker.description,
                        picker.warning,
                        error,
                    ],
                    tight=True,
                ),
                actions=[
                    ft.TextButton(
                        content=afanes.ui.strings.CANCEL_ACTION,
                        on_click=cancel,
                        key="new-log-cancel",
                    ),
                    ft.FilledButton(
                        content=afanes.ui.strings.LOG_CREATE_ACTION,
                        on_click=submit,
                        key="new-log-submit",
                    ),
                ],
            ),
        )
        self.page.update()

    def show_vault_dialog(self) -> None:
        """Ask for a vault path in a dialog, for a browser session."""
        field = ft.TextField(
            label=afanes.ui.strings.WELCOME_PATH_LABEL,
            hint_text=afanes.ui.strings.WELCOME_PATH_HINT,
            value="" if self.state.session.vault_root is None else str(self.state.session.vault_root),
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
