"""Tests for locale selection and locale-aware display formatting."""

import calendar
import datetime
import locale

import pytest

from afanes.core.localization import LocaleFormat, LocaleResolver, LocaleTag
from afanes.models.note import DatePrecision, NoteDate


class TestLocaleTag:
    def test_a_regional_spanish_tag_resolves_to_spanish(self) -> None:
        tag = LocaleTag.parse("es-MX")

        assert tag.language == "es"
        assert tag.tag == "es-mx"

    def test_a_regional_english_tag_resolves_to_english(self) -> None:
        tag = LocaleTag.parse("en-GB")

        assert tag.language == "en"
        assert tag.tag == "en-gb"

    def test_an_unsupported_language_resolves_to_english(self) -> None:
        tag = LocaleTag.parse("fr-FR")

        assert tag.language == "en"
        assert tag.tag == "en"

    def test_an_encoding_suffix_is_removed(self) -> None:
        tag = LocaleTag.parse("es_ES.UTF-8")

        assert tag.language == "es"
        assert tag.tag == "es-es"

    def test_a_modifier_is_removed(self) -> None:
        tag = LocaleTag.parse("es_ES@euro")

        assert tag.tag == "es-es"

    def test_a_windows_locale_name_is_normalized(self) -> None:
        assert LocaleTag.parse("Spanish_Spain.1252").language == "es"
        assert LocaleTag.parse("English_United States.1252").language == "en"

    def test_an_unavailable_tag_resolves_to_english(self) -> None:
        assert LocaleTag.parse(None) == LocaleTag(language="en", tag="en")
        assert LocaleTag.parse("") == LocaleTag(language="en", tag="en")

    def test_an_unsupported_language_cannot_be_constructed(self) -> None:
        with pytest.raises(ValueError, match="Unsupported language"):
            LocaleTag(language="fr", tag="fr")


class TestLocaleResolver:
    def test_a_saved_spanish_override_wins(self) -> None:
        tag = LocaleResolver.resolve("es", {"LANG": "en_US.UTF-8"}, "en_US")

        assert tag.language == "es"

    def test_a_saved_english_override_wins(self) -> None:
        tag = LocaleResolver.resolve("en", {"LANG": "es_ES.UTF-8"}, "es_ES")

        assert tag.language == "en"

    def test_an_unsupported_override_falls_back_to_the_environment(self) -> None:
        tag = LocaleResolver.resolve("fr", {"LANG": "es_ES.UTF-8"}, "en_US")

        assert tag.language == "es"

    def test_lc_all_wins_over_the_other_variables(self) -> None:
        tag = LocaleResolver.resolve(None, {"LC_ALL": "en_US.UTF-8", "LC_MESSAGES": "es_ES.UTF-8"}, "es_ES")

        assert tag.language == "en"

    def test_lc_messages_wins_over_lang(self) -> None:
        tag = LocaleResolver.resolve(None, {"LC_MESSAGES": "es_ES.UTF-8", "LANG": "en_US.UTF-8"}, "en_US")

        assert tag.language == "es"

    def test_lang_wins_over_the_operating_system_locale(self) -> None:
        tag = LocaleResolver.resolve(None, {"LANG": "es_ES.UTF-8"}, "en_US")

        assert tag.language == "es"

    def test_the_operating_system_locale_is_used_when_the_environment_is_empty(self) -> None:
        tag = LocaleResolver.resolve(None, {}, "es_ES")

        assert tag.language == "es"

    def test_an_unsupported_environment_locale_resolves_to_english(self) -> None:
        tag = LocaleResolver.resolve(None, {"LANG": "fr_FR.UTF-8"}, "es_ES")

        assert tag.language == "en"

    def test_an_unavailable_system_locale_resolves_to_english(self) -> None:
        tag = LocaleResolver.resolve(None, {}, None)

        assert tag.language == "en"

    def test_a_windows_environment_name_resolves(self) -> None:
        assert LocaleResolver.resolve(None, {"LANG": "Spanish_Spain.1252"}, None).language == "es"
        assert LocaleResolver.resolve(None, {"LANG": "English_United States.1252"}, None).language == "en"

    def test_resolution_never_calls_setlocale(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fail(*_args: object, **_kwargs: object) -> None:
            message = "setlocale must not be called"
            raise AssertionError(message)

        monkeypatch.setattr(locale, "setlocale", fail)

        assert LocaleResolver.resolve(None, {"LANG": "es_ES.UTF-8"}, "es_ES").language == "es"

    def test_the_system_locale_reads_the_character_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def getlocale(_category: int) -> tuple[str | None, str | None]:
            return ("es_ES", "UTF-8")

        monkeypatch.setattr(locale, "getlocale", getlocale)

        assert LocaleResolver.system_locale() == "es_ES"

    def test_the_system_locale_is_none_when_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def getlocale(_category: int) -> tuple[str | None, str | None]:
            return (None, None)

        monkeypatch.setattr(locale, "getlocale", getlocale)

        assert LocaleResolver.system_locale() is None


class TestLocaleFormat:
    def test_an_english_day_title_uses_the_long_english_date(self) -> None:
        date = NoteDate("2026-11-13", DatePrecision.DAY)

        assert LocaleFormat.for_language("en").log_title(date) == "November 13, 2026"

    def test_a_spanish_day_title_uses_the_long_spanish_date(self) -> None:
        date = NoteDate("2026-11-13", DatePrecision.DAY)

        assert LocaleFormat.for_language("es").log_title(date) == "13 de noviembre de 2026"

    def test_an_english_month_title_uses_the_month_and_year(self) -> None:
        date = NoteDate("2026-11", DatePrecision.MONTH)

        assert LocaleFormat.for_language("en").log_title(date) == "November 2026"

    def test_a_spanish_month_title_uses_the_month_and_year(self) -> None:
        date = NoteDate("2026-11", DatePrecision.MONTH)

        assert LocaleFormat.for_language("es").log_title(date) == "noviembre de 2026"

    def test_a_year_title_is_the_year_in_both_languages(self) -> None:
        date = NoteDate("2026", DatePrecision.YEAR)

        assert LocaleFormat.for_language("en").log_title(date) == "2026"
        assert LocaleFormat.for_language("es").log_title(date) == "2026"

    def test_english_short_dates_use_the_abbreviated_month(self) -> None:
        date = NoteDate("2026-11-13", DatePrecision.DAY)

        assert LocaleFormat.for_language("en").short_date(date) == "Nov 13, 2026"

    def test_spanish_short_dates_put_the_day_first(self) -> None:
        date = NoteDate("2026-11-13", DatePrecision.DAY)

        assert LocaleFormat.for_language("es").short_date(date) == "13 nov 2026"

    def test_short_dates_keep_month_and_year_precision(self) -> None:
        month = NoteDate("2026-11", DatePrecision.MONTH)
        year = NoteDate("2026", DatePrecision.YEAR)

        assert LocaleFormat.for_language("en").short_date(month) == "Nov 2026"
        assert LocaleFormat.for_language("es").short_date(month) == "nov 2026"
        assert LocaleFormat.for_language("en").short_date(year) == "2026"
        assert LocaleFormat.for_language("es").short_date(year) == "2026"

    def test_month_names_are_localized(self) -> None:
        english = LocaleFormat.for_language("en")
        spanish = LocaleFormat.for_language("es")

        assert english.month_name(11) == "November"
        assert spanish.month_name(11) == "noviembre"

    def test_a_month_outside_the_calendar_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Month must be between"):
            LocaleFormat.for_language("en").month_name(13)

    def test_weekday_labels_are_localized_and_monday_first(self) -> None:
        assert LocaleFormat.for_language("en").weekday_labels() == ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
        assert LocaleFormat.for_language("es").weekday_labels() == ("Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do")

    def test_english_time_uses_a_twelve_hour_clock(self) -> None:
        assert LocaleFormat.for_language("en").time(datetime.time(14, 30)) == "2:30 PM"
        assert LocaleFormat.for_language("en").time(datetime.time(0, 5)) == "12:05 AM"

    def test_spanish_time_uses_a_twenty_four_hour_clock(self) -> None:
        assert LocaleFormat.for_language("es").time(datetime.time(14, 30)) == "14:30"
        assert LocaleFormat.for_language("es").time(datetime.time(0, 5)) == "00:05"

    def test_counts_use_comma_grouping_in_both_languages(self) -> None:
        assert LocaleFormat.for_language("en").count(1234) == "1,234"
        assert LocaleFormat.for_language("es").count(1234) == "1,234"

    def test_small_counts_are_unchanged(self) -> None:
        assert LocaleFormat.for_language("en").count(12) == "12"
        assert LocaleFormat.for_language("es").count(12) == "12"

    def test_an_unsupported_language_falls_back_to_english(self) -> None:
        assert LocaleFormat.for_language("fr").language == "en"

    def test_formatting_does_not_depend_on_calendar_month_names(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(calendar, "month_name", [])
        date = NoteDate("2026-11-13", DatePrecision.DAY)

        assert LocaleFormat.for_language("en").log_title(date) == "November 13, 2026"
        assert LocaleFormat.for_language("es").log_title(date) == "13 de noviembre de 2026"

    def test_formatting_does_not_depend_on_the_process_c_locale(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fail(*_args: object, **_kwargs: object) -> None:
            message = "setlocale must not be called"
            raise AssertionError(message)

        monkeypatch.setattr(locale, "setlocale", fail)
        date = NoteDate("2026-11-13", DatePrecision.DAY)

        assert LocaleFormat.for_language("es").short_date(date) == "13 nov 2026"
