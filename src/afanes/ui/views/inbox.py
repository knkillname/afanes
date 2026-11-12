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
import afanes.ui.views.page
from afanes.core.vault import VaultFailure, VaultNote
from afanes.ui.components.banner import Banner


class WelcomeView:
    """First-run welcome state.

    Parameters
    ----------
    on_choose : Callable[[], Awaitable[None]] | None
        Command that opens the native folder picker and selects a vault.
        Supplied by the desktop presentation.
    on_open_path : Callable[[str], Awaitable[None]] | None
        Command that opens the vault named by a typed path. Supplied by the
        browser presentation, which has no native directory dialog.
    on_create : Callable[[], Awaitable[None]] | None
        Command that opens the new-vault dialog. Supplied by both
        presentations, because no native dialog can name a folder that does not
        exist yet.

    Raises
    ------
    ValueError
        If neither selection command is supplied. Each presentation must offer
        exactly one way to choose an existing vault.
    """

    def __init__(
        self,
        on_choose: Callable[[], Awaitable[None]] | None = None,
        on_open_path: Callable[[str], Awaitable[None]] | None = None,
        on_create: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Store the vault selection actions for this presentation."""
        if on_choose is None and on_open_path is None:
            message = "The welcome state needs one vault selection command."
            raise ValueError(message)
        self._on_choose = on_choose
        self._on_open_path = on_open_path
        self._on_create = on_create

    def build(self) -> ft.Control:
        """Build the welcome layout.

        Returns
        -------
        ft.Control
            Centered welcome layout with the selection action for this
            presentation and any startup message.
        """
        controls: list[ft.Control] = [
            ft.Text(
                afanes.ui.strings.WELCOME_TITLE,
                theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(afanes.ui.strings.WELCOME_BODY, text_align=ft.TextAlign.CENTER),
        ]
        if self._on_choose is not None:
            controls.append(
                ft.FilledButton(
                    content=afanes.ui.strings.WELCOME_CHOOSE,
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=self._on_choose,
                    autofocus=True,
                    key="welcome-choose",
                ),
            )
        if self._on_open_path is not None:
            controls.extend(self._vault_path_entry(self._on_open_path))
        if self._on_create is not None:
            controls.append(
                ft.FilledButton(
                    content=afanes.ui.strings.NEW_VAULT_ACTION,
                    icon=ft.Icons.CREATE_NEW_FOLDER,
                    on_click=self._on_create,
                    key="welcome-create",
                ),
            )
        controls.append(
            ft.Text(
                afanes.ui.strings.WELCOME_NOTE,
                size=12,
                color=afanes.ui.theme.MUTED_TEXT_COLOR,
                text_align=ft.TextAlign.CENTER,
            ),
        )
        message = afanes.ui.state.app_state.message
        if message is not None:
            controls.append(Banner(message).build())
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

    @staticmethod
    def _vault_path_entry(on_open_path: Callable[[str], Awaitable[None]]) -> list[ft.Control]:
        """Build the typed-path selection controls for a browser session."""
        field = ft.TextField(
            label=afanes.ui.strings.WELCOME_PATH_LABEL,
            hint_text=afanes.ui.strings.WELCOME_PATH_HINT,
            width=420,
            autofocus=True,
            key="welcome-path",
        )

        async def open_typed_path() -> None:
            await on_open_path(field.value or "")

        field.on_submit = open_typed_path
        button = ft.FilledButton(
            content=afanes.ui.strings.WELCOME_OPEN,
            icon=ft.Icons.FOLDER_OPEN,
            on_click=open_typed_path,
            key="welcome-open",
        )
        return [field, button]


class SessionNotice:
    """Notice shown when another session already owns the workspace.

    Parameters
    ----------
    on_retry : Callable[[], Awaitable[None]]
        Command that tries to claim the session again.
    """

    def __init__(self, on_retry: Callable[[], Awaitable[None]]) -> None:
        """Store the retry action."""
        self._on_retry = on_retry

    def build(self) -> ft.Control:
        """Build the session notice.

        Returns
        -------
        ft.Control
            Centered notice with a single retry action.
        """
        return ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                controls=[
                    ft.Text(
                        afanes.ui.strings.SESSION_ACTIVE_TITLE,
                        theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(afanes.ui.strings.SESSION_ACTIVE_BODY, text_align=ft.TextAlign.CENTER),
                    ft.FilledButton(
                        content=afanes.ui.strings.SESSION_RETRY,
                        on_click=self._on_retry,
                        autofocus=True,
                        key="session-retry",
                    ),
                ],
                spacing=afanes.ui.theme.SECTION_GAP,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                width=520,
            ),
        )


class InboxView:
    """Composer, newest-first note list, and page pane.

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
        self.page_view = afanes.ui.views.page.PageView(update, on_process)

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
            controls=[self.list_panel, self.page_view.build()],
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
        """Open a note in the page pane and update the view."""
        self._set_working(working=True)
        try:
            await self._state.open_page(path)
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

    def _set_working(self, *, working: bool) -> None:
        """Disable controls and show progress while a command runs."""
        self.progress.visible = working
        self.capture_button.disabled = working
        self.refresh_button.disabled = working
        self.change_button.disabled = working
        self.composer.read_only = working
        self.page_view.refresh()
        self._update()

    def _refresh_dynamic(self) -> None:
        """Refresh the list, banners, count, and page pane from application state."""
        state = self._state
        self.count_text.value = afanes.ui.strings.note_count(len(state.notes))
        self.vault_text.value = str(state.vault_root) if state.vault_root is not None else ""
        if state.notes:
            self.list_view.controls = [self._note_row(note) for note in state.notes]
        else:
            self.list_view.controls = [self._empty_state()]
        banners: list[ft.Control] = []
        if state.message is not None:
            banners.append(Banner(state.message).build())
        if state.failures:
            banners.append(self._failure_banner(state.failures))
        self.banners.controls = banners
        self.banners.visible = bool(banners)
        self.page_view.refresh()

    def _failure_banner(self, failures: tuple[VaultFailure, ...]) -> ft.Control:
        """Build a warning banner whose paths open raw rescue mode."""
        controls: list[ft.Control] = [
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=afanes.ui.theme.ERROR_TEXT_COLOR, size=18),
                    ft.Text(
                        afanes.ui.strings.scan_warning_title(len(failures)),
                        color=afanes.ui.theme.ERROR_TEXT_COLOR,
                        selectable=True,
                        expand=True,
                    ),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        ]
        controls.extend(
            ft.TextButton(
                content=failure.path.as_posix(),
                on_click=self._open_failure_handler(failure.path),
            )
            for failure in failures
        )
        return ft.Container(
            bgcolor=afanes.ui.theme.ERROR_CONTAINER_COLOR,
            padding=afanes.ui.theme.BANNER_PADDING,
            border_radius=afanes.ui.theme.CARD_RADIUS,
            content=ft.Column(controls=controls, spacing=0),
        )

    def _open_failure_handler(self, path: Path) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler that opens one unreadable note."""

        async def handle() -> None:
            await self._state.open_failure(path)
            self._refresh_dynamic()
            self._update()

        return handle

    def _note_row(self, note: VaultNote) -> ft.Control:
        """Build one clickable note row."""
        page = self._state.page
        selected = page is not None and page.path == note.path
        return ft.ListTile(
            title=note.title,
            subtitle=note.relative_path.as_posix(),
            leading=ft.Icons.DESCRIPTION,
            selected=selected,
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
