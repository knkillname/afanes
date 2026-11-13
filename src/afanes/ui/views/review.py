# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Guided review cards for captures, steps, and projects.

The view reads a snapshotted review session from the shared application state
and forwards every write to its commands. It never parses Markdown or performs
file I/O.
"""

import datetime
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
from afanes.ui.components.step_text import StepText


class ReviewView:
    """Review queue, step cards, project cards, and the completion summary.

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
        self._form_mode: str | None = None
        self._typed = ""
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
        session = self._state.review.review_session
        controls: list[ft.Control] = []
        if self._state.status.message is not None:
            controls.append(Banner(self._state.status.message).build())
        if session is None:
            controls.append(self._start_card())
        elif session.complete:
            controls.append(self._completion_card(session.reviewed_count, session.skipped_count))
        else:
            item = session.current
            if item is None:
                controls.append(self._completion_card(session.reviewed_count, session.skipped_count))
            elif item.kind is afanes.core.search.ReviewItemKind.INBOX:
                controls.append(self._capture_card(item))
            elif item.step is not None:
                controls.append(self._step_card(item))
            else:
                controls.append(self._project_card(item))
        self.root.controls = controls

    def _start_card(self) -> ft.Control:
        """Build the review entry card or its zero state."""
        count = self._state.browser.pending_count()
        if count == 0:
            body = ft.Column(
                controls=[
                    ft.Text(afanes.ui.strings.REVIEW_ZERO_TITLE, style=afanes.ui.theme.TEXT_ROLES["title-3"]),
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
                ft.Text(afanes.ui.strings.REVIEW_TITLE, style=afanes.ui.theme.TEXT_ROLES["title-2"]),
                ft.Text(afanes.ui.strings.review_pending(count), selectable=True),
                ft.FilledButton(
                    content=afanes.ui.strings.REVIEW_START_ACTION,
                    icon=ft.Icons.PLAY_ARROW_OUTLINED,
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
                ft.Text(afanes.ui.strings.REVIEW_COMPLETE_TITLE, style=afanes.ui.theme.TEXT_ROLES["title-2"]),
                ft.Text(
                    afanes.ui.strings.REVIEW_COMPLETE_BODY.format(reviewed=reviewed, skipped=skipped),
                    selectable=True,
                ),
                ft.FilledButton(
                    content=afanes.ui.strings.REVIEW_BACK_TO_BROWSER,
                    icon=ft.Icons.ARROW_BACK_OUTLINED,
                    on_click=self._finish,
                    key="review-finish",
                ),
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
        )
        return Card(body).build()

    def _capture_card(self, item: ReviewItem) -> ft.Control:
        """Build the card for an inbox capture awaiting processing."""
        title = self._state.session.note_title(item.path)
        body = ft.Column(
            controls=[
                ft.Text(afanes.ui.strings.REVIEW_CAPTURE_TITLE, style=afanes.ui.theme.TEXT_ROLES["heading"]),
                ft.Text(title, style=afanes.ui.theme.TEXT_ROLES["title-2"], selectable=True),
                ft.Row(
                    controls=[
                        ft.FilledButton(
                            content=afanes.ui.strings.REVIEW_PROCESS_ACTION,
                            icon=ft.Icons.PLAY_ARROW_OUTLINED,
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

    def _step_card(self, item: ReviewItem) -> ft.Control:
        """Build a due-step or waiting-step card with its actions."""
        step = item.step
        summary = item.project
        if step is None or summary is None:
            return self._broken_card(item)
        due = item.kind is afanes.core.search.ReviewItemKind.DUE_STEP
        title = afanes.ui.strings.REVIEW_DUE_STEP_TITLE if due else afanes.ui.strings.REVIEW_WAITING_STEP_TITLE
        controls: list[ft.Control] = [
            ft.Text(title, style=afanes.ui.theme.TEXT_ROLES["heading"]),
            ft.Text(summary.note.title, style=afanes.ui.theme.TEXT_ROLES["title-4"], selectable=True),
            StepText(step.text, afanes.ui.theme.TEXT_ROLES["title-2"], selectable=True).build(),
        ]
        if step.owners:
            controls.append(
                ft.Text(
                    afanes.ui.strings.REVIEW_STEP_OWNERS.format(owners=", ".join(step.owners)),
                    color=afanes.ui.theme.MUTED_TEXT_COLOR,
                )
            )
        if step.plan is not None:
            controls.append(
                ft.Text(
                    afanes.ui.strings.PAGE_STEP_PLAN.format(date=step.plan.isoformat()),
                    color=afanes.ui.theme.MUTED_TEXT_COLOR,
                )
            )
        controls.append(self._form_controls())
        controls.append(self._step_actions(due=due))
        return Card(ft.Column(controls=controls, spacing=afanes.ui.theme.ITEM_GAP)).build()

    def _step_actions(self, *, due: bool) -> ft.Control:
        """Build the action row for one due or waiting step."""
        buttons: list[ft.Control] = []
        if due:
            buttons.extend(
                [
                    ft.FilledButton(
                        content=afanes.ui.strings.REVIEW_DO_NOW,
                        icon=ft.Icons.CHECK_OUTLINED,
                        on_click=self._do_now,
                        key="review-do-now",
                    ),
                    ft.OutlinedButton(
                        content=afanes.ui.strings.REVIEW_POSTPONE,
                        on_click=self._open_postpone,
                        key="review-postpone",
                    ),
                    ft.OutlinedButton(
                        content=afanes.ui.strings.REVIEW_DELEGATE,
                        on_click=self._open_delegate,
                        key="review-delegate",
                    ),
                ]
            )
        else:
            buttons.append(
                ft.OutlinedButton(
                    content=afanes.ui.strings.REVIEW_REASSIGN,
                    on_click=self._open_reassign,
                    key="review-reassign",
                )
            )
        buttons.extend(
            [
                ft.TextButton(
                    content=afanes.ui.strings.REVIEW_OPEN_PROJECT,
                    icon=ft.Icons.OPEN_IN_NEW_OUTLINED,
                    on_click=self._open_project,
                    key="review-open-project",
                ),
                ft.TextButton(
                    content=afanes.ui.strings.REVIEW_SKIP,
                    on_click=self._skip,
                    key="review-skip",
                ),
            ]
        )
        return ft.Row(controls=buttons, spacing=afanes.ui.theme.ITEM_GAP, wrap=True)

    def _project_card(self, item: ReviewItem) -> ft.Control:
        """Build the project review card with its next step."""
        summary = item.project
        if summary is None:
            return self._broken_card(item)
        controls: list[ft.Control] = [
            ft.Text(afanes.ui.strings.REVIEW_TITLE, style=afanes.ui.theme.TEXT_ROLES["heading"]),
            ft.Text(summary.note.title, style=afanes.ui.theme.TEXT_ROLES["title-2"], selectable=True),
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
        controls.append(self._form_controls())
        controls.append(self._confirmation_controls())
        if summary.next_step is None:
            controls.append(
                ft.Row(
                    controls=[
                        ft.OutlinedButton(
                            content=afanes.ui.strings.REVIEW_CREATE_STEP,
                            icon=ft.Icons.ADD_OUTLINED,
                            on_click=self._open_add_step,
                            key="review-create",
                        ),
                        ft.OutlinedButton(
                            content=afanes.ui.strings.REVIEW_MARK_DONE,
                            icon=ft.Icons.CHECK_OUTLINED,
                            on_click=self._confirm_done,
                            key="review-mark-done",
                        ),
                        ft.OutlinedButton(
                            content=afanes.ui.strings.REVIEW_DEFER,
                            icon=ft.Icons.SCHEDULE_OUTLINED,
                            on_click=self._confirm_defer,
                            key="review-defer",
                        ),
                    ],
                    spacing=afanes.ui.theme.ITEM_GAP,
                    wrap=True,
                )
            )
        controls.append(
            ft.Row(
                controls=[
                    ft.TextButton(
                        content=afanes.ui.strings.REVIEW_OPEN_PROJECT,
                        icon=ft.Icons.OPEN_IN_NEW_OUTLINED,
                        on_click=self._open_project,
                        key="review-open-project",
                    ),
                    ft.FilledButton(
                        content=afanes.ui.strings.REVIEW_NEXT,
                        icon=ft.Icons.ARROW_FORWARD_OUTLINED,
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
        return Card(ft.Column(controls=controls, spacing=afanes.ui.theme.ITEM_GAP)).build()

    def _next_step_controls(self, summary: ProjectSummary) -> list[ft.Control]:
        """Build the next-step and remaining-step controls."""
        controls: list[ft.Control] = []
        if summary.next_step is None:
            controls.append(
                ft.Text(
                    afanes.ui.strings.REVIEW_NO_NEXT_STEP,
                    color=afanes.ui.theme.MUTED_TEXT_COLOR,
                    selectable=True,
                )
            )
            return controls
        body_style = ft.TextStyle(color=afanes.ui.theme.TEXT_COLOR)
        controls.append(
            ft.Column(
                controls=[
                    ft.Text(afanes.ui.strings.REVIEW_NEXT_STEP, style=afanes.ui.theme.TEXT_ROLES["heading"]),
                    StepText(summary.next_step.text, body_style, selectable=True).build(),
                ],
                spacing=0,
            )
        )
        remaining = summary.open_steps[1:]
        if remaining:
            controls.append(ft.Text(afanes.ui.strings.REVIEW_OTHER_STEPS, style=afanes.ui.theme.TEXT_ROLES["heading"]))
            controls.extend(StepText(step.text, body_style, selectable=True).build() for step in remaining)
        return controls

    def _broken_card(self, item: ReviewItem) -> ft.Control:
        """Build the fallback card for an unreadable review item."""
        return Card(
            ft.Column(
                controls=[
                    ft.Text(afanes.ui.strings.REVIEW_PROJECT_FAILED.format(detail=item.path.as_posix())),
                    ft.TextButton(content=afanes.ui.strings.REVIEW_SKIP, on_click=self._skip),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
            )
        ).build()

    def _form_controls(self) -> ft.Control:
        """Build the inline form for the active step action."""
        if self._form_mode is None:
            return ft.Container(visible=False)
        error = ft.Text(
            self._form_error or "",
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            visible=self._form_error is not None,
            selectable=True,
        )
        label = self._form_label()
        field = ft.TextField(
            label=label,
            hint_text="2026-11-20" if self._form_mode == "postpone" else "Ada",
            value=self._typed,
            on_change=self._change_typed,
            key="review-form-field",
        )
        return ft.Column(
            controls=[
                field,
                error,
                ft.Row(
                    controls=[
                        ft.FilledButton(
                            content=afanes.ui.strings.REVIEW_CONFIRM,
                            icon=ft.Icons.CHECK_OUTLINED,
                            on_click=self._submit_form,
                            key="review-form-submit",
                        ),
                        ft.TextButton(
                            content=afanes.ui.strings.REVIEW_CANCEL,
                            on_click=self._cancel_form,
                            key="review-form-cancel",
                        ),
                    ],
                    spacing=afanes.ui.theme.ITEM_GAP,
                    wrap=True,
                ),
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
        )

    def _form_label(self) -> str:
        """Return the label for the active inline form."""
        if self._form_mode in {"delegate", "reassign"}:
            return afanes.ui.strings.REVIEW_OWNER_LABEL
        if self._form_mode == "postpone":
            return afanes.ui.strings.REVIEW_POSTPONE_LABEL
        return afanes.ui.strings.REVIEW_STEP_TITLE_LABEL

    def _confirmation_controls(self) -> ft.Control:
        """Build the inline confirmation for closing or deferring."""
        if self._confirmation is None:
            return ft.Container(visible=False)
        message = afanes.ui.strings.REVIEW_MARK_DONE if self._confirmation == "done" else afanes.ui.strings.REVIEW_DEFER
        return ft.Container(
            bgcolor=afanes.ui.theme.CARD_SURFACE_COLOR,
            border=ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR),
            border_radius=afanes.ui.theme.SURFACE_RADIUS,
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
        await self._state.review.start()
        self._reset_local_state()
        self.refresh()
        self._update()

    async def _finish(self) -> None:
        """Close the session and return to the browser."""
        await self._state.review.finish()
        self._reset_local_state()
        self.refresh()
        self._update()

    async def _next(self) -> None:
        """Advance past the current project."""
        await self._state.review.next()
        self._reset_local_state()
        self.refresh()
        self._update()

    async def _skip(self) -> None:
        """Skip the current item without changing it."""
        await self._state.review.skip()
        self._reset_local_state()
        self.refresh()
        self._update()

    async def _process_capture(self, path: Path) -> None:
        """Open the Processing Wizard for one review capture."""
        await self._state.processing.begin(path)
        self.refresh()
        self._update()

    async def _open_project(self) -> None:
        """Open the current item's project page."""
        await self._state.review.open_project()
        self.refresh()
        self._update()

    async def _do_now(self) -> None:
        """Complete the current due step."""
        await self._state.review.do_now()
        self._reset_local_state()
        self.refresh()
        self._update()

    async def _open_postpone(self) -> None:
        """Open the postpone form."""
        self._open_form("postpone")

    async def _open_delegate(self) -> None:
        """Open the delegate form."""
        self._open_form("delegate")

    async def _open_reassign(self) -> None:
        """Open the reassign form."""
        self._open_form("reassign")

    async def _open_add_step(self) -> None:
        """Open the next-step form for a stalled project."""
        self._open_form("add_step")

    def _open_form(self, mode: str) -> None:
        """Show one inline form and clear any confirmation."""
        self._form_mode = mode
        self._typed = ""
        self._form_error = None
        self._confirmation = None
        self.refresh()
        self._update()

    async def _cancel_form(self) -> None:
        """Close the inline form without writing."""
        self._form_mode = None
        self._typed = ""
        self._form_error = None
        self.refresh()
        self._update()

    async def _change_typed(self) -> None:
        """Keep the typed form value for the next refresh."""
        field = next(
            (
                control
                for control in self._walk(self.root)
                if isinstance(control, ft.TextField) and control.key == "review-form-field"
            ),
            None,
        )
        self._typed = "" if field is None else field.value or ""

    async def _submit_form(self) -> None:
        """Submit the active inline form."""
        value = self._typed.strip()
        if not value:
            self._form_error = (
                afanes.ui.strings.REVIEW_INVALID_DATE
                if self._form_mode == "postpone"
                else afanes.ui.strings.REVIEW_TITLE_REQUIRED
            )
            self.refresh()
            self._update()
            return
        changed = False
        if self._form_mode == "postpone":
            try:
                plan = datetime.date.fromisoformat(value)
            except ValueError:
                self._form_error = afanes.ui.strings.REVIEW_INVALID_DATE
                self.refresh()
                self._update()
                return
            changed = await self._state.review.postpone(plan)
        elif self._form_mode == "delegate":
            changed = await self._state.review.delegate(value)
        elif self._form_mode == "reassign":
            changed = await self._state.review.reassign(value)
        elif self._form_mode == "add_step":
            changed = await self._state.review.add_step(value) is not None
        if changed:
            self._form_mode = None
            self._typed = ""
            self._form_error = None
        else:
            self._form_error = self._state.status.message
        self.refresh()
        self._update()

    async def _confirm_done(self) -> None:
        """Ask for confirmation before marking the project done."""
        self._confirmation = "done"
        self._form_mode = None
        self.refresh()
        self._update()

    async def _confirm_defer(self) -> None:
        """Ask for confirmation before deferring the project."""
        self._confirmation = "later"
        self._form_mode = None
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
            changed = await self._state.review.mark_project_done()
        elif self._confirmation == "later":
            changed = await self._state.review.defer_project()
        else:
            changed = False
        if changed:
            self._confirmation = None
        self.refresh()
        self._update()

    def _process_handler(self, path: Path) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async handler that opens processing."""

        async def handle() -> None:
            await self._process_capture(path)

        return handle

    def _reset_local_state(self) -> None:
        """Clear form and confirmation state between review items."""
        self._form_mode = None
        self._typed = ""
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
