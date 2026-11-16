"""Tests for the Log month calendar component."""

import asyncio
import datetime
import typing

import flet as ft

import afanes.core.localization
import afanes.core.log
import afanes.i18n.ui
import afanes.ui.components.calendar as calendar_component
import afanes.ui.theme

START_DAY = 12
NEXT_DAY = 13
PREVIOUS_DAY = 19
NEXT_WEEK_DAY = 20
MID_MONTH = 15
WEEK_START_DAY = 6
NOVEMBER = 11


def _day_text(grid: calendar_component.CalendarGrid, day: int) -> ft.Text:
    content = grid.day_buttons[day].content
    assert isinstance(content, ft.Column)
    number = content.controls[0]
    assert isinstance(number, ft.Text)
    return number


def _keyboard(key: str, *, ctrl: bool = False) -> ft.KeyboardEvent:
    return ft.KeyboardEvent(
        name="key_down",
        control=typing.cast("ft.Page", None),
        key=key,
        shift=False,
        ctrl=ctrl,
        alt=False,
        meta=False,
    )


def _month(
    *, day_counts: dict[int, int] | None = None, month_count: int = 0, year_count: int = 0
) -> afanes.core.log.CalendarMonth:
    counts = day_counts or {}
    return afanes.core.log.CalendarMonth(
        year=2025,
        month=10,
        first_weekday=2,
        days_in_month=31,
        days=tuple(afanes.core.log.CalendarDay(day=day, count=counts.get(day, 0)) for day in range(1, 32)),
        month_count=month_count,
        year_count=year_count,
    )


class TestLogCalendar:
    def test_builds_a_month_grid_with_accents(self) -> None:
        selected: list[int] = []
        calendar = calendar_component.LogCalendar(selected.append, lambda: None, lambda: None)

        control = calendar.build(_month(day_counts={12: 2}, month_count=1, year_count=1))

        assert control.key == "log-calendar"
        assert calendar.title.value == "October 2025"
        assert calendar.month_dot.visible is True
        assert calendar.year_dot.visible is True
        assert calendar.month_dot.bgcolor == afanes.ui.theme.LOG_ENTRY_DOT_COLOR
        assert calendar.year_dot.bgcolor == afanes.ui.theme.LOG_ENTRY_DOT_COLOR
        assert afanes.ui.theme.LOG_ENTRY_DOT_COLOR == afanes.ui.theme.ACCENT_FILL
        assert calendar.day_buttons[12].data == {"day": 12, "count": 2}
        style = calendar.day_buttons[START_DAY].style
        assert style is not None
        assert style.bgcolor == afanes.ui.theme.LOG_ENTRY_TINT
        plain_style = calendar.day_buttons[NEXT_DAY].style
        assert plain_style is None or plain_style.bgcolor is None

    def test_day_dots_follow_the_filtered_counts(self) -> None:
        calendar = calendar_component.LogCalendar(lambda _day: None, lambda: None, lambda: None)

        calendar.build(_month(day_counts={12: 0, 13: 1}))

        hidden = calendar.day_buttons[12].content
        shown = calendar.day_buttons[13].content
        assert isinstance(hidden, ft.Column)
        assert isinstance(shown, ft.Column)
        assert isinstance(hidden.controls[1], ft.Container)
        assert isinstance(shown.controls[1], ft.Container)
        assert hidden.controls[1].visible is False
        assert shown.controls[1].visible is True

    def test_empty_month_hides_header_dots(self) -> None:
        calendar = calendar_component.LogCalendar(lambda _day: None, lambda: None, lambda: None)

        calendar.build(_month())

        assert calendar.month_dot.visible is False
        assert calendar.year_dot.visible is False
        assert all(button.style is None or button.style.bgcolor is None for button in calendar.day_buttons.values())

    def test_day_click_reports_the_day(self) -> None:
        selected: list[int] = []
        calendar = calendar_component.LogCalendar(selected.append, lambda: None, lambda: None)
        calendar.build(_month())
        handler = calendar.day_buttons[START_DAY].on_click
        assert handler is not None

        typing.cast("typing.Callable[[], None]", handler)()

        assert selected == [12]

    def test_month_navigation_forwards(self) -> None:
        calls: list[str] = []
        calendar = calendar_component.LogCalendar(
            lambda _day: None,
            lambda: calls.append("previous"),
            lambda: calls.append("next"),
        )
        calendar.build(_month())
        previous = calendar.prev_button.on_click
        upcoming = calendar.next_button.on_click
        assert previous is not None
        assert upcoming is not None

        typing.cast("typing.Callable[[], None]", previous)()
        typing.cast("typing.Callable[[], None]", upcoming)()

        assert calls == ["previous", "next"]

    def test_arrows_move_focus_by_day_and_week(self) -> None:
        calendar = calendar_component.LogCalendar(lambda _day: None, lambda: None, lambda: None)
        calendar.build(_month())

        asyncio.run(calendar.focus_date(datetime.date(2025, 10, START_DAY)))
        assert asyncio.run(calendar.handle_key(_keyboard("ArrowRight"))) is True
        assert calendar.focused_day == NEXT_DAY
        assert asyncio.run(calendar.handle_key(_keyboard("ArrowDown"))) is True
        assert calendar.focused_day == NEXT_WEEK_DAY
        assert asyncio.run(calendar.handle_key(_keyboard("ArrowLeft"))) is True
        assert calendar.focused_day == PREVIOUS_DAY
        assert asyncio.run(calendar.handle_key(_keyboard("ArrowUp"))) is True
        assert calendar.focused_day == START_DAY

    def test_page_keys_move_by_month(self) -> None:
        moved: list[datetime.date] = []

        async def record(value: datetime.date) -> None:
            moved.append(value)

        calendar = calendar_component.LogCalendar(
            lambda _day: None,
            lambda: None,
            lambda: None,
            on_move=record,
        )
        calendar.build(_month())
        asyncio.run(calendar.focus_date(datetime.date(2025, 10, MID_MONTH)))

        assert asyncio.run(calendar.handle_key(_keyboard("PageDown"))) is True
        assert asyncio.run(calendar.handle_key(_keyboard("PageUp"))) is True

        assert moved == [datetime.date(2025, NOVEMBER, MID_MONTH)]
        assert calendar.focused_day == MID_MONTH

    def test_home_and_end_reach_the_week_bounds(self) -> None:
        calendar = calendar_component.LogCalendar(lambda _day: None, lambda: None, lambda: None)
        calendar.build(_month())
        asyncio.run(calendar.focus_date(datetime.date(2025, 10, START_DAY)))

        assert asyncio.run(calendar.handle_key(_keyboard("Home"))) is True
        assert calendar.focused_day == WEEK_START_DAY
        assert asyncio.run(calendar.handle_key(_keyboard("End"))) is True
        assert calendar.focused_day == START_DAY

    def test_enter_matches_a_pointer_click(self) -> None:
        selected: list[int] = []
        calendar = calendar_component.LogCalendar(selected.append, lambda: None, lambda: None)
        calendar.build(_month())
        asyncio.run(calendar.focus_date(datetime.date(2025, 10, START_DAY)))

        assert asyncio.run(calendar.handle_key(_keyboard("Enter"))) is True
        typing.cast("typing.Callable[[], None]", calendar.day_buttons[START_DAY].on_click)()

        assert selected == [12, 12]

    def test_tab_and_control_chords_leave_the_calendar(self) -> None:
        calendar = calendar_component.LogCalendar(lambda _day: None, lambda: None, lambda: None)
        calendar.build(_month())
        asyncio.run(calendar.focus_date(datetime.date(2025, 10, START_DAY)))

        assert asyncio.run(calendar.handle_key(_keyboard("Tab"))) is False
        assert asyncio.run(calendar.handle_key(_keyboard("F", ctrl=True))) is False
        assert calendar.focused_day == START_DAY

    def test_the_focus_ring_follows_a_keyboard_move(self) -> None:
        calendar = calendar_component.LogCalendar(lambda _day: None, lambda: None, lambda: None)
        calendar.build(_month())
        asyncio.run(calendar.focus_date(datetime.date(2025, 10, START_DAY)))

        asyncio.run(calendar.handle_key(_keyboard("ArrowRight")))

        focused = calendar.day_buttons[NEXT_DAY].style
        previous = calendar.day_buttons[START_DAY].style
        assert focused is not None
        assert focused.side == afanes.ui.theme.CALENDAR_FOCUS_SIDE
        assert previous is None or previous.side is None


class TestCalendarGrid:
    def test_selected_day_uses_the_neutral_fill(self) -> None:
        grid = calendar_component.CalendarGrid(
            lambda _day: None,
            selected=datetime.date(2025, 10, 12),
        )

        grid.build(_month())

        style = grid.day_buttons[12].style
        assert style is not None
        assert style.bgcolor == afanes.ui.theme.CALENDAR_SELECTED_COLOR
        assert afanes.ui.theme.CALENDAR_SELECTED_COLOR == afanes.ui.theme.SELECTED_ROW_COLOR

    def test_today_uses_accent_text_and_a_bold_weight(self) -> None:
        grid = calendar_component.CalendarGrid(
            lambda _day: None,
            today=datetime.date(2025, 10, 13),
        )

        grid.build(_month())

        style = grid.day_buttons[13].style
        assert style is not None
        assert style.side is None
        number = _day_text(grid, 13)
        assert number.style == afanes.ui.theme.CALENDAR_TODAY_TEXT
        assert afanes.ui.theme.CALENDAR_TODAY_TEXT.color == afanes.ui.theme.CALENDAR_TODAY_COLOR
        assert afanes.ui.theme.CALENDAR_TODAY_TEXT.weight == ft.FontWeight.W_700

    def test_selected_today_keeps_the_neutral_fill(self) -> None:
        today = datetime.date(2025, 10, 12)
        grid = calendar_component.CalendarGrid(lambda _day: None, selected=today, today=today)

        grid.build(_month())

        style = grid.day_buttons[12].style
        assert style is not None
        assert style.bgcolor == afanes.ui.theme.CALENDAR_SELECTED_COLOR
        assert style.side is None
        assert _day_text(grid, 12).style == afanes.ui.theme.CALENDAR_TODAY_TEXT

    def test_set_marks_moves_the_selection_and_today(self) -> None:
        grid = calendar_component.CalendarGrid(lambda _day: None)
        grid.build(_month())
        selected = datetime.date(2025, 10, 20)
        today = datetime.date(2025, 10, 21)

        grid.set_marks(selected, today)

        selected_style = grid.day_buttons[20].style
        today_style = grid.day_buttons[21].style
        assert selected_style is not None
        assert today_style is not None
        assert selected_style.bgcolor == afanes.ui.theme.CALENDAR_SELECTED_COLOR
        assert today_style.side is None
        assert _day_text(grid, 21).style == afanes.ui.theme.CALENDAR_TODAY_TEXT
        assert grid.day_buttons[12].style is not None
        assert grid.day_buttons[12].style.bgcolor is None

    def test_the_focus_ring_moves_with_the_focused_day(self) -> None:
        grid = calendar_component.CalendarGrid(lambda _day: None)
        grid.build(_month())

        grid.mark_focus(12)

        focused = grid.day_buttons[12].style
        assert focused is not None
        assert focused.side == afanes.ui.theme.CALENDAR_FOCUS_SIDE

        grid.mark_focus(13)

        previous = grid.day_buttons[12].style
        moved = grid.day_buttons[13].style
        assert previous is not None
        assert moved is not None
        assert previous.side is None
        assert moved.side == afanes.ui.theme.CALENDAR_FOCUS_SIDE

    def test_a_custom_tooltip_names_the_day(self) -> None:
        grid = calendar_component.CalendarGrid(
            lambda _day: None,
            day_tooltip=lambda cell: f"day {cell.day}",
        )

        grid.build(_month())

        assert grid.day_buttons[12].tooltip == "day 12"

    def test_day_focus_and_blur_report_the_day(self) -> None:
        events: list[tuple[str, int]] = []
        grid = calendar_component.CalendarGrid(
            lambda _day: None,
            on_day_focus=lambda day: events.append(("focus", day)),
            on_day_blur=lambda day: events.append(("blur", day)),
        )
        grid.build(_month())
        focus = grid.day_buttons[12].on_focus
        blur = grid.day_buttons[12].on_blur
        assert focus is not None
        assert blur is not None

        typing.cast("typing.Callable[[], None]", focus)()
        typing.cast("typing.Callable[[], None]", blur)()

        assert events == [("focus", 12), ("blur", 12)]

    def test_grid_keys_carry_the_prefix(self) -> None:
        grid = calendar_component.CalendarGrid(lambda _day: None, key_prefix="picker")

        control = grid.build(_month())

        assert control.key == "picker-grid-root"
        assert grid.weekdays.key == "picker-weekdays"
        assert grid.grid.key == "picker-grid"
        assert grid.day_buttons[12].key == "picker-day-12"


class TestSpanishCalendar:
    def test_month_and_weekday_labels_are_spanish(self) -> None:
        copy = afanes.i18n.ui.UiCopy.for_locale(afanes.core.localization.LocaleTag.parse("es"))
        calendar = calendar_component.LogCalendar(
            lambda _day: None,
            lambda: None,
            lambda: None,
            copy=copy,
        )

        calendar.build(_month())

        assert calendar.title.value == "octubre de 2025"
        weekday_texts = [control.value for control in calendar.weekdays.controls if isinstance(control, ft.Text)]
        assert weekday_texts == ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]

    def test_english_month_and_weekday_labels_remain_english(self) -> None:
        calendar = calendar_component.LogCalendar(lambda _day: None, lambda: None, lambda: None)

        calendar.build(_month())

        assert calendar.title.value == "October 2025"
        weekday_texts = [control.value for control in calendar.weekdays.controls if isinstance(control, ft.Text)]
        assert weekday_texts == ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
