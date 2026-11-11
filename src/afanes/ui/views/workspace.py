# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Persistent workspace shell with the vault browser and page pane.

The view is presentational. It reads the shared application state and forwards
user intent to its commands; it never parses Markdown, queries SQL, or writes a
vault file. The browser stays visible while the main area shows the page pane,
the Processing Wizard, or a guided review.
"""

from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

import afanes.core.search
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
import afanes.ui.views.page
import afanes.ui.views.processing
import afanes.ui.views.projects
import afanes.ui.views.review
from afanes.core.vault import VaultFailure, VaultNote

_SECTION_ICONS = {
    afanes.ui.state.WorkspaceSection.INBOX: ft.Icons.INBOX,
    afanes.ui.state.WorkspaceSection.PROJECTS: ft.Icons.FOLDER,
    afanes.ui.state.WorkspaceSection.ACTIONS: ft.Icons.CHECK_CIRCLE_OUTLINE,
    afanes.ui.state.WorkspaceSection.PEOPLE: ft.Icons.PEOPLE,
    afanes.ui.state.WorkspaceSection.REFERENCES: ft.Icons.BOOK,
    afanes.ui.state.WorkspaceSection.NOTES: ft.Icons.DESCRIPTION,
}


class WorkspaceView:
    """Browser sidebar, capture bar, and a main area for focused work.

    Parameters
    ----------
    update : Callable[[], None]
        Requests a repaint of the page. Tests pass a no-op or a counter.
    on_change_vault : Callable[[], Awaitable[None]]
        Command that opens the folder picker and switches the vault.
    """

    def __init__(
        self,
        update: Callable[[], None],
        on_change_vault: Callable[[], Awaitable[None]],
    ) -> None:
        """Build the workspace controls against the shared application state.

        Parameters
        ----------
        update : Callable[[], None]
            Requests a repaint of the page.
        on_change_vault : Callable[[], Awaitable[None]]
            Command that opens the folder picker and switches the vault.
        """
        self._state = afanes.ui.state.app_state
        self._update = update
        self._on_change_vault = on_change_vault
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
            size=12,
            color=afanes.ui.theme.MUTED_TEXT_COLOR,
            selectable=True,
        )
        self.refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip=afanes.ui.strings.REFRESH_ACTION,
            on_click=self._refresh,
            key="workspace-refresh",
        )
        self.change_button = ft.TextButton(
            content=afanes.ui.strings.CHANGE_VAULT_ACTION,
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._change_vault,
        )
        self.capture_field = ft.TextField(
            label=afanes.ui.strings.COMPOSER_LABEL,
            hint_text=afanes.ui.strings.COMPOSER_HINT,
            multiline=True,
            min_lines=1,
            max_lines=4,
            shift_enter=True,
            filled=True,
            expand=True,
            on_submit=self._capture,
            key="workspace-capture-field",
        )
        self.capture_button = ft.FilledButton(
            content=afanes.ui.strings.CAPTURE_ACTION,
            icon=ft.Icons.SEND,
            on_click=self._capture,
            key="workspace-capture-button",
        )

        self.review_count = ft.Text("", size=12, color=afanes.ui.theme.MUTED_TEXT_COLOR)
        self.review_tile = ft.ListTile(
            title=afanes.ui.strings.REVIEW_TITLE,
            leading=ft.Icons.PLAY_ARROW,
            trailing=self.review_count,
            selected=False,
            dense=True,
            on_click=self._select_review,
            key="review-entry",
        )
        self.section_counts: dict[afanes.ui.state.WorkspaceSection, ft.Text] = {}
        self.section_tiles: dict[afanes.ui.state.WorkspaceSection, ft.ListTile] = {}
        for section in afanes.ui.state.WorkspaceSection:
            if section is afanes.ui.state.WorkspaceSection.REVIEW:
                continue
            self.section_counts[section] = ft.Text("", size=12, color=afanes.ui.theme.MUTED_TEXT_COLOR)
            self.section_tiles[section] = ft.ListTile(
                title=afanes.ui.strings.WORKSPACE_SECTION_LABELS[section.value],
                leading=_SECTION_ICONS[section],
                trailing=self.section_counts[section],
                selected=False,
                dense=True,
                on_click=self._section_handler(section),
                key=f"section-{section.value}",
            )

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
            bgcolor=afanes.ui.theme.SURFACE_CONTAINER_COLOR,
            border_radius=afanes.ui.theme.CARD_RADIUS,
            content=ft.Column(
                controls=[
                    self.review_tile,
                    ft.Divider(height=1),
                    *self.section_tiles.values(),
                    self.search_field,
                    ft.Container(content=self.browser_list, expand=True),
                    self.failures_column,
                ],
                spacing=0,
                expand=True,
            ),
        )

        self.banners = ft.Column(controls=[], spacing=afanes.ui.theme.ITEM_GAP)
        self.page_view = afanes.ui.views.page.PageView(self._on_page_update, self._process_note)
        self.main_host = ft.Container(expand=True)
        self.header = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(afanes.ui.strings.APP_TITLE, theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                        self.vault_text,
                    ],
                    spacing=0,
                ),
                ft.Container(expand=True),
                self.progress,
                self.refresh_button,
                self.change_button,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.root = ft.Column(
            controls=[
                self.header,
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

    async def _capture(self) -> None:
        """Capture the current field text and refresh the browser."""
        text = self.capture_field.value or ""
        self._set_working(working=True)
        try:
            path = await self._state.capture(text)
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
            await self._state.refresh()
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

    async def _select(self, path: Path) -> None:
        """Open one browser entry in the page pane."""
        self._set_working(working=True)
        try:
            await self._state.open_page(path)
        finally:
            self._set_working(working=False)
        self._refresh_dynamic()
        self._update()

    async def _select_section(self, section: afanes.ui.state.WorkspaceSection) -> None:
        """Switch the browser to one section."""
        await self._state.set_section(section)
        self._refresh_dynamic()
        self._update()

    async def _select_review(self) -> None:
        """Open the review destination."""
        await self._state.set_section(afanes.ui.state.WorkspaceSection.REVIEW)
        self._refresh_dynamic()
        self._update()

    async def _search(self) -> None:
        """Apply the browser search text."""
        await self._state.set_browser_query(self.search_field.value or "")
        self._refresh_dynamic()
        self._update()

    async def _process_note(self, path: Path) -> None:
        """Open the Processing Wizard for one inbox capture."""
        opened = await self._state.begin_processing(path)
        if opened:
            self._refresh_dynamic()
            self._update()

    async def _cancel_processing(self) -> None:
        """Close the Processing Wizard without writing."""
        self._state.cancel_processing()
        self._refresh_dynamic()
        self._update()

    async def _finish_processing(self) -> None:
        """Close the Processing Wizard success state."""
        self._state.finish_processing()
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
        self.progress.visible = working
        self.capture_button.disabled = working
        self.refresh_button.disabled = working
        self.change_button.disabled = working
        self.capture_field.read_only = working
        self._set_section_tiles_disabled(disabled=working)
        self._update()

    def _set_section_tiles_disabled(self, *, disabled: bool) -> None:
        """Enable or disable the section entries during a command."""
        for tile in self.section_tiles.values():
            tile.disabled = disabled
        self.review_tile.disabled = disabled

    def _refresh_dynamic(self) -> None:
        """Refresh counts, browser entries, banners, and the main area."""
        state = self._state
        self.vault_text.value = str(state.vault_root) if state.vault_root is not None else ""
        listing = state.browser_listing
        for section, tile in self.section_tiles.items():
            browser_section = section.browser_section
            count = 0
            if listing is not None and browser_section is not None:
                count = len(listing.group(browser_section).notes)
            self.section_counts[section].value = str(count)
            tile.selected = state.active_section is section
        self.review_count.value = afanes.ui.strings.review_pending(state.review_pending_count)
        self.review_tile.selected = state.active_section is afanes.ui.state.WorkspaceSection.REVIEW
        self.search_field.value = state.browser_query
        self.browser_list.controls = self._browser_controls(listing)
        self._refresh_failures()
        self._refresh_banners()
        self._refresh_main()
        self.progress.visible = state.busy

    def _browser_controls(
        self,
        listing: afanes.core.search.BrowserListing | None,
    ) -> list[ft.Control]:
        """Build the sidebar entries for the active section."""
        state = self._state
        if state.active_section is afanes.ui.state.WorkspaceSection.REVIEW:
            return [
                ft.Container(
                    padding=afanes.ui.theme.ITEM_GAP,
                    content=ft.Text(
                        afanes.ui.strings.review_pending(state.review_pending_count),
                        color=afanes.ui.theme.MUTED_TEXT_COLOR,
                    ),
                )
            ]
        if state.active_section is afanes.ui.state.WorkspaceSection.PROJECTS:
            if self._projects_view is None:
                self._projects_view = afanes.ui.views.projects.ProjectsView(self._update, self._select)
            self._projects_view.refresh()
            return [self._projects_view.root]
        section = state.active_section.browser_section
        if listing is None or section is None:
            return []
        notes = listing.group(section).notes
        if not notes:
            message = (
                afanes.ui.strings.BROWSER_NO_MATCH if state.browser_query.strip() else afanes.ui.strings.BROWSER_EMPTY
            )
            return [
                ft.Container(
                    padding=afanes.ui.theme.ITEM_GAP,
                    content=ft.Text(message, color=afanes.ui.theme.MUTED_TEXT_COLOR, selectable=True),
                )
            ]
        return [self._note_row(note) for note in notes]

    def _note_row(self, note: VaultNote) -> ft.Control:
        """Build one clickable browser entry."""
        page = self._state.page
        selected = page is not None and page.path == note.path
        return ft.ListTile(
            title=note.title,
            subtitle=note.relative_path.as_posix(),
            leading=ft.Icons.DESCRIPTION,
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
        section: afanes.ui.state.WorkspaceSection,
    ) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler to one section."""

        async def handle() -> None:
            await self._select_section(section)

        return handle

    def _refresh_failures(self) -> None:
        """Refresh the unreadable-notes section."""
        failures = self._state.failures
        if not failures:
            self.failures_column.controls = []
            self.failures_column.visible = False
            return
        controls: list[ft.Control] = [
            ft.Divider(height=1),
            ft.Text(
                afanes.ui.strings.BROWSER_FAILURES,
                size=12,
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
            await self._state.open_failure(path)
            self._refresh_dynamic()
            self._update()

        return handle

    def _refresh_banners(self) -> None:
        """Refresh the warning banners."""
        banners: list[ft.Control] = []
        message = self._state.message
        if message is not None:
            banners.append(_banner(message))
        self.banners.controls = banners
        self.banners.visible = bool(banners)

    def _refresh_main(self) -> None:
        """Show the page pane, the Processing Wizard, or the review area."""
        state = self._state
        if state.processing_note is not None or state.processing_result is not None:
            key = (state.processing_note, state.processing_result)
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
        if state.active_section is afanes.ui.state.WorkspaceSection.REVIEW:
            if self._review_view is None:
                self._review_view = afanes.ui.views.review.ReviewView(self._on_review_update)
            self._review_view.refresh()
            self.main_host.content = self._review_view.build()
            return
        self.page_view.refresh()
        self.main_host.content = self.page_view.build()


def build_workspace(
    update: Callable[[], None],
    on_change_vault: Callable[[], Awaitable[None]],
) -> ft.Control:
    """Build the workspace shell.

    Parameters
    ----------
    update : Callable[[], None]
        Requests a repaint of the page.
    on_change_vault : Callable[[], Awaitable[None]]
        Command that opens the folder picker and switches the vault.

    Returns
    -------
    ft.Control
        Composed workspace layout.
    """
    return WorkspaceView(update, on_change_vault).build()


def _banner(message: str) -> ft.Control:
    """Build an accessible warning banner."""
    return ft.Container(
        bgcolor=afanes.ui.theme.ERROR_CONTAINER_COLOR,
        padding=afanes.ui.theme.BANNER_PADDING,
        border_radius=afanes.ui.theme.CARD_RADIUS,
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=afanes.ui.theme.ERROR_TEXT_COLOR, size=18),
                ft.Text(
                    message,
                    color=afanes.ui.theme.ERROR_TEXT_COLOR,
                    selectable=True,
                    expand=True,
                ),
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    )
