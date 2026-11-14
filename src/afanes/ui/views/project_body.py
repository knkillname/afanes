# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Step-aware read mode for one project body.

The view renders the blocks returned by the page state. Prose stays ordinary
Markdown; a task list becomes an accent card whose rows expose the checked
state, step text, metadata, and the plan and owner actions. The view performs
no Markdown parsing and no vault I/O.
"""

import datetime
from collections.abc import Awaitable, Callable

import flet as ft

import afanes.core.vault.snapshot
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
from afanes.core.editing import DraftMode
from afanes.core.project_body import ProseBlock, StepEntry, StepListBlock
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType
from afanes.models.step import ProjectStep, StepEdit, StepEditKind
from afanes.ui.components.step_text import StepText, StepTextOptions

type PickDate = Callable[[datetime.date | None], Awaitable[datetime.date | None]]


class ProjectBodyView:
    """Render one project's prose and step cards in read mode.

    Parameters
    ----------
    update : Callable[[], None]
        Requests a repaint of the page.
    on_follow_link : Callable[[str], Awaitable[None]]
        Command that resolves one link destination.
    pick_date : PickDate | None
        Command that opens the date picker and returns the chosen date, or
        ``None`` when the presentation has no picker.
    """

    def __init__(
        self,
        update: Callable[[], None],
        on_follow_link: Callable[[str], Awaitable[None]],
        pick_date: PickDate | None = None,
        on_follow_role: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        """Build the project body controls against the shared application state.

        Parameters
        ----------
        update : Callable[[], None]
            Requests a repaint of the page.
        on_follow_link : Callable[[str], Awaitable[None]]
            Command that resolves one link destination.
        pick_date : PickDate | None
            Command that opens the date picker.
        on_follow_role : Callable[[str], Awaitable[None]] | None
            Command that opens or creates the page for a role name, or ``None``
            when role navigation is unavailable.
        """
        self._state = afanes.ui.state.app_state
        self._update = update
        self._on_follow_link = on_follow_link
        self._on_follow_role = on_follow_role
        self._pick_date = pick_date
        self._owner_panel: int | None = None
        self._owner_query = ""
        self._error = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["caption"],
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            visible=False,
            selectable=True,
        )
        self._owner_field = ft.TextField(
            label=afanes.ui.strings.PAGE_STEP_OWNER_ADD,
            hint_text=afanes.ui.strings.PAGE_STEP_OWNER_HINT,
            expand=True,
            on_submit=self._add_owner_from_field,
            on_change=self._change_owner_query,
            key="step-owner-field",
        )
        self._owner_suggestions = ft.Column(controls=[], spacing=0, visible=False)
        self.root = ft.Column(
            controls=[],
            spacing=afanes.ui.theme.SECTION_GAP,
            key="project-body",
        )
        self.refresh()

    def build(self) -> ft.Control:
        """Return the root control for the project body.

        Returns
        -------
        ft.Control
            Rendered prose and step cards for the open project.
        """
        return self.root

    def refresh(self) -> None:
        """Rebuild every block from the shared page state."""
        state = self._state
        page = state.pages.page
        labels = state.pages.page_labels
        editing = state.pages.editing or state.pages.page_mode is DraftMode.RAW
        visible = (
            page is not None
            and not editing
            and labels is not None
            and labels.note_type is NoteType.PROJECT
            and state.pages.trash_entry is None
        )
        self.root.visible = visible
        if not visible:
            self.root.controls = []
            self._close_owner_panel()
            return
        blocks = state.pages.page_body_blocks
        self._keep_owner_panel(blocks)
        controls: list[ft.Control] = [self._error]
        controls.extend(self._block_control(block) for block in blocks)
        if not blocks:
            controls.append(
                ft.Text(
                    afanes.ui.strings.PAGE_PROJECT_EMPTY_BODY,
                    color=afanes.ui.theme.MUTED_TEXT_COLOR,
                    selectable=True,
                )
            )
        self.root.controls = controls

    def _keep_owner_panel(self, blocks: tuple[object, ...]) -> None:
        """Close a panel whose step disappeared."""
        if self._owner_panel is None:
            return
        for block in blocks:
            if isinstance(block, StepListBlock) and any(
                entry.step.line_index == self._owner_panel for entry in block.entries
            ):
                return
        self._close_owner_panel()

    def _block_control(self, block: object) -> ft.Control:
        """Build one prose block or one step card."""
        if isinstance(block, ProseBlock):
            return self._prose(block)
        if isinstance(block, StepListBlock):
            return self._step_card(block)
        return ft.Text("")

    def _prose(self, block: ProseBlock) -> ft.Control:
        """Render one prose block as ordinary Markdown."""
        return ft.Markdown(
            value=block.source,
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            auto_follow_links=False,
            on_tap_link=self._follow_link,
        )

    def _step_card(self, block: StepListBlock) -> ft.Control:
        """Render one contiguous task list as an accent card."""
        rows: list[ft.Control] = []
        for entry in block.entries:
            rows.append(self._step_row(entry))
            if self._owner_panel == entry.step.line_index:
                rows.append(self._owner_panel_control(entry.step))
        return ft.Container(
            bgcolor=afanes.ui.theme.STEP_SURFACE_COLOR,
            border=ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR),
            border_radius=afanes.ui.theme.SURFACE_RADIUS,
            padding=afanes.ui.theme.ITEM_GAP,
            content=ft.Column(
                controls=rows,
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
            key=f"step-card-{block.start_line}",
        )

    def _step_row(self, entry: StepEntry) -> ft.Control:
        """Render one step with its text, metadata, and actions."""
        step = entry.step
        details = self._details(step)
        text_style = ft.TextStyle(color=afanes.ui.theme.STEP_TEXT_COLOR)
        row = ft.Row(
            controls=[
                ft.Checkbox(
                    value=step.checked,
                    on_change=self._toggle_handler(step),
                    semantics_label=step.text,
                    active_color=afanes.ui.theme.STEP_TEXT_COLOR,
                ),
                StepText(
                    step.text,
                    text_style,
                    StepTextOptions(expand=True, on_tap_link=self._follow_link),
                ).build(),
                self._step_action(
                    ft.Icons.CALENDAR_MONTH_OUTLINED,
                    afanes.ui.strings.PAGE_STEP_PLAN_ACTION,
                    self._plan_handler(step),
                ),
                *(
                    [
                        self._step_action(
                            ft.Icons.EVENT_BUSY_OUTLINED,
                            afanes.ui.strings.PAGE_STEP_CLEAR_PLAN,
                            self._clear_plan_handler(step),
                        )
                    ]
                    if step.plan is not None
                    else []
                ),
                self._step_action(
                    ft.Icons.PERSON_OUTLINE,
                    afanes.ui.strings.PAGE_STEP_OWNER_ACTION,
                    self._owner_handler(step),
                ),
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        controls: list[ft.Control] = [row]
        if entry.detail:
            controls.append(
                StepText(
                    entry.detail,
                    text_style,
                    StepTextOptions(on_tap_link=self._follow_link),
                ).build()
            )
        if details:
            controls.append(
                ft.Row(
                    controls=details,
                    spacing=afanes.ui.theme.ITEM_GAP,
                    wrap=True,
                )
            )
        return ft.Container(
            padding=ft.Padding.only(left=entry.depth * afanes.ui.theme.STEP_INDENT),
            content=ft.Column(controls=controls, spacing=0),
        )

    def _details(self, step: ProjectStep) -> list[ft.Control]:
        """Build the structured metadata labels for one step."""
        details: list[ft.Control] = []
        if step.owners:
            details.append(self._owner_detail(step))
        if step.plan is not None:
            details.append(self._detail(afanes.ui.strings.PAGE_STEP_PLAN.format(date=step.plan.isoformat())))
        if step.actual is not None:
            details.append(self._detail(afanes.ui.strings.PAGE_STEP_ACTUAL.format(date=step.actual.isoformat())))
        if step.tags:
            details.append(self._detail(afanes.ui.strings.PAGE_STEP_TAGS.format(tags=", ".join(step.tags))))
        return details

    def _owner_detail(self, step: ProjectStep) -> ft.Control:
        """Render the step owners as individually clickable names."""
        spans: list[ft.TextSpan] = [ft.TextSpan(afanes.ui.strings.PAGE_STEP_OWNERS_LABEL)]
        for index, owner in enumerate(step.owners):
            if index:
                spans.append(ft.TextSpan(", "))
            spans.append(self._role_span(owner))
        return ft.Text(spans=spans, style=afanes.ui.theme.TEXT_ROLES["caption"])

    def _role_span(self, name: str) -> ft.TextSpan:
        """Build one link-styled span for a step owner name."""
        return ft.TextSpan(
            name,
            style=self._role_label_style(name),
            tooltip=self._role_tooltip(name),
            on_click=self._role_handler(name),
        )

    def _role_outcome(self, name: str) -> afanes.core.vault.snapshot.LinkOutcome:
        """Return how a written role name resolves in the current scan."""
        snapshot = self._state.session.snapshot
        if snapshot is None:
            return afanes.core.vault.snapshot.LinkOutcome.MISSING
        reference = NoteReference(scheme=ReferenceScheme.NOTE, name=name)
        return snapshot.link_target(reference).outcome

    def _role_handler(self, name: str) -> Callable[[], Awaitable[None]]:
        """Bind a role name to its navigation command."""

        async def handle() -> None:
            if self._on_follow_role is not None:
                await self._on_follow_role(name)

        return handle

    def _role_label_style(self, name: str) -> ft.TextStyle:
        """Return the link or broken-link style for one role name."""
        outcome = self._role_outcome(name)
        if outcome in (afanes.core.vault.snapshot.LinkOutcome.MISSING, afanes.core.vault.snapshot.LinkOutcome.BROKEN):
            return afanes.ui.theme.ROLE_BROKEN_TEXT_STYLE
        return afanes.ui.theme.ROLE_LINK_TEXT_STYLE

    def _role_tooltip(self, name: str) -> str | None:
        """Return the hover explanation for one role name."""
        outcome = self._role_outcome(name)
        if outcome in (afanes.core.vault.snapshot.LinkOutcome.MISSING, afanes.core.vault.snapshot.LinkOutcome.BROKEN):
            return afanes.ui.strings.ROLE_LINK_MISSING
        if outcome is afanes.core.vault.snapshot.LinkOutcome.AMBIGUOUS:
            return afanes.ui.strings.ROLE_LINK_AMBIGUOUS
        return None

    @staticmethod
    def _detail(text: str) -> ft.Control:
        """Render one metadata label on the step surface."""
        return ft.Text(
            text,
            style=afanes.ui.theme.TEXT_ROLES["caption"],
        )

    def _step_action(
        self,
        icon: ft.IconData,
        tooltip: str,
        handler: Callable[[], Awaitable[None]],
    ) -> ft.Control:
        """Build one always-visible, understated step action."""
        button = ft.IconButton(
            icon=icon,
            icon_color=afanes.ui.theme.STEP_MUTED_ACTION_COLOR,
            tooltip=tooltip,
            on_click=handler,
            style=ft.ButtonStyle(
                icon_color={
                    ft.ControlState.HOVERED: afanes.ui.theme.STEP_TEXT_COLOR,
                    ft.ControlState.FOCUSED: afanes.ui.theme.STEP_TEXT_COLOR,
                },
            ),
        )
        return ft.Semantics(label=tooltip, button=True, content=button)

    def _toggle_handler(self, step: ProjectStep) -> Callable[[ft.Event[ft.Checkbox]], Awaitable[None]]:
        """Bind a checkbox event to the step line rewrite."""

        async def handle(event: ft.Event[ft.Checkbox]) -> None:
            await self._state.pages.toggle_page_step(step.line_index, checked=bool(event.control.value))
            self.refresh()
            self._update()

        return handle

    def _plan_handler(self, step: ProjectStep) -> Callable[[], Awaitable[None]]:
        """Bind the calendar action to the date picker."""

        async def handle() -> None:
            await self._choose_plan(step)

        return handle

    def _clear_plan_handler(self, step: ProjectStep) -> Callable[[], Awaitable[None]]:
        """Bind the clear action to a plan removal."""

        async def handle() -> None:
            await self._write_edit(StepEdit(line_index=step.line_index, kind=StepEditKind.PLAN, plan=None))

        return handle

    async def _choose_plan(self, step: ProjectStep) -> None:
        """Open the date picker and write the chosen plan date."""
        if self._pick_date is None:
            return
        chosen = await self._pick_date(step.plan)
        if chosen is None:
            return
        await self._write_edit(StepEdit(line_index=step.line_index, kind=StepEditKind.PLAN, plan=chosen))

    def _owner_handler(self, step: ProjectStep) -> Callable[[], Awaitable[None]]:
        """Bind the person action to the inline owner panel."""

        async def handle() -> None:
            self._owner_panel = None if self._owner_panel == step.line_index else step.line_index
            self._owner_query = ""
            self._owner_field.value = ""
            self._error.visible = False
            self.refresh()
            self._update()

        return handle

    def _owner_panel_control(self, step: ProjectStep) -> ft.Control:
        """Render the owner chips, add field, and suggestions for one step."""
        chips: list[ft.Control] = [
            ft.Chip(
                label=owner,
                label_text_style=self._role_label_style(owner),
                tooltip=self._role_tooltip(owner),
                on_click=self._role_handler(owner),
                delete_icon_tooltip=afanes.ui.strings.PAGE_STEP_OWNER_REMOVE.format(owner=owner),
                on_delete=self._remove_owner_handler(step, owner),
            )
            for owner in step.owners
        ]
        self._refresh_owner_suggestions()
        return ft.Container(
            padding=ft.Padding.only(left=afanes.ui.theme.ITEM_GAP),
            content=ft.Column(
                controls=[
                    ft.Text(
                        afanes.ui.strings.PAGE_STEP_OWNER_TITLE,
                        style=afanes.ui.theme.TEXT_ROLES["heading"],
                        color=afanes.ui.theme.STEP_TEXT_COLOR,
                    ),
                    ft.Row(controls=chips, spacing=afanes.ui.theme.ITEM_GAP, wrap=True),
                    ft.Row(
                        controls=[
                            self._owner_field,
                            ft.IconButton(
                                icon=ft.Icons.PERSON_ADD_OUTLINED,
                                tooltip=afanes.ui.strings.PAGE_STEP_OWNER_ADD,
                                on_click=self._add_owner_from_field,
                                icon_color=afanes.ui.theme.STEP_TEXT_COLOR,
                            ),
                        ],
                        spacing=afanes.ui.theme.ITEM_GAP,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                    self._owner_suggestions,
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
        )

    def _change_owner_query(self, _event: object = None) -> None:
        """Refresh owner suggestions from the typed query."""
        self._owner_query = (self._owner_field.value or "").strip()
        self._refresh_owner_suggestions()
        self._update()

    def _refresh_owner_suggestions(self) -> None:
        """Fill the suggestion list from note names in the vault."""
        if self._owner_panel is None or not self._owner_query:
            self._owner_suggestions.controls = []
            self._owner_suggestions.visible = False
            return
        candidates = self._state.session.assignment_candidates(ReferenceScheme.NOTE, self._owner_query)
        self._owner_suggestions.controls = [
            ft.ListTile(
                title=note.title,
                subtitle=note.name if note.name != note.title else None,
                on_click=self._suggestion_handler(note.name),
            )
            for note in candidates
        ]
        self._owner_suggestions.visible = bool(self._owner_suggestions.controls)

    def _suggestion_handler(self, name: str) -> Callable[[], Awaitable[None]]:
        """Bind a suggestion tile to one owner name."""

        async def handle() -> None:
            await self._add_owner(name)

        return handle

    async def _add_owner_from_field(self, _event: object = None) -> None:
        """Add the name typed into the owner field."""
        name = (self._owner_field.value or "").strip()
        if not name:
            return
        await self._add_owner(name)

    async def _add_owner(self, name: str) -> None:
        """Append one owner and clear the field on success."""
        step = self._find_step()
        if step is None:
            return
        cleaned = name.strip()
        if not cleaned:
            return
        if cleaned in step.owners:
            self._show_error(afanes.ui.strings.PAGE_STEP_OWNER_DUPLICATE.format(owner=cleaned))
            return
        if await self._write_edit(
            StepEdit(
                line_index=step.line_index,
                kind=StepEditKind.OWNERS,
                owners=(*step.owners, cleaned),
            )
        ):
            self._owner_field.value = ""
            self._owner_query = ""
            self._owner_suggestions.controls = []
            self._owner_suggestions.visible = False
            self.refresh()
            self._update()

    def _remove_owner_handler(self, step: ProjectStep, owner: str) -> Callable[[], Awaitable[None]]:
        """Bind one chip deletion to the remaining owner list."""

        async def handle() -> None:
            await self._write_edit(
                StepEdit(
                    line_index=step.line_index,
                    kind=StepEditKind.OWNERS,
                    owners=tuple(name for name in step.owners if name != owner),
                )
            )

        return handle

    async def _write_edit(self, edit: StepEdit) -> bool:
        """Write one step metadata edit and refresh the body."""
        written = await self._state.pages.edit_page_step_metadata(edit)
        if written:
            self._error.visible = False
            self.refresh()
            self._update()
        else:
            notice = self._state.status.take_notice()
            message = afanes.ui.strings.PAGE_STEP_FAILED.format(detail="") if notice is None else notice.message
            self._show_error(message)
        return written

    def _find_step(self) -> ProjectStep | None:
        """Return the step whose owner panel is open."""
        if self._owner_panel is None:
            return None
        for block in self._state.pages.page_body_blocks:
            if isinstance(block, StepListBlock):
                for entry in block.entries:
                    if entry.step.line_index == self._owner_panel:
                        return entry.step
        return None

    def _show_error(self, message: str) -> None:
        """Show a local message without replacing the page state banner."""
        self._error.value = message
        self._error.visible = True
        self._update()

    def _close_owner_panel(self) -> None:
        """Close the inline owner panel and clear its transient state."""
        self._owner_panel = None
        self._owner_query = ""
        self._owner_field.value = ""
        self._owner_suggestions.controls = []
        self._owner_suggestions.visible = False

    async def _follow_link(self, event: ft.Event[ft.Markdown]) -> None:
        """Forward a tapped step or prose link."""
        destination = event.data
        if isinstance(destination, str):
            await self._on_follow_link(destination)
