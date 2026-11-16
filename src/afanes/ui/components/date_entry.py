# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared date entry: a field calendar action and a calendar dialog.

The dialog is presentational. It converts a precision-aware
:class:`afanes.models.note.NoteDate` into one pending selection and reports it
through a callback; the caller's existing validation and save command stay
authoritative. The component performs no vault access.
"""

import asyncio
import calendar
import dataclasses
import datetime
from collections.abc import Awaitable, Callable

import flet as ft

import afanes.core.log
import afanes.i18n.ui
import afanes.models.note
import afanes.ui.components.calendar
import afanes.ui.theme

MODES = (
    afanes.models.note.DatePrecision.DAY,
    afanes.models.note.DatePrecision.MONTH,
    afanes.models.note.DatePrecision.YEAR,
)
DAYS_PER_WEEK = afanes.ui.components.calendar.DAYS_PER_WEEK
ALL_PRECISIONS = frozenset(MODES)
DAY_PRECISION = frozenset({afanes.models.note.DatePrecision.DAY})

type PickDate = Callable[[datetime.date | None], Awaitable[datetime.date | None]]

type PickNoteDate = Callable[
    [afanes.models.note.NoteDate | None, frozenset[afanes.models.note.DatePrecision]],
    Awaitable[afanes.models.note.NoteDate | None],
]


@dataclasses.dataclass(frozen=True, slots=True)
class DatePickerActions:
    """Callbacks a date field supplies to its embedded calendar action.

    Attributes
    ----------
    pick : collections.abc.Callable[[], collections.abc.Awaitable[afanes.models.note.NoteDate | None]]
        Ask for a note date and return it, or ``None`` when cancelled.
    on_picked : collections.abc.Callable[[afanes.models.note.NoteDate], collections.abc.Awaitable[None]]
        Write the picked value through the field's existing command.
    """

    pick: Callable[[], Awaitable[afanes.models.note.NoteDate | None]]
    on_picked: Callable[[afanes.models.note.NoteDate], Awaitable[None]]


class DatePickerButton:
    """Calendar action embedded in a date field.

    Parameters
    ----------
    actions : DatePickerActions
        Field callbacks that open the picker and write the result.
    copy : afanes.i18n.ui.UiCopy | None
        Active interface catalog. English is used when omitted.
    """

    def __init__(
        self,
        actions: DatePickerActions,
        *,
        copy: afanes.i18n.ui.UiCopy | None = None,
    ) -> None:
        """Store the field callbacks and build the suffix button."""
        self._copy = afanes.i18n.ui.UiCopy.english() if copy is None else copy
        self._actions = actions
        self.button = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
            tooltip=self._copy.DATE_PICKER_OPEN,
            on_click=self._open,
            icon_color=afanes.ui.theme.MUTED_ACTION_COLOR,
            style=ft.ButtonStyle(
                icon_color={
                    ft.ControlState.HOVERED: afanes.ui.theme.TEXT_COLOR,
                    ft.ControlState.FOCUSED: afanes.ui.theme.TEXT_COLOR,
                },
            ),
            key="date-picker-open",
        )

    def attach(self, field: ft.TextField) -> ft.TextField:
        """Place the calendar action inside a text field.

        Parameters
        ----------
        field : flet.TextField
            Date field that receives the suffix action.

        Returns
        -------
        flet.TextField
            The same field with the calendar action attached.
        """
        field.suffix = self.button
        return field

    async def _open(self, _event: object = None) -> None:
        """Ask for a date and forward a confirmed value."""
        picked = await self._actions.pick()
        if picked is not None:
            await self._actions.on_picked(picked)


class DatePickerDialog:
    """Precision-aware calendar dialog for one pending note date.

    Parameters
    ----------
    current : afanes.models.note.NoteDate | None
        Current field value, or ``None`` when the field is empty or invalid.
    precisions : frozenset[afanes.models.note.DatePrecision]
        Precisions the field accepts. The mode switch appears only when more
        than one precision is allowed.
    on_confirm : collections.abc.Callable[[afanes.models.note.NoteDate], collections.abc.Awaitable[None]]
        Called with the confirmed value.
    on_cancel : collections.abc.Callable[[], collections.abc.Awaitable[None]]
        Called when the dialog is cancelled or dismissed.
    copy : afanes.i18n.ui.UiCopy | None
        Active interface catalog. English is used when omitted.
    today : datetime.date | None
        Date treated as today. The real date is used when omitted.
    update : collections.abc.Callable[[], None] | None
        Requests a repaint of the live dialog. ``None`` keeps the dialog
        detached for tests.
    first_date : datetime.date
        Earliest selectable date.
    last_date : datetime.date
        Latest selectable date.

    Raises
    ------
    ValueError
        If the precision set is empty or the date range is inverted.
    """

    def __init__(  # noqa: PLR0913
        self,
        current: afanes.models.note.NoteDate | None,
        precisions: frozenset[afanes.models.note.DatePrecision],
        on_confirm: Callable[[afanes.models.note.NoteDate], Awaitable[None]],
        on_cancel: Callable[[], Awaitable[None]],
        *,
        copy: afanes.i18n.ui.UiCopy | None = None,
        today: datetime.date | None = None,
        update: Callable[[], None] | None = None,
        first_date: datetime.date = datetime.date.min,
        last_date: datetime.date = datetime.date.max,
    ) -> None:
        """Build the dialog and its initial month grid."""
        if not precisions:
            message = "The date picker needs at least one precision"
            raise ValueError(message)
        if first_date > last_date:
            message = "The first date must not be after the last date"
            raise ValueError(message)
        self._copy = afanes.i18n.ui.UiCopy.english() if copy is None else copy
        self._precisions = frozenset(precisions)
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel
        self._update = update
        self._first_date = first_date
        self._last_date = last_date
        self._today = datetime.datetime.now(tz=datetime.UTC).astimezone().date() if today is None else today
        self._precision = self._initial_precision(current)
        self.anchor = self._initial_anchor(current)
        self._grid_focus_key: tuple[str, int] | None = None
        self._grid_kind: str | None = None
        self._visible_day_month: tuple[int, int] | None = None
        self._visible_month_year: int | None = None
        self._visible_year_start: int | None = None
        self._focus_task: asyncio.Task[None] | None = None
        self.day_grid: afanes.ui.components.calendar.CalendarGrid | None = None
        self.month_buttons: dict[int, ft.TextButton] = {}
        self.year_buttons: dict[int, ft.TextButton] = {}
        self._build_controls()
        self._refresh()

    @property
    def precision(self) -> afanes.models.note.DatePrecision:
        """Return the active output precision.

        Returns
        -------
        afanes.models.note.DatePrecision
            Day, month, or year.
        """
        return self._precision

    @property
    def result(self) -> afanes.models.note.NoteDate:
        """Return the value Select will write.

        Returns
        -------
        afanes.models.note.NoteDate
            Anchor date at the active precision.
        """
        if self._precision is afanes.models.note.DatePrecision.YEAR:
            return afanes.models.note.NoteDate.from_year(self.anchor.year)
        if self._precision is afanes.models.note.DatePrecision.MONTH:
            return afanes.models.note.NoteDate.from_text(f"{self.anchor.year:04d}-{self.anchor.month:02d}")
        return afanes.models.note.NoteDate.from_date(self.anchor)

    async def open(self) -> None:
        """Move focus to the selected cell of the initial grid."""
        self._update_view()
        await self._focus_selection()

    async def confirm(self) -> None:
        """Report the pending value."""
        self._cancel_focus_task()
        await self._on_confirm(self.result)

    async def cancel(self) -> None:
        """Report that the dialog was cancelled."""
        self._cancel_focus_task()
        await self._on_cancel()

    async def handle_key(self, event: ft.KeyboardEvent) -> bool:
        """Apply one keyboard event to the open dialog.

        Parameters
        ----------
        event : flet.KeyboardEvent
            Key-down event routed by the application shell.

        Returns
        -------
        bool
            ``True`` when the dialog handled the event.
        """
        key = self._key_name(event)
        if key == "ESCAPE":
            await self.cancel()
            return True
        if key == "TAB":
            return False
        if key == "ENTER":
            if self._grid_focus_key is not None:
                await self.confirm()
                return True
            return False
        if not self._move(key, shift=event.shift):
            return False
        self._refresh()
        self._update_view()
        await self._focus_selection()
        return True

    def select_day(self, day: int) -> None:
        """Select one day in the visible month.

        Parameters
        ----------
        day : int
            Calendar day from 1 to 31.
        """
        self.anchor = self._with_parts(self.anchor.year, self.anchor.month, day)
        self._grid_focus_key = ("day", day)
        if self.day_grid is not None:
            self.day_grid.mark_focus(day)
        self._refresh()
        self._update_view()
        self._schedule_focus()

    def select_month(self, month: int) -> None:
        """Select one month in the visible year.

        Parameters
        ----------
        month : int
            Calendar month from 1 to 12.
        """
        self.anchor = self._with_parts(self.anchor.year, month, self.anchor.day)
        self._grid_focus_key = ("month", month)
        self._refresh()
        self._update_view()
        self._schedule_focus()

    def select_year(self, year: int) -> None:
        """Select one year.

        Parameters
        ----------
        year : int
            Calendar year to select.
        """
        self.anchor = self._with_parts(year, self.anchor.month, self.anchor.day)
        self._grid_focus_key = ("year", year)
        self._refresh()
        self._update_view()
        self._schedule_focus()

    def set_precision(self, precision: afanes.models.note.DatePrecision) -> None:
        """Switch the output precision while keeping the anchor date.

        Parameters
        ----------
        precision : afanes.models.note.DatePrecision
            Requested precision. A precision the field forbids is ignored.
        """
        if precision not in self._precisions:
            return
        self._precision = precision
        self._grid_focus_key = None
        self._refresh()
        self._update_view()
        self._schedule_focus()

    def _build_controls(self) -> None:
        """Build the dialog shell and its stable actions."""
        self.caption = ft.Text("", style=afanes.ui.theme.TEXT_ROLES["caption-heading"], key="date-picker-caption")
        self.period_title = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["heading"],
            expand=True,
            text_align=ft.TextAlign.CENTER,
            key="date-picker-period",
        )
        self.previous_large_button = self._nav_button(
            ft.Icons.KEYBOARD_DOUBLE_ARROW_LEFT_OUTLINED,
            self._previous_large,
            "date-picker-previous-large",
            self._copy.DATE_PICKER_PREVIOUS_YEAR,
        )
        self.previous_button = self._nav_button(
            ft.Icons.CHEVRON_LEFT_OUTLINED,
            self._previous,
            "date-picker-previous",
            self._copy.LOG_PREVIOUS_MONTH,
        )
        self.next_button = self._nav_button(
            ft.Icons.CHEVRON_RIGHT_OUTLINED,
            self._next,
            "date-picker-next",
            self._copy.LOG_NEXT_MONTH,
        )
        self.next_large_button = self._nav_button(
            ft.Icons.KEYBOARD_DOUBLE_ARROW_RIGHT_OUTLINED,
            self._next_large,
            "date-picker-next-large",
            self._copy.DATE_PICKER_NEXT_YEAR,
        )
        self.nav_row = ft.Row(
            controls=[
                self.previous_large_button,
                self.previous_button,
                self.period_title,
                self.next_button,
                self.next_large_button,
            ],
            spacing=afanes.ui.theme.CALENDAR_HEADER_SPACING,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            key="date-picker-navigation",
        )
        self.mode_buttons = {
            precision: self._mode_button(precision) for precision in MODES if precision in self._precisions
        }
        self.mode_row = ft.Row(
            controls=list(self.mode_buttons.values()),
            spacing=afanes.ui.theme.NO_GAP,
            visible=len(self.mode_buttons) > 1,
            key="date-picker-modes",
        )
        self.grid_host = ft.Column(controls=[], spacing=afanes.ui.theme.NO_GAP, key="date-picker-grid-host")
        self.current_button = ft.TextButton(
            content="",
            on_click=self._select_current,
            on_focus=self._clear_grid_focus,
            key="date-picker-current",
        )
        self.cancel_button = ft.TextButton(
            content=self._copy.CANCEL_ACTION,
            on_click=self._cancel_event,
            on_focus=self._clear_grid_focus,
            key="date-picker-cancel",
        )
        self.select_button = ft.OutlinedButton(
            content=self._copy.DATE_PICKER_SELECT,
            on_click=self._confirm_event,
            on_focus=self._clear_grid_focus,
            key="date-picker-select",
        )
        self.body = ft.Column(
            controls=[self.caption, self.mode_row, self.nav_row, self.grid_host],
            spacing=afanes.ui.theme.ITEM_GAP,
            width=afanes.ui.theme.DATE_PICKER_WIDTH,
            key="date-picker-body",
        )
        self.dialog = ft.AlertDialog(
            title=ft.Text(self._copy.DATE_PICKER_TITLE, key="date-picker-title"),
            content=self.body,
            actions=[self.current_button, self.cancel_button, self.select_button],
            modal=False,
            scrollable=True,
            key="date-picker-dialog",
        )

    def _mode_button(self, precision: afanes.models.note.DatePrecision) -> ft.TextButton:
        """Build one mode-switch button."""
        return ft.TextButton(
            content=self._mode_label(precision),
            height=afanes.ui.theme.DATE_PICKER_PERIOD_HEIGHT,
            expand=True,
            style=self._mode_style(precision),
            on_click=self._precision_handler(precision),
            on_focus=self._clear_grid_focus,
            key=f"date-picker-mode-{precision.value}",
        )

    def _nav_button(
        self,
        icon: ft.IconData,
        handler: Callable[[object], None],
        key: str,
        tooltip: str,
    ) -> ft.IconButton:
        """Build one navigation chevron with its accessible name."""
        return ft.IconButton(
            icon=icon,
            tooltip=tooltip,
            on_click=handler,
            on_focus=self._clear_grid_focus,
            key=key,
        )

    def _refresh(self) -> None:
        """Render the caption, modes, navigation, and active grid."""
        self.caption.value = self._copy.DATE_PICKER_SELECTED.format(
            date=self._copy.locale_format.log_title(self.result)
        )
        self.current_button.content = self._current_label()
        for precision, button in self.mode_buttons.items():
            button.style = self._mode_style(precision)
        self._refresh_navigation()
        if self._precision is afanes.models.note.DatePrecision.DAY:
            self._build_day_grid()
        elif self._precision is afanes.models.note.DatePrecision.MONTH:
            self._build_month_grid()
        else:
            self._build_year_grid()

    def _refresh_navigation(self) -> None:
        """Update the period title and chevron meaning for the active mode."""
        if self._precision is afanes.models.note.DatePrecision.DAY:
            month_date = afanes.models.note.NoteDate.from_text(f"{self.anchor.year:04d}-{self.anchor.month:02d}")
            self.period_title.value = self._copy.locale_format.log_title(month_date)
            self.previous_large_button.visible = True
            self.next_large_button.visible = True
            self.previous_large_button.tooltip = self._copy.DATE_PICKER_PREVIOUS_YEAR
            self.next_large_button.tooltip = self._copy.DATE_PICKER_NEXT_YEAR
            self.previous_button.tooltip = self._copy.LOG_PREVIOUS_MONTH
            self.next_button.tooltip = self._copy.LOG_NEXT_MONTH
            return
        self.previous_large_button.visible = False
        self.next_large_button.visible = False
        if self._precision is afanes.models.note.DatePrecision.MONTH:
            self.period_title.value = f"{self.anchor.year:04d}"
            self.previous_button.tooltip = self._copy.DATE_PICKER_PREVIOUS_YEAR
            self.next_button.tooltip = self._copy.DATE_PICKER_NEXT_YEAR
            return
        start = self._decade_start()
        end = min(start + 9, datetime.date.max.year)
        self.period_title.value = f"{start:04d}-{end:04d}"
        self.previous_button.tooltip = self._copy.DATE_PICKER_PREVIOUS_DECADE
        self.next_button.tooltip = self._copy.DATE_PICKER_NEXT_DECADE

    def _build_day_grid(self) -> None:
        """Render the Monday-first day grid for the anchor month.

        Notes
        -----
        Selection-only updates reuse the existing day cells. Rebuilding them
        would replace the control that owns pointer focus, and Flet does not
        move keyboard focus to a button on a pointer tap.
        """
        if self.day_grid is None:
            self.day_grid = afanes.ui.components.calendar.CalendarGrid(
                self.select_day,
                copy=self._copy,
                selected=self.anchor,
                today=self._today,
                day_tooltip=self._day_tooltip,
                key_prefix="date-picker",
                on_day_focus=self._grid_focus,
                on_day_blur=self._grid_blur,
            )
        month_key = (self.anchor.year, self.anchor.month)
        if self._visible_day_month != month_key:
            self.day_grid.build(afanes.core.log.CalendarMonth.for_month(self.anchor.year, self.anchor.month))
            self._visible_day_month = month_key
        self.day_grid.set_marks(self.anchor, self._today)
        if self._grid_kind != "day":
            self.grid_host.controls = [self.day_grid.root]
            self._grid_kind = "day"
            self._grid_focus_key = None

    def _build_month_grid(self) -> None:
        """Render the twelve-month grid for the anchor year."""
        rebuilt = self._visible_month_year != self.anchor.year or not self.month_buttons
        if rebuilt:
            self.month_buttons = {
                month: self._period_button(
                    self._copy.locale_format.month_name(month),
                    f"date-picker-month-{month}",
                    self._month_handler(month),
                    self._period_focus_handler("month", month),
                    self._period_blur_handler("month", month),
                    selected=self.anchor.month == month,
                    today=self._today.year == self.anchor.year and self._today.month == month,
                )
                for month in range(1, 13)
            }
            self._visible_month_year = self.anchor.year
        self._apply_month_styles()
        switched = self._grid_kind != "month"
        if switched:
            self._grid_focus_key = None
        if switched or rebuilt:
            self.grid_host.controls = self._period_rows(
                list(self.month_buttons.values()),
                afanes.ui.theme.DATE_PICKER_MONTH_COLUMNS,
            )
            self._grid_kind = "month"

    def _build_year_grid(self) -> None:
        """Render the decade year grid around the anchor year."""
        start = self._decade_start()
        rebuilt = self._visible_year_start != start or not self.year_buttons
        if rebuilt:
            years = list(range(start, min(start + 10, datetime.date.max.year + 1)))
            self.year_buttons = {
                year: self._period_button(
                    f"{year:04d}",
                    f"date-picker-year-{year}",
                    self._year_handler(year),
                    self._period_focus_handler("year", year),
                    self._period_blur_handler("year", year),
                    selected=self.anchor.year == year,
                    today=self._today.year == year,
                )
                for year in years
            }
            self._visible_year_start = start
        self._apply_year_styles()
        switched = self._grid_kind != "year"
        if switched:
            self._grid_focus_key = None
        if switched or rebuilt:
            self.grid_host.controls = self._period_rows(
                list(self.year_buttons.values()),
                afanes.ui.theme.DATE_PICKER_YEAR_COLUMNS,
            )
            self._grid_kind = "year"

    def _period_button(  # noqa: PLR0913
        self,
        label: str,
        key: str,
        handler: Callable[[object], None],
        focus: Callable[[object], None],
        blur: Callable[[object], None],
        *,
        selected: bool,
        today: bool,
    ) -> ft.TextButton:
        """Build one month or year cell."""
        return ft.TextButton(
            content=label,
            height=afanes.ui.theme.DATE_PICKER_PERIOD_HEIGHT,
            expand=True,
            style=self._period_style(selected=selected, today=today, focused=False),
            on_click=handler,
            on_focus=focus,
            on_blur=blur,
            key=key,
        )

    def _period_rows(self, buttons: list[ft.TextButton], columns: int) -> list[ft.Control]:
        """Split period buttons into equal-width rows."""
        rows: list[ft.Control] = []
        for index in range(0, len(buttons), columns):
            controls: list[ft.Control] = list(buttons[index : index + columns])
            rows.append(
                ft.Row(
                    controls=controls,
                    spacing=afanes.ui.theme.CALENDAR_GRID_SPACING,
                )
            )
        return rows

    def _period_style(self, *, selected: bool, today: bool, focused: bool) -> ft.ButtonStyle:
        """Build the style for one month or year cell."""
        return ft.ButtonStyle(
            bgcolor=afanes.ui.theme.CALENDAR_SELECTED_COLOR if selected else None,
            side=afanes.ui.theme.CALENDAR_FOCUS_SIDE if focused else None,
            color=afanes.ui.theme.CALENDAR_TODAY_COLOR if today else None,
            text_style=ft.TextStyle(weight=ft.FontWeight.W_700) if today else None,
            shape=afanes.ui.theme.CALENDAR_CELL_SHAPE,
            padding=afanes.ui.theme.CALENDAR_CELL_PADDING,
            overlay_color=afanes.ui.theme.FOCUS_COLOR,
        )

    def _apply_month_styles(self) -> None:
        """Paint the selected, today, and focus marks on every month cell."""
        for month, button in self.month_buttons.items():
            button.style = self._period_style(
                selected=self.anchor.month == month,
                today=self._today.year == self.anchor.year and self._today.month == month,
                focused=self._grid_focus_key == ("month", month),
            )

    def _apply_year_styles(self) -> None:
        """Paint the selected, today, and focus marks on every year cell."""
        for year, button in self.year_buttons.items():
            button.style = self._period_style(
                selected=self.anchor.year == year,
                today=self._today.year == year,
                focused=self._grid_focus_key == ("year", year),
            )

    def _mode_style(self, precision: afanes.models.note.DatePrecision) -> ft.ButtonStyle:
        """Build the style for one mode-switch button."""
        selected = self._precision is precision
        return ft.ButtonStyle(
            bgcolor=afanes.ui.theme.CALENDAR_SELECTED_COLOR if selected else None,
            shape=afanes.ui.theme.CALENDAR_CELL_SHAPE,
            padding=afanes.ui.theme.CALENDAR_CELL_PADDING,
            overlay_color=afanes.ui.theme.FOCUS_COLOR,
        )

    def _current_label(self) -> str:
        """Return the current-period action for the active mode."""
        if self._precision is afanes.models.note.DatePrecision.DAY:
            return self._copy.DATE_PICKER_TODAY
        if self._precision is afanes.models.note.DatePrecision.MONTH:
            return self._copy.DATE_PICKER_THIS_MONTH
        return self._copy.DATE_PICKER_THIS_YEAR

    def _mode_label(self, precision: afanes.models.note.DatePrecision) -> str:
        """Return the localized mode label."""
        if precision is afanes.models.note.DatePrecision.DAY:
            return self._copy.DATE_MODE_DAY
        if precision is afanes.models.note.DatePrecision.MONTH:
            return self._copy.DATE_MODE_MONTH
        return self._copy.DATE_MODE_YEAR

    def _initial_precision(self, current: afanes.models.note.NoteDate | None) -> afanes.models.note.DatePrecision:
        """Return the precision the dialog opens in."""
        if current is not None and current.precision in self._precisions:
            return current.precision
        return next(precision for precision in MODES if precision in self._precisions)

    def _initial_anchor(self, current: afanes.models.note.NoteDate | None) -> datetime.date:
        """Return the concrete anchor date for the current value."""
        if current is None:
            value = self._today
        else:
            month = self._today.month if current.precision is afanes.models.note.DatePrecision.YEAR else current.month
            day = self._today.day if current.precision is not afanes.models.note.DatePrecision.DAY else current.day
            value = self._with_parts(current.year, month, day)
        return self._clamp_to_range(value)

    def _with_parts(self, year: int, month: int, day: int) -> datetime.date:
        """Build a bounded date, clamping the day to the month length."""
        year = min(max(year, datetime.date.min.year), datetime.date.max.year)
        month = min(max(month, 1), 12)
        day = min(max(day, 1), calendar.monthrange(year, month)[1])
        return self._clamp_to_range(datetime.date(year, month, day))

    def _clamp_to_range(self, value: datetime.date) -> datetime.date:
        """Clamp a date to the selectable range."""
        return min(max(value, self._first_date), self._last_date)

    def _move(self, key: str, *, shift: bool) -> bool:
        """Apply one key to the anchor date."""
        if self._precision is afanes.models.note.DatePrecision.DAY:
            return self._move_day(key, shift=shift)
        if self._precision is afanes.models.note.DatePrecision.MONTH:
            return self._move_month(key)
        return self._move_year(key)

    def _move_day(self, key: str, *, shift: bool) -> bool:
        """Move the anchor in day mode."""
        if key == "ARROWLEFT":
            self.anchor = self._shift_days(-1)
        elif key == "ARROWRIGHT":
            self.anchor = self._shift_days(1)
        elif key == "ARROWUP":
            self.anchor = self._shift_days(-DAYS_PER_WEEK)
        elif key == "ARROWDOWN":
            self.anchor = self._shift_days(DAYS_PER_WEEK)
        elif key == "HOME":
            self.anchor = self._shift_days(-self.anchor.weekday())
        elif key == "END":
            self.anchor = self._shift_days(DAYS_PER_WEEK - 1 - self.anchor.weekday())
        elif key == "PAGEUP":
            self.anchor = self._shift_years(-1) if shift else self._shift_months(-1)
        elif key == "PAGEDOWN":
            self.anchor = self._shift_years(1) if shift else self._shift_months(1)
        else:
            return False
        return True

    def _move_month(self, key: str) -> bool:
        """Move the anchor in month mode."""
        if key == "ARROWLEFT":
            self.anchor = self._shift_months(-1)
        elif key == "ARROWRIGHT":
            self.anchor = self._shift_months(1)
        elif key == "ARROWUP":
            self.anchor = self._shift_months(-afanes.ui.theme.DATE_PICKER_MONTH_COLUMNS)
        elif key == "ARROWDOWN":
            self.anchor = self._shift_months(afanes.ui.theme.DATE_PICKER_MONTH_COLUMNS)
        elif key == "HOME":
            self.anchor = self._with_parts(self.anchor.year, 1, self.anchor.day)
        elif key == "END":
            self.anchor = self._with_parts(self.anchor.year, 12, self.anchor.day)
        elif key == "PAGEUP":
            self.anchor = self._shift_years(-1)
        elif key == "PAGEDOWN":
            self.anchor = self._shift_years(1)
        else:
            return False
        return True

    def _move_year(self, key: str) -> bool:
        """Move the anchor in year mode."""
        start = self._decade_start()
        end = min(start + 9, datetime.date.max.year)
        if key == "ARROWLEFT":
            self.anchor = self._shift_years(-1)
        elif key == "ARROWRIGHT":
            self.anchor = self._shift_years(1)
        elif key == "ARROWUP":
            self.anchor = self._shift_years(-afanes.ui.theme.DATE_PICKER_YEAR_COLUMNS)
        elif key == "ARROWDOWN":
            self.anchor = self._shift_years(afanes.ui.theme.DATE_PICKER_YEAR_COLUMNS)
        elif key == "HOME":
            self.anchor = self._with_parts(start, self.anchor.month, self.anchor.day)
        elif key == "END":
            self.anchor = self._with_parts(end, self.anchor.month, self.anchor.day)
        elif key == "PAGEUP":
            self.anchor = self._shift_years(-10)
        elif key == "PAGEDOWN":
            self.anchor = self._shift_years(10)
        else:
            return False
        return True

    def _shift_days(self, delta: int) -> datetime.date:
        """Shift the anchor by calendar days within the range."""
        ordinal = self.anchor.toordinal() + delta
        ordinal = min(max(ordinal, self._first_date.toordinal()), self._last_date.toordinal())
        return datetime.date.fromordinal(ordinal)

    def _shift_months(self, delta: int) -> datetime.date:
        """Shift the anchor by calendar months, clamping the day."""
        index = self.anchor.year * 12 + (self.anchor.month - 1) + delta
        year, month_index = divmod(index, 12)
        if year < datetime.date.min.year:
            return self._first_date
        if year > datetime.date.max.year:
            return self._last_date
        return self._with_parts(year, month_index + 1, self.anchor.day)

    def _shift_years(self, delta: int) -> datetime.date:
        """Shift the anchor by calendar years, clamping the day."""
        return self._with_parts(self.anchor.year + delta, self.anchor.month, self.anchor.day)

    def _decade_start(self) -> int:
        """Return the first year of the anchor's decade page."""
        return max(datetime.date.min.year, (self.anchor.year // 10) * 10)

    def _day_tooltip(self, cell: afanes.core.log.CalendarDay) -> str:
        """Return the localized full date for one day cell."""
        value = afanes.models.note.NoteDate.from_text(f"{self.anchor.year:04d}-{self.anchor.month:02d}-{cell.day:02d}")
        return self._copy.locale_format.log_title(value)

    async def _focus_selection(self) -> None:
        """Paint the focus ring and move keyboard focus to the selected cell."""
        if self._precision is afanes.models.note.DatePrecision.DAY:
            if self.day_grid is None:
                return
            self.day_grid.mark_focus(self.anchor.day)
            if self._update is None:
                return
            await self.day_grid.focus_day(self.anchor.day)
            return
        self._grid_focus_key = self._selection_focus_key()
        if self._precision is afanes.models.note.DatePrecision.MONTH:
            self._apply_month_styles()
            button = self.month_buttons.get(self.anchor.month)
        else:
            self._apply_year_styles()
            button = self.year_buttons.get(self.anchor.year)
        if button is None or self._update is None:
            return
        try:
            await button.focus()
        except RuntimeError:
            # A detached dialog, such as a unit-test instance, has no client to focus.
            return

    def _update_view(self) -> None:
        """Request a repaint when the dialog is attached."""
        if self._update is not None:
            self._update()

    def _schedule_focus(self) -> None:
        """Request focus on the selected cell after a pointer selection.

        Notes
        -----
        Flet buttons do not take keyboard focus on a pointer tap. The selected
        cell is focused explicitly after the repaint, and a late blur from the
        previously focused cell is ignored by the focus-record check.
        """
        if self._update is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._cancel_focus_task()
        self._focus_task = loop.create_task(self._focus_selection())

    def _cancel_focus_task(self) -> None:
        """Cancel a pending focus request when the dialog closes."""
        task = self._focus_task
        self._focus_task = None
        if task is not None and not task.done():
            task.cancel()

    def _precision_handler(self, precision: afanes.models.note.DatePrecision) -> Callable[[object], None]:
        """Bind a mode button to its precision."""

        def handle(_event: object = None) -> None:
            self.set_precision(precision)

        return handle

    def _month_handler(self, month: int) -> Callable[[object], None]:
        """Bind a month cell to its month."""

        def handle(_event: object = None) -> None:
            self.select_month(month)

        return handle

    def _year_handler(self, year: int) -> Callable[[object], None]:
        """Bind a year cell to its year."""

        def handle(_event: object = None) -> None:
            self.select_year(year)

        return handle

    def _select_current(self, _event: object = None) -> None:
        """Select today, the current month, or the current year."""
        if self._precision is afanes.models.note.DatePrecision.DAY:
            self.anchor = self._with_parts(self._today.year, self._today.month, self._today.day)
        elif self._precision is afanes.models.note.DatePrecision.MONTH:
            self.anchor = self._with_parts(self._today.year, self._today.month, self.anchor.day)
        else:
            self.anchor = self._with_parts(self._today.year, self.anchor.month, self.anchor.day)
        self._grid_focus_key = self._selection_focus_key()
        self._refresh()
        self._update_view()
        self._schedule_focus()

    def _previous(self, _event: object = None) -> None:
        """Move the visible period back by one unit."""
        self._step_navigation(-1)

    def _next(self, _event: object = None) -> None:
        """Move the visible period forward by one unit."""
        self._step_navigation(1)

    def _previous_large(self, _event: object = None) -> None:
        """Move the visible period back by the larger unit."""
        self._step_large_navigation(-1)

    def _next_large(self, _event: object = None) -> None:
        """Move the visible period forward by the larger unit."""
        self._step_large_navigation(1)

    def _step_navigation(self, direction: int) -> None:
        """Apply the small chevron step for the active mode."""
        if self._precision is afanes.models.note.DatePrecision.DAY:
            self.anchor = self._shift_months(direction)
        elif self._precision is afanes.models.note.DatePrecision.MONTH:
            self.anchor = self._shift_years(direction)
        else:
            self.anchor = self._shift_years(10 * direction)
        self._grid_focus_key = self._selection_focus_key()
        self._refresh()
        self._update_view()
        self._schedule_focus()

    def _step_large_navigation(self, direction: int) -> None:
        """Apply the large chevron step in day mode."""
        self.anchor = self._shift_years(direction)
        self._grid_focus_key = self._selection_focus_key()
        self._refresh()
        self._update_view()
        self._schedule_focus()

    async def _cancel_event(self, _event: object = None) -> None:
        """Cancel from a button click."""
        await self.cancel()

    async def _confirm_event(self, _event: object = None) -> None:
        """Confirm from a button click."""
        await self.confirm()

    def _grid_focus(self, day: int) -> None:
        """Record that a day cell holds focus."""
        self._grid_focus_key = ("day", day)

    def _grid_blur(self, day: int) -> None:
        """Clear the day focus only while that cell still owns it."""
        if self._grid_focus_key == ("day", day):
            self._grid_focus_key = None

    def _period_focus_handler(self, kind: str, value: int) -> Callable[[object], None]:
        """Move the accent ring to the focused month or year cell."""

        def handle(_event: object = None) -> None:
            self._grid_focus_key = (kind, value)
            self._apply_period_styles()

        return handle

    def _period_blur_handler(self, kind: str, value: int) -> Callable[[object], None]:
        """Clear a month or year ring only while that cell still owns focus."""

        def handle(_event: object = None) -> None:
            if self._grid_focus_key != (kind, value):
                return
            self._grid_focus_key = None
            self._apply_period_styles()

        return handle

    def _apply_period_styles(self) -> None:
        """Refresh both period grids after a focus or selection change."""
        self._apply_month_styles()
        self._apply_year_styles()

    def _clear_grid_focus(self, _event: object = None) -> None:
        """Clear the grid-focus record when another control takes focus."""
        self._grid_focus_key = None
        self._apply_period_styles()

    def _selection_focus_key(self) -> tuple[str, int]:
        """Return the focus record for the selected cell of the active mode."""
        if self._precision is afanes.models.note.DatePrecision.DAY:
            return ("day", self.anchor.day)
        if self._precision is afanes.models.note.DatePrecision.MONTH:
            return ("month", self.anchor.month)
        return ("year", self.anchor.year)

    def _key_name(self, event: ft.KeyboardEvent) -> str:
        """Return a normalized key name."""
        return (event.key or "").upper().replace("_", "").replace(" ", "")
