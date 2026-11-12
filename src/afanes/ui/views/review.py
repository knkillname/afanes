# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Guided review cards for pending captures and project next steps.

The view reads a snapshotted review session from the shared application state
and forwards every write to its commands. It never parses Markdown or performs
file I/O.
"""

from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

import afanes.core.search
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
from afanes.core.search import ProjectSummary, ReviewItem
from afanes.ui.components.banner import Banner
from afanes.ui.components.panel import Card
from afanes.ui.components.status import StatusLabel


class ReviewView:
    """Review queue, project cards, and the completion summary.

    Parameters
    ----------
    update : Callable[[], None]
        Requests a repaint of the page and its surrounding workspace.
    """

    def __init__(self, update: Callable[[], None]) -> None:
        """Build review controls against the shared application state.

        Parameters
        ----------
        update : Callable[[], None]
            Requests a repaint of the page and its surrounding workspace.
        """
        self._state = afanes.ui.state.app_state
        self._update = update
        self._creating = False
        self._action_title = ""
        self._form_error: str | None = None
        self._confirmation: str | None = None
        self.root = ft.Column(controls=[], spacing=afanes.ui.theme.ITEM_GAP, expand=True, key="review-view")
        self.refresh()

    def build(self) -> ft.Control:
        """Return the root control for the review area.

        Returns
        -------
        ft.Control
            Composed review layout.
        """
        return self.root

    def refresh(self) -> None:
        """Rebuild the review controls from the current session."""
        session = self._state.review_session
        controls: list[ft.Control] = []
        if self._state.message is not None:
            controls.append(Banner(self._state.message).build())
        if session is None:
            controls.append(self._start_card())
        elif session.complete:
            controls.append(self._completion_card(session.reviewed_count, session.skipped_count))
        else:
            item = session.current
            if item is None:
                controls.append(self._completion_card(session.reviewed_count, session.skipped_count))
            elif item.kind is afanes.core.search.ReviewItemKind.PROJECT:
                controls.append(self._project_card(item))
            else:
                controls.append(self._capture_card(item))
        self.root.controls = controls

    def _start_card(self) -> ft.Control:
        """Build the review entry card or its zero state."""
        count = self._state.review_pending_count
        if count == 0:
            body = ft.Column(
                controls=[
                    ft.Text(afanes.ui.strings.REVIEW_ZERO_TITLE, theme_style=ft.TextThemeStyle.TITLE_LARGE),
                    ft.Text(
                        afanes.ui.strings.REVIEW_ZERO_BODY,
                        color=afanes.ui.theme.MUTED_TEXT_COLOR,
                        selectable=True,
                    ),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
            )
            return Card(body).build()
        body = ft.Column(
            controls=[
                ft.Text(afanes.ui.strings.REVIEW_TITLE, theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                ft.Text(afanes.ui.strings.review_pending(count), selectable=True),
                ft.FilledButton(
                    content=afanes.ui.strings.REVIEW_START_ACTION,
                    icon=ft.Icons.PLAY_ARROW,
                    on_click=self._start,
                    key="review-start",
                ),
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
        )
        return Card(body).build()

    def _completion_card(self, reviewed: int, skipped: int) -> ft.Control:
        """Build the end-of-session summary."""
        body = ft.Column(
            controls=[
                ft.Text(afanes.ui.strings.REVIEW_COMPLETE_TITLE, theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                ft.Text(
                    afanes.ui.strings.REVIEW_COMPLETE_BODY.format(reviewed=reviewed, skipped=skipped),
                    selectable=True,
                ),
                ft.FilledButton(
                    content=afanes.ui.strings.REVIEW_BACK_TO_BROWSER,
                    icon=ft.Icons.ARROW_BACK,
                    on_click=self._finish,
                    key="review-finish",
                ),
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
        )
        return Card(body).build()

    def _capture_card(self, item: ReviewItem) -> ft.Control:
        """Build the fallback card for an inbox capture awaiting processing."""
        title = self._state.note_title(item.path)
        body = ft.Column(
            controls=[
                ft.Text(afanes.ui.strings.REVIEW_CAPTURE_TITLE, theme_style=ft.TextThemeStyle.LABEL_LARGE),
                ft.Text(title, theme_style=ft.TextThemeStyle.HEADLINE_SMALL, selectable=True),
                ft.Row(
                    controls=[
                        ft.FilledButton(
                            content=afanes.ui.strings.REVIEW_PROCESS_ACTION,
                            icon=ft.Icons.PLAY_ARROW,
                            on_click=self._process_handler(item.path),
                            key="review-process-capture",
                        ),
                        ft.TextButton(
                            content=afanes.ui.strings.REVIEW_SKIP,
                            on_click=self._skip,
                            key="review-skip",
                        ),
                    ],
                    spacing=afanes.ui.theme.ITEM_GAP,
                    wrap=True,
                ),
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
        )
        return Card(body).build()

    def _project_card(self, item: ReviewItem) -> ft.Control:
        """Build the project review card with its next step."""
        summary = item.project
        if summary is None:
            return Card(
                ft.Column(
                    controls=[
                        ft.Text(afanes.ui.strings.REVIEW_PROJECT_FAILED.format(detail=item.path.as_posix())),
                        ft.TextButton(content=afanes.ui.strings.REVIEW_SKIP, on_click=self._skip),
                    ],
                    spacing=afanes.ui.theme.ITEM_GAP,
                )
            ).build()
        controls: list[ft.Control] = [
            ft.Text(afanes.ui.strings.REVIEW_TITLE, theme_style=ft.TextThemeStyle.LABEL_LARGE),
            ft.Text(summary.note.title, theme_style=ft.TextThemeStyle.HEADLINE_SMALL, selectable=True),
            ft.Text(
                afanes.ui.strings.PROJECT_STATUS.format(status=StatusLabel(summary.note.status).text),
                color=afanes.ui.theme.MUTED_TEXT_COLOR,
            ),
        ]
        if summary.note.due_date is not None:
            controls.append(
                ft.Text(
                    afanes.ui.strings.PROJECT_DUE.format(date=summary.note.due_date.isoformat()),
                    color=afanes.ui.theme.MUTED_TEXT_COLOR,
                )
            )
        controls.extend(self._next_step_controls(summary))
        controls.append(self._confirmation_controls())
        controls.append(self._creation_controls())
        controls.append(
            ft.Row(
                controls=[
                    ft.TextButton(
                        content=afanes.ui.strings.REVIEW_OPEN_PROJECT,
                        icon=ft.Icons.OPEN_IN_NEW,
                        on_click=self._open_handler(summary.note.path, afanes.ui.state.WorkspaceSection.PROJECTS),
                        key="review-open-project",
                    ),
                    ft.FilledButton(
                        content=afanes.ui.strings.REVIEW_NEXT,
                        icon=ft.Icons.ARROW_FORWARD,
                        on_click=self._next,
                        key="review-next",
                    ),
                    ft.TextButton(
                        content=afanes.ui.strings.REVIEW_SKIP,
                        on_click=self._skip,
                        key="review-skip",
                    ),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
                wrap=True,
            )
        )
        if summary.next_action is None:
            controls.append(
                ft.Row(
                    controls=[
                        ft.OutlinedButton(
                            content=afanes.ui.strings.REVIEW_CREATE_ACTION,
                            icon=ft.Icons.ADD,
                            on_click=self._toggle_create,
                            key="review-create",
                        ),
                        ft.OutlinedButton(
                            content=afanes.ui.strings.REVIEW_MARK_DONE,
                            icon=ft.Icons.CHECK,
                            on_click=self._confirm_done,
                            key="review-mark-done",
                        ),
                        ft.OutlinedButton(
                            content=afanes.ui.strings.REVIEW_DEFER,
                            icon=ft.Icons.SCHEDULE,
                            on_click=self._confirm_defer,
                            key="review-defer",
                        ),
                    ],
                    spacing=afanes.ui.theme.ITEM_GAP,
                    wrap=True,
                )
            )
        return Card(ft.Column(controls=controls, spacing=afanes.ui.theme.ITEM_GAP)).build()

    def _next_step_controls(self, summary: ProjectSummary) -> list[ft.Control]:
        """Build the next-step and remaining-action controls."""
        controls: list[ft.Control] = []
        if summary.next_action is None:
            controls.append(
                ft.Text(
                    afanes.ui.strings.REVIEW_NO_NEXT_STEP,
                    color=afanes.ui.theme.MUTED_TEXT_COLOR,
                    selectable=True,
                )
            )
            return controls
        controls.append(
            ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(afanes.ui.strings.REVIEW_NEXT_STEP, theme_style=ft.TextThemeStyle.LABEL_LARGE),
                            ft.Text(summary.next_action.title, selectable=True),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    ft.TextButton(
                        content=afanes.ui.strings.REVIEW_OPEN_ACTION,
                        on_click=self._open_handler(summary.next_action.path, afanes.ui.state.WorkspaceSection.ACTIONS),
                        key="review-open-action",
                    ),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        remaining = summary.open_actions[1:]
        if remaining:
            controls.append(ft.Text(afanes.ui.strings.REVIEW_OTHER_ACTIONS, theme_style=ft.TextThemeStyle.LABEL_LARGE))
            controls.extend(
                ft.TextButton(
                    content=note.title,
                    on_click=self._open_handler(note.path, afanes.ui.state.WorkspaceSection.ACTIONS),
                )
                for note in remaining
            )
        return controls

    def _creation_controls(self) -> ft.Control:
        """Build the next-action form when it is open."""
        if not self._creating:
            return ft.Container(visible=False)
        error = ft.Text(
            self._form_error or "",
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            visible=self._form_error is not None,
            selectable=True,
        )
        field = ft.TextField(
            label=afanes.ui.strings.REVIEW_ACTION_TITLE_LABEL,
            hint_text=afanes.ui.strings.REVIEW_ACTION_TITLE_HINT,
            value=self._action_title,
            on_change=self._change_title,
            key="review-action-title",
        )
        return ft.Column(
            controls=[
                field,
                error,
                ft.Row(
                    controls=[
                        ft.FilledButton(
                            content=afanes.ui.strings.REVIEW_ACTION_CONFIRM,
                            icon=ft.Icons.ADD,
                            on_click=self._create_action,
                            key="review-action-submit",
                        ),
                        ft.TextButton(
                            content=afanes.ui.strings.REVIEW_ACTION_CANCEL,
                            on_click=self._cancel_create,
                            key="review-action-cancel",
                        ),
                    ],
                    spacing=afanes.ui.theme.ITEM_GAP,
                    wrap=True,
                ),
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
        )

    def _confirmation_controls(self) -> ft.Control:
        """Build the inline confirmation for closing or deferring."""
        if self._confirmation is None:
            return ft.Container(visible=False)
        message = afanes.ui.strings.REVIEW_MARK_DONE if self._confirmation == "done" else afanes.ui.strings.REVIEW_DEFER
        return ft.Container(
            bgcolor=afanes.ui.theme.SURFACE_CONTAINER_COLOR,
            border_radius=afanes.ui.theme.CARD_RADIUS,
            padding=afanes.ui.theme.ITEM_GAP,
            content=ft.Column(
                controls=[
                    ft.Text(message, selectable=True),
                    ft.Row(
                        controls=[
                            ft.FilledButton(
                                content=(
                                    afanes.ui.strings.REVIEW_CONFIRM_DONE
                                    if self._confirmation == "done"
                                    else afanes.ui.strings.REVIEW_CONFIRM_DEFER
                                ),
                                on_click=self._confirm_status,
                                key="review-confirm",
                            ),
                            ft.TextButton(
                                content=afanes.ui.strings.REVIEW_CANCEL,
                                on_click=self._cancel_confirmation,
                                key="review-cancel-confirmation",
                            ),
                        ],
                        spacing=afanes.ui.theme.ITEM_GAP,
                        wrap=True,
                    ),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
        )

    async def _start(self) -> None:
        """Start a review session."""
        await self._state.start_review()
        self._reset_local_state()
        self.refresh()
        self._update()

    async def _finish(self) -> None:
        """Close the session and return to the browser."""
        await self._state.finish_review()
        self._reset_local_state()
        self.refresh()
        self._update()

    async def _next(self) -> None:
        """Advance past the current project."""
        await self._state.review_next()
        self._reset_local_state()
        self.refresh()
        self._update()

    async def _skip(self) -> None:
        """Skip the current item without changing it."""
        await self._state.review_skip()
        self._reset_local_state()
        self.refresh()
        self._update()

    async def _process_capture(self, path: Path) -> None:
        """Open the Processing Wizard for one review capture."""
        await self._state.begin_processing(path)
        self.refresh()
        self._update()

    async def _open(self, path: Path, section: afanes.ui.state.WorkspaceSection) -> None:
        """Open a project or action page and switch to its section."""
        await self._state.open_page(path)
        await self._state.set_section(section)
        self.refresh()
        self._update()

    def _process_handler(self, path: Path) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler that opens processing."""

        async def handle() -> None:
            await self._process_capture(path)

        return handle

    def _open_handler(
        self,
        path: Path,
        section: afanes.ui.state.WorkspaceSection,
    ) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler that opens one page."""

        async def handle() -> None:
            await self._open(path, section)

        return handle

    async def _toggle_create(self) -> None:
        """Open the next-action form."""
        self._creating = True
        self._confirmation = None
        self._form_error = None
        self.refresh()
        self._update()

    async def _cancel_create(self) -> None:
        """Close the next-action form without writing."""
        self._creating = False
        self._action_title = ""
        self._form_error = None
        self.refresh()
        self._update()

    async def _change_title(self) -> None:
        """Keep the typed action title for the next refresh."""
        field = next(
            (
                control
                for control in self._walk(self.root)
                if isinstance(control, ft.TextField) and control.key == "review-action-title"
            ),
            None,
        )
        self._action_title = "" if field is None else field.value or ""

    async def _create_action(self) -> None:
        """Create the typed next action for the current project."""
        if not self._action_title.strip():
            self._form_error = afanes.ui.strings.REVIEW_TITLE_REQUIRED
            self.refresh()
            self._update()
            return
        path = await self._state.create_review_action(self._action_title)
        if path is None:
            self._form_error = self._state.message
        else:
            self._creating = False
            self._action_title = ""
            self._form_error = None
        self.refresh()
        self._update()

    async def _confirm_done(self) -> None:
        """Ask for confirmation before marking the project done."""
        self._confirmation = "done"
        self._creating = False
        self.refresh()
        self._update()

    async def _confirm_defer(self) -> None:
        """Ask for confirmation before deferring the project."""
        self._confirmation = "later"
        self._creating = False
        self.refresh()
        self._update()

    async def _cancel_confirmation(self) -> None:
        """Close the status confirmation without writing."""
        self._confirmation = None
        self.refresh()
        self._update()

    async def _confirm_status(self) -> None:
        """Apply the confirmed project status change."""
        if self._confirmation == "done":
            changed = await self._state.mark_review_project_done()
        elif self._confirmation == "later":
            changed = await self._state.defer_review_project()
        else:
            changed = False
        if changed:
            self._confirmation = None
        self.refresh()
        self._update()

    def _reset_local_state(self) -> None:
        """Clear form and confirmation state between review items."""
        self._creating = False
        self._action_title = ""
        self._form_error = None
        self._confirmation = None

    @staticmethod
    def _walk(control: ft.Control) -> list[ft.Control]:
        """Return a control and its descendants for small local lookups."""
        found = [control]
        for child in getattr(control, "controls", []) or []:
            found.extend(ReviewView._walk(child))
        content = getattr(control, "content", None)
        if isinstance(content, ft.Control):
            found.extend(ReviewView._walk(content))
        return found
