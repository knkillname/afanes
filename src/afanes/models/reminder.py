# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reminder schedules stored in note frontmatter.

The module owns the immutable reminder value objects: one recurrence or one
one-shot, an optional IANA time zone, and the last handled instant. It also
owns the occurrence calculation. The module imports only the standard library
and performs no file I/O and no clock reads; callers pass the reference
instant and the system zone.
"""

import dataclasses
import datetime
import zoneinfo
from collections.abc import Iterator
from enum import StrEnum
from typing import Self

MAX_MONTH_SEARCH = 24
MAX_WEEKDAY_SEARCH_DAYS = 7
MAX_DAILY_SEARCH_DAYS = 2

MAX_HOUR = 23
MAX_MINUTE = 59
MIN_DAY = 1
MAX_DAY = 31
MIN_NTH = 1
MAX_NTH = 5
MONTHS_PER_YEAR = 12
LAST_MONTH = 12
TIME_TEXT_LENGTH = 5
TIME_SEPARATOR_INDEX = 2
MINUTE_TEXT_START = 3


class Weekday(StrEnum):
    """Monday-first weekday vocabulary.

    Attributes
    ----------
    MONDAY : str
        Canonical short name for Monday.
    TUESDAY : str
        Canonical short name for Tuesday.
    WEDNESDAY : str
        Canonical short name for Wednesday.
    THURSDAY : str
        Canonical short name for Thursday.
    FRIDAY : str
        Canonical short name for Friday.
    SATURDAY : str
        Canonical short name for Saturday.
    SUNDAY : str
        Canonical short name for Sunday.
    """

    MONDAY = "mon"
    TUESDAY = "tue"
    WEDNESDAY = "wed"
    THURSDAY = "thu"
    FRIDAY = "fri"
    SATURDAY = "sat"
    SUNDAY = "sun"

    @classmethod
    def from_text(cls, value: str) -> Self:
        """Parse a canonical short weekday name.

        Parameters
        ----------
        value : str
            Written weekday name.

        Returns
        -------
        Weekday
            Matching weekday.

        Raises
        ------
        ValueError
            If the text is not one of the canonical short names.
        """
        try:
            return cls(value.strip().lower())
        except ValueError as exc:
            message = f"Unknown weekday: {value!r}"
            raise ValueError(message) from exc

    @classmethod
    def from_date(cls, day: datetime.date) -> Self:
        """Return the weekday of a calendar date.

        Parameters
        ----------
        day : datetime.date
            Calendar date to inspect.

        Returns
        -------
        Weekday
            Monday-first weekday for the date.
        """
        return tuple(cls)[day.weekday()]

    @property
    def position(self) -> int:
        """Return the zero-based Monday-first position.

        Returns
        -------
        int
            Zero for Monday through six for Sunday.
        """
        return tuple(type(self)).index(self)


class ReminderKind(StrEnum):
    """Kinds of recurrence a reminder can declare.

    Attributes
    ----------
    DAILY : str
        Every calendar day.
    WEEKDAYS : str
        Selected weekdays.
    MONTH_DAY : str
        One day of every month.
    NTH_WEEKDAY : str
        The first through fifth named weekday of every month.
    LAST_DAY : str
        The last calendar day of every month.
    LAST_WEEKDAY : str
        The last named weekday of every month.
    """

    DAILY = "daily"
    WEEKDAYS = "weekdays"
    MONTH_DAY = "month_day"
    NTH_WEEKDAY = "nth_weekday"
    LAST_DAY = "last_day"
    LAST_WEEKDAY = "last_weekday"


class ReminderProblem(StrEnum):
    """Machine-readable reason a reminder mapping is malformed.

    Attributes
    ----------
    NOT_MAPPING : str
        The value is not a string-keyed mapping.
    SCHEDULE : str
        The mapping does not declare exactly one of recurrence or once.
    UNKNOWN_KIND : str
        The recurrence kind is missing or unsupported.
    TIMES : str
        The times list is missing, empty, or malformed.
    WEEKDAYS : str
        The weekdays list is missing, empty, or malformed.
    DAY : str
        The day of month is missing or outside 1 to 31.
    ORDINAL : str
        The nth weekday ordinal is missing or outside 1 to 5.
    WEEKDAY : str
        A required weekday is missing or malformed.
    ONCE : str
        The one-shot value is not a local calendar date and time.
    HANDLED : str
        The handled value is not an absolute instant with an offset.
    ZONE : str
        The zone is not a valid IANA time-zone name.
    """

    NOT_MAPPING = "not-mapping"
    SCHEDULE = "schedule"
    UNKNOWN_KIND = "unknown-kind"
    TIMES = "times"
    WEEKDAYS = "weekdays"
    DAY = "day"
    ORDINAL = "ordinal"
    WEEKDAY = "weekday"
    ONCE = "once"
    HANDLED = "handled"
    ZONE = "zone"


@dataclasses.dataclass(frozen=True, slots=True, order=True)
class ClockTime:
    """One local wall-clock time of day.

    Attributes
    ----------
    hour : int
        Hour from 0 to 23.
    minute : int
        Minute from 0 to 59.
    """

    hour: int
    minute: int

    def __post_init__(self) -> None:
        """Reject values outside the 24-hour clock.

        Raises
        ------
        ValueError
            If either part is not an integer in range.
        """
        if isinstance(self.hour, bool) or not isinstance(self.hour, int) or not 0 <= self.hour <= MAX_HOUR:
            message = f"Invalid reminder hour: {self.hour!r}"
            raise ValueError(message)
        if isinstance(self.minute, bool) or not isinstance(self.minute, int) or not 0 <= self.minute <= MAX_MINUTE:
            message = f"Invalid reminder minute: {self.minute!r}"
            raise ValueError(message)

    @classmethod
    def from_text(cls, value: str) -> Self:
        """Parse one strict ``HH:MM`` time.

        Parameters
        ----------
        value : str
            Written time. Leading zeroes are required.

        Returns
        -------
        ClockTime
            Parsed time.

        Raises
        ------
        ValueError
            If the text is not a zero-padded 24-hour time.
        """
        valid = (
            isinstance(value, str)
            and len(value) == TIME_TEXT_LENGTH
            and value[TIME_SEPARATOR_INDEX] == ":"
            and value[:TIME_SEPARATOR_INDEX].isdigit()
            and value[MINUTE_TEXT_START:].isdigit()
        )
        if not valid:
            message = f"Invalid reminder time: {value!r}"
            raise ValueError(message)
        try:
            time = cls(hour=int(value[:TIME_SEPARATOR_INDEX]), minute=int(value[MINUTE_TEXT_START:]))
        except ValueError as exc:
            message = f"Invalid reminder time: {value!r}"
            raise ValueError(message) from exc
        if time.text != value:
            message = f"Invalid reminder time: {value!r}"
            raise ValueError(message)
        return time

    @property
    def text(self) -> str:
        """Return the canonical zero-padded text.

        Returns
        -------
        str
            Time written as ``HH:MM``.
        """
        return f"{self.hour:02d}:{self.minute:02d}"

    def instants(self, day: datetime.date, zone: zoneinfo.ZoneInfo) -> tuple[datetime.datetime, ...]:
        """Return the absolute instants for this time on one local day.

        Parameters
        ----------
        day : datetime.date
            Local calendar date.
        zone : zoneinfo.ZoneInfo
            Time zone that interprets the wall-clock time.

        Returns
        -------
        tuple[datetime.datetime, ...]
            Zero instants for a daylight-saving gap, one for an ordinary
            time, or two for a repeated hour. Each instant is timezone-aware.

        Notes
        -----
        A repeated hour produces two instants, but occurrence selection keeps
        at most one entry. A nonexistent gap time is omitted rather than
        shifted to a different wall-clock time.
        """
        instants: dict[datetime.datetime, datetime.datetime] = {}
        for fold in (0, 1):
            aware = datetime.datetime(
                day.year,
                day.month,
                day.day,
                self.hour,
                self.minute,
                tzinfo=zone,
                fold=fold,
            )
            round_trip = aware.astimezone(datetime.UTC).astimezone(zone)
            if round_trip.replace(tzinfo=None) != aware.replace(tzinfo=None):
                continue
            instants[aware.astimezone(datetime.UTC)] = aware
        return tuple(sorted(instants.values(), key=lambda instant: instant.astimezone(datetime.UTC)))


@dataclasses.dataclass(frozen=True, slots=True)
class RecurrenceFields:
    """Fields that vary between recurrence kinds.

    Attributes
    ----------
    known : frozenset[str]
        Canonical mapping keys that belong to the parsed kind.
    weekdays : tuple[Weekday, ...]
        Selected weekdays for the weekdays kind.
    day : int | None
        Day of month for the month-day kind.
    nth : int | None
        Ordinal for the nth-weekday kind.
    weekday : Weekday | None
        Weekday for the nth-weekday and last-weekday kinds.
    """

    known: frozenset[str]
    weekdays: tuple[Weekday, ...] = ()
    day: int | None = None
    nth: int | None = None
    weekday: Weekday | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class Recurrence:
    """One repeating reminder schedule.

    Attributes
    ----------
    kind : ReminderKind
        Recurrence kind.
    times : tuple[ClockTime, ...]
        One or more local wall-clock times, sorted and unique.
    weekdays : tuple[Weekday, ...]
        Selected weekdays for the weekdays kind, sorted Monday first.
    day : int | None
        Day of month for the month-day kind.
    nth : int | None
        Ordinal from 1 to 5 for the nth-weekday kind.
    weekday : Weekday | None
        Weekday for the nth-weekday and last-weekday kinds.
    extra : tuple[tuple[str, object], ...]
        Unknown nested keys preserved from the source mapping.
    """

    kind: ReminderKind
    times: tuple[ClockTime, ...]
    weekdays: tuple[Weekday, ...] = ()
    day: int | None = None
    nth: int | None = None
    weekday: Weekday | None = None
    extra: tuple[tuple[str, object], ...] = ()

    def __post_init__(self) -> None:
        """Validate and normalize the recurrence shape.

        Raises
        ------
        ValueError
            If times are empty or the fields do not match the kind.
        """
        if not self.times:
            message = "A recurrence requires at least one time"
            raise ValueError(message)
        if any(not isinstance(time, ClockTime) for time in self.times):
            message = "Recurrence times must be ClockTime values"
            raise ValueError(message)
        object.__setattr__(self, "times", tuple(sorted(set(self.times))))
        object.__setattr__(self, "weekdays", tuple(sorted(set(self.weekdays), key=lambda day: day.position)))
        self._validate_shape()

    @classmethod
    def from_mapping(cls, value: object) -> "RecurrenceParse":
        """Parse a raw recurrence mapping.

        Parameters
        ----------
        value : object
            Raw nested mapping from frontmatter.

        Returns
        -------
        RecurrenceParse
            Parsed recurrence, or the first malformed-field problem.

        Notes
        -----
        Existing but irrelevant fields are preserved as unknown keys. Unknown
        keys are never a parse error.
        """
        mapping = cls.string_mapping(value)
        if mapping is None:
            return RecurrenceParse(problem=ReminderProblem.NOT_MAPPING)
        kind_value = mapping.get("kind")
        if not isinstance(kind_value, str):
            return RecurrenceParse(problem=ReminderProblem.UNKNOWN_KIND)
        try:
            kind = ReminderKind(kind_value)
        except ValueError:
            return RecurrenceParse(problem=ReminderProblem.UNKNOWN_KIND, detail=kind_value)
        times = cls._times(mapping.get("times"))
        if times is None:
            return RecurrenceParse(problem=ReminderProblem.TIMES)
        return cls._from_kind(kind, times, mapping)

    @classmethod
    def _from_kind(
        cls,
        kind: ReminderKind,
        times: tuple[ClockTime, ...],
        mapping: dict[str, object],
    ) -> "RecurrenceParse":
        """Parse the fields that belong to one recurrence kind."""
        if kind is ReminderKind.WEEKDAYS:
            return cls._from_weekdays(kind, times, mapping)
        if kind is ReminderKind.MONTH_DAY:
            return cls._from_month_day(kind, times, mapping)
        if kind is ReminderKind.NTH_WEEKDAY:
            return cls._from_nth_weekday(kind, times, mapping)
        if kind is ReminderKind.LAST_WEEKDAY:
            return cls._from_last_weekday(kind, times, mapping)
        return cls._build(kind, times, mapping, RecurrenceFields(known=frozenset({"kind", "times"})))

    @classmethod
    def _from_weekdays(
        cls,
        kind: ReminderKind,
        times: tuple[ClockTime, ...],
        mapping: dict[str, object],
    ) -> "RecurrenceParse":
        """Parse a selected-weekdays recurrence."""
        weekdays = cls._weekdays(mapping.get("weekdays"))
        if weekdays is None:
            return RecurrenceParse(problem=ReminderProblem.WEEKDAYS)
        return cls._build(
            kind,
            times,
            mapping,
            RecurrenceFields(known=frozenset({"kind", "times", "weekdays"}), weekdays=weekdays),
        )

    @classmethod
    def _from_month_day(
        cls,
        kind: ReminderKind,
        times: tuple[ClockTime, ...],
        mapping: dict[str, object],
    ) -> "RecurrenceParse":
        """Parse a day-of-month recurrence."""
        day = cls._bounded_int(mapping.get("day"), minimum=MIN_DAY, maximum=MAX_DAY)
        if day is None:
            return RecurrenceParse(problem=ReminderProblem.DAY)
        return cls._build(
            kind,
            times,
            mapping,
            RecurrenceFields(known=frozenset({"kind", "times", "day"}), day=day),
        )

    @classmethod
    def _from_nth_weekday(
        cls,
        kind: ReminderKind,
        times: tuple[ClockTime, ...],
        mapping: dict[str, object],
    ) -> "RecurrenceParse":
        """Parse an nth-weekday recurrence."""
        nth = cls._bounded_int(mapping.get("nth"), minimum=MIN_NTH, maximum=MAX_NTH)
        if nth is None:
            return RecurrenceParse(problem=ReminderProblem.ORDINAL)
        weekday = cls._weekday(mapping.get("weekday"))
        if weekday is None:
            return RecurrenceParse(problem=ReminderProblem.WEEKDAY)
        return cls._build(
            kind,
            times,
            mapping,
            RecurrenceFields(
                known=frozenset({"kind", "times", "nth", "weekday"}),
                nth=nth,
                weekday=weekday,
            ),
        )

    @classmethod
    def _from_last_weekday(
        cls,
        kind: ReminderKind,
        times: tuple[ClockTime, ...],
        mapping: dict[str, object],
    ) -> "RecurrenceParse":
        """Parse a last-weekday recurrence."""
        weekday = cls._weekday(mapping.get("weekday"))
        if weekday is None:
            return RecurrenceParse(problem=ReminderProblem.WEEKDAY)
        return cls._build(
            kind,
            times,
            mapping,
            RecurrenceFields(known=frozenset({"kind", "times", "weekday"}), weekday=weekday),
        )

    @classmethod
    def _build(
        cls,
        kind: ReminderKind,
        times: tuple[ClockTime, ...],
        mapping: dict[str, object],
        fields: "RecurrenceFields",
    ) -> "RecurrenceParse":
        """Build a recurrence from parsed fields and preserved extras."""
        extra = tuple((key, item) for key, item in mapping.items() if key not in fields.known)
        try:
            recurrence = cls(
                kind=kind,
                times=times,
                weekdays=fields.weekdays,
                day=fields.day,
                nth=fields.nth,
                weekday=fields.weekday,
                extra=extra,
            )
        except ValueError:
            return RecurrenceParse(problem=ReminderProblem.TIMES)
        return RecurrenceParse(recurrence=recurrence)

    def to_mapping(self) -> dict[str, object]:
        """Serialize the recurrence into a fresh mapping.

        Returns
        -------
        dict[str, object]
            Canonical fields followed by the preserved unknown keys.
        """
        mapping: dict[str, object] = {"kind": self.kind.value}
        if self.kind is ReminderKind.WEEKDAYS:
            mapping["weekdays"] = [day.value for day in self.weekdays]
        elif self.kind is ReminderKind.MONTH_DAY:
            mapping["day"] = self.day
        elif self.kind is ReminderKind.NTH_WEEKDAY:
            mapping["nth"] = self.nth
            mapping["weekday"] = self.weekday.value if self.weekday is not None else None
        elif self.kind is ReminderKind.LAST_WEEKDAY:
            mapping["weekday"] = self.weekday.value if self.weekday is not None else None
        mapping["times"] = [time.text for time in self.times]
        mapping.update(self.extra)
        return mapping

    def latest_occurrence(
        self,
        reference: datetime.datetime,
        zone: zoneinfo.ZoneInfo,
    ) -> datetime.datetime | None:
        """Return the latest occurrence at or before a reference instant.

        Parameters
        ----------
        reference : datetime.datetime
            Timezone-aware instant to search from.
        zone : zoneinfo.ZoneInfo
            Zone that interprets the local wall-clock times.

        Returns
        -------
        datetime.datetime | None
            Latest matching instant, or ``None`` when the search window has
            no occurrence.

        Raises
        ------
        ValueError
            If the reference instant is not timezone-aware.
        """
        type(self).require_aware(reference)
        for day in self._previous_days(reference.astimezone(zone).date()):
            matches = [instant for instant in self._instants(day, zone) if instant <= reference]
            if matches:
                return max(matches, key=lambda instant: instant.astimezone(datetime.UTC))
        return None

    def next_occurrence(
        self,
        reference: datetime.datetime,
        zone: zoneinfo.ZoneInfo,
    ) -> datetime.datetime | None:
        """Return the earliest occurrence after a reference instant.

        Parameters
        ----------
        reference : datetime.datetime
            Timezone-aware instant to search from.
        zone : zoneinfo.ZoneInfo
            Zone that interprets the local wall-clock times.

        Returns
        -------
        datetime.datetime | None
            Next matching instant, or ``None`` when the search window has no
            occurrence.

        Raises
        ------
        ValueError
            If the reference instant is not timezone-aware.
        """
        type(self).require_aware(reference)
        for day in self._next_days(reference.astimezone(zone).date()):
            matches = [instant for instant in self._instants(day, zone) if instant > reference]
            if matches:
                return min(matches, key=lambda instant: instant.astimezone(datetime.UTC))
        return None

    @staticmethod
    def string_mapping(value: object) -> dict[str, object] | None:
        """Return a string-keyed mapping copy, or ``None`` for another shape."""
        if not isinstance(value, dict):
            return None
        mapping: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                return None
            mapping[key] = item
        return mapping

    @staticmethod
    def _times(value: object) -> tuple[ClockTime, ...] | None:
        """Parse one or more strict clock times."""
        if not isinstance(value, list) or not value:
            return None
        times: list[ClockTime] = []
        for item in value:
            if not isinstance(item, str):
                return None
            try:
                times.append(ClockTime.from_text(item))
            except ValueError:
                return None
        return tuple(sorted(set(times)))

    @staticmethod
    def _weekdays(value: object) -> tuple[Weekday, ...] | None:
        """Parse one or more weekday names."""
        if not isinstance(value, list) or not value:
            return None
        weekdays: list[Weekday] = []
        for item in value:
            if not isinstance(item, str):
                return None
            try:
                weekdays.append(Weekday.from_text(item))
            except ValueError:
                return None
        return tuple(sorted(set(weekdays), key=lambda day: day.position))

    @staticmethod
    def _weekday(value: object) -> Weekday | None:
        """Parse one weekday name."""
        if not isinstance(value, str):
            return None
        try:
            return Weekday.from_text(value)
        except ValueError:
            return None

    @staticmethod
    def _bounded_int(value: object, *, minimum: int, maximum: int) -> int | None:
        """Parse one bounded integer."""
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            return None
        return value

    @staticmethod
    def require_aware(value: datetime.datetime) -> None:
        """Reject a naive instant.

        Raises
        ------
        ValueError
            If the value has no timezone offset.
        """
        if not Recurrence.is_aware(value):
            message = "A reminder instant must be timezone-aware"
            raise ValueError(message)

    @staticmethod
    def is_aware(value: datetime.datetime) -> bool:
        """Return whether a datetime carries a timezone offset.

        Parameters
        ----------
        value : datetime.datetime
            Value to inspect.

        Returns
        -------
        bool
            ``True`` when the value is timezone-aware.
        """
        return value.tzinfo is not None and value.utcoffset() is not None

    @staticmethod
    def _days_in_month(year: int, month: int) -> int:
        """Return the number of calendar days in one month."""
        if month == LAST_MONTH:
            return MAX_DAY
        return (datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)).day

    @staticmethod
    def _shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
        """Shift a year and month by a signed month count."""
        index = year * MONTHS_PER_YEAR + (month - 1) + offset
        quotient, remainder = divmod(index, MONTHS_PER_YEAR)
        return quotient, remainder + 1

    def _instants(self, day: datetime.date, zone: zoneinfo.ZoneInfo) -> tuple[datetime.datetime, ...]:
        """Return every existing instant for one local candidate day."""
        instants = [instant for time in self.times for instant in time.instants(day, zone)]
        return tuple(sorted(instants, key=lambda instant: instant.astimezone(datetime.UTC)))

    def _previous_days(self, reference_day: datetime.date) -> Iterator[datetime.date]:
        """Yield candidate days from the reference date backwards."""
        if self.kind in (ReminderKind.DAILY, ReminderKind.WEEKDAYS):
            limit = MAX_DAILY_SEARCH_DAYS if self.kind is ReminderKind.DAILY else MAX_WEEKDAY_SEARCH_DAYS
            for offset in range(limit):
                day = reference_day - datetime.timedelta(days=offset)
                if self._matches(day):
                    yield day
            return
        for offset in range(MAX_MONTH_SEARCH):
            year, month = self._shift_month(reference_day.year, reference_day.month, -offset)
            day = self._day_in_month(year, month)
            if day is not None and day <= reference_day:
                yield day

    def _next_days(self, reference_day: datetime.date) -> Iterator[datetime.date]:
        """Yield candidate days from the reference date forwards."""
        if self.kind in (ReminderKind.DAILY, ReminderKind.WEEKDAYS):
            limit = MAX_DAILY_SEARCH_DAYS if self.kind is ReminderKind.DAILY else MAX_WEEKDAY_SEARCH_DAYS + 1
            for offset in range(limit):
                day = reference_day + datetime.timedelta(days=offset)
                if self._matches(day):
                    yield day
            return
        for offset in range(MAX_MONTH_SEARCH):
            year, month = self._shift_month(reference_day.year, reference_day.month, offset)
            day = self._day_in_month(year, month)
            if day is not None and day >= reference_day:
                yield day

    def _matches(self, day: datetime.date) -> bool:
        """Return whether a day matches the daily or weekday kinds."""
        if self.kind is ReminderKind.DAILY:
            return True
        if self.kind is ReminderKind.WEEKDAYS:
            return Weekday.from_date(day) in self.weekdays
        return False

    def _day_in_month(self, year: int, month: int) -> datetime.date | None:
        """Return the monthly occurrence date, or ``None`` when it is skipped."""
        if self.kind is ReminderKind.MONTH_DAY:
            return self._month_day(year, month)
        if self.kind is ReminderKind.LAST_DAY:
            return datetime.date(year, month, self._days_in_month(year, month))
        if self.kind is ReminderKind.NTH_WEEKDAY:
            return self._nth_weekday(year, month)
        if self.kind is ReminderKind.LAST_WEEKDAY:
            return self._last_weekday(year, month)
        return None

    def _month_day(self, year: int, month: int) -> datetime.date | None:
        """Return the chosen day when the month contains it."""
        if self.day is None or self.day > self._days_in_month(year, month):
            return None
        return datetime.date(year, month, self.day)

    def _nth_weekday(self, year: int, month: int) -> datetime.date | None:
        """Return the chosen nth weekday when the month contains it."""
        if self.nth is None or self.weekday is None:
            return None
        first = datetime.date(year, month, 1)
        day = 1 + (self.weekday.position - first.weekday()) % 7 + 7 * (self.nth - 1)
        if day > self._days_in_month(year, month):
            return None
        return datetime.date(year, month, day)

    def _last_weekday(self, year: int, month: int) -> datetime.date | None:
        """Return the last chosen weekday of the month."""
        if self.weekday is None:
            return None
        last = datetime.date(year, month, self._days_in_month(year, month))
        return last - datetime.timedelta(days=(last.weekday() - self.weekday.position) % 7)

    def _validate_shape(self) -> None:
        """Reject fields that do not belong to the declared kind.

        Raises
        ------
        ValueError
            If required fields are missing or unrelated fields are set.
        """
        if self.kind is ReminderKind.WEEKDAYS:
            self._validate_weekdays()
        elif self.kind is ReminderKind.MONTH_DAY:
            self._validate_month_day()
        elif self.kind is ReminderKind.NTH_WEEKDAY:
            self._validate_nth_weekday()
        elif self.kind is ReminderKind.LAST_WEEKDAY:
            self._validate_last_weekday()
        else:
            self._validate_plain()

    def _validate_weekdays(self) -> None:
        """Validate the selected-weekdays shape."""
        if not self.weekdays or self.day is not None or self.nth is not None or self.weekday is not None:
            message = "A weekdays recurrence requires weekdays only"
            raise ValueError(message)

    def _validate_month_day(self) -> None:
        """Validate the day-of-month shape."""
        if self.weekdays or self.day is None or self.nth is not None or self.weekday is not None:
            message = "A month-day recurrence requires one day"
            raise ValueError(message)

    def _validate_nth_weekday(self) -> None:
        """Validate the nth-weekday shape."""
        if self.weekdays or self.day is not None or self.nth is None or self.weekday is None:
            message = "An nth-weekday recurrence requires an ordinal and a weekday"
            raise ValueError(message)

    def _validate_last_weekday(self) -> None:
        """Validate the last-weekday shape."""
        if self.weekdays or self.day is not None or self.nth is not None or self.weekday is None:
            message = "A last-weekday recurrence requires a weekday"
            raise ValueError(message)

    def _validate_plain(self) -> None:
        """Validate a kind that carries no extra fields."""
        if self.weekdays or self.day is not None or self.nth is not None or self.weekday is not None:
            message = "This recurrence kind does not declare extra fields"
            raise ValueError(message)


@dataclasses.dataclass(frozen=True, slots=True)
class RecurrenceParse:
    """Result of parsing one raw recurrence mapping.

    Attributes
    ----------
    recurrence : Recurrence | None
        Parsed recurrence, or ``None`` when the mapping is malformed.
    problem : ReminderProblem | None
        First malformed-field problem, or ``None`` on success.
    detail : str
        Written value associated with the problem, when one is useful.
    """

    recurrence: Recurrence | None = None
    problem: ReminderProblem | None = None
    detail: str = ""

    @property
    def is_valid(self) -> bool:
        """Return whether parsing succeeded.

        Returns
        -------
        bool
            ``True`` when a recurrence was parsed.
        """
        return self.recurrence is not None


@dataclasses.dataclass(frozen=True, slots=True)
class OneShot:
    """One local calendar date and time.

    Attributes
    ----------
    local : datetime.datetime
        Naive local date and time with minute precision.
    """

    local: datetime.datetime

    def __post_init__(self) -> None:
        """Reject timestamps that are not local minute-precision values.

        Raises
        ------
        TypeError
            If the value is not a datetime.
        ValueError
            If the value is timezone-aware or carries seconds or microseconds.
        """
        if not isinstance(self.local, datetime.datetime):
            message = "A one-shot requires a datetime"
            raise TypeError(message)
        if self.local.tzinfo is not None or self.local.utcoffset() is not None:
            message = "A one-shot is a local date and time"
            raise ValueError(message)
        if self.local.second != 0 or self.local.microsecond != 0:
            message = "A one-shot uses minute precision"
            raise ValueError(message)

    @classmethod
    def from_value(cls, value: object) -> Self:
        """Parse one raw one-shot value.

        Parameters
        ----------
        value : object
            Raw value. A string must use ``YYYY-MM-DDTHH:MM``; a YAML
            timestamp must already be a naive minute-precision datetime.

        Returns
        -------
        OneShot
            Parsed local date and time.

        Raises
        ------
        ValueError
            If the value is not a local minute-precision date and time.
        """
        if isinstance(value, datetime.datetime):
            return cls(local=value)
        if isinstance(value, str):
            try:
                parsed = datetime.datetime.fromisoformat(value.strip())
            except ValueError as exc:
                message = f"Invalid one-shot: {value!r}"
                raise ValueError(message) from exc
            return cls(local=parsed)
        message = f"Invalid one-shot: {value!r}"
        raise ValueError(message)

    @property
    def text(self) -> str:
        """Return the canonical local text.

        Returns
        -------
        str
            Date and time written as ``YYYY-MM-DDTHH:MM``.
        """
        return self.local.isoformat(timespec="minutes")

    def instants(self, zone: zoneinfo.ZoneInfo) -> tuple[datetime.datetime, ...]:
        """Return the absolute instants for this local date and time.

        Parameters
        ----------
        zone : zoneinfo.ZoneInfo
            Zone that interprets the local value.

        Returns
        -------
        tuple[datetime.datetime, ...]
            Zero instants in a daylight-saving gap, one for an ordinary time,
            or two for a repeated hour.
        """
        return ClockTime(hour=self.local.hour, minute=self.local.minute).instants(self.local.date(), zone)

    def latest_occurrence(
        self,
        reference: datetime.datetime,
        zone: zoneinfo.ZoneInfo,
    ) -> datetime.datetime | None:
        """Return the one-shot instant when it is at or before the reference.

        Parameters
        ----------
        reference : datetime.datetime
            Timezone-aware instant to compare against.
        zone : zoneinfo.ZoneInfo
            Zone that interprets the local value.

        Returns
        -------
        datetime.datetime | None
            Latest existing instant at or before the reference, or ``None``.

        Raises
        ------
        ValueError
            If the reference instant is not timezone-aware.
        """
        Recurrence.require_aware(reference)
        matches = [instant for instant in self.instants(zone) if instant <= reference]
        return max(matches, key=lambda instant: instant.astimezone(datetime.UTC)) if matches else None

    def next_occurrence(
        self,
        reference: datetime.datetime,
        zone: zoneinfo.ZoneInfo,
    ) -> datetime.datetime | None:
        """Return the one-shot instant when it is after the reference.

        Parameters
        ----------
        reference : datetime.datetime
            Timezone-aware instant to compare against.
        zone : zoneinfo.ZoneInfo
            Zone that interprets the local value.

        Returns
        -------
        datetime.datetime | None
            Earliest existing instant after the reference, or ``None``.

        Raises
        ------
        ValueError
            If the reference instant is not timezone-aware.
        """
        Recurrence.require_aware(reference)
        matches = [instant for instant in self.instants(zone) if instant > reference]
        return min(matches, key=lambda instant: instant.astimezone(datetime.UTC)) if matches else None


@dataclasses.dataclass(frozen=True, slots=True)
class ScheduleParse:
    """Result of parsing the recurrence or one-shot member.

    Attributes
    ----------
    schedule : Recurrence | OneShot | None
        Parsed schedule, or ``None`` when the mapping is malformed.
    problem : ReminderProblem | None
        First malformed-field problem, or ``None`` on success.
    detail : str
        Written value associated with the problem, when one is useful.
    """

    schedule: Recurrence | OneShot | None = None
    problem: ReminderProblem | None = None
    detail: str = ""

    @property
    def is_valid(self) -> bool:
        """Return whether parsing succeeded.

        Returns
        -------
        bool
            ``True`` when a schedule was parsed.
        """
        return self.schedule is not None


@dataclasses.dataclass(frozen=True, slots=True)
class ReminderParse:
    """Result of parsing one raw reminder mapping.

    Attributes
    ----------
    reminder : Reminder | None
        Parsed reminder, or ``None`` when the mapping is malformed.
    problem : ReminderProblem | None
        First malformed-field problem, or ``None`` on success.
    detail : str
        Written value associated with the problem, when one is useful.
    """

    reminder: "Reminder | None" = None
    problem: ReminderProblem | None = None
    detail: str = ""

    @property
    def is_valid(self) -> bool:
        """Return whether parsing succeeded.

        Returns
        -------
        bool
            ``True`` when a reminder was parsed.
        """
        return self.reminder is not None


@dataclasses.dataclass(frozen=True, slots=True)
class Reminder:
    """One whole-note reminder schedule.

    Attributes
    ----------
    schedule : Recurrence | OneShot
        Repeating schedule or one local date and time.
    zone : str | None
        Stored IANA zone name, or ``None`` to use the system zone.
    handled : datetime.datetime | None
        Last absolute instant acknowledged by dismissal.
    extra : tuple[tuple[str, object], ...]
        Unknown nested keys preserved from the source mapping.

    Notes
    -----
    The reminder is the on-disk contract. Occurrence methods are pure: they
    receive the reference instant and the system zone from the caller and never
    read the clock or the filesystem.
    """

    schedule: Recurrence | OneShot
    zone: str | None = None
    handled: datetime.datetime | None = None
    extra: tuple[tuple[str, object], ...] = ()

    def __post_init__(self) -> None:
        """Validate the zone and handled instant.

        Raises
        ------
        ValueError
            If the zone is unknown or the handled value is not an absolute
            instant with an offset.
        """
        if self.zone is not None:
            self._zone(self.zone)
        if self.handled is not None:
            Recurrence.require_aware(self.handled)

    @classmethod
    def from_mapping(cls, value: object) -> ReminderParse:
        """Parse one raw reminder mapping.

        Parameters
        ----------
        value : object
            Raw value of the ``reminder`` key.

        Returns
        -------
        ReminderParse
            Parsed reminder, or the first malformed-field problem. Unknown
            nested keys are preserved in the parsed reminder.
        """
        mapping = Recurrence.string_mapping(value)
        if mapping is None:
            return ReminderParse(problem=ReminderProblem.NOT_MAPPING)
        try:
            zone_name = cls._zone_name(mapping.get("zone"))
        except ValueError:
            return ReminderParse(problem=ReminderProblem.ZONE, detail=str(mapping.get("zone", "")))
        parsed_schedule = cls._schedule(mapping)
        if parsed_schedule.schedule is None:
            return ReminderParse(problem=parsed_schedule.problem, detail=parsed_schedule.detail)
        try:
            handled = cls._handled(mapping.get("handled"))
        except (TypeError, ValueError):
            return ReminderParse(problem=ReminderProblem.HANDLED)
        known = {"zone", "recurrence", "once", "handled"}
        extra = tuple((key, item) for key, item in mapping.items() if key not in known)
        try:
            reminder = cls(schedule=parsed_schedule.schedule, zone=zone_name, handled=handled, extra=extra)
        except ValueError:
            return ReminderParse(problem=ReminderProblem.ZONE)
        return ReminderParse(reminder=reminder)

    @classmethod
    def _schedule(cls, mapping: dict[str, object]) -> ScheduleParse:
        """Parse the recurrence or one-shot member of a reminder mapping."""
        recurrence_value = mapping.get("recurrence")
        once_value = mapping.get("once")
        recurrence_declared = recurrence_value is not None
        once_declared = once_value is not None
        if recurrence_declared == once_declared:
            return ScheduleParse(problem=ReminderProblem.SCHEDULE)
        if recurrence_declared:
            parsed = Recurrence.from_mapping(recurrence_value)
            return ScheduleParse(schedule=parsed.recurrence, problem=parsed.problem, detail=parsed.detail)
        try:
            return ScheduleParse(schedule=OneShot.from_value(once_value))
        except ValueError:
            return ScheduleParse(problem=ReminderProblem.ONCE)

    def to_mapping(self) -> dict[str, object]:
        """Serialize the reminder into a fresh mapping.

        Returns
        -------
        dict[str, object]
            Stored zone, schedule, handled instant, and preserved unknown
            keys. A missing zone stays absent.
        """
        mapping: dict[str, object] = {}
        if self.zone is not None:
            mapping["zone"] = self.zone
        if isinstance(self.schedule, Recurrence):
            mapping["recurrence"] = self.schedule.to_mapping()
        else:
            mapping["once"] = self.schedule.text
        if self.handled is not None:
            mapping["handled"] = self.handled.isoformat()
        mapping.update(self.extra)
        return mapping

    def resolved_zone(self, system_zone: str) -> str:
        """Return the stored zone or the system zone.

        Parameters
        ----------
        system_zone : str
            Computer's current IANA zone name.

        Returns
        -------
        str
            Stored zone name when present, otherwise the system zone.
        """
        return self.zone if self.zone is not None else system_zone

    def latest_occurrence(
        self,
        reference: datetime.datetime,
        system_zone: str,
    ) -> datetime.datetime | None:
        """Return the latest occurrence at or before a reference instant.

        Parameters
        ----------
        reference : datetime.datetime
            Timezone-aware instant to search from.
        system_zone : str
            IANA zone used when the reminder stores no zone.

        Returns
        -------
        datetime.datetime | None
            Latest matching instant, or ``None``.

        Raises
        ------
        ValueError
            If the reference instant is not timezone-aware.
        """
        return self.schedule.latest_occurrence(reference, self._zone(self.resolved_zone(system_zone)))

    def next_occurrence(
        self,
        reference: datetime.datetime,
        system_zone: str,
    ) -> datetime.datetime | None:
        """Return the earliest occurrence after a reference instant.

        Parameters
        ----------
        reference : datetime.datetime
            Timezone-aware instant to search from.
        system_zone : str
            IANA zone used when the reminder stores no zone.

        Returns
        -------
        datetime.datetime | None
            Next matching instant, or ``None``.

        Raises
        ------
        ValueError
            If the reference instant is not timezone-aware.
        """
        return self.schedule.next_occurrence(reference, self._zone(self.resolved_zone(system_zone)))

    def due_occurrence(
        self,
        reference: datetime.datetime,
        system_zone: str,
    ) -> datetime.datetime | None:
        """Return the occurrence that is due, if any.

        Parameters
        ----------
        reference : datetime.datetime
            Timezone-aware instant to evaluate.
        system_zone : str
            IANA zone used when the reminder stores no zone.

        Returns
        -------
        datetime.datetime | None
            Latest occurrence when it is after the handled instant, or when no
            handled instant applies; otherwise ``None``.

        Notes
        -----
        A handled instant later than the reference is treated as absent, so a
        clock skew or a hand-edited future value cannot suppress the reminder
        indefinitely. A dismissal at the shown occurrence suppresses only that
        occurrence.
        """
        latest = self.latest_occurrence(reference, system_zone)
        if latest is None:
            return None
        handled = self.handled
        if handled is not None and handled.astimezone(datetime.UTC) > reference.astimezone(datetime.UTC):
            handled = None
        if handled is not None and latest.astimezone(datetime.UTC) <= handled.astimezone(datetime.UTC):
            return None
        return latest

    def same_schedule(self, other: "Reminder") -> bool:
        """Return whether two reminders declare the same schedule and zone.

        Parameters
        ----------
        other : Reminder
            Reminder to compare.

        Returns
        -------
        bool
            ``True`` when the recurrence or one-shot and zone are equal.
            Handled instants and unknown keys do not participate.
        """
        return self.schedule == other.schedule and self.zone == other.zone

    def with_handled(self, occurrence: datetime.datetime) -> Self:
        """Return a copy that marks one occurrence handled.

        Parameters
        ----------
        occurrence : datetime.datetime
            Absolute instant to record.

        Returns
        -------
        Reminder
            New reminder with the handled value replaced.
        """
        return dataclasses.replace(self, handled=occurrence)

    def without_handled(self) -> Self:
        """Return a copy with no handled instant.

        Returns
        -------
        Reminder
            New reminder with the handled value cleared.
        """
        return dataclasses.replace(self, handled=None)

    def with_schedule(self, schedule: "Recurrence | OneShot", zone: str | None) -> Self:
        """Return a copy with a replaced schedule and zone.

        Parameters
        ----------
        schedule : Recurrence | OneShot
            Replacement schedule.
        zone : str | None
            Replacement IANA zone, or ``None`` for the system zone.

        Returns
        -------
        Reminder
            New reminder. A changed schedule or zone clears the handled
            instant; an unchanged schedule preserves it.
        """
        candidate = dataclasses.replace(self, schedule=schedule, zone=zone)
        if candidate.same_schedule(self):
            return dataclasses.replace(candidate, handled=self.handled)
        return dataclasses.replace(candidate, handled=None)

    @classmethod
    def _zone_name(cls, value: object) -> str | None:
        """Return a validated zone name, or ``None`` when the key is absent.

        Raises
        ------
        ValueError
            If the value is not a valid IANA zone name.
        """
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            message = "A reminder zone must be a non-empty string"
            raise ValueError(message)
        name = value.strip()
        cls._zone(name)
        return name

    @staticmethod
    def _zone(name: str) -> zoneinfo.ZoneInfo:
        """Resolve one IANA zone name.

        Raises
        ------
        ValueError
            If the name is empty or the time-zone database does not contain it.
        """
        if not name.strip():
            message = "A time zone name must not be empty"
            raise ValueError(message)
        try:
            return zoneinfo.ZoneInfo(name)
        except zoneinfo.ZoneInfoNotFoundError as exc:
            message = f"Unknown time zone: {name}"
            raise ValueError(message) from exc

    @staticmethod
    def _handled(value: object) -> datetime.datetime | None:
        """Parse the optional handled instant.

        Parameters
        ----------
        value : object
            Raw handled value.

        Returns
        -------
        datetime.datetime | None
            Aware instant, or ``None`` when absent.

        Raises
        ------
        ValueError
            If the value is not an absolute instant with an offset.
        """
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            if not Recurrence.is_aware(value):
                message = "A handled instant must carry an offset"
                raise ValueError(message)
            return value
        if not isinstance(value, str):
            message = "A handled instant must be a timestamp"
            raise TypeError(message)
        try:
            parsed = datetime.datetime.fromisoformat(value.strip())
        except ValueError as exc:
            message = f"Invalid handled instant: {value!r}"
            raise ValueError(message) from exc
        if not Recurrence.is_aware(parsed):
            message = "A handled instant must carry an offset"
            raise ValueError(message)
        return parsed
