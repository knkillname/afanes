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
import datetime
from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

import afanes.core.log
import afanes.core.search
import afanes.ui.components.calendar
import afanes.ui.components.frozen
import afanes.ui.components.log_tree
import afanes.ui.state
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


class WorkspaceView:
    """Browser sidebar, capture bar, and a main area for focused work.

    Parameters
    ----------
    update : Callable[[], None]
        Requests a repaint of the page. Tests pass a no-op or a counter.
    on_change_vault : Callable[[], Awaitable[None]]
        Command that opens an existing vault through the folder picker or the
        typed-path dialog.
    on_create_vault : Callable[[], Awaitable[None]]
        Command that asks for a new vault path and creates it.
    on_close_vault : Callable[[], Awaitable[None]]
        Command that closes the current vault and returns to the welcome state.
    on_new_reference : Callable[[], Awaitable[None]] | None
        Command that opens the new-reference dialog from the References
        section.
    on_log_entry : Callable[[NoteDate], Awaitable[None]] | None
        Command that opens or creates the log entry for a date.
    """

    def __init__(
        self,
        update: Callable[[], None],
        on_change_vault: Callable[[], Awaitable[None]],
        on_create_vault: Callable[[], Awaitable[None]],
        on_close_vault: Callable[[], Awaitable[None]],
        on_new_reference: Callable[[], Awaitable[None]] | None = None,
        pick_date: afanes.ui.views.page.PickDate | None = None,
        on_log_entry: Callable[[NoteDate], Awaitable[None]] | None = None,
        on_missing_role: Callable[[str], Awaitable[None]] | None = None,
        pick_role: afanes.ui.views.page.PickRole | None = None,
    ) -> None:
        """Build the workspace controls against the shared application state.

        Parameters
        ----------
        update : Callable[[], None]
            Requests a repaint of the page.
        on_change_vault : Callable[[], Awaitable[None]]
            Command that opens an existing vault.
        on_create_vault : Callable[[], Awaitable[None]]
            Command that creates a new vault.
        on_close_vault : Callable[[], Awaitable[None]]
            Command that closes the current vault.
        on_new_reference : Callable[[], Awaitable[None]] | None
            Command that opens the new-reference dialog. ``None`` leaves the
            action inert, which tests use for unrelated shell coverage.
        pick_date : afanes.ui.views.page.PickDate | None
            Command that opens the date picker for step and project dates.
        on_log_entry : Callable[[NoteDate], Awaitable[None]] | None
            Command that opens or creates a log entry for a date.
        on_missing_role : Callable[[str], Awaitable[None]] | None
            Command that asks for a category before creating a missing role
            reference.
        pick_role : afanes.ui.views.page.PickRole | None
            Command that asks for an owner or requester name in read mode.
        """
        self._state = afanes.ui.state.app_state
        self._update = update
        self._on_change_vault = on_change_vault
        self._on_create_vault = on_create_vault
        self._on_close_vault = on_close_vault
        self._on_new_reference = on_new_reference
        self._on_log_entry = on_log_entry
        self._pick_date = pick_date
        self._on_missing_role = on_missing_role
        self._pick_role = pick_role
        self.log_calendar: afanes.ui.components.calendar.LogCalendar | None = None
        self.log_tree: afanes.ui.components.log_tree.LogTree | None = None
        self.log_today_button: ft.FilledButton | None = None
        self.log_entries_button: ft.TextButton | None = None
        self.log_everything_button: ft.TextButton | None = None
        self._processing_view: afanes.ui.views.processing.ProcessingView | None = None
        self._processing_key: tuple[Path | None, Path | None] | None = None
        self._projects_view: afanes.ui.views.projects.ProjectsView | None = None
        self._review_view: afanes.ui.views.review.ReviewView | None = None

        self.progress = ft.ProgressRing(
            width=16,
            height=16,
            visible=False,
            semantics_label=afanes.ui.strings.WORKING,
        )
        self.vault_text = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["caption"],
            selectable=True,
        )
        self.refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH_OUTLINED,
            tooltip=afanes.ui.strings.REFRESH_ACTION,
            on_click=self._refresh,
            key="workspace-refresh",
        )
        self.new_reference_button = ft.FilledButton(
            content=afanes.ui.strings.BROWSER_NEW_REFERENCE,
            icon=ft.Icons.ADD_OUTLINED,
            on_click=self._new_reference,
            key="browser-new-reference",
        )
        self.change_button = ft.PopupMenuButton(
            content=ft.Text(afanes.ui.strings.CHANGE_VAULT_ACTION),
            icon=ft.Icons.FOLDER_OPEN_OUTLINED,
            tooltip=afanes.ui.strings.CHANGE_VAULT_ACTION,
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
            ],
            key="workspace-change",
        )
        self.capture_field = ft.TextField(
            label=afanes.ui.strings.COMPOSER_LABEL,
            hint_text=afanes.ui.strings.COMPOSER_HINT,
            multiline=True,
            min_lines=1,
            max_lines=4,
            shift_enter=True,
            expand=True,
            on_submit=self._capture,
            key="workspace-capture-field",
        )
        self.capture_button = ft.FilledButton(
            content=afanes.ui.strings.CAPTURE_ACTION,
            icon=ft.Icons.SEND_OUTLINED,
            on_click=self._capture,
            key="workspace-capture-button",
        )

        self.review_count = ft.Text("", style=afanes.ui.theme.TEXT_ROLES["caption"])
        self.review_icon = ft.Icon(ft.Icons.PLAY_ARROW_OUTLINED, color=afanes.ui.theme.SECTION_ICON_COLOR)
        self.review_tile = ft.ListTile(
            title=afanes.ui.strings.REVIEW_TITLE,
            leading=self.review_icon,
            trailing=self.review_count,
            selected=False,
            dense=True,
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
                dense=True,
                on_click=self._section_handler(section),
                key=f"section-{section.value}",
            )
            self.section_tiles[section] = tile
            self.section_edges[section] = ft.Container(content=tile, border_radius=afanes.ui.theme.SURFACE_RADIUS)

        self.search_field = ft.TextField(
            label=afanes.ui.strings.BROWSER_SEARCH_LABEL,
            hint_text=afanes.ui.strings.BROWSER_SEARCH_HINT,
            dense=True,
            on_change=self._search,
            key="browser-search",
        )
        self.browser_list = ft.ListView(
            controls=[],
            expand=True,
            spacing=0,
            padding=0,
            key="browser-list",
        )
        self.failures_column = ft.Column(controls=[], spacing=0, visible=False)
        self.sidebar = ft.Container(
            width=afanes.ui.theme.SIDEBAR_WIDTH,
            padding=afanes.ui.theme.ITEM_GAP,
            bgcolor=afanes.ui.theme.REGION_SURFACE_COLOR,
            border=ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR),
            border_radius=afanes.ui.theme.SURFACE_RADIUS,
            content=ft.Column(
                controls=[
                    self.review_edge,
                    ft.Divider(height=1),
                    *self.section_edges.values(),
                    self.search_field,
                    ft.Container(content=self.browser_list, expand=True),
                    self.failures_column,
                ],
                spacing=0,
                expand=True,
            ),
        )

        self.banners = ft.Column(controls=[], spacing=afanes.ui.theme.ITEM_GAP)
        self.page_view = afanes.ui.views.page.PageView(
            self._on_page_update,
            self._process_note,
            self._pick_date,
            self._on_missing_role,
            self._pick_role,
        )
        self.main_host = ft.Container(expand=True)
        self.status_bar = ft.Container(
            padding=ft.Padding.only(top=afanes.ui.theme.ITEM_GAP),
            border=ft.Border(top=ft.BorderSide(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR)),
            content=ft.Row(
                controls=[
                    self.vault_text,
                    ft.Container(expand=True),
                    self.progress,
                    self.refresh_button,
                    self.change_button,
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        self.root = ft.Column(
            controls=[
                ft.Row(
                    controls=[self.capture_field, self.capture_button],
                    spacing=afanes.ui.theme.ITEM_GAP,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
                self.banners,
                ft.Row(
                    controls=[self.sidebar, self.main_host],
                    spacing=afanes.ui.theme.SECTION_GAP,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                    expand=True,
                ),
                self.status_bar,
            ],
            spacing=afanes.ui.theme.SECTION_GAP,
            expand=True,
            key="workspace-view",
        )
        self._refresh_dynamic()

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
        self._refresh_dynamic()
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

    async def _select(self, path: Path) -> None:
        """Open one browser entry in the page pane."""
        self._set_working(working=True)
        try:
            await self._state.navigation.open_page(path)
        finally:
            self._set_working(working=False)
        self._refresh_dynamic()
        await self.page_view.scroll_to_top()
        self._update()

    async def _select_section(self, section: afanes.ui.state.browser.WorkspaceSection) -> None:
        """Switch the browser to one section."""
        await self._state.browser.set_section(section)
        self._refresh_dynamic()
        self._update()

    async def _select_review(self) -> None:
        """Open the review destination."""
        await self._state.browser.set_section(afanes.ui.state.browser.WorkspaceSection.REVIEW)
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
        self._refresh_dynamic()
        self._update()

    def _on_page_update(self) -> None:
        """Refresh the workspace after a page command changes state."""
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
        self.capture_button.disabled = working
        self.refresh_button.disabled = working
        self.change_button.disabled = working
        self.new_reference_button.disabled = working
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
        self.vault_text.value = str(state.session.vault_root) if state.session.vault_root is not None else ""
        listing = state.browser.listing()
        for section, tile in self.section_tiles.items():
            browser_section = section.browser_section
            count = 0
            if section is afanes.ui.state.browser.WorkspaceSection.LOG:
                timeline = state.browser.timeline()
                count = len(timeline.entries()) if timeline is not None else 0
            elif listing is not None and browser_section is not None:
                count = sum(len(group.notes) for group in listing.groups_for(browser_section))
            self.section_counts[section].value = str(count)
            active = state.browser.active_section is section
            tile.selected = active
            self.section_icons[section].color = afanes.ui.theme.SECTION_ICON_COLOR
        review_active = state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.REVIEW
        self.review_count.value = afanes.ui.strings.review_pending(state.browser.pending_count())
        self.review_tile.selected = review_active
        self.review_icon.color = afanes.ui.theme.SECTION_ICON_COLOR
        self.search_field.value = state.browser.query
        self.browser_list.controls = self._browser_controls(listing)
        self._refresh_failures()
        self._refresh_banners()
        self._refresh_main()
        self.progress.visible = state.status.busy

    def _browser_controls(
        self,
        listing: afanes.core.search.BrowserListing | None,
    ) -> list[ft.Control]:
        """Build the sidebar entries for the active section."""
        state = self._state
        if state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.REVIEW:
            return [
                ft.Container(
                    padding=afanes.ui.theme.ITEM_GAP,
                    content=ft.Text(
                        afanes.ui.strings.review_pending(state.browser.pending_count()),
                        color=afanes.ui.theme.MUTED_TEXT_COLOR,
                    ),
                )
            ]
        if state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.PROJECTS:
            if self._projects_view is None:
                self._projects_view = afanes.ui.views.projects.ProjectsView(self._update, self._select)
            self._projects_view.refresh()
            return [self._projects_view.root]
        if state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.LOG:
            return self._log_controls()
        section = state.browser.active_section.browser_section
        if listing is None or section is None:
            return []
        groups = listing.groups_for(section)
        controls: list[ft.Control] = []
        if section is afanes.core.search.BrowserSection.REFERENCES:
            controls.append(
                ft.Container(
                    padding=afanes.ui.theme.ITEM_GAP,
                    content=self.new_reference_button,
                )
            )
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
            groups_empty = not any(group.notes for group in groups)
        else:
            notes = groups[0].notes if groups else ()
            controls = [self._note_row(note) for note in notes]
            groups_empty = not notes
        if groups_empty:
            message = (
                afanes.ui.strings.BROWSER_NO_MATCH if state.browser.query.strip() else afanes.ui.strings.BROWSER_EMPTY
            )
            controls.append(
                ft.Container(
                    padding=afanes.ui.theme.ITEM_GAP,
                    content=ft.Text(message, color=afanes.ui.theme.MUTED_TEXT_COLOR, selectable=True),
                )
            )
        return controls

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
        self.log_today_button = ft.FilledButton(
            content=afanes.ui.strings.LOG_TODAY_ENTRY,
            icon=ft.Icons.TODAY_OUTLINED,
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
            dense=True,
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
            dense=True,
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
        """Refresh the warning banners."""
        banners: list[ft.Control] = []
        message = self._state.status.message
        if message is not None:
            banners.append(Banner(message).build())
        self.banners.controls = banners
        self.banners.visible = bool(banners)

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
            self.main_host.content = self._processing_view.build()
            return
        self._processing_view = None
        self._processing_key = None
        if state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.REVIEW:
            if self._review_view is None:
                self._review_view = afanes.ui.views.review.ReviewView(self._on_review_update)
            self._review_view.refresh()
            self.main_host.content = self._review_view.build()
            return
        self.page_view.refresh()
        self.main_host.content = self.page_view.build()
