# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Month calendar used by the Log sidebar.

The component is presentational: it receives a
:class:`afanes.core.log.CalendarMonth` and forwards day and month navigation
intent. It performs no vault access and never derives dates from files.
"""

import datetime
from collections.abc import Callable

import flet as ft

import afanes.core.log
import afanes.ui.strings
import afanes.ui.theme

WEEKDAY_LABELS = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
DAYS_PER_WEEK = 7
CELL_HEIGHT = 34


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
    """

    def __init__(
        self,
        on_select: Callable[[int], object],
        on_previous: Callable[[], object],
        on_next: Callable[[], object],
    ) -> None:
        """Store the calendar actions."""
        self._on_select = on_select
        self._on_previous = on_previous
        self._on_next = on_next
        self.title = ft.Text("", style=afanes.ui.theme.TEXT_ROLES["caption-heading"])
        self.month_dot = ft.Container(
            width=6,
            height=6,
            border_radius=3,
            bgcolor=afanes.ui.theme.LOG_ENTRY_DOT_COLOR,
            visible=False,
            tooltip=afanes.ui.strings.LOG_MONTH_ENTRY_MARK,
        )
        self.year_dot = ft.Container(
            width=6,
            height=6,
            border_radius=3,
            bgcolor=afanes.ui.theme.LOG_ENTRY_DOT_COLOR,
            visible=False,
            tooltip=afanes.ui.strings.LOG_YEAR_ENTRY_MARK,
        )
        self.prev_button = ft.IconButton(
            icon=ft.Icons.CHEVRON_LEFT_OUTLINED,
            tooltip=afanes.ui.strings.LOG_PREVIOUS_MONTH,
            on_click=self._previous,
            key="log-calendar-previous",
        )
        self.next_button = ft.IconButton(
            icon=ft.Icons.CHEVRON_RIGHT_OUTLINED,
            tooltip=afanes.ui.strings.LOG_NEXT_MONTH,
            on_click=self._next,
            key="log-calendar-next",
        )
        self.weekdays = ft.Row(
            controls=[
                ft.Text(label, style=afanes.ui.theme.TEXT_ROLES["caption"], expand=True, text_align=ft.TextAlign.CENTER)
                for label in WEEKDAY_LABELS
            ],
            spacing=0,
        )
        self.grid = ft.Column(controls=[], spacing=0)
        self.day_buttons: dict[int, ft.TextButton] = {}
        self.root = ft.Column(
            controls=[
                ft.Row(
                    controls=[self.prev_button, self.title, self.year_dot, self.month_dot, self.next_button],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.weekdays,
                self.grid,
            ],
            spacing=2,
            key="log-calendar",
        )

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
        month_name = datetime.date(calendar.year, calendar.month, 1).strftime("%B")
        self.title.value = f"{month_name} {calendar.year}"
        self.year_dot.visible = calendar.has_year_entry
        self.month_dot.visible = calendar.has_month_entry
        self.day_buttons = {}
        cells: list[ft.Control] = [ft.Container(expand=True, height=CELL_HEIGHT) for _ in range(calendar.first_weekday)]
        for cell in calendar.days:
            button = self._day_button(cell)
            self.day_buttons[cell.day] = button
            cells.append(button)
        while len(cells) % DAYS_PER_WEEK:
            cells.append(ft.Container(expand=True, height=CELL_HEIGHT))
        rows: list[ft.Control] = [
            ft.Row(controls=cells[index : index + DAYS_PER_WEEK], spacing=0)
            for index in range(0, len(cells), DAYS_PER_WEEK)
        ]
        self.grid.controls = rows
        return self.root

    def _day_button(self, cell: afanes.core.log.CalendarDay) -> ft.TextButton:
        """Build one focusable day cell."""
        dot = ft.Container(
            width=4,
            height=4,
            border_radius=2,
            bgcolor=afanes.ui.theme.LOG_ENTRY_DOT_COLOR,
            visible=cell.count > 0,
        )
        return ft.TextButton(
            content=ft.Column(
                controls=[ft.Text(str(cell.day), style=afanes.ui.theme.TEXT_ROLES["caption"]), dot],
                spacing=1,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            data={"day": cell.day, "count": cell.count},
            tooltip=afanes.ui.strings.CopyFormatter.log_day_tooltip(cell.day, cell.count),
            style=ft.ButtonStyle(
                bgcolor=afanes.ui.theme.LOG_ENTRY_TINT if cell.count else None,
                padding=0,
            ),
            height=CELL_HEIGHT,
            expand=True,
            on_click=self._select_handler(cell.day),
        )

    def _select_handler(self, day: int) -> Callable[[object], None]:
        """Bind a day click to the selection callback."""

        def handle(_event: object = None) -> None:
            self._on_select(day)

        return handle

    def _previous(self, _event: object = None) -> None:
        """Forward the previous-month action."""
        self._on_previous()

    def _next(self, _event: object = None) -> None:
        """Forward the next-month action."""
        self._on_next()
