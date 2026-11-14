# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only timeline queries over a scanned vault.

The module derives year, month, and day buckets, the Undated group, and calendar
marks from a :class:`afanes.core.vault.snapshot.VaultSnapshot`. It performs no
file I/O, never writes, and never builds a persistent index.
"""

import calendar
import dataclasses
from collections.abc import Iterable
from enum import StrEnum
from typing import Self

import afanes.core.names
import afanes.core.search
from afanes.core.vault.snapshot import VaultNote, VaultSnapshot
from afanes.models.note import DatePrecision, NoteDate, NoteType


class LogMode(StrEnum):
    """Which notes the Log workspace shows.

    Attributes
    ----------
    ENTRIES : str
        Only ``type: log`` notes.
    EVERYTHING : str
        Every parsed note, including log entries, as a date lens.
    """

    ENTRIES = "entries"
    EVERYTHING = "everything"

    @property
    def stored_value(self) -> str:
        """Return the value persisted in UI preferences.

        Returns
        -------
        str
            Stable lowercase mode value.
        """
        return self.value


@dataclasses.dataclass(frozen=True, slots=True)
class LogTitle:
    """Default display title for a log entry date.

    Attributes
    ----------
    text : str
        Long date title: a month name, day, and year for a day, a month name
        and year for a month, or a four-digit year for a year.
    """

    text: str

    @classmethod
    def for_date(cls, date: NoteDate) -> Self:
        """Build the default title for one note date.

        Parameters
        ----------
        date : NoteDate
            Entry date at year, month, or day precision.

        Returns
        -------
        LogTitle
            Long date title using the standard library English month names.
            A single-digit day is written without a leading zero.

        Notes
        -----
        The title stays independent from the filename, which always uses the
        ISO date text.
        """
        if date.precision is DatePrecision.YEAR:
            return cls(f"{date.year:04d}")
        month_name = calendar.month_name[date.month]
        if date.precision is DatePrecision.MONTH:
            return cls(f"{month_name} {date.year:04d}")
        return cls(f"{month_name} {date.day}, {date.year:04d}")


@dataclasses.dataclass(frozen=True, slots=True)
class LogDay:
    """Log entries that share one calendar day.

    Attributes
    ----------
    day : int
        Calendar day.
    entries : tuple[VaultNote, ...]
        Notes dated to this exact day, ordered by display title.
    """

    day: int
    entries: tuple[VaultNote, ...]

    @property
    def count(self) -> int:
        """Return the number of entries on this day.

        Returns
        -------
        int
            Length of :attr:`entries`.
        """
        return len(self.entries)


@dataclasses.dataclass(frozen=True, slots=True)
class LogMonth:
    """One calendar month in the Log tree.

    Attributes
    ----------
    year : int
        Calendar year.
    month : int
        Calendar month.
    entries : tuple[VaultNote, ...]
        Notes dated to this exact month.
    days : tuple[LogDay, ...]
        Day buckets with at least one entry, newest first.
    """

    year: int
    month: int
    entries: tuple[VaultNote, ...]
    days: tuple[LogDay, ...]

    @property
    def count(self) -> int:
        """Return the number of notes at or below this month.

        Returns
        -------
        int
            Month entries plus every day entry.
        """
        return len(self.entries) + sum(day.count for day in self.days)


@dataclasses.dataclass(frozen=True, slots=True)
class LogYear:
    """One calendar year in the Log tree.

    Attributes
    ----------
    year : int
        Calendar year.
    entries : tuple[VaultNote, ...]
        Notes dated to this exact year.
    months : tuple[LogMonth, ...]
        Month buckets with at least one entry, newest first.
    """

    year: int
    entries: tuple[VaultNote, ...]
    months: tuple[LogMonth, ...]

    @property
    def count(self) -> int:
        """Return the number of notes at or below this year.

        Returns
        -------
        int
            Year entries plus every month entry.
        """
        return len(self.entries) + sum(month.count for month in self.months)


@dataclasses.dataclass(frozen=True, slots=True)
class CalendarDay:
    """One day cell in the Log calendar.

    Attributes
    ----------
    day : int
        Calendar day.
    count : int
        Number of day-precision notes on that day.
    """

    day: int
    count: int


@dataclasses.dataclass(frozen=True, slots=True)
class CalendarMonth:
    """Calendar marks for one month.

    Attributes
    ----------
    year : int
        Calendar year.
    month : int
        Calendar month.
    first_weekday : int
        ISO weekday of the first day, where Monday is ``0``.
    days_in_month : int
        Number of days in the month.
    days : tuple[CalendarDay, ...]
        One cell per day, in calendar order. A zero count means no entry.
    month_count : int
        Number of notes dated to the whole month.
    year_count : int
        Number of notes dated to the whole year.
    """

    year: int
    month: int
    first_weekday: int
    days_in_month: int
    days: tuple[CalendarDay, ...]
    month_count: int
    year_count: int

    @property
    def has_month_entry(self) -> bool:
        """Return whether the month itself has an entry.

        Returns
        -------
        bool
            ``True`` when :attr:`month_count` is positive.
        """
        return self.month_count > 0

    @property
    def has_year_entry(self) -> bool:
        """Return whether the year itself has an entry.

        Returns
        -------
        bool
            ``True`` when :attr:`year_count` is positive.
        """
        return self.year_count > 0


class LogTimeline:
    """Year, month, day, and calendar views over one snapshot.

    Parameters
    ----------
    snapshot : VaultSnapshot
        Read-only scan result.
    mode : LogMode
        Whether to show only log entries or every parsed note.
    query : str
        Optional search query. Matching follows the browser rules and filters
        both the tree and the calendar.
    """

    def __init__(
        self,
        snapshot: VaultSnapshot,
        mode: LogMode = LogMode.ENTRIES,
        query: str = "",
    ) -> None:
        """Store the snapshot, mode, and query this timeline uses.

        Parameters
        ----------
        snapshot : VaultSnapshot
            Read-only scan result.
        mode : LogMode
            Entries or Everything.
        query : str
            Search query. An empty query keeps every note.
        """
        self._snapshot = snapshot
        self._mode = mode
        self._query = query

    @property
    def mode(self) -> LogMode:
        """Return the active mode.

        Returns
        -------
        LogMode
            Entries or Everything.
        """
        return self._mode

    @property
    def query(self) -> str:
        """Return the active search query.

        Returns
        -------
        str
            Query exactly as typed.
        """
        return self._query

    def with_query(self, query: str) -> "LogTimeline":
        """Return a timeline filtered by a search query.

        Parameters
        ----------
        query : str
            New query. An empty query keeps every note.

        Returns
        -------
        LogTimeline
            Timeline sharing the snapshot and mode.
        """
        return LogTimeline(self._snapshot, self._mode, query)

    def with_mode(self, mode: LogMode) -> "LogTimeline":
        """Return a timeline with a different mode.

        Parameters
        ----------
        mode : LogMode
            Entries or Everything.

        Returns
        -------
        LogTimeline
            Timeline sharing the snapshot and query.
        """
        return LogTimeline(self._snapshot, mode, self._query)

    def entries(self) -> tuple[VaultNote, ...]:
        """Return every note included in the current mode and query.

        Returns
        -------
        tuple[VaultNote, ...]
            Matching notes, ordered by date and title.
        """
        notes = [
            note for note in self._snapshot.notes if self._mode is LogMode.EVERYTHING or note.note_type is NoteType.LOG
        ]
        if self._query.strip():
            notes = list(afanes.core.search.Browser.filter_notes(notes, self._query))
        return tuple(notes)

    def years(self) -> tuple[LogYear, ...]:
        """Group dated notes into year buckets.

        Returns
        -------
        tuple[LogYear, ...]
            Years newest first. Each year holds its own entries and its months.
        """
        years: dict[int, list[VaultNote]] = {}
        for note in self.entries():
            if note.date is None:
                continue
            years.setdefault(note.date.year, []).append(note)
        return tuple(self._year(year, years[year]) for year in sorted(years, reverse=True))

    def undated(self) -> tuple[VaultNote, ...]:
        """Return included notes without a date.

        Returns
        -------
        tuple[VaultNote, ...]
            Undated notes ordered by display title.
        """
        return self._sorted(note for note in self.entries() if note.date is None)

    def calendar(self, year: int, month: int) -> CalendarMonth:
        """Build calendar marks for one month.

        Parameters
        ----------
        year : int
            Calendar year.
        month : int
            Calendar month, 1-12.

        Returns
        -------
        CalendarMonth
            Day cells plus month and year entry counts.

        Raises
        ------
        ValueError
            If the month is outside 1-12 or the date is invalid.
        """
        first_weekday, days_in_month = calendar.monthrange(year, month)
        counts: dict[int, int] = {}
        month_count = 0
        year_count = 0
        for note in self.entries():
            date = note.date
            if date is None or date.year != year:
                continue
            if date.precision is DatePrecision.YEAR:
                year_count += 1
                continue
            if date.month != month:
                continue
            if date.precision is DatePrecision.MONTH:
                month_count += 1
                continue
            counts[date.day] = counts.get(date.day, 0) + 1
        days = tuple(CalendarDay(day=day, count=counts.get(day, 0)) for day in range(1, days_in_month + 1))
        return CalendarMonth(
            year=year,
            month=month,
            first_weekday=first_weekday,
            days_in_month=days_in_month,
            days=days,
            month_count=month_count,
            year_count=year_count,
        )

    def _year(self, year: int, notes: list[VaultNote]) -> LogYear:
        """Build one year bucket from notes sharing that year."""
        year_entries: list[VaultNote] = []
        months: dict[int, list[VaultNote]] = {}
        for note in notes:
            date = note.date
            if date is None:
                continue
            if date.precision is DatePrecision.YEAR:
                year_entries.append(note)
            else:
                months.setdefault(date.month, []).append(note)
        return LogYear(
            year=year,
            entries=self._sorted(year_entries),
            months=tuple(self._month(year, month, months[month]) for month in sorted(months, reverse=True)),
        )

    def _month(self, year: int, month: int, notes: list[VaultNote]) -> LogMonth:
        """Build one month bucket from notes sharing that month."""
        month_entries: list[VaultNote] = []
        days: dict[int, list[VaultNote]] = {}
        for note in notes:
            date = note.date
            if date is None:
                continue
            if date.precision is DatePrecision.MONTH:
                month_entries.append(note)
            else:
                days.setdefault(date.day, []).append(note)
        return LogMonth(
            year=year,
            month=month,
            entries=self._sorted(month_entries),
            days=tuple(LogDay(day=day, entries=self._sorted(days[day])) for day in sorted(days, reverse=True)),
        )

    @staticmethod
    def _sorted(notes: Iterable[VaultNote]) -> tuple[VaultNote, ...]:
        """Sort notes by display title, identity, and path."""
        return tuple(sorted(notes, key=lambda note: note.alphabetical_order))
