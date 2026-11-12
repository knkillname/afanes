# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Note vocabulary used by the reference engine, the parser, and the vault."""

import dataclasses
import datetime
import typing
from enum import StrEnum

_YEAR_TEXT_LENGTH = 4
_MONTH_TEXT_LENGTH = 7
_DAY_TEXT_LENGTH = 10


class Status(StrEnum):
    """Workflow states for projects and references.

    Attributes
    ----------
    ACTIVE : str
        Available or currently in progress.
    WAITING : str
        Delegated or blocked on someone else.
    DONE : str
        Completed.
    CANCELLED : str
        Abandoned without completion.
    ARCHIVED : str
        Kept but hidden from active views.
    LATER : str
        Deferred for possible future attention.
    """

    ACTIVE = "active"
    WAITING = "waiting"
    DONE = "done"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"
    LATER = "later"


# Public per-type status policy. Absence of a status is always allowed; these
# sets constrain a status only when the key is present.
PROJECT_STATUSES: frozenset[Status] = frozenset(
    {
        Status.ACTIVE,
        Status.WAITING,
        Status.DONE,
        Status.CANCELLED,
        Status.ARCHIVED,
        Status.LATER,
    }
)
REFERENCE_STATUSES: frozenset[Status] = frozenset({Status.LATER, Status.ARCHIVED})
NOTE_STATUSES: frozenset[Status] = frozenset()


class NoteType(StrEnum):
    """Kinds of notes a vault can contain.

    Attributes
    ----------
    NOTE : str
        Unclarified capture that still needs an explicit processing outcome.
    REFERENCE : str
        Non-actionable knowledge kept for later consultation.
    PROJECT : str
        Outcome whose body contains the steps that advance it.
    LOG : str
        Dated diary entry whose identity is its date.
    """

    NOTE = "note"
    PROJECT = "project"
    REFERENCE = "reference"
    LOG = "log"

    @property
    def allowed_statuses(self) -> frozenset[Status]:
        """Return the statuses valid for this note type.

        Returns
        -------
        frozenset[Status]
            Statuses allowed when a status key is present. An absent status is
            always allowed and is not represented in the result.
        """
        if self is NoteType.PROJECT:
            return PROJECT_STATUSES
        if self is NoteType.REFERENCE:
            return REFERENCE_STATUSES
        return NOTE_STATUSES


class DatePrecision(StrEnum):
    """Granularity represented by a note date.

    Attributes
    ----------
    YEAR : str
        The date names a whole calendar year, as ``YYYY``.
    MONTH : str
        The date names a whole calendar month, as ``YYYY-MM``.
    DAY : str
        The date names one calendar day, as ``YYYY-MM-DD``.
    """

    YEAR = "year"
    MONTH = "month"
    DAY = "day"


@dataclasses.dataclass(frozen=True, slots=True)
class NoteDate:
    """ISO calendar date with year, month, or day precision.

    Attributes
    ----------
    text : str
        ISO text exactly as written: ``YYYY``, ``YYYY-MM``, or ``YYYY-MM-DD``.
    precision : DatePrecision
        Granularity represented by :attr:`text`.

    Raises
    ------
    ValueError
        If the text does not describe a valid calendar value at the declared
        precision.

    Notes
    -----
    A partial date is a calendar value, not an instant. It never carries a time
    or timezone. Ordering uses :attr:`sort_key`, which places year precision
    before months and months before days within the same year.
    """

    text: str
    precision: DatePrecision

    def __post_init__(self) -> None:
        """Validate the ISO text against the declared precision.

        Raises
        ------
        ValueError
            If the text is not exactly ``YYYY``, ``YYYY-MM``, or
            ``YYYY-MM-DD``, or the value is not a valid calendar value.
        """
        value = self.text.strip()
        if value != self.text:
            message = "A note date must not have surrounding whitespace"
            raise ValueError(message)
        if self.precision is DatePrecision.YEAR:
            if len(value) != _YEAR_TEXT_LENGTH or not value.isdigit():
                message = f"Invalid note date: {value!r}; use YYYY, YYYY-MM, or YYYY-MM-DD"
                raise ValueError(message)
            self._calendar_date(int(value), 1, 1)
            return
        if self.precision is DatePrecision.MONTH:
            if len(value) != _MONTH_TEXT_LENGTH or value[4] != "-" or not (value[:4] + value[5:]).isdigit():
                message = f"Invalid note date: {value!r}; use YYYY, YYYY-MM, or YYYY-MM-DD"
                raise ValueError(message)
            self._calendar_date(int(value[:4]), int(value[5:]), 1)
            return
        if len(value) != _DAY_TEXT_LENGTH:
            message = f"Invalid note date: {value!r}; use YYYY, YYYY-MM, or YYYY-MM-DD"
            raise ValueError(message)
        try:
            datetime.date.fromisoformat(value)
        except ValueError as exc:
            message = f"Invalid note date: {value!r}; use YYYY, YYYY-MM, or YYYY-MM-DD"
            raise ValueError(message) from exc

    @staticmethod
    def _calendar_date(year: int, month: int, day: int) -> datetime.date:
        """Return a calendar date or raise a uniform validation error.

        Parameters
        ----------
        year : int
            Calendar year.
        month : int
            Calendar month.
        day : int
            Calendar day.

        Returns
        -------
        datetime.date
            Validated calendar date.

        Raises
        ------
        ValueError
            If the values do not form a valid calendar date.
        """
        try:
            return datetime.date(year, month, day)
        except ValueError as exc:
            message = f"Invalid note date: {year:04d}-{month:02d}-{day:02d}"
            raise ValueError(message) from exc

    @classmethod
    def from_text(cls, text: str) -> "NoteDate":
        """Parse ISO text into a note date.

        Parameters
        ----------
        text : str
            Date written as ``YYYY``, ``YYYY-MM``, or ``YYYY-MM-DD``.
            Surrounding whitespace is removed.

        Returns
        -------
        NoteDate
            Parsed date with the precision implied by the number of parts.

        Raises
        ------
        ValueError
            If the text is not a valid ISO partial date.
        """
        value = text.strip()
        if len(value) == _YEAR_TEXT_LENGTH:
            return cls(value, DatePrecision.YEAR)
        if len(value) == _MONTH_TEXT_LENGTH:
            return cls(value, DatePrecision.MONTH)
        if len(value) == _DAY_TEXT_LENGTH:
            return cls(value, DatePrecision.DAY)
        message = f"Invalid note date: {value!r}; use YYYY, YYYY-MM, or YYYY-MM-DD"
        raise ValueError(message)

    @classmethod
    def from_date(cls, value: datetime.date) -> "NoteDate":
        """Build a day-precision date from a calendar date.

        Parameters
        ----------
        value : datetime.date
            Calendar date to represent.

        Returns
        -------
        NoteDate
            Day-precision note date.
        """
        return cls(value.isoformat(), DatePrecision.DAY)

    @classmethod
    def from_year(cls, year: int) -> "NoteDate":
        """Build a year-precision date.

        Parameters
        ----------
        year : int
            Calendar year.

        Returns
        -------
        NoteDate
            Year-precision note date.

        Raises
        ------
        ValueError
            If the year is not a valid calendar year.
        """
        return cls(f"{year:04d}", DatePrecision.YEAR)

    @property
    def year(self) -> int:
        """Return the calendar year.

        Returns
        -------
        int
            Four-digit calendar year.
        """
        return int(self.text[:4])

    @property
    def month(self) -> int:
        """Return the calendar month, or ``0`` for year precision.

        Returns
        -------
        int
            Calendar month, or ``0`` when the date names a whole year.
        """
        if self.precision is DatePrecision.YEAR:
            return 0
        return int(self.text[5:7])

    @property
    def day(self) -> int:
        """Return the calendar day, or ``0`` for year or month precision.

        Returns
        -------
        int
            Calendar day, or ``0`` when the date is not day-precision.
        """
        if self.precision is not DatePrecision.DAY:
            return 0
        return int(self.text[8:10])

    @property
    def sort_key(self) -> tuple[int, int, int]:
        """Return a deterministic ordering key.

        Returns
        -------
        tuple[int, int, int]
            Year, month, and day, with absent parts represented by zero.
        """
        return (self.year, self.month, self.day)

    def to_yaml_value(self) -> object:
        """Return the value written into frontmatter.

        Returns
        -------
        object
            A :class:`datetime.date` for day precision, so YAML writes an
            unquoted ISO date, or the ISO text for year and month precision.
        """
        if self.precision is DatePrecision.DAY:
            return datetime.date.fromisoformat(self.text)
        return self.text

    def __str__(self) -> str:
        """Return the ISO text.

        Returns
        -------
        str
            Date written as ``YYYY``, ``YYYY-MM``, or ``YYYY-MM-DD``.
        """
        return self.text

    def __lt__(self, other: object) -> bool:
        """Compare two note dates by calendar order.

        Parameters
        ----------
        other : object
            Value to compare against.

        Returns
        -------
        bool
            ``True`` when this date sorts before ``other``.

        Raises
        ------
        TypeError
            If ``other`` is not a :class:`NoteDate`.
        """
        if not isinstance(other, NoteDate):
            return NotImplemented
        return self.sort_key < other.sort_key


@dataclasses.dataclass(frozen=True, slots=True, eq=False)
class CategoryLabel:
    """Free-form label that groups reference notes and selects a folder.

    Attributes
    ----------
    value : str
        Written label, preserving its original case and spacing.

    Raises
    ------
    ValueError
        If the label is blank, is a traversal segment, or contains a path
        separator. The frontmatter parser converts this into a domain error.

    Notes
    -----
    Labels are not a closed list and do not select a reference scheme. Two
    labels that differ only in case compare equal and produce the same hash, so
    grouping and folder reuse are case-insensitive while the written form is
    preserved.
    """

    value: str

    def __post_init__(self) -> None:
        r"""Validate that the label is one non-empty path segment.

        Raises
        ------
        ValueError
            If the label is blank, is ``.`` or ``..``, or contains ``/`` or
            ``\\``.
        """
        label = self.value.strip()
        if not label:
            message = "A category label must not be empty"
            raise ValueError(message)
        if "/" in label or "\\" in label:
            message = "A category label must be a single path segment"
            raise ValueError(message)
        if label in {".", ".."}:
            message = "A category label must name a folder, not a traversal"
            raise ValueError(message)

    @property
    def key(self) -> str:
        """Return the case-folded comparison key.

        Returns
        -------
        str
            Case-folded label used for grouping and folder reuse.
        """
        return self.value.casefold()

    @typing.override
    def __eq__(self, other: object) -> bool:
        """Compare labels case-insensitively.

        Parameters
        ----------
        other : object
            Value to compare against.

        Returns
        -------
        bool
            ``True`` when ``other`` is a :class:`CategoryLabel` with the same
            case-folded value.
        """
        if not isinstance(other, CategoryLabel):
            return NotImplemented
        return self.key == other.key

    def __hash__(self) -> int:
        """Return a hash consistent with case-insensitive equality.

        Returns
        -------
        int
            Hash of the case-folded label.
        """
        return hash(self.key)
