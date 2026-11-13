# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Projects workspace grouped by status.

The view reads project summaries from the shared application state and forwards
selection to a callback. It never parses Markdown or performs file I/O.
"""

from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

import afanes.core.search
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
from afanes.core.search import ProjectGroup, ProjectStage, ProjectSummary
from afanes.ui.components.frozen import FrozenControlRecovery
from afanes.ui.components.status import StatusLabel
from afanes.ui.components.step_text import StepText


class ProjectsView:
    """Status groups and project rows for the sidebar.

    Parameters
    ----------
    update : Callable[[], None]
        Requests a repaint of the page.
    on_select : Callable[[Path], Awaitable[None]]
        Command that opens a project note in the page pane.
    """

    def __init__(
        self,
        update: Callable[[], None],
        on_select: Callable[[Path], Awaitable[None]],
    ) -> None:
        """Build the project groups against the shared application state.

        Parameters
        ----------
        update : Callable[[], None]
            Requests a repaint of the page.
        on_select : Callable[[Path], Awaitable[None]]
            Command that opens a project note in the page pane.
        """
        self._state = afanes.ui.state.app_state
        self._update = update
        self._on_select = on_select
        self._rows: dict[Path, ft.Container] = {}
        self._focused: Path | None = None
        self._signature: tuple[object, ...] | None = None
        self.root = ft.Column(
            controls=[],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            key="projects-view",
        )
        self.refresh()

    def build(self) -> ft.Control:
        """Return the root control for the Projects view.

        Returns
        -------
        ft.Control
            Composed status-grouped layout.
        """
        return self.root

    def refresh(self) -> None:
        """Rebuild project groups or update the selection in place.

        Notes
        -----
        Search matching uses the shared browser query. A selection change keeps
        the existing row controls so keyboard focus stays on the row that was
        clicked; a content change rebuilds the groups and clears the focus ring
        because the replaced rows no longer own focus. This method performs no
        file I/O and never changes a project.
        """
        query = self._state.browser.query
        grouped: list[tuple[ProjectGroup, tuple[ProjectSummary, ...]]] = [
            (
                group,
                tuple(summary for summary in group.projects if afanes.core.search.Browser.matches(summary.note, query)),
            )
            for group in self._state.browser.project_groups()
        ]
        signature = self._signature_for(grouped, query)
        if signature == self._signature and self._rows:
            self._apply_selection()
            return
        self._rows = {}
        self._focused = None
        controls: list[ft.Control] = [self._expansion(group, projects) for group, projects in grouped]
        total = sum(len(projects) for _, projects in grouped)
        if total == 0 and query.strip():
            controls.insert(
                0,
                ft.Container(
                    padding=afanes.ui.theme.ITEM_GAP,
                    content=ft.Text(
                        afanes.ui.strings.BROWSER_NO_MATCH,
                        color=afanes.ui.theme.MUTED_TEXT_COLOR,
                        selectable=True,
                    ),
                ),
            )
        self.root.controls = controls
        self._signature = signature

    def _expansion(self, group: ProjectGroup, projects: tuple[ProjectSummary, ...]) -> ft.ExpansionTile:
        """Build one collapsible status group."""
        label = afanes.ui.strings.PROJECT_GROUP_LABELS[group.stage.value]
        rows = [self._project_row(summary) for summary in projects]
        controls: list[ft.Control] = []
        if rows:
            controls.append(
                ft.Column(
                    controls=rows,
                    spacing=afanes.ui.theme.ROW_GAP,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                )
            )
        return ft.ExpansionTile(
            title=ft.Text(f"{label} ({len(projects)})", style=afanes.ui.theme.TEXT_ROLES["heading"]),
            controls=controls,
            expanded=group.stage is not ProjectStage.CLOSED,
            expanded_cross_axis_alignment=ft.CrossAxisAlignment.STRETCH,
            maintain_state=True,
            key=f"project-group-{group.stage.value}",
        )

    def _project_row(self, summary: ProjectSummary) -> ft.Control:
        """Build one focusable project row with its next step and metadata."""
        note = summary.note
        if summary.next_step is None:
            next_step: ft.Control = ft.Text(
                afanes.ui.strings.PROJECT_NO_NEXT_STEP,
                style=afanes.ui.theme.TEXT_ROLES["caption"],
            )
        else:
            next_step = StepText(
                afanes.ui.strings.PROJECT_NEXT_STEP.format(title=summary.next_step.text),
                afanes.ui.theme.TEXT_ROLES["body"],
                on_tap_link=self._link_handler(note.path),
                underline_links=False,
            ).build()
        meta: list[str] = [StatusLabel(note.status).text]
        if note.due_date is not None:
            meta.append(afanes.ui.strings.PROJECT_DUE.format(date=note.due_date.isoformat()))
        meta.append(afanes.ui.strings.CopyFormatter.open_step_count(summary.open_count))
        page = self._state.pages.page
        selected = page is not None and page.path == note.path
        row = ft.Container(
            bgcolor=afanes.ui.theme.SELECTED_ROW_COLOR if selected else afanes.ui.theme.TRANSPARENT_COLOR,
            border=ft.Border.all(afanes.ui.theme.FOCUS_RING_WIDTH, afanes.ui.theme.TRANSPARENT_COLOR),
            border_radius=afanes.ui.theme.CONTROL_RADIUS,
            key=f"project-row-{note.relative_path.as_posix()}",
        )
        button = ft.TextButton(
            content=ft.Column(
                controls=[
                    ft.Text(note.title, style=afanes.ui.theme.TEXT_ROLES["heading"]),
                    next_step,
                    ft.Text(
                        afanes.ui.strings.PROJECT_META_SEPARATOR.join(meta),
                        style=afanes.ui.theme.TEXT_ROLES["caption"],
                    ),
                ],
                spacing=0,
                expand=True,
            ),
            style=ft.ButtonStyle(
                padding=ft.Padding.symmetric(
                    horizontal=afanes.ui.theme.ITEM_GAP,
                    vertical=afanes.ui.theme.ITEM_GAP,
                ),
                alignment=ft.Alignment.CENTER_LEFT,
                shape=ft.RoundedRectangleBorder(radius=afanes.ui.theme.CONTROL_RADIUS),
                overlay_color={
                    ft.ControlState.FOCUSED: afanes.ui.theme.TRANSPARENT_COLOR,
                    ft.ControlState.HOVERED: afanes.ui.theme.HOVER_COLOR,
                    ft.ControlState.PRESSED: afanes.ui.theme.SPLASH_COLOR,
                },
            ),
            on_focus=self._focus_handler(note.path),
            on_blur=self._blur_handler(note.path),
            on_click=self._select_handler(note.path),
            key=f"project-{note.relative_path.as_posix()}",
        )
        row.content = button
        self._rows[note.path] = row
        return row

    def _apply_selection(self) -> None:
        """Mark the open project row without replacing any row control.

        Notes
        -----
        The accent ring belongs to the open row only. Any selection change that
        leaves the previously focused row behind clears the ring, so a link or
        keyboard navigation cannot leave a second row looking selected. Flet can
        mark a row immutable while reconciling a keyed update, so the markers
        are cleared before any row property is assigned.
        """
        FrozenControlRecovery.clear(self.root)
        page = self._state.pages.page
        if page is None or page.path != self._focused:
            self._focused = None
        for path, row in self._rows.items():
            row.bgcolor = (
                afanes.ui.theme.SELECTED_ROW_COLOR
                if page is not None and page.path == path
                else afanes.ui.theme.TRANSPARENT_COLOR
            )
            row.border = ft.Border.all(
                afanes.ui.theme.FOCUS_RING_WIDTH,
                afanes.ui.theme.FOCUS_RING_COLOR if path == self._focused else afanes.ui.theme.TRANSPARENT_COLOR,
            )

    def _signature_for(
        self,
        grouped: list[tuple[ProjectGroup, tuple[ProjectSummary, ...]]],
        query: str,
    ) -> tuple[object, ...]:
        """Return the content signature that decides whether rows rebuild."""
        return (
            query,
            tuple(
                (
                    group.stage,
                    tuple(
                        (
                            summary.note.path,
                            summary.note.title,
                            summary.note.status,
                            summary.note.due_date,
                            summary.open_count,
                            summary.next_step.text if summary.next_step is not None else None,
                        )
                        for summary in projects
                    ),
                )
                for group, projects in grouped
            ),
        )

    def _focus_handler(self, path: Path) -> Callable[[object], Awaitable[None]]:
        """Bind the accent focus ring to one project row."""

        async def handle(_event: object = None) -> None:
            self._focused = path
            self._apply_focus()
            self._update()

        return handle

    def _blur_handler(self, path: Path) -> Callable[[object], Awaitable[None]]:
        """Clear the focus ring only while that row still owns focus."""

        async def handle(_event: object = None) -> None:
            if self._focused != path:
                return
            self._focused = None
            self._apply_focus()
            self._update()

        return handle

    def _apply_focus(self) -> None:
        """Paint the accent ring on the focused row and clear every other row."""
        FrozenControlRecovery.clear(self.root)
        for path, row in self._rows.items():
            color = afanes.ui.theme.FOCUS_RING_COLOR if path == self._focused else afanes.ui.theme.TRANSPARENT_COLOR
            row.border = ft.Border.all(afanes.ui.theme.FOCUS_RING_WIDTH, color)

    async def _focus_row(self, path: Path) -> None:
        """Move the accent ring to one row and request toolkit focus."""
        self._focused = path
        self._apply_focus()
        self._update()
        row = self._rows.get(path)
        if row is None or not isinstance(row.content, ft.TextButton):
            return
        try:
            await row.content.focus()
        except RuntimeError:
            return

    def _select_handler(self, path: Path) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler to one project path."""

        async def handle() -> None:
            await self._focus_row(path)
            await self._on_select(path)

        return handle

    def _link_handler(self, path: Path) -> Callable[[ft.Event[ft.Markdown]], Awaitable[None]]:
        """Treat a link tap in a row preview as a tap on the whole row.

        Notes
        -----
        Flet attaches a tap recognizer to every Markdown link, even when no
        link handler is set. Forwarding it to selection keeps a preview link
        from becoming a dead zone that focuses the row without opening it.
        """

        async def handle(_event: ft.Event[ft.Markdown]) -> None:
            await self._focus_row(path)
            await self._on_select(path)

        return handle
