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

import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
from afanes.core.editing import DraftMode
from afanes.core.project_body import ProseBlock, StepEntry, StepListBlock
from afanes.models.link import ReferenceScheme
from afanes.models.note import NoteType
from afanes.models.step import ProjectStep, StepEdit, StepEditKind
from afanes.ui.components.step_text import StepText

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
        """
        self._state = afanes.ui.state.app_state
        self._update = update
        self._on_follow_link = on_follow_link
        self._pick_date = pick_date
        self._owner_panel: int | None = None
        self._owner_query = ""
        self._error = ft.Text(
            "",
            size=12,
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            visible=False,
            selectable=True,
        )
        self._owner_field = ft.TextField(
            label=afanes.ui.strings.PAGE_STEP_OWNER_ADD,
            hint_text=afanes.ui.strings.PAGE_STEP_OWNER_HINT,
            dense=True,
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
        visible = page is not None and not editing and labels is not None and labels.note_type is NoteType.PROJECT
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
            border_radius=afanes.ui.theme.CARD_RADIUS,
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
                    expand=True,
                    on_tap_link=self._follow_link,
                ).build(),
                self._step_action(
                    ft.Icons.CALENDAR_MONTH,
                    afanes.ui.strings.PAGE_STEP_PLAN_ACTION,
                    self._plan_handler(step),
                ),
                *(
                    [
                        self._step_action(
                            ft.Icons.EVENT_BUSY,
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
                    on_tap_link=self._follow_link,
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
            details.append(self._detail(afanes.ui.strings.PAGE_STEP_OWNERS.format(owners=", ".join(step.owners))))
        if step.plan is not None:
            details.append(self._detail(afanes.ui.strings.PAGE_STEP_PLAN.format(date=step.plan.isoformat())))
        if step.actual is not None:
            details.append(self._detail(afanes.ui.strings.PAGE_STEP_ACTUAL.format(date=step.actual.isoformat())))
        if step.tags:
            details.append(self._detail(afanes.ui.strings.PAGE_STEP_TAGS.format(tags=", ".join(step.tags))))
        return details

    @staticmethod
    def _detail(text: str) -> ft.Control:
        """Render one metadata label on the step surface."""
        return ft.Text(
            text,
            size=12,
            color=afanes.ui.theme.STEP_TEXT_COLOR,
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
                        theme_style=ft.TextThemeStyle.LABEL_LARGE,
                        color=afanes.ui.theme.STEP_TEXT_COLOR,
                    ),
                    ft.Row(controls=chips, spacing=afanes.ui.theme.ITEM_GAP, wrap=True),
                    ft.Row(
                        controls=[
                            self._owner_field,
                            ft.IconButton(
                                icon=ft.Icons.PERSON_ADD,
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
                dense=True,
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
            message = self._state.status.message or afanes.ui.strings.PAGE_STEP_FAILED.format(detail="")
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
