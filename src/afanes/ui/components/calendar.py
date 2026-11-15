# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Month calendar shared by the Log sidebar and the date picker.

The component is presentational: it receives a
:class:`afanes.core.log.CalendarMonth` and forwards day and month navigation
intent. It performs no vault access and never derives dates from files.
"""

import datetime
from collections.abc import Callable

import flet as ft

import afanes.core.log
import afanes.i18n.ui
import afanes.models.note
import afanes.ui.theme

DAYS_PER_WEEK = 7


class CalendarGrid:
    """Monday-first month grid with selection and today marks.

    Parameters
    ----------
    on_select : Callable[[int], object]
        Called with a day number when a day cell is clicked.
    copy : afanes.i18n.ui.UiCopy | None
        Active interface catalog. English is used when omitted.
    selected : datetime.date | None
        Date to mark with the neutral selected-row fill.
    today : datetime.date | None
        Date to mark with the accent outline.
    day_tooltip : Callable[[afanes.core.log.CalendarDay], str] | None
        Tooltip builder for a day cell. The localized entry-count tooltip is
        used when omitted.
    key_prefix : str
        Prefix for the weekday row, grid, and root control keys.
    on_day_focus : Callable[[int], object] | None
        Called with a day number when a cell gains focus.
    on_day_blur : Callable[[int], object] | None
        Called with a day number when a cell loses focus.
    """

    def __init__(  # noqa: PLR0913
        self,
        on_select: Callable[[int], object],
        *,
        copy: afanes.i18n.ui.UiCopy | None = None,
        selected: datetime.date | None = None,
        today: datetime.date | None = None,
        day_tooltip: Callable[[afanes.core.log.CalendarDay], str] | None = None,
        key_prefix: str = "calendar",
        on_day_focus: Callable[[int], object] | None = None,
        on_day_blur: Callable[[int], object] | None = None,
    ) -> None:
        """Store the grid selection, labels, and callbacks."""
        self._copy = afanes.i18n.ui.UiCopy.english() if copy is None else copy
        self._on_select = on_select
        self._on_day_focus = on_day_focus
        self._on_day_blur = on_day_blur
        self._day_tooltip = day_tooltip
        self._selected = selected
        self._today = today
        self._month: afanes.core.log.CalendarMonth | None = None
        self.weekdays = ft.Row(
            controls=[
                ft.Text(
                    label,
                    style=afanes.ui.theme.TEXT_ROLES["caption"],
                    expand=True,
                    text_align=ft.TextAlign.CENTER,
                )
                for label in self._copy.locale_format.weekday_labels()
            ],
            spacing=afanes.ui.theme.CALENDAR_GRID_SPACING,
            key=f"{key_prefix}-weekdays",
        )
        self.grid = ft.Column(
            controls=[],
            spacing=afanes.ui.theme.CALENDAR_GRID_SPACING,
            key=f"{key_prefix}-grid",
        )
        self.day_buttons: dict[int, ft.TextButton] = {}
        self.root = ft.Column(
            controls=[self.weekdays, self.grid],
            spacing=afanes.ui.theme.CALENDAR_ROW_SPACING,
            key=f"{key_prefix}-grid-root",
        )
        self._key_prefix = key_prefix

    def build(self, calendar: afanes.core.log.CalendarMonth) -> ft.Control:
        """Render one month and return the root control.

        Parameters
        ----------
        calendar : afanes.core.log.CalendarMonth
            Month cells to render.

        Returns
        -------
        ft.Control
            Weekday row and day grid.
        """
        self._month = calendar
        self.day_buttons = {}
        cells: list[ft.Control] = [
            ft.Container(expand=True, height=afanes.ui.theme.CALENDAR_CELL_HEIGHT)
            for _ in range(calendar.first_weekday)
        ]
        for cell in calendar.days:
            button = self._day_button(cell)
            self.day_buttons[cell.day] = button
            cells.append(button)
        while len(cells) % DAYS_PER_WEEK:
            cells.append(ft.Container(expand=True, height=afanes.ui.theme.CALENDAR_CELL_HEIGHT))
        self.grid.controls = [
            ft.Row(controls=cells[index : index + DAYS_PER_WEEK], spacing=afanes.ui.theme.CALENDAR_GRID_SPACING)
            for index in range(0, len(cells), DAYS_PER_WEEK)
        ]
        return self.root

    def set_marks(self, selected: datetime.date | None, today: datetime.date | None) -> None:
        """Update the selected and today marks in place.

        Parameters
        ----------
        selected : datetime.date | None
            Date to mark with the neutral selected-row fill.
        today : datetime.date | None
            Date to mark with the accent outline.
        """
        self._selected = selected
        self._today = today
        for day, button in self.day_buttons.items():
            button.style = self._day_style(day, self._current_count(day))

    async def focus_day(self, day: int) -> None:
        """Move keyboard focus to one day cell.

        Parameters
        ----------
        day : int
            Calendar day to focus. An absent day is ignored.
        """
        button = self.day_buttons.get(day)
        if button is None:
            return
        try:
            await button.focus()
        except RuntimeError:
            # A detached grid, such as a unit-test instance, has no client to focus.
            return

    def _day_button(self, cell: afanes.core.log.CalendarDay) -> ft.TextButton:
        """Build one focusable day cell."""
        dot = ft.Container(
            width=afanes.ui.theme.CALENDAR_DAY_DOT_SIZE,
            height=afanes.ui.theme.CALENDAR_DAY_DOT_SIZE,
            border_radius=afanes.ui.theme.CALENDAR_DAY_DOT_RADIUS,
            bgcolor=afanes.ui.theme.LOG_ENTRY_DOT_COLOR,
            visible=cell.count > 0,
        )
        return ft.TextButton(
            content=ft.Column(
                controls=[ft.Text(str(cell.day), style=afanes.ui.theme.TEXT_ROLES["caption"]), dot],
                spacing=afanes.ui.theme.CALENDAR_CELL_SPACING,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            data={"day": cell.day, "count": cell.count},
            tooltip=self._tooltip(cell),
            style=self._day_style(cell.day, cell.count),
            height=afanes.ui.theme.CALENDAR_CELL_HEIGHT,
            expand=True,
            key=f"{self._key_prefix}-day-{cell.day}",
            on_click=self._select_handler(cell.day),
            on_focus=self._focus_handler(cell.day),
            on_blur=self._blur_handler(cell.day),
        )

    def _day_style(self, day: int, count: int) -> ft.ButtonStyle:
        """Build the style for one day cell."""
        selected = self._matches_day(self._selected, day)
        today = self._matches_day(self._today, day)
        bgcolor = afanes.ui.theme.LOG_ENTRY_TINT if count else None
        if selected:
            bgcolor = afanes.ui.theme.CALENDAR_SELECTED_COLOR
        return ft.ButtonStyle(
            bgcolor=bgcolor,
            side=afanes.ui.theme.CALENDAR_TODAY_SIDE if today else None,
            color=afanes.ui.theme.CALENDAR_TODAY_COLOR if today and not selected else None,
            shape=afanes.ui.theme.CALENDAR_CELL_SHAPE,
            padding=afanes.ui.theme.CALENDAR_CELL_PADDING,
            overlay_color=afanes.ui.theme.FOCUS_COLOR,
        )

    def _matches_day(self, value: datetime.date | None, day: int) -> bool:
        """Return whether a date falls on the rendered month and day."""
        if value is None or self._month is None:
            return False
        return value.year == self._month.year and value.month == self._month.month and value.day == day

    def _current_count(self, day: int) -> int:
        """Return the entry count for one rendered day."""
        if self._month is None:
            return 0
        return self._month.days[day - 1].count

    def _tooltip(self, cell: afanes.core.log.CalendarDay) -> str:
        """Return the tooltip for one day cell."""
        if self._day_tooltip is not None:
            return self._day_tooltip(cell)
        return self._copy.formatter.log_day_tooltip(cell.day, cell.count)

    def _select_handler(self, day: int) -> Callable[[object], None]:
        """Bind a day click to the selection callback."""

        def handle(_event: object = None) -> None:
            self._on_select(day)

        return handle

    def _focus_handler(self, day: int) -> Callable[[object], None]:
        """Bind a cell focus event to the focus callback."""

        def handle(_event: object = None) -> None:
            if self._on_day_focus is not None:
                self._on_day_focus(day)

        return handle

    def _blur_handler(self, day: int) -> Callable[[object], None]:
        """Bind a cell blur event to the blur callback."""

        def handle(_event: object = None) -> None:
            if self._on_day_blur is not None:
                self._on_day_blur(day)

        return handle


class LogCalendar:
    """Month grid with accented days and month navigation.

    Parameters
    ----------
    on_select : Callable[[int], object]
        Called with a day number when a day cell is clicked.
    on_previous : Callable[[], object]
        Called when the previous-month control is clicked.
    on_next : Callable[[], object]
        Called when the next-month control is clicked.
    copy : afanes.i18n.ui.UiCopy | None
        Active interface catalog. English is used when omitted.
    """

    def __init__(
        self,
        on_select: Callable[[int], object],
        on_previous: Callable[[], object],
        on_next: Callable[[], object],
        *,
        copy: afanes.i18n.ui.UiCopy | None = None,
    ) -> None:
        """Store the calendar actions."""
        self._copy = afanes.i18n.ui.UiCopy.english() if copy is None else copy
        self._on_previous = on_previous
        self._on_next = on_next
        self.title = ft.Text("", style=afanes.ui.theme.TEXT_ROLES["caption-heading"])
        self.month_dot = ft.Container(
            width=afanes.ui.theme.CALENDAR_HEADER_DOT_SIZE,
            height=afanes.ui.theme.CALENDAR_HEADER_DOT_SIZE,
            border_radius=afanes.ui.theme.CALENDAR_HEADER_DOT_RADIUS,
            bgcolor=afanes.ui.theme.LOG_ENTRY_DOT_COLOR,
            visible=False,
            tooltip=self._copy.LOG_MONTH_ENTRY_MARK,
        )
        self.year_dot = ft.Container(
            width=afanes.ui.theme.CALENDAR_HEADER_DOT_SIZE,
            height=afanes.ui.theme.CALENDAR_HEADER_DOT_SIZE,
            border_radius=afanes.ui.theme.CALENDAR_HEADER_DOT_RADIUS,
            bgcolor=afanes.ui.theme.LOG_ENTRY_DOT_COLOR,
            visible=False,
            tooltip=self._copy.LOG_YEAR_ENTRY_MARK,
        )
        self.prev_button = ft.IconButton(
            icon=ft.Icons.CHEVRON_LEFT_OUTLINED,
            tooltip=self._copy.LOG_PREVIOUS_MONTH,
            on_click=self._previous,
            key="log-calendar-previous",
        )
        self.next_button = ft.IconButton(
            icon=ft.Icons.CHEVRON_RIGHT_OUTLINED,
            tooltip=self._copy.LOG_NEXT_MONTH,
            on_click=self._next,
            key="log-calendar-next",
        )
        self._days = CalendarGrid(on_select, copy=self._copy, key_prefix="log-calendar")
        self.root = ft.Column(
            controls=[
                ft.Row(
                    controls=[self.prev_button, self.title, self.year_dot, self.month_dot, self.next_button],
                    spacing=afanes.ui.theme.CALENDAR_HEADER_SPACING,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self._days.root,
            ],
            spacing=afanes.ui.theme.CALENDAR_ROW_SPACING,
            key="log-calendar",
        )

    @property
    def weekdays(self) -> ft.Row:
        """Return the shared weekday row.

        Returns
        -------
        ft.Row
            Monday-first weekday labels.
        """
        return self._days.weekdays

    @property
    def grid(self) -> ft.Column:
        """Return the shared day grid.

        Returns
        -------
        ft.Column
            One row per calendar week.
        """
        return self._days.grid

    @property
    def day_buttons(self) -> dict[int, ft.TextButton]:
        """Return the day buttons by day number.

        Returns
        -------
        dict[int, ft.TextButton]
            Day cells of the rendered month.
        """
        return self._days.day_buttons

    def build(self, calendar: afanes.core.log.CalendarMonth) -> ft.Control:
        """Render one month and return the root control.

        Parameters
        ----------
        calendar : afanes.core.log.CalendarMonth
            Month marks from the Log timeline.

        Returns
        -------
        ft.Control
            Month header, weekday row, and day grid.
        """
        month_date = afanes.models.note.NoteDate.from_text(f"{calendar.year:04d}-{calendar.month:02d}")
        self.title.value = self._copy.locale_format.log_title(month_date)
        self.year_dot.visible = calendar.has_year_entry
        self.month_dot.visible = calendar.has_month_entry
        self._days.build(calendar)
        return self.root

    def _previous(self, _event: object = None) -> None:
        """Forward the previous-month action."""
        self._on_previous()

    def _next(self, _event: object = None) -> None:
        """Forward the next-month action."""
        self._on_next()
