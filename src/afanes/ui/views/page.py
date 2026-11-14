# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read, edit, and raw rescue modes for the page pane.

The view renders the shared application state and forwards intent to its
commands. It performs no Markdown parsing, SQL, or file I/O. Confirmation
flows are inline panels so the pane stays usable without a rendered dialog.
"""

import asyncio
import dataclasses
from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

import afanes.core.connections
import afanes.core.search
import afanes.core.vault.snapshot
import afanes.ui.components.field_flow
import afanes.ui.components.page_panels
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
from afanes.core.editing import DraftMode, PageDraft
from afanes.core.vault.snapshot import LinkOutcome
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteType, Status
from afanes.ui.components.banner import Banner
from afanes.ui.components.frozen import FrozenControlRecovery
from afanes.ui.components.panel import Panel
from afanes.ui.components.template_cards import TemplateCardContext, TemplateCardPicker
from afanes.ui.state.navigation import RoleFollowOutcome
from afanes.ui.views.project_body import PickDate, ProjectBodyView

type PickRole = Callable[[str, str | None], Awaitable[str | None]]


@dataclasses.dataclass(frozen=True, slots=True)
class PageActions:
    """Callbacks and pickers supplied by the workspace to a page view.

    Attributes
    ----------
    update : collections.abc.Callable[[], None]
        Requests a repaint of the page.
    on_process : collections.abc.Callable[[pathlib.Path], collections.abc.Awaitable[None]] | None
        Command that opens the Processing Wizard for an Inbox capture.
    pick_date : PickDate | None
        Command that opens the date picker for step and project dates.
    on_missing_role : collections.abc.Callable[[str], collections.abc.Awaitable[None]] | None
        Command that asks for a category before creating a missing role
        reference, or ``None`` when creation is unavailable.
    pick_role : PickRole | None
        Command that asks for an owner or requester name, or ``None`` when the
        read-mode action is unavailable.
    on_back : collections.abc.Callable[[], collections.abc.Awaitable[bool]] | None
        Optional fallback tried before the page history. It returns ``True``
        when the host handled the back request itself.
    """

    update: Callable[[], None]
    on_process: Callable[[Path], Awaitable[None]] | None = None
    pick_date: PickDate | None = None
    on_missing_role: Callable[[str], Awaitable[None]] | None = None
    pick_role: PickRole | None = None
    on_back: Callable[[], Awaitable[bool]] | None = None


class PageView:
    """Read, edit, and raw rescue modes for one note.

    Parameters
    ----------
    actions : PageActions
        Callbacks and pickers supplied by the host workspace.
    """

    def __init__(self, actions: PageActions) -> None:
        """Build the page controls against the shared application state.

        Parameters
        ----------
        actions : PageActions
            Callbacks and pickers supplied by the host workspace.
        """
        self._state = afanes.ui.state.app_state
        self._update = actions.update
        self._on_process = actions.on_process
        self._pick_date = actions.pick_date
        self._on_missing_role = actions.on_missing_role
        self._pick_role = actions.pick_role
        self._on_back = actions.on_back
        self._rename_open = False
        self._rename_error: str | None = None
        self._starter_task: asyncio.Task[None] | None = None
        self._role_suggestion_field: str | None = None
        self._field_flow_width = float(afanes.ui.theme.SHELL_WIDE_MIN)
        self._build_header()
        self._build_meta()
        self._build_read_content()
        self._build_edit_form()
        self._build_raw_panel()
        self._build_dialogs()
        self._build_layout()
        self.refresh()

    def _build_header(self) -> None:
        """Build the toolbar and its actions."""
        self.back_button = ft.IconButton(
            icon=ft.Icons.ARROW_BACK_OUTLINED,
            tooltip=afanes.ui.strings.PAGE_BACK,
            on_click=self.go_back,
        )
        self.title = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["title-3"],
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )
        self.path = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["caption"],
            selectable=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )
        self.progress = ft.ProgressRing(
            width=16,
            height=16,
            visible=False,
            semantics_label=afanes.ui.strings.WORKING,
        )
        self.status_text = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["caption"],
        )
        self.process_button = ft.TextButton(
            content=afanes.ui.strings.PROCESS_ACTION,
            icon=ft.Icons.PLAY_ARROW_OUTLINED,
            on_click=self.process_current,
            visible=False,
            key="process-note",
        )
        self.edit_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_EDIT,
            icon=ft.Icons.EDIT_OUTLINED,
            on_click=self.start_edit,
            key="page-edit-action",
        )
        self.done_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_DONE,
            icon=ft.Icons.CHECK_OUTLINED,
            on_click=self.finish_edit,
            visible=False,
            key="page-done-action",
        )
        self.restore_button = ft.FilledButton(
            content=afanes.ui.strings.TRASH_RESTORE,
            icon=ft.Icons.RESTORE_OUTLINED,
            on_click=self.restore_trash,
            visible=False,
            key="trash-restore-action",
        )
        self.edit_item = ft.PopupMenuItem(
            content=afanes.ui.strings.PAGE_EDIT,
            on_click=self.start_edit,
            key="page-edit",
        )
        self.rename_item = ft.PopupMenuItem(
            content=afanes.ui.strings.PAGE_RENAME,
            icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE,
            on_click=self.begin_rename,
            key="page-rename",
        )
        self.trash_item = ft.PopupMenuItem(
            content=afanes.ui.strings.PAGE_TRASH,
            icon=ft.Icons.DELETE_OUTLINE,
            on_click=self.trash_page,
            key="page-trash",
        )
        self.delete_item = ft.PopupMenuItem(
            content=afanes.ui.strings.TRASH_DELETE_PERMANENTLY,
            icon=ft.Icons.DELETE_FOREVER_OUTLINED,
            on_click=self.begin_delete_trash,
            key="page-delete-permanently",
        )
        self.menu_button = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT_OUTLINED,
            tooltip=afanes.ui.strings.PAGE_ACTIONS,
            items=[self.edit_item, self.rename_item, self.trash_item, self.delete_item],
            key="page-menu",
        )
        self.header = ft.Row(
            controls=[
                self.back_button,
                self.title,
                self.progress,
                self.process_button,
                self.edit_button,
                self.done_button,
                self.restore_button,
                self.menu_button,
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
            key="page-toolbar",
        )

    def _build_meta(self) -> None:
        """Build the metadata row."""
        self.meta_status = ft.Text("", style=afanes.ui.theme.TEXT_ROLES["caption"])
        self.meta_owner = ft.Text("", style=afanes.ui.theme.TEXT_ROLES["caption"])
        self.meta_owner_button = ft.IconButton(
            icon=ft.Icons.PERSON_ADD_OUTLINED,
            tooltip=afanes.ui.strings.PAGE_OWNER_SET,
            icon_color=afanes.ui.theme.MUTED_ACTION_COLOR,
            on_click=self.choose_owner,
            style=ft.ButtonStyle(
                icon_color={
                    ft.ControlState.HOVERED: afanes.ui.theme.TEXT_COLOR,
                    ft.ControlState.FOCUSED: afanes.ui.theme.TEXT_COLOR,
                },
            ),
            key="page-owner-set",
        )
        self.meta_asked = ft.Text("", style=afanes.ui.theme.TEXT_ROLES["caption"])
        self.meta_asked_button = ft.IconButton(
            icon=ft.Icons.PERSON_SEARCH_OUTLINED,
            tooltip=afanes.ui.strings.PAGE_ASKED_BY_SET,
            icon_color=afanes.ui.theme.MUTED_ACTION_COLOR,
            on_click=self.choose_asked_by,
            style=ft.ButtonStyle(
                icon_color={
                    ft.ControlState.HOVERED: afanes.ui.theme.TEXT_COLOR,
                    ft.ControlState.FOCUSED: afanes.ui.theme.TEXT_COLOR,
                },
            ),
            key="page-asked-by-set",
        )
        self.meta_due = ft.Text("", style=afanes.ui.theme.TEXT_ROLES["caption"])
        self.meta_date = ft.Text("", style=afanes.ui.theme.TEXT_ROLES["caption"])
        self.meta_due_button = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
            tooltip=afanes.ui.strings.PAGE_PROJECT_DUE_ADD,
            icon_color=afanes.ui.theme.MUTED_ACTION_COLOR,
            on_click=self.choose_due_date,
            style=ft.ButtonStyle(
                icon_color={
                    ft.ControlState.HOVERED: afanes.ui.theme.TEXT_COLOR,
                    ft.ControlState.FOCUSED: afanes.ui.theme.TEXT_COLOR,
                },
            ),
        )
        self.meta_due_clear = ft.IconButton(
            icon=ft.Icons.EVENT_BUSY_OUTLINED,
            tooltip=afanes.ui.strings.PAGE_PROJECT_DUE_CLEAR,
            icon_color=afanes.ui.theme.MUTED_ACTION_COLOR,
            on_click=self.clear_due_date,
            style=ft.ButtonStyle(
                icon_color={
                    ft.ControlState.HOVERED: afanes.ui.theme.TEXT_COLOR,
                    ft.ControlState.FOCUSED: afanes.ui.theme.TEXT_COLOR,
                },
            ),
        )
        self.meta_row = ft.Row(
            controls=[
                self.meta_date,
                self.meta_status,
                self.meta_owner,
                self.meta_owner_button,
                self.meta_asked,
                self.meta_asked_button,
                self.meta_due,
                self.meta_due_button,
                self.meta_due_clear,
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            visible=False,
            key="page-meta",
        )

    def _build_read_content(self) -> None:
        """Build the read-mode content and connections panel."""
        self.banners = ft.Column(controls=[], spacing=afanes.ui.theme.ITEM_GAP)
        self.empty_text = ft.Text(
            afanes.ui.strings.PAGE_EMPTY,
            color=afanes.ui.theme.MUTED_TEXT_COLOR,
        )
        self.read_body = ft.Markdown(
            value="",
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            auto_follow_links=False,
            on_tap_link=self.handle_link,
        )
        self.project_body = ProjectBodyView(self._update, self.follow, self._pick_date, self.follow_role)
        self._show_completed_steps = False
        self._show_finished_projects = False
        self._connections_page: Path | None = None
        self.connections_steps_toggle = ft.Checkbox(
            label=afanes.ui.strings.PAGE_CONNECTIONS_SHOW_COMPLETED_STEPS,
            value=False,
            on_change=self.toggle_completed_steps,
            key="connections-completed-steps",
        )
        self.connections_projects_toggle = ft.Checkbox(
            label=afanes.ui.strings.PAGE_CONNECTIONS_SHOW_FINISHED_PROJECTS,
            value=False,
            on_change=self.toggle_finished_projects,
            key="connections-finished-projects",
        )
        self.connections_body = ft.Column(
            controls=[],
            spacing=afanes.ui.theme.CONNECTIONS_GAP,
            key="connections-body",
        )
        self.connections_panel = Panel(
            afanes.ui.strings.PAGE_CONNECTIONS_TITLE,
            self.connections_body,
            [self.connections_steps_toggle, self.connections_projects_toggle],
        ).build()
        self.connections_panel.visible = False

    def _build_edit_form(self) -> None:
        """Build the edit form controls."""
        self.identity_text = ft.Text("", selectable=True, style=afanes.ui.theme.TEXT_ROLES["caption"])
        self.log_starter_picker = TemplateCardPicker(
            TemplateCardContext.LOG,
            "log-draft",
            self._starter_changed,
        )
        self.log_starter_picker.dropdown.height = afanes.ui.theme.PAGE_FORM_FIELD_HEIGHT
        self.log_starter_picker.dropdown.visible = False
        self.log_starter_panel = ft.Column(
            controls=[
                self.log_starter_picker.description,
                self.log_starter_picker.warning,
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
            visible=False,
        )
        self.body_field = ft.TextField(
            label=afanes.ui.strings.PAGE_BODY_LABEL,
            multiline=True,
            fit_parent_size=True,
            text_vertical_align=ft.VerticalAlignment.START,
            expand=True,
            on_change=self.change_body,
        )
        self.type_dropdown = ft.Dropdown(
            label=afanes.ui.strings.PAGE_TYPE_LABEL,
            options=[
                ft.dropdown.Option(key=note_type.value, text=afanes.ui.strings.PAGE_TYPE_LABELS[note_type.value])
                for note_type in NoteType
            ],
            on_select=self.change_type,
            height=afanes.ui.theme.PAGE_FORM_FIELD_HEIGHT,
        )
        self.category_field = ft.Dropdown(
            label=afanes.ui.strings.PAGE_CATEGORY_LABEL,
            hint_text=afanes.ui.strings.PAGE_CATEGORY_HINT,
            options=[],
            editable=True,
            enable_filter=True,
            on_select=self.change_category,
            on_blur=self._commit_category_on_blur,
            height=afanes.ui.theme.PAGE_FORM_FIELD_HEIGHT,
        )
        self.category_error = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["caption"],
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            visible=False,
            selectable=True,
        )
        self.status_dropdown = ft.Dropdown(
            label=afanes.ui.strings.PAGE_STATUS_LABEL,
            options=[],
            on_select=self.change_status,
            height=afanes.ui.theme.PAGE_FORM_FIELD_HEIGHT,
        )
        self.due_field = ft.TextField(
            label=afanes.ui.strings.PAGE_DUE_DATE_LABEL,
            hint_text="2026-11-20",
            on_change=self.change_due_date,
            height=afanes.ui.theme.PAGE_FORM_FIELD_HEIGHT,
        )
        self.date_field = ft.TextField(
            label=afanes.ui.strings.PAGE_DATE_LABEL,
            hint_text="2025-10-12",
            on_blur=self.commit_date,
            on_submit=self.commit_date,
            height=afanes.ui.theme.PAGE_FORM_FIELD_HEIGHT,
        )
        self.date_error = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["caption"],
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            visible=False,
            selectable=True,
        )
        self.asked_by_field = ft.TextField(
            label=afanes.ui.strings.PAGE_ASKED_BY_LABEL,
            hint_text=afanes.ui.strings.PAGE_ASKED_BY_HINT,
            on_change=self.change_asked_by,
            height=afanes.ui.theme.PAGE_FORM_FIELD_HEIGHT,
        )
        self.owner_field = ft.TextField(
            label=afanes.ui.strings.PAGE_OWNER_LABEL,
            hint_text=afanes.ui.strings.PAGE_OWNER_HINT,
            on_change=self.change_owner,
            height=afanes.ui.theme.PAGE_FORM_FIELD_HEIGHT,
        )
        self.name_suggestions = ft.Column(controls=[], spacing=0, visible=False)
        self.due_error = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["caption"],
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            visible=False,
            selectable=True,
        )
        self.form_fields = afanes.ui.components.field_flow.FieldFlow(
            [
                self.type_dropdown,
                self.category_field,
                self.status_dropdown,
                self.date_field,
                self.log_starter_picker.dropdown,
                self.due_field,
                self.owner_field,
                self.asked_by_field,
            ]
        )
        self.edit_form = ft.Column(
            controls=[
                self.identity_text,
                self.form_fields.row,
                self.name_suggestions,
                self.category_error,
                self.date_error,
                self.due_error,
                self.log_starter_panel,
                self.body_field,
            ],
            spacing=afanes.ui.theme.SECTION_GAP,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            visible=False,
        )

    def _build_raw_panel(self) -> None:
        """Build the raw rescue panel."""
        self.raw_warning = ft.Text(
            afanes.ui.strings.PAGE_RAW_WARNING,
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            selectable=True,
        )
        self.raw_field = ft.TextField(
            label=afanes.ui.strings.PAGE_BODY_LABEL,
            multiline=True,
            fit_parent_size=True,
            text_vertical_align=ft.VerticalAlignment.START,
            expand=True,
            on_change=self.change_raw_text,
        )
        self.raw_save_button = ft.FilledButton(
            content=afanes.ui.strings.PAGE_RAW_SAVE,
            on_click=self.save_raw,
        )
        self.raw_panel = ft.Column(
            controls=[self.raw_warning, self.raw_field, self.raw_save_button],
            spacing=afanes.ui.theme.ITEM_GAP,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            visible=False,
        )

    def _build_dialogs(self) -> None:
        """Build the inline confirmation panels."""
        self.conflict = afanes.ui.components.page_panels.ConflictPanel(
            self.reload_page,
            self.overwrite_page,
            self.recreate_page,
            self.discard_draft,
        )
        self.conflict_text = self.conflict.text
        self.reload_button = self.conflict.reload
        self.overwrite_button = self.conflict.overwrite
        self.recreate_button = self.conflict.recreate
        self.discard_button = self.conflict.discard
        self.conflict_panel = self.conflict.panel
        self.ambiguous = afanes.ui.components.page_panels.AmbiguousPanel(self.clear_ambiguous)
        self.ambiguous_list = self.ambiguous.list
        self.ambiguous_cancel_button = self.ambiguous.cancel
        self.ambiguous_panel = self.ambiguous.panel
        self.repair = afanes.ui.components.page_panels.RepairPanel(
            self.rewrite_links,
            self.keep_links,
            self.cancel_repair,
        )
        self.repair_text = self.repair.text
        self.repair_rewrite_button = self.repair.rewrite
        self.repair_keep_button = self.repair.keep
        self.repair_cancel_button = self.repair.cancel
        self.repair_panel = self.repair.panel
        self.type_change = afanes.ui.components.page_panels.TypeChangePanel(
            self.confirm_type_change,
            self.cancel_type_change,
        )
        self.type_change_text = self.type_change.text
        self.type_change_confirm_button = self.type_change.confirm
        self.type_change_cancel_button = self.type_change.cancel
        self.type_change_panel = self.type_change.panel
        self.category_move = afanes.ui.components.page_panels.CategoryMovePanel(
            self.confirm_category_move,
            self.cancel_category_move,
        )
        self.category_move_text = self.category_move.text
        self.category_move_confirm_button = self.category_move.confirm
        self.category_move_cancel_button = self.category_move.cancel
        self.category_move_panel = self.category_move.panel
        self.rename = afanes.ui.components.page_panels.RenamePanel(
            self.change_rename_text,
            self.preview_rename,
            self.confirm_rename,
            self.cancel_rename,
        )
        self.rename_field = self.rename.field
        self.rename_error = self.rename.error
        self.rename_preview_text = self.rename.preview_text
        self.rename_preview_button = self.rename.preview
        self.rename_confirm_button = self.rename.confirm
        self.rename_cancel_button = self.rename.cancel
        self.rename_panel = self.rename.panel
        self.overwrite_trash = afanes.ui.components.page_panels.DestructiveConfirmPanel(
            self.confirm_trash_overwrite,
            self.cancel_trash_overwrite,
        )
        self.overwrite_trash_panel = self.overwrite_trash.panel
        self.delete_trash = afanes.ui.components.page_panels.DestructiveConfirmPanel(
            self.confirm_trash_delete,
            self.cancel_trash_delete,
        )
        self.delete_trash_panel = self.delete_trash.panel
        self.dialogs = ft.Column(
            controls=[
                self.conflict_panel,
                self.ambiguous_panel,
                self.repair_panel,
                self.type_change_panel,
                self.category_move_panel,
                self.rename_panel,
                self.overwrite_trash_panel,
                self.delete_trash_panel,
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
        )

    def _build_layout(self) -> None:
        """Assemble the page surface."""
        self.content = ft.Column(
            controls=[self.empty_text, self.project_body.build(), self.read_body, self.connections_panel],
            spacing=afanes.ui.theme.ITEM_GAP,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        self.mode_host = ft.Stack(
            controls=[self.content, self.edit_form, self.raw_panel],
            expand=True,
            fit=ft.StackFit.EXPAND,
            key="page-mode-host",
        )
        self.trash_info = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["caption"],
            selectable=True,
            visible=False,
        )
        self.body_header = ft.Row(
            controls=[self.path, self.status_text],
            spacing=afanes.ui.theme.ITEM_GAP,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.page_content = ft.Column(
            controls=[
                self.body_header,
                self.trash_info,
                self.meta_row,
                self.banners,
                self.dialogs,
                self.mode_host,
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
            expand=True,
        )
        self.page_column = ft.Container(
            expand=True,
            content=self.page_content,
        )
        self.root = ft.Container(
            expand=True,
            padding=afanes.ui.theme.ITEM_GAP,
            bgcolor=afanes.ui.theme.CARD_SURFACE_COLOR,
            border=ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR),
            border_radius=afanes.ui.theme.SURFACE_RADIUS,
            on_size_change=self._resize_field_flow,
            content=ft.Row(
                controls=[self.page_column],
                spacing=afanes.ui.theme.ITEM_GAP,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                expand=True,
            ),
        )

    def toolbar(self) -> ft.Control:
        """Return the page toolbar for a host that owns the detail region.

        Returns
        -------
        ft.Control
            Back, title, progress, the single primary action, and the
            secondary page menu.
        """
        return self.header

    def body(self) -> ft.Control:
        """Return the page card without its toolbar.

        Returns
        -------
        ft.Control
            Bounded page content for the detail region.
        """
        return self.root

    def build(self) -> ft.Control:
        """Return the root control for the page pane.

        Returns
        -------
        ft.Control
            Composed read, edit, and raw rescue layout with its toolbar.
        """
        return ft.Column(
            controls=[self.header, self.root],
            spacing=afanes.ui.theme.SECTION_GAP,
            expand=True,
            key="page-view",
        )

    def _resize_field_flow(self, event: ft.LayoutSizeChangeEvent[ft.LayoutControl]) -> None:
        """Reflow the label controls for one rendered card width.

        Parameters
        ----------
        event : flet.LayoutSizeChangeEvent[flet.LayoutControl]
            Size event whose width is the rendered page card width.
        """
        width = max(0.0, event.width - 2 * afanes.ui.theme.ITEM_GAP)
        self._field_flow_width = width
        self.form_fields.layout(width)
        try:
            self.form_fields.row.update()
        except RuntimeError:
            return

    async def scroll_to_top(self) -> None:
        """Move the reusable page pane to its starting scroll position.

        Notes
        -----
        The pane may be reattached while the host rebuilds its detail region.
        A scroll request can arrive before the client knows the control, so an
        unattached control is left untouched instead of failing the command.
        """
        try:
            await self.content.scroll_to(offset=0, duration=0)
        except RuntimeError:
            return

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
        await self._state.navigation.follow_link(destination)
        self.refresh()
        await self.scroll_to_top()
        self._update()

    async def follow_role(self, name: str) -> None:
        """Open a project role name or start creating its missing note.

        Parameters
        ----------
        name : str
            Written owner, requester, or step owner name.

        Notes
        -----
        A resolved or ambiguous name follows the shared page navigation rules.
        A missing name delegates to the category dialog callback; this view
        writes nothing by itself.
        """
        outcome = await self._state.navigation.follow_role(name)
        if outcome is RoleFollowOutcome.MISSING:
            if self._on_missing_role is not None:
                await self._on_missing_role(name)
            return
        self.refresh()
        await self.scroll_to_top()
        self._update()

    def _role_outcome(self, name: str) -> LinkOutcome:
        """Return how a written role name resolves in the current scan."""
        snapshot = self._state.session.snapshot
        if snapshot is None:
            return LinkOutcome.MISSING
        reference = NoteReference(scheme=ReferenceScheme.NOTE, name=name)
        return snapshot.link_target(reference).outcome

    def _role_span(self, name: str) -> ft.TextSpan:
        """Build one link-styled text span for a role name."""
        outcome = self._role_outcome(name)
        broken = outcome in (LinkOutcome.MISSING, LinkOutcome.BROKEN)
        style = afanes.ui.theme.ROLE_BROKEN_TEXT_STYLE if broken else afanes.ui.theme.ROLE_LINK_TEXT_STYLE
        if broken:
            tooltip = afanes.ui.strings.ROLE_LINK_MISSING
        elif outcome is LinkOutcome.AMBIGUOUS:
            tooltip = afanes.ui.strings.ROLE_LINK_AMBIGUOUS
        else:
            tooltip = None
        return ft.TextSpan(
            name,
            style=style,
            tooltip=tooltip,
            on_click=self._role_handler(name),
        )

    def _role_handler(self, name: str) -> Callable[[], Awaitable[None]]:
        """Bind a role-name span to its navigation command."""

        async def handle() -> None:
            await self.follow_role(name)

        return handle

    def refresh(self) -> None:
        """Refresh every control from the shared application state."""
        FrozenControlRecovery.clear(self.header)
        FrozenControlRecovery.clear(self.root)
        page = self._state.pages.page
        editing = self._state.pages.editing or self._state.pages.page_mode is DraftMode.RAW
        self.content.visible = not editing
        self._refresh_header(page, editing=editing)
        self._refresh_meta(page, editing=editing)
        self._refresh_read(page, editing=editing)
        self._refresh_connections(page, editing=editing)
        self._refresh_edit(page, editing=editing)
        self.form_fields.layout(self._field_flow_width)
        self._refresh_raw(page)
        self._refresh_banners()
        self._refresh_conflict()
        self._refresh_ambiguity()
        self._refresh_repair()
        self._refresh_type_change()
        self._refresh_category_move()
        self._refresh_rename()
        self._refresh_trash_decisions()

    def _refresh_header(self, page: PageDraft | None, *, editing: bool) -> None:
        """Refresh the header, mode buttons, and write status."""
        state = self._state
        self.title.value = state.pages.page_title if page is not None else ""
        self.path.value = state.pages.page_path_label
        self.back_button.disabled = page is None and not state.navigation.history
        trashed = state.pages.trash_entry is not None
        normal = page is not None and not editing and self._state.pages.page_mode is DraftMode.NORMAL
        process_visible = page is not None and normal and not trashed and self._is_inbox_page(page)
        self.process_button.visible = process_visible
        self.edit_button.visible = normal and not process_visible and not trashed
        self.restore_button.visible = trashed and not editing
        self.done_button.visible = page is not None and editing and not trashed
        labels = self._state.pages.page_labels if page is not None else None
        is_log = labels is not None and labels.note_type is NoteType.LOG
        self.edit_item.visible = normal and process_visible and not trashed
        self.rename_item.visible = normal and not is_log and not trashed
        self.trash_item.visible = page is not None and not editing and not trashed
        self.delete_item.visible = trashed and not editing
        self.menu_button.visible = page is not None and not editing
        self.progress.visible = state.status.busy or state.pages.saving
        if state.pages.saving:
            self.status_text.value = afanes.ui.strings.PAGE_SAVING
        elif page is not None and editing and state.pages.page_is_dirty:
            self.status_text.value = afanes.ui.strings.PAGE_UNSAVED
        else:
            self.status_text.value = ""

    def _refresh_read(self, page: PageDraft | None, *, editing: bool) -> None:
        """Refresh the rendered read mode or the step-aware project body."""
        state = self._state
        labels = state.pages.page_labels if page is not None else None
        is_project = labels is not None and labels.note_type is NoteType.PROJECT and state.pages.trash_entry is None
        visible = page is not None and not editing
        self.empty_text.visible = page is None
        self.read_body.visible = visible and not is_project
        self.project_body.refresh()
        if visible and page is not None and not is_project:
            self.read_body.value = (
                state.pages.page_raw_text
                if page.mode is DraftMode.RAW and state.pages.trash_entry is not None
                else state.pages.page_read_text
            )
        entry = state.pages.trash_entry
        self.trash_info.visible = entry is not None and visible
        if entry is not None:
            self.trash_info.value = (
                afanes.ui.strings.TRASH_INFO.format(
                    path=entry.birthplace_text,
                    date=entry.trashed_on.isoformat(),
                )
                if entry.trashed_on is not None
                else afanes.ui.strings.TRASH_INFO_NO_DATE.format(path=entry.birthplace_text)
            )

    def _refresh_connections(self, page: PageDraft | None, *, editing: bool) -> None:
        """Refresh the read-only Connections section after the rendered body."""
        state = self._state
        path = page.path if page is not None else None
        if path != self._connections_page:
            self._connections_page = path
            self._show_completed_steps = False
            self._show_finished_projects = False
        labels = state.pages.page_labels if page is not None else None
        parsed = (
            page is not None
            and path is not None
            and not editing
            and page.mode is DraftMode.NORMAL
            and labels is not None
            and state.pages.trash_entry is None
        )
        connections = state.session.connections if parsed else None
        result = connections.for_note(path) if connections is not None and path is not None else None
        if result is None or not result.has_connections:
            self.connections_panel.visible = False
            self.connections_body.controls = []
            return
        self.connections_steps_toggle.value = self._show_completed_steps
        self.connections_steps_toggle.visible = result.has_completed_steps
        self.connections_projects_toggle.value = self._show_finished_projects
        self.connections_projects_toggle.visible = bool(
            result.finished_projects or result.finished_project_owner_projects
        )
        sections: list[ft.Control] = []
        linked_from = self._linked_from_controls(result)
        if linked_from:
            sections.append(self._connection_subsection(afanes.ui.strings.PAGE_CONNECTIONS_LINKED_FROM, linked_from))
        owned_projects = self._owned_project_controls(result)
        if owned_projects:
            sections.append(
                self._connection_subsection(afanes.ui.strings.PAGE_CONNECTIONS_OWNED_PROJECTS, owned_projects)
            )
        owned_steps = self._owned_step_controls(result)
        if owned_steps:
            sections.append(self._connection_subsection(afanes.ui.strings.PAGE_CONNECTIONS_OWNED_STEPS, owned_steps))
        requested_projects = self._requested_project_controls(result)
        if requested_projects:
            sections.append(
                self._connection_subsection(
                    afanes.ui.strings.PAGE_CONNECTIONS_REQUESTED_PROJECTS,
                    requested_projects,
                )
            )
        self.connections_body.controls = sections
        self.connections_panel.visible = True

    def _connection_subsection(self, title: str, rows: list[ft.Control]) -> ft.Column:
        """Build one labeled group of connection rows."""
        return ft.Column(
            controls=[
                ft.Text(title, style=afanes.ui.theme.TEXT_ROLES["caption-heading"]),
                *rows,
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
        )

    def _linked_from_controls(self, result: afanes.core.connections.ConnectionSet) -> list[ft.Control]:
        """Build one row per note whose body links here."""
        return [
            ft.TextButton(
                content=note.title,
                on_click=self._connection_handler(note.path),
            )
            for note in result.linked_from
        ]

    def _owned_project_controls(self, result: afanes.core.connections.ConnectionSet) -> list[ft.Control]:
        """Build owned-project rows, with finished projects behind the toggle."""
        projects = list(result.project_owner_projects)
        if self._show_finished_projects:
            projects.extend(result.finished_project_owner_projects)
        return [
            ft.TextButton(
                content=project.title,
                on_click=self._connection_handler(project.path),
            )
            for project in projects
        ]

    def _owned_step_controls(self, result: afanes.core.connections.ConnectionSet) -> list[ft.Control]:
        """Build owned-step rows grouped by project."""
        rows: list[ft.Control] = []
        for owned in result.owned_projects:
            steps = list(owned.open_steps)
            if self._show_completed_steps:
                steps.extend(owned.completed_steps)
            if not steps:
                continue
            rows.append(
                ft.TextButton(
                    content=ft.Text(owned.project.title, style=afanes.ui.theme.TEXT_ROLES["caption"]),
                    on_click=self._connection_handler(owned.project.path),
                )
            )
            rows.extend(
                ft.Container(
                    content=ft.TextButton(
                        content=step.text,
                        on_click=self._connection_handler(owned.project.path),
                    ),
                    padding=ft.Padding.only(left=afanes.ui.theme.STEP_INDENT),
                )
                for step in steps
            )
        return rows

    def _requested_project_controls(self, result: afanes.core.connections.ConnectionSet) -> list[ft.Control]:
        """Build requested-project rows, with finished projects behind the toggle."""
        projects = list(result.requested_projects)
        if self._show_finished_projects:
            projects.extend(result.finished_projects)
        return [
            ft.TextButton(
                content=project.title,
                on_click=self._connection_handler(project.path),
            )
            for project in projects
        ]

    def _refresh_meta(self, page: PageDraft | None, *, editing: bool) -> None:
        """Refresh the note date and the project status and due-date row."""
        state = self._state
        labels = state.pages.page_labels if page is not None else None
        visible = page is not None and not editing and labels is not None and state.pages.trash_entry is None
        self.meta_row.visible = visible
        if not visible or labels is None:
            self.meta_owner.visible = False
            self.meta_owner_button.visible = False
            self.meta_asked.visible = False
            self.meta_asked_button.visible = False
            return
        self.meta_date.value = (
            afanes.ui.strings.PAGE_DATE.format(date=labels.date_text)
            if labels.date_text.strip()
            else afanes.ui.strings.PAGE_NO_DATE
        )
        is_project = labels.note_type is NoteType.PROJECT
        self.meta_status.visible = is_project
        self.meta_due.visible = is_project
        self.meta_due_button.visible = is_project
        self.meta_due_clear.visible = is_project and labels.due_date is not None
        self.meta_owner_button.visible = is_project
        self.meta_asked_button.visible = is_project
        if not is_project:
            self.meta_owner.visible = False
            self.meta_asked.visible = False
            return
        status_label = (
            afanes.ui.strings.PROCESSING_STATUS_LABELS[labels.status.value]
            if labels.status is not None
            else afanes.ui.strings.PAGE_PROJECT_NO_STATUS
        )
        self.meta_status.value = afanes.ui.strings.PROJECT_STATUS.format(status=status_label)
        owner = labels.owner_text.strip()
        self.meta_owner.spans = (
            [
                ft.TextSpan(f"{afanes.ui.strings.PAGE_OWNER_LABEL} "),
                self._role_span(owner),
            ]
            if owner
            else []
        )
        self.meta_owner.visible = bool(owner)
        asked_by = labels.asked_by_text.strip()
        self.meta_asked.spans = (
            [
                ft.TextSpan(f"{afanes.ui.strings.PAGE_ASKED_BY_LABEL} "),
                self._role_span(asked_by),
            ]
            if asked_by
            else []
        )
        self.meta_asked.visible = bool(asked_by)
        due_date = labels.due_date
        self.meta_due.value = (
            afanes.ui.strings.PROJECT_DUE.format(date=due_date.isoformat())
            if due_date is not None
            else afanes.ui.strings.PAGE_PROJECT_NO_DUE
        )

    def _refresh_edit(self, page: PageDraft | None, *, editing: bool) -> None:
        """Refresh the body field and label form."""
        state = self._state
        labels = state.pages.page_labels if page is not None else None
        visible = page is not None and editing and state.pages.page_mode is DraftMode.NORMAL and labels is not None
        self.edit_form.visible = visible
        if not visible or page is None or labels is None:
            self.log_starter_panel.visible = False
            self._clear_role_suggestions()
            return

        body = state.pages.page_body
        if self.body_field.value != body:
            self.body_field.value = body
        self.identity_text.value = f"{afanes.ui.strings.PAGE_IDENTITY_LABEL}: {page.identity}"
        self.type_dropdown.value = labels.note_type.value
        self.category_field.visible = labels.note_type is NoteType.REFERENCE
        category_value = labels.category.value if labels.category is not None else ""
        self.category_field.options = self._category_options()
        if self.category_field.value != category_value:
            self.category_field.value = category_value
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
        self.date_field.visible = True
        if self.date_field.value != labels.date_text:
            self.date_field.value = labels.date_text
        self.date_error.value = labels.date_error or ""
        self.date_error.visible = labels.date_error is not None
        self.due_field.visible = labels.note_type is NoteType.PROJECT
        if self.due_field.value != labels.due_date_text:
            self.due_field.value = labels.due_date_text
        self.asked_by_field.visible = labels.note_type is NoteType.PROJECT
        if self.asked_by_field.value != labels.asked_by_text:
            self.asked_by_field.value = labels.asked_by_text
        self.owner_field.visible = labels.note_type is NoteType.PROJECT
        if self.owner_field.value != labels.owner_text:
            self.owner_field.value = labels.owner_text
        self.due_error.value = labels.due_date_error or ""
        self.due_error.visible = labels.due_date_error is not None
        self._refresh_log_starter()
        self._refresh_role_suggestions()

    def _refresh_log_starter(self) -> None:
        """Show the Starter control while a new log draft is otherwise empty."""
        starter = self._state.pages.log_starter
        visible = self._state.pages.log_starter_visible and starter is not None
        self.log_starter_picker.dropdown.visible = visible
        self.log_starter_panel.visible = visible
        if not visible or starter is None:
            return
        self.log_starter_picker.refresh(starter.cards, starter.issues)
        self.log_starter_picker.select(starter.selected)

    def _refresh_raw(self, page: PageDraft | None) -> None:
        """Refresh raw rescue mode."""
        state = self._state
        visible = page is not None and state.pages.page_mode is DraftMode.RAW and state.pages.trash_entry is None
        self.raw_panel.visible = visible
        if visible and page is not None and self.raw_field.value != state.pages.page_raw_text:
            self.raw_field.value = state.pages.page_raw_text
        self.raw_save_button.disabled = self._state.status.busy or self._state.pages.saving

    def _refresh_banners(self) -> None:
        """Refresh the page's persistent banner."""
        message = self._state.pages.banner
        self.banners.controls = [] if message is None else [Banner(message).build()]
        self.banners.visible = message is not None

    def _refresh_conflict(self) -> None:
        """Refresh the conflict recovery panel."""
        conflict = self._state.pages.conflict
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
        self.ambiguous_panel.visible = bool(state.navigation.ambiguous)
        self.ambiguous_list.controls = [
            ft.ListTile(
                title=state.session.note_title(path),
                subtitle=path.as_posix(),
                on_click=self._candidate_handler(path),
            )
            for path in state.navigation.ambiguous
        ]

    def _refresh_repair(self) -> None:
        """Refresh the unsafe-reference repair panel."""
        preview = self._state.pages.repair_preview
        self.repair_panel.visible = preview is not None
        if preview is None:
            return
        count = sum(site.reference_count for site in preview.sites)
        notes = len(preview.sites)
        self.repair_text.value = (
            afanes.ui.strings.PAGE_REPAIR_BODY.format(old=preview.old.name, new=preview.new.name)
            + " "
            + afanes.ui.strings.PAGE_REPAIR_COUNT.format(
                detail=afanes.ui.strings.CopyFormatter.reference_count(count, notes)
            )
        )

    def _refresh_type_change(self) -> None:
        """Refresh the scheme-change confirmation panel."""
        labels = self._state.dialogs.pending_labels
        sites = self._state.dialogs.type_change_sites
        self.type_change_panel.visible = labels is not None and bool(sites)
        if labels is None or not sites:
            return
        count = sum(site.reference_count for site in sites)
        self.type_change_text.value = afanes.ui.strings.PAGE_TYPE_CHANGE_BODY.format(
            detail=afanes.ui.strings.CopyFormatter.reference_count(count, len(sites))
        )

    def _refresh_rename(self) -> None:
        """Refresh the rename panel."""
        self._set_rename_available()
        preview = self._state.dialogs.rename_preview
        self.rename_panel.visible = self._rename_open or preview is not None
        self.rename_field.visible = preview is None
        self.rename_preview_button.visible = preview is None
        self.rename_confirm_button.visible = preview is not None
        self.rename_error.value = self._rename_error or ""
        self.rename_error.visible = self._rename_error is not None
        if preview is None:
            self.rename_preview_text.value = ""
            return
        count = preview.reference_count
        self.rename_preview_text.value = afanes.ui.strings.PAGE_RENAME_PREVIEW.format(
            detail=afanes.ui.strings.CopyFormatter.reference_count(count, len(preview.affected))
        )

    def _set_rename_available(self) -> None:
        """Keep the rename actions available only for a non-blank name."""
        valid = bool((self.rename_field.value or "").strip())
        self.rename_preview_button.disabled = not valid
        self.rename_confirm_button.disabled = not valid

    def _refresh_category_move(self) -> None:
        """Refresh the category move confirmation panel."""
        preview = self._state.dialogs.category_move
        self.category_move_panel.visible = preview is not None
        if preview is None:
            return
        self.category_move_text.value = afanes.ui.strings.PAGE_CATEGORY_MOVE_BODY.format(
            path=preview.target_path,
        )

    def _refresh_trash_decisions(self) -> None:
        """Refresh the overwrite and permanent-delete confirmations."""
        pending = self._state.dialogs.trash_dialogs
        overwrite = pending.overwrite_entry
        self.overwrite_trash_panel.visible = overwrite is not None
        if overwrite is not None:
            self.overwrite_trash.title.value = afanes.ui.strings.TRASH_OVERWRITE_TITLE
            self.overwrite_trash.body.value = afanes.ui.strings.TRASH_OVERWRITE_BODY.format(
                path=overwrite.birthplace_text,
            )
            self.overwrite_trash.confirm.content = afanes.ui.strings.TRASH_OVERWRITE_CONFIRM
        delete = pending.delete_entry
        self.delete_trash_panel.visible = delete is not None
        if delete is not None:
            self.delete_trash.title.value = afanes.ui.strings.TRASH_DELETE_TITLE
            self.delete_trash.body.value = afanes.ui.strings.TRASH_DELETE_BODY
            self.delete_trash.confirm.content = afanes.ui.strings.TRASH_DELETE_CONFIRM

    def _is_inbox_page(self, page: PageDraft) -> bool:
        """Return whether the open page is an Inbox capture."""
        return page.path is not None and any(note.path == page.path for note in self._state.session.notes)

    async def go_back(self) -> None:
        """Return to the previous page or let the host close the detail."""
        self._rename_open = False
        if self._on_back is not None and await self._on_back():
            return
        await self._state.navigation.back()
        self.refresh()
        await self.scroll_to_top()
        self._update()

    async def start_edit(self) -> None:
        """Switch to edit mode."""
        self._role_suggestion_field = None
        self._state.pages.edit_page()
        self.refresh()
        self._update()

    async def finish_edit(self) -> None:
        """Commit the draft and return to read mode."""
        self._role_suggestion_field = None
        previous = self._state.pages.page.path if self._state.pages.page is not None else None
        await self.commit_date()
        current = self._state.pages.page.path if self._state.pages.page is not None else None
        if current != previous:
            self.refresh()
            self._update()
            return
        await self._state.pages.done_editing()
        self.refresh()
        self._update()

    async def commit_date(self) -> None:
        """Write the Date field when the user leaves it."""
        await self._state.dialogs.save_page_date(self.date_field.value or "")
        self.refresh()
        self._update()

    def _starter_changed(self) -> None:
        """Schedule the Starter selection command from a picker event."""
        self._starter_task = asyncio.create_task(self.change_log_starter())

    async def change_log_starter(self) -> None:
        """Apply the Starter card or Empty choice to the open log draft."""
        await self._state.pages.select_log_starter(self.log_starter_picker.selected_card)
        self.refresh()
        self._update()

    async def change_body(self) -> None:
        """Forward the body field to the draft."""
        await self._state.pages.set_page_body(self.body_field.value or "")
        self.refresh()
        self._update()

    async def change_raw_text(self) -> None:
        """Forward raw rescue text to the draft."""
        await self._state.pages.set_page_raw_text(self.raw_field.value or "")
        self.refresh()
        self._update()

    async def change_rename_text(self) -> None:
        """Update the rename actions as the new name changes."""
        self._set_rename_available()
        self._update()

    async def save_raw(self) -> None:
        """Write raw rescue text from the current field."""
        await self._state.pages.set_page_raw_text(self.raw_field.value or "")
        await self._state.pages.autosave()
        self.refresh()
        self._update()

    async def change_type(self) -> None:
        """Forward the selected type."""
        value = self.type_dropdown.value
        if value:
            await self._state.dialogs.set_page_type(NoteType(value))
        self.refresh()
        self._update()

    def _category_options(self) -> list[ft.dropdown.Option]:
        """Return the category labels already used by reference notes.

        Returns
        -------
        list[flet.dropdown.Option]
            One option per distinct label, sorted case-insensitively.
        """
        listing = self._state.browser.listing()
        if listing is None:
            return []
        labels = {
            group.label.value
            for group in listing.groups_for(afanes.core.search.BrowserSection.REFERENCES)
            if group.label is not None
        }
        return [ft.dropdown.Option(key=label, text=label) for label in sorted(labels, key=str.casefold)]

    async def _commit_category_on_blur(self, _event: object = None) -> None:
        """Commit typed category text when the combobox loses focus.

        Parameters
        ----------
        _event : object
            Focus-change event supplied by Flet; unused.

        Notes
        -----
        Enter and a menu selection already reach :meth:`change_category`. The
        blur commit covers a typed label that the user leaves without
        submitting, unless a category move is already waiting for confirmation.
        """
        if self._state.dialogs.category_move is not None:
            return
        page = self._state.pages.page
        labels = page.labels if page is not None else None
        current = labels.category.value if labels is not None and labels.category is not None else ""
        if (self.category_field.value or "").strip() == current:
            return
        await self.change_category()

    async def change_category(self) -> None:
        """Forward the category label, using a new label only when valid."""
        value = (self.category_field.value or "").strip()
        try:
            category = CategoryLabel(value) if value else None
        except ValueError:
            self.category_error.value = afanes.ui.strings.PAGE_CATEGORY_INVALID
            self.category_error.visible = True
            self._update()
            return
        self.category_error.visible = False
        await self._state.dialogs.set_page_category(category)
        self.refresh()
        self._update()

    async def change_status(self) -> None:
        """Forward the selected status."""
        value = self.status_dropdown.value
        status = Status(value) if value else None
        await self._state.dialogs.set_page_status(status)
        self.refresh()
        self._update()

    async def change_due_date(self) -> None:
        """Forward the due-date text."""
        await self._state.dialogs.set_page_due_date(self.due_field.value or "")
        self.refresh()
        self._update()

    async def change_asked_by(self) -> None:
        """Forward the requester text."""
        self._role_suggestion_field = "asked_by"
        await self._state.dialogs.set_page_asked_by(self.asked_by_field.value or "")
        self.refresh()
        self._update()

    async def change_owner(self) -> None:
        """Forward the project-owner text."""
        self._role_suggestion_field = "owner"
        await self._state.pages.set_page_owner(self.owner_field.value or "")
        self.refresh()
        self._update()

    def _refresh_role_suggestions(self) -> None:
        """Fill the role-name suggestions from the active field."""
        field = self._role_suggestion_field
        if field is None or not self.edit_form.visible:
            self._clear_role_suggestions()
            return
        source = self.owner_field if field == "owner" else self.asked_by_field
        query = (source.value or "").strip()
        if not query:
            self._clear_role_suggestions()
            return
        candidates = self._state.session.assignment_candidates(ReferenceScheme.NOTE, query)
        self.name_suggestions.controls = [
            ft.ListTile(
                title=note.title,
                subtitle=note.name if note.name != note.title else None,
                on_click=self._role_suggestion_handler(note.name),
            )
            for note in candidates
        ]
        self.name_suggestions.visible = bool(self.name_suggestions.controls)

    def _clear_role_suggestions(self) -> None:
        """Empty and hide the role-name suggestion list."""
        self.name_suggestions.controls = []
        self.name_suggestions.visible = False

    def _role_suggestion_handler(self, name: str) -> Callable[[], Awaitable[None]]:
        """Bind a suggestion tile to the role field being edited."""

        async def handle() -> None:
            field = self._role_suggestion_field
            self._role_suggestion_field = None
            if field == "owner":
                self.owner_field.value = name
                await self._state.pages.set_page_owner(name)
            elif field == "asked_by":
                self.asked_by_field.value = name
                await self._state.dialogs.set_page_asked_by(name)
            self._clear_role_suggestions()
            self.refresh()
            self._update()

        return handle

    async def choose_owner(self) -> None:
        """Ask for a project owner and write it from read mode."""
        labels = self._state.pages.page_labels
        if labels is None or labels.note_type is not NoteType.PROJECT or self._pick_role is None:
            return
        chosen = await self._pick_role("owner", labels.owner_text.strip() or None)
        if chosen is None:
            return
        await self._state.pages.set_page_owner(chosen, save=True)
        self.refresh()
        self._update()

    async def choose_asked_by(self) -> None:
        """Ask for a project requester and write it from read mode."""
        labels = self._state.pages.page_labels
        if labels is None or labels.note_type is not NoteType.PROJECT or self._pick_role is None:
            return
        chosen = await self._pick_role("asked_by", labels.asked_by_text.strip() or None)
        if chosen is None:
            return
        await self._state.dialogs.set_page_asked_by(chosen, save=True)
        self.refresh()
        self._update()

    async def choose_due_date(self) -> None:
        """Open the date picker and write the chosen project due date."""
        labels = self._state.pages.page_labels
        if labels is None or labels.note_type is not NoteType.PROJECT or self._pick_date is None:
            return
        chosen = await self._pick_date(labels.due_date)
        if chosen is None:
            return
        await self._state.dialogs.save_page_due_date(chosen.isoformat())
        self.refresh()
        self._update()

    async def clear_due_date(self) -> None:
        """Remove the project due date from read mode."""
        await self._state.dialogs.save_page_due_date("")
        self.refresh()
        self._update()

    async def process_current(self) -> None:
        """Open the Processing Wizard for the current Inbox capture."""
        page = self._state.pages.page
        if page is None or page.path is None or self._on_process is None:
            return
        await self._on_process(page.path)

    async def open_connection(self, path: Path) -> None:
        """Open one connection target in the page pane.

        Parameters
        ----------
        path : Path
            Absolute path of the linked note or project.
        """
        await self._state.navigation.open_page(path)
        self.refresh()
        await self.scroll_to_top()
        self._update()

    async def toggle_completed_steps(self, event: ft.Event[ft.Checkbox]) -> None:
        """Show or hide completed owned steps.

        Parameters
        ----------
        event : flet.Event[flet.Checkbox]
            Toggle event whose control carries the new boolean value.
        """
        self._show_completed_steps = bool(event.control.value)
        self.refresh()
        self._update()

    async def toggle_finished_projects(self, event: ft.Event[ft.Checkbox]) -> None:
        """Show or hide finished requested projects.

        Parameters
        ----------
        event : flet.Event[flet.Checkbox]
            Toggle event whose control carries the new boolean value.
        """
        self._show_finished_projects = bool(event.control.value)
        self.refresh()
        self._update()

    def _connection_handler(self, path: Path) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler to one connection path."""

        async def handle() -> None:
            await self.open_connection(path)

        return handle

    async def choose_page(self, path: Path) -> None:
        """Open one candidate from the picker."""
        self._rename_open = False
        await self._state.navigation.choose_candidate(path)
        self.refresh()
        await self.scroll_to_top()
        self._update()

    def _candidate_handler(self, path: Path) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler to one candidate path."""

        async def handle() -> None:
            await self.choose_page(path)

        return handle

    async def clear_ambiguous(self) -> None:
        """Close the candidate picker."""
        await self._state.navigation.clear_ambiguous()
        self.refresh()
        self._update()

    async def reload_page(self) -> None:
        """Reload the conflicted file from disk."""
        await self._state.dialogs.reload_page()
        self.refresh()
        self._update()

    async def overwrite_page(self) -> None:
        """Overwrite the conflicted file with the draft."""
        await self._state.dialogs.overwrite_page()
        self.refresh()
        self._update()

    async def recreate_page(self) -> None:
        """Recreate a vanished page from the draft."""
        await self._state.dialogs.recreate_page()
        self.refresh()
        self._update()

    async def discard_draft(self) -> None:
        """Discard the draft without writing."""
        self._state.pages.clear()
        self.refresh()
        self._update()

    async def rewrite_links(self) -> None:
        """Apply the unsafe-reference repair."""
        await self._state.dialogs.apply_repair()
        self.refresh()
        self._update()

    async def keep_links(self) -> None:
        """Leave unsafe references unchanged."""
        await self._state.dialogs.keep_repair()
        self.refresh()
        self._update()

    async def cancel_repair(self) -> None:
        """Cancel the creation that triggered a repair."""
        await self._state.dialogs.cancel_repair()
        self.refresh()
        self._update()

    async def confirm_type_change(self) -> None:
        """Apply the pending type or category change."""
        await self._state.dialogs.apply_type_change()
        self.refresh()
        self._update()

    async def cancel_type_change(self) -> None:
        """Revert the pending type or category change."""
        await self._state.dialogs.cancel_type_change()
        self.refresh()
        self._update()

    async def confirm_category_move(self) -> None:
        """Apply the pending category change and move the file."""
        await self._state.dialogs.apply_category_move()
        self.refresh()
        self._update()

    async def cancel_category_move(self) -> None:
        """Keep the category and the file location unchanged."""
        await self._state.dialogs.cancel_category_move()
        self.refresh()
        self._update()

    async def begin_rename(self) -> None:
        """Open the rename panel."""
        page = self._state.pages.page
        if page is None:
            return
        self._rename_open = True
        self._rename_error = None
        self.rename_field.value = page.identity
        await self._state.dialogs.cancel_rename()
        self.refresh()
        self._update()

    async def preview_rename(self) -> None:
        """Plan the rename and show its reference counts."""
        title = (self.rename_field.value or "").strip()
        if not title:
            self._rename_error = afanes.ui.strings.PAGE_RENAME_LABEL
            self.refresh()
            self._update()
            return
        self._rename_error = None
        await self._state.dialogs.begin_rename(title)
        self.refresh()
        self._update()

    async def confirm_rename(self) -> None:
        """Apply the retained rename preview."""
        await self._state.dialogs.apply_rename()
        self._rename_open = False
        self._rename_error = None
        self.refresh()
        self._update()

    async def cancel_rename(self) -> None:
        """Close the rename panel without changing the page."""
        await self._state.dialogs.cancel_rename()
        self._rename_open = False
        self._rename_error = None
        self.refresh()
        self._update()

    async def trash_page(self) -> None:
        """Move the open page to trash and offer its undo."""
        await self._state.dialogs.trash_page()
        self.refresh()
        self._update()

    async def restore_trash(self) -> None:
        """Restore the open read-only trashed note."""
        await self._state.dialogs.trash_dialogs.restore()
        self.refresh()
        self._update()

    async def begin_delete_trash(self) -> None:
        """Open the permanent-delete confirmation for the trashed note."""
        await self._state.dialogs.trash_dialogs.begin_delete()
        self.refresh()
        self._update()

    async def confirm_trash_overwrite(self) -> None:
        """Restore the waiting entry and replace the occupied birthplace."""
        await self._state.dialogs.trash_dialogs.confirm_overwrite()
        self.refresh()
        self._update()

    async def cancel_trash_overwrite(self) -> None:
        """Dismiss the overwrite confirmation without writing."""
        await self._state.dialogs.trash_dialogs.cancel_overwrite()
        self.refresh()
        self._update()

    async def confirm_trash_delete(self) -> None:
        """Permanently delete the trashed note after confirmation."""
        await self._state.dialogs.trash_dialogs.confirm_delete()
        self.refresh()
        self._update()

    async def cancel_trash_delete(self) -> None:
        """Dismiss the permanent-delete confirmation without deleting."""
        await self._state.dialogs.trash_dialogs.cancel_delete()
        self.refresh()
        self._update()
