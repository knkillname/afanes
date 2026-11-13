# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Persistent workspace shell with the vault browser and page pane.

The view is presentational. It reads the shared application state and forwards
user intent to its commands; it never parses Markdown, queries SQL, or writes a
vault file. The browser stays visible while the main area shows the page pane,
the Processing Wizard, or a guided review.
"""

import asyncio
import dataclasses
import datetime
from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

import afanes.core.log
import afanes.core.search
import afanes.ui.components.calendar
import afanes.ui.components.capture_bar
import afanes.ui.components.frozen
import afanes.ui.components.log_tree
import afanes.ui.state
import afanes.ui.state.browser
import afanes.ui.state.status
import afanes.ui.strings
import afanes.ui.theme
import afanes.ui.views.page
import afanes.ui.views.processing
import afanes.ui.views.projects
import afanes.ui.views.review
from afanes.core.vault.snapshot import VaultFailure, VaultNote
from afanes.models.note import DatePrecision, NoteDate
from afanes.ui.components.banner import Banner
from afanes.ui.components.frozen import FrozenControlRecovery

_MONTHS_IN_YEAR = 12

_SECTION_ICONS = {
    afanes.ui.state.browser.WorkspaceSection.INBOX: ft.Icons.INBOX_OUTLINED,
    afanes.ui.state.browser.WorkspaceSection.PROJECTS: ft.Icons.FOLDER_OUTLINED,
    afanes.ui.state.browser.WorkspaceSection.REFERENCES: ft.Icons.BOOK_OUTLINED,
    afanes.ui.state.browser.WorkspaceSection.LOG: ft.Icons.CALENDAR_MONTH_OUTLINED,
    afanes.ui.state.browser.WorkspaceSection.NEEDS_ATTENTION: ft.Icons.WARNING_AMBER_OUTLINED,
}


@dataclasses.dataclass(frozen=True, slots=True)
class WorkspaceActions:
    """Callbacks and pickers supplied by the application to the workspace.

    Attributes
    ----------
    update : collections.abc.Callable[[], None]
        Requests a repaint of the page.
    on_change_vault : collections.abc.Callable[[], collections.abc.Awaitable[None]]
        Command that opens an existing vault.
    on_create_vault : collections.abc.Callable[[], collections.abc.Awaitable[None]]
        Command that creates a new vault.
    on_close_vault : collections.abc.Callable[[], collections.abc.Awaitable[None]]
        Command that closes the current vault.
    on_new_reference : collections.abc.Callable[[], collections.abc.Awaitable[None]] | None
        Command that opens the new-reference dialog.
    pick_date : afanes.ui.views.page.PickDate | None
        Command that opens the date picker for step and project dates.
    on_log_entry : collections.abc.Callable[[afanes.models.note.NoteDate], collections.abc.Awaitable[None]] | None
        Command that opens or creates a log entry for a date.
    on_missing_role : collections.abc.Callable[[str], collections.abc.Awaitable[None]] | None
        Command that asks for a category before creating a missing role.
    pick_role : afanes.ui.views.page.PickRole | None
        Command that asks for an owner or requester name in read mode.
    on_about : collections.abc.Callable[[], collections.abc.Awaitable[None]] | None
        Command that shows the About dialog.
    on_notice : collections.abc.Callable[[afanes.ui.state.status.Notice], None] | None
        Command that shows one transient notice, or ``None`` when the view is
        used without a toast presenter.
    """

    update: Callable[[], None]
    on_change_vault: Callable[[], Awaitable[None]]
    on_create_vault: Callable[[], Awaitable[None]]
    on_close_vault: Callable[[], Awaitable[None]]
    on_new_reference: Callable[[], Awaitable[None]] | None = None
    pick_date: afanes.ui.views.page.PickDate | None = None
    on_log_entry: Callable[[NoteDate], Awaitable[None]] | None = None
    on_missing_role: Callable[[str], Awaitable[None]] | None = None
    pick_role: afanes.ui.views.page.PickRole | None = None
    on_about: Callable[[], Awaitable[None]] | None = None
    on_notice: Callable[[afanes.ui.state.status.Notice], None] | None = None


class WorkspaceView:
    """Browser sidebar, capture bar, and a main area for focused work.

    Parameters
    ----------
    actions : WorkspaceActions
        Callbacks and pickers supplied by the application shell.
    """

    def __init__(self, actions: WorkspaceActions) -> None:
        """Build the workspace controls against the shared application state.

        Parameters
        ----------
        actions : WorkspaceActions
            Callbacks and pickers supplied by the application shell.
        """
        self._state = afanes.ui.state.app_state
        self._update = actions.update
        self._on_change_vault = actions.on_change_vault
        self._on_create_vault = actions.on_create_vault
        self._on_close_vault = actions.on_close_vault
        self._on_new_reference = actions.on_new_reference
        self._on_log_entry = actions.on_log_entry
        self._on_about = actions.on_about
        self._pick_date = actions.pick_date
        self._on_missing_role = actions.on_missing_role
        self._pick_role = actions.pick_role
        self._on_notice = actions.on_notice
        self.log_calendar: afanes.ui.components.calendar.LogCalendar | None = None
        self.log_tree: afanes.ui.components.log_tree.LogTree | None = None
        self.log_today_button: ft.TextButton | None = None
        self.log_entries_button: ft.TextButton | None = None
        self.log_everything_button: ft.TextButton | None = None
        self._processing_view: afanes.ui.views.processing.ProcessingView | None = None
        self._processing_key: tuple[Path | None, Path | None] | None = None
        self._projects_view: afanes.ui.views.projects.ProjectsView | None = None
        self._review_view: afanes.ui.views.review.ReviewView | None = None
        self._breakpoint = "wide"
        self._drawer_open = False
        self._show_detail = False
        self._build_header()
        self._build_navigation()
        self._build_browser()
        self._build_detail()
        self._render_shell()
        self._refresh_dynamic()

    def _build_header(self) -> None:
        """Build the toolbar, capture bar, and primary menu."""
        self.progress = ft.ProgressRing(
            width=16,
            height=16,
            visible=False,
            semantics_label=afanes.ui.strings.WORKING,
        )
        self.vault_text = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["heading"],
            selectable=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )
        self.refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH_OUTLINED,
            tooltip=afanes.ui.strings.REFRESH_ACTION,
            on_click=self._refresh,
            key="workspace-refresh",
        )
        self.new_reference_button = ft.IconButton(
            icon=ft.Icons.ADD_OUTLINED,
            tooltip=afanes.ui.strings.BROWSER_NEW_REFERENCE,
            on_click=self._new_reference,
            visible=False,
            key="browser-new-reference",
        )
        self.change_button = ft.PopupMenuButton(
            icon=ft.Icons.FOLDER_OPEN_OUTLINED,
            tooltip=afanes.ui.strings.MAIN_MENU,
            items=[
                ft.PopupMenuItem(
                    content=afanes.ui.strings.CHANGE_VAULT_OPEN,
                    on_click=self._change_vault,
                    key="workspace-change-open",
                ),
                ft.PopupMenuItem(
                    content=afanes.ui.strings.CHANGE_VAULT_CREATE,
                    on_click=self._create_vault,
                    key="workspace-change-create",
                ),
                ft.PopupMenuItem(
                    content=afanes.ui.strings.CLOSE_VAULT_ACTION,
                    on_click=self._close_vault,
                    key="workspace-close-vault",
                ),
                ft.PopupMenuItem(
                    content=afanes.ui.strings.ABOUT_ACTION,
                    on_click=self._about,
                    key="workspace-about",
                ),
            ],
            key="workspace-change",
        )
        self.drawer_close_button = ft.IconButton(
            icon=ft.Icons.CLOSE_OUTLINED,
            tooltip=afanes.ui.strings.CLOSE_NAVIGATION,
            on_click=self._close_drawer,
            visible=False,
            key="workspace-drawer-close",
        )
        self.nav_toggle = ft.IconButton(
            icon=ft.Icons.MENU_OUTLINED,
            tooltip=afanes.ui.strings.WORKSPACE_NAVIGATION,
            on_click=self._open_drawer,
            visible=False,
            key="workspace-navigation-toggle",
        )
        self.new_capture_button = ft.IconButton(
            icon=ft.Icons.NOTE_ADD_OUTLINED,
            tooltip=afanes.ui.strings.NEW_CAPTURE_ACTION,
            on_click=self._new_capture,
            key="workspace-new-capture",
        )
        self.capture = afanes.ui.components.capture_bar.CaptureBar(self._capture, self._capture_changed)
        self.capture_field = self.capture.field
        self.capture_button = self.capture.button
        self.capture_actions = self.capture.actions
        self.capture_label = self.capture.label
        self.capture_section = self.capture.section

    def _build_navigation(self) -> None:
        """Build the review entry and section navigation."""
        self.review_count = ft.Text("", style=afanes.ui.theme.TEXT_ROLES["caption"])
        self.review_icon = ft.Icon(ft.Icons.PLAY_ARROW_OUTLINED, color=afanes.ui.theme.SECTION_ICON_COLOR)
        self.review_tile = ft.ListTile(
            title=afanes.ui.strings.REVIEW_TITLE,
            leading=self.review_icon,
            trailing=self.review_count,
            selected=False,
            on_click=self._select_review,
            key="review-entry",
        )
        self.review_edge = ft.Container(content=self.review_tile, border_radius=afanes.ui.theme.SURFACE_RADIUS)
        self.section_counts: dict[afanes.ui.state.browser.WorkspaceSection, ft.Text] = {}
        self.section_icons: dict[afanes.ui.state.browser.WorkspaceSection, ft.Icon] = {}
        self.section_tiles: dict[afanes.ui.state.browser.WorkspaceSection, ft.ListTile] = {}
        self.section_edges: dict[afanes.ui.state.browser.WorkspaceSection, ft.Container] = {}
        for section in afanes.ui.state.browser.WorkspaceSection:
            if section is afanes.ui.state.browser.WorkspaceSection.REVIEW:
                continue
            self.section_counts[section] = ft.Text("", style=afanes.ui.theme.TEXT_ROLES["caption"])
            self.section_icons[section] = ft.Icon(_SECTION_ICONS[section], color=afanes.ui.theme.SECTION_ICON_COLOR)
            tile = ft.ListTile(
                title=afanes.ui.strings.WORKSPACE_SECTION_LABELS[section.value],
                leading=self.section_icons[section],
                trailing=self.section_counts[section],
                selected=False,
                on_click=self._section_handler(section),
                key=f"section-{section.value}",
            )
            self.section_tiles[section] = tile
            self.section_edges[section] = ft.Container(content=tile, border_radius=afanes.ui.theme.SURFACE_RADIUS)

        self.navigation_header = ft.Container(
            height=afanes.ui.theme.HEADER_HEIGHT,
            content=ft.Row(
                controls=[self.vault_text, self.change_button, self.drawer_close_button],
                spacing=afanes.ui.theme.ITEM_GAP,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        self.navigation = ft.Container(
            width=afanes.ui.theme.NAVIGATION_WIDTH,
            bgcolor=afanes.ui.theme.REGION_SURFACE_COLOR,
            content=ft.Column(
                controls=[
                    self.navigation_header,
                    ft.Divider(height=afanes.ui.theme.BORDER_WIDTH),
                    self.review_edge,
                    *self.section_edges.values(),
                ],
                spacing=0,
                expand=True,
            ),
            key="workspace-navigation",
        )

    def _build_browser(self) -> None:
        """Build the browser search, header, and list."""
        self.search_field = ft.TextField(
            hint_text=afanes.ui.strings.BROWSER_SEARCH_HINT,
            prefix_icon=ft.Icons.SEARCH_OUTLINED,
            expand=True,
            on_change=self._search,
            key="browser-search",
        )
        self.browser_search_clear = ft.IconButton(
            icon=ft.Icons.CLOSE_OUTLINED,
            tooltip=afanes.ui.strings.BROWSER_SEARCH_CLEAR,
            on_click=self._clear_search,
            visible=False,
            key="browser-search-clear",
        )
        self.browser_search_bar = ft.Container(
            height=afanes.ui.theme.HEADER_HEIGHT,
            content=ft.Row(
                controls=[self.search_field, self.browser_search_clear],
                spacing=afanes.ui.theme.ITEM_GAP,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            key="browser-search-bar",
        )
        self.browser_list = ft.ListView(
            controls=[],
            expand=True,
            spacing=0,
            padding=0,
            key="browser-list",
        )
        self.failures_column = ft.Column(controls=[], spacing=0, visible=False)
        self.browser_title = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["title-4"],
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )
        self.browser_actions = ft.Row(controls=[], spacing=afanes.ui.theme.ITEM_GAP)
        self.browser_header = ft.Container(
            height=afanes.ui.theme.HEADER_HEIGHT,
            content=ft.Row(
                controls=[
                    self.nav_toggle,
                    self.browser_title,
                    self.refresh_button,
                    self.browser_actions,
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            key="browser-header",
        )
        self.browser_body = ft.Column(
            controls=[
                self.capture_section,
                ft.Container(content=self.browser_list, expand=True),
                self.failures_column,
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
            expand=True,
        )
        self.browser_divider = ft.Divider(height=afanes.ui.theme.BORDER_WIDTH, key="browser-divider")
        self.browser_top = ft.Column(
            controls=[self.browser_header, self.browser_search_bar, self.browser_divider],
            spacing=afanes.ui.theme.NO_GAP,
            key="browser-top",
        )
        self.browser_region = ft.Container(
            width=afanes.ui.theme.BROWSER_MAX_WIDTH,
            bgcolor=afanes.ui.theme.PAGE_SURFACE_COLOR,
            content=ft.Column(
                controls=[self.browser_top, self.browser_body],
                spacing=afanes.ui.theme.SECTION_GAP,
                expand=True,
            ),
            key="workspace-browser",
        )

    def _build_detail(self) -> None:
        """Build the detail pane and the root shell."""
        self.banners = ft.Column(controls=[], spacing=afanes.ui.theme.ITEM_GAP)
        self.page_view = afanes.ui.views.page.PageView(
            afanes.ui.views.page.PageActions(
                update=self._on_page_update,
                on_process=self._process_note,
                pick_date=self._pick_date,
                on_missing_role=self._on_missing_role,
                pick_role=self._pick_role,
                on_back=self._back_to_browser_if_empty,
            )
        )
        self.detail_title = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["title-3"],
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )
        self.detail_back_button = ft.IconButton(
            icon=ft.Icons.ARROW_BACK_OUTLINED,
            tooltip=afanes.ui.strings.PAGE_BACK,
            on_click=self._back_to_browser,
            visible=False,
            key="workspace-detail-back",
        )
        self.detail_flow = ft.Row(
            controls=[self.detail_back_button, self.detail_title],
            spacing=afanes.ui.theme.ITEM_GAP,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        self.detail_host = ft.Container(expand=True)
        self.detail_bar = ft.Container(
            height=afanes.ui.theme.HEADER_HEIGHT,
            content=ft.Row(
                controls=[self.detail_host, self.new_capture_button],
                spacing=afanes.ui.theme.ITEM_GAP,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            key="workspace-detail-toolbar",
        )
        self.main_host = ft.Container(expand=True)
        self.detail_region = ft.Container(
            expand=True,
            content=ft.Column(
                controls=[self.detail_bar, self.main_host],
                spacing=afanes.ui.theme.ITEM_GAP,
                expand=True,
            ),
            key="workspace-detail",
        )
        self.shell_row = ft.Row(
            controls=[],
            spacing=afanes.ui.theme.WORKSPACE_BODY_GAP,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            expand=True,
        )
        self.shell_column = ft.Column(
            controls=[self.banners, self.shell_row],
            spacing=afanes.ui.theme.ITEM_GAP,
            expand=True,
        )
        self.root = ft.Stack(
            controls=[self.shell_column],
            expand=True,
            fit=ft.StackFit.EXPAND,
            key="workspace-view",
        )

    def resize(self, width: int) -> None:
        """Choose the shell arrangement for one available width.

        Parameters
        ----------
        width : int
            Viewport width in logical pixels.

        Notes
        -----
        The open page, active destination, and search query are retained; only
        the column arrangement changes.
        """
        if width >= afanes.ui.theme.SHELL_WIDE_MIN:
            arrangement = "wide"
        elif width >= afanes.ui.theme.SHELL_MEDIUM_MIN:
            arrangement = "medium"
        else:
            arrangement = "narrow"
        self._breakpoint = arrangement
        self._render_shell()
        self._update()

    def close_drawer(self) -> None:
        """Close the transient navigation drawer."""
        if not self._drawer_open:
            return
        self._drawer_open = False
        self._render_shell()
        self._update()

    def _render_shell(self) -> None:
        """Arrange the shell controls for the stored breakpoint."""
        wide = self._breakpoint == "wide"
        narrow = self._breakpoint == "narrow"
        if wide:
            self._drawer_open = False
        self.nav_toggle.visible = not wide
        self.drawer_close_button.visible = not wide
        if wide:
            self.navigation.border = ft.Border.all(
                afanes.ui.theme.BORDER_WIDTH,
                afanes.ui.theme.BORDER_COLOR,
            )
            self.navigation.border_radius = afanes.ui.theme.SURFACE_RADIUS
            self.navigation.shadow = None
            self.navigation.padding = afanes.ui.theme.NAVIGATION_PADDING
            self.navigation.left = None
            self.navigation.top = None
            self.navigation.bottom = None
            self.navigation.width = afanes.ui.theme.NAVIGATION_WIDTH
        else:
            self.navigation.border = ft.Border.all(
                afanes.ui.theme.BORDER_WIDTH,
                afanes.ui.theme.BORDER_COLOR,
            )
            self.navigation.border_radius = afanes.ui.theme.SURFACE_RADIUS
            self.navigation.shadow = afanes.ui.theme.DRAWER_SHADOW
            self.navigation.padding = afanes.ui.theme.ITEM_GAP
            self.navigation.left = afanes.ui.theme.PAGE_PADDING
            self.navigation.top = afanes.ui.theme.PAGE_PADDING
            self.navigation.bottom = afanes.ui.theme.PAGE_PADDING
            self.navigation.width = afanes.ui.theme.DRAWER_WIDTH
        if wide:
            self.browser_region.width = afanes.ui.theme.BROWSER_MAX_WIDTH
            self.browser_region.expand = False
            self.shell_row.controls = [self.navigation, self.browser_region, self.detail_region]
        elif narrow:
            self.browser_region.width = None
            self.browser_region.expand = True
            self.shell_row.controls = [self.detail_region if self._show_detail else self.browser_region]
        else:
            self.browser_region.width = afanes.ui.theme.BROWSER_MAX_WIDTH
            self.browser_region.expand = False
            self.shell_row.controls = [self.browser_region, self.detail_region]
        overlay = self._drawer_control() if self._drawer_open and not wide else None
        self.root.controls = [self.shell_column] if overlay is None else [self.shell_column, overlay]
        if self._breakpoint == "narrow":
            self.detail_back_button.visible = self._show_detail

    def _drawer_control(self) -> ft.Control:
        """Return the transient navigation overlay with its scrim."""
        return ft.Stack(
            controls=[
                ft.Container(
                    expand=True,
                    bgcolor=afanes.ui.theme.DRAWER_SCRIM_COLOR,
                    on_click=self._close_drawer,
                    key="workspace-drawer-scrim",
                ),
                self.navigation,
            ],
            expand=True,
            fit=ft.StackFit.EXPAND,
            key="workspace-drawer",
        )

    async def _open_drawer(self) -> None:
        """Open the transient navigation drawer."""
        self._drawer_open = True
        self._render_shell()
        self._update()

    async def _close_drawer(self) -> None:
        """Close the transient navigation drawer from its scrim."""
        self.close_drawer()

    async def _back_to_browser(self) -> None:
        """Show the browser in a one-region layout."""
        self._show_detail = False
        self._render_shell()
        self._update()

    async def _back_to_browser_if_empty(self) -> bool:
        """Return to the browser when the detail has no page history.

        Returns
        -------
        bool
            ``True`` when this shell handled the back request.
        """
        if self._breakpoint == "narrow" and self._show_detail and not self._state.navigation.history:
            await self._back_to_browser()
            return True
        return False

    def build(self) -> ft.Control:
        """Return the root control for the workspace.

        Returns
        -------
        ft.Control
            Composed workspace layout.
        """
        return self.root

    def refresh(self) -> None:
        """Rebuild the dynamic lists from state and repaint once.

        Notes
        -----
        The shell calls this only when a background refresh reports a change.
        It reads the retained controller state and performs no file I/O.
        """
        self._refresh_dynamic()
        self._update()

    async def _capture(self) -> None:
        """Capture the current field text and refresh the browser."""
        text = self.capture_field.value or ""
        self._set_working(working=True)
        try:
            path = await self._state.session.capture(text)
        finally:
            self._set_working(working=False)
        if path is not None:
            self.capture_field.value = ""
        self._refresh_capture_action()
        self._refresh_dynamic()
        self._update()

    def _capture_available(self) -> bool:
        """Return whether the composer has non-blank text."""
        return bool((self.capture_field.value or "").strip())

    def _refresh_capture_action(self) -> None:
        """Disable Capture while the composer is blank."""
        self.capture_button.disabled = not self._capture_available()

    async def _capture_changed(self) -> None:
        """Track the composer text as it changes."""
        self._refresh_capture_action()
        self._update()

    async def _refresh(self) -> None:
        """Re-read the vault and refresh the browser."""
        self._set_working(working=True)
        try:
            await self._state.workspace.refresh()
        finally:
            self._set_working(working=False)
        self._refresh_dynamic()
        self._update()

    async def _change_vault(self) -> None:
        """Delegate a vault change to the application shell."""
        self._set_working(working=True)
        try:
            await self._on_change_vault()
        finally:
            self._set_working(working=False)

    async def _create_vault(self) -> None:
        """Delegate new-vault creation to the application shell."""
        self._set_working(working=True)
        try:
            await self._on_create_vault()
        finally:
            self._set_working(working=False)

    async def _close_vault(self) -> None:
        """Delegate closing the current vault to the application shell."""
        self._set_working(working=True)
        try:
            await self._on_close_vault()
        finally:
            self._set_working(working=False)

    async def _new_reference(self) -> None:
        """Open the new-reference dialog through the application shell."""
        if self._on_new_reference is None:
            return
        self._set_working(working=True)
        try:
            await self._on_new_reference()
        finally:
            self._set_working(working=False)

    async def _about(self) -> None:
        """Show the About dialog through the application shell."""
        if self._on_about is None:
            return
        await self._on_about()

    async def start_capture(self) -> None:
        """Switch to the Inbox and focus the capture composer."""
        await self._state.browser.set_section(afanes.ui.state.browser.WorkspaceSection.INBOX)
        self._refresh_dynamic()
        self._update()
        await self._focus_capture()

    async def _new_capture(self) -> None:
        """Run the New Capture command from the toolbar."""
        await self.start_capture()

    async def focus_search(self) -> None:
        """Focus the permanent browser search entry."""
        await self._focus(self.search_field)

    async def clear_search(self) -> bool:
        """Clear the browser search query.

        Returns
        -------
        bool
            ``True`` when a non-empty query was cleared, ``False`` when the
            browser was already showing the active destination.
        """
        if not self._searching():
            return False
        await self._state.browser.set_query("")
        self.search_field.value = ""
        self._refresh_dynamic()
        self._update()
        await self._focus(self.search_field)
        return True

    async def _clear_search(self) -> None:
        """Clear the browser search from the row action."""
        await self.clear_search()

    async def _focus_capture(self) -> None:
        """Focus the capture composer when the control is attached."""
        await self._focus(self.capture_field)

    async def _focus(self, control: ft.TextField) -> None:
        """Focus one text field, ignoring an unattached control."""
        try:
            await control.focus()
        except RuntimeError:
            return

    async def _select(self, path: Path) -> None:
        """Open one browser entry in the page pane."""
        self._set_working(working=True)
        try:
            await self._state.navigation.open_page(path)
        finally:
            self._set_working(working=False)
        self._show_detail = True
        self._render_shell()
        self._refresh_dynamic()
        self._update()
        await self.page_view.scroll_to_top()

    async def _select_section(self, section: afanes.ui.state.browser.WorkspaceSection) -> None:
        """Switch the browser to one section."""
        await self._state.browser.set_section(section)
        self._drawer_open = False
        self._show_detail = False
        self._render_shell()
        self._refresh_dynamic()
        self._update()

    async def _select_review(self) -> None:
        """Open the review destination."""
        await self._state.browser.set_section(afanes.ui.state.browser.WorkspaceSection.REVIEW)
        self._drawer_open = False
        self._show_detail = True
        self._render_shell()
        self._refresh_dynamic()
        self._update()

    async def _search(self) -> None:
        """Apply the browser search text."""
        await self._state.browser.set_query(self.search_field.value or "")
        self._refresh_dynamic()
        self._update()

    async def _process_note(self, path: Path) -> None:
        """Open the Processing Wizard for one inbox capture."""
        opened = await self._state.processing.begin(path)
        if opened:
            self._show_detail = True
            self._render_shell()
            self._refresh_dynamic()
            self._update()

    async def _cancel_processing(self) -> None:
        """Close the Processing Wizard without writing."""
        self._state.processing.cancel()
        self._refresh_dynamic()
        self._update()

    async def _finish_processing(self) -> None:
        """Close the Processing Wizard success state."""
        self._state.processing.finish()
        self._show_detail = False
        self._render_shell()
        self._refresh_dynamic()
        self._update()

    def _on_page_update(self) -> None:
        """Refresh the workspace after a page command changes state.

        Notes
        -----
        Any page command means the detail is the region the user is working in.
        Marking it here keeps an edit, a link, or a page action visible when the
        window later collapses to the one-region presentation.
        """
        self._show_detail = True
        self._refresh_dynamic()
        self._update()

    def _on_processing_update(self) -> None:
        """Refresh the workspace after a processing command changes state."""
        self._refresh_dynamic()
        self._update()

    def _on_review_update(self) -> None:
        """Refresh the workspace after a review command changes state."""
        self._refresh_dynamic()
        self._update()

    def _set_working(self, *, working: bool) -> None:
        """Disable controls and show progress while a command runs."""
        self._own_controls()
        self.progress.visible = working
        self.capture_button.disabled = working or not self._capture_available()
        self.refresh_button.disabled = working
        self.change_button.disabled = working
        self.new_reference_button.disabled = working
        self.new_capture_button.disabled = working
        self.nav_toggle.disabled = working
        self.capture_field.read_only = working
        if self.log_today_button is not None:
            self.log_today_button.disabled = working
        self._set_section_tiles_disabled(disabled=working)
        self._update()

    def _own_controls(self) -> None:
        """Clear stale toolkit freeze markers from this workspace's controls.

        Notes
        -----
        Flet 1.1.x can mark an imperative control as immutable while reconciling
        a keyed update. Every control under :attr:`root` belongs to this view, so
        a marker on one of them is stale and makes the next assignment raise.
        The shared recovery helper reads control metadata only and never reads or
        writes the vault.
        """
        FrozenControlRecovery.clear(self.root)

    def _set_section_tiles_disabled(self, *, disabled: bool) -> None:
        """Enable or disable the section entries during a command."""
        for tile in self.section_tiles.values():
            tile.disabled = disabled
        self.review_tile.disabled = disabled

    def _refresh_dynamic(self) -> None:
        """Refresh counts, browser entries, banners, and the main area."""
        self._own_controls()
        state = self._state
        root = state.session.vault_root
        self.vault_text.value = root.name if root is not None else ""
        self.vault_text.tooltip = str(root) if root is not None else None
        listing = state.browser.listing()
        counts = state.browser.counts()
        for section, tile in self.section_tiles.items():
            self.section_counts[section].value = str(counts.get(section, 0))
            active = state.browser.active_section is section
            tile.selected = active
            self.section_icons[section].color = afanes.ui.theme.SECTION_ICON_COLOR
        review_active = state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.REVIEW
        self.review_count.value = afanes.ui.strings.CopyFormatter.review_pending(state.browser.pending_count())
        self.review_tile.selected = review_active
        self.review_icon.color = afanes.ui.theme.SECTION_ICON_COLOR
        self.search_field.value = state.browser.query
        searching = self._searching()
        self.browser_search_clear.visible = searching
        self._refresh_browser_header()
        self.capture_section.visible = (
            not searching and state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.INBOX
        )
        self.browser_list.controls = self._browser_controls(listing)
        self._refresh_failures()
        self._refresh_banners()
        self._consume_notice()
        self._refresh_main()
        self.progress.visible = state.status.busy

    def _searching(self) -> bool:
        """Return whether a non-empty query is showing global results."""
        return bool(self._state.browser.query.strip())

    def _refresh_browser_header(self) -> None:
        """Refresh the browser title and the destination actions."""
        state = self._state
        section = state.browser.active_section
        searching = self._searching()
        if searching:
            title = afanes.ui.strings.BROWSER_SEARCH_TITLE
        elif section is afanes.ui.state.browser.WorkspaceSection.REVIEW:
            title = afanes.ui.strings.REVIEW_TITLE
        else:
            title = afanes.ui.strings.WORKSPACE_SECTION_LABELS[section.value]
        self.browser_title.value = title
        references = section is afanes.ui.state.browser.WorkspaceSection.REFERENCES and not searching
        self.new_reference_button.visible = references
        self.browser_actions.controls = [self.new_reference_button] if references else []

    def _browser_controls(
        self,
        listing: afanes.core.search.BrowserListing | None,
    ) -> list[ft.Control]:
        """Build the browser entries for the active destination or search."""
        state = self._state
        if self._searching():
            return self._search_controls(listing)
        if state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.REVIEW:
            return self._review_queue_controls()
        if state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.PROJECTS:
            if self._projects_view is None:
                self._projects_view = afanes.ui.views.projects.ProjectsView(self._update, self._select)
            self._projects_view.refresh()
            return [self._projects_view.root]
        if state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.LOG:
            return self._log_controls()
        return self._section_controls(state.browser.active_section, listing)

    def _section_controls(
        self,
        active_section: afanes.ui.state.browser.WorkspaceSection,
        listing: afanes.core.search.BrowserListing | None,
    ) -> list[ft.Control]:
        """Build the browser entries for a non-special destination."""
        section = active_section.browser_section
        if listing is None or section is None:
            return []
        if section is afanes.core.search.BrowserSection.REFERENCES:
            return self._reference_controls(listing.groups_for(section))
        return self._flat_controls(listing.groups_for(section))

    def _reference_controls(self, groups: tuple[afanes.core.search.BrowserGroup, ...]) -> list[ft.Control]:
        """Build the categorized reference list for the References section."""
        controls: list[ft.Control] = []
        for group in groups:
            if not group.notes:
                continue
            controls.append(
                ft.Container(
                    padding=afanes.ui.theme.ITEM_GAP,
                    content=ft.Text(
                        group.title,
                        style=afanes.ui.theme.TEXT_ROLES["caption-heading"],
                    ),
                )
            )
            controls.extend(self._note_row(note) for note in group.notes)
        if not controls:
            controls.append(self._empty_message(afanes.ui.strings.BROWSER_EMPTY))
        return controls

    def _flat_controls(self, groups: tuple[afanes.core.search.BrowserGroup, ...]) -> list[ft.Control]:
        """Build the flat note list for Inbox or Needs attention."""
        notes = groups[0].notes if groups else ()
        if not notes:
            return [self._empty_message(afanes.ui.strings.BROWSER_EMPTY)]
        return [self._note_row(note) for note in notes]

    def _empty_message(self, message: str) -> ft.Control:
        """Build one muted empty-state message."""
        return ft.Container(
            padding=afanes.ui.theme.ITEM_GAP,
            content=ft.Text(message, color=afanes.ui.theme.MUTED_TEXT_COLOR, selectable=True),
        )

    def _search_controls(
        self,
        listing: afanes.core.search.BrowserListing | None,
    ) -> list[ft.Control]:
        """Build section-grouped search results across every destination."""
        state = self._state
        controls: list[ft.Control] = []
        matched = False
        if listing is not None:
            for section in (
                afanes.core.search.BrowserSection.INBOX,
                afanes.core.search.BrowserSection.PROJECTS,
                afanes.core.search.BrowserSection.REFERENCES,
            ):
                notes = [note for group in listing.groups_for(section) for note in group.notes]
                if not notes:
                    continue
                matched = True
                controls.append(self._heading(afanes.ui.strings.WORKSPACE_SECTION_LABELS[section.value], len(notes)))
                controls.extend(self._note_row(note) for note in notes)
        timeline = state.browser.timeline()
        log_entries = timeline.entries() if timeline is not None else ()
        if log_entries:
            matched = True
            controls.append(self._heading(afanes.ui.strings.WORKSPACE_SECTION_LABELS["log"], len(log_entries)))
        controls.extend(self._note_row(note) for note in log_entries)
        if listing is not None:
            misplaced = listing.group(afanes.core.search.BrowserSection.NEEDS_ATTENTION).notes
            if misplaced:
                matched = True
                controls.append(
                    self._heading(
                        afanes.ui.strings.WORKSPACE_SECTION_LABELS[
                            afanes.core.search.BrowserSection.NEEDS_ATTENTION.value
                        ],
                        len(misplaced),
                    )
                )
                controls.extend(self._note_row(note) for note in misplaced)
        if not matched:
            return [
                self._empty_message(afanes.ui.strings.BROWSER_NO_MATCH_QUERY.format(query=state.browser.query.strip()))
            ]
        return controls

    @staticmethod
    def _heading(label: str, count: int) -> ft.Control:
        """Build one search-result section heading with its match count."""
        return ft.Container(
            padding=afanes.ui.theme.ITEM_GAP,
            content=ft.Text(
                f"{label} ({count})",
                style=afanes.ui.theme.TEXT_ROLES["caption-heading"],
            ),
        )

    def _review_queue_controls(self) -> list[ft.Control]:
        """Build the selectable snapshot queue for the active review session."""
        state = self._state
        session = state.review.review_session
        if session is None:
            return [
                ft.Container(
                    padding=afanes.ui.theme.ITEM_GAP,
                    content=ft.Text(
                        afanes.ui.strings.CopyFormatter.review_pending(state.browser.pending_count()),
                        color=afanes.ui.theme.MUTED_TEXT_COLOR,
                    ),
                )
            ]
        return [
            self._review_card(index, item, current=index == session.index) for index, item in enumerate(session.items)
        ]

    def _review_card(
        self,
        index: int,
        item: afanes.core.search.ReviewItem,
        *,
        current: bool,
    ) -> ft.Control:
        """Build one clickable review queue card."""
        kind = afanes.ui.strings.REVIEW_KIND_LABELS[item.kind.value]
        details: list[ft.Control] = [
            ft.Text(kind, style=afanes.ui.theme.TEXT_ROLES["caption"]),
        ]
        if current:
            details.append(
                ft.Text(
                    afanes.ui.strings.REVIEW_CURRENT,
                    style=afanes.ui.theme.TEXT_ROLES["caption-heading"],
                )
            )
        return ft.Container(
            key=f"review-queue-{index}",
            bgcolor=afanes.ui.theme.SELECTED_ROW_COLOR if current else afanes.ui.theme.SURFACE_CONTAINER_COLOR,
            border=ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR),
            border_radius=afanes.ui.theme.SURFACE_RADIUS,
            padding=afanes.ui.theme.ITEM_GAP,
            on_click=self._review_select_handler(index),
            content=ft.Column(
                controls=[
                    ft.Text(self._review_item_title(item), style=afanes.ui.theme.TEXT_ROLES["heading"]),
                    ft.Row(
                        controls=details,
                        spacing=afanes.ui.theme.ITEM_GAP,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=afanes.ui.theme.BORDER_WIDTH,
            ),
        )

    def _review_select_handler(self, index: int) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler that makes one queue item current."""

        async def handle() -> None:
            selected = await self._state.review.select(index)
            if selected:
                self._show_detail = True
                self._render_shell()
                if self._review_view is not None:
                    self._review_view.reset_transient_state()
            self._refresh_dynamic()
            self._update()

        return handle

    def _review_item_title(self, item: afanes.core.search.ReviewItem) -> str:
        """Return the display title for one review queue item."""
        if item.kind is afanes.core.search.ReviewItemKind.INBOX:
            note = next((note for note in self._state.session.notes if note.path == item.path), None)
            return note.title if note is not None else item.path.stem
        if item.step is not None:
            return item.step.text
        if item.project is not None:
            return item.project.note.title
        return item.path.stem

    @staticmethod
    def _today() -> datetime.date:
        """Return the local calendar date used by the Log shortcuts.

        Returns
        -------
        datetime.date
            Current local calendar date.
        """
        return datetime.datetime.now(tz=datetime.UTC).astimezone().date()

    async def open_note(self, path: Path) -> None:
        """Open one note in the page pane.

        Parameters
        ----------
        path : Path
            Note path to open.
        """
        await self._select(path)

    async def open_today_log(self) -> None:
        """Open or create today's log entry."""
        await self._log_today()

    async def open_log_day(self, day: int) -> None:
        """Open, expand, or create a calendar day.

        Parameters
        ----------
        day : int
            Calendar day.
        """
        await self._log_select_day(day)

    async def show_log_mode(self, mode: str) -> None:
        """Select the Log mode.

        Parameters
        ----------
        mode : str
            ``entries`` or ``everything``.
        """
        if mode == "entries":
            await self._log_entries()
        else:
            await self._log_everything()

    async def open_log_month(self, year: int, month: int) -> None:
        """Open or create the entry for a whole month.

        Parameters
        ----------
        year : int
            Calendar year.
        month : int
            Calendar month.
        """
        await self._log_create_month(year, month)

    def _log_controls(self) -> list[ft.Control]:
        """Build the calendar, mode switch, and date tree for the Log."""
        state = self._state
        timeline = state.browser.timeline()
        if timeline is None:
            return []
        today = self._today()
        year = state.browser.log_year if state.browser.log_year is not None else today.year
        month = state.browser.log_month if state.browser.log_month is not None else today.month
        selected_day = None
        if (
            state.browser.log_year is not None
            and state.browser.log_month is not None
            and state.browser.log_day is not None
        ):
            selected_day = (state.browser.log_year, state.browser.log_month, state.browser.log_day)
        self.log_entries_button = self._log_mode_button(
            afanes.ui.strings.LOG_MODE_ENTRIES,
            active=state.browser.log_mode is afanes.core.log.LogMode.ENTRIES,
            on_click=self._log_entries,
            key="log-mode-entries",
        )
        self.log_everything_button = self._log_mode_button(
            afanes.ui.strings.LOG_MODE_EVERYTHING,
            active=state.browser.log_mode is afanes.core.log.LogMode.EVERYTHING,
            on_click=self._log_everything,
            key="log-mode-everything",
        )
        self.log_today_button = ft.TextButton(
            content=afanes.ui.strings.LOG_TODAY_ENTRY,
            on_click=self._log_today,
            key="log-today-entry",
        )
        self.log_calendar = afanes.ui.components.calendar.LogCalendar(
            lambda day: asyncio.create_task(self._log_select_day(day)),
            lambda: asyncio.create_task(self._log_previous_month()),
            lambda: asyncio.create_task(self._log_next_month()),
        )
        self.log_tree = afanes.ui.components.log_tree.LogTree(
            lambda path: asyncio.create_task(self._select(path)),
            lambda year, month: asyncio.create_task(self._log_create_month(year, month)),
            lambda year: asyncio.create_task(self._log_create_year(year)),
            selected_day,
        )
        calendar_month = timeline.calendar(year, month)
        return [
            ft.Row(
                controls=[self.log_today_button],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
            ft.Row(
                controls=[self.log_entries_button, self.log_everything_button],
                spacing=0,
            ),
            ft.Container(
                padding=afanes.ui.theme.ITEM_GAP,
                content=self.log_calendar.build(calendar_month),
            ),
            ft.Divider(height=1),
            self.log_tree.build(timeline),
        ]

    @staticmethod
    def _log_mode_button(
        label: str,
        *,
        active: bool,
        on_click: Callable[[], Awaitable[None]],
        key: str,
    ) -> ft.TextButton:
        """Build one Log mode control with an active tint."""
        return ft.TextButton(
            content=label,
            on_click=on_click,
            key=key,
            style=ft.ButtonStyle(
                bgcolor=afanes.ui.theme.SELECTED_ROW_COLOR if active else None,
            ),
        )

    async def _log_entries(self) -> None:
        """Switch the Log to Entries mode."""
        await self._state.workspace.set_log_mode("entries")
        self._refresh_dynamic()
        self._update()

    async def _log_everything(self) -> None:
        """Switch the Log to Everything mode."""
        await self._state.workspace.set_log_mode("everything")
        self._refresh_dynamic()
        self._update()

    async def _log_today(self) -> None:
        """Open or create today's log entry."""
        await self._open_log_date(NoteDate.from_date(self._today()))

    async def _log_select_day(self, day: int) -> None:
        """Open, expand, or create the selected calendar day."""
        state = self._state
        timeline = state.browser.timeline()
        if timeline is None:
            return
        today = self._today()
        year = state.browser.log_year if state.browser.log_year is not None else today.year
        month = state.browser.log_month if state.browser.log_month is not None else today.month
        calendar = timeline.calendar(year, month)
        count = calendar.days[day - 1].count
        if count == 0:
            await self._open_log_date(NoteDate.from_text(f"{year:04d}-{month:02d}-{day:02d}"))
            return
        if count == 1:
            target = next(
                (
                    note
                    for note in timeline.entries()
                    if note.date is not None
                    and note.date.precision is DatePrecision.DAY
                    and note.date.year == year
                    and note.date.month == month
                    and note.date.day == day
                ),
                None,
            )
            if target is not None:
                await self._select(target.path)
                return
        state.browser.select_log_day(day)
        self._refresh_dynamic()
        self._update()

    async def _log_create_month(self, year: int, month: int) -> None:
        """Open or create the entry for a whole month."""
        await self._open_log_date(NoteDate.from_text(f"{year:04d}-{month:02d}"))

    async def _log_create_year(self, year: int) -> None:
        """Open or create the entry for a whole year."""
        await self._open_log_date(NoteDate.from_text(f"{year:04d}"))

    async def _open_log_date(self, date: NoteDate) -> None:
        """Forward a date to the log entry command."""
        if self._on_log_entry is None:
            return
        self._set_working(working=True)
        try:
            await self._on_log_entry(date)
        finally:
            self._set_working(working=False)
        self._refresh_dynamic()
        self._update()

    async def _log_previous_month(self) -> None:
        """Move the calendar one month back."""
        today = self._today()
        year = self._state.browser.log_year if self._state.browser.log_year is not None else today.year
        month = self._state.browser.log_month if self._state.browser.log_month is not None else today.month
        if month == 1:
            year, month = year - 1, 12
        else:
            month -= 1
        self._state.browser.show_log_month(year, month)
        self._refresh_dynamic()
        self._update()

    async def _log_next_month(self) -> None:
        """Move the calendar one month forward."""
        today = self._today()
        year = self._state.browser.log_year if self._state.browser.log_year is not None else today.year
        month = self._state.browser.log_month if self._state.browser.log_month is not None else today.month
        if month == _MONTHS_IN_YEAR:
            year, month = year + 1, 1
        else:
            month += 1
        self._state.browser.show_log_month(year, month)
        self._refresh_dynamic()
        self._update()

    def _note_row(self, note: VaultNote) -> ft.Control:
        """Build one clickable browser entry."""
        page = self._state.pages.page
        selected = page is not None and page.path == note.path
        return ft.ListTile(
            title=note.title,
            subtitle=note.relative_path.as_posix(),
            leading=ft.Icons.DESCRIPTION_OUTLINED,
            selected=selected,
            on_click=self._select_handler(note.path),
        )

    def _select_handler(self, path: Path) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler to one note path."""

        async def handle() -> None:
            await self._select(path)

        return handle

    def _section_handler(
        self,
        section: afanes.ui.state.browser.WorkspaceSection,
    ) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler to one section."""

        async def handle() -> None:
            await self._select_section(section)

        return handle

    def _refresh_failures(self) -> None:
        """Refresh the unreadable-notes section."""
        failures = self._state.session.failures
        if not failures:
            self.failures_column.controls = []
            self.failures_column.visible = False
            return
        controls: list[ft.Control] = [
            ft.Divider(height=1),
            ft.Text(
                afanes.ui.strings.BROWSER_FAILURES,
                style=afanes.ui.theme.TEXT_ROLES["caption"],
                color=afanes.ui.theme.ERROR_TEXT_COLOR,
            ),
        ]
        controls.extend(self._failure_row(failure) for failure in failures)
        self.failures_column.controls = controls
        self.failures_column.visible = True

    def _failure_row(self, failure: VaultFailure) -> ft.Control:
        """Build one clickable unreadable-note entry."""
        return ft.ListTile(
            title=failure.path.as_posix(),
            leading=ft.Icons.ERROR_OUTLINE,
            on_click=self._failure_handler(failure.path),
        )

    def _failure_handler(self, path: Path) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler that opens one unreadable note."""

        async def handle() -> None:
            await self._state.navigation.open_failure(path)
            self._refresh_dynamic()
            self._update()

        return handle

    def _refresh_banners(self) -> None:
        """Refresh the persistent banners owned by the workspace states."""
        messages = (
            self._state.workspace.banner,
            self._state.session.banner,
            self._state.processing.banner,
        )
        banners = [Banner(message).build() for message in messages if message is not None]
        self.banners.controls = banners
        self.banners.visible = bool(banners)

    def _consume_notice(self) -> None:
        """Take one transient notice and forward it to the toast presenter."""
        notice = self._state.status.take_notice()
        if notice is not None and self._on_notice is not None:
            self._on_notice(notice)

    def _refresh_main(self) -> None:
        """Show the page pane, the Processing Wizard, or the review area."""
        state = self._state
        if state.processing.note is not None or state.processing.result is not None:
            key = (state.processing.note, state.processing.result)
            if self._processing_view is None or key != self._processing_key:
                self._processing_view = afanes.ui.views.processing.ProcessingView(
                    self._on_processing_update,
                    self._cancel_processing,
                    self._finish_processing,
                )
                self._processing_key = key
            self.detail_title.value = afanes.ui.strings.PROCESSING_TITLE
            self._show_flow_toolbar()
            self.main_host.content = self._processing_view.build()
            return
        self._processing_view = None
        self._processing_key = None
        if state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.REVIEW:
            if self._review_view is None:
                self._review_view = afanes.ui.views.review.ReviewView(self._on_review_update)
            self._review_view.refresh()
            self.detail_title.value = afanes.ui.strings.REVIEW_TITLE
            self._show_flow_toolbar()
            self.main_host.content = self._review_view.build()
            return
        self.page_view.refresh()
        self.detail_host.content = self.page_view.toolbar()
        if self._breakpoint == "narrow" and state.pages.page is not None:
            self.page_view.back_button.disabled = False
        self.main_host.content = self.page_view.body()

    def _show_flow_toolbar(self) -> None:
        """Show the flow title and Back control instead of the page toolbar."""
        self.detail_back_button.visible = self._breakpoint == "narrow" and self._show_detail
        self.detail_host.content = self.detail_flow
