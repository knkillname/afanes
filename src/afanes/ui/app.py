# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Flet application shell and first-run routing."""

import asyncio
import contextlib
import datetime
from pathlib import Path

import flet as ft

import afanes.core.vault.service
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
import afanes.ui.views.inbox
import afanes.ui.views.workspace
from afanes.core.template_cards import TemplateCard, TemplateCardListing
from afanes.models.note import CategoryLabel, NoteDate, NoteType

# Public task name so the shell can be observed without exposing its fields.
REFRESH_TASK_NAME = "workspace-refresh"


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
        self.workspace: afanes.ui.views.workspace.WorkspaceView | None = None
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
        self.page.theme = afanes.ui.theme.THEME
        self.page.dark_theme = afanes.ui.theme.THEME
        self.page.bgcolor = afanes.ui.theme.PAGE_SURFACE_COLOR
        self.page.padding = afanes.ui.theme.PAGE_PADDING
        self.page.on_disconnect = self.release_session
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

    async def render(self) -> None:
        """Render the welcome state or the workspace for the current session."""
        await self._stop_refresh_loop()
        self.workspace = None
        self.page.controls.clear()
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
                self.page.update,
                self.choose_vault,
                self.create_vault,
                self.close_vault,
                on_new_reference=self.show_new_reference_dialog,
                pick_date=self.pick_date,
                on_log_entry=self.show_log_entry_dialog,
            )
            self.workspace = workspace
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
        selected = await self.picker.get_directory_path(dialog_title=afanes.ui.strings.WELCOME_CHOOSE)
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
        folders = ", ".join(f"{folder.as_posix()}/" for folder in afanes.core.vault.service.Vault.default_layout())
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
            if not await self.state.workspace.create_vault(Path(text), template=selector.value or None):
                self._show_create_error(error, self.state.status.message or afanes.ui.strings.VAULT_PATH_REQUIRED)
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
        choices, options = self._reference_template_options(listing.for_type(NoteType.REFERENCE))
        name_field = ft.TextField(
            label=afanes.ui.strings.BROWSER_NAME_LABEL,
            autofocus=True,
            key="new-reference-name",
        )
        selector = ft.Dropdown(
            label=afanes.ui.strings.BROWSER_TEMPLATE_LABEL,
            options=options,
            value="empty",
            key="new-reference-template",
        )
        description = ft.Text(
            afanes.ui.strings.BROWSER_TEMPLATE_DESCRIPTION_EMPTY,
            size=12,
            color=afanes.ui.theme.MUTED_TEXT_COLOR,
            selectable=True,
        )
        warning = ft.Text(
            afanes.ui.strings.BROWSER_TEMPLATE_INVALID.format(
                paths=", ".join(issue.relative_path.as_posix() for issue in listing.issues)
            ),
            color=afanes.ui.theme.ERROR_COLOR,
            visible=bool(listing.issues),
            key="new-reference-template-warning",
        )
        error = ft.Text(
            "",
            color=afanes.ui.theme.ERROR_COLOR,
            visible=False,
            key="new-reference-error",
        )

        def refresh_description(_event: object = None) -> None:
            card = choices.get(selector.value or "empty")
            if card is None or not card.description:
                description.value = (
                    afanes.ui.strings.BROWSER_TEMPLATE_DESCRIPTION_EMPTY
                    if card is None
                    else afanes.ui.strings.BROWSER_TEMPLATE_NO_DESCRIPTION
                )
            else:
                description.value = card.description
            self.page.update()

        selector.on_select = refresh_description

        async def submit() -> None:
            name = (name_field.value or "").strip()
            if not name:
                self._show_create_error(error, afanes.ui.strings.BROWSER_NAME_REQUIRED)
                return
            card = choices.get(selector.value or "empty")
            category = card.category if card is not None and card.category is not None else CategoryLabel("general")
            scaffold = card.body if card is not None and card.body.strip() else None
            if not await self.state.navigation.create_reference(name, category, scaffold):
                self._show_create_error(error, self.state.status.message or afanes.ui.strings.BROWSER_NAME_REQUIRED)
                return
            self.page.pop_dialog()
            await self.render()

        async def cancel() -> None:
            self.page.pop_dialog()
            self.page.update()

        name_field.on_submit = submit
        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text(afanes.ui.strings.BROWSER_NEW_REFERENCE_TITLE),
                content=ft.Column(
                    controls=[
                        ft.Text(afanes.ui.strings.BROWSER_NEW_REFERENCE_BODY),
                        name_field,
                        selector,
                        description,
                        warning,
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
                    ft.FilledButton(
                        content=afanes.ui.strings.BROWSER_CREATE_ACTION,
                        on_click=submit,
                        key="new-reference-submit",
                    ),
                ],
            ),
        )
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
        choices, options = self._reference_template_options(listing.for_type(NoteType.LOG))
        title_field = ft.TextField(
            label=afanes.ui.strings.LOG_TITLE_LABEL,
            autofocus=True,
            key="new-log-title",
        )
        selector = ft.Dropdown(
            label=afanes.ui.strings.LOG_CARD_LABEL,
            options=options,
            value="empty",
            key="new-log-template",
        )
        description = ft.Text(
            afanes.ui.strings.LOG_CARD_DESCRIPTION_EMPTY,
            size=12,
            color=afanes.ui.theme.MUTED_TEXT_COLOR,
            selectable=True,
        )
        warning = ft.Text(
            afanes.ui.strings.BROWSER_TEMPLATE_INVALID.format(
                paths=", ".join(issue.relative_path.as_posix() for issue in listing.issues)
            ),
            color=afanes.ui.theme.ERROR_COLOR,
            visible=bool(listing.issues),
            key="new-log-template-warning",
        )
        error = ft.Text(
            "",
            color=afanes.ui.theme.ERROR_COLOR,
            visible=False,
            key="new-log-error",
        )

        def refresh_description(_event: object = None) -> None:
            card = choices.get(selector.value or "empty")
            if card is None or not card.description:
                description.value = (
                    afanes.ui.strings.LOG_CARD_DESCRIPTION_EMPTY
                    if card is None
                    else afanes.ui.strings.BROWSER_TEMPLATE_NO_DESCRIPTION
                )
            else:
                description.value = card.description
            self.page.update()

        selector.on_select = refresh_description

        async def submit() -> None:
            title = (title_field.value or "").strip()
            if not title:
                self._show_create_error(error, afanes.ui.strings.LOG_TITLE_REQUIRED)
                return
            card = choices.get(selector.value or "empty")
            scaffold = card.body if card is not None and card.body.strip() else None
            if not await self.state.navigation.open_or_create_log_entry(date, title, scaffold):
                self._show_create_error(
                    error,
                    self.state.status.message or afanes.ui.strings.LOG_TITLE_REQUIRED,
                )
                return
            self.page.pop_dialog()
            await self.render()

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
                        selector,
                        description,
                        warning,
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

    @staticmethod
    def _reference_template_options(
        cards: tuple[TemplateCard, ...],
    ) -> tuple[dict[str, TemplateCard | None], list[ft.dropdown.Option]]:
        """Build the dialog's template choices and their display options.

        Parameters
        ----------
        cards : tuple[TemplateCard, ...]
            Valid cards read from the vault.

        Returns
        -------
        tuple[dict[str, TemplateCard | None], list[flet.dropdown.Option]]
            Lookup from option key to card, with ``empty`` mapped to ``None``,
            and the options in the same order with Empty last.
        """
        counts: dict[str, int] = {}
        for card in cards:
            counts[card.title.casefold()] = counts.get(card.title.casefold(), 0) + 1
        choices: dict[str, TemplateCard | None] = {}
        options: list[ft.dropdown.Option] = []
        for card in cards:
            key = f"card:{card.relative_path.as_posix()}"
            choices[key] = card
            options.append(ft.dropdown.Option(key=key, text=_Shell._reference_template_text(card, counts)))
        choices["empty"] = None
        options.append(ft.dropdown.Option(key="empty", text=afanes.ui.strings.BROWSER_TEMPLATE_EMPTY))
        return choices, options

    @staticmethod
    def _reference_template_text(card: TemplateCard, counts: dict[str, int]) -> str:
        """Return the display text for one browser template option."""
        duplicate = counts[card.title.casefold()] > 1
        if card.description:
            if duplicate:
                return afanes.ui.strings.BROWSER_TEMPLATE_OPTION_DUPLICATE.format(
                    title=card.title,
                    description=card.description,
                    path=card.relative_path.as_posix(),
                )
            return afanes.ui.strings.BROWSER_TEMPLATE_OPTION.format(
                title=card.title,
                description=card.description,
            )
        if duplicate:
            return afanes.ui.strings.BROWSER_TEMPLATE_OPTION_DUPLICATE_PLAIN.format(
                title=card.title,
                path=card.relative_path.as_posix(),
            )
        return afanes.ui.strings.BROWSER_TEMPLATE_OPTION_PLAIN.format(title=card.title)

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
