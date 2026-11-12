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
from afanes.core.processing import AppendStepPlan, ProcessingOutcome, ProcessingPlan
from afanes.core.template_cards import TemplateCard
from afanes.core.vault.snapshot import VaultNote
from afanes.models.link import ReferenceScheme
from afanes.models.note import Status
from afanes.ui.components.banner import Banner


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
        self._plan_hidden = self._state.processing.plan is None
        self._suppress_suggestions = False

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
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            auto_follow_links=False,
            on_tap_link=self._ignore_link,
        )
        self.capture_panel = ft.Container(
            bgcolor=afanes.ui.theme.CARD_SURFACE_COLOR,
            border=ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR),
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
            ProcessingOutcome.PROJECT,
            ProcessingOutcome.DONE_NOW,
            ProcessingOutcome.APPEND_STEP,
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
        self.project = ft.TextField(
            label=afanes.ui.strings.PROCESSING_PROJECT_LABEL,
            hint_text="Launch",
            on_change=self._invalidate_plan,
            width=420,
            visible=False,
        )
        self._template_choices: dict[str, TemplateCard | None] = {}
        self.template = ft.Dropdown(
            label=afanes.ui.strings.PROCESSING_TEMPLATE_LABEL,
            options=[],
            value="empty",
            on_select=self._invalidate_plan,
            width=420,
            visible=False,
            key="processing-template",
        )
        self.template_description = ft.Text(
            "",
            color=afanes.ui.theme.MUTED_TEXT_COLOR,
            selectable=True,
            visible=False,
        )
        self.template_warning = ft.Text(
            "",
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            selectable=True,
            visible=False,
        )
        self.project_suggestions = ft.Column(controls=[], spacing=0, visible=False)
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
                self.template,
                self.template_description,
                self.template_warning,
                ft.Row(
                    controls=[self.due_date, self.project],
                    spacing=afanes.ui.theme.ITEM_GAP,
                    wrap=True,
                ),
                self.project_suggestions,
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
            bgcolor=afanes.ui.theme.CARD_SURFACE_COLOR,
            border=ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR),
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
            bgcolor=afanes.ui.theme.CARD_SURFACE_COLOR,
            border=ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR),
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

    def _template_options(self) -> list[ft.dropdown.Option]:
        """Build the template options from the catalog loaded for this capture.

        Returns
        -------
        list[flet.dropdown.Option]
            One option per valid card, followed by Empty. Duplicate titles
            include the relative card path so they stay distinguishable.
        """
        cards = self._state.processing.cards
        counts: dict[str, int] = {}
        for card in cards:
            counts[card.title.casefold()] = counts.get(card.title.casefold(), 0) + 1
        options: list[ft.dropdown.Option] = []
        self._template_choices = {}
        for card in cards:
            key = f"card:{card.relative_path.as_posix()}"
            self._template_choices[key] = card
            options.append(ft.dropdown.Option(key=key, text=self._template_option_text(card, counts)))
        self._template_choices["empty"] = None
        options.append(ft.dropdown.Option(key="empty", text=afanes.ui.strings.PROCESSING_TEMPLATE_EMPTY))
        return options

    def _refresh_template(self) -> None:
        """Rebuild the template options and keep the selection valid."""
        selected = self.template.value
        self.template.options = self._template_options()
        if selected not in self._template_choices:
            selected = "empty"
        self.template.value = selected

    @staticmethod
    def _template_option_text(card: TemplateCard, counts: dict[str, int]) -> str:
        """Return the display text for one card option."""
        duplicate = counts[card.title.casefold()] > 1
        if card.description:
            if duplicate:
                return afanes.ui.strings.PROCESSING_TEMPLATE_OPTION_DUPLICATE.format(
                    title=card.title,
                    description=card.description,
                    path=card.relative_path.as_posix(),
                )
            return afanes.ui.strings.PROCESSING_TEMPLATE_OPTION.format(
                title=card.title,
                description=card.description,
            )
        if duplicate:
            return afanes.ui.strings.PROCESSING_TEMPLATE_OPTION_DUPLICATE_PLAIN.format(
                title=card.title,
                path=card.relative_path.as_posix(),
            )
        return afanes.ui.strings.PROCESSING_TEMPLATE_OPTION_PLAIN.format(title=card.title)

    def _selected_card(self) -> TemplateCard | None:
        """Return the selected card, or ``None`` for Empty."""
        key = self.template.value or "empty"
        return self._template_choices.get(key)

    def _template_summary(self) -> str:
        """Return the description line for the selected template option."""
        card = self._selected_card()
        if card is None:
            return afanes.ui.strings.PROCESSING_TEMPLATE_DESCRIPTION_EMPTY
        return card.description or afanes.ui.strings.PROCESSING_TEMPLATE_NO_DESCRIPTION

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
        project: str | None = None
        card: TemplateCard | None = None

        if outcome in (ProcessingOutcome.PROJECT, ProcessingOutcome.DONE_NOW):
            if outcome is ProcessingOutcome.PROJECT and self.status.value is not None:
                status = Status(self.status.value)
            due_text = (self.due_date.value or "").strip()
            if due_text:
                try:
                    due_date = datetime.date.fromisoformat(due_text)
                except ValueError:
                    self._show_form_error(afanes.ui.strings.PROCESSING_INVALID_DATE)
                    return
        if outcome is ProcessingOutcome.APPEND_STEP:
            project = (self.project.value or "").strip() or None
        if outcome in (ProcessingOutcome.REFERENCE, ProcessingOutcome.LATER):
            card = self._selected_card()

        self.form_error.visible = False
        self._set_working(working=True)
        try:
            plan = await self._state.processing.build_plan(
                outcome,
                status=status,
                due_date=due_date,
                project=project,
                card=card,
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
            target = await self._state.processing.apply()
            if target is not None:
                await self._state.review.record_processed()
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
        self.project.disabled = working
        self.template.disabled = working
        for control in self.project_suggestions.controls:
            if isinstance(control, ft.ListTile):
                control.disabled = working
        self.preview_button.disabled = working
        self.cancel_button.disabled = working
        self.confirm_button.disabled = working
        self.done_button.disabled = working
        self.progress.visible = working
        self._update()

    def _refresh_dynamic(self) -> None:
        """Refresh visibility, plan details, and banners from application state."""
        state = self._state
        self._refresh_template()
        self.capture_title.value = (
            state.session.note_title(state.processing.note) if state.processing.note is not None else ""
        )
        self.capture_body.value = state.processing.body or ""

        outcome = self._selected_outcome()
        self.status.visible = outcome is ProcessingOutcome.PROJECT
        self.due_date.visible = outcome is ProcessingOutcome.PROJECT
        self.project.visible = outcome is ProcessingOutcome.APPEND_STEP
        reference_outcome = outcome in (ProcessingOutcome.REFERENCE, ProcessingOutcome.LATER)
        self.template.visible = reference_outcome
        self.template_description.visible = reference_outcome
        if reference_outcome:
            self.template_description.value = self._template_summary()
        issues = self._state.processing.card_issues
        self.template_warning.visible = reference_outcome and bool(issues)
        if issues:
            paths = ", ".join(issue.relative_path.as_posix() for issue in issues)
            self.template_warning.value = afanes.ui.strings.PROCESSING_TEMPLATE_INVALID.format(paths=paths)
        self._refresh_suggestions()

        success = state.processing.result is not None
        self.form.visible = not success
        self.success_panel.visible = success
        self.cancel_button.visible = not success
        self.done_button.visible = success
        if state.processing.result is not None:
            self.success_text.value = afanes.ui.strings.PROCESSING_SUCCESS_BODY.format(path=state.processing.result)

        plan = state.processing.plan
        show_plan = plan is not None and not self._plan_hidden and not success
        self.plan_panel.visible = show_plan
        if show_plan:
            self._populate_plan(plan)

        banners: list[ft.Control] = []
        if state.status.message is not None:
            banners.append(Banner(state.status.message).build())
        self.banners.controls = banners
        self.banners.visible = bool(banners)
        self.progress.visible = self._working or state.status.busy

    def _populate_plan(self, plan: ProcessingPlan | AppendStepPlan) -> None:
        """Fill the preview panel from a validated plan."""
        if isinstance(plan, AppendStepPlan):
            self.plan_destination.value = afanes.ui.strings.PROCESSING_DESTINATION.format(path=plan.project_path)
            self.plan_details.value = "\n".join(
                [
                    afanes.ui.strings.PROCESSING_OUTCOME_LABELS[ProcessingOutcome.APPEND_STEP.value],
                    f"Step: {plan.step_text}",
                ]
            )
            self.plan_warnings.controls = []
            self.plan_warnings.visible = False
            return
        self.plan_destination.value = afanes.ui.strings.PROCESSING_DESTINATION.format(path=plan.target_path)
        details = [afanes.ui.strings.PROCESSING_OUTCOME_LABELS[plan.outcome.value]]
        if plan.target_status is not None:
            details.append(f"Status: {plan.target_status.value}")
        if plan.due_date is not None:
            details.append(f"Due: {plan.due_date.isoformat()}")
        if plan.category is not None:
            details.append(afanes.ui.strings.PROCESSING_PLAN_CATEGORY.format(category=plan.category.value))
        if plan.scaffold is not None:
            details.append(afanes.ui.strings.PROCESSING_PLAN_SCAFFOLD)
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
        self.plan_warnings.controls = warnings
        self.plan_warnings.visible = bool(warnings)

    def _refresh_suggestions(self) -> None:
        """Refresh the append-target suggestions from the retained snapshot."""
        if self._suppress_suggestions:
            self._clear_suggestions(self.project_suggestions)
            return
        self._render_suggestions(
            self.project_suggestions,
            ReferenceScheme.PROJECT,
            (self.project.value or "").strip(),
            visible=self.project.visible,
            apply=self._apply_project_suggestion,
        )

    def _render_suggestions(
        self,
        column: ft.Column,
        scheme: ReferenceScheme,
        query: str,
        *,
        visible: bool,
        apply: Callable[[str], None],
    ) -> None:
        """Fill one suggestion list from the active field text."""
        if not visible or not query:
            self._clear_suggestions(column)
            return
        candidates = self._state.session.assignment_candidates(scheme, query)
        column.controls = [self._suggestion_tile(note, apply) for note in candidates]
        column.visible = bool(column.controls)

    @staticmethod
    def _clear_suggestions(column: ft.Column) -> None:
        """Empty one suggestion list and hide it."""
        column.controls = []
        column.visible = False

    def _suggestion_tile(self, note: VaultNote, apply: Callable[[str], None]) -> ft.Control:
        """Build one selectable project suggestion."""
        subtitle = note.name if note.name != note.title else None
        return ft.ListTile(
            title=note.title,
            subtitle=subtitle,
            dense=True,
            on_click=self._suggestion_handler(note.name, apply),
        )

    def _suggestion_handler(
        self,
        identity: str,
        apply: Callable[[str], None],
    ) -> Callable[[], Awaitable[None]]:
        """Bind a no-argument async selection handler to one page identity."""

        async def handle() -> None:
            self._suppress_suggestions = True
            try:
                apply(identity)
                self._invalidate_plan()
            finally:
                self._suppress_suggestions = False

        return handle

    def _apply_project_suggestion(self, identity: str) -> None:
        """Replace the project field with a page identity."""
        self.project.value = identity
