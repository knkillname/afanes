# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read, edit, and raw rescue modes for the page pane.

The view renders the shared application state and forwards intent to its
commands. It performs no Markdown parsing, SQL, or file I/O. Confirmation
flows are inline panels so the pane stays usable without a rendered dialog.
"""

from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
from afanes.core.editing import DraftMode, PageDraft
from afanes.core.vault import VaultNote
from afanes.models.link import ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory, Status
from afanes.ui.components.banner import Banner
from afanes.ui.components.panel import Panel


class PageView:
    """Read, edit, and raw rescue modes for one note.

    Parameters
    ----------
    update : Callable[[], None]
        Requests a repaint of the page.
    on_process : Callable[[Path], Awaitable[None]] | None
        Command that opens the Processing Wizard for an Inbox capture, or
        ``None`` when processing is unavailable.
    """

    def __init__(
        self,
        update: Callable[[], None],
        on_process: Callable[[Path], Awaitable[None]] | None = None,
    ) -> None:
        """Build the page controls against the shared application state.

        Parameters
        ----------
        update : Callable[[], None]
            Requests a repaint of the page.
        on_process : Callable[[Path], Awaitable[None]] | None
            Command that opens the Processing Wizard for an Inbox capture.
        """
        self._state = afanes.ui.state.app_state
        self._update = update
        self._on_process = on_process
        self._suppress_suggestions = False
        self._rename_open = False

        self.back_button = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip=afanes.ui.strings.PAGE_BACK,
            on_click=self.go_back,
        )
        self.title = ft.Text("", theme_style=ft.TextThemeStyle.HEADLINE_SMALL)
        self.path = ft.Text(
            "",
            size=12,
            color=afanes.ui.theme.MUTED_TEXT_COLOR,
            selectable=True,
        )
        self.progress = ft.ProgressRing(
            width=16,
            height=16,
            visible=False,
            semantics_label=afanes.ui.strings.WORKING,
        )
        self.status_text = ft.Text(
            "",
            size=12,
            color=afanes.ui.theme.MUTED_TEXT_COLOR,
        )
        self.process_button = ft.TextButton(
            content=afanes.ui.strings.PROCESS_ACTION,
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.process_current,
            visible=False,
            key="process-note",
        )
        self.edit_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_EDIT,
            icon=ft.Icons.EDIT,
            on_click=self.start_edit,
        )
        self.done_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_DONE,
            icon=ft.Icons.CHECK,
            on_click=self.finish_edit,
            visible=False,
        )
        self.rename_button = ft.TextButton(
            content=afanes.ui.strings.PAGE_RENAME,
            icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE,
            on_click=self.begin_rename,
        )
        self.trash_button = ft.TextButton(
            content=afanes.ui.strings.PAGE_TRASH,
            icon=ft.Icons.DELETE_OUTLINE,
            on_click=self.begin_trash,
        )
        self.header = ft.Row(
            controls=[
                self.back_button,
                ft.Column(controls=[self.title, self.path], spacing=0, expand=True),
                self.progress,
                self.status_text,
                self.process_button,
                self.edit_button,
                self.done_button,
                self.rename_button,
                self.trash_button,
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.banners = ft.Column(controls=[], spacing=afanes.ui.theme.ITEM_GAP)
        self.empty_text = ft.Text(
            afanes.ui.strings.PAGE_EMPTY,
            color=afanes.ui.theme.MUTED_TEXT_COLOR,
        )
        self.read_body = ft.Markdown(
            value="",
            selectable=True,
            auto_follow_links=False,
            on_tap_link=self.handle_link,
        )

        self.identity_text = ft.Text("", selectable=True, size=12, color=afanes.ui.theme.MUTED_TEXT_COLOR)
        self.body_field = ft.TextField(
            label=afanes.ui.strings.PAGE_BODY_LABEL,
            multiline=True,
            min_lines=afanes.ui.theme.PAGE_BODY_MIN_LINES,
            max_lines=None,
            on_change=self.change_body,
        )
        self.type_dropdown = ft.Dropdown(
            label=afanes.ui.strings.PAGE_TYPE_LABEL,
            options=[
                ft.dropdown.Option(key=note_type.value, text=afanes.ui.strings.PAGE_TYPE_LABELS[note_type.value])
                for note_type in NoteType
            ],
            on_select=self.change_type,
            width=afanes.ui.theme.PAGE_FIELD_WIDTH,
        )
        self.category_dropdown = ft.Dropdown(
            label=afanes.ui.strings.PAGE_CATEGORY_LABEL,
            options=[
                ft.dropdown.Option(key="", text=afanes.ui.strings.PAGE_NONE),
                *[
                    ft.dropdown.Option(key=category.value, text=label)
                    for category, label in (
                        (ReferenceCategory.PERSON, afanes.ui.strings.PAGE_CATEGORY_LABELS["person"]),
                    )
                ],
            ],
            on_select=self.change_category,
            width=afanes.ui.theme.PAGE_FIELD_WIDTH,
        )
        self.status_dropdown = ft.Dropdown(
            label=afanes.ui.strings.PAGE_STATUS_LABEL,
            options=[],
            on_select=self.change_status,
            width=afanes.ui.theme.PAGE_FIELD_WIDTH,
        )
        self.due_field = ft.TextField(
            label=afanes.ui.strings.PAGE_DUE_DATE_LABEL,
            hint_text="2026-11-20",
            on_change=self.change_due_date,
            width=afanes.ui.theme.PAGE_DUE_WIDTH,
        )
        self.due_error = ft.Text(
            "",
            size=12,
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            visible=False,
            selectable=True,
        )
        self.people_field = ft.TextField(
            label=afanes.ui.strings.PAGE_PEOPLE_LABEL,
            hint_text="Ada, Grace",
            on_change=self.change_people,
            width=afanes.ui.theme.PAGE_NAME_WIDTH,
        )
        self.people_suggestions = ft.Column(controls=[], spacing=0, visible=False)
        self.project_field = ft.TextField(
            label=afanes.ui.strings.PAGE_PROJECT_LABEL,
            hint_text="Release 1.0",
            on_change=self.change_project,
            width=afanes.ui.theme.PAGE_NAME_WIDTH,
        )
        self.project_suggestions = ft.Column(controls=[], spacing=0, visible=False)
        self.edit_form = ft.Column(
            controls=[
                self.identity_text,
                ft.Row(
                    controls=[self.type_dropdown, self.category_dropdown, self.status_dropdown],
                    spacing=afanes.ui.theme.ITEM_GAP,
                    wrap=True,
                ),
                ft.Row(controls=[self.due_field], spacing=afanes.ui.theme.ITEM_GAP, wrap=True),
                self.due_error,
                self.people_field,
                self.people_suggestions,
                self.project_field,
                self.project_suggestions,
                self.body_field,
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
            visible=False,
        )

        self.raw_warning = ft.Text(
            afanes.ui.strings.PAGE_RAW_WARNING,
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            selectable=True,
        )
        self.raw_field = ft.TextField(
            label=afanes.ui.strings.PAGE_BODY_LABEL,
            multiline=True,
            min_lines=afanes.ui.theme.PAGE_RAW_MIN_LINES,
            max_lines=None,
            on_change=self.change_raw_text,
        )
        self.raw_save_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_RAW_SAVE,
            icon=ft.Icons.SAVE,
            on_click=self.save_raw,
        )
        self.raw_panel = ft.Column(
            controls=[self.raw_warning, self.raw_field, self.raw_save_button],
            spacing=afanes.ui.theme.ITEM_GAP,
            visible=False,
        )

        self.conflict_text = ft.Text("", selectable=True)
        self.reload_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_CONFLICT_RELOAD,
            icon=ft.Icons.SYNC,
            on_click=self.reload_page,
        )
        self.overwrite_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_CONFLICT_OVERWRITE,
            icon=ft.Icons.SAVE,
            on_click=self.overwrite_page,
        )
        self.recreate_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_CONFLICT_RECREATE,
            icon=ft.Icons.ADD,
            on_click=self.recreate_page,
        )
        self.discard_button = ft.TextButton(
            content=afanes.ui.strings.PAGE_CONFLICT_DISCARD,
            on_click=self.discard_draft,
        )
        self.conflict_panel = Panel(
            afanes.ui.strings.PAGE_CONFLICT_TITLE,
            self.conflict_text,
            [self.reload_button, self.overwrite_button, self.recreate_button, self.discard_button],
        ).build()
        self.conflict_panel.visible = False

        self.ambiguous_list = ft.Column(controls=[], spacing=0)
        self.ambiguous_cancel_button = ft.TextButton(
            content=afanes.ui.strings.PAGE_CANCEL,
            on_click=self.clear_ambiguous,
        )
        self.ambiguous_panel = Panel(
            afanes.ui.strings.PAGE_AMBIGUOUS_TITLE,
            ft.Column(
                controls=[
                    ft.Text(afanes.ui.strings.PAGE_AMBIGUOUS_BODY, selectable=True),
                    self.ambiguous_list,
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
            [self.ambiguous_cancel_button],
        ).build()
        self.ambiguous_panel.visible = False

        self.repair_text = ft.Text("", selectable=True)
        self.repair_rewrite_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_REPAIR_REWRITE,
            icon=ft.Icons.LINK,
            on_click=self.rewrite_links,
        )
        self.repair_keep_button = ft.TextButton(
            content=afanes.ui.strings.PAGE_REPAIR_KEEP,
            on_click=self.keep_links,
        )
        self.repair_cancel_button = ft.TextButton(
            content=afanes.ui.strings.PAGE_REPAIR_CANCEL,
            on_click=self.cancel_repair,
        )
        self.repair_panel = Panel(
            afanes.ui.strings.PAGE_REPAIR_TITLE,
            self.repair_text,
            [self.repair_rewrite_button, self.repair_keep_button, self.repair_cancel_button],
        ).build()
        self.repair_panel.visible = False

        self.type_change_text = ft.Text("", selectable=True)
        self.type_change_confirm_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_TYPE_CHANGE_CONFIRM,
            icon=ft.Icons.CHECK,
            on_click=self.confirm_type_change,
        )
        self.type_change_cancel_button = ft.TextButton(
            content=afanes.ui.strings.PAGE_CANCEL,
            on_click=self.cancel_type_change,
        )
        self.type_change_panel = Panel(
            afanes.ui.strings.PAGE_TYPE_CHANGE_TITLE,
            self.type_change_text,
            [self.type_change_confirm_button, self.type_change_cancel_button],
        ).build()
        self.type_change_panel.visible = False

        self.rename_field = ft.TextField(
            label=afanes.ui.strings.PAGE_RENAME_LABEL,
            width=afanes.ui.theme.PAGE_RENAME_WIDTH,
        )
        self.rename_preview_text = ft.Text("", selectable=True)
        self.rename_preview_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_RENAME,
            icon=ft.Icons.VISIBILITY,
            on_click=self.preview_rename,
        )
        self.rename_confirm_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_RENAME_CONFIRM,
            icon=ft.Icons.CHECK,
            on_click=self.confirm_rename,
        )
        self.rename_cancel_button = ft.TextButton(
            content=afanes.ui.strings.PAGE_CANCEL,
            on_click=self.cancel_rename,
        )
        self.rename_panel = ft.Container(
            bgcolor=afanes.ui.theme.SURFACE_CONTAINER_COLOR,
            border_radius=afanes.ui.theme.CARD_RADIUS,
            padding=afanes.ui.theme.ITEM_GAP,
            visible=False,
            content=ft.Column(
                controls=[
                    ft.Text(afanes.ui.strings.PAGE_RENAME_TITLE, theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                    self.rename_field,
                    self.rename_preview_text,
                    ft.Row(
                        controls=[self.rename_preview_button, self.rename_confirm_button, self.rename_cancel_button],
                        spacing=afanes.ui.theme.ITEM_GAP,
                        wrap=True,
                    ),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
        )

        self.trash_text = ft.Text("", selectable=True)
        self.trash_confirm_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_TRASH_CONFIRM,
            icon=ft.Icons.DELETE_OUTLINE,
            on_click=self.confirm_trash,
        )
        self.trash_cancel_button = ft.TextButton(
            content=afanes.ui.strings.PAGE_CANCEL,
            on_click=self.cancel_trash,
        )
        self.trash_panel = Panel(
            afanes.ui.strings.PAGE_TRASH_TITLE,
            self.trash_text,
            [self.trash_confirm_button, self.trash_cancel_button],
        ).build()
        self.trash_panel.visible = False

        self.dialogs = ft.Column(
            controls=[
                self.conflict_panel,
                self.ambiguous_panel,
                self.repair_panel,
                self.type_change_panel,
                self.rename_panel,
                self.trash_panel,
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
        )
        self.content = ft.Column(
            controls=[self.empty_text, self.read_body, self.edit_form, self.raw_panel],
            spacing=afanes.ui.theme.ITEM_GAP,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        self.root = ft.Container(
            expand=True,
            padding=afanes.ui.theme.ITEM_GAP,
            bgcolor=afanes.ui.theme.SURFACE_CONTAINER_COLOR,
            border_radius=afanes.ui.theme.CARD_RADIUS,
            content=ft.Column(
                controls=[self.header, ft.Divider(), self.banners, self.dialogs, self.content],
                spacing=afanes.ui.theme.ITEM_GAP,
                expand=True,
            ),
        )
        self.refresh()

    def build(self) -> ft.Control:
        """Return the root control for the page pane.

        Returns
        -------
        ft.Control
            Composed read, edit, and raw rescue layout.
        """
        return self.root

    async def handle_link(self, event: ft.Event[ft.Markdown]) -> None:
        """Route a tapped Markdown link.

        Parameters
        ----------
        event : ft.Event[ft.Markdown]
            Tap event whose ``data`` is the destination string.
        """
        destination = event.data
        if isinstance(destination, str):
            await self.follow(destination)

    async def follow(self, destination: str) -> None:
        """Forward one link destination to the application state.

        Parameters
        ----------
        destination : str
            Destination exactly as written in the link.
        """
        await self._state.follow_link(destination)
        self.refresh()
        self._update()

    def refresh(self) -> None:
        """Refresh every control from the shared application state."""
        page = self._state.page
        editing = self._state.editing or self._state.page_mode is DraftMode.RAW
        self._refresh_header(page, editing=editing)
        self._refresh_read(page, editing=editing)
        self._refresh_edit(page, editing=editing)
        self._refresh_raw(page)
        self._refresh_banners()
        self._refresh_conflict()
        self._refresh_ambiguity()
        self._refresh_repair()
        self._refresh_type_change()
        self._refresh_rename()
        self._refresh_trash()

    def _refresh_header(self, page: PageDraft | None, *, editing: bool) -> None:
        """Refresh the header, mode buttons, and write status."""
        state = self._state
        self.title.value = state.page_title if page is not None else ""
        self.path.value = state.page_path_label
        self.back_button.disabled = page is None and not state.history
        self.edit_button.visible = page is not None and not editing and self._state.page_mode is DraftMode.NORMAL
        self.done_button.visible = page is not None and editing
        self.rename_button.visible = page is not None and not editing and self._state.page_mode is DraftMode.NORMAL
        self.trash_button.visible = page is not None and not editing
        self.process_button.visible = page is not None and not editing and self._is_inbox_page(page)
        self.progress.visible = state.busy or state.saving
        if state.saving:
            self.status_text.value = afanes.ui.strings.PAGE_SAVING
        elif page is not None and editing and state.page_is_dirty:
            self.status_text.value = afanes.ui.strings.PAGE_UNSAVED
        else:
            self.status_text.value = ""

    def _refresh_read(self, page: PageDraft | None, *, editing: bool) -> None:
        """Refresh the rendered read mode."""
        state = self._state
        visible = page is not None and not editing
        self.empty_text.visible = page is None
        self.read_body.visible = visible
        if visible and page is not None:
            self.read_body.value = state.page_body

    def _refresh_edit(self, page: PageDraft | None, *, editing: bool) -> None:
        """Refresh the body field and label form."""
        state = self._state
        labels = state.page_labels if page is not None else None
        visible = page is not None and editing and state.page_mode is DraftMode.NORMAL and labels is not None
        self.edit_form.visible = visible
        if not visible or page is None or labels is None:
            self._clear_suggestions(self.people_suggestions)
            self._clear_suggestions(self.project_suggestions)
            return

        body = state.page_body
        if self.body_field.value != body:
            self.body_field.value = body
        self.identity_text.value = f"{afanes.ui.strings.PAGE_IDENTITY_LABEL}: {page.identity}"
        self.type_dropdown.value = labels.note_type.value
        self.category_dropdown.visible = labels.note_type is NoteType.REFERENCE
        self.category_dropdown.value = labels.category.value if labels.category is not None else ""
        allowed = labels.note_type.allowed_statuses
        self.status_dropdown.options = [
            ft.dropdown.Option(key="", text=afanes.ui.strings.PAGE_NONE),
            *[
                ft.dropdown.Option(
                    key=status.value,
                    text=afanes.ui.strings.PROCESSING_STATUS_LABELS[status.value],
                )
                for status in Status
                if status in allowed
            ],
        ]
        self.status_dropdown.visible = bool(allowed)
        self.status_dropdown.value = labels.status.value if labels.status is not None else ""
        if self.due_field.value != labels.due_date_text:
            self.due_field.value = labels.due_date_text
        self.due_error.value = labels.due_date_error or ""
        self.due_error.visible = labels.due_date_error is not None
        people_text = ", ".join(labels.people)
        if self.people_field.value != people_text:
            self.people_field.value = people_text
        project_text = labels.project or ""
        if self.project_field.value != project_text:
            self.project_field.value = project_text
        self._refresh_suggestions()

    def _refresh_raw(self, page: PageDraft | None) -> None:
        """Refresh raw rescue mode."""
        state = self._state
        visible = page is not None and state.page_mode is DraftMode.RAW
        self.raw_panel.visible = visible
        if visible and page is not None and self.raw_field.value != state.page_raw_text:
            self.raw_field.value = state.page_raw_text
        self.raw_save_button.disabled = self._state.busy or self._state.saving

    def _refresh_banners(self) -> None:
        """Refresh the message banner."""
        message = self._state.message
        self.banners.controls = [] if message is None else [Banner(message).build()]
        self.banners.visible = message is not None

    def _refresh_conflict(self) -> None:
        """Refresh the conflict recovery panel."""
        conflict = self._state.conflict
        self.conflict_panel.visible = conflict is not None
        changed = conflict == "changed"
        self.conflict_text.value = (
            afanes.ui.strings.PAGE_CONFLICT_CHANGED if changed else afanes.ui.strings.PAGE_CONFLICT_MISSING
        )
        self.reload_button.visible = changed
        self.overwrite_button.visible = changed
        self.recreate_button.visible = not changed
        self.discard_button.visible = True

    def _refresh_ambiguity(self) -> None:
        """Refresh the candidate picker."""
        state = self._state
        self.ambiguous_panel.visible = bool(state.ambiguous)
        self.ambiguous_list.controls = [
            ft.ListTile(
                title=state.note_title(path),
                subtitle=path.as_posix(),
                dense=True,
                on_click=self._candidate_handler(path),
            )
            for path in state.ambiguous
        ]

    def _refresh_repair(self) -> None:
        """Refresh the unsafe-reference repair panel."""
        preview = self._state.repair_preview
        self.repair_panel.visible = preview is not None
        if preview is None:
            return
        count = sum(site.reference_count for site in preview.sites)
        notes = len(preview.sites)
        self.repair_text.value = (
            afanes.ui.strings.PAGE_REPAIR_BODY.format(old=preview.old.name, new=preview.new.name)
            + " "
            + afanes.ui.strings.PAGE_REPAIR_COUNT.format(detail=afanes.ui.strings.reference_count(count, notes))
        )

    def _refresh_type_change(self) -> None:
        """Refresh the scheme-change confirmation panel."""
        labels = self._state.pending_labels
        sites = self._state.type_change_sites
        self.type_change_panel.visible = labels is not None and bool(sites)
        if labels is None or not sites:
            return
        count = sum(site.reference_count for site in sites)
        self.type_change_text.value = afanes.ui.strings.PAGE_TYPE_CHANGE_BODY.format(
            detail=afanes.ui.strings.reference_count(count, len(sites))
        )

    def _refresh_rename(self) -> None:
        """Refresh the rename panel."""
        preview = self._state.rename_preview
        self.rename_panel.visible = self._rename_open or preview is not None
        self.rename_field.visible = preview is None
        self.rename_preview_button.visible = preview is None
        self.rename_confirm_button.visible = preview is not None
        if preview is None:
            self.rename_preview_text.value = ""
            return
        count = preview.reference_count
        self.rename_preview_text.value = afanes.ui.strings.PAGE_RENAME_PREVIEW.format(
            detail=afanes.ui.strings.reference_count(count, len(preview.affected))
        )

    def _refresh_trash(self) -> None:
        """Refresh the trash confirmation panel."""
        preview = self._state.trash_preview
        self.trash_panel.visible = preview is not None
        if preview is None:
            return
        self.trash_text.value = afanes.ui.strings.PAGE_TRASH_BODY.format(
            path=preview.trash_path,
            detail=afanes.ui.strings.reference_count(preview.reference_count, len(preview.affected_notes)),
        )

    def _refresh_suggestions(self) -> None:
        """Refresh assignment suggestions from the retained vault snapshot."""
        if self._suppress_suggestions:
            self._clear_suggestions(self.people_suggestions)
            self._clear_suggestions(self.project_suggestions)
            return
        self._render_suggestions(
            self.people_suggestions,
            ReferenceScheme.PERSON,
            self._active_people_token(),
            apply_text=self._apply_people_suggestion,
            apply_state=self._apply_people_state,
        )
        self._render_suggestions(
            self.project_suggestions,
            ReferenceScheme.PROJECT,
            (self.project_field.value or "").strip(),
            apply_text=self._apply_project_suggestion,
            apply_state=self._apply_project_state,
        )

    def _render_suggestions(
        self,
        column: ft.Column,
        scheme: ReferenceScheme,
        query: str,
        *,
        apply_text: Callable[[str], None],
        apply_state: Callable[[str], Awaitable[None]],
    ) -> None:
        """Fill one suggestion list from the active field text."""
        if not query:
            self._clear_suggestions(column)
            return
        candidates = self._state.assignment_candidates(scheme, query)
        column.controls = [self._suggestion_tile(note, apply_text, apply_state) for note in candidates]
        column.visible = bool(column.controls)

    @staticmethod
    def _clear_suggestions(column: ft.Column) -> None:
        """Empty one suggestion list and hide it."""
        column.controls = []
        column.visible = False

    def _suggestion_tile(
        self,
        note: VaultNote,
        apply_text: Callable[[str], None],
        apply_state: Callable[[str], Awaitable[None]],
    ) -> ft.Control:
        """Build one selectable assignment suggestion."""
        subtitle = note.name if note.name != note.title else None
        return ft.ListTile(
            title=note.title,
            subtitle=subtitle,
            dense=True,
            on_click=self._suggestion_handler(note.name, apply_text, apply_state),
        )

    def _suggestion_handler(
        self,
        identity: str,
        apply_text: Callable[[str], None],
        apply_state: Callable[[str], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async selection handler to one page identity."""

        async def handle() -> None:
            self._suppress_suggestions = True
            try:
                apply_text(identity)
                await apply_state(identity)
            finally:
                self._suppress_suggestions = False
            self.refresh()
            self._update()

        return handle

    def _active_people_token(self) -> str:
        """Return the token after the last comma in the people field."""
        return (self.people_field.value or "").rsplit(",", 1)[-1].strip()

    def _apply_people_suggestion(self, identity: str) -> None:
        """Replace the active people token with a page identity."""
        value = self.people_field.value or ""
        head, separator, _ = value.rpartition(",")
        self.people_field.value = f"{head.rstrip()}, {identity}" if separator else identity

    async def _apply_people_state(self, _identity: str) -> None:
        """Forward the people field after a suggestion selection."""
        await self._state.set_page_people(self._people_values())

    def _apply_project_suggestion(self, identity: str) -> None:
        """Replace the project field with a page identity."""
        self.project_field.value = identity

    async def _apply_project_state(self, identity: str) -> None:
        """Forward the project field after a suggestion selection."""
        await self._state.set_page_project(identity)

    def _people_values(self) -> tuple[str, ...]:
        """Split the people field into trimmed identities."""
        return tuple(part.strip() for part in (self.people_field.value or "").split(",") if part.strip())

    def _is_inbox_page(self, page: PageDraft) -> bool:
        """Return whether the open page is an Inbox capture."""
        return page.path is not None and any(note.path == page.path for note in self._state.notes)

    async def go_back(self) -> None:
        """Return to the previous page."""
        self._rename_open = False
        await self._state.back()
        self.refresh()
        self._update()

    async def start_edit(self) -> None:
        """Switch to edit mode."""
        self._state.edit_page()
        self.refresh()
        self._update()

    async def finish_edit(self) -> None:
        """Commit the draft and return to read mode."""
        await self._state.done_editing()
        self.refresh()
        self._update()

    async def change_body(self) -> None:
        """Forward the body field to the draft."""
        await self._state.set_page_body(self.body_field.value or "")
        self.refresh()
        self._update()

    async def change_raw_text(self) -> None:
        """Forward raw rescue text to the draft."""
        await self._state.set_page_raw_text(self.raw_field.value or "")
        self.refresh()
        self._update()

    async def save_raw(self) -> None:
        """Write raw rescue text from the current field."""
        await self._state.set_page_raw_text(self.raw_field.value or "")
        await self._state.autosave()
        self.refresh()
        self._update()

    async def change_type(self) -> None:
        """Forward the selected type."""
        value = self.type_dropdown.value
        if value:
            await self._state.set_page_type(NoteType(value))
        self.refresh()
        self._update()

    async def change_category(self) -> None:
        """Forward the selected reference category."""
        value = self.category_dropdown.value
        category = ReferenceCategory(value) if value else None
        await self._state.set_page_category(category)
        self.refresh()
        self._update()

    async def change_status(self) -> None:
        """Forward the selected status."""
        value = self.status_dropdown.value
        status = Status(value) if value else None
        await self._state.set_page_status(status)
        self.refresh()
        self._update()

    async def change_due_date(self) -> None:
        """Forward the due-date text."""
        await self._state.set_page_due_date(self.due_field.value or "")
        self.refresh()
        self._update()

    async def change_people(self) -> None:
        """Forward the people field."""
        await self._state.set_page_people(self._people_values())
        self.refresh()
        self._update()

    async def change_project(self) -> None:
        """Forward the project field."""
        await self._state.set_page_project(self.project_field.value or "")
        self.refresh()
        self._update()

    async def process_current(self) -> None:
        """Open the Processing Wizard for the current Inbox capture."""
        page = self._state.page
        if page is None or page.path is None or self._on_process is None:
            return
        await self._on_process(page.path)

    async def choose_page(self, path: Path) -> None:
        """Open one candidate from the picker."""
        self._rename_open = False
        await self._state.choose_candidate(path)
        self.refresh()
        self._update()

    def _candidate_handler(self, path: Path) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler to one candidate path."""

        async def handle() -> None:
            await self.choose_page(path)

        return handle

    async def clear_ambiguous(self) -> None:
        """Close the candidate picker."""
        await self._state.clear_ambiguous()
        self.refresh()
        self._update()

    async def reload_page(self) -> None:
        """Reload the conflicted file from disk."""
        await self._state.reload_page()
        self.refresh()
        self._update()

    async def overwrite_page(self) -> None:
        """Overwrite the conflicted file with the draft."""
        await self._state.overwrite_page()
        self.refresh()
        self._update()

    async def recreate_page(self) -> None:
        """Recreate a vanished page from the draft."""
        await self._state.recreate_page()
        self.refresh()
        self._update()

    async def discard_draft(self) -> None:
        """Discard the draft without writing."""
        await self._state.discard_draft()
        self.refresh()
        self._update()

    async def rewrite_links(self) -> None:
        """Apply the unsafe-reference repair."""
        await self._state.apply_repair()
        self.refresh()
        self._update()

    async def keep_links(self) -> None:
        """Leave unsafe references unchanged."""
        await self._state.keep_repair()
        self.refresh()
        self._update()

    async def cancel_repair(self) -> None:
        """Cancel the creation that triggered a repair."""
        await self._state.cancel_repair()
        self.refresh()
        self._update()

    async def confirm_type_change(self) -> None:
        """Apply the pending type or category change."""
        await self._state.apply_type_change()
        self.refresh()
        self._update()

    async def cancel_type_change(self) -> None:
        """Revert the pending type or category change."""
        await self._state.cancel_type_change()
        self.refresh()
        self._update()

    async def begin_rename(self) -> None:
        """Open the rename panel."""
        page = self._state.page
        if page is None:
            return
        self._rename_open = True
        self.rename_field.value = page.identity
        await self._state.cancel_rename()
        self.refresh()
        self._update()

    async def preview_rename(self) -> None:
        """Plan the rename and show its reference counts."""
        title = (self.rename_field.value or "").strip()
        if not title:
            self._state.message = afanes.ui.strings.PAGE_RENAME_LABEL
            self.refresh()
            self._update()
            return
        await self._state.begin_rename(title)
        self.refresh()
        self._update()

    async def confirm_rename(self) -> None:
        """Apply the retained rename preview."""
        await self._state.apply_rename()
        self._rename_open = False
        self.refresh()
        self._update()

    async def cancel_rename(self) -> None:
        """Close the rename panel without changing the page."""
        await self._state.cancel_rename()
        self._rename_open = False
        self.refresh()
        self._update()

    async def begin_trash(self) -> None:
        """Plan moving the page to trash."""
        await self._state.begin_trash()
        self.refresh()
        self._update()

    async def confirm_trash(self) -> None:
        """Move the page to trash."""
        await self._state.apply_trash()
        self.refresh()
        self._update()

    async def cancel_trash(self) -> None:
        """Close the trash panel without moving the page."""
        await self._state.cancel_trash()
        self.refresh()
        self._update()
