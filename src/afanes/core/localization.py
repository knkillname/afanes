# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Locale selection and locale-aware display formatting.

The module owns the supported language set, the non-mutating locale resolver,
and the explicit display tables used for dates, times, and counts. It never
calls ``locale.setlocale``: that function mutates process-global state and is
not thread-safe.
"""

import dataclasses
import datetime
import locale
from collections.abc import Mapping
from typing import Self

import afanes.models.note

# Public locale policy shared by the interface and the command line.
SUPPORTED_LANGUAGES = ("en", "es")
DEFAULT_LANGUAGE = "en"
MONTHS_PER_YEAR = 12
HOURS_PER_HALF_DAY = 12

# Public environment precedence. The first present variable wins.
LOCALE_ENVIRONMENT_VARIABLES = ("LC_ALL", "LC_MESSAGES", "LANG")

# Public language names accepted from Windows locale identifiers.
_WINDOWS_LANGUAGES = {
    "english": "en",
    "spanish": "es",
}

_ENGLISH_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_SPANISH_MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
_ENGLISH_SHORT_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
_SPANISH_SHORT_MONTHS = (
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
)
_ENGLISH_WEEKDAYS = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
_SPANISH_WEEKDAYS = ("Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do")


@dataclasses.dataclass(frozen=True, slots=True)
class LocaleTag:
    """One normalized locale tag and its supported language.

    Attributes
    ----------
    language : str
        Supported language code, either ``en`` or ``es``.
    tag : str
        Normalized locale tag that produced the language, such as ``es-mx``.
    """

    language: str
    tag: str

    def __post_init__(self) -> None:
        """Validate the language and normalized tag.

        Raises
        ------
        ValueError
            If the language is unsupported or the tag is empty.
        """
        if self.language not in SUPPORTED_LANGUAGES:
            message = f"Unsupported language: {self.language!r}"
            raise ValueError(message)
        if not self.tag:
            message = "Locale tag must not be empty"
            raise ValueError(message)

    @classmethod
    def normalize(cls, tag: str | None) -> str:
        """Normalize a locale tag without changing its language.

        Parameters
        ----------
        tag : str | None
            Raw locale tag, environment value, or Windows locale name.

        Returns
        -------
        str
            Lowercase tag with hyphens, without an encoding suffix or modifier.
            An empty or unavailable value normalizes to ``en``.
        """
        if tag is None:
            return DEFAULT_LANGUAGE
        text = tag.strip()
        if not text:
            return DEFAULT_LANGUAGE
        text = text.split(".", 1)[0]
        text = text.split("@", 1)[0]
        normalized = text.replace("_", "-").casefold()
        return normalized or DEFAULT_LANGUAGE

    @classmethod
    def language_of(cls, tag: str | None) -> str | None:
        """Return the supported language a tag names, if any.

        Parameters
        ----------
        tag : str | None
            Raw locale tag, environment value, or Windows locale name.

        Returns
        -------
        str | None
            ``en`` or ``es`` for a supported tag, or ``None`` when the tag names
            no supported language. The caller decides how to fall back.
        """
        normalized = cls.normalize(tag)
        prefix = normalized.split("-", 1)[0]
        windows = _WINDOWS_LANGUAGES.get(prefix)
        if windows is not None:
            return windows
        if prefix in SUPPORTED_LANGUAGES:
            return prefix
        return None

    @classmethod
    def parse(cls, tag: str | None) -> Self:
        """Build a supported locale from any tag.

        Parameters
        ----------
        tag : str | None
            Raw locale tag, environment value, or Windows locale name.

        Returns
        -------
        LocaleTag
            Supported locale. A regional supported tag keeps its normalized
            form; every unsupported or unavailable tag resolves to English.
        """
        language = cls.language_of(tag)
        if language is None:
            return cls(language=DEFAULT_LANGUAGE, tag=DEFAULT_LANGUAGE)
        return cls(language=language, tag=cls.normalize(tag))


class LocaleResolver:
    """Resolve the active locale without mutating process-global state."""

    @classmethod
    def system_locale(cls) -> str | None:
        """Return the locale Python reports for the process character type.

        Returns
        -------
        str | None
            Locale tag, or ``None`` when the operating system reports none.

        Notes
        -----
        ``locale.getlocale`` reads the process state without changing it. The
        ``LC_CTYPE`` category is the locale Python initializes from the
        environment at startup, and it is available on every supported
        platform.
        """
        tag, _encoding = locale.getlocale(locale.LC_CTYPE)
        return tag

    @classmethod
    def resolve(
        cls,
        override: str | None,
        environ: Mapping[str, str],
        os_locale: str | None,
    ) -> LocaleTag:
        """Resolve the active locale from an override and the environment.

        Parameters
        ----------
        override : str | None
            Saved language preference, or ``None`` to use the system locale.
            An unsupported value is ignored so a corrupt preference falls back
            to system resolution.
        environ : collections.abc.Mapping[str, str]
            Environment variables to inspect.
        os_locale : str | None
            Locale reported by the operating system, used when the environment
            carries no locale variable.

        Returns
        -------
        LocaleTag
            Active locale. The resolution order is the saved override,
            ``LC_ALL``, ``LC_MESSAGES``, ``LANG``, the operating-system locale,
            and finally English.

        Notes
        -----
        The resolver is deterministic and side-effect free. It never calls
        ``locale.setlocale`` and never reads the network.
        """
        if override is not None and override.strip() and LocaleTag.language_of(override) is not None:
            return LocaleTag.parse(override)
        for name in LOCALE_ENVIRONMENT_VARIABLES:
            value = environ.get(name)
            if value is not None and value.strip():
                return LocaleTag.parse(value)
        if os_locale is not None and os_locale.strip():
            return LocaleTag.parse(os_locale)
        return LocaleTag.parse(None)


@dataclasses.dataclass(frozen=True, slots=True)
class LocaleFormat:
    """Display formatting for one supported language.

    Attributes
    ----------
    language : str
        Supported language code, either ``en`` or ``es``.

    Notes
    -----
    The tables are explicit so the process C locale cannot change display.
    The calendar is Monday-first for both languages.
    """

    language: str

    def __post_init__(self) -> None:
        """Validate the supported language.

        Raises
        ------
        ValueError
            If the language is unsupported.
        """
        if self.language not in SUPPORTED_LANGUAGES:
            message = f"Unsupported language: {self.language!r}"
            raise ValueError(message)

    @classmethod
    def for_language(cls, language: str) -> Self:
        """Return formatting for a language code.

        Parameters
        ----------
        language : str
            Language code. An unsupported value resolves to English.

        Returns
        -------
        LocaleFormat
            Formatting table for the supported language.
        """
        resolved = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        return cls(language=resolved)

    @classmethod
    def for_locale(cls, locale: LocaleTag) -> Self:
        """Return formatting for a resolved locale.

        Parameters
        ----------
        locale : LocaleTag
            Active locale.

        Returns
        -------
        LocaleFormat
            Formatting table for the locale's language.
        """
        return cls.for_language(locale.language)

    def month_name(self, month: int) -> str:
        """Return the full month name.

        Parameters
        ----------
        month : int
            Calendar month from 1 to 12.

        Returns
        -------
        str
            Full month name in the active language.

        Raises
        ------
        ValueError
            If the month is outside 1-12.
        """
        if not 1 <= month <= MONTHS_PER_YEAR:
            message = f"Month must be between 1 and 12: {month}"
            raise ValueError(message)
        names = _SPANISH_MONTHS if self.language == "es" else _ENGLISH_MONTHS
        return names[month - 1]

    def short_month_name(self, month: int) -> str:
        """Return the abbreviated month name.

        Parameters
        ----------
        month : int
            Calendar month from 1 to 12.

        Returns
        -------
        str
            Abbreviated month name in the active language.

        Raises
        ------
        ValueError
            If the month is outside 1-12.
        """
        if not 1 <= month <= MONTHS_PER_YEAR:
            message = f"Month must be between 1 and 12: {month}"
            raise ValueError(message)
        names = _SPANISH_SHORT_MONTHS if self.language == "es" else _ENGLISH_SHORT_MONTHS
        return names[month - 1]

    def weekday_labels(self) -> tuple[str, ...]:
        """Return the Monday-first weekday labels.

        Returns
        -------
        tuple[str, ...]
            Seven two-letter labels, Monday first.
        """
        return _SPANISH_WEEKDAYS if self.language == "es" else _ENGLISH_WEEKDAYS

    def log_title(self, date: afanes.models.note.NoteDate) -> str:
        """Return the long default title for a log date.

        Parameters
        ----------
        date : afanes.models.note.NoteDate
            Date at year, month, or day precision.

        Returns
        -------
        str
            Year title, month title, or day title in the active language.
        """
        if date.precision is afanes.models.note.DatePrecision.YEAR:
            return f"{date.year:04d}"
        month = self.month_name(date.month)
        if date.precision is afanes.models.note.DatePrecision.MONTH:
            return f"{month} {date.year:04d}" if self.language == "en" else f"{month} de {date.year:04d}"
        if self.language == "en":
            return f"{month} {date.day}, {date.year:04d}"
        return f"{date.day} de {month} de {date.year:04d}"

    def short_date(self, date: afanes.models.note.NoteDate) -> str:
        """Return a compact human-readable date.

        Parameters
        ----------
        date : afanes.models.note.NoteDate
            Date at year, month, or day precision.

        Returns
        -------
        str
            Compact date used in metadata rows. ISO input and filenames never
            use this method.
        """
        if date.precision is afanes.models.note.DatePrecision.YEAR:
            return f"{date.year:04d}"
        month = self.short_month_name(date.month)
        if date.precision is afanes.models.note.DatePrecision.MONTH:
            return f"{month} {date.year:04d}"
        if self.language == "en":
            return f"{month} {date.day}, {date.year:04d}"
        return f"{date.day} {month} {date.year:04d}"

    def time(self, value: datetime.time) -> str:
        """Return a clock time in the active language.

        Parameters
        ----------
        value : ``datetime.time``
            Clock time.

        Returns
        -------
        str
            Twelve-hour time with an English meridiem marker, or a zero-padded
            twenty-four-hour time in Spanish.
        """
        if self.language == "es":
            return f"{value.hour:02d}:{value.minute:02d}"
        hour = value.hour % HOURS_PER_HALF_DAY
        if hour == 0:
            hour = HOURS_PER_HALF_DAY
        marker = "AM" if value.hour < HOURS_PER_HALF_DAY else "PM"
        return f"{hour}:{value.minute:02d} {marker}"

    def count(self, value: int) -> str:
        """Return an integer with comma grouping.

        Parameters
        ----------
        value : int
            Count to format.

        Returns
        -------
        str
            Grouped count such as ``1,234``. Both supported languages use comma
            grouping and the dot as the decimal separator.

        Notes
        -----
        Spanish regional formats disagree about grouping. The supported
        convention is the Mexican one: comma grouping and dot decimals.
        Decimal values are not rendered by this method.
        """
        return f"{value:,d}"
