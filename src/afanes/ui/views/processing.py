# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Presentational Processing Wizard for one inbox capture."""

import datetime
from collections.abc import Awaitable, Callable

import flet as ft

import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
from afanes.core.processing import ProcessingOutcome, ProcessingPlan
from afanes.models.note import Status


def build_processing(
    update: Callable[[], None],
    on_cancel: Callable[[], Awaitable[None]],
    on_finish: Callable[[], Awaitable[None]],
) -> ft.Control:
    """Build the Processing Wizard.

    Parameters
    ----------
    update : Callable[[], None]
        Requests a repaint of the page.
    on_cancel : Callable[[], Awaitable[None]]
        Command that closes the wizard without writing.
    on_finish : Callable[[], Awaitable[None]]
        Command that closes the success state and returns to the Inbox.

    Returns
    -------
    ft.Control
        Composed wizard layout.
    """
    return ProcessingView(update, on_cancel, on_finish).build()


class ProcessingView:
    """Outcome form, plan preview, and confirmation for one capture.

    Parameters
    ----------
    update : Callable[[], None]
        Requests a repaint of the page.
    on_cancel : Callable[[], Awaitable[None]]
        Command that closes the wizard without writing.
    on_finish : Callable[[], Awaitable[None]]
        Command that closes the success state and returns to the Inbox.
    """

    def __init__(
        self,
        update: Callable[[], None],
        on_cancel: Callable[[], Awaitable[None]],
        on_finish: Callable[[], Awaitable[None]],
    ) -> None:
        """Build the wizard controls against the shared application state.

        Parameters
        ----------
        update : Callable[[], None]
            Requests a repaint of the page.
        on_cancel : Callable[[], Awaitable[None]]
            Command that closes the wizard without writing.
        on_finish : Callable[[], Awaitable[None]]
            Command that closes the success state and returns to the Inbox.
        """
        self._state = afanes.ui.state.app_state
        self._update = update
        self._on_cancel = on_cancel
        self._on_finish = on_finish
        self._working = False
        self._plan_hidden = self._state.processing_plan is None

        self.progress = ft.ProgressRing(
            width=16,
            height=16,
            visible=False,
            semantics_label=afanes.ui.strings.WORKING,
        )
        self.title = ft.Text(
            afanes.ui.strings.PROCESSING_TITLE,
            theme_style=ft.TextThemeStyle.HEADLINE_SMALL,
        )
        self.capture_title = ft.Text(
            "",
            theme_style=ft.TextThemeStyle.TITLE_LARGE,
        )
        self.capture_body = ft.Markdown(
            value="",
            selectable=True,
            auto_follow_links=False,
            on_tap_link=self._ignore_link,
        )
        self.capture_panel = ft.Container(
            bgcolor=afanes.ui.theme.SURFACE_CONTAINER_COLOR,
            border_radius=afanes.ui.theme.CARD_RADIUS,
            padding=afanes.ui.theme.ITEM_GAP,
            content=ft.Column(
                controls=[self.capture_title, self.capture_body],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
        )
        self.banners = ft.Column(controls=[], spacing=afanes.ui.theme.ITEM_GAP)
        self.form_error = ft.Text(
            "",
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            visible=False,
            selectable=True,
        )

        outcome_order = (
            ProcessingOutcome.ACTION,
            ProcessingOutcome.PROJECT,
            ProcessingOutcome.REFERENCE,
            ProcessingOutcome.LATER,
            ProcessingOutcome.TRASH,
        )
        self.outcome = ft.Dropdown(
            label=afanes.ui.strings.PROCESSING_OUTCOME_LABEL,
            options=[
                ft.dropdown.Option(
                    key=outcome.value,
                    text=afanes.ui.strings.PROCESSING_OUTCOME_LABELS[outcome.value],
                )
                for outcome in outcome_order
            ],
            on_select=self._invalidate_plan,
            width=280,
        )
        self.status = ft.Dropdown(
            label=afanes.ui.strings.PROCESSING_STATUS_LABEL,
            options=[
                ft.dropdown.Option(key=status.value, text=label)
                for status, label in (
                    (Status.ACTIVE, afanes.ui.strings.PROCESSING_STATUS_LABELS["active"]),
                    (Status.WAITING, afanes.ui.strings.PROCESSING_STATUS_LABELS["waiting"]),
                    (Status.DONE, afanes.ui.strings.PROCESSING_STATUS_LABELS["done"]),
                    (Status.CANCELLED, afanes.ui.strings.PROCESSING_STATUS_LABELS["cancelled"]),
                    (Status.ARCHIVED, afanes.ui.strings.PROCESSING_STATUS_LABELS["archived"]),
                    (Status.LATER, afanes.ui.strings.PROCESSING_STATUS_LABELS["later"]),
                )
            ],
            value=Status.ACTIVE.value,
            on_select=self._invalidate_plan,
            width=220,
            visible=False,
        )
        self.due_date = ft.TextField(
            label=afanes.ui.strings.PROCESSING_DUE_DATE_LABEL,
            hint_text="2026-11-20",
            on_change=self._invalidate_plan,
            width=260,
            visible=False,
        )
        self.people = ft.TextField(
            label=afanes.ui.strings.PROCESSING_PEOPLE_LABEL,
            hint_text="Ada, Grace",
            on_change=self._invalidate_plan,
            width=420,
            visible=False,
        )
        self.project = ft.TextField(
            label=afanes.ui.strings.PROCESSING_PROJECT_LABEL,
            hint_text="Launch",
            on_change=self._invalidate_plan,
            width=420,
            visible=False,
        )
        self.preview_button = ft.FilledButton(
            content=afanes.ui.strings.PROCESSING_PREVIEW_ACTION,
            icon=ft.Icons.VISIBILITY,
            on_click=self._preview,
        )
        self.cancel_button = ft.TextButton(
            content=afanes.ui.strings.PROCESSING_CANCEL_ACTION,
            on_click=self._cancel,
            key="processing-cancel",
        )
        self.form = ft.Column(
            controls=[
                ft.Text(
                    afanes.ui.strings.PROCESSING_OUTCOME_LABEL,
                    theme_style=ft.TextThemeStyle.TITLE_MEDIUM,
                ),
                ft.Row(
                    controls=[self.outcome, self.status],
                    spacing=afanes.ui.theme.ITEM_GAP,
                    wrap=True,
                ),
                ft.Row(
                    controls=[self.due_date, self.project],
                    spacing=afanes.ui.theme.ITEM_GAP,
                    wrap=True,
                ),
                self.people,
                self.form_error,
                self.preview_button,
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
        )

        self.plan_destination = ft.Text("", selectable=True)
        self.plan_details = ft.Text("", selectable=True)
        self.plan_warnings = ft.Column(controls=[], spacing=afanes.ui.theme.ITEM_GAP)
        self.confirm_button = ft.FilledButton(
            content=afanes.ui.strings.PROCESSING_CONFIRM_ACTION,
            icon=ft.Icons.CHECK,
            on_click=self._confirm,
        )
        self.plan_panel = ft.Container(
            bgcolor=afanes.ui.theme.SURFACE_CONTAINER_COLOR,
            border_radius=afanes.ui.theme.CARD_RADIUS,
            padding=afanes.ui.theme.ITEM_GAP,
            visible=False,
            content=ft.Column(
                controls=[
                    ft.Text(
                        afanes.ui.strings.PROCESSING_PLAN_TITLE,
                        theme_style=ft.TextThemeStyle.TITLE_MEDIUM,
                    ),
                    self.plan_destination,
                    self.plan_details,
                    self.plan_warnings,
                    self.confirm_button,
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
        )

        self.success_title = ft.Text(
            afanes.ui.strings.PROCESSING_SUCCESS_TITLE,
            theme_style=ft.TextThemeStyle.TITLE_LARGE,
        )
        self.success_text = ft.Text("", selectable=True)
        self.done_button = ft.FilledButton(
            content=afanes.ui.strings.PROCESSING_DONE_ACTION,
            on_click=self._done,
            key="processing-done",
        )
        self.success_panel = ft.Container(
            bgcolor=afanes.ui.theme.SURFACE_CONTAINER_COLOR,
            border_radius=afanes.ui.theme.CARD_RADIUS,
            padding=afanes.ui.theme.ITEM_GAP,
            visible=False,
            content=ft.Column(
                controls=[self.success_title, self.success_text, self.done_button],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
        )

        self.actions = ft.Row(
            controls=[
                self.cancel_button,
                self.done_button,
                self.progress,
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.root = ft.Column(
            controls=[
                self.title,
                self.capture_panel,
                self.banners,
                self.form,
                self.plan_panel,
                self.success_panel,
                self.actions,
            ],
            spacing=afanes.ui.theme.SECTION_GAP,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            key="processing-view",
        )
        self._refresh_dynamic()

    def build(self) -> ft.Control:
        """Return the root control for the wizard.

        Returns
        -------
        ft.Control
            Composed Processing Wizard layout.
        """
        return self.root

    def _ignore_link(self) -> None:
        """Swallow a link tap in the capture preview."""
        return None

    def _selected_outcome(self) -> ProcessingOutcome | None:
        """Return the selected outcome, or ``None`` when the field is empty."""
        if self.outcome.value is None:
            return None
        try:
            return ProcessingOutcome(self.outcome.value)
        except ValueError:
            return None

    def _invalidate_plan(self) -> None:
        """Hide stale plan details after the form changes."""
        self._plan_hidden = True
        self.form_error.visible = False
        self._refresh_dynamic()
        self._update()

    def _show_form_error(self, message: str) -> None:
        """Show a local form error without calling the controller."""
        self.form_error.value = message
        self.form_error.visible = True
        self._update()

    async def _preview(self) -> None:
        """Build a processing plan from the form values."""
        outcome = self._selected_outcome()
        if outcome is None:
            self._show_form_error(afanes.ui.strings.PROCESSING_EMPTY_OUTCOME)
            return

        status: Status | None = None
        due_date: datetime.date | None = None
        people: tuple[str, ...] = ()
        project: str | None = None

        if outcome in (ProcessingOutcome.ACTION, ProcessingOutcome.PROJECT):
            if self.status.value is not None:
                status = Status(self.status.value)
            due_text = (self.due_date.value or "").strip()
            if due_text:
                try:
                    due_date = datetime.date.fromisoformat(due_text)
                except ValueError:
                    self._show_form_error(afanes.ui.strings.PROCESSING_INVALID_DATE)
                    return
        if outcome is not ProcessingOutcome.TRASH:
            people = tuple(part.strip() for part in (self.people.value or "").split(",") if part.strip())
        if outcome is ProcessingOutcome.ACTION:
            project = (self.project.value or "").strip() or None

        self.form_error.visible = False
        self._set_working(working=True)
        try:
            plan = await self._state.plan_processing(
                outcome,
                status=status,
                due_date=due_date,
                people=people,
                project=project,
            )
        finally:
            self._set_working(working=False)
        self._plan_hidden = plan is None
        self._refresh_dynamic()
        self._update()

    async def _confirm(self) -> None:
        """Apply the current plan after confirmation."""
        self._set_working(working=True)
        try:
            await self._state.apply_processing()
        finally:
            self._set_working(working=False)
        self._refresh_dynamic()
        self._update()

    async def _cancel(self) -> None:
        """Close the wizard without writing."""
        await self._on_cancel()

    async def _done(self) -> None:
        """Close the success state and return to the Inbox."""
        await self._on_finish()

    def _set_working(self, *, working: bool) -> None:
        """Disable controls and show progress while a command runs."""
        self._working = working
        self.outcome.disabled = working
        self.status.disabled = working
        self.due_date.disabled = working
        self.people.disabled = working
        self.project.disabled = working
        self.preview_button.disabled = working
        self.cancel_button.disabled = working
        self.confirm_button.disabled = working
        self.done_button.disabled = working
        self.progress.visible = working
        self._update()

    def _refresh_dynamic(self) -> None:
        """Refresh visibility, plan details, and banners from application state."""
        state = self._state
        self.capture_title.value = state.processing_note.stem if state.processing_note is not None else ""
        self.capture_body.value = state.processing_body or ""

        outcome = self._selected_outcome()
        actionable = outcome in (ProcessingOutcome.ACTION, ProcessingOutcome.PROJECT)
        self.status.visible = actionable
        self.due_date.visible = actionable
        self.project.visible = outcome is ProcessingOutcome.ACTION
        self.people.visible = outcome is not None and outcome is not ProcessingOutcome.TRASH

        success = state.processing_result is not None
        self.form.visible = not success
        self.success_panel.visible = success
        self.cancel_button.visible = not success
        self.done_button.visible = success
        if state.processing_result is not None:
            self.success_text.value = afanes.ui.strings.PROCESSING_SUCCESS_BODY.format(path=state.processing_result)

        plan = state.processing_plan
        show_plan = plan is not None and not self._plan_hidden and not success
        self.plan_panel.visible = show_plan
        if show_plan:
            self._populate_plan(plan)

        banners: list[ft.Control] = []
        if state.message is not None:
            banners.append(_banner(state.message))
        self.banners.controls = banners
        self.banners.visible = bool(banners)
        self.progress.visible = self._working or state.busy

    def _populate_plan(self, plan: ProcessingPlan) -> None:
        """Fill the preview panel from a validated plan."""
        self.plan_destination.value = afanes.ui.strings.PROCESSING_DESTINATION.format(path=plan.target_path)
        details = [afanes.ui.strings.PROCESSING_OUTCOME_LABELS[plan.outcome.value]]
        if plan.target_status is not None:
            details.append(f"Status: {plan.target_status.value}")
        if plan.due_date is not None:
            details.append(f"Due: {plan.due_date.isoformat()}")
        if plan.people:
            details.append("People: " + ", ".join(reference.name for reference in plan.people))
        if plan.project is not None:
            details.append(f"Project: {plan.project.name}")
        self.plan_details.value = "\n".join(details)

        warnings: list[ft.Control] = []
        if plan.outcome is ProcessingOutcome.TRASH and plan.reference_count:
            warnings.append(
                ft.Text(
                    afanes.ui.strings.PROCESSING_REFERENCE_WARNING.format(count=plan.reference_count),
                    color=afanes.ui.theme.ERROR_TEXT_COLOR,
                    selectable=True,
                )
            )
        elif plan.changes_scheme and plan.reference_count:
            warnings.append(
                ft.Text(
                    afanes.ui.strings.PROCESSING_SCHEME_WARNING.format(count=plan.reference_count),
                    color=afanes.ui.theme.ERROR_TEXT_COLOR,
                    selectable=True,
                )
            )
        if plan.unresolved_references:
            names = ", ".join(reference.name for reference in plan.unresolved_references)
            warnings.append(
                ft.Text(
                    afanes.ui.strings.PROCESSING_UNRESOLVED.format(names=names),
                    color=afanes.ui.theme.MUTED_TEXT_COLOR,
                    selectable=True,
                )
            )
        self.plan_warnings.controls = warnings
        self.plan_warnings.visible = bool(warnings)


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
