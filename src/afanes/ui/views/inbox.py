# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Welcome and Inbox views for the capture loop.

Both views are presentational. They read the shared application state and
forward user intent to its commands; they never read vault files, parse
Markdown, or write to disk. A single update callback requests a repaint so the
views can be constructed without a live Flet page in tests.
"""

from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
from afanes.core.vault import VaultNote


def build_welcome(on_choose: Callable[[], Awaitable[None]]) -> ft.Control:
    """Build the first-run welcome state.

    Parameters
    ----------
    on_choose : Callable[[], Awaitable[None]]
        Command that opens the folder picker and selects a vault.

    Returns
    -------
    ft.Control
        Centered welcome layout with a folder action and any startup message.
    """
    controls: list[ft.Control] = [
        ft.Text(
            afanes.ui.strings.WELCOME_TITLE,
            theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM,
            text_align=ft.TextAlign.CENTER,
        ),
        ft.Text(afanes.ui.strings.WELCOME_BODY, text_align=ft.TextAlign.CENTER),
        ft.FilledButton(
            content=afanes.ui.strings.WELCOME_CHOOSE,
            icon=ft.Icons.FOLDER_OPEN,
            on_click=on_choose,
            autofocus=True,
        ),
        ft.Text(
            afanes.ui.strings.WELCOME_NOTE,
            size=12,
            color=afanes.ui.theme.MUTED_TEXT_COLOR,
            text_align=ft.TextAlign.CENTER,
        ),
    ]
    message = afanes.ui.state.app_state.message
    if message is not None:
        controls.append(_banner(message))
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


class InboxView:
    """Composer, newest-first note list, and read-only preview.

    Parameters
    ----------
    update : Callable[[], None]
        Requests a repaint of the page. Tests pass a no-op or a counter.
    on_change_vault : Callable[[], Awaitable[None]]
        Command that opens the folder picker and switches the vault.
    on_process : Callable[[Path], Awaitable[None]]
        Command that opens the Processing Wizard for a selected capture.
    """

    def __init__(
        self,
        update: Callable[[], None],
        on_change_vault: Callable[[], Awaitable[None]],
        on_process: Callable[[Path], Awaitable[None]],
    ) -> None:
        """Build the Inbox controls against the shared application state.

        Parameters
        ----------
        update : Callable[[], None]
            Requests a repaint of the page.
        on_change_vault : Callable[[], Awaitable[None]]
            Command that opens the folder picker and switches the vault.
        on_process : Callable[[Path], Awaitable[None]]
            Command that opens the Processing Wizard for a selected capture.
        """
        self._state = afanes.ui.state.app_state
        self._update = update
        self._on_change_vault = on_change_vault
        self._on_process = on_process

        self.progress = ft.ProgressRing(
            width=16,
            height=16,
            visible=False,
            semantics_label=afanes.ui.strings.WORKING,
        )
        self.composer = ft.TextField(
            label=afanes.ui.strings.COMPOSER_LABEL,
            hint_text=afanes.ui.strings.COMPOSER_HINT,
            multiline=True,
            min_lines=afanes.ui.theme.COMPOSER_MIN_LINES,
            max_lines=afanes.ui.theme.COMPOSER_MAX_LINES,
            shift_enter=True,
            autofocus=True,
            filled=True,
            expand=True,
            on_submit=self._capture,
        )
        self.capture_button = ft.FilledButton(
            content=afanes.ui.strings.CAPTURE_ACTION,
            icon=ft.Icons.SEND,
            on_click=self._capture,
        )
        self.refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip=afanes.ui.strings.REFRESH_ACTION,
            on_click=self._refresh,
        )
        self.change_button = ft.TextButton(
            content=afanes.ui.strings.CHANGE_VAULT_ACTION,
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._change_vault,
        )
        self.count_text = ft.Text(
            "",
            theme_style=ft.TextThemeStyle.BODY_SMALL,
            color=afanes.ui.theme.MUTED_TEXT_COLOR,
        )
        self.vault_text = ft.Text(
            "",
            size=12,
            color=afanes.ui.theme.MUTED_TEXT_COLOR,
            selectable=True,
        )
        self.banners = ft.Column(controls=[], spacing=afanes.ui.theme.ITEM_GAP)
        self.list_view = ft.ListView(
            controls=[],
            expand=True,
            spacing=afanes.ui.theme.ITEM_GAP,
            padding=0,
        )
        self.list_panel = ft.Container(
            content=self.list_view,
            width=afanes.ui.theme.LIST_WIDTH,
            padding=afanes.ui.theme.ITEM_GAP,
            bgcolor=afanes.ui.theme.SURFACE_CONTAINER_COLOR,
            border_radius=afanes.ui.theme.CARD_RADIUS,
        )
        self.preview_title = ft.Text(
            afanes.ui.strings.PREVIEW_TITLE,
            theme_style=ft.TextThemeStyle.TITLE_MEDIUM,
        )
        self.preview_empty = ft.Text(
            afanes.ui.strings.PREVIEW_EMPTY,
            color=afanes.ui.theme.MUTED_TEXT_COLOR,
        )
        self.preview_body = ft.Markdown(
            value="",
            selectable=True,
            auto_follow_links=False,
            on_tap_link=self.handle_link,
        )
        self.preview_body.visible = False
        self.process_button = ft.FilledButton(
            content=afanes.ui.strings.PROCESS_ACTION,
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._process_selected,
            disabled=True,
            key="process-note",
        )
        self.preview_header = ft.Row(
            controls=[
                self.preview_title,
                ft.Container(expand=True),
                self.process_button,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.preview_content = ft.Column(
            controls=[self.preview_empty, self.preview_body],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=afanes.ui.theme.ITEM_GAP,
        )
        self.preview_panel = ft.Container(
            content=ft.Column(
                controls=[self.preview_header, ft.Divider(), self.preview_content],
                expand=True,
            ),
            expand=True,
            padding=afanes.ui.theme.ITEM_GAP,
            bgcolor=afanes.ui.theme.SURFACE_CONTAINER_COLOR,
            border_radius=afanes.ui.theme.CARD_RADIUS,
        )

        header = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(
                                    afanes.ui.strings.INBOX_TITLE,
                                    theme_style=ft.TextThemeStyle.HEADLINE_SMALL,
                                ),
                                self.count_text,
                            ],
                            spacing=afanes.ui.theme.ITEM_GAP,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
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
        composer_row = ft.Row(
            controls=[self.composer, self.capture_button],
            spacing=afanes.ui.theme.ITEM_GAP,
            vertical_alignment=ft.CrossAxisAlignment.END,
        )
        body = ft.Row(
            controls=[self.list_panel, self.preview_panel],
            expand=True,
            spacing=afanes.ui.theme.SECTION_GAP,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.root = ft.Column(
            controls=[header, composer_row, self.banners, body],
            expand=True,
            spacing=afanes.ui.theme.SECTION_GAP,
        )
        self._refresh_dynamic()

    def build(self) -> ft.Control:
        """Return the root control for the Inbox.

        Returns
        -------
        ft.Control
            Composed Inbox layout.
        """
        return self.root

    def handle_link(self) -> None:
        """Swallow a link tap without navigating or launching an external program."""
        return None

    async def _capture(self) -> None:
        """Capture the composer text and update the view."""
        text = self.composer.value or ""
        self._set_working(working=True)
        try:
            path = await self._state.capture(text)
        finally:
            self._set_working(working=False)
        if path is not None:
            self.composer.value = ""
        self._refresh_dynamic()
        self._update()

    async def _refresh(self) -> None:
        """Re-read the vault and update the view."""
        self._set_working(working=True)
        try:
            await self._state.refresh()
        finally:
            self._set_working(working=False)
        self._refresh_dynamic()
        self._update()

    async def _select(self, path: Path) -> None:
        """Load a note into the preview and update the view."""
        self._set_working(working=True)
        try:
            await self._state.select_note(path)
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

    async def _process_selected(self) -> None:
        """Open the Processing Wizard for the selected capture."""
        path = self._state.selected
        if path is None:
            return
        await self._on_process(path)

    def _set_working(self, *, working: bool) -> None:
        """Disable controls and show progress while a command runs."""
        self.progress.visible = working
        self.capture_button.disabled = working
        self.refresh_button.disabled = working
        self.change_button.disabled = working
        self.process_button.disabled = working or self._state.selected is None
        self.composer.read_only = working
        self._update()

    def _refresh_dynamic(self) -> None:
        """Refresh the list, banners, count, and preview from application state."""
        state = self._state
        self.count_text.value = afanes.ui.strings.note_count(len(state.notes))
        self.vault_text.value = str(state.vault_root) if state.vault_root is not None else ""
        if state.notes:
            self.list_view.controls = [self._note_row(note) for note in state.notes]
        else:
            self.list_view.controls = [self._empty_state()]
        banners: list[ft.Control] = []
        if state.message is not None:
            banners.append(_banner(state.message))
        if state.failures:
            paths = ", ".join(failure.path.as_posix() for failure in state.failures)
            banners.append(_banner(afanes.ui.strings.scan_warning(len(state.failures), paths)))
        self.banners.controls = banners
        self.banners.visible = bool(banners)
        self.process_button.disabled = state.selected is None
        if state.selected is None:
            self.preview_title.value = afanes.ui.strings.PREVIEW_TITLE
            self.preview_empty.visible = True
            self.preview_body.visible = False
            self.preview_body.value = ""
        else:
            self.preview_title.value = state.note_title(state.selected)
            self.preview_body.value = state.preview_body or ""
            self.preview_body.visible = True
            self.preview_empty.visible = False

    def _note_row(self, note: VaultNote) -> ft.Control:
        """Build one clickable note row."""
        return ft.ListTile(
            title=note.title,
            subtitle=note.relative_path.as_posix(),
            leading=ft.Icons.DESCRIPTION,
            selected=note.path == self._state.selected,
            on_click=self._select_handler(note.path),
        )

    def _select_handler(self, path: Path) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler to one note path."""

        async def handle() -> None:
            await self._select(path)

        return handle

    def _empty_state(self) -> ft.Control:
        """Build the empty-inbox message."""
        return ft.Container(
            padding=afanes.ui.theme.SECTION_GAP,
            content=ft.Column(
                controls=[
                    ft.Text(
                        afanes.ui.strings.EMPTY_TITLE,
                        theme_style=ft.TextThemeStyle.TITLE_MEDIUM,
                    ),
                    ft.Text(
                        afanes.ui.strings.EMPTY_BODY,
                        color=afanes.ui.theme.MUTED_TEXT_COLOR,
                    ),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
        )


def build_inbox(
    update: Callable[[], None],
    on_change_vault: Callable[[], Awaitable[None]],
    on_process: Callable[[Path], Awaitable[None]],
) -> ft.Control:
    """Build the Inbox view.

    Parameters
    ----------
    update : Callable[[], None]
        Requests a repaint of the page.
    on_change_vault : Callable[[], Awaitable[None]]
        Command that opens the folder picker and switches the vault.
    on_process : Callable[[Path], Awaitable[None]]
        Command that opens the Processing Wizard for a selected capture.

    Returns
    -------
    ft.Control
        Composed Inbox layout.
    """
    return InboxView(update, on_change_vault, on_process).build()


def _banner(message: str) -> ft.Control:
    """Build an accessible warning banner."""
    return ft.Container(
        bgcolor=afanes.ui.theme.ERROR_CONTAINER_COLOR,
        padding=afanes.ui.theme.BANNER_PADDING,
        border_radius=afanes.ui.theme.CARD_RADIUS,
        content=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.ERROR_OUTLINE,
                    color=afanes.ui.theme.ERROR_TEXT_COLOR,
                    size=18,
                ),
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
