# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Collapsed year/month/day tree for the Log sidebar.

The component is presentational: it receives a
:class:`afanes.core.log.LogTimeline` and forwards selection and creation intent.
It performs no vault access and never derives dates from files.
"""

import datetime
from collections.abc import Callable
from pathlib import Path

import flet as ft

import afanes.core.log
import afanes.ui.strings
import afanes.ui.theme
from afanes.core.vault.snapshot import VaultNote


class LogTree:
    """Year, month, and day rows for the Log sidebar.

    Parameters
    ----------
    on_select : Callable[[Path], object]
        Called with a note path when an entry row is clicked.
    on_create_month : Callable[[int, int], object]
        Called with a year and month when the empty-month plus is clicked.
    on_create_year : Callable[[int], object]
        Called with a year when the empty-year plus is clicked.
    selected_day : tuple[int, int, int] | None
        Year, month, and day to expand initially, or ``None`` to keep every
        year collapsed.
    """

    def __init__(
        self,
        on_select: Callable[[Path], object],
        on_create_month: Callable[[int, int], object],
        on_create_year: Callable[[int], object],
        selected_day: tuple[int, int, int] | None = None,
    ) -> None:
        """Store the tree actions and initial expansion."""
        self._on_select = on_select
        self._on_create_month = on_create_month
        self._on_create_year = on_create_year
        self._selected_day = selected_day
        self.year_tiles: dict[int, ft.ExpansionTile] = {}
        self.month_tiles: dict[tuple[int, int], ft.ExpansionTile] = {}
        self.day_tiles: dict[tuple[int, int, int], ft.ExpansionTile] = {}
        self.note_rows: dict[Path, ft.ListTile] = {}
        self.plus_buttons: dict[str, ft.IconButton] = {}
        self.open_buttons: dict[str, ft.IconButton] = {}
        self.undated_tile: ft.ExpansionTile | None = None
        self.root = ft.Column(controls=[], spacing=0, key="log-tree")

    def build(self, timeline: afanes.core.log.LogTimeline) -> ft.Control:
        """Render the tree for one timeline and return the root control.

        Parameters
        ----------
        timeline : afanes.core.log.LogTimeline
            Year, month, day, and Undated buckets from the Log query service.

        Returns
        -------
        ft.Control
            Collapsed year rows, an Undated row when needed, or an empty state.
        """
        self.year_tiles = {}
        self.month_tiles = {}
        self.day_tiles = {}
        self.note_rows = {}
        self.plus_buttons = {}
        self.open_buttons = {}
        controls: list[ft.Control] = [self._year_tile(year) for year in timeline.years()]
        undated = timeline.undated()
        if undated:
            self.undated_tile = self._undated_tile(undated)
            controls.append(self.undated_tile)
        if not controls:
            controls.append(
                ft.Container(
                    padding=afanes.ui.theme.ITEM_GAP,
                    content=ft.Text(
                        afanes.ui.strings.LOG_EMPTY,
                        color=afanes.ui.theme.MUTED_TEXT_COLOR,
                        selectable=True,
                    ),
                )
            )
        self.root.controls = controls
        return self.root

    def _year_tile(self, year: afanes.core.log.LogYear) -> ft.ExpansionTile:
        """Build one year row and its entries and months."""
        controls: list[ft.Control] = [self._note_row(note) for note in year.entries]
        controls.extend(self._month_tile(month) for month in year.months)
        control = self._control_for(
            key=f"year:{year.year}",
            year=year.year,
            month=None,
            has_entry=bool(year.entries),
            entry=year.entries[0] if year.entries else None,
            tooltip_create=afanes.ui.strings.LOG_NEW_YEAR_ENTRY.format(year=year.year),
            tooltip_open=afanes.ui.strings.LOG_OPEN_YEAR_ENTRY.format(year=year.year),
        )
        tile = ft.ExpansionTile(
            title=ft.Row(
                controls=[
                    ft.Text(str(year.year)),
                    ft.Text(
                        afanes.ui.strings.log_entry_count(year.count),
                        size=11,
                        color=afanes.ui.theme.MUTED_TEXT_COLOR,
                    ),
                    control,
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            controls=controls,
            expanded=self._selected_day is not None and self._selected_day[0] == year.year,
            maintain_state=False,
            key=f"log-year-{year.year}",
        )
        self.year_tiles[year.year] = tile
        return tile

    def _month_tile(self, month: afanes.core.log.LogMonth) -> ft.ExpansionTile:
        """Build one month row and its entries and days."""
        controls: list[ft.Control] = [self._note_row(note) for note in month.entries]
        controls.extend(self._day_tile(day) for day in month.days)
        name = datetime.date(month.year, month.month, 1).strftime("%B")
        period = f"{name} {month.year}"
        control = self._control_for(
            key=f"month:{month.year}-{month.month:02d}",
            year=month.year,
            month=month.month,
            has_entry=bool(month.entries),
            entry=month.entries[0] if month.entries else None,
            tooltip_create=afanes.ui.strings.LOG_NEW_MONTH_ENTRY.format(period=period),
            tooltip_open=afanes.ui.strings.LOG_OPEN_MONTH_ENTRY.format(period=period),
        )
        tile = ft.ExpansionTile(
            title=ft.Row(
                controls=[
                    ft.Text(name),
                    ft.Text(
                        afanes.ui.strings.log_entry_count(month.count),
                        size=11,
                        color=afanes.ui.theme.MUTED_TEXT_COLOR,
                    ),
                    control,
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            controls=controls,
            expanded=self._selected_day is not None
            and self._selected_day[0] == month.year
            and self._selected_day[1] == month.month,
            maintain_state=False,
            key=f"log-month-{month.year}-{month.month:02d}",
        )
        self.month_tiles[(month.year, month.month)] = tile
        return tile

    def _day_tile(self, day: afanes.core.log.LogDay) -> ft.ExpansionTile:
        """Build one day row and its entries."""
        date = day.entries[0].date if day.entries else None
        expanded = (
            self._selected_day is not None
            and date is not None
            and self._selected_day[0] == date.year
            and self._selected_day[1] == date.month
            and self._selected_day[2] == day.day
        )
        tile = ft.ExpansionTile(
            title=ft.Row(
                controls=[
                    ft.Text(str(day.day)),
                    ft.Text(
                        afanes.ui.strings.log_entry_count(day.count),
                        size=11,
                        color=afanes.ui.theme.MUTED_TEXT_COLOR,
                    ),
                ],
                spacing=4,
            ),
            controls=[self._note_row(note) for note in day.entries],
            expanded=expanded,
            maintain_state=False,
            key=f"log-day-{date.year}-{date.month:02d}-{day.day}" if date is not None else f"log-day-{day.day}",
        )
        if date is not None:
            self.day_tiles[(date.year, date.month, day.day)] = tile
        return tile

    def _note_row(self, note: VaultNote) -> ft.ListTile:
        """Build one clickable entry row."""
        row = ft.ListTile(
            title=note.title,
            subtitle=note.relative_path.as_posix(),
            leading=ft.Icons.DESCRIPTION,
            dense=True,
            on_click=self._select_handler(note.path),
            key=f"log-entry-{note.relative_path.as_posix()}",
        )
        self.note_rows[note.path] = row
        return row

    def _undated_tile(self, notes: tuple[VaultNote, ...]) -> ft.ExpansionTile:
        """Build the Undated row."""
        return ft.ExpansionTile(
            title=ft.Row(
                controls=[
                    ft.Text(afanes.ui.strings.LOG_UNDATED),
                    ft.Text(
                        afanes.ui.strings.log_entry_count(len(notes)),
                        size=11,
                        color=afanes.ui.theme.MUTED_TEXT_COLOR,
                    ),
                ]
            ),
            controls=[self._note_row(note) for note in notes],
            maintain_state=False,
            key="log-undated",
        )

    def _control_for(
        self,
        *,
        key: str,
        year: int,
        month: int | None,
        has_entry: bool,
        entry: VaultNote | None,
        tooltip_create: str,
        tooltip_open: str,
    ) -> ft.IconButton:
        """Build the plus or open control for a year or month row."""
        if has_entry and entry is not None:
            button = ft.IconButton(
                icon=ft.Icons.EVENT_AVAILABLE,
                tooltip=tooltip_open,
                on_click=self._open_handler(entry.path),
                icon_size=16,
                key=f"{key}:open",
            )
            self.open_buttons[key] = button
            return button
        button = ft.IconButton(
            icon=ft.Icons.ADD,
            tooltip=tooltip_create,
            on_click=self._create_handler(year, month),
            icon_size=16,
            key=f"{key}:create",
        )
        self.plus_buttons[key] = button
        return button

    def _select_handler(self, path: Path) -> Callable[[object], None]:
        """Bind a note selection callback."""

        def handle(_event: object = None) -> None:
            self._on_select(path)

        return handle

    def _open_handler(self, path: Path) -> Callable[[object], None]:
        """Bind an open-entry callback."""

        def handle(_event: object = None) -> None:
            self._on_select(path)

        return handle

    def _create_handler(self, year: int, month: int | None) -> Callable[[object], None]:
        """Bind a month or year creation callback."""

        def handle(_event: object = None) -> None:
            if month is None:
                self._on_create_year(year)
            else:
                self._on_create_month(year, month)

        return handle
