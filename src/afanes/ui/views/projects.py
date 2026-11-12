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
        self.root = ft.Column(controls=[], spacing=0, key="projects-view")
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
        """Rebuild every project group from the latest scan.

        Notes
        -----
        Search matching uses the shared browser query. This method performs no
        file I/O and never changes a project.
        """
        query = self._state.browser.query
        groups = self._state.browser.project_groups()
        controls: list[ft.Control] = []
        total = 0
        for group in groups:
            projects = tuple(
                summary for summary in group.projects if afanes.core.search.Browser.matches(summary.note, query)
            )
            total += len(projects)
            controls.append(self._expansion(group, projects))
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

    def _expansion(self, group: ProjectGroup, projects: tuple[ProjectSummary, ...]) -> ft.ExpansionTile:
        """Build one collapsible status group."""
        label = afanes.ui.strings.PROJECT_GROUP_LABELS[group.stage.value]
        return ft.ExpansionTile(
            title=ft.Text(f"{label} ({len(projects)})", theme_style=ft.TextThemeStyle.TITLE_SMALL),
            controls=[self._project_tile(summary) for summary in projects],
            expanded=group.stage is not ProjectStage.CLOSED,
            dense=True,
            maintain_state=True,
            key=f"project-group-{group.stage.value}",
        )

    def _project_tile(self, summary: ProjectSummary) -> ft.Control:
        """Build one clickable project row with its next step."""
        note = summary.note
        details: list[ft.Control] = [
            ft.Text(
                afanes.ui.strings.PROJECT_STATUS.format(status=StatusLabel(note.status).text),
                size=12,
                color=afanes.ui.theme.MUTED_TEXT_COLOR,
            )
        ]
        if note.due_date is not None:
            details.append(
                ft.Text(
                    afanes.ui.strings.PROJECT_DUE.format(date=note.due_date.isoformat()),
                    size=12,
                    color=afanes.ui.theme.MUTED_TEXT_COLOR,
                )
            )
        details.append(
            ft.Text(
                afanes.ui.strings.open_step_count(summary.open_count),
                size=12,
                color=afanes.ui.theme.MUTED_TEXT_COLOR,
            )
        )
        if summary.next_step is None:
            details.append(ft.Text(afanes.ui.strings.PROJECT_NO_NEXT_STEP, size=12, selectable=True))
        else:
            details.append(
                StepText(
                    afanes.ui.strings.PROJECT_NEXT_STEP.format(title=summary.next_step.text),
                    ft.TextStyle(size=12, color=afanes.ui.theme.MUTED_TEXT_COLOR),
                    selectable=True,
                ).build()
            )
        page = self._state.pages.page
        return ft.ListTile(
            title=note.title,
            subtitle=ft.Column(controls=details, spacing=0),
            selected=page is not None and page.path == note.path,
            dense=True,
            on_click=self._select_handler(note.path),
            key=f"project-{note.relative_path.as_posix()}",
        )

    def _select_handler(self, path: Path) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler to one project path."""

        async def handle() -> None:
            await self._on_select(path)

        return handle
