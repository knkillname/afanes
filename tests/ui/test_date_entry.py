"""Tests for the shared date entry dialog and field action."""

import asyncio
import datetime
import typing

import flet as ft
import pytest

import afanes.core.localization
import afanes.i18n.ui
import afanes.models.note
import afanes.ui.components.date_entry as date_entry_component
import afanes.ui.theme

ALL_PRECISIONS = frozenset(
    {
        afanes.models.note.DatePrecision.DAY,
        afanes.models.note.DatePrecision.MONTH,
        afanes.models.note.DatePrecision.YEAR,
    }
)
DAY_ONLY = frozenset({afanes.models.note.DatePrecision.DAY})
TODAY = datetime.date(2026, 11, 14)
NOVEMBER_LAST_DAY = 30


def _event(key: str, *, shift: bool = False) -> ft.KeyboardEvent:
    return ft.KeyboardEvent(
        name="key_down",
        control=typing.cast("ft.Page", None),
        key=key,
        shift=shift,
        ctrl=False,
        alt=False,
        meta=False,
    )


def _note(text: str) -> afanes.models.note.NoteDate:
    return afanes.models.note.NoteDate.from_text(text)


def _dialog(
    current: afanes.models.note.NoteDate | None = None,
    *,
    precisions: frozenset[afanes.models.note.DatePrecision] = ALL_PRECISIONS,
    copy: afanes.i18n.ui.UiCopy | None = None,
    update: typing.Callable[[], None] | None = None,
    today: datetime.date = TODAY,
) -> tuple[date_entry_component.DatePickerDialog, list[afanes.models.note.NoteDate], list[bool]]:
    confirmed: list[afanes.models.note.NoteDate] = []
    cancelled: list[bool] = []

    async def confirm(value: afanes.models.note.NoteDate) -> None:
        confirmed.append(value)

    async def cancel() -> None:
        cancelled.append(True)

    dialog = date_entry_component.DatePickerDialog(
        current,
        precisions,
        confirm,
        cancel,
        copy=copy,
        today=today,
        update=update,
    )
    return dialog, confirmed, cancelled


async def _ignore_confirm(_value: afanes.models.note.NoteDate) -> None:
    return None


async def _ignore_cancel() -> None:
    return None


def _noop() -> None:
    return None


def _run(awaitable: typing.Awaitable[None]) -> None:
    asyncio.run(typing.cast("typing.Coroutine[typing.Any, typing.Any, None]", awaitable))


def _run_bool(awaitable: typing.Awaitable[bool]) -> bool:
    return asyncio.run(typing.cast("typing.Coroutine[typing.Any, typing.Any, bool]", awaitable))


def _click(control: ft.TextButton | ft.IconButton | ft.OutlinedButton) -> None:
    handler = control.on_click
    assert handler is not None
    typing.cast("typing.Callable[[], None]", handler)()


def _focus(control: ft.TextButton) -> None:
    handler = control.on_focus
    assert handler is not None
    typing.cast("typing.Callable[[], None]", handler)()


class TestDialogShell:
    def test_builds_the_title_caption_and_actions(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        assert dialog.dialog.key == "date-picker-dialog"
        assert dialog.dialog.modal is False
        assert isinstance(dialog.dialog.title, ft.Text)
        assert dialog.dialog.title.value == "Choose Date"
        assert dialog.caption.value == "Selected: November 14, 2026"
        actions = dialog.dialog.actions
        assert actions is not None
        assert [action.key for action in actions] == [
            "date-picker-current",
            "date-picker-cancel",
            "date-picker-select",
        ]

    def test_select_and_cancel_are_named_actions(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        assert isinstance(dialog.select_button.content, str)
        assert dialog.select_button.content == "Select"
        assert isinstance(dialog.cancel_button.content, str)
        assert dialog.cancel_button.content == "Cancel"
        assert isinstance(dialog.select_button, ft.OutlinedButton)

    def test_all_precisions_show_three_modes(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        assert dialog.mode_row.visible is True
        assert [button.key for button in dialog.mode_row.controls] == [
            "date-picker-mode-day",
            "date-picker-mode-month",
            "date-picker-mode-year",
        ]

    def test_day_only_hides_the_mode_switch(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"), precisions=DAY_ONLY)

        assert dialog.mode_row.visible is False
        assert [button.key for button in dialog.mode_row.controls] == ["date-picker-mode-day"]

    def test_the_caption_follows_the_active_precision(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)
        assert dialog.caption.value == "Selected: November 2026"
        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)
        assert dialog.caption.value == "Selected: 2026"

    def test_the_current_action_follows_the_mode(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        assert dialog.current_button.content == "Today"
        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)
        assert dialog.current_button.content == "This Month"
        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)
        assert dialog.current_button.content == "This Year"

    def test_the_day_header_names_the_month_and_year(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        assert dialog.period_title.value == "November 2026"

    def test_the_month_header_names_the_year(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)

        assert dialog.period_title.value == "2026"

    def test_the_year_header_names_the_decade(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)

        assert dialog.period_title.value == "2020-2029"

    def test_an_empty_precision_set_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one precision"):
            date_entry_component.DatePickerDialog(None, frozenset(), _ignore_confirm, _ignore_cancel)

    def test_an_inverted_range_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="first date"):
            date_entry_component.DatePickerDialog(
                None,
                ALL_PRECISIONS,
                _ignore_confirm,
                _ignore_cancel,
                first_date=datetime.date(2026, 1, 2),
                last_date=datetime.date(2026, 1, 1),
            )


class TestInitialPrecision:
    def test_a_day_value_opens_in_day_mode(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        assert dialog.precision is afanes.models.note.DatePrecision.DAY
        assert dialog.anchor == datetime.date(2026, 11, 14)
        assert dialog.result == _note("2026-11-14")

    def test_a_month_value_opens_in_month_mode(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11"))

        assert dialog.precision is afanes.models.note.DatePrecision.MONTH
        assert dialog.result == _note("2026-11")

    def test_a_year_value_opens_in_year_mode(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026"))

        assert dialog.precision is afanes.models.note.DatePrecision.YEAR
        assert dialog.result == _note("2026")

    def test_an_empty_value_opens_in_day_mode_with_today(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(None)

        assert dialog.precision is afanes.models.note.DatePrecision.DAY
        assert dialog.anchor == TODAY
        assert dialog.result == _note("2026-11-14")

    def test_a_precision_the_field_forbids_falls_back_to_day(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11"), precisions=DAY_ONLY)

        assert dialog.precision is afanes.models.note.DatePrecision.DAY

    def test_a_month_value_uses_today_for_the_hidden_day(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-02"))

        assert dialog.anchor == datetime.date(2026, 2, 14)

    def test_a_short_month_clamps_the_hidden_day(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(
            _note("2026-02"),
            today=datetime.date(2026, 3, 31),
        )

        assert dialog.anchor == datetime.date(2026, 2, 28)


class TestPrecisionOutput:
    def test_each_mode_writes_its_precision(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        assert dialog.result.text == "2026-11-14"
        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)
        assert dialog.result.text == "2026-11"
        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)
        assert dialog.result.text == "2026"

    def test_day_to_month_to_day_round_trips(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)
        dialog.set_precision(afanes.models.note.DatePrecision.DAY)

        assert dialog.anchor == datetime.date(2026, 11, 14)
        assert dialog.result == _note("2026-11-14")

    def test_a_short_month_clamps_the_day(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-01-31"))

        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)
        dialog.select_month(2)
        dialog.set_precision(afanes.models.note.DatePrecision.DAY)

        assert dialog.anchor == datetime.date(2026, 2, 28)

    def test_a_leap_day_clamps_in_a_common_year(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2028-02-29"))

        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)
        dialog.select_year(2027)
        dialog.set_precision(afanes.models.note.DatePrecision.DAY)

        assert dialog.anchor == datetime.date(2027, 2, 28)

    def test_selecting_a_year_keeps_the_month_and_day(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-07-09"))

        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)
        dialog.select_year(2030)

        assert dialog.result == _note("2030")

    def test_selecting_a_month_keeps_the_year_and_day(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-07-09"))

        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)
        dialog.select_month(12)

        assert dialog.result == _note("2026-12")

    def test_a_forbidden_precision_is_ignored(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"), precisions=DAY_ONLY)

        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)

        assert dialog.precision is afanes.models.note.DatePrecision.DAY


class TestGrids:
    def test_the_month_grid_lists_the_localized_months(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)

        labels = [button.content for button in dialog.month_buttons.values()]
        assert labels == [
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
        ]
        selected = dialog.month_buttons[11].style
        assert selected is not None
        assert selected.bgcolor == afanes.ui.theme.CALENDAR_SELECTED_COLOR

    def test_the_year_grid_shows_the_decade(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)

        assert sorted(dialog.year_buttons) == list(range(2020, 2030))
        selected = dialog.year_buttons[2026].style
        assert selected is not None
        assert selected.bgcolor == afanes.ui.theme.CALENDAR_SELECTED_COLOR

    def test_the_year_page_marks_today(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-01-01"))

        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)

        style = dialog.year_buttons[2026].style
        assert style is not None
        assert style.side == afanes.ui.theme.CALENDAR_TODAY_SIDE

    def test_the_next_button_pages_the_decade(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))
        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)

        _click(dialog.next_button)

        assert dialog.period_title.value == "2030-2039"
        assert dialog.anchor.year == TODAY.year + 10

    def test_the_previous_button_wraps_a_month_across_the_year(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-01-31"))

        _click(dialog.previous_button)

        assert dialog.anchor == datetime.date(2025, 12, 31)

    def test_the_large_chevrons_move_by_year(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        _click(dialog.next_large_button)

        assert dialog.anchor == datetime.date(2027, 11, 14)

    def test_the_current_action_selects_today(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2020-01-01"))

        _click(dialog.current_button)

        assert dialog.anchor == TODAY

    def test_the_current_action_selects_the_current_month(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2020-01-31"))

        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)
        _click(dialog.current_button)

        assert dialog.result == _note("2026-11")
        assert dialog.anchor.day == NOVEMBER_LAST_DAY

    def test_the_current_action_selects_the_current_year(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2020-01-01"))

        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)
        _click(dialog.current_button)

        assert dialog.result == _note("2026")

    def test_a_year_before_1900_is_selectable(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("0005-06-15"))

        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)
        dialog.select_year(1801)

        assert dialog.result == _note("1801")

    def test_a_year_after_2100_is_selectable(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2150-03-04"))

        assert dialog.result == _note("2150-03-04")

    def test_the_calendar_extremes_are_selectable(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("0001-01-01"))

        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)
        assert dialog.period_title.value == "0001-0010"
        dialog.select_year(9999)
        dialog.set_precision(afanes.models.note.DatePrecision.DAY)

        assert dialog.result == _note("9999-01-01")


class TestKeyboard:
    def test_day_arrows_move_by_day_and_week(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        _run_bool(dialog.handle_key(_event("Arrow Right")))
        assert dialog.anchor == datetime.date(2026, 11, 15)
        _run_bool(dialog.handle_key(_event("Arrow Down")))
        assert dialog.anchor == datetime.date(2026, 11, 22)
        _run_bool(dialog.handle_key(_event("Arrow Up")))
        assert dialog.anchor == datetime.date(2026, 11, 15)

    def test_day_page_keys_move_by_month_and_year(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        _run_bool(dialog.handle_key(_event("Page Down")))
        assert dialog.anchor == datetime.date(2026, 12, 14)
        _run_bool(dialog.handle_key(_event("Page Up", shift=True)))
        assert dialog.anchor == datetime.date(2025, 12, 14)
        _run_bool(dialog.handle_key(_event("Page Down", shift=True)))
        assert dialog.anchor == datetime.date(2026, 12, 14)
        _run_bool(dialog.handle_key(_event("Page Up")))
        assert dialog.anchor == datetime.date(2026, 11, 14)

    def test_day_home_and_end_move_to_the_week_boundary(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        _run_bool(dialog.handle_key(_event("Home")))
        assert dialog.anchor == datetime.date(2026, 11, 9)
        _run_bool(dialog.handle_key(_event("End")))
        assert dialog.anchor == datetime.date(2026, 11, 15)

    def test_month_arrows_move_by_month_and_row(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))
        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)

        _run_bool(dialog.handle_key(_event("Arrow Right")))
        assert dialog.result == _note("2026-12")
        _run_bool(dialog.handle_key(_event("Arrow Down")))
        assert dialog.result == _note("2027-03")
        _run_bool(dialog.handle_key(_event("Arrow Up")))
        assert dialog.result == _note("2026-12")

    def test_month_page_keys_move_by_year(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))
        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)

        _run_bool(dialog.handle_key(_event("Page Down")))
        assert dialog.result == _note("2027-11")

    def test_month_home_and_end_move_to_january_and_december(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))
        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)

        _run_bool(dialog.handle_key(_event("Home")))
        assert dialog.result == _note("2026-01")
        _run_bool(dialog.handle_key(_event("End")))
        assert dialog.result == _note("2026-12")

    def test_year_arrows_move_by_year_and_row(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))
        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)

        _run_bool(dialog.handle_key(_event("Arrow Right")))
        assert dialog.result == _note("2027")
        _run_bool(dialog.handle_key(_event("Arrow Down")))
        assert dialog.result == _note("2032")
        _run_bool(dialog.handle_key(_event("Arrow Up")))
        assert dialog.result == _note("2027")

    def test_year_page_keys_move_by_decade(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))
        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)

        _run_bool(dialog.handle_key(_event("Page Down")))
        assert dialog.result == _note("2036")
        _run_bool(dialog.handle_key(_event("Page Up")))
        assert dialog.result == _note("2026")

    def test_year_home_and_end_move_to_the_page_ends(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))
        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)

        _run_bool(dialog.handle_key(_event("Home")))
        assert dialog.result == _note("2020")
        _run_bool(dialog.handle_key(_event("End")))
        assert dialog.result == _note("2029")

    def test_enter_confirms_only_with_a_focused_grid_cell(self) -> None:
        dialog, confirmed, _cancelled = _dialog(_note("2026-11-14"))

        handled = _run_bool(dialog.handle_key(_event("Enter")))
        assert handled is False
        assert confirmed == []

        assert dialog.day_grid is not None
        _focus(dialog.day_grid.day_buttons[14])
        handled = _run_bool(dialog.handle_key(_event("Enter")))
        assert handled is True
        assert confirmed == [_note("2026-11-14")]

    def test_enter_confirms_a_month_cell(self) -> None:
        dialog, confirmed, _cancelled = _dialog(_note("2026-11-14"))
        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)
        _focus(dialog.month_buttons[11])

        handled = _run_bool(dialog.handle_key(_event("Enter")))

        assert handled is True
        assert confirmed == [_note("2026-11")]

    def test_escape_cancels(self) -> None:
        dialog, _confirmed, cancelled = _dialog(_note("2026-11-14"))

        handled = _run_bool(dialog.handle_key(_event("Escape")))

        assert handled is True
        assert cancelled == [True]

    def test_tab_is_left_to_the_toolkit(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        handled = _run_bool(dialog.handle_key(_event("Tab")))

        assert handled is False

    def test_an_unknown_key_is_not_handled(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        handled = _run_bool(dialog.handle_key(_event("F5")))

        assert handled is False

    def test_focus_follows_the_moved_selection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        dialog, _confirmed, _cancelled = _dialog(
            _note("2026-11-30"),
            update=_noop,
        )
        focused: list[int] = []

        async def fake_focus(day: int) -> None:
            focused.append(day)

        assert dialog.day_grid is not None
        monkeypatch.setattr(dialog.day_grid, "focus_day", fake_focus)

        _run_bool(dialog.handle_key(_event("Arrow Right")))

        assert dialog.anchor == datetime.date(2026, 12, 1)
        assert focused == [1]

    def test_open_focuses_the_selected_day(self, monkeypatch: pytest.MonkeyPatch) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"), update=_noop)
        focused: list[int] = []

        async def fake_focus(day: int) -> None:
            focused.append(day)

        assert dialog.day_grid is not None
        monkeypatch.setattr(dialog.day_grid, "focus_day", fake_focus)

        _run(dialog.open())

        assert focused == [14]


class TestLocalization:
    def test_english_month_and_weekdays(self) -> None:
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"))

        assert dialog.period_title.value == "November 2026"
        assert dialog.day_grid is not None
        labels = [control.value for control in dialog.day_grid.weekdays.controls if isinstance(control, ft.Text)]
        assert labels == ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    def test_spanish_month_weekdays_and_controls(self) -> None:
        copy = afanes.i18n.ui.UiCopy.for_locale(afanes.core.localization.LocaleTag.parse("es"))
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"), copy=copy)

        assert dialog.period_title.value == "noviembre de 2026"
        assert isinstance(dialog.dialog.title, ft.Text)
        assert dialog.dialog.title.value == "Elegir fecha"
        assert dialog.select_button.content == "Seleccionar"
        assert dialog.cancel_button.content == "Cancelar"
        assert dialog.caption.value == "Selección: 14 de noviembre de 2026"
        assert dialog.current_button.content == "Hoy"
        assert dialog.day_grid is not None
        labels = [control.value for control in dialog.day_grid.weekdays.controls if isinstance(control, ft.Text)]
        assert labels == ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]

    def test_spanish_modes_and_period_actions(self) -> None:
        copy = afanes.i18n.ui.UiCopy.for_locale(afanes.core.localization.LocaleTag.parse("es"))
        dialog, _confirmed, _cancelled = _dialog(_note("2026-11-14"), copy=copy)

        assert [button.content for button in dialog.mode_buttons.values()] == ["Día", "Mes", "Año"]
        dialog.set_precision(afanes.models.note.DatePrecision.MONTH)
        assert dialog.current_button.content == "Este mes"
        dialog.set_precision(afanes.models.note.DatePrecision.YEAR)
        assert dialog.current_button.content == "Este año"

    def test_the_chosen_value_is_locale_independent(self) -> None:
        english, _confirmed, _cancelled = _dialog(_note("2026-11-14"))
        spanish_copy = afanes.i18n.ui.UiCopy.for_locale(afanes.core.localization.LocaleTag.parse("es"))
        spanish, _confirmed_es, _cancelled_es = _dialog(_note("2026-11-14"), copy=spanish_copy)

        assert english.result == spanish.result


class TestDatePickerButton:
    def test_attaches_to_a_field_suffix(self) -> None:
        async def pick() -> afanes.models.note.NoteDate | None:
            return None

        async def picked(_value: afanes.models.note.NoteDate) -> None:
            return None

        field = ft.TextField(label="Date")
        button = date_entry_component.DatePickerButton(date_entry_component.DatePickerActions(pick, picked))

        attached = button.attach(field)

        assert attached is field
        assert field.suffix is button.button
        assert button.button.key == "date-picker-open"
        assert button.button.tooltip == "Choose Date…"

    def test_a_picked_value_reaches_the_field(self) -> None:
        async def pick() -> afanes.models.note.NoteDate | None:
            return _note("2026-12-01")

        written: list[afanes.models.note.NoteDate] = []

        async def picked(value: afanes.models.note.NoteDate) -> None:
            written.append(value)

        button = date_entry_component.DatePickerButton(date_entry_component.DatePickerActions(pick, picked))
        handler = button.button.on_click
        assert handler is not None

        _run(typing.cast("typing.Callable[[], typing.Awaitable[None]]", handler)())

        assert written == [_note("2026-12-01")]

    def test_a_cancelled_pick_writes_nothing(self) -> None:
        async def pick() -> afanes.models.note.NoteDate | None:
            return None

        written: list[afanes.models.note.NoteDate] = []

        async def picked(value: afanes.models.note.NoteDate) -> None:
            written.append(value)

        button = date_entry_component.DatePickerButton(date_entry_component.DatePickerActions(pick, picked))
        handler = button.button.on_click
        assert handler is not None

        _run(typing.cast("typing.Callable[[], typing.Awaitable[None]]", handler)())

        assert written == []

    def test_the_tooltip_uses_the_active_locale(self) -> None:
        async def pick() -> afanes.models.note.NoteDate | None:
            return None

        async def picked(_value: afanes.models.note.NoteDate) -> None:
            return None

        copy = afanes.i18n.ui.UiCopy.for_locale(afanes.core.localization.LocaleTag.parse("es"))
        button = date_entry_component.DatePickerButton(date_entry_component.DatePickerActions(pick, picked), copy=copy)

        assert button.button.tooltip == "Elegir fecha…"
